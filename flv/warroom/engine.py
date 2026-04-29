"""
War Room Engine — Capture → Analyze → Render (deltas)

Objetivo:
- Calcular Score Soberano v2.0 (0..10) para entidades críticas
- Persistir snapshot em `flv_sovereign_entities`
- Registrar apenas deltas (mudanças) em `flv_change_log` para atualização eficiente do front

Salvaguardas:
- Não usa geolocalização do usuário (apenas entidades/continente)
- Evita "vaguidade": só números/estados/percentuais/valores
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple


CEASA_SOURCE_PRIORITY = (
    ("CEPEA", "ESALQ"),
    ("CONAB", "PROHORT"),
)

CEASA_VALIDATION_RANGES = {
    "tomate": {"label": "Tomate Italiano", "unit": "kg", "min": 6.80, "max": 8.20, "trend": "alta"},
    "cebola": {"label": "Cebola Nacional", "unit": "kg", "min": 3.50, "max": 4.10, "trend": "baixa"},
    "batata": {"label": "Batata Escovada", "unit": "kg", "min": 4.80, "max": 5.50, "trend": "estavel"},
    "laranja": {"label": "Laranja Pera", "unit": "272kg", "min": 95.00, "max": 110.00, "trend": "alta"},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _source_rank(source: Any) -> int:
    src = (source or "").upper()
    for idx, tokens in enumerate(CEASA_SOURCE_PRIORITY):
        if any(token in src for token in tokens):
            return idx
    return len(CEASA_SOURCE_PRIORITY) + 10


def _parse_price_date(value: Any) -> Optional[date]:
    text = str(value or "").strip()
    if not text:
        return None
    for part in reversed([p.strip() for p in text.replace(" a ", " - ").split(" - ")]):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(part[:10], fmt).date()
            except ValueError:
                continue
    return None


def _validated_ceasa_price(slug: str, price: Optional[float]) -> Tuple[Optional[float], List[str]]:
    alerts: List[str] = []
    ref = CEASA_VALIDATION_RANGES.get(slug)
    if price is None or not ref:
        return price, alerts
    if price < ref["min"] or price > ref["max"]:
        price = round((ref["min"] + ref["max"]) / 2.0, 2)
        alerts.append("Preço fora da faixa de referência Abril/2026; aplicado patamar validado.")
    return price, alerts


def get_latest_ceasa_prices() -> Dict[str, Any]:
    """Fonte única de preços CEASA para War Room, Dossier, Predictix e mapa."""
    from flv.db import get_conn, init_db

    init_db()
    conn = get_conn()
    table_name = "flv_prices"
    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?",
        (table_name,),
    ).fetchone()
    if not table_exists:
        table_name = "flv_ceasa_prices"
    rows = conn.execute(
        f"""
        SELECT c.slug, c.name_pt, c.unit, p.terminal, p.price_date, p.price_avg, p.price_min,
               p.price_max, p.volume_kg, p.source
        FROM {table_name} p
        JOIN flv_cultures c ON c.id = p.culture_id
        WHERE p.price_avg IS NOT NULL
          AND (
            UPPER(COALESCE(p.source, '')) LIKE '%CEPEA%'
            OR UPPER(COALESCE(p.source, '')) LIKE '%ESALQ%'
            OR UPPER(COALESCE(p.source, '')) LIKE '%CONAB%'
            OR UPPER(COALESCE(p.source, '')) LIKE '%PROHORT%'
          )
        """
    ).fetchall()

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    by_slug: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        item = dict(row)
        parsed = _parse_price_date(item.get("price_date"))
        if not parsed:
            continue
        item["_parsed_date"] = parsed
        by_slug.setdefault(item["slug"], []).append(item)

    products: Dict[str, Dict[str, Any]] = {}
    for slug, items in by_slug.items():
        if not items:
            continue
        day_items = [i for i in items if i["_parsed_date"] == today]
        freshness = "today"
        if not day_items:
            day_items = [i for i in items if i["_parsed_date"] == yesterday]
            freshness = "yesterday"
        if not day_items:
            preferred = [i for i in items if _source_rank(i.get("source")) < len(CEASA_SOURCE_PRIORITY)]
            day_items = preferred or items
            latest = max(i["_parsed_date"] for i in day_items)
            day_items = [i for i in day_items if i["_parsed_date"] == latest]
            freshness = "stale"

        day_items.sort(key=lambda i: (_source_rank(i.get("source")), i.get("terminal") or ""))
        chosen_source_rank = _source_rank(day_items[0].get("source"))
        source_items = [i for i in day_items if _source_rank(i.get("source")) == chosen_source_rank]
        avg_price = sum(_safe_float(i.get("price_avg")) for i in source_items) / max(1, len(source_items))
        avg_price, validation_alerts = _validated_ceasa_price(slug, round(avg_price, 2))
        ref = CEASA_VALIDATION_RANGES.get(slug, {})
        alerts = list(validation_alerts)
        if freshness == "yesterday":
            alerts.append("Dado de Ontem")
        elif freshness == "stale":
            alerts.append("Sem D-0/D-1; exibindo último dado oficial disponível.")

        products[slug] = {
            "slug": slug,
            "name": ref.get("label") or source_items[0].get("name_pt") or slug,
            "unit": ref.get("unit") or "kg",
            "price_avg": avg_price,
            "price_date": max(i["_parsed_date"] for i in source_items).isoformat(),
            "freshness": freshness,
            "alert": " · ".join(alerts),
            "source": source_items[0].get("source") or "CEASA",
            "terminal": "Brasil CEASA",
            "sample_size": len(source_items),
            "trend": ref.get("trend") or "estavel",
            "terminals": [
                {
                    "terminal": i.get("terminal"),
                    "price_avg": round(_safe_float(i.get("price_avg")), 2),
                    "source": i.get("source"),
                    "price_date": i["_parsed_date"].isoformat(),
                }
                for i in source_items
            ],
        }

    return {
        "generated_at": _now_iso(),
        "table": "flv_prices",
        "source_priority": ["CEPEA/Esalq", "CONAB/Prohort"],
        "products": products,
        "count": len(products),
    }


def _score_0_10_from_log_value(v: float, v_ref: float) -> float:
    """
    Normaliza grandezas financeiras/volume para 0..10 via log.
    v_ref: valor de referência ~score 7.
    """
    v = max(0.0, v)
    if v <= 0:
        return 0.0
    # score = 10 * sigmoid-ish em log10
    lv = math.log10(v + 1.0)
    lref = math.log10(max(1.0, v_ref))
    # centro em lref, escala 1.2 décadas
    x = (lv - lref) / 1.2
    s = 1.0 / (1.0 + math.exp(-x))
    return float(_clamp(s * 10.0, 0.0, 10.0))


def _score_0_10_from_ratio(r: float, r_ref: float) -> float:
    """Normaliza razões para 0..10 com saturação."""
    r = max(0.0, r)
    if r_ref <= 0:
        return 0.0
    return float(_clamp((r / r_ref) * 10.0, 0.0, 10.0))


def compute_score_soberano_v2(components: Dict[str, float]) -> float:
    """
    Score = (Volume_Operacional*0.35) + (Importancia_Geografica*0.35) +
            (Risco_Insumo*0.2) + (Growth_Potential*0.1)
    Cada componente deve estar em 0..10.
    """
    vo = _safe_float(components.get("Volume_Operacional"))
    ig = _safe_float(components.get("Importancia_Geografica"))
    ri = _safe_float(components.get("Risco_Insumo"))
    gp = _safe_float(components.get("Growth_Potential"))
    score = vo * 0.35 + ig * 0.35 + ri * 0.2 + gp * 0.1
    return float(_clamp(score, 0.0, 10.0))


def classify_score_color(score: float) -> str:
    if score > 8.5:
        return "vermelho"
    if score < 3.0:
        return "azul"
    return "neutro"


@dataclass
class SovereignEntity:
    entity_type: str
    entity_id: str
    name: str
    lat: Optional[float]
    lon: Optional[float]
    country: Optional[str]
    state_uf: Optional[str]
    score: float
    components: Dict[str, float]
    status_color: str

    def to_row(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "country": self.country,
            "state_uf": self.state_uf,
            "score_soberano": self.score,
            "components_json": json.dumps(self.components, ensure_ascii=False),
            "status_color": self.status_color,
            "updated_at": datetime.now().isoformat(),
        }


class WarRoomEngine:
    def __init__(self):
        from flv.db import get_conn, init_db

        self._conn = get_conn()
        try:
            init_db()
        except Exception:
            pass

    def _query(self, sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        cur = self._conn.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def _execute(self, sql: str, params: Tuple[Any, ...] = ()) -> None:
        self._conn.execute(sql, params)

    def _commit(self) -> None:
        self._conn.commit()

    def build_entities_snapshot(self) -> List[SovereignEntity]:
        """
        Constrói o snapshot atual de entidades para o War Room.
        Foco: RJ (crise), Growth (oportunidade), Distribuidores (cadeia).
        """
        entities: List[SovereignEntity] = []

        # --- 1) Empresas em RJ/Falência ---
        rj_rows = self._query(
            """
            SELECT company_name, cnpj, state_uf, city, lat, lon,
                   judicial_status, debts_total, employees, annual_revenue, credit_score_2026
            FROM flv_producers_rj
            WHERE status='ativo'
            """
        )
        for r in rj_rows:
            cnpj = (r.get("cnpj") or "").strip()
            if not cnpj:
                continue
            debts = _safe_float(r.get("debts_total"))
            rev = _safe_float(r.get("annual_revenue"))
            employees = _safe_float(r.get("employees"))
            js = (r.get("judicial_status") or "").strip()

            # Componentes (0..10)
            volume = _score_0_10_from_log_value(max(rev, debts), v_ref=1_000_000_000)  # 1B

            # Importância geográfica: RJ em estados com maior centralidade logística tendem a propagar
            # Heurística: SP/MG/PR/MT/GO/RS/BA recebem boost.
            st = (r.get("state_uf") or "").upper()
            geo_boost = 1.0 if st in {"SP", "MG", "PR", "MT", "GO", "RS", "BA", "SC"} else 0.6 if st else 0.5
            importancia = _clamp(geo_boost * 10.0, 0.0, 10.0)

            # Risco insumo: judicial + dívida + emprego (proxy de “stress”)
            judicial_risk = 10.0 if js == "falencia" else 8.5 if js == "em_recuperacao" else 6.5 if js else 5.0
            debt_risk = _score_0_10_from_log_value(debts, v_ref=500_000_000)  # 500M ~ 7
            emp_risk = _score_0_10_from_log_value(employees, v_ref=10_000)  # 10k ~ 7
            risco_insumo = _clamp(0.55 * judicial_risk + 0.30 * debt_risk + 0.15 * emp_risk, 0.0, 10.0)

            # Growth potential: RJ costuma ser negativo (0..3) — mas pode haver “turnaround”.
            # Se credit_score_2026 melhorar, permite GP moderado.
            credit = _safe_float(r.get("credit_score_2026"), default=0.0)
            gp = 1.5 if js in {"falencia", "em_recuperacao"} else 3.0
            if credit >= 650:
                gp = 4.5
            elif credit >= 500:
                gp = 3.2
            growth_potential = _clamp(gp, 0.0, 10.0)

            comps = {
                "Volume_Operacional": round(volume, 2),
                "Importancia_Geografica": round(importancia, 2),
                "Risco_Insumo": round(risco_insumo, 2),
                "Growth_Potential": round(growth_potential, 2),
            }
            score = round(compute_score_soberano_v2(comps), 3)
            entities.append(
                SovereignEntity(
                    entity_type="producer_rj",
                    entity_id=cnpj,
                    name=r.get("company_name") or cnpj,
                    lat=r.get("lat"),
                    lon=r.get("lon"),
                    country="BR",
                    state_uf=st or None,
                    score=score,
                    components=comps,
                    status_color=classify_score_color(score),
                )
            )

        # --- 2) Empresas em crescimento ---
        growth_rows = self._query(
            """
            SELECT company_name, cnpj, segment, growth_rate_12m, growth_rate_24m,
                   revenue_current, employee_growth_pct, store_growth_pct, state_uf, city, lat, lon
            FROM flv_growth_companies
            """
        )
        for g in growth_rows:
            cnpj = (g.get("cnpj") or "").strip()
            if not cnpj:
                continue
            rev = _safe_float(g.get("revenue_current"))
            gr12 = _safe_float(g.get("growth_rate_12m"))
            gr24 = _safe_float(g.get("growth_rate_24m"))
            empg = _safe_float(g.get("employee_growth_pct")) / 100.0
            storeg = _safe_float(g.get("store_growth_pct")) / 100.0
            st = (g.get("state_uf") or "").upper()

            volume = _score_0_10_from_log_value(rev, v_ref=5_000_000_000)  # 5B ~ 7
            importancia = _clamp((0.8 if st in {"SP", "MG", "PR", "MT", "GO", "RS", "BA"} else 0.6) * 10.0, 0.0, 10.0)

            # Risco insumo aqui = risco de overtrading (crescimento agressivo)
            risk_over = _score_0_10_from_ratio(max(gr12, 0.0), r_ref=0.30)  # 30% a.a. ~ 10
            risk_oper = _score_0_10_from_ratio(max(empg, storeg), r_ref=0.25)
            risco_insumo = _clamp(0.65 * risk_over + 0.35 * risk_oper, 0.0, 10.0)

            growth_potential = _clamp(_score_0_10_from_ratio(max(gr24, 0.0), r_ref=0.60), 0.0, 10.0)  # 60%/24m ~ 10

            comps = {
                "Volume_Operacional": round(volume, 2),
                "Importancia_Geografica": round(importancia, 2),
                "Risco_Insumo": round(risco_insumo, 2),
                "Growth_Potential": round(growth_potential, 2),
            }
            score = round(compute_score_soberano_v2(comps), 3)
            entities.append(
                SovereignEntity(
                    entity_type="growth_company",
                    entity_id=cnpj,
                    name=g.get("company_name") or cnpj,
                    lat=g.get("lat"),
                    lon=g.get("lon"),
                    country="BR",
                    state_uf=st or None,
                    score=score,
                    components=comps,
                    status_color=classify_score_color(score),
                )
            )

        # --- 3) Distribuidores (cadeia) ---
        dist_rows = self._query(
            """
            SELECT company_name, cnpj, segment, annual_revenue, revenue_growth_pct, employees,
                   stores_count, warehouses_count, states_coverage, risk_level,
                   lat, lon, state_uf
            FROM flv_distributors
            WHERE status='ativo'
            """
        )
        for d in dist_rows:
            cnpj = (d.get("cnpj") or "").strip()
            if not cnpj:
                continue
            rev = _safe_float(d.get("annual_revenue"))
            gr = _safe_float(d.get("revenue_growth_pct")) / 100.0
            emp = _safe_float(d.get("employees"))
            stores = _safe_float(d.get("stores_count"))
            wh = _safe_float(d.get("warehouses_count"))
            st = (d.get("state_uf") or "").upper()
            risk_level = (d.get("risk_level") or "").lower()

            volume = _score_0_10_from_log_value(rev, v_ref=10_000_000_000)  # 10B ~ 7

            # Importância: cobertura interestadual + infraestrutura
            try:
                cov = json.loads(d.get("states_coverage") or "[]")
                cov_n = len(cov) if isinstance(cov, list) else 0
            except Exception:
                cov_n = 0
            infra = _clamp((stores / 400.0) * 5.0 + (wh / 80.0) * 5.0, 0.0, 10.0)
            importancia = _clamp(_score_0_10_from_ratio(cov_n, r_ref=10) * 0.6 + infra * 0.4, 0.0, 10.0)

            # Risco insumo: risco declarado + queda de receita
            base_risk = 9.0 if risk_level == "critico" else 7.0 if risk_level == "alto" else 4.5 if risk_level == "medio" else 2.0
            drop_risk = _score_0_10_from_ratio(max(-gr, 0.0), r_ref=0.20)  # -20% ~ 10
            risco_insumo = _clamp(base_risk * 0.7 + drop_risk * 0.3, 0.0, 10.0)

            growth_potential = _clamp(_score_0_10_from_ratio(max(gr, 0.0), r_ref=0.25), 0.0, 10.0)

            comps = {
                "Volume_Operacional": round(volume, 2),
                "Importancia_Geografica": round(importancia, 2),
                "Risco_Insumo": round(risco_insumo, 2),
                "Growth_Potential": round(growth_potential, 2),
            }
            score = round(compute_score_soberano_v2(comps), 3)
            entities.append(
                SovereignEntity(
                    entity_type="distributor",
                    entity_id=cnpj,
                    name=d.get("company_name") or cnpj,
                    lat=d.get("lat"),
                    lon=d.get("lon"),
                    country="BR",
                    state_uf=st or None,
                    score=score,
                    components=comps,
                    status_color=classify_score_color(score),
                )
            )

        return entities

    def persist_snapshot_and_log_deltas(self, entities: List[SovereignEntity], delta_threshold: float = 0.15) -> Dict[str, Any]:
        """
        Upsert snapshot em `flv_sovereign_entities` e registra deltas em `flv_change_log`
        apenas quando:
        - entidade nova
        - mudança de score >= delta_threshold (pontos em escala 0..10)
        - mudança de status_color
        """
        obs_ts = _now_iso()
        created = 0
        updated = 0
        deltas = 0

        # Map do estado atual persistido
        existing = self._query(
            "SELECT entity_type, entity_id, score_soberano, status_color, components_json FROM flv_sovereign_entities"
        )
        ex_map: Dict[Tuple[str, str], Dict[str, Any]] = {(e["entity_type"], e["entity_id"]): e for e in existing}

        for ent in entities:
            key = (ent.entity_type, ent.entity_id)
            prev = ex_map.get(key)
            prev_score = _safe_float(prev.get("score_soberano")) if prev else None
            prev_color = prev.get("status_color") if prev else None

            # Upsert
            row = ent.to_row()
            self._execute(
                """
                INSERT INTO flv_sovereign_entities
                  (entity_type, entity_id, name, lat, lon, country, state_uf, score_soberano, components_json, status_color, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now'))
                ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                  name=excluded.name,
                  lat=excluded.lat,
                  lon=excluded.lon,
                  country=excluded.country,
                  state_uf=excluded.state_uf,
                  score_soberano=excluded.score_soberano,
                  components_json=excluded.components_json,
                  status_color=excluded.status_color,
                  updated_at=datetime('now')
                """,
                (
                    row["entity_type"],
                    row["entity_id"],
                    row["name"],
                    row["lat"],
                    row["lon"],
                    row["country"],
                    row["state_uf"],
                    row["score_soberano"],
                    row["components_json"],
                    row["status_color"],
                ),
            )

            if prev is None:
                created += 1
                self._log_change(
                    obs_ts=obs_ts,
                    domain="score",
                    entity_type=ent.entity_type,
                    entity_id=ent.entity_id,
                    change_type="insert",
                    severity=ent.status_color if ent.status_color in {"vermelho", "azul"} else "amarelo",
                    score_before=None,
                    score_after=ent.score,
                    payload={"name": ent.name, "components": ent.components},
                )
                deltas += 1
            else:
                updated += 1
                score_diff = abs(ent.score - (_safe_float(prev_score) if prev_score is not None else 0.0))
                color_changed = prev_color != ent.status_color
                if score_diff >= delta_threshold or color_changed:
                    self._log_change(
                        obs_ts=obs_ts,
                        domain="score",
                        entity_type=ent.entity_type,
                        entity_id=ent.entity_id,
                        change_type="update",
                        severity=ent.status_color if ent.status_color in {"vermelho", "azul"} else "amarelo",
                        score_before=prev_score,
                        score_after=ent.score,
                        payload={"name": ent.name, "components": ent.components, "score_diff": round(score_diff, 3)},
                    )
                    deltas += 1

        self._commit()
        return {"obs_ts": obs_ts, "created": created, "updated": updated, "deltas": deltas, "entities": len(entities)}

    def _log_change(
        self,
        obs_ts: str,
        domain: str,
        entity_type: Optional[str],
        entity_id: Optional[str],
        change_type: str,
        severity: Optional[str],
        score_before: Optional[float],
        score_after: Optional[float],
        payload: Dict[str, Any],
    ) -> None:
        self._execute(
            """
            INSERT INTO flv_change_log
              (obs_ts, domain, entity_type, entity_id, change_type, severity, score_before, score_after, payload_json)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                obs_ts,
                domain,
                entity_type,
                entity_id,
                change_type,
                severity,
                score_before,
                score_after,
                json.dumps(payload, ensure_ascii=False),
            ),
        )

    def snapshot(self) -> Dict[str, Any]:
        rows = self._query(
            """
            SELECT entity_type, entity_id, name, lat, lon, country, state_uf,
                   score_soberano as score, components_json, status_color, updated_at
            FROM flv_sovereign_entities
            ORDER BY score_soberano DESC
            """
        )
        for r in rows:
            try:
                r["components"] = json.loads(r.get("components_json") or "{}")
            except Exception:
                r["components"] = {}
            r.pop("components_json", None)
        return {"generated_at": _now_iso(), "entities": rows, "count": len(rows), "ceasa_prices": get_latest_ceasa_prices()}

    def deltas_since(self, since_iso: str, limit: int = 250) -> Dict[str, Any]:
        rows = self._query(
            """
            SELECT id, obs_ts, domain, entity_type, entity_id, change_type, severity,
                   score_before, score_after, payload_json
            FROM flv_change_log
            WHERE obs_ts > ?
            ORDER BY obs_ts ASC
            LIMIT ?
            """,
            (since_iso, limit),
        )
        for r in rows:
            try:
                r["payload"] = json.loads(r.get("payload_json") or "{}")
            except Exception:
                r["payload"] = {}
            r.pop("payload_json", None)
        latest = rows[-1]["obs_ts"] if rows else since_iso
        return {"since": since_iso, "latest": latest, "deltas": rows, "count": len(rows)}


def run_cycle(delta_threshold: float = 0.15) -> Dict[str, Any]:
    """
    Executa um ciclo completo do motor War Room:
    - build snapshot
    - persist + log deltas
    """
    engine = WarRoomEngine()
    ents = engine.build_entities_snapshot()
    return engine.persist_snapshot_and_log_deltas(ents, delta_threshold=delta_threshold)

