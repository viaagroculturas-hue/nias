"""
NIAS — Persistência de clima sul-americano no banco SQLite.
Integra openmeteo_batch_sa com flv_climate e nias_regions.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# ETAPA 2 — Seed dos polos sul-americanos em nias_regions
# ═══════════════════════════════════════════════════════════════════════════

def seed_nias_regions(conn: sqlite3.Connection) -> int:
    """
    Insere/atualiza os 44 polos sul-americanos em nias_regions.
    Usa UPSERT (INSERT OR REPLACE) para ser idempotente.
    Não remove polos existentes.
    Retorna o número de polos processados.
    """
    from flv.south_america_regions import SOUTH_AMERICA_REGIONS

    now = datetime.now().isoformat()
    count = 0
    for r in SOUTH_AMERICA_REGIONS:
        products_json = json.dumps(r.get("products", []), ensure_ascii=False)
        conn.execute("""
            INSERT OR REPLACE INTO nias_regions
              (id, scope, country, country_code, region, state_or_department,
               city, lat, lon, products, importance, notes, source, active, updated_at)
            VALUES (?, 'south_america', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NIAS', 1, ?)
        """, (
            r["id"],
            r["country"],
            r["country_code"],
            r["region"],
            r.get("state_or_department"),
            r.get("city"),
            r["lat"],
            r["lon"],
            products_json,
            r.get("importance"),
            r.get("notes"),
            now,
        ))
        count += 1

    conn.commit()
    logger.info("[SA-Regions] %d polos upsertados em nias_regions", count)
    return count


def get_nias_regions(conn: sqlite3.Connection, country_code: Optional[str] = None) -> list:
    """Retorna polos ativos. Filtro opcional por país."""
    if country_code:
        rows = conn.execute(
            "SELECT * FROM nias_regions WHERE active=1 AND country_code=? ORDER BY country_code, region",
            (country_code.upper(),)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM nias_regions WHERE active=1 ORDER BY country_code, region"
        ).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════
# ETAPA 5 — Persistência do clima SA em flv_climate
# ═══════════════════════════════════════════════════════════════════════════

def persist_south_america_weather(conn: sqlite3.Connection, weather_result: dict) -> int:
    """
    Salva dados climáticos sul-americanos em flv_climate.
    Usa delete+insert por chave lógica: (scope, country_code, region_id, obs_date, source).
    Não apaga registros brasileiros existentes (mun_id based).
    Retorna o número de registros inseridos.
    """
    results = weather_result.get("results", [])
    if not results:
        logger.warning("[SA-Weather] Nenhum resultado para persistir")
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    source = "Open-Meteo"
    inserted = 0

    for point in results:
        country_code = point.get("country_code", "??")
        region_id    = point.get("id", "")
        region_name  = point.get("region", "")
        lat          = point.get("lat")
        lon          = point.get("lon")
        current      = point.get("current", {})

        temp_max = None
        temp_min = None
        precip   = None
        wind_ms  = None
        humidity = None

        # Preferir dados daily (mais precisos para o dia)
        forecast = point.get("forecast_7d", {})
        dates    = forecast.get("dates", [])
        if dates and today in dates:
            idx = dates.index(today)
            temps_max = forecast.get("temp_max", [])
            temps_min = forecast.get("temp_min", [])
            precips   = forecast.get("precip_mm", [])
            winds     = forecast.get("wind_max_kmh", [])
            temp_max  = temps_max[idx] if idx < len(temps_max) else None
            temp_min  = temps_min[idx] if idx < len(temps_min) else None
            precip    = precips[idx]   if idx < len(precips)   else None
            wind_ms   = (winds[idx] / 3.6) if (idx < len(winds) and winds[idx] is not None) else None
        else:
            # Fallback para current
            temp_c   = current.get("temperature_c")
            temp_max = temp_c
            temp_min = temp_c

        humidity = current.get("humidity_pct")
        if wind_ms is None:
            wind_kmh = current.get("wind_kmh")
            wind_ms  = (wind_kmh / 3.6) if wind_kmh is not None else None
        if precip is None:
            precip = current.get("precip_mm", 0.0)

        # Remover registro anterior para mesma chave lógica (idempotência)
        conn.execute("""
            DELETE FROM flv_climate
            WHERE scope='south_america'
              AND country_code=?
              AND region_id=?
              AND obs_date=?
              AND source=?
        """, (country_code, region_id, today, source))

        # Inserir novo registro
        conn.execute("""
            INSERT INTO flv_climate
              (mun_id, obs_date, temp_max_c, temp_min_c, precip_mm,
               humidity_pct, wind_ms, source, is_synthetic, data_quality,
               scope, country_code, region_id, region_name, lat, lon)
            VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, 0, 'real',
                    'south_america', ?, ?, ?, ?, ?)
        """, (
            today, temp_max, temp_min, precip,
            humidity, wind_ms, source,
            country_code, region_id, region_name, lat, lon,
        ))
        inserted += 1

    conn.commit()
    logger.info("[SA-Weather] %d registros inseridos em flv_climate", inserted)
    return inserted


# ═══════════════════════════════════════════════════════════════════════════
# ETAPA 4 — Ciclo integrado: fetch → persist → log
# ═══════════════════════════════════════════════════════════════════════════

def run_south_america_weather_cycle(conn: sqlite3.Connection, force: bool = False) -> dict:
    """
    Ciclo completo:
      1. Busca clima em batch para todos os polos SA (Open-Meteo)
      2. Respeita cache de 60 min e rate limit 429
      3. Persiste em flv_climate
      4. Retorna resultado estruturado com logs

    Args:
        conn: conexão SQLite já aberta
        force: ignorar cache e forçar nova busca
    """
    from flv.openmeteo_batch_sa import fetch_south_america_weather, get_cache_status
    from flv.scheduler import _log as sched_log

    cache_status = get_cache_status()

    # Garantir que os polos estão no banco antes de coletar clima
    try:
        existing = conn.execute("SELECT COUNT(*) FROM nias_regions WHERE active=1").fetchone()[0]
        if existing < 40:
            seeded = seed_nias_regions(conn)
            sched_log(f"[OpenMeteo-SA] Seed polos: {seeded} upsertados em nias_regions")
        else:
            sched_log(f"[OpenMeteo-SA] Polos já no banco: {existing} ativos")
    except Exception as e:
        sched_log(f"[OpenMeteo-SA] WARN seed_nias_regions: {e}")

    # Verificar rate limit antes de tentar
    if cache_status.get("rate_limited") and not force:
        until = cache_status.get("rate_limited_until", "?")
        sched_log(f"[OpenMeteo-SA] RATE_LIMIT ativo até {until} — skip")
        return {
            "status": "rate_limited",
            "rate_limited_until": until,
            "inserted": 0,
            "source": "Open-Meteo",
            "scope": "south_america",
        }

    # Verificar cache válido
    if cache_status.get("cache_valid") and not force:
        sched_log(f"[OpenMeteo-SA] CACHE_HIT age<60min — skip fetch, verificando persistência")
        # Se tiver cache válido mas não há dados no banco de hoje, persistir do cache
        from flv.openmeteo_batch_sa import _cache as _om_cache
        if _om_cache and _om_cache.get("results"):
            today = datetime.now().strftime("%Y-%m-%d")
            count_today = conn.execute(
                "SELECT COUNT(*) FROM flv_climate WHERE scope='south_america' AND obs_date=?",
                (today,)
            ).fetchone()[0]
            if count_today == 0:
                inserted = persist_south_america_weather(conn, _om_cache)
                sched_log(f"[OpenMeteo-SA] CACHE → DB: {inserted} inseridos para {today}")
                return {"status": "cached_persisted", "inserted": inserted, "scope": "south_america"}
        return {"status": "cached", "inserted": 0, "scope": "south_america"}

    # Número de pontos
    from flv.south_america_regions import get_weather_points
    points = get_weather_points()
    sched_log(f"[OpenMeteo-SA] START points={len(points)}")

    # Buscar dados
    weather_result = fetch_south_america_weather(points=points, force=force)
    status = weather_result.get("status", "error")

    if status == "rate_limited":
        until = weather_result.get("rate_limited_until", "?")
        sched_log(f"[OpenMeteo-SA] RATE_LIMIT http=429 retry_after={until}")
        return {
            "status": "rate_limited",
            "rate_limited_until": until,
            "inserted": 0,
            "source": "Open-Meteo",
            "scope": "south_america",
        }

    if status == "error":
        msg = weather_result.get("message", "Erro desconhecido")
        sched_log(f"[OpenMeteo-SA] ERROR message={msg}")
        return {
            "status": "error",
            "message": msg,
            "inserted": 0,
            "scope": "south_america",
        }

    # Persistir
    try:
        inserted = persist_south_america_weather(conn, weather_result)
        fetched_at = weather_result.get("fetched_at", datetime.now().isoformat())
        sched_log(f"[OpenMeteo-SA] SUCCESS inserted={inserted} fetched_at={fetched_at}")
        return {
            "status": "success",
            "inserted": inserted,
            "total_points": weather_result.get("total_points", len(points)),
            "source": "Open-Meteo",
            "scope": "south_america",
            "fetched_at": fetched_at,
        }
    except Exception as e:
        sched_log(f"[OpenMeteo-SA] ERROR persist: {e}")
        return {
            "status": "error",
            "message": f"Persist error: {e}",
            "inserted": 0,
            "scope": "south_america",
        }


# ═══════════════════════════════════════════════════════════════════════════
# Query helpers para os endpoints
# ═══════════════════════════════════════════════════════════════════════════

def _ensure_sa_columns(conn: sqlite3.Connection) -> bool:
    """
    Garante que flv_climate tem colunas SA. Retorna True se pronto.
    Usa ensure_runtime_schema para migração segura.
    """
    try:
        from flv.db_migration import ensure_runtime_schema
        ensure_runtime_schema(conn)
        return True
    except Exception as e:
        logger.warning("[SA-Weather] Não foi possível migrar schema: %s", e)
        return False


def get_latest_sa_weather(conn: sqlite3.Connection, country_code: Optional[str] = None) -> list:
    """
    Retorna os dados climáticos SA mais recentes do banco.
    Filtra por country_code se fornecido.
    Retorna [] se as colunas SA ainda não existem no banco.
    """
    _ensure_sa_columns(conn)
    try:
        if country_code:
            rows = conn.execute("""
                SELECT obs_date, country_code, region_id, region_name, lat, lon,
                       temp_max_c, temp_min_c, precip_mm, humidity_pct, wind_ms,
                       source, data_quality, scope
                FROM flv_climate
                WHERE scope='south_america' AND country_code=?
                  AND obs_date = (
                    SELECT MAX(obs_date) FROM flv_climate
                    WHERE scope='south_america' AND country_code=?
                  )
                ORDER BY region_name
            """, (country_code.upper(), country_code.upper())).fetchall()
        else:
            rows = conn.execute("""
                SELECT obs_date, country_code, region_id, region_name, lat, lon,
                       temp_max_c, temp_min_c, precip_mm, humidity_pct, wind_ms,
                       source, data_quality, scope
                FROM flv_climate
                WHERE scope='south_america'
                  AND obs_date = (
                    SELECT MAX(obs_date) FROM flv_climate WHERE scope='south_america'
                  )
                ORDER BY country_code, region_name
            """).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError as e:
        logger.warning("[SA-Weather] Query falhou (schema incompleto?): %s", e)
        return []


def get_sa_weather_summary(conn: sqlite3.Connection) -> dict:
    """Resumo do clima SA no banco (para health/status)."""
    _ensure_sa_columns(conn)
    try:
        row = conn.execute("""
            SELECT COUNT(*) as total, MAX(obs_date) as latest_date,
                   COUNT(DISTINCT country_code) as countries
            FROM flv_climate WHERE scope='south_america'
        """).fetchone()
        return {
            "total_records": row["total"] if row else 0,
            "latest_date":   row["latest_date"] if row else None,
            "countries":     row["countries"] if row else 0,
            "scope":         "south_america",
        }
    except sqlite3.OperationalError:
        return {"total_records": 0, "latest_date": None, "countries": 0, "scope": "south_america"}
