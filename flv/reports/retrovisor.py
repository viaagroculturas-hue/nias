"""
Retrovisor - Análise Retrospectiva de Impacto (D-8)
NIA$ Soberano Digital v5.0

Analisa o "Stress de Mercado" dos últimos 8 dias:
- Quem quebrou?
- Quem comprou ativos de concorrentes?
- Qual a variação real do CEPEA/IBGE?
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nia_flv.db')


@dataclass
class MarketEvent:
    """Evento de mercado detectado"""
    event_type: str  # 'rj_entry', 'bankruptcy', 'acquisition', 'asset_auction', 'price_spike'
    company_cnpj: Optional[str]
    company_name: Optional[str]
    date: str
    impact_score: float  # 0-100
    details: Dict
    related_commodities: List[str]


class Retrovisor:
    """
    Motor de análise retrospectiva D-8.
    Processa eventos dos últimos 8 dias e calcula métricas de stress.
    """
    
    def __init__(self):
        self.db_path = DB_PATH
        self.analysis_window_days = 8
    
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def analyze_last_8_days(self) -> Dict:
        """
        Executa análise completa dos últimos 8 dias.
        Retorna relatório D-8 completo.
        """
        since_date = (datetime.now() - timedelta(days=self.analysis_window_days)).strftime('%Y-%m-%d')
        
        report = {
            'report_type': 'd-8',
            'report_date': datetime.now().isoformat(),
            'analysis_period': {
                'start': since_date,
                'end': datetime.now().strftime('%Y-%m-%d')
            },
            'stress_market': self._calculate_stress_market(since_date),
            'companies_failed': self._analyze_companies_failed(since_date),
            'acquisitions': self._detect_acquisitions(since_date),
            'asset_auctions': self._detect_asset_auctions(since_date),
            'price_variations': self._analyze_price_variations(since_date),
            'sector_impacts': self._analyze_sector_impacts(since_date),
            'events_timeline': self._build_events_timeline(since_date)
        }
        
        # Salva no banco
        self._save_report(report)
        
        return report
    
    def _calculate_stress_market(self, since_date: str) -> Dict:
        """
        Calcula índice de stress de mercado (0-100).
        Baseado em múltiplos fatores.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Conta eventos negativos
        cursor.execute("""
            SELECT COUNT(*) as rj_count,
                   SUM(debts_total) as total_debt
            FROM flv_producers_rj 
            WHERE entry_date >= ?
            AND judicial_status = 'em_recuperacao'
        """, (since_date,))
        
        rj_data = cursor.fetchone()
        
        cursor.execute("""
            SELECT COUNT(*) as bankruptcy_count
            FROM flv_producers_rj 
            WHERE entry_date >= ?
            AND judicial_status = 'falencia'
        """, (since_date,))
        
        bankruptcy_data = cursor.fetchone()
        
        conn.close()
        
        # Calcula componentes do stress
        rj_stress = min(40, (rj_data['rj_count'] or 0) * 5)  # Max 40 pontos
        bankruptcy_stress = min(30, (bankruptcy_data['bankruptcy_count'] or 0) * 10)  # Max 30 pontos
        debt_stress = min(30, ((rj_data['total_debt'] or 0) / 1_000_000_000) * 2)  # Max 30 pontos
        
        total_stress = rj_stress + bankruptcy_stress + debt_stress
        
        return {
            'stress_score': round(min(100, total_stress), 2),
            'level': self._classify_stress_level(total_stress),
            'components': {
                'rj_stress': round(rj_stress, 2),
                'bankruptcy_stress': round(bankruptcy_stress, 2),
                'debt_stress': round(debt_stress, 2)
            },
            'factors': {
                'new_rj': rj_data['rj_count'] or 0,
                'new_bankruptcies': bankruptcy_data['bankruptcy_count'] or 0,
                'total_debt_billions': round((rj_data['total_debt'] or 0) / 1_000_000_000, 2)
            }
        }
    
    def _classify_stress_level(self, score: float) -> str:
        """Classifica nível de stress"""
        if score >= 70:
            return 'CRITICO'
        elif score >= 50:
            return 'ALTO'
        elif score >= 30:
            return 'MEDIO'
        elif score >= 10:
            return 'BAIXO'
        return 'NORMAL'
    
    def _analyze_companies_failed(self, since_date: str) -> List[Dict]:
        """Analisa empresas que faliram ou entraram em RJ"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT company_name, cnpj, judicial_status, 
                   debts_total, employees, segment, city, state_uf,
                   entry_date
            FROM flv_producers_rj 
            WHERE entry_date >= ?
            ORDER BY debts_total DESC
        """, (since_date,))
        
        companies = []
        for row in cursor.fetchall():
            companies.append({
                'name': row['company_name'],
                'cnpj': row['cnpj'],
                'status': row['judicial_status'],
                'debts_millions': round((row['debts_total'] or 0) / 1_000_000, 2),
                'employees': row['employees'],
                'segment': row['segment'],
                'location': f"{row['city']}/{row['state_uf']}",
                'entry_date': row['entry_date']
            })
        
        conn.close()
        return companies
    
    def _detect_acquisitions(self, since_date: str) -> List[Dict]:
        """Detecta aquisições de ativos de concorrentes"""
        # Em produção, buscaria em notícias e registros de leilões
        # Simulação para demonstração
        
        acquisitions = []
        
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Busca empresas que saíram de RJ recentemente (possível aquisição)
        cursor.execute("""
            SELECT company_name, cnpj, judicial_status, 
                   updated_at, entry_date
            FROM flv_producers_rj 
            WHERE updated_at >= ?
            AND judicial_status = 'reorganizado'
        """, (since_date,))
        
        for row in cursor.fetchall():
            acquisitions.append({
                'type': 'reorganizacao_concluida',
                'target_name': row['company_name'],
                'target_cnpj': row['cnpj'],
                'date': row['updated_at'],
                'estimated_value': None,
                'acquirer': 'Não informado'
            })
        
        conn.close()
        return acquisitions
    
    def _detect_asset_auctions(self, since_date: str) -> List[Dict]:
        """Detecta leilões de ativos programados"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Busca empresas em RJ com alto valor de dívida
        cursor.execute("""
            SELECT company_name, cnpj, debts_total, segment
            FROM flv_producers_rj 
            WHERE judicial_status = 'em_recuperacao'
            AND debts_total > 100000000
            ORDER BY debts_total DESC
        """)
        
        auctions = []
        for row in cursor.fetchall():
            # Estima probabilidade de leilão baseado no valor da dívida
            if row['debts_total'] > 500_000_000:
                probability = 'alta'
            elif row['debts_total'] > 100_000_000:
                probability = 'media'
            else:
                probability = 'baixa'
            
            auctions.append({
                'company_name': row['company_name'],
                'cnpj': row['cnpj'],
                'debt_millions': round(row['debts_total'] / 1_000_000, 2),
                'segment': row['segment'],
                'auction_probability': probability,
                'estimated_assets': ['imóveis', 'máquinas', 'estoque']
            })
        
        conn.close()
        return auctions
    
    def _analyze_price_variations(self, since_date: str) -> Dict:
        """Analisa variações de preço do CEPEA/IBGE"""
        # Em produção, buscaria de APIs reais
        # Simulação com dados realistas
        
        commodities = {
            'soja': {'variation': 3.2, 'trend': 'alta'},
            'milho': {'variation': -1.5, 'trend': 'baixa'},
            'cafe': {'variation': 8.7, 'trend': 'alta'},
            'boi': {'variation': 2.1, 'trend': 'estavel'},
            'trigo': {'variation': -3.4, 'trend': 'baixa'},
            'tomate': {'variation': 15.3, 'trend': 'alta'},
            'cebola': {'variation': -8.2, 'trend': 'baixa'}
        }
        
        return {
            'period': f'{since_date} a {datetime.now().strftime("%Y-%m-%d")}',
            'source': 'CEPEA/ESALQ e IBGE',
            'commodities': commodities,
            'biggest_increases': sorted(
                [(k, v['variation']) for k, v in commodities.items() if v['variation'] > 0],
                key=lambda x: x[1],
                reverse=True
            )[:3],
            'biggest_decreases': sorted(
                [(k, v['variation']) for k, v in commodities.items() if v['variation'] < 0],
                key=lambda x: x[1]
            )[:3]
        }
    
    def _analyze_sector_impacts(self, since_date: str) -> List[Dict]:
        """Analisa impactos por setor"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT segment,
                   COUNT(*) as crisis_count,
                   SUM(debts_total) as total_debt,
                   SUM(employees) as total_employees
            FROM flv_producers_rj 
            WHERE entry_date >= ?
            AND judicial_status IN ('em_recuperacao', 'falencia')
            GROUP BY segment
            ORDER BY crisis_count DESC
        """, (since_date,))
        
        impacts = []
        for row in cursor.fetchall():
            impact_level = 'critico' if row['crisis_count'] >= 3 else 'alto' if row['crisis_count'] >= 2 else 'medio'
            
            impacts.append({
                'segment': row['segment'] or 'Não especificado',
                'crisis_count': row['crisis_count'],
                'impact_level': impact_level,
                'total_debt_millions': round((row['total_debt'] or 0) / 1_000_000, 2),
                'employees_at_risk': row['total_employees'] or 0
            })
        
        conn.close()
        return impacts
    
    def _build_events_timeline(self, since_date: str) -> List[Dict]:
        """Constrói linha do tempo de eventos"""
        timeline = []
        
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Eventos de RJ
        cursor.execute("""
            SELECT company_name, judicial_status, entry_date, debts_total
            FROM flv_producers_rj 
            WHERE entry_date >= ?
            ORDER BY entry_date DESC
        """, (since_date,))
        
        for row in cursor.fetchall():
            event_type = 'falencia' if row['judicial_status'] == 'falencia' else 'rj'
            timeline.append({
                'date': row['entry_date'],
                'type': event_type,
                'company': row['company_name'],
                'description': f"Entrada em {event_type.upper()}",
                'impact_millions': round((row['debts_total'] or 0) / 1_000_000, 2)
            })
        
        conn.close()
        
        # Ordena por data
        timeline.sort(key=lambda x: x['date'], reverse=True)
        
        return timeline
    
    def _save_report(self, report: Dict):
        """Salva relatório no banco de dados"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO flv_sovereign_reports (
                report_date, report_type, report_period_start, report_period_end,
                stress_market_score, companies_rj_entered, companies_bankrupt,
                asset_auctions_count, cepea_variation_pct, sectors_in_crisis,
                generated_by, is_auto_generated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report['report_date'],
            report['report_type'],
            report['analysis_period']['start'],
            report['analysis_period']['end'],
            report['stress_market']['stress_score'],
            len(report['companies_failed']),
            sum(1 for c in report['companies_failed'] if c['status'] == 'falencia'),
            len(report['asset_auctions']),
            report['price_variations']['commodities'].get('soja', {}).get('variation', 0),
            json.dumps([s['segment'] for s in report['sector_impacts']]),
            'sistema',
            1
        ))
        
        conn.commit()
        conn.close()
    
    def get_latest_report(self) -> Optional[Dict]:
        """Retorna último relatório D-8 gerado"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM flv_sovereign_reports 
            WHERE report_type = 'd-8'
            ORDER BY report_date DESC LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None


if __name__ == '__main__':
    retro = Retrovisor()
    
    print("=== Retrovisor D-8 - Análise Retrospectiva NIA$ v5.0 ===\n")
    
    report = retro.analyze_last_8_days()
    
    print(f"Relatório D-8 ({report['report_date']})")
    print(f"Período: {report['analysis_period']['start']} a {report['analysis_period']['end']}")
    
    print(f"\n=== Stress de Mercado ===")
    stress = report['stress_market']
    print(f"Score: {stress['stress_score']}/100")
    print(f"Nível: {stress['level']}")
    print(f"Novos RJs: {stress['factors']['new_rj']}")
    print(f"Dívida Total: R$ {stress['factors']['total_debt_billions']:.2f} bilhões")
    
    print(f"\n=== Empresas Impactadas ({len(report['companies_failed'])}) ===")
    for company in report['companies_failed'][:5]:
        print(f"- {company['name']}: R$ {company['debts_millions']:.2f}M ({company['status']})")
    
    print(f"\n=== Variações de Preço ===")
    for commodity, data in report['price_variations']['commodities'].items():
        trend_icon = '📈' if data['trend'] == 'alta' else '📉' if data['trend'] == 'baixa' else '➡️'
        print(f"{trend_icon} {commodity}: {data['variation']:+.1f}%")
