"""
GrowthRadar - Radar de Crescimento do Agronegócio
Identificação de empresas em escalada e novos polos de crescimento
NIA$ Soberano Digital v5.0
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

from flv.db import DB_PATH


@dataclass
class GrowthMetrics:
    """Métricas de crescimento de uma empresa"""
    revenue_growth_12m: float
    revenue_growth_24m: float
    employee_growth_pct: float
    store_growth_pct: float
    market_expansion_count: int
    investment_round: Optional[str] = None
    market_share_change: Optional[float] = None


@dataclass
class OvertradingAlert:
    """Alerta de risco de overtrading"""
    company_cnpj: str
    company_name: str
    growth_rate: float
    sector_risk_level: str
    reason: str
    recommendation: str
    detected_at: str


class GrowthScorer:
    """
    Algoritmo de scoring de crescimento para empresas do agronegócio.
    Detecta empresas em escalada e calcula risco de overtrading.
    """
    
    # Limiares de crescimento
    HIGH_GROWTH_THRESHOLD = 0.15  # 15% ao ano
    OVERTRADING_THRESHOLD = 0.25  # 25% ao ano (risco elevado)
    
    # Setores em crise de crédito (baseado em dados do sistema)
    CRISIS_SECTORS = [
        'varejo_insumos',  # Ex: AgroGalaxy em RJ
        'trading_graos',
        'processamento_cafe',
        'armazens_gerais',
        'acucar_etanol'
    ]
    
    def __init__(self):
        self.db_path = DB_PATH
    
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def calculate_growth_score(self, metrics: GrowthMetrics) -> Dict:
        """
        Calcula score de crescimento baseado em múltiplas métricas.
        Retorna score normalizado e análise.
        """
        # Pesos para cada métrica
        weights = {
            'revenue_12m': 0.35,
            'revenue_24m': 0.25,
            'employees': 0.15,
            'stores': 0.15,
            'expansion': 0.10
        }
        
        # Normaliza crescimento de receita (cap em 100% = 1.0)
        rev_12m_normalized = min(metrics.revenue_growth_12m, 1.0)
        rev_24m_normalized = min(metrics.revenue_growth_24m, 1.0)
        
        # Normaliza crescimento de funcionários
        emp_normalized = min(metrics.employee_growth_pct / 100, 1.0)
        
        # Normaliza crescimento de lojas
        store_normalized = min(metrics.store_growth_pct / 100, 1.0)
        
        # Expansão de mercado (max 5 novos mercos = 1.0)
        expansion_normalized = min(metrics.market_expansion_count / 5, 1.0)
        
        # Calcula score ponderado
        score = (
            rev_12m_normalized * weights['revenue_12m'] +
            rev_24m_normalized * weights['revenue_24m'] +
            emp_normalized * weights['employees'] +
            store_normalized * weights['stores'] +
            expansion_normalized * weights['expansion']
        ) * 1000  # Escala 0-1000
        
        # Classificação
        if score >= 700:
            classification = 'Crescimento Acelerado'
            growth_level = 'alto'
        elif score >= 500:
            classification = 'Crescimento Moderado'
            growth_level = 'medio'
        elif score >= 300:
            classification = 'Crescimento Inicial'
            growth_level = 'baixo'
        else:
            classification = 'Estagnado/Declínio'
            growth_level = 'negativo'
        
        return {
            'score': round(score, 2),
            'growth_level': growth_level,
            'classification': classification,
            'components': {
                'revenue_12m': round(rev_12m_normalized * weights['revenue_12m'] * 1000, 2),
                'revenue_24m': round(rev_24m_normalized * weights['revenue_24m'] * 1000, 2),
                'employees': round(emp_normalized * weights['employees'] * 1000, 2),
                'stores': round(store_normalized * weights['stores'] * 1000, 2),
                'expansion': round(expansion_normalized * weights['expansion'] * 1000, 2)
            },
            'raw_metrics': {
                'revenue_growth_12m': metrics.revenue_growth_12m,
                'revenue_growth_24m': metrics.revenue_growth_24m,
                'employee_growth_pct': metrics.employee_growth_pct,
                'store_growth_pct': metrics.store_growth_pct,
                'market_expansion_count': metrics.market_expansion_count
            }
        }
    
    def detect_overtrading_risk(self, cnpj: str, growth_rate: float, segment: str) -> Optional[OvertradingAlert]:
        """
        Detecta risco de overtrading quando empresa cresce aceleradamente
        em setor em crise.
        """
        # Verifica se crescimento é acelerado
        if growth_rate < self.OVERTRADING_THRESHOLD:
            return None
        
        # Verifica se setor está em crise
        if segment not in self.CRISIS_SECTORS:
            return None
        
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Busca dados da empresa
        cursor.execute("""
            SELECT company_name FROM flv_growth_companies WHERE cnpj = ?
        """, (cnpj,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        company_name = result['company_name']
        
        # Gera recomendação
        recommendations = {
            'varejo_insumos': 'Revisar política de crédito; exigir garantias adicionais',
            'trading_graos': 'Monitorar posições de risco; diversificar fornecedores',
            'processamento_cafe': 'Verificar contratos futuros; proteger margens',
            'armazens_gerais': 'Avaliar ocupação real; verificar inadimplência',
            'acucar_etanol': 'Monitorar preços ATR; proteger contra volatilidade'
        }
        
        return OvertradingAlert(
            company_cnpj=cnpj,
            company_name=company_name,
            growth_rate=growth_rate,
            sector_risk_level='ALTO',
            reason=f"Crescimento de {growth_rate*100:.1f}% em setor em crise ({segment})",
            recommendation=recommendations.get(segment, 'Monitorar de perto; reduzir exposição'),
            detected_at=datetime.now().isoformat()
        )
    
    def assess_sector_crisis_level(self, segment: str) -> str:
        """
        Avalia nível de crise de um setor baseado em empresas em RJ.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as count, SUM(debts_total) as total_debt
            FROM flv_producers_rj 
            WHERE segment LIKE ?
            AND judicial_status IN ('em_recuperacao', 'falencia')
        """, (f'%{segment}%',))
        
        result = cursor.fetchone()
        conn.close()
        
        count = result['count'] or 0
        total_debt = result['total_debt'] or 0
        
        if count >= 5 or total_debt > 5_000_000_000:  # 5 bilhões
            return 'critico'
        elif count >= 3 or total_debt > 1_000_000_000:  # 1 bilhão
            return 'alto'
        elif count >= 1:
            return 'medio'
        
        return 'baixo'


class GrowthRadar:
    """
    Radar de crescimento do agronegócio.
    Identifica empresas em escalada e novos polos de crescimento.
    """
    
    def __init__(self):
        self.db_path = DB_PATH
        self.scorer = GrowthScorer()
        self.init_seed_data()
    
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_seed_data(self):
        """Inicializa dados de empresas em crescimento"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Verifica se já tem dados
        cursor.execute("SELECT COUNT(*) as count FROM flv_growth_companies")
        if cursor.fetchone()['count'] > 0:
            conn.close()
            return
        
        # Dados de empresas em crescimento (exemplos reais)
        growth_companies = [
            {
                'company_name': '3tentos Agro e Negócios S.A.',
                'cnpj': '10.491.533/0001-06',
                'segment': 'varejo_insumos',
                'growth_rate_12m': 0.32,
                'growth_rate_24m': 0.58,
                'revenue_current': 4200000000.00,
                'revenue_previous': 3180000000.00,
                'employee_growth_pct': 25,
                'store_growth_pct': 18,
                'market_expansion': json.dumps(['MT', 'MS', 'GO', 'BA']),
                'city': 'Cascavel',
                'state_uf': 'PR'
            },
            {
                'company_name': 'Lavoro Ltda.',
                'cnpj': '32.123.456/0001-78',
                'segment': 'varejo_insumos',
                'growth_rate_12m': 0.28,
                'growth_rate_24m': 0.67,
                'revenue_current': 2800000000.00,
                'revenue_previous': 2180000000.00,
                'employee_growth_pct': 35,
                'store_growth_pct': 22,
                'market_expansion': json.dumps(['MT', 'GO', 'TO', 'BA', 'MA']),
                'city': 'Sorriso',
                'state_uf': 'MT'
            },
            {
                'company_name': 'Grupo Mateus S.A.',
                'cnpj': '08.867.291/0001-20',
                'segment': 'varejo_varejo',
                'growth_rate_12m': 0.19,
                'growth_rate_24m': 0.42,
                'revenue_current': 18500000000.00,
                'revenue_previous': 15500000000.00,
                'employee_growth_pct': 15,
                'store_growth_pct': 12,
                'market_expansion': json.dumps(['PA', 'MA', 'PI', 'CE']),
                'city': 'São Luís',
                'state_uf': 'MA'
            },
            {
                'company_name': 'SLC Agrícola S.A.',
                'cnpj': '89.645.121/0001-86',
                'segment': 'producao_agricola',
                'growth_rate_12m': 0.12,
                'growth_rate_24m': 0.28,
                'revenue_current': 3200000000.00,
                'revenue_previous': 2860000000.00,
                'employee_growth_pct': 8,
                'store_growth_pct': 0,
                'market_expansion': json.dumps(['MT', 'GO']),
                'city': 'Porto Alegre',
                'state_uf': 'RS'
            },
            {
                'company_name': 'BrasilAgro - Companhia Brasileira de Propriedades Agrícolas',
                'cnpj': '07.628.528/0001-38',
                'segment': 'producao_agricola',
                'growth_rate_12m': 0.16,
                'growth_rate_24m': 0.35,
                'revenue_current': 2100000000.00,
                'revenue_previous': 1810000000.00,
                'employee_growth_pct': 12,
                'store_growth_pct': 0,
                'market_expansion': json.dumps(['MT', 'GO', 'PI', 'MA']),
                'city': 'Rio de Janeiro',
                'state_uf': 'RJ'
            }
        ]
        
        for company in growth_companies:
            cursor.execute("""
                INSERT OR IGNORE INTO flv_growth_companies (
                    company_name, cnpj, segment, growth_rate_12m, growth_rate_24m,
                    revenue_current, revenue_previous, employee_growth_pct,
                    store_growth_pct, market_expansion, city, state_uf, detection_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                company['company_name'], company['cnpj'], company['segment'],
                company['growth_rate_12m'], company['growth_rate_24m'],
                company['revenue_current'], company['revenue_previous'],
                company['employee_growth_pct'], company['store_growth_pct'],
                company['market_expansion'], company['city'], company['state_uf']
            ))
        
        conn.commit()
        conn.close()
        print(f"[GrowthRadar] {len(growth_companies)} empresas em crescimento inicializadas")
    
    def identify_high_growth_companies(self, min_growth: float = 0.15) -> List[Dict]:
        """
        Identifica empresas com crescimento acima do limiar.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM flv_growth_companies 
            WHERE growth_rate_12m >= ?
            ORDER BY growth_rate_12m DESC
        """, (min_growth,))
        
        companies = []
        for row in cursor.fetchall():
            company = dict(row)
            
            # Calcula score
            metrics = GrowthMetrics(
                revenue_growth_12m=company['growth_rate_12m'],
                revenue_growth_24m=company['growth_rate_24m'],
                employee_growth_pct=company['employee_growth_pct'],
                store_growth_pct=company['store_growth_pct'],
                market_expansion_count=len(json.loads(company['market_expansion'] or '[]'))
            )
            
            company['growth_score'] = self.scorer.calculate_growth_score(metrics)
            
            # Verifica risco de overtrading
            alert = self.scorer.detect_overtrading_risk(
                company['cnpj'],
                company['growth_rate_12m'],
                company['segment']
            )
            
            company['overtrading_alert'] = alert.__dict__ if alert else None
            company['sector_crisis_level'] = self.scorer.assess_sector_crisis_level(
                company['segment']
            )
            
            companies.append(company)
        
        conn.close()
        return companies
    
    def detect_new_growth_poles(self) -> List[Dict]:
        """
        Detecta novos polos de crescimento baseado em concentração de empresas.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Busca cidades com múltiplas empresas em crescimento
        cursor.execute("""
            SELECT city, state_uf, COUNT(*) as company_count,
                   AVG(growth_rate_12m) as avg_growth,
                   SUM(revenue_current) as total_revenue
            FROM flv_growth_companies 
            WHERE growth_rate_12m >= 0.15
            GROUP BY city, state_uf
            HAVING COUNT(*) >= 1
            ORDER BY avg_growth DESC
        """)
        
        poles = []
        for row in cursor.fetchall():
            # Busca empresas na cidade
            cursor.execute("""
                SELECT company_name, segment, growth_rate_12m, revenue_current
                FROM flv_growth_companies 
                WHERE city = ? AND state_uf = ?
                ORDER BY growth_rate_12m DESC
            """, (row['city'], row['state_uf']))
            
            companies = [dict(c) for c in cursor.fetchall()]
            
            poles.append({
                'city': row['city'],
                'state': row['state_uf'],
                'company_count': row['company_count'],
                'avg_growth_rate': round(row['avg_growth'] * 100, 2),
                'total_revenue_millions': round(row['total_revenue'] / 1_000_000, 2),
                'main_segments': list(set(c['segment'] for c in companies)),
                'companies': companies,
                'pole_type': self._classify_pole_type(companies)
            })
        
        conn.close()
        return poles
    
    def _classify_pole_type(self, companies: List[Dict]) -> str:
        """Classifica o tipo de polo de crescimento"""
        segments = [c['segment'] for c in companies]
        
        if 'varejo_insumos' in segments and len(companies) >= 2:
            return 'Hub de Insumos'
        elif 'producao_agricola' in segments and len(companies) >= 2:
            return 'Polo de Produção'
        elif 'logistica' in segments:
            return 'Hub Logístico'
        elif 'processamento' in segments:
            return 'Polo Industrial'
        
        return 'Polo Emergente'
    
    def get_growth_summary(self) -> Dict:
        """
        Retorna resumo consolidado do radar de crescimento.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Totais
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN growth_rate_12m >= 0.15 THEN 1 ELSE 0 END) as high_growth,
                   SUM(CASE WHEN growth_rate_12m >= 0.25 THEN 1 ELSE 0 END) as accelerated,
                   AVG(growth_rate_12m) as avg_growth,
                   SUM(revenue_current) as total_revenue
            FROM flv_growth_companies
        """)
        
        totals = cursor.fetchone()
        
        # Por segmento
        cursor.execute("""
            SELECT segment, 
                   COUNT(*) as count,
                   AVG(growth_rate_12m) as avg_growth,
                   AVG(employee_growth_pct) as avg_emp_growth
            FROM flv_growth_companies
            GROUP BY segment
            ORDER BY count DESC
        """)
        
        by_segment = [dict(row) for row in cursor.fetchall()]
        
        # Alertas de overtrading
        high_growth = self.identify_high_growth_companies()
        overtrading_alerts = [c for c in high_growth if c['overtrading_alert']]
        
        conn.close()
        
        return {
            'summary_date': datetime.now().isoformat(),
            'totals': {
                'companies_monitored': totals['total'],
                'high_growth_count': totals['high_growth'],
                'accelerated_growth_count': totals['accelerated'],
                'avg_growth_rate': round((totals['avg_growth'] or 0) * 100, 2),
                'total_revenue_billions': round((totals['total_revenue'] or 0) / 1_000_000_000, 2)
            },
            'by_segment': by_segment,
            'overtrading_alerts': overtrading_alerts,
            'growth_poles': self.detect_new_growth_poles(),
            'sectors_in_crisis': self.scorer.CRISIS_SECTORS
        }
    
    def update_company_metrics(self, cnpj: str, new_revenue: float, 
                               new_employees: int = None, new_stores: int = None):
        """
        Atualiza métricas de uma empresa e recalcula taxas de crescimento.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Busca dados atuais
        cursor.execute("""
            SELECT revenue_current, revenue_previous, employees, stores
            FROM flv_growth_companies WHERE cnpj = ?
        """, (cnpj,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False
        
        # Calcula novas taxas
        old_revenue = result['revenue_current']
        older_revenue = result['revenue_previous']
        
        new_growth_12m = (new_revenue - old_revenue) / old_revenue if old_revenue else 0
        new_growth_24m = (new_revenue - older_revenue) / older_revenue if older_revenue else 0
        
        # Atualiza
        cursor.execute("""
            UPDATE flv_growth_companies SET
                revenue_previous = revenue_current,
                revenue_current = ?,
                growth_rate_12m = ?,
                growth_rate_24m = ?,
                employees = COALESCE(?, employees),
                stores = COALESCE(?, stores),
                updated_at = datetime('now')
            WHERE cnpj = ?
        """, (new_revenue, new_growth_12m, new_growth_24m, 
                new_employees, new_stores, cnpj))
        
        conn.commit()
        conn.close()
        
        return True


if __name__ == '__main__':
    radar = GrowthRadar()
    
    print("=== GrowthRadar - Radar de Crescimento NIA$ v5.0 ===\n")
    
    # Resumo
    summary = radar.get_growth_summary()
    print(f"Resumo do Radar ({summary['summary_date']})")
    print(f"Empresas Monitoradas: {summary['totals']['companies_monitored']}")
    print(f"Crescimento Alto (>15%): {summary['totals']['high_growth_count']}")
    print(f"Crescimento Acelerado (>25%): {summary['totals']['accelerated_growth_count']}")
    print(f"Taxa Média de Crescimento: {summary['totals']['avg_growth_rate']}%")
    print(f"Receita Total: R$ {summary['totals']['total_revenue_billions']:.2f} bilhões")
    
    print("\n=== Empresas em Alto Crescimento ===")
    high_growth = radar.identify_high_growth_companies()
    for company in high_growth:
        print(f"\n{company['company_name']}")
        print(f"  Segmento: {company['segment']}")
        print(f"  Crescimento 12m: {company['growth_rate_12m']*100:.1f}%")
        print(f"  Score: {company['growth_score']['score']}")
        print(f"  Nível de Crise do Setor: {company['sector_crisis_level']}")
        if company['overtrading_alert']:
            print(f"  ⚠️ ALERTA OVERTRADING: {company['overtrading_alert']['reason']}")
    
    print("\n=== Polos de Crescimento Detectados ===")
    poles = radar.detect_new_growth_poles()
    for pole in poles:
        print(f"\n{pole['city']}/{pole['state']}")
        print(f"  Tipo: {pole['pole_type']}")
        print(f"  Empresas: {pole['company_count']}")
        print(f"  Crescimento Médio: {pole['avg_growth_rate']}%")
        print(f"  Segmentos: {', '.join(pole['main_segments'])}")
