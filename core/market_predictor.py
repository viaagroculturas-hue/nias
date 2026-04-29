#!/usr/bin/env python3
"""
Market predictor for FLV crops.

Cruza quebras de safra bio-climaticas ja detectadas pelo motor de alertas
com historico CEPEA/CEASA para prever tendencia de preco em 15 dias.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nia_flv.db")
TARGET_CROPS = ("tomate", "cebola", "batata")
HORIZON_DAYS = 15
MODEL_VERSION = "market-predictor-v1"


@dataclass
class PricePoint:
    date: str
    price: float
    source: str
    terminal: Optional[str] = None


@dataclass
class CropBreak:
    region_key: str
    alert_type: str
    severity: str
    supply_impact_pct: float
    price_impact_pct: float
    message: str
    created_at: str
    valid_until: Optional[str] = None
    trigger_value: Optional[float] = None
    threshold_value: Optional[float] = None


@dataclass
class BioClimateSnapshot:
    ndvi: Optional[float]
    ndvi_anomaly: Optional[float]
    precip_7d_mm: Optional[float]
    temp_max_avg_c: Optional[float]
    temp_min_avg_c: Optional[float]
    climate_risk_score: float
    risk_factors: List[str]


@dataclass
class ForecastPoint:
    date: str
    price: float
    lower: float
    upper: float


@dataclass
class MarketPrediction:
    product: str
    product_name: str
    horizon_days: int
    current_price: Optional[float]
    predicted_price: Optional[float]
    price_change_pct: float
    trend: str
    confidence_pct: float
    model: str
    forecast: List[ForecastPoint]
    crop_breaks: List[CropBreak]
    bio_climate: BioClimateSnapshot
    alerts: List[Dict]
    generated_at: str

    def to_dict(self) -> Dict:
        data = asdict(self)
        return data


class MarketPredictor:
    """Predicts Alta/Baixa for tomate, cebola and batata over the next 15 days."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def predict_all(self, persist: bool = False) -> Dict[str, Dict]:
        """Run 15-day predictions for the supported crops."""
        result = {}
        for crop_slug in TARGET_CROPS:
            prediction = self.predict(crop_slug, persist=persist)
            result[crop_slug] = prediction.to_dict()
        return {
            "generated_at": datetime.now().isoformat(),
            "horizon_days": HORIZON_DAYS,
            "products": result,
            "summary": self._build_summary(result),
        }

    def predict(self, crop_slug: str, persist: bool = False) -> MarketPrediction:
        crop_slug = self._normalize_crop(crop_slug)
        try:
            with self.get_conn() as conn:
                culture = self._get_culture(conn, crop_slug)
                prices = self._load_price_history(conn, crop_slug)
                crop_breaks = self._load_crop_breaks(conn, crop_slug)
                bio_climate = self._load_bio_climate_snapshot(conn, crop_slug)
        except sqlite3.Error:
            culture = {"slug": crop_slug, "name_pt": crop_slug.title()}
            prices = self._synthetic_price_history(crop_slug)
            crop_breaks = []
            bio_climate = self._empty_bio_climate_snapshot()

        forecast = self._forecast_prices(prices, crop_breaks, bio_climate, HORIZON_DAYS)
        current_price = prices[-1].price if prices else None
        predicted_price = forecast[-1].price if forecast else current_price
        price_change_pct = self._pct_change(current_price, predicted_price)
        trend = self._classify_trend(price_change_pct)
        confidence = self._confidence(prices, crop_breaks, bio_climate)
        alerts = self._build_alerts(crop_slug, crop_breaks, bio_climate, price_change_pct)

        prediction = MarketPrediction(
            product=crop_slug,
            product_name=culture.get("name_pt", crop_slug.title()),
            horizon_days=HORIZON_DAYS,
            current_price=round(current_price, 2) if current_price is not None else None,
            predicted_price=round(predicted_price, 2) if predicted_price is not None else None,
            price_change_pct=round(price_change_pct, 2),
            trend=trend,
            confidence_pct=confidence,
            model=MODEL_VERSION,
            forecast=forecast,
            crop_breaks=crop_breaks,
            bio_climate=bio_climate,
            alerts=alerts,
            generated_at=datetime.now().isoformat(),
        )

        if persist:
            self.persist_prediction(prediction)

        return prediction

    def persist_prediction(self, prediction: MarketPrediction) -> None:
        """Store forecast points and shortage alerts in the FLV SQLite schema."""
        try:
            conn_cm = self.get_conn()
        except sqlite3.Error:
            return

        try:
            with conn_cm as conn:
                culture = self._get_culture(conn, prediction.product)
                culture_id = culture.get("id")
                if not culture_id:
                    return

                features_json = json.dumps(
                    {
                        "crop_breaks": [asdict(item) for item in prediction.crop_breaks],
                        "bio_climate": asdict(prediction.bio_climate),
                        "alerts": prediction.alerts,
                        "price_change_pct": prediction.price_change_pct,
                    },
                    ensure_ascii=True,
                )

                for point in prediction.forecast:
                    conn.execute(
                        """
                        INSERT INTO flv_predictions (
                            culture_id, target_date, horizon_days, predicted_price,
                            price_lower_80, price_upper_80, trend_direction,
                            confidence_pct, model_version, features_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            culture_id,
                            point.date,
                            prediction.horizon_days,
                            point.price,
                            point.lower,
                            point.upper,
                            prediction.trend,
                            prediction.confidence_pct,
                            MODEL_VERSION,
                            features_json,
                        ),
                    )

                for alert in prediction.alerts:
                    if alert.get("type") != "Escassez Iminente":
                        continue
                    conn.execute(
                        """
                        INSERT INTO flv_alerts (
                            culture_id, region_key, alert_type, severity, trigger_value,
                            threshold_value, impact_supply_pct, impact_price_pct,
                            message, valid_until
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            culture_id,
                            alert.get("region_key", "mercado_nacional"),
                            alert["type"],
                            alert["severity"],
                            alert.get("risk_score"),
                            70.0,
                            alert.get("supply_impact_pct"),
                            prediction.price_change_pct,
                            alert["message"],
                            (datetime.now() + timedelta(days=prediction.horizon_days)).strftime("%Y-%m-%d"),
                        ),
                    )
                conn.commit()
        except sqlite3.Error:
            return

    def _get_culture(self, conn: sqlite3.Connection, crop_slug: str) -> Dict:
        row = conn.execute(
            "SELECT id, slug, name_pt, unit FROM flv_cultures WHERE slug = ?",
            (crop_slug,),
        ).fetchone()
        return dict(row) if row else {"slug": crop_slug, "name_pt": crop_slug.title()}

    def _load_price_history(self, conn: sqlite3.Connection, crop_slug: str, days: int = 180) -> List[PricePoint]:
        rows = conn.execute(
            """
            SELECT p.price_date, AVG(p.price_avg) AS price_avg,
                   GROUP_CONCAT(DISTINCT p.source) AS sources,
                   GROUP_CONCAT(DISTINCT p.terminal) AS terminals
            FROM flv_ceasa_prices p
            JOIN flv_cultures c ON c.id = p.culture_id
            WHERE c.slug = ?
              AND p.price_date >= date('now', ?)
              AND p.price_avg > 0
            GROUP BY p.price_date
            ORDER BY p.price_date
            """,
            (crop_slug, f"-{days} days"),
        ).fetchall()

        points = [
            PricePoint(
                date=row["price_date"],
                price=float(row["price_avg"]),
                source=row["sources"] or "CEPEA/CEASA",
                terminal=row["terminals"],
            )
            for row in rows
            if row["price_avg"] is not None
        ]
        if points:
            return points
        return self._synthetic_price_history(crop_slug)

    def _load_crop_breaks(self, conn: sqlite3.Connection, crop_slug: str, days: int = 15) -> List[CropBreak]:
        rows = conn.execute(
            """
            SELECT a.region_key, a.alert_type, a.severity, a.impact_supply_pct,
                   a.impact_price_pct, a.message, a.created_at, a.valid_until,
                   a.trigger_value, a.threshold_value
            FROM flv_alerts a
            JOIN flv_cultures c ON c.id = a.culture_id
            WHERE c.slug = ?
              AND a.created_at >= datetime('now', ?)
              AND (a.valid_until IS NULL OR a.valid_until >= date('now'))
            ORDER BY
              CASE a.severity WHEN 'vermelho' THEN 3 WHEN 'laranja' THEN 2 ELSE 1 END DESC,
              a.created_at DESC
            """,
            (crop_slug, f"-{days} days"),
        ).fetchall()

        return [
            CropBreak(
                region_key=row["region_key"],
                alert_type=row["alert_type"],
                severity=row["severity"] or "amarelo",
                supply_impact_pct=float(row["impact_supply_pct"] or 0),
                price_impact_pct=float(row["impact_price_pct"] or 0),
                message=row["message"] or "",
                created_at=row["created_at"],
                valid_until=row["valid_until"],
                trigger_value=row["trigger_value"],
                threshold_value=row["threshold_value"],
            )
            for row in rows
        ]

    def _load_bio_climate_snapshot(self, conn: sqlite3.Connection, crop_slug: str) -> BioClimateSnapshot:
        mun_rows = conn.execute(
            """
            SELECT DISTINCT m.id
            FROM flv_municipalities m
            JOIN flv_mun_culture mc ON mc.mun_id = m.id
            JOIN flv_cultures c ON c.id = mc.culture_id
            WHERE c.slug = ?
            """,
            (crop_slug,),
        ).fetchall()
        mun_ids = [row["id"] for row in mun_rows]

        if not mun_ids:
            producer_states = self._producer_states(conn, crop_slug)
            if producer_states:
                placeholders = ",".join("?" for _ in producer_states)
                mun_rows = conn.execute(
                    f"SELECT id FROM flv_municipalities WHERE state_uf IN ({placeholders})",
                    producer_states,
                ).fetchall()
                mun_ids = [row["id"] for row in mun_rows]

        ndvi, ndvi_anomaly = self._latest_ndvi(conn, mun_ids)
        precip_7d, temp_max_avg, temp_min_avg = self._recent_climate(conn, mun_ids)
        score, factors = self._bio_climate_risk_score(
            ndvi=ndvi,
            ndvi_anomaly=ndvi_anomaly,
            precip_7d=precip_7d,
            temp_max_avg=temp_max_avg,
            temp_min_avg=temp_min_avg,
        )

        return BioClimateSnapshot(
            ndvi=self._round_or_none(ndvi, 3),
            ndvi_anomaly=self._round_or_none(ndvi_anomaly, 3),
            precip_7d_mm=self._round_or_none(precip_7d, 1),
            temp_max_avg_c=self._round_or_none(temp_max_avg, 1),
            temp_min_avg_c=self._round_or_none(temp_min_avg, 1),
            climate_risk_score=round(score, 1),
            risk_factors=factors,
        )

    def _empty_bio_climate_snapshot(self) -> BioClimateSnapshot:
        return BioClimateSnapshot(
            ndvi=None,
            ndvi_anomaly=None,
            precip_7d_mm=None,
            temp_max_avg_c=None,
            temp_min_avg_c=None,
            climate_risk_score=0.0,
            risk_factors=[],
        )

    def _forecast_prices(
        self,
        prices: Sequence[PricePoint],
        crop_breaks: Sequence[CropBreak],
        bio_climate: BioClimateSnapshot,
        horizon: int,
    ) -> List[ForecastPoint]:
        if not prices:
            return []

        base_forecast = self._statsmodels_forecast(prices, horizon)
        if not base_forecast:
            base_forecast = self._holt_fallback(prices, horizon)

        shock_curve = self._supply_shock_curve(crop_breaks, bio_climate, horizon)
        volatility = self._historical_volatility([p.price for p in prices])
        forecast = []

        for idx, (date_str, raw_price) in enumerate(base_forecast, start=1):
            adjusted = max(raw_price * (1 + shock_curve[idx - 1]), 0.01)
            band = max(0.06, min(0.25, volatility * 1.65 + abs(shock_curve[idx - 1]) * 0.45))
            forecast.append(
                ForecastPoint(
                    date=date_str,
                    price=round(adjusted, 2),
                    lower=round(adjusted * (1 - band), 2),
                    upper=round(adjusted * (1 + band), 2),
                )
            )
        return forecast

    def _statsmodels_forecast(self, prices: Sequence[PricePoint], horizon: int) -> List[Tuple[str, float]]:
        if len(prices) < 10:
            return []
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
        except Exception:
            return []

        values = [max(p.price, 0.01) for p in prices]
        try:
            seasonal = "add" if len(values) >= 28 else None
            seasonal_periods = 7 if seasonal else None
            model = ExponentialSmoothing(
                values,
                trend="add",
                seasonal=seasonal,
                seasonal_periods=seasonal_periods,
                initialization_method="estimated",
            )
            fit = model.fit(optimized=True)
            preds = fit.forecast(horizon)
        except Exception:
            return []

        last_date = self._parse_date(prices[-1].date)
        return [
            ((last_date + timedelta(days=idx)).strftime("%Y-%m-%d"), float(value))
            for idx, value in enumerate(preds, start=1)
        ]

    def _holt_fallback(self, prices: Sequence[PricePoint], horizon: int) -> List[Tuple[str, float]]:
        values = [max(p.price, 0.01) for p in prices]
        alpha = 0.45
        beta = 0.18
        level = values[0]
        trend = values[1] - values[0] if len(values) > 1 else 0.0

        for value in values[1:]:
            previous_level = level
            level = alpha * value + (1 - alpha) * (level + trend)
            trend = beta * (level - previous_level) + (1 - beta) * trend

        if len(values) >= 14:
            short = statistics.mean(values[-7:])
            long = statistics.mean(values[-14:-7])
            trend = 0.5 * trend + 0.5 * ((short - long) / 7)

        last_date = self._parse_date(prices[-1].date)
        return [
            ((last_date + timedelta(days=i)).strftime("%Y-%m-%d"), max(level + trend * i, 0.01))
            for i in range(1, horizon + 1)
        ]

    def _supply_shock_curve(
        self,
        crop_breaks: Sequence[CropBreak],
        bio_climate: BioClimateSnapshot,
        horizon: int,
    ) -> List[float]:
        price_shock = sum(max(item.price_impact_pct, 0.0) for item in crop_breaks) / 100.0
        supply_shock = sum(abs(min(item.supply_impact_pct, 0.0)) for item in crop_breaks) / 100.0
        severity_weight = sum(self._severity_weight(item.severity) for item in crop_breaks) / 100.0
        climate_shock = bio_climate.climate_risk_score / 100.0 * 0.12
        total_shock = min(0.55, price_shock * 0.45 + supply_shock * 0.35 + severity_weight + climate_shock)

        curve = []
        for day in range(1, horizon + 1):
            ramp = 1 - math.exp(-day / 5.0)
            decay = 1.0 if day <= 10 else max(0.72, 1 - (day - 10) * 0.035)
            curve.append(total_shock * ramp * decay)
        return curve

    def _build_alerts(
        self,
        crop_slug: str,
        crop_breaks: Sequence[CropBreak],
        bio_climate: BioClimateSnapshot,
        price_change_pct: float,
    ) -> List[Dict]:
        alerts = []
        shortage_score = self._shortage_score(crop_breaks, bio_climate, price_change_pct)
        severe_breaks = [item for item in crop_breaks if item.severity in {"laranja", "vermelho"}]

        if shortage_score >= 70:
            severity = "vermelho" if shortage_score >= 85 else "laranja"
            regions = sorted({item.region_key for item in severe_breaks}) or ["mercado_nacional"]
            alerts.append(
                {
                    "type": "Escassez Iminente",
                    "severity": severity,
                    "product": crop_slug,
                    "region_key": ",".join(regions),
                    "risk_score": round(shortage_score, 1),
                    "supply_impact_pct": round(sum(item.supply_impact_pct for item in crop_breaks), 1),
                    "message": (
                        f"Escassez Iminente de {crop_slug}: quebras bio-climaticas e tendencia "
                        f"de preco indicam risco nos proximos {HORIZON_DAYS} dias."
                    ),
                }
            )

        for item in severe_breaks[:3]:
            alerts.append(
                {
                    "type": item.alert_type,
                    "severity": item.severity,
                    "product": crop_slug,
                    "region_key": item.region_key,
                    "risk_score": round(shortage_score, 1),
                    "supply_impact_pct": item.supply_impact_pct,
                    "message": item.message,
                }
            )

        return alerts

    def _confidence(
        self,
        prices: Sequence[PricePoint],
        crop_breaks: Sequence[CropBreak],
        bio_climate: BioClimateSnapshot,
    ) -> float:
        data_score = min(35.0, len(prices) * 0.35)
        model_score = 20.0 if len(prices) >= 30 else 12.0
        alert_score = min(20.0, len(crop_breaks) * 7.0)
        climate_score = 15.0 if bio_climate.risk_factors else 8.0
        confidence = 25.0 + data_score + model_score + alert_score + climate_score
        return round(max(35.0, min(92.0, confidence)), 1)

    def _shortage_score(
        self,
        crop_breaks: Sequence[CropBreak],
        bio_climate: BioClimateSnapshot,
        price_change_pct: float,
    ) -> float:
        break_score = min(55.0, sum(abs(min(item.supply_impact_pct, 0.0)) for item in crop_breaks) * 0.9)
        severity_score = min(20.0, sum(self._severity_weight(item.severity) for item in crop_breaks))
        climate_score = bio_climate.climate_risk_score * 0.35
        trend_score = max(0.0, min(15.0, price_change_pct * 1.2))
        return min(100.0, break_score + severity_score + climate_score + trend_score)

    def _bio_climate_risk_score(
        self,
        ndvi: Optional[float],
        ndvi_anomaly: Optional[float],
        precip_7d: Optional[float],
        temp_max_avg: Optional[float],
        temp_min_avg: Optional[float],
    ) -> Tuple[float, List[str]]:
        score = 0.0
        factors = []
        if ndvi is not None and ndvi < 0.48:
            score += 25
            factors.append("NDVI baixo")
        if ndvi_anomaly is not None and ndvi_anomaly < -0.08:
            score += 25
            factors.append("anomalia negativa de NDVI")
        if precip_7d is not None and precip_7d < 5:
            score += 18
            factors.append("deficit hidrico 7d")
        if precip_7d is not None and precip_7d > 110:
            score += 16
            factors.append("excesso de chuva 7d")
        if temp_max_avg is not None and temp_max_avg >= 35:
            score += 18
            factors.append("estresse termico")
        if temp_min_avg is not None and temp_min_avg <= 4:
            score += 20
            factors.append("risco de frio/geada")
        return min(100.0, score), factors

    def _latest_ndvi(self, conn: sqlite3.Connection, mun_ids: Sequence[int]) -> Tuple[Optional[float], Optional[float]]:
        if mun_ids:
            placeholders = ",".join("?" for _ in mun_ids)
            rows = conn.execute(
                f"""
                SELECT ndvi_value, ndvi_anomaly
                FROM flv_ndvi
                WHERE mun_id IN ({placeholders})
                  AND obs_date >= date('now', '-30 days')
                ORDER BY obs_date DESC
                LIMIT 20
                """,
                list(mun_ids),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT ndvi_value, ndvi_anomaly
                FROM flv_ndvi
                WHERE obs_date >= date('now', '-30 days')
                ORDER BY obs_date DESC
                LIMIT 20
                """
            ).fetchall()

        ndvi_values = [float(row["ndvi_value"]) for row in rows if row["ndvi_value"] is not None]
        anomaly_values = [float(row["ndvi_anomaly"]) for row in rows if row["ndvi_anomaly"] is not None]
        return (
            statistics.mean(ndvi_values) if ndvi_values else None,
            statistics.mean(anomaly_values) if anomaly_values else None,
        )

    def _recent_climate(
        self,
        conn: sqlite3.Connection,
        mun_ids: Sequence[int],
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if mun_ids:
            placeholders = ",".join("?" for _ in mun_ids)
            rows = conn.execute(
                f"""
                SELECT obs_date, AVG(precip_mm) AS precip_mm,
                       AVG(temp_max_c) AS temp_max_c,
                       AVG(temp_min_c) AS temp_min_c
                FROM flv_climate
                WHERE mun_id IN ({placeholders})
                  AND obs_date >= date('now', '-7 days')
                GROUP BY obs_date
                """,
                list(mun_ids),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT obs_date, AVG(precip_mm) AS precip_mm,
                       AVG(temp_max_c) AS temp_max_c,
                       AVG(temp_min_c) AS temp_min_c
                FROM flv_climate
                WHERE obs_date >= date('now', '-7 days')
                GROUP BY obs_date
                """
            ).fetchall()

        if not rows:
            return None, None, None

        precip = sum(float(row["precip_mm"] or 0) for row in rows)
        temp_max_vals = [float(row["temp_max_c"]) for row in rows if row["temp_max_c"] is not None]
        temp_min_vals = [float(row["temp_min_c"]) for row in rows if row["temp_min_c"] is not None]
        return (
            precip,
            statistics.mean(temp_max_vals) if temp_max_vals else None,
            statistics.mean(temp_min_vals) if temp_min_vals else None,
        )

    def _producer_states(self, conn: sqlite3.Connection, crop_slug: str) -> List[str]:
        row = conn.execute("SELECT main_producers FROM flv_cultures WHERE slug = ?", (crop_slug,)).fetchone()
        if not row or not row["main_producers"]:
            return []
        return [item.strip() for item in row["main_producers"].split(",") if item.strip()]

    def _synthetic_price_history(self, crop_slug: str) -> List[PricePoint]:
        base_prices = {"tomate": 68.20, "cebola": 38.70, "batata": 52.10}
        seasonal_bias = {"tomate": 0.0015, "cebola": -0.0008, "batata": 0.0004}
        base = base_prices.get(crop_slug, 40.0)
        bias = seasonal_bias.get(crop_slug, 0.0)
        start = datetime.now() - timedelta(days=59)
        points = []
        for idx in range(60):
            wave = math.sin(idx / 6.0) * 0.025
            price = base * (1 + (idx - 30) * bias + wave)
            points.append(
                PricePoint(
                    date=(start + timedelta(days=idx)).strftime("%Y-%m-%d"),
                    price=round(max(price, 0.01), 2),
                    source="fallback-seed",
                    terminal="CEPEA/CEASA",
                )
            )
        return points

    def _build_summary(self, products: Dict[str, Dict]) -> Dict:
        shortage = [
            slug
            for slug, data in products.items()
            if any(alert.get("type") == "Escassez Iminente" for alert in data.get("alerts", []))
        ]
        trend_counts = {"alta": 0, "baixa": 0, "estavel": 0}
        for data in products.values():
            trend_counts[data.get("trend", "estavel")] = trend_counts.get(data.get("trend", "estavel"), 0) + 1
        return {
            "trend_counts": trend_counts,
            "shortage_alerts": shortage,
            "highest_risk_product": max(
                products,
                key=lambda slug: products[slug]["bio_climate"]["climate_risk_score"],
            )
            if products
            else None,
        }

    def _normalize_crop(self, crop_slug: str) -> str:
        normalized = (crop_slug or "").strip().lower()
        aliases = {"tomate mesa": "tomate", "batata inglesa": "batata"}
        normalized = aliases.get(normalized, normalized)
        if normalized not in TARGET_CROPS:
            raise ValueError(f"Cultura nao suportada: {crop_slug}. Use {', '.join(TARGET_CROPS)}.")
        return normalized

    @staticmethod
    def _classify_trend(price_change_pct: float) -> str:
        if price_change_pct >= 2.0:
            return "alta"
        if price_change_pct <= -2.0:
            return "baixa"
        return "estavel"

    @staticmethod
    def _pct_change(current: Optional[float], future: Optional[float]) -> float:
        if current is None or future is None or current <= 0:
            return 0.0
        return ((future - current) / current) * 100.0

    @staticmethod
    def _historical_volatility(values: Sequence[float]) -> float:
        if len(values) < 3:
            return 0.08
        returns = []
        for previous, current in zip(values, values[1:]):
            if previous > 0:
                returns.append((current - previous) / previous)
        return statistics.pstdev(returns[-30:]) if len(returns) >= 2 else 0.08

    @staticmethod
    def _severity_weight(severity: str) -> float:
        return {"amarelo": 4.0, "laranja": 9.0, "vermelho": 14.0}.get(severity, 3.0)

    @staticmethod
    def _round_or_none(value: Optional[float], digits: int) -> Optional[float]:
        return round(value, digits) if value is not None else None

    @staticmethod
    def _parse_date(value: str) -> datetime:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value[:10], fmt)
            except ValueError:
                continue
        return datetime.now()


def predict_market_trends(persist: bool = False, db_path: str = DEFAULT_DB_PATH) -> Dict[str, Dict]:
    """Convenience API used by jobs/endpoints."""
    return MarketPredictor(db_path=db_path).predict_all(persist=persist)


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Preve tendencia de Tomate, Cebola e Batata em 15 dias.")
    parser.add_argument("--persist", action="store_true", help="Grava previsoes e alertas no SQLite.")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Caminho do banco SQLite.")
    args = parser.parse_args(argv)

    report = predict_market_trends(persist=args.persist, db_path=args.db)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
