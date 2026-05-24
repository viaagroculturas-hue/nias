"""
GrowthScorer - Algoritmo de Scoring de Crescimento
Módulo separado para cálculos de scoring e análise de crescimento
NIA$ Soberano Digital v5.0

Este módulo contém as classes e funções auxiliares para o GrowthRadar.
A classe principal GrowthScorer está implementada em growth_radar.py
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nia_flv.db')


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
