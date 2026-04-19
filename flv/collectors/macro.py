"""FLV Macro Collector — Macroeconomic indicators (USD, Selic, IPCA, Diesel).

All series land in `flv_macro(series, obs_date, value, source)` with UPSERT semantics.
Consumed by `flv.model.feature_builder` as optional regressors.
"""
import urllib.request
import urllib.error
import json
import re
import time
from datetime import datetime, timedelta, timezone

# BCB SGS returns HTTP 406/400 when asked for the unbounded history of large
# series (e.g. sgs.1 spans 40+ years of daily ticks). Always request a bounded
# date range — this is the officially documented query shape.
BCB_BASE = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
    "?dataInicial={di}&dataFinal={df}&formato=json"
)

# series slug -> (SGS code, human label, source tag)
BCB_SERIES = {
    "usd_brl":      (1,     "Dolar PTAX venda (R$/USD)",         "BCB-SGS-1"),
    "selic_meta":   (432,   "Meta Selic anual (% a.a.)",         "BCB-SGS-432"),
    "ipca_yoy":     (13522, "IPCA acumulado 12 meses (%)",       "BCB-SGS-13522"),
}

# Lookback cap to avoid downloading decades of ticks every run.
DEFAULT_LOOKBACK_DAYS = 720

# Note: BCB SGS rejects some custom UA strings with HTTP 406. A browser-style UA
# is accepted for all series consistently.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; nias-macro/1.0)",
    "Accept": "application/json",
}


def _br_to_iso(date_br):
    """'dd/mm/yyyy' -> 'yyyy-mm-dd'. Returns None if malformed."""
    if not date_br:
        return None
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", date_br.strip())
    if not m:
        return None
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"


def _http_get_json(url, timeout=20):
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _upsert(conn, series, obs_date, value, source):
    conn.execute(
        "INSERT OR REPLACE INTO flv_macro (series, obs_date, value, source) VALUES (?,?,?,?)",
        (series, obs_date, float(value), source),
    )


def _bcb_date_range(lookback_days):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    return start.strftime("%d/%m/%Y"), end.strftime("%d/%m/%Y")


def fetch_bcb(conn, lookback_days=DEFAULT_LOOKBACK_DAYS):
    """Fetch all configured BCB SGS series. Returns number of rows inserted/updated."""
    di, df = _bcb_date_range(lookback_days)
    count = 0
    for slug, (code, _label, source) in BCB_SERIES.items():
        try:
            url = BCB_BASE.format(code=code, di=di, df=df)
            data = _http_get_json(url)
        except Exception as e:
            print(f"[FLV-Macro] BCB {slug} (sgs {code}) erro: {e}")
            continue

        if not isinstance(data, list):
            continue

        for row in data:
            iso = _br_to_iso(row.get("data"))
            val = row.get("valor")
            if not iso or val in (None, ""):
                continue
            try:
                _upsert(conn, slug, iso, float(val), source)
                count += 1
            except (ValueError, TypeError):
                continue
    conn.commit()
    return count


def fetch_diesel_anp(conn):
    """Best-effort diesel S10 national-average price via ANP open summary.

    ANP publishes a weekly CSV at
      https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca/ca-2024-02.csv
    (url schema changes over time). To stay robust, we attempt the lightweight
    JSON summary first; if it fails, we leave diesel blank and let the feature
    builder forward-fill.
    """
    # Try ANP's "ultima pesquisa" JSON (undocumented but stable since 2022).
    candidates = [
        "https://preco.anp.gov.br/include/Resumo_Semanal_Index.asp",
        "https://preco.anp.gov.br/include/Resumo_Por_Estado_Index.asp",
    ]
    price = None
    source = None
    for url in candidates:
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                html = resp.read().decode("latin-1", errors="ignore")
        except Exception:
            continue

        # Look for "DIESEL S10" followed by a price in R$ format.
        m = re.search(
            r"DIESEL\s*S[-\s]?10[^0-9]{0,200}?([0-9]+[,\.][0-9]{2,3})",
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            try:
                price = float(m.group(1).replace(",", "."))
                source = "ANP-ResumoSemanal"
                break
            except ValueError:
                continue

    if price is None:
        print("[FLV-Macro] Diesel ANP indisponivel — pulando (feature_builder fara forward-fill)")
        return 0

    obs_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        _upsert(conn, "diesel_s10", obs_date, price, source)
        conn.commit()
        return 1
    except Exception as e:
        print(f"[FLV-Macro] Diesel upsert erro: {e}")
        return 0


def fetch_all():
    """Pipeline entrypoint: fetch all macro series and upsert into flv_macro."""
    from flv.db import get_conn

    t0 = time.time()
    conn = get_conn()

    # Ensure the macro table exists even if schema hasn't been re-applied yet.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS flv_macro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series TEXT NOT NULL,
            obs_date TEXT NOT NULL,
            value REAL NOT NULL,
            source TEXT NOT NULL DEFAULT 'BCB',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(series, obs_date)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_macro_series_date ON flv_macro(series, obs_date)")
    conn.commit()

    bcb_rows = fetch_bcb(conn)
    diesel_rows = fetch_diesel_anp(conn)

    total = bcb_rows + diesel_rows
    elapsed = time.time() - t0
    print(f"[FLV-Macro] {total} linhas (BCB={bcb_rows}, diesel={diesel_rows}) em {elapsed:.1f}s")
    return total


def latest_by_date(conn, series, obs_date):
    """Return the most recent `value` for `series` <= `obs_date`, or None."""
    row = conn.execute(
        "SELECT value FROM flv_macro WHERE series=? AND obs_date<=? ORDER BY obs_date DESC LIMIT 1",
        (series, obs_date),
    ).fetchone()
    return row["value"] if row else None


def series_as_map(conn, series, min_date=None):
    """Return {obs_date: value} for a given series, optionally filtered by min_date."""
    if min_date:
        rows = conn.execute(
            "SELECT obs_date, value FROM flv_macro WHERE series=? AND obs_date>=? ORDER BY obs_date",
            (series, min_date),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT obs_date, value FROM flv_macro WHERE series=? ORDER BY obs_date",
            (series,),
        ).fetchall()
    return {r["obs_date"]: r["value"] for r in rows}


if __name__ == "__main__":
    fetch_all()
