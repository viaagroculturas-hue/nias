"""CEASA/CONAB PROHORT price API for NIAS.

This module never fabricates prices. It returns only values collected from
public official/reference sources and marks unavailable states explicitly.
Primary source: CONAB/PROHORT public portal files or Pentaho generated content.
Secondary source: local consolidated CEASA database already bundled with NIAS.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

CACHE_TTL_SECONDS = int(os.getenv("CEASA_PRICE_CACHE_TTL", "1800"))
_CACHE: Dict[str, Any] = {"ts": 0, "payload": None}

UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]

UF_NAMES = {
    "AC":"Acre", "AL":"Alagoas", "AP":"Amapá", "AM":"Amazonas", "BA":"Bahia", "CE":"Ceará",
    "DF":"Distrito Federal", "ES":"Espírito Santo", "GO":"Goiás", "MA":"Maranhão", "MT":"Mato Grosso",
    "MS":"Mato Grosso do Sul", "MG":"Minas Gerais", "PA":"Pará", "PB":"Paraíba", "PR":"Paraná",
    "PE":"Pernambuco", "PI":"Piauí", "RJ":"Rio de Janeiro", "RN":"Rio Grande do Norte",
    "RS":"Rio Grande do Sul", "RO":"Rondônia", "RR":"Roraima", "SC":"Santa Catarina", "SP":"São Paulo",
    "SE":"Sergipe", "TO":"Tocantins",
}

PROHORT_DOWNLOAD_CANDIDATES = [
    "https://portaldeinformacoes.conab.gov.br/downloads/arquivos/PrecosSemanalUF.txt",
    "https://portaldeinformacoes.conab.gov.br/downloads/arquivos/ProhortDiario.txt",
]

PROHORT_DAILY_HTML = (
    "https://pentahoportaldeinformacoes.conab.gov.br/pentaho/api/repos/"
    "%3Ahome%3APROHORT%3AprecoDia.wcdf/generatedContent?password=password&userid=pentaho"
)

HEADERS = {
    "User-Agent": "NIAS/1.0 (+https://render.com) Python urllib official data collector",
    "Accept": "text/plain,text/csv,text/html,application/json,*/*",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _parse_decimal(value: Any) -> Optional[float]:
    text = _normalize_text(value)
    if not text or text in {"-", "—", "n/d", "ND"}:
        return None
    text = re.sub(r"[^0-9,.-]", "", text)
    if not text:
        return None
    # Brazilian format: 1.234,56 -> 1234.56
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        val = float(text)
        if val <= 0:
            return None
        return round(val, 4)
    except ValueError:
        return None


def _guess_uf(*parts: str) -> str:
    joined = " ".join(parts).upper()
    for uf in UFS:
        if re.search(rf"\b{uf}\b", joined):
            return uf
    # common CEASA names without UF code
    aliases = {
        "CEAGESP": "SP", "SÃO PAULO": "SP", "SAO PAULO": "SP", "CONTAGEM": "MG",
        "BELO HORIZONTE": "MG", "CURITIBA": "PR", "MARINGÁ": "PR", "MARINGA": "PR",
        "RECIFE": "PE", "IRAJA": "RJ", "IRAJÁ": "RJ", "VITÓRIA": "ES", "VITORIA": "ES",
        "GOIÂNIA": "GO", "GOIANIA": "GO", "SALVADOR": "BA", "FORTALEZA": "CE",
        "MARACANAÚ": "CE", "MARACANAU": "CE", "JOÃO PESSOA": "PB", "JOAO PESSOA": "PB",
        "PALMAS": "TO", "TERESINA": "PI", "ARACAJU": "SE", "NATAL": "RN",
        "CUIABÁ": "MT", "CUIABA": "MT", "CAMPO GRANDE": "MS", "PORTO ALEGRE": "RS",
        "GRAVATAÍ": "RS", "GRAVATAI": "RS", "FLORIANÓPOLIS": "SC", "FLORIANOPOLIS": "SC",
        "SÃO JOSÉ": "SC", "SAO JOSE": "SC", "BELÉM": "PA", "BELEM": "PA",
        "MANAUS": "AM", "PORTO VELHO": "RO", "RIO BRANCO": "AC", "MACAPÁ": "AP", "MACAPA": "AP",
        "BOA VISTA": "RR", "SÃO LUÍS": "MA", "SAO LUIS": "MA", "MACEIÓ": "AL", "MACEIO": "AL",
    }
    for key, uf in aliases.items():
        if key in joined:
            return uf
    return ""


def _fetch_url(url: str, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "latin-1"
        return raw.decode(charset, errors="ignore")


def _detect_delimiter(sample: str) -> str:
    for delim in [";", "\t", ",", "|"]:
        if sample.count(delim) >= 3:
            return delim
    return ";"


def _parse_prohort_text(raw: str, source_url: str, limit: int = 20000) -> List[Dict[str, Any]]:
    if not raw.strip():
        return []
    lines = raw.splitlines()
    if not lines:
        return []
    delim = _detect_delimiter(lines[0])
    reader = csv.reader(lines, delimiter=delim)
    rows = list(reader)
    if not rows:
        return []

    header = [_normalize_text(h).lower() for h in rows[0]]
    records: List[Dict[str, Any]] = []

    # Use header-based parsing when possible.
    def find_col(candidates: Iterable[str]) -> Optional[int]:
        for cand in candidates:
            for i, h in enumerate(header):
                if cand in h:
                    return i
        return None

    product_i = find_col(["produto", "mercadoria"])
    ceasa_i = find_col(["ceasa", "entreposto", "mercado"])
    uf_i = find_col([" uf", "uf", "estado"])
    date_i = find_col(["data", "semana"])
    price_i = find_col(["valor", "preco", "preço", "cotacao", "cotação"])
    unit_i = find_col(["unidade", "embalagem", "kg"])

    # Fallback for known CONAB PrecosSemanalUF layout referenced in legacy code:
    # produto;classificacao;id;uf;regiao;ano;mes;data_semana;semana;nivel;valor
    if product_i is None and len(rows[0]) >= 11:
        product_i, uf_i, date_i, price_i = 0, 3, 7, 10

    # Fallback for ProhortDiario variants.
    if product_i is None and len(rows[0]) >= 8:
        ceasa_i, product_i, date_i, price_i = 3, 4, 6, 7

    if product_i is None or price_i is None:
        return []

    # Process last rows first for large daily files, then deduplicate.
    data_rows = rows[1:]
    if len(data_rows) > limit:
        data_rows = data_rows[-limit:]

    seen = set()
    for cols in data_rows:
        if len(cols) <= max(product_i, price_i):
            continue
        product = _normalize_text(cols[product_i])
        price = _parse_decimal(cols[price_i])
        if not product or price is None:
            continue
        ceasa = _normalize_text(cols[ceasa_i]) if ceasa_i is not None and len(cols) > ceasa_i else ""
        uf = _normalize_text(cols[uf_i]).upper() if uf_i is not None and len(cols) > uf_i else ""
        if uf not in UFS:
            uf = _guess_uf(uf, ceasa)
        date = _normalize_text(cols[date_i]) if date_i is not None and len(cols) > date_i else ""
        unit = _normalize_text(cols[unit_i]) if unit_i is not None and len(cols) > unit_i else "R$/unidade informada pela fonte"
        key = (uf, ceasa, product.upper(), date, price)
        if key in seen:
            continue
        seen.add(key)
        records.append({
            "uf": uf,
            "state": UF_NAMES.get(uf, uf or "não identificado"),
            "ceasa": ceasa or (f"CEASA-{uf}" if uf else "não identificado"),
            "product": product,
            "classification": "",
            "price": price,
            "unit": unit or "R$/unidade informada pela fonte",
            "date": date,
            "source": "CONAB/PROHORT",
            "source_url": source_url,
            "quality": "official_collected",
            "is_real_price": True,
        })
    return records


def _parse_prohort_html(raw: str) -> List[Dict[str, Any]]:
    # Conservative parser: only table rows with at least product/ceasa/price-like values.
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", raw, flags=re.I | re.S)
    parsed: List[Dict[str, Any]] = []
    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.I | re.S)
        cells = [re.sub(r"<[^>]+>", " ", c).strip() for c in cells]
        cells = [re.sub(r"\s+", " ", c) for c in cells if c.strip()]
        if len(cells) < 3:
            continue
        joined = " ".join(cells)
        price = None
        for c in reversed(cells):
            price = _parse_decimal(c)
            if price is not None:
                break
        if price is None:
            continue
        uf = _guess_uf(joined)
        product = cells[0]
        ceasa = next((c for c in cells if "CEASA" in c.upper() or "CEAGESP" in c.upper()), "")
        parsed.append({
            "uf": uf,
            "state": UF_NAMES.get(uf, uf or "não identificado"),
            "ceasa": ceasa or (f"CEASA-{uf}" if uf else "não identificado"),
            "product": product,
            "classification": "",
            "price": price,
            "unit": "R$/unidade informada pela fonte",
            "date": "",
            "source": "CONAB/PROHORT Preços Diários",
            "source_url": PROHORT_DAILY_HTML,
            "quality": "official_collected",
            "is_real_price": True,
        })
    return parsed


def _load_local_ceasa_db(base_dir: str) -> List[Dict[str, Any]]:
    candidates = [
        os.path.join(base_dir, "data", "ceasa", "ceasa.db"),
        os.path.join(base_dir, "data", "nia_flv.db"),
        os.path.join(base_dir, "nia_flv.db"),
    ]
    out: List[Dict[str, Any]] = []
    for db_path in candidates:
        if not os.path.exists(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "cotacoes" in tables:
                rows = cur.execute("SELECT * FROM cotacoes ORDER BY data_coleta DESC LIMIT 5000").fetchall()
                for row in rows:
                    d = dict(row)
                    product = d.get("produto") or d.get("product") or ""
                    price = _parse_decimal(d.get("preco") or d.get("price") or d.get("valor"))
                    if not product or price is None:
                        continue
                    origem = d.get("origem") or d.get("ceasa") or d.get("source") or ""
                    uf = _guess_uf(origem, d.get("estado") or d.get("uf") or "")
                    out.append({
                        "uf": uf,
                        "state": UF_NAMES.get(uf, uf or "não identificado"),
                        "ceasa": origem or (f"CEASA-{uf}" if uf else "não identificado"),
                        "product": product,
                        "classification": d.get("classificacao") or "",
                        "price": price,
                        "unit": d.get("unidade") or "R$/unidade local",
                        "date": d.get("data_coleta") or d.get("data") or "",
                        "source": "Base local NIAS/CEASA",
                        "source_url": db_path,
                        "quality": "local_cache_verify_source",
                        "is_real_price": True,
                    })

            # Banco principal do NIAS: preços CEASA normalizados.
            # Regra de verdade: somente linhas não sintéticas entram como preço exibível.
            if "flv_ceasa_prices" in tables and "flv_cultures" in tables:
                rows = cur.execute(
                    """
                    SELECT p.terminal, p.price_date, p.price_avg, p.price_min, p.price_max,
                           p.source, p.data_quality, p.is_synthetic,
                           c.name_pt, c.conab_key, c.unit
                    FROM flv_ceasa_prices p
                    JOIN flv_cultures c ON c.id = p.culture_id
                    WHERE COALESCE(p.is_synthetic,0)=0
                      AND p.price_avg IS NOT NULL
                      AND p.price_avg > 0
                    ORDER BY date(p.price_date) DESC, p.id DESC
                    LIMIT 8000
                    """
                ).fetchall()
                for row in rows:
                    d = dict(row)
                    terminal = d.get("terminal") or ""
                    uf = _guess_uf(terminal, d.get("source") or "")
                    product = d.get("name_pt") or d.get("conab_key") or ""
                    price = _parse_decimal(d.get("price_avg"))
                    if not product or price is None:
                        continue
                    out.append({
                        "uf": uf,
                        "state": UF_NAMES.get(uf, uf or "não identificado"),
                        "ceasa": terminal or (f"CEASA-{uf}" if uf else "não identificado"),
                        "product": product,
                        "classification": d.get("conab_key") or "",
                        "price": price,
                        "unit": d.get("unit") or "R$/kg",
                        "date": d.get("price_date") or "",
                        "source": d.get("source") or "CONAB/PROHORT",
                        "source_url": db_path,
                        "quality": "official_local_db",
                        "is_real_price": True,
                    })
            conn.close()
        except Exception:
            continue
    return out


def _dedupe_latest(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for r in records:
        key = (
            _normalize_text(r.get("uf")),
            _normalize_text(r.get("ceasa")).upper(),
            _normalize_text(r.get("product")).upper(),
            _normalize_text(r.get("classification")).upper(),
        )
        old = best.get(key)
        if old is None or _normalize_text(r.get("date")) >= _normalize_text(old.get("date")):
            best[key] = r
    return sorted(best.values(), key=lambda x: (_normalize_text(x.get("uf")), _normalize_text(x.get("product"))))


def build_ceasa_price_payload(base_dir: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
    if not force_refresh and _CACHE.get("payload") and time.time() - _CACHE.get("ts", 0) < CACHE_TTL_SECONDS:
        return _CACHE["payload"]

    base_dir = base_dir or os.getcwd()
    records: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    # Carregamento rápido e confiável: primeiro usa o banco versionado em /data.
    # Coleta online pesada da CONAB só roda com refresh=1, para não congelar a aba Mercado.
    records.extend(_load_local_ceasa_db(base_dir))

    if force_refresh or not records:
        for url in PROHORT_DOWNLOAD_CANDIDATES:
            try:
                raw = _fetch_url(url, timeout=18)
                parsed = _parse_prohort_text(raw, url)
                records.extend(parsed)
                if parsed:
                    break
            except Exception as exc:
                errors.append({"source": url, "error": str(exc)[:240]})

        if not records:
            try:
                raw = _fetch_url(PROHORT_DAILY_HTML, timeout=12)
                records.extend(_parse_prohort_html(raw))
            except Exception as exc:
                errors.append({"source": PROHORT_DAILY_HTML, "error": str(exc)[:240]})
    records = _dedupe_latest(records)

    by_uf: Dict[str, Dict[str, Any]] = {}
    for uf in UFS:
        uf_rows = [r for r in records if r.get("uf") == uf]
        prices = [r["price"] for r in uf_rows if isinstance(r.get("price"), (int, float))]
        by_uf[uf] = {
            "uf": uf,
            "state": UF_NAMES[uf],
            "records": len(uf_rows),
            "products": len({_normalize_text(r.get("product")).upper() for r in uf_rows}),
            "ceasas": sorted({_normalize_text(r.get("ceasa")) for r in uf_rows if _normalize_text(r.get("ceasa"))}),
            "avg_price": round(sum(prices) / len(prices), 2) if prices else None,
            "min_price": round(min(prices), 2) if prices else None,
            "max_price": round(max(prices), 2) if prices else None,
            "status": "coletado" if uf_rows else "sem_dado_oficial_disponivel_no_coletor",
        }

    payload = {
        "ok": bool(records),
        "generated_at": _now_iso(),
        "meta": {
            "total_records": len(records),
            "states_with_prices": sum(1 for uf in UFS if by_uf[uf]["records"] > 0),
            "states_total": len(UFS),
            "cache_ttl_seconds": CACHE_TTL_SECONDS,
            "truth_policy": "O NIAS só exibe preço quando a coleta retorna fonte oficial/referencial. Estados sem coleta ficam marcados como sem dado, não recebem preço estimado.",
        },
        "sources": [
            {"name": "CONAB/PROHORT", "url": "https://portaldeinformacoes.conab.gov.br/mercado-atacadista-hortigranjeiro.html", "type": "oficial/referencial"},
            {"name": "CONAB PROHORT Preços Diários", "url": PROHORT_DAILY_HTML, "type": "oficial/referencial"},
            {"name": "CEAGESP Cotações", "url": "https://ceagesp.gov.br/cotacoes/", "type": "oficial/referencial estadual"},
            {"name": "CEASA estaduais", "url": "portais estaduais", "type": "oficial estadual; exige conector por UF quando fora do PROHORT"},
        ],
        "coverage": by_uf,
        "records": records,
        "errors": errors,
    }
    _CACHE["payload"] = payload
    _CACHE["ts"] = time.time()
    return payload


def filter_payload(payload: Dict[str, Any], query: Dict[str, List[str]]) -> Dict[str, Any]:
    uf = (query.get("uf") or [""])[0].upper()
    product = (query.get("product") or query.get("produto") or [""])[0].lower().strip()
    ceasa = (query.get("ceasa") or [""])[0].lower().strip()
    limit = int((query.get("limit") or ["1000"])[0] or 1000)
    records = payload.get("records", [])
    if uf:
        records = [r for r in records if r.get("uf") == uf]
    if product:
        records = [r for r in records if product in _normalize_text(r.get("product")).lower()]
    if ceasa:
        records = [r for r in records if ceasa in _normalize_text(r.get("ceasa")).lower()]
    out = dict(payload)
    out["records"] = records[:max(1, min(limit, 5000))]
    out["meta"] = dict(payload.get("meta", {}), filtered_records=len(records[:max(1, min(limit, 5000))]))
    return out
