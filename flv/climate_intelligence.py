"""
NiasClimate — Motor de Inteligencia Climatica.
Usa dados do banco (flv_climate + flv_ceasa_prices) para analise clima x preco.
"""
from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timedelta

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.environ.get('NIAS_DB_PATH') or os.path.join(_ROOT, 'data', 'nia_flv.db')

def _conn():
    c = sqlite3.connect(_DB_PATH, check_same_thread=False, timeout=10)
    c.row_factory = sqlite3.Row
    return c


class ClimateEngine:
    def __init__(self):
        self._events = []
        self._impacts = []

    def get_status(self):
        conn = _conn()
        climate_count = conn.execute("SELECT COUNT(*) FROM flv_climate").fetchone()[0]
        price_count = conn.execute("SELECT COUNT(*) FROM flv_ceasa_prices").fetchone()[0]
        mun_count = conn.execute("SELECT COUNT(*) FROM flv_municipalities").fetchone()[0]
        last_climate = conn.execute(
            "SELECT MAX(obs_date) FROM flv_climate"
        ).fetchone()[0]
        return {
            'status': 'operational' if climate_count > 0 else 'awaiting_data',
            'climate_records': climate_count,
            'price_records': price_count,
            'municipalities': mun_count,
            'last_climate_date': last_climate,
            'source': 'Open-Meteo',
            'db_path': _DB_PATH,
        }

    def detect_extreme_events(self):
        conn = _conn()
        self._events = []
        try:
            rows = conn.execute("""
                SELECT c.obs_date, c.temp_max_c, c.temp_min_c, c.precip_mm,
                       m.name as mun_name
                FROM flv_climate c
                JOIN flv_municipalities m ON c.mun_id = m.id
                WHERE c.obs_date >= date('now', '-30 days')
                ORDER BY c.obs_date DESC
            """).fetchall()
            for r in rows:
                if r['temp_max_c'] and r['temp_max_c'] > 38:
                    self._events.append({
                        'type': 'heat_wave',
                        'date': r['obs_date'],
                        'municipality': r['mun_name'],
                        'value': r['temp_max_c'],
                        'severity': 'high',
                    })
                if r['precip_mm'] and r['precip_mm'] > 50:
                    self._events.append({
                        'type': 'heavy_rain',
                        'date': r['obs_date'],
                        'municipality': r['mun_name'],
                        'value': r['precip_mm'],
                        'severity': 'medium',
                    })
                if r['temp_min_c'] and r['temp_min_c'] < 5:
                    self._events.append({
                        'type': 'frost_risk',
                        'date': r['obs_date'],
                        'municipality': r['mun_name'],
                        'value': r['temp_min_c'],
                        'severity': 'high',
                    })
        except Exception:
            pass
        return self._events

    def generate_climate_alerts(self):
        alerts = []
        for ev in self._events:
            alerts.append({
                'event': ev['type'],
                'municipality': ev['municipality'],
                'date': ev['date'],
                'severity': ev['severity'],
                'message': f"{ev['type']} em {ev['municipality']} ({ev['date']}): {ev['value']}",
            })
        return alerts

    def analyze_weather_price_correlation(self):
        conn = _conn()
        try:
            rows = conn.execute("""
                SELECT c.slug, cu.name_pt as product,
                       AVG(cl.temp_max_c) as avg_temp,
                       AVG(cl.precip_mm) as avg_precip,
                       AVG(p.price_avg) as avg_price,
                       COUNT(*) as samples
                FROM flv_ceasa_prices p
                JOIN flv_cultures c ON p.culture_id = c.id
                JOIN flv_municipalities m ON c.id IS NOT NULL
                JOIN flv_climate cl ON cl.mun_id = m.id
                    AND cl.obs_date = p.price_date
                JOIN flv_cultures cu ON p.culture_id = cu.id
                GROUP BY c.slug
                HAVING samples >= 3
            """).fetchall()
            if rows:
                correlations = []
                for r in rows:
                    correlations.append({
                        'product': r['product'] or r['slug'],
                        'avg_temp_c': round(r['avg_temp'], 1) if r['avg_temp'] else None,
                        'avg_precip_mm': round(r['avg_precip'], 1) if r['avg_precip'] else None,
                        'avg_price': round(r['avg_price'], 2) if r['avg_price'] else None,
                        'samples': r['samples'],
                    })
                return {
                    'mode': 'real_data',
                    'correlations': correlations,
                    'total': len(correlations),
                }
        except Exception:
            pass
        return {
            'mode': 'insufficient_data',
            'reason': 'Dados climaticos insuficientes para correlacao. Aguardando pipeline popular flv_climate.',
            'correlations': [],
            'total': 0,
        }

    def calculate_price_impact(self):
        self._impacts = []
        for ev in self._events:
            self._impacts.append({
                'event': ev['type'],
                'municipality': ev['municipality'],
                'estimated_impact': 'moderate' if ev['severity'] == 'medium' else 'high',
            })
        return self._impacts

    def generate_climate_report(self):
        status = self.get_status()
        return {
            'report_date': datetime.now().isoformat(),
            'status': status,
            'events': self._events,
            'impacts': self._impacts,
            'alerts_count': len(self._events),
        }

    def get_regions(self):
        conn = _conn()
        try:
            rows = conn.execute("""
                SELECT m.name, m.state, m.lat, m.lon,
                       COUNT(cl.id) as climate_records
                FROM flv_municipalities m
                LEFT JOIN flv_climate cl ON cl.mun_id = m.id
                GROUP BY m.id
            """).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []


_engine = None

def get_climate_engine():
    global _engine
    if _engine is None:
        _engine = ClimateEngine()
    return _engine
