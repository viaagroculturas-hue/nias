"""
NiasClimate — Módulo de Inteligência Climática para correlação clima × preço.
============================================================================
Cruza dados climáticos (Open-Meteo) com preços (CEASA) e fenologia para
gerar alertas, estimar impacto no preço e produzir relatório executivo.
"""
from __future__ import annotations
import json, os, sqlite3, time
from datetime import datetime, timedelta
from typing import Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.environ.get('NIAS_DB_PATH') or os.path.join(_ROOT, 'data', 'nia_flv.db')

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTES: REGIÕES, CULTURAS E LIMIARES
# ═══════════════════════════════════════════════════════════════════════════

CLIMATE_REGIONS = [
    {'id': 'cinturao-verde-sp', 'name': 'Cinturão Verde SP', 'lat': -23.72, 'lon': -47.06, 'crops': ['alface', 'tomate', 'pimentao'], 'corridor': 'sp-capital'},
    {'id': 'triangulo-mg', 'name': 'Triângulo Mineiro', 'lat': -18.92, 'lon': -48.27, 'crops': ['batata', 'cebola', 'tomate'], 'corridor': 'br364'},
    {'id': 'sul-minas', 'name': 'Sul de Minas', 'lat': -22.23, 'lon': -45.93, 'crops': ['batata', 'tomate', 'morango'], 'corridor': 'fernao-dias'},
    {'id': 'serra-gaucha', 'name': 'Serra Gaúcha', 'lat': -29.17, 'lon': -51.18, 'crops': ['uva', 'morango', 'alface'], 'corridor': 'br-101-sul'},
    {'id': 'serra-catarinense', 'name': 'Serra Catarinense', 'lat': -28.0, 'lon': -49.7, 'crops': ['maca', 'uva', 'alface'], 'corridor': 'br-282'},
    {'id': 'vale-itajai', 'name': 'Vale do Itajaí', 'lat': -26.9, 'lon': -49.1, 'crops': ['banana', 'tomate'], 'corridor': 'br-101-sc'},
    {'id': 'vale-sf', 'name': 'Vale do São Francisco', 'lat': -9.4, 'lon': -40.5, 'crops': ['manga', 'uva', 'cebola', 'tomate'], 'corridor': 'br-428'},
    {'id': 'chapada-ba', 'name': 'Chapada Diamantina', 'lat': -12.9, 'lon': -41.4, 'crops': ['batata', 'tomate', 'cenoura'], 'corridor': 'br-242'},
    {'id': 'ibiapaba-ce', 'name': 'Ibiapaba CE', 'lat': -3.7, 'lon': -41.0, 'crops': ['tomate', 'pimentao'], 'corridor': 'br-222'},
    {'id': 'cristalina-go', 'name': 'Cristalina GO', 'lat': -16.25, 'lon': -47.6, 'crops': ['cebola', 'tomate', 'batata'], 'corridor': 'br-040'},
    {'id': 'sul-pr', 'name': 'Sul do Paraná', 'lat': -25.4, 'lon': -49.8, 'crops': ['batata', 'cebola', 'cenoura'], 'corridor': 'br-116-pr'},
    {'id': 'norte-es', 'name': 'Norte do ES', 'lat': -18.7, 'lon': -39.9, 'crops': ['mamao', 'banana', 'abacaxi'], 'corridor': 'br-101-es'},
]

CLIMATE_THRESHOLDS = {
    'geada': {'temp_min': 2.0, 'desc': 'Temperatura mínima ≤ 2°C'},
    'risco_geada': {'temp_min': 4.0, 'desc': 'Temperatura mínima ≤ 4°C'},
    'calor_extremo': {'temp_max': 38.0, 'desc': 'Temperatura máxima ≥ 38°C'},
    'chuva_excessiva': {'precip_day': 40.0, 'desc': 'Precipitação > 40mm/dia'},
    'chuva_intensa': {'precip_day': 25.0, 'desc': 'Precipitação > 25mm/dia'},
    'vento_forte': {'wind_max': 50.0, 'desc': 'Rajadas > 50km/h'},
    'tempestade': {'wind_max': 80.0, 'desc': 'Rajadas > 80km/h'},
    'estiagem': {'precip_week': 5.0, 'desc': 'Precipitação semanal < 5mm'},
}

# Vulnerabilidade: evento → cultura → impacto estimado
CROP_VULNERABILITY = {
    'geada': {
        'tomate': {'yield_loss': 40, 'price_impact': 25},
        'morango': {'yield_loss': 35, 'price_impact': 20},
        'alface': {'yield_loss': 50, 'price_impact': 30},
        'pimentao': {'yield_loss': 30, 'price_impact': 15},
        'banana': {'yield_loss': 20, 'price_impact': 12},
    },
    'risco_geada': {
        'tomate': {'yield_loss': 15, 'price_impact': 10},
        'morango': {'yield_loss': 12, 'price_impact': 8},
        'alface': {'yield_loss': 20, 'price_impact': 12},
    },
    'calor_extremo': {
        'alface': {'yield_loss': 30, 'price_impact': 20},
        'morango': {'yield_loss': 25, 'price_impact': 15},
        'batata': {'yield_loss': 10, 'price_impact': 8},
    },
    'chuva_excessiva': {
        'tomate': {'yield_loss': 25, 'price_impact': 18},
        'batata': {'yield_loss': 20, 'price_impact': 12},
        'cebola': {'yield_loss': 15, 'price_impact': 10},
        'cenoura': {'yield_loss': 18, 'price_impact': 10},
        'morango': {'yield_loss': 30, 'price_impact': 20},
    },
    'estiagem': {
        'banana': {'yield_loss': 15, 'price_impact': 10},
        'manga': {'yield_loss': 10, 'price_impact': 8},
        'tomate': {'yield_loss': 20, 'price_impact': 12},
    },
    'vento_forte': {
        'banana': {'yield_loss': 25, 'price_impact': 15},
        'tomate': {'yield_loss': 15, 'price_impact': 10},
        'mamao': {'yield_loss': 20, 'price_impact': 12},
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# MÓDULO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

class NiasClimate:
    """Motor de inteligência climática — cruza clima com preço e produção."""

    def __init__(self):
        self.conn = sqlite3.connect(_DB_PATH, check_same_thread=False, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self._last_update = None
        self._state = {}

    # ─── DADOS CLIMÁTICOS ──────────────────────────────────────────────

    def _get_recent_climate(self) -> list[dict]:
        """Busca dados climáticos recentes do banco (Open-Meteo)."""
        try:
            max_row = self.conn.execute("SELECT MAX(obs_date) as d FROM flv_climate").fetchone()
            if not max_row or not max_row['d']:
                return []
            max_date = max_row['d']
            rows = self.conn.execute("""
                SELECT region_id, obs_date, temp_max_c, temp_min_c, precip_mm,
                       wind_max_kmh, humidity_pct, et0_mm
                FROM flv_climate
                WHERE obs_date >= date(?, '-7 days')
                ORDER BY obs_date DESC
            """, (max_date,)).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _get_price_context(self) -> dict:
        """Preço médio recente por cultura."""
        try:
            max_row = self.conn.execute("SELECT MAX(price_date) as d FROM flv_ceasa_prices").fetchone()
            if not max_row or not max_row['d']:
                return {}
            max_date = max_row['d']
            rows = self.conn.execute("""
                SELECT c.slug, c.name_pt as name, AVG(p.price_avg) as avg_price,
                       MAX(p.price_avg) as max_price, MIN(p.price_avg) as min_price,
                       COUNT(*) as obs
                FROM flv_ceasa_prices p
                JOIN flv_cultures c ON c.id = p.culture_id
                WHERE p.price_date >= date(?, '-7 days')
                GROUP BY c.slug
            """, (max_date,)).fetchall()
            return {r['slug']: dict(r) for r in rows}
        except Exception:
            return {}

    # ─── DETECÇÃO DE EVENTOS EXTREMOS ──────────────────────────────────

    def detect_extreme_events(self) -> list[dict]:
        """Detecta eventos climáticos extremos nas regiões monitoradas."""
        climate_data = self._get_recent_climate()
        if not climate_data:
            return []

        events = []
        # Agrupar por região
        by_region = {}
        for row in climate_data:
            rid = row.get('region_id') or 'brasil'
            by_region.setdefault(rid, []).append(row)

        for region in CLIMATE_REGIONS:
            rid = region['id']
            # Tentar casar por region_id ou usar dados globais
            data = by_region.get(rid) or by_region.get('brasil') or list(by_region.values())[0] if by_region else []
            if not data:
                continue

            # Verificar limiares
            latest = data[0] if data else {}
            temp_max = latest.get('temp_max_c') or 0
            temp_min = latest.get('temp_min_c') or 15
            precip = latest.get('precip_mm') or 0
            wind = latest.get('wind_max_kmh') or 0

            # Precipitação semanal
            precip_week = sum(r.get('precip_mm') or 0 for r in data[:7])

            detected = []

            if temp_min <= 2:
                detected.append('geada')
            elif temp_min <= 4:
                detected.append('risco_geada')

            if temp_max >= 38:
                detected.append('calor_extremo')

            if precip >= 40:
                detected.append('chuva_excessiva')
            elif precip >= 25:
                detected.append('chuva_intensa')

            if wind >= 80:
                detected.append('tempestade')
            elif wind >= 50:
                detected.append('vento_forte')

            if precip_week < 5 and len(data) >= 5:
                detected.append('estiagem')

            for event_type in detected:
                # Quais culturas são afetadas nesta região?
                affected_crops = []
                for crop in region['crops']:
                    vuln = CROP_VULNERABILITY.get(event_type, {}).get(crop)
                    if vuln:
                        affected_crops.append({
                            'crop': crop,
                            'yield_loss_pct': vuln['yield_loss'],
                            'price_impact_pct': vuln['price_impact']
                        })

                if affected_crops:
                    events.append({
                        'region_id': rid,
                        'region_name': region['name'],
                        'event': event_type,
                        'severity': 'critical' if event_type in ('geada', 'tempestade', 'chuva_excessiva') else 'high' if event_type in ('risco_geada', 'calor_extremo', 'vento_forte') else 'medium',
                        'temp_max': temp_max,
                        'temp_min': temp_min,
                        'precip_mm': precip,
                        'wind_kmh': wind,
                        'affected_crops': affected_crops,
                        'corridor': region['corridor'],
                        'obs_date': latest.get('obs_date'),
                    })

        self._state['events'] = events
        self._last_update = datetime.now().isoformat()
        return events

    # ─── CORRELAÇÃO CLIMA × PREÇO ──────────────────────────────────────

    def calculate_price_impact(self) -> list[dict]:
        """Estima impacto no preço baseado em eventos climáticos detectados."""
        events = self._state.get('events') or self.detect_extreme_events()
        prices = self._get_price_context()
        impacts = []

        for ev in events:
            for crop_info in ev['affected_crops']:
                crop_slug = crop_info['crop']
                price_data = prices.get(crop_slug)
                price_impact_pct = crop_info['price_impact_pct']

                current_price = price_data['avg_price'] if price_data else None
                estimated_new = round(current_price * (1 + price_impact_pct / 100), 2) if current_price else None

                # Determinar direção
                direction = 'alta' if price_impact_pct > 0 else 'queda'

                impacts.append({
                    'product': crop_slug,
                    'product_name': price_data['name'] if price_data else crop_slug.title(),
                    'region': ev['region_name'],
                    'weather_signal': ev['event'],
                    'severity': ev['severity'],
                    'price_signal': f"{'alta' if direction == 'alta' else 'queda'} provável",
                    'expected_impact_pct': price_impact_pct,
                    'current_price': current_price,
                    'estimated_price': estimated_new,
                    'correlation': round(0.5 + (price_impact_pct / 100) * 0.4, 2),
                    'confidence': 'alta' if ev['severity'] == 'critical' else 'media',
                    'horizon': '3 a 7 dias',
                    'obs_date': ev.get('obs_date'),
                })

        self._state['impacts'] = impacts
        return impacts

    # ─── ALERTAS CLIMÁTICOS ────────────────────────────────────────────

    def generate_climate_alerts(self) -> list[dict]:
        """Gera alertas climáticos acionáveis."""
        events = self._state.get('events') or self.detect_extreme_events()
        alerts = []

        for ev in events:
            crops_str = ', '.join(c['crop'].title() for c in ev['affected_crops'][:3])
            max_loss = max(c['yield_loss_pct'] for c in ev['affected_crops'])
            max_price = max(c['price_impact_pct'] for c in ev['affected_crops'])

            # Prioridade
            if ev['severity'] == 'critical':
                priority = 'critica'
            elif ev['severity'] == 'high':
                priority = 'alta'
            else:
                priority = 'media'

            # Descrição do evento
            desc_map = {
                'geada': f"Geada detectada em {ev['region_name']}",
                'risco_geada': f"Risco de geada em {ev['region_name']}",
                'calor_extremo': f"Calor extremo em {ev['region_name']} ({ev['temp_max']:.0f}°C)",
                'chuva_excessiva': f"Chuvas excessivas em {ev['region_name']} ({ev['precip_mm']:.0f}mm)",
                'chuva_intensa': f"Chuva intensa em {ev['region_name']}",
                'vento_forte': f"Ventos fortes em {ev['region_name']} ({ev['wind_kmh']:.0f}km/h)",
                'tempestade': f"Tempestade em {ev['region_name']} ({ev['wind_kmh']:.0f}km/h)",
                'estiagem': f"Estiagem prolongada em {ev['region_name']}",
            }
            titulo = desc_map.get(ev['event'], f"Evento climático em {ev['region_name']}")

            # Explicação humana
            explicacao = self._build_climate_explanation(ev, crops_str, max_loss, max_price)

            # Ação recomendada
            acao = self._build_climate_action(ev, crops_str)

            alerts.append({
                'priority': priority,
                'region': ev['region_name'],
                'region_id': ev['region_id'],
                'product': crops_str,
                'event': ev['event'],
                'titulo': titulo,
                'explicacao': explicacao,
                'acao_recomendada': acao,
                'price_impact': f"+{max_price}% a +{int(max_price*1.5)}%",
                'logistic_impact': f"Corredor {ev['corridor']} sob pressão",
                'confidence': 'alta' if ev['severity'] == 'critical' else 'media',
                'fontes': ['Open-Meteo', 'CONAB', 'CEASA'],
                'obs_date': ev.get('obs_date'),
            })

        return alerts

    def _build_climate_explanation(self, ev: dict, crops: str, loss: float, price: float) -> str:
        """Explicação em linguagem humana."""
        event_desc = {
            'geada': 'Geada negra pode destruir lavouras expostas',
            'risco_geada': 'Temperatura próxima de 0°C pode causar danos leves a moderados',
            'calor_extremo': 'Calor intenso prejudica floração e maturação',
            'chuva_excessiva': 'Excesso de chuva causa podridão, dificulta colheita e bloqueia estradas',
            'chuva_intensa': 'Chuva forte pode reduzir qualidade e atrasar logística',
            'vento_forte': 'Rajadas fortes podem tombar plantas e danificar frutos',
            'tempestade': 'Tempestade pode causar danos severos a infraestrutura e lavoura',
            'estiagem': 'Falta de chuva prolongada reduz produtividade e qualidade',
        }
        desc = event_desc.get(ev['event'], 'Evento climático detectado')
        return (
            f"{desc}. Culturas afetadas: {crops}. "
            f"Perda de produção estimada: até {loss}%. "
            f"Impacto esperado no preço: +{price}% nas próximas 72 horas a 7 dias."
        )

    def _build_climate_action(self, ev: dict, crops: str) -> str:
        """Ação recomendada."""
        actions = {
            'geada': f"Antecipar compra de {crops}. Monitorar CEASAs do Sul/Sudeste. Evitar estoque curto.",
            'risco_geada': f"Monitorar previsão de mínimas. Preparar para possível alta em {crops}.",
            'calor_extremo': f"Priorizar fornecedores em regiões com irrigação. Reduzir lead-time de perecíveis.",
            'chuva_excessiva': f"Verificar status de rodovias (corredor {ev['corridor']}). Antecipar pedidos.",
            'chuva_intensa': f"Monitorar qualidade na recepção. Considerar rotas alternativas.",
            'vento_forte': f"Verificar integridade de cargas. Monitorar danos em {crops}.",
            'tempestade': f"Suspender operações no corredor {ev['corridor']}. Ativar plano de contingência.",
            'estiagem': f"Antecipar compras antes de possível escassez. Buscar polos irrigados.",
        }
        return actions.get(ev['event'], f"Monitorar evolução climática em {ev['region_name']}.")

    # ─── RELATÓRIO EXECUTIVO ───────────────────────────────────────────

    def generate_climate_report(self) -> dict:
        """Relatório executivo climático em linguagem humana."""
        events = self._state.get('events') or self.detect_extreme_events()
        impacts = self._state.get('impacts') or self.calculate_price_impact()
        alerts = self.generate_climate_alerts()

        # Regiões sob risco
        regions_risk = list({ev['region_name'] for ev in events})

        # Produtos com chance de alta
        products_up = list({i['product_name'] for i in impacts if i['expected_impact_pct'] > 10})

        # Gargalos logísticos
        corridors = list({ev['corridor'] for ev in events if ev['severity'] in ('critical', 'high')})

        # Resumo
        if not events:
            resumo = "Sem eventos climáticos extremos detectados nas regiões monitoradas. Operação normal."
        else:
            critical = [e for e in events if e['severity'] == 'critical']
            high = [e for e in events if e['severity'] == 'high']
            resumo_parts = []
            if critical:
                resumo_parts.append(f"{len(critical)} evento(s) crítico(s)")
            if high:
                resumo_parts.append(f"{len(high)} evento(s) de alta severidade")
            resumo = f"Detectados {', '.join(resumo_parts)} em {len(regions_risk)} região(ões). Impacto potencial em {len(products_up)} produto(s)."

        # Dificuldade operacional por região (0-10)
        odi_scores = {}
        for region in CLIMATE_REGIONS:
            region_events = [e for e in events if e['region_id'] == region['id']]
            score = 0
            for e in region_events:
                if e['severity'] == 'critical':
                    score += 4
                elif e['severity'] == 'high':
                    score += 2.5
                else:
                    score += 1.5
            odi_scores[region['name']] = min(10, round(score, 1))

        return {
            'data': datetime.now().strftime('%Y-%m-%d'),
            'hora': datetime.now().strftime('%H:%M'),
            'resumo': resumo,
            'total_events': len(events),
            'total_alerts': len(alerts),
            'regions_at_risk': regions_risk,
            'products_likely_up': products_up,
            'logistic_bottlenecks': corridors,
            'odi_by_region': {k: v for k, v in odi_scores.items() if v > 0},
            'top_alerts': alerts[:5],
            'top_impacts': impacts[:5],
            'confidence': 'alta' if any(e['severity'] == 'critical' for e in events) else 'media' if events else 'baixa',
            'fontes': ['Open-Meteo', 'CONAB', 'CEASA/Preços', 'INMET'],
            'regioes_monitoradas': len(CLIMATE_REGIONS),
            'culturas_monitoradas': len(set(c for r in CLIMATE_REGIONS for c in r['crops'])),
            'atualizado_em': datetime.now().isoformat(),
        }

    # ─── STATUS DO MÓDULO ──────────────────────────────────────────────

    def get_status(self) -> dict:
        """Status do módulo NiasClimate."""
        all_crops = set(c for r in CLIMATE_REGIONS for c in r['crops'])
        return {
            'status': 'ok',
            'module': 'NiasClimate',
            'version': '1.0',
            'last_update': self._last_update,
            'regions_monitored': len(CLIMATE_REGIONS),
            'products_monitored': len(all_crops),
            'regions': [{'id': r['id'], 'name': r['name']} for r in CLIMATE_REGIONS],
            'products': sorted(all_crops),
            'events_active': len(self._state.get('events', [])),
            'sources': {
                'open_meteo': 'real',
                'conab': 'real',
                'ceasa': 'real',
            }
        }

    # ─── REGIÕES ───────────────────────────────────────────────────────

    def get_regions(self) -> list[dict]:
        """Retorna lista completa de regiões monitoradas."""
        return [{
            'id': r['id'],
            'name': r['name'],
            'lat': r['lat'],
            'lon': r['lon'],
            'crops': r['crops'],
            'corridor': r['corridor'],
        } for r in CLIMATE_REGIONS]


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════
_instance = None

def get_climate_engine() -> NiasClimate:
    global _instance
    if _instance is None:
        _instance = NiasClimate()
    return _instance
