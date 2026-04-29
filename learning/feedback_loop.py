#!/usr/bin/env python3
"""
Feedback loop diario do NIA$.

Compara a Previsao de Preco gravada pelo modelo com o Preco Real CEPEA/CEASA.
Quando o erro absoluto passa de 5%, ajusta pesos entre clima e logistica e
registra cada calibracao no log de Evolucao da Inteligencia.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple


ERROR_THRESHOLD_PCT = 5.0
LEARNING_RATE = 0.08
MIN_WEIGHT = 0.15
MAX_WEIGHT = 0.85
DEFAULT_CLIMATE_WEIGHT = 0.50
DEFAULT_LOGISTICS_WEIGHT = 0.50
MODEL_NAME = "nia-price-v1"


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clamp(value: float, min_value: float = MIN_WEIGHT, max_value: float = MAX_WEIGHT) -> float:
    return max(min_value, min(max_value, value))


def _normalizar_pesos(climate_weight: float, logistics_weight: float) -> Tuple[float, float]:
    climate_weight = _clamp(climate_weight)
    logistics_weight = _clamp(logistics_weight)
    total = climate_weight + logistics_weight
    if total <= 0:
        return DEFAULT_CLIMATE_WEIGHT, DEFAULT_LOGISTICS_WEIGHT
    climate_weight = _clamp(climate_weight / total)
    logistics_weight = _clamp(1.0 - climate_weight)
    total = climate_weight + logistics_weight
    return round(climate_weight / total, 4), round(logistics_weight / total, 4)


def init_feedback_schema(conn) -> None:
    """Cria tabelas usadas pelo ciclo de aprendizado, sem depender de migracao externa."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_model_weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            culture_id INTEGER REFERENCES flv_cultures(id),
            terminal TEXT NOT NULL DEFAULT '',
            climate_weight REAL NOT NULL,
            logistics_weight REAL NOT NULL,
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(model_name, culture_id, terminal)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inteligencia_evolucao_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date TEXT NOT NULL,
            event_type TEXT NOT NULL,
            model_name TEXT NOT NULL,
            culture_id INTEGER REFERENCES flv_cultures(id),
            terminal TEXT,
            prediction_id INTEGER REFERENCES flv_predictions(id),
            predicted_price REAL,
            actual_price REAL,
            error_pct REAL,
            climate_weight_before REAL,
            logistics_weight_before REAL,
            climate_weight_after REAL,
            logistics_weight_after REAL,
            adjustment_reason TEXT,
            details_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_learning_weights_lookup "
        "ON learning_model_weights(model_name, culture_id, terminal)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_intel_evo_date "
        "ON inteligencia_evolucao_log(event_date, event_type)"
    )
    conn.commit()


class FeedbackLoop:
    """Executa avaliacao diaria e calibracao automatica dos pesos do modelo."""

    def __init__(
        self,
        conn=None,
        model_name: str = MODEL_NAME,
        error_threshold_pct: float = ERROR_THRESHOLD_PCT,
        learning_rate: float = LEARNING_RATE,
    ):
        self.conn = conn
        self.model_name = model_name
        self.error_threshold_pct = float(error_threshold_pct)
        self.learning_rate = float(learning_rate)

    def _conn(self):
        if self.conn is not None:
            return self.conn
        from flv.db import get_conn, init_db

        init_db()
        self.conn = get_conn()
        return self.conn

    def run_daily(self, reference_date: Optional[str] = None, lookback_days: int = 1) -> Dict[str, Any]:
        """Executa o ciclo diario de comparacao previsao x real e ajusta pesos."""
        conn = self._conn()
        init_feedback_schema(conn)

        rows = self._fetch_prediction_pairs(conn, reference_date, lookback_days)
        adjustments: List[Dict[str, Any]] = []
        evaluated = 0
        skipped = 0

        for row in rows:
            actual = float(row["actual_price"])
            predicted = float(row["predicted_price"])
            if actual <= 0:
                skipped += 1
                continue

            error_pct = abs(predicted - actual) / actual * 100.0
            evaluated += 1
            self._record_accuracy(conn, row, actual, error_pct)

            if error_pct > self.error_threshold_pct:
                adjustments.append(self._adjust_weights(conn, row, predicted, actual, error_pct))

        conn.commit()
        result = {
            "status": "ok",
            "reference_date": reference_date or _today(),
            "lookback_days": lookback_days,
            "evaluated": evaluated,
            "skipped": skipped,
            "adjustments_count": len(adjustments),
            "threshold_pct": self.error_threshold_pct,
            "adjustments": adjustments,
        }
        print(
            "[FeedbackLoop] Avaliadas {evaluated} previsoes; {adjustments_count} ajuste(s) acima de {threshold_pct:.1f}%.".format(
                **result
            )
        )
        return result

    def _fetch_prediction_pairs(self, conn, reference_date: Optional[str], lookback_days: int) -> List[Any]:
        end_date = reference_date or _today()
        start_date = (
            datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=max(lookback_days - 1, 0))
        ).strftime("%Y-%m-%d")

        rows = conn.execute(
            """
            SELECT
                p.id AS prediction_id,
                p.culture_id,
                c.slug AS culture_slug,
                c.name_pt AS culture_name,
                p.terminal,
                p.target_date,
                p.predicted_price,
                p.model_version,
                cp.price_avg AS actual_price,
                cp.source AS actual_source
            FROM flv_predictions p
            JOIN flv_ceasa_prices cp
              ON cp.culture_id = p.culture_id
             AND COALESCE(cp.terminal, '') = COALESCE(p.terminal, '')
             AND cp.price_date = p.target_date
            LEFT JOIN flv_cultures c ON c.id = p.culture_id
            WHERE p.target_date BETWEEN ? AND ?
              AND p.predicted_price IS NOT NULL
              AND cp.price_avg IS NOT NULL
            ORDER BY p.target_date, p.culture_id, p.terminal, p.generated_at DESC
            """,
            (start_date, end_date),
        ).fetchall()
        return list(rows)

    def _record_accuracy(self, conn, row, actual_price: float, error_pct: float) -> None:
        already = conn.execute(
            "SELECT id FROM flv_accuracy WHERE prediction_id=? AND actual_date=?",
            (row["prediction_id"], row["target_date"]),
        ).fetchone()
        if already:
            return
        conn.execute(
            "INSERT INTO flv_accuracy (prediction_id, actual_price, actual_date, mape_pct) VALUES (?,?,?,?)",
            (row["prediction_id"], actual_price, row["target_date"], error_pct),
        )

    def _get_weights(self, conn, culture_id: int, terminal: Optional[str]) -> Tuple[float, float]:
        row = conn.execute(
            """
            SELECT climate_weight, logistics_weight
            FROM learning_model_weights
            WHERE model_name=? AND culture_id=? AND terminal=?
            """,
            (self.model_name, culture_id, terminal or ""),
        ).fetchone()
        if row:
            return float(row["climate_weight"]), float(row["logistics_weight"])
        return DEFAULT_CLIMATE_WEIGHT, DEFAULT_LOGISTICS_WEIGHT

    def _upsert_weights(
        self,
        conn,
        culture_id: int,
        terminal: Optional[str],
        climate_weight: float,
        logistics_weight: float,
    ) -> None:
        conn.execute(
            """
            INSERT INTO learning_model_weights
                (model_name, culture_id, terminal, climate_weight, logistics_weight, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(model_name, culture_id, terminal) DO UPDATE SET
                climate_weight=excluded.climate_weight,
                logistics_weight=excluded.logistics_weight,
                updated_at=excluded.updated_at
            """,
            (self.model_name, culture_id, terminal or "", climate_weight, logistics_weight, _iso_now()),
        )

    def _adjust_weights(self, conn, row, predicted: float, actual: float, error_pct: float) -> Dict[str, Any]:
        old_climate, old_logistics = self._get_weights(conn, row["culture_id"], row["terminal"])
        climate_signal, logistics_signal, signal_details = self._driver_signals(conn, row)

        if climate_signal == 0 and logistics_signal == 0:
            # Sem evidencia contextual: reduz suavemente o driver dominante para evitar cristalizacao.
            climate_signal = -1.0 if old_climate >= old_logistics else 0.5
            logistics_signal = 0.5 if old_climate >= old_logistics else -1.0

        direction = 1.0 if predicted < actual else -1.0
        scale = min(error_pct / 20.0, 1.0) * self.learning_rate
        delta_climate = direction * climate_signal * scale
        delta_logistics = direction * logistics_signal * scale

        new_climate, new_logistics = _normalizar_pesos(
            old_climate + delta_climate,
            old_logistics + delta_logistics,
        )
        self._upsert_weights(conn, row["culture_id"], row["terminal"], new_climate, new_logistics)

        reason = self._build_reason(predicted, actual, error_pct, climate_signal, logistics_signal)
        details = {
            "culture_slug": row["culture_slug"],
            "culture_name": row["culture_name"],
            "target_date": row["target_date"],
            "actual_source": row["actual_source"],
            "model_version": row["model_version"],
            "signals": signal_details,
            "learning_rate": self.learning_rate,
        }
        conn.execute(
            """
            INSERT INTO inteligencia_evolucao_log (
                event_date, event_type, model_name, culture_id, terminal, prediction_id,
                predicted_price, actual_price, error_pct,
                climate_weight_before, logistics_weight_before,
                climate_weight_after, logistics_weight_after,
                adjustment_reason, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _today(),
                "ajuste_pesos",
                self.model_name,
                row["culture_id"],
                row["terminal"],
                row["prediction_id"],
                predicted,
                actual,
                error_pct,
                old_climate,
                old_logistics,
                new_climate,
                new_logistics,
                reason,
                json.dumps(details, ensure_ascii=False, sort_keys=True),
            ),
        )
        return {
            "prediction_id": row["prediction_id"],
            "culture": row["culture_slug"],
            "terminal": row["terminal"],
            "target_date": row["target_date"],
            "predicted_price": round(predicted, 4),
            "actual_price": round(actual, 4),
            "error_pct": round(error_pct, 4),
            "weights_before": {"climate": old_climate, "logistics": old_logistics},
            "weights_after": {"climate": new_climate, "logistics": new_logistics},
            "reason": reason,
        }

    def _driver_signals(self, conn, row) -> Tuple[float, float, Dict[str, Any]]:
        target_date = row["target_date"]
        climate = conn.execute(
            """
            SELECT AVG(precip_mm) AS avg_precip, AVG(temp_max_c) AS avg_temp
            FROM flv_climate
            WHERE obs_date BETWEEN date(?, '-7 day') AND ?
            """,
            (target_date, target_date),
        ).fetchone()
        macro = conn.execute(
            """
            SELECT diesel_change_pct, brent_change_pct, wti_change_pct
            FROM flv_macro_indicators
            WHERE obs_date <= ?
            ORDER BY obs_date DESC
            LIMIT 1
            """,
            (target_date,),
        ).fetchone()

        avg_precip = _as_float(climate["avg_precip"] if climate else None)
        avg_temp = _as_float(climate["avg_temp"] if climate else None)
        diesel_change = _as_float(macro["diesel_change_pct"] if macro else None)
        brent_change = _as_float(macro["brent_change_pct"] if macro else None)
        wti_change = _as_float(macro["wti_change_pct"] if macro else None)

        climate_signal = 0.0
        if avg_precip is not None:
            climate_signal += min(abs(avg_precip - 5.0) / 20.0, 1.0)
        if avg_temp is not None:
            climate_signal += min(abs(avg_temp - 28.0) / 12.0, 1.0)
        climate_signal = min(climate_signal, 1.0)

        logistics_components = [v for v in (diesel_change, brent_change, wti_change) if v is not None]
        logistics_signal = min(sum(abs(v) for v in logistics_components) / 10.0, 1.0) if logistics_components else 0.0

        details = {
            "climate": {
                "avg_precip_7d": avg_precip,
                "avg_temp_7d": avg_temp,
                "signal": round(climate_signal, 4),
            },
            "logistics": {
                "diesel_change_pct": diesel_change,
                "brent_change_pct": brent_change,
                "wti_change_pct": wti_change,
                "signal": round(logistics_signal, 4),
            },
        }
        return climate_signal, logistics_signal, details

    def _build_reason(
        self,
        predicted: float,
        actual: float,
        error_pct: float,
        climate_signal: float,
        logistics_signal: float,
    ) -> str:
        sentido = "subestimou" if predicted < actual else "superestimou"
        driver = "clima" if climate_signal >= logistics_signal else "logistica"
        return (
            f"Previsao {sentido} o preco real em {error_pct:.2f}%; "
            f"maior evidencia contextual em {driver}."
        )


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def run_daily_feedback(reference_date: Optional[str] = None, lookback_days: int = 1) -> Dict[str, Any]:
    return FeedbackLoop().run_daily(reference_date=reference_date, lookback_days=lookback_days)


def main(argv: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    parser = argparse.ArgumentParser(description="Executa feedback loop diario NIA$")
    parser.add_argument("--date", dest="reference_date", help="Data alvo YYYY-MM-DD; padrao: hoje")
    parser.add_argument("--lookback-days", type=int, default=1, help="Janela de dias para avaliar")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_daily_feedback(reference_date=args.reference_date, lookback_days=args.lookback_days)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return result


if __name__ == "__main__":
    main()
