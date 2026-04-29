"""
GrowthScorer - Algoritmo de Scoring de Crescimento
Módulo separado para cálculos de scoring e análise de crescimento
NIA$ Soberano Digital v5.0

Este módulo contém as classes e funções auxiliares para o GrowthRadar.
A classe principal GrowthScorer está implementada em growth_radar.py
"""

import json
import math
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nia_flv.db')


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def calculate_delta_judicial_weight(
    ndvi_hydric_stress: float,
    rj_exposure_index: float,
    base_weight: float = 0.20,
) -> Dict[str, float]:
    """
    Dynamic Delta Judicial weight for Score Soberano v2.0.

    Severe hydric stress over a production/comarca cluster with high RJ density
    should dominate the judicial delta instead of behaving like a linear factor.
    """
    ndvi_hydric_stress = clamp(ndvi_hydric_stress)
    rj_exposure_index = clamp(rj_exposure_index)
    combined_pressure = clamp(ndvi_hydric_stress * rj_exposure_index)

    if ndvi_hydric_stress >= 0.70 and rj_exposure_index >= 0.60:
        weight = min(0.55, max(base_weight * 2.75, 0.45))
        trigger_level = 'disparo'
    elif combined_pressure >= 0.35:
        weight = min(0.40, base_weight * (1.0 + combined_pressure * 2.0))
        trigger_level = 'elevado'
    elif combined_pressure >= 0.15:
        weight = min(0.30, base_weight * (1.0 + combined_pressure))
        trigger_level = 'observacao'
    else:
        weight = base_weight
        trigger_level = 'normal'

    return {
        'weight': round(weight, 4),
        'pressure': round(combined_pressure, 4),
        'trigger_level': trigger_level,
        'ndvi_hydric_stress': round(ndvi_hydric_stress, 4),
        'rj_exposure_index': round(rj_exposure_index, 4),
    }


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _ndvi_stress(ndvi: float) -> float:
    return clamp((0.45 - float(ndvi or 0.55)) / 0.20)


@dataclass
class DeltaJudicialPressure:
    """Contexto de Delta Judicial usado pelo Score Soberano v2.0."""
    pressure: float
    weight: float
    trigger_level: str
    ndvi_hydric_stress: float
    rj_exposure_index: float
    rj_count_nearby: int
    nearest_rj_km: float


def assess_delta_judicial_pressure(
    city: Optional[str] = None,
    state_uf: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    db_path: str = DB_PATH,
) -> DeltaJudicialPressure:
    """
    Cruza estresse hídrico (NDVI/Open-Meteo proxy) com concentração de RJs.

    Se não houver coordenadas da empresa, usa o município/cidade como proxy da
    comarca ou do cluster de produção.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    state_uf = (state_uf or '').upper() or None
    if (lat is None or lon is None) and city:
        cursor.execute(
            """
            SELECT lat, lon FROM flv_municipalities
            WHERE lower(name)=lower(?) AND (? IS NULL OR state_uf=?)
            LIMIT 1
            """,
            (city, state_uf, state_uf),
        )
        mun = cursor.fetchone()
        if mun:
            lat, lon = mun['lat'], mun['lon']

    try:
        lat = float(lat) if lat is not None else None
        lon = float(lon) if lon is not None else None
    except Exception:
        lat, lon = None, None

    cursor.execute(
        """
        SELECT m.lat, m.lon, n.ndvi_value
        FROM flv_ndvi n
        JOIN flv_municipalities m ON m.id = n.mun_id
        WHERE (? IS NULL OR m.state_uf=?)
        ORDER BY n.obs_date DESC
        LIMIT 40
        """,
        (state_uf, state_uf),
    )
    ndvi_rows = cursor.fetchall()
    if lat is not None and lon is not None and ndvi_rows:
        nearest_ndvi = min(
            ndvi_rows,
            key=lambda r: _haversine_km(lat, lon, float(r['lat']), float(r['lon'])),
        )['ndvi_value']
    elif ndvi_rows:
        nearest_ndvi = sum(float(r['ndvi_value']) for r in ndvi_rows) / len(ndvi_rows)
    else:
        nearest_ndvi = 0.55

    cursor.execute(
        """
        SELECT lat, lon, judicial_status
        FROM flv_producers_rj
        WHERE status='ativo'
          AND judicial_status IN ('em_recuperacao', 'falencia')
          AND (? IS NULL OR state_uf=?)
          AND lat IS NOT NULL AND lon IS NOT NULL
        """,
        (state_uf, state_uf),
    )
    rj_rows = cursor.fetchall()
    conn.close()

    weighted = 0.0
    nearby = 0
    nearest = 999.0
    for r in rj_rows:
        status_weight = 1.0 if r['judicial_status'] == 'falencia' else 0.85
        if lat is not None and lon is not None:
            dist = _haversine_km(lat, lon, float(r['lat']), float(r['lon']))
            nearest = min(nearest, dist)
            if dist <= 180:
                nearby += 1
            geo_weight = math.exp(-dist / 120.0) if dist <= 350 else 0.0
        else:
            dist = 0.0
            nearest = 0.0
            nearby += 1
            geo_weight = 0.50
        weighted += status_weight * geo_weight

    rj_exposure_index = clamp(weighted / 3.0)
    ndvi_hydric_stress = _ndvi_stress(nearest_ndvi)
    weight_ctx = calculate_delta_judicial_weight(ndvi_hydric_stress, rj_exposure_index)
    return DeltaJudicialPressure(
        pressure=weight_ctx['pressure'],
        weight=weight_ctx['weight'],
        trigger_level=weight_ctx['trigger_level'],
        ndvi_hydric_stress=weight_ctx['ndvi_hydric_stress'],
        rj_exposure_index=weight_ctx['rj_exposure_index'],
        rj_count_nearby=nearby,
        nearest_rj_km=round(nearest, 2),
    )


@dataclass
class GrowthPrediction:
    """Predição de crescimento futuro"""
    company_cnpj: str
    predicted_growth_6m: float
    predicted_growth_12m: float
    confidence: float
    factors: Dict[str, float]
    scenario_optimistic: float
    scenario_pessimistic: float


class GrowthPredictor:
    """
    Preditor de crescimento futuro baseado em tendências.
    """
    
    def __init__(self):
        self.db_path = DB_PATH
    
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def predict_growth(self, cnpj: str) -> Optional[GrowthPrediction]:
        """
        Prediz crescimento futuro baseado em histórico e fatores de mercado.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM flv_growth_companies WHERE cnpj = ?
        """, (cnpj,))
        
        company = cursor.fetchone()
        if not company:
            conn.close()
            return None
        
        # Fatores de predição
        factors = self._calculate_factors(company)
        
        # Calcula projeções
        base_growth = company['growth_rate_12m']
        
        # Ajusta por fatores
        adjustment = (
            factors['market_momentum'] * 0.3 +
            factors['sector_outlook'] * 0.25 +
            factors['financial_health'] * 0.25 +
            factors['expansion_capacity'] * 0.2
        )
        
        predicted_6m = base_growth * (1 + adjustment) * 0.5  # 6 meses = metade do ciclo
        predicted_12m = base_growth * (1 + adjustment)
        
        # Cenários
        optimistic = predicted_12m * 1.3
        pessimistic = predicted_12m * 0.7
        
        # Confiança baseada em consistência histórica
        consistency = 1 - abs(company['growth_rate_12m'] - company['growth_rate_24m'] / 2)
        confidence = min(0.95, max(0.5, consistency + 0.3))
        
        conn.close()
        
        return GrowthPrediction(
            company_cnpj=cnpj,
            predicted_growth_6m=round(predicted_6m, 4),
            predicted_growth_12m=round(predicted_12m, 4),
            confidence=round(confidence, 4),
            factors=factors,
            scenario_optimistic=round(optimistic, 4),
            scenario_pessimistic=round(pessimistic, 4)
        )
    
    def _calculate_factors(self, company) -> Dict[str, float]:
        """Calcula fatores que influenciam crescimento futuro"""
        factors = {
            'market_momentum': 0.0,  # -1 a 1
            'sector_outlook': 0.0,
            'financial_health': 0.0,
            'expansion_capacity': 0.0
        }
        
        # Momento de mercado (baseado em tendência)
        if company['growth_rate_12m'] > company['growth_rate_24m'] / 2:
            factors['market_momentum'] = 0.2  # Aceleração
        else:
            factors['market_momentum'] = -0.1  # Desaceleração
        
        # Perspectiva do setor
        crisis_sectors = ['varejo_insumos', 'trading_graos']
        if company['segment'] in crisis_sectors:
            factors['sector_outlook'] = -0.3
        else:
            factors['sector_outlook'] = 0.1
        
        # Saúde financeira (proxy por crescimento consistente)
        consistency = 1 - abs(company['growth_rate_12m'] - company['growth_rate_24m'] / 2)
        factors['financial_health'] = consistency - 0.5
        
        # Capacidade de expansão
        market_expansion = json.loads(company['market_expansion'] or '[]')
        if len(market_expansion) >= 4:
            factors['expansion_capacity'] = 0.15  # Já expandiu muito
        elif len(market_expansion) >= 2:
            factors['expansion_capacity'] = 0.3   # Espaço para crescer
        else:
            factors['expansion_capacity'] = 0.5   # Grande potencial
        
        return factors


class GrowthBenchmark:
    """
    Benchmark de crescimento contra concorrentes e setor.
    """
    
    def __init__(self):
        self.db_path = DB_PATH
    
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def benchmark_company(self, cnpj: str) -> Optional[Dict]:
        """
        Compara empresa contra benchmarks do setor.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Busca empresa
        cursor.execute("""
            SELECT * FROM flv_growth_companies WHERE cnpj = ?
        """, (cnpj,))
        
        company = cursor.fetchone()
        if not company:
            conn.close()
            return None
        
        # Benchmarks do setor
        cursor.execute("""
            SELECT 
                AVG(growth_rate_12m) as avg_growth,
                PERCENTILE_75(growth_rate_12m) as p75_growth,
                PERCENTILE_90(growth_rate_12m) as p90_growth,
                MAX(growth_rate_12m) as max_growth,
                COUNT(*) as total_companies
            FROM flv_growth_companies 
            WHERE segment = ?
        """, (company['segment'],))
        
        # SQLite não tem PERCENTILE nativo, simula com AVG
        cursor.execute("""
            SELECT 
                AVG(growth_rate_12m) as avg_growth,
                AVG(revenue_current) as avg_revenue,
                COUNT(*) as total_companies
            FROM flv_growth_companies 
            WHERE segment = ?
        """, (company['segment'],))
        
        sector_avg = cursor.fetchone()
        
        # Ranking na cidade
        cursor.execute("""
            SELECT COUNT(*) + 1 as rank
            FROM flv_growth_companies 
            WHERE city = ? AND state_uf = ? 
            AND growth_rate_12m > ?
        """, (company['city'], company['state_uf'], company['growth_rate_12m']))
        
        city_rank = cursor.fetchone()['rank']
        
        # Ranking no estado
        cursor.execute("""
            SELECT COUNT(*) + 1 as rank
            FROM flv_growth_companies 
            WHERE state_uf = ? AND growth_rate_12m > ?
        """, (company['state_uf'], company['growth_rate_12m']))
        
        state_rank = cursor.fetchone()['rank']
        
        conn.close()
        
        company_growth = company['growth_rate_12m']
        avg_growth = sector_avg['avg_growth'] or 0
        
        return {
            'company_cnpj': cnpj,
            'company_name': company['company_name'],
            'segment': company['segment'],
            'metrics': {
                'growth_rate': company_growth,
                'revenue': company['revenue_current'],
                'employees': company['employees']
            },
            'sector_benchmarks': {
                'avg_growth_rate': avg_growth,
                'avg_revenue': sector_avg['avg_revenue'],
                'total_companies': sector_avg['total_companies']
            },
            'comparison': {
                'growth_vs_sector': company_growth - avg_growth,
                'growth_percentile': self._calculate_percentile(company_growth, company['segment']),
                'city_rank': city_rank,
                'state_rank': state_rank
            },
            'assessment': self._generate_assessment(company_growth, avg_growth)
        }
    
    def _calculate_percentile(self, growth_rate: float, segment: str) -> int:
        """Calcula percentil aproximado de crescimento"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT growth_rate_12m FROM flv_growth_companies 
            WHERE segment = ?
            ORDER BY growth_rate_12m
        """, (segment,))
        
        rates = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not rates:
            return 50
        
        # Conta quantos estão abaixo
        below = sum(1 for r in rates if r < growth_rate)
        return int((below / len(rates)) * 100)
    
    def _generate_assessment(self, company_growth: float, sector_avg: float) -> str:
        """Gera avaliação qualitativa"""
        diff = company_growth - sector_avg
        
        if diff > 0.15:
            return 'Crescimento Excepcional - Muito acima do setor'
        elif diff > 0.05:
            return 'Crescimento Forte - Acima do setor'
        elif diff > -0.05:
            return 'Crescimento Na Média do Setor'
        elif diff > -0.15:
            return 'Crescimento Abaixo do Setor - Atenção'
        else:
            return 'Crescimento Fraco - Requer Análise'


# Funções utilitárias para exportação de dados

def export_growth_report(format: str = 'json') -> str:
    """
    Exporta relatório de crescimento em formato especificado.
    """
    from growth_radar import GrowthRadar
    
    radar = GrowthRadar()
    summary = radar.get_growth_summary()
    
    if format == 'json':
        return json.dumps(summary, indent=2, default=str)
    elif format == 'csv':
        # Simplificado - em produção usar pandas
        lines = ['company_name,growth_rate_12m,segment,city,state']
        companies = radar.identify_high_growth_companies()
        for c in companies:
            lines.append(f"{c['company_name']},{c['growth_rate_12m']},{c['segment']},{c['city']},{c['state_uf']}")
        return '\n'.join(lines)
    
    return json.dumps(summary, default=str)


def get_investment_opportunities(min_growth: float = 0.20, max_risk: str = 'medio') -> List[Dict]:
    """
    Identifica oportunidades de investimento baseado em crescimento e risco.
    """
    from growth_radar import GrowthRadar
    
    radar = GrowthRadar()
    companies = radar.identify_high_growth_companies(min_growth)
    
    opportunities = []
    for company in companies:
        # Filtra por nível de risco
        risk_levels = {'baixo': 0, 'medio': 1, 'alto': 2, 'critico': 3}
        if risk_levels.get(company['sector_crisis_level'], 4) <= risk_levels.get(max_risk, 1):
            opportunities.append({
                'cnpj': company['cnpj'],
                'name': company['company_name'],
                'growth_rate': company['growth_rate_12m'],
                'revenue': company['revenue_current'],
                'segment': company['segment'],
                'city': company['city'],
                'state': company['state_uf'],
                'growth_score': company['growth_score']['score'],
                'risk_level': company['sector_crisis_level'],
                'recommendation': 'COMPRA' if company['growth_rate_12m'] > 0.25 else 'NEUTRO'
            })
    
    return sorted(opportunities, key=lambda x: x['growth_rate'], reverse=True)


if __name__ == '__main__':
    print("=== GrowthScorer - Algoritmos de Scoring NIA$ v5.0 ===\n")
    
    # Testa preditor
    predictor = GrowthPredictor()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT cnpj, company_name FROM flv_growth_companies LIMIT 3")
    companies = cursor.fetchall()
    conn.close()
    
    print("Predições de Crescimento:")
    for company in companies:
        pred = predictor.predict_growth(company['cnpj'])
        if pred:
            print(f"\n{company['company_name']}")
            print(f"  Predição 6m: {pred.predicted_growth_6m*100:.1f}%")
            print(f"  Predição 12m: {pred.predicted_growth_12m*100:.1f}%")
            print(f"  Confiança: {pred.confidence*100:.1f}%")
            print(f"  Cenário Otimista: {pred.scenario_optimistic*100:.1f}%")
            print(f"  Cenário Pessimista: {pred.scenario_pessimistic*100:.1f}%")
    
    # Testa benchmark
    print("\n\nBenchmarks:")
    benchmark = GrowthBenchmark()
    if companies:
        result = benchmark.benchmark_company(companies[0]['cnpj'])
        if result:
            print(f"\n{result['company_name']}")
            print(f"  Crescimento: {result['metrics']['growth_rate']*100:.1f}%")
            print(f"  Média do Setor: {result['sector_benchmarks']['avg_growth_rate']*100:.1f}%")
            print(f"  Diferença: {result['comparison']['growth_vs_sector']*100:.1f}%")
            print(f"  Ranking na Cidade: #{result['comparison']['city_rank']}")
            print(f"  Ranking no Estado: #{result['comparison']['state_rank']}")
            print(f"  Avaliação: {result['assessment']}")
    
    # Oportunidades de investimento
    print("\n\nOportunidades de Investimento:")
    opportunities = get_investment_opportunities()
    for opp in opportunities[:5]:
        print(f"\n{opp['name']}")
        print(f"  Crescimento: {opp['growth_rate']*100:.1f}%")
        print(f"  Score: {opp['growth_score']}")
        print(f"  Recomendação: {opp['recommendation']}")
