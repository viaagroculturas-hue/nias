"""
CrisisWatch - Módulo de Vigilância de Crise
Rastreamento de Recuperações Judiciais e Falências no Agronegócio
NIA$ Soberano Digital v5.0
"""

import json
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import urllib.request
import urllib.parse
import re
from dataclasses import dataclass

# Garante que o banco seja encontrado independente de onde o script é executado
if getattr(sys, 'frozen', False):
    # Executando como executável
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Executando como script
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(BASE_DIR, 'nia_flv.db')

@dataclass
class JudicialProcess:
    """Representa um processo judicial (RJ ou Falência)"""
    cnpj: str
    company_name: str
    process_number: str
    court: str
    process_type: str  # 'rj', 'falencia', 'recuperacao_extraordinaria'
    status: str
    entry_date: str
    debt_amount: Optional[float] = None
    employees_affected: Optional[int] = None
    main_activity: Optional[str] = None
    last_update: Optional[str] = None


class CrisisWatch:
    """
    Motor de vigilância de crise para o agronegócio.
    Monitora RJs, falências e mudanças de status judicial.
    """
    
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()
        
    def get_conn(self):
        """Obtém conexão com o banco de dados"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Garante que as tabelas necessárias existam"""
        # A tabela já é criada pelo flv_schema.sql
        pass
    
    def check_new_rj(self) -> List[Dict]:
        """
        Verifica novos processos de RJ em fontes públicas.
        Retorna lista de processos detectados.
        """
        new_processes = []
        
        # Simulação: Em produção, isso faria scraping de diários oficiais
        # e APIs de tribunais (TJSP, TJMG, etc.)
        
        # Busca empresas que entraram em RJ nos últimos 7 dias
        conn = self.get_conn()
        cursor = conn.cursor()
        
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT * FROM flv_producers_rj 
            WHERE entry_date >= ? 
            AND judicial_status = 'em_recuperacao'
            ORDER BY entry_date DESC
        """, (seven_days_ago,))
        
        rows = cursor.fetchall()
        
        for row in rows:
            new_processes.append({
                'cnpj': row['cnpj'],
                'company_name': row['company_name'],
                'process_number': row['process_number'],
                'court': row['court'],
                'entry_date': row['entry_date'],
                'debts_total': row['debts_total'],
                'employees': row['employees'],
                'city': row['city'],
                'state_uf': row['state_uf']
            })
        
        conn.close()
        return new_processes
    
    def calculate_credit_score(self, cnpj: str) -> Dict:
        """
        Calcula score de crédito 2026 baseado em histórico judicial.
        Retorna score de 0 a 1000 e análise.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM flv_producers_rj 
            WHERE cnpj = ?
        """, (cnpj,))
        
        company = cursor.fetchone()
        
        if not company:
            conn.close()
            return {
                'cnpj': cnpj,
                'score': None,
                'status': 'not_found',
                'message': 'Empresa não encontrada no monitoramento'
            }
        
        # Algoritmo de scoring simplificado
        base_score = 500
        
        # Penalidades por status judicial
        status_penalties = {
            'em_recuperacao': -200,
            'recuperacao_aprovada': -150,
            'falencia': -400,
            'reorganizado': -100
        }
        
        score = base_score + status_penalties.get(company['judicial_status'], 0)
        
        # Penalidade por volume de dívida
        if company['debts_total']:
            if company['debts_total'] > 1_000_000_000:  # > 1 bilhão
                score -= 150
            elif company['debts_total'] > 500_000_000:  # > 500 milhões
                score -= 100
            elif company['debts_total'] > 100_000_000:  # > 100 milhões
                score -= 50
        
        # Histórico de 24 meses
        history = self._get_credit_history_24m(cnpj)
        
        # Se tem histórico de recuperação anterior
        if history and len(history) > 1:
            score -= 100  # Reincidente
        
        score = max(0, min(1000, score))  # Limita entre 0 e 1000
        
        # Classificação de risco
        if score >= 700:
            risk_level = 'baixo'
            classification = 'Risco Baixo - Monitorar'
        elif score >= 500:
            risk_level = 'medio'
            classification = 'Risco Médio - Atenção'
        elif score >= 300:
            risk_level = 'alto'
            classification = 'Risco Alto - Cautela'
        else:
            risk_level = 'critico'
            classification = 'Risco Crítico - Evitar'
        
        # Atualiza score no banco
        cursor.execute("""
            UPDATE flv_producers_rj 
            SET credit_score_2026 = ?,
                credit_history_24m = ?,
                updated_at = datetime('now')
            WHERE cnpj = ?
        """, (score, json.dumps(history), cnpj))
        
        conn.commit()
        conn.close()
        
        return {
            'cnpj': cnpj,
            'company_name': company['company_name'],
            'score': score,
            'risk_level': risk_level,
            'classification': classification,
            'status': company['judicial_status'],
            'debts_total': company['debts_total'],
            'history_24m': history,
            'factors': {
                'status_penalty': status_penalties.get(company['judicial_status'], 0),
                'debt_penalty': self._calculate_debt_penalty(company['debts_total']),
                'reincidence_penalty': -100 if history and len(history) > 1 else 0
            }
        }
    
    def _get_credit_history_24m(self, cnpj: str) -> List[Dict]:
        """Retorna histórico de crédito dos últimos 24 meses"""
        # Simulação: em produção, buscaria de SERASA/SPC
        history = []
        
        # Gera dados simulados para demonstração
        for i in range(24):
            month = (datetime.now() - timedelta(days=30*i)).strftime('%Y-%m')
            # Simula deterioração gradual do score
            base = 700 - (i * 10)
            history.append({
                'month': month,
                'score': max(300, base),
                'inquiries': max(0, 5 - i//3),  # Consultas diminuem com tempo
                'delays': max(0, 3 - i//6) if i < 12 else 0  # Atrasos históricos
            })
        
        return history
    
    def _calculate_debt_penalty(self, debt: Optional[float]) -> int:
        """Calcula penalidade baseada no valor da dívida"""
        if not debt:
            return 0
        if debt > 1_000_000_000:
            return -150
        elif debt > 500_000_000:
            return -100
        elif debt > 100_000_000:
            return -50
        return 0
    
    def get_crisis_summary(self) -> Dict:
        """
        Retorna resumo da crise atual no agronegócio.
        Métricas consolidadas para o dashboard.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Total em recuperação judicial
        cursor.execute("""
            SELECT COUNT(*) as count, SUM(debts_total) as total_debt,
                   SUM(employees) as total_employees
            FROM flv_producers_rj 
            WHERE judicial_status = 'em_recuperacao'
        """)
        rj_data = cursor.fetchone()
        
        # Falências
        cursor.execute("""
            SELECT COUNT(*) as count, SUM(debts_total) as total_debt
            FROM flv_producers_rj 
            WHERE judicial_status = 'falencia'
        """)
        falencia_data = cursor.fetchone()
        
        # Por estado
        cursor.execute("""
            SELECT state_uf, COUNT(*) as count, SUM(debts_total) as debt
            FROM flv_producers_rj 
            WHERE judicial_status IN ('em_recuperacao', 'falencia')
            GROUP BY state_uf
            ORDER BY count DESC
        """)
        by_state = [dict(row) for row in cursor.fetchall()]
        
        # Por setor/segmento
        cursor.execute("""
            SELECT segment, COUNT(*) as count, SUM(debts_total) as debt
            FROM flv_producers_rj 
            WHERE judicial_status IN ('em_recuperacao', 'falencia')
            AND segment IS NOT NULL
            GROUP BY segment
            ORDER BY count DESC
        """)
        by_segment = [dict(row) for row in cursor.fetchall()]
        
        # Últimas entradas (7 dias)
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT company_name, cnpj, judicial_status, entry_date, debts_total, segment
            FROM flv_producers_rj 
            WHERE entry_date >= ?
            ORDER BY entry_date DESC
            LIMIT 10
        """, (seven_days_ago,))
        recent_entries = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        total_crisis_debt = (rj_data['total_debt'] or 0) + (falencia_data['total_debt'] or 0)
        
        return {
            'summary_date': datetime.now().isoformat(),
            'totals': {
                'in_rj': rj_data['count'] or 0,
                'bankrupt': falencia_data['count'] or 0,
                'total_companies': (rj_data['count'] or 0) + (falencia_data['count'] or 0),
                'total_debt_billions': round(total_crisis_debt / 1_000_000_000, 2),
                'employees_at_risk': rj_data['total_employees'] or 0
            },
            'by_state': by_state,
            'by_segment': by_segment,
            'recent_entries': recent_entries,
            'alert_level': self._calculate_alert_level(
                rj_data['count'] or 0, 
                total_crisis_debt
            )
        }
    
    def _calculate_alert_level(self, rj_count: int, total_debt: float) -> str:
        """Calcula nível de alerta baseado em métricas"""
        if rj_count > 50 or total_debt > 100_000_000_000:  # 100 bilhões
            return 'CRITICO'
        elif rj_count > 20 or total_debt > 50_000_000_000:  # 50 bilhões
            return 'ALTO'
        elif rj_count > 5 or total_debt > 10_000_000_000:  # 10 bilhões
            return 'MEDIO'
        return 'BAIXO'
    
    def update_company_status(self, cnpj: str, new_status: str, details: Dict = None):
        """
        Atualiza status judicial de uma empresa.
        Registra mudança no histórico.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Busca status atual
        cursor.execute("""
            SELECT judicial_status FROM flv_producers_rj WHERE cnpj = ?
        """, (cnpj,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False
        
        old_status = result['judicial_status']
        
        # Atualiza status
        cursor.execute("""
            UPDATE flv_producers_rj 
            SET judicial_status = ?,
                process_status_detail = ?,
                last_judicial_update = datetime('now'),
                updated_at = datetime('now')
            WHERE cnpj = ?
        """, (new_status, json.dumps(details) if details else None, cnpj))
        
        conn.commit()
        conn.close()
        
        return {
            'cnpj': cnpj,
            'old_status': old_status,
            'new_status': new_status,
            'updated_at': datetime.now().isoformat()
        }
    
    def get_companies_by_risk_level(self, risk_level: str) -> List[Dict]:
        """
        Retorna empresas filtradas por nível de risco de crédito.
        """
        score_ranges = {
            'baixo': (700, 1000),
            'medio': (500, 699),
            'alto': (300, 499),
            'critico': (0, 299)
        }
        
        min_score, max_score = score_ranges.get(risk_level, (0, 1000))
        
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM flv_producers_rj 
            WHERE credit_score_2026 BETWEEN ? AND ?
            ORDER BY credit_score_2026 DESC
        """, (min_score, max_score))
        
        companies = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return companies
    
    def run_daily_check(self) -> Dict:
        """
        Executa verificação diária de crises.
        Retorna relatório de atividades.
        """
        report = {
            'check_date': datetime.now().isoformat(),
            'new_processes': [],
            'status_changes': [],
            'scores_updated': []
        }
        
        # Verifica novos processos
        new_processes = self.check_new_rj()
        report['new_processes'] = new_processes
        report['new_processes_count'] = len(new_processes)
        
        # Atualiza scores de empresas sem score
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cnpj FROM flv_producers_rj 
            WHERE credit_score_2026 IS NULL
            LIMIT 50
        """)
        
        companies_without_score = cursor.fetchall()
        conn.close()
        
        for row in companies_without_score:
            try:
                score_result = self.calculate_credit_score(row['cnpj'])
                report['scores_updated'].append({
                    'cnpj': row['cnpj'],
                    'score': score_result.get('score')
                })
            except Exception as e:
                report['scores_updated'].append({
                    'cnpj': row['cnpj'],
                    'error': str(e)
                })
        
        return report


def seed_crisis_data():
    """
    Popula dados iniciais de empresas em crise para demonstração.
    """
    from ..seed_empresas_agro_rj_nacional import seed_empresas_agro_rj
    seed_empresas_agro_rj()


if __name__ == '__main__':
    # Teste do módulo
    cw = CrisisWatch()
    
    print("=== CrisisWatch - Vigilância de Crise NIA$ v5.0 ===\n")
    
    # Resumo da crise
    summary = cw.get_crisis_summary()
    print(f"Resumo da Crise ({summary['summary_date']})")
    print(f"Nível de Alerta: {summary['alert_level']}")
    print(f"Empresas em RJ: {summary['totals']['in_rj']}")
    print(f"Falências: {summary['totals']['bankrupt']}")
    print(f"Dívida Total: R$ {summary['totals']['total_debt_billions']:.2f} bilhões")
    print(f"Empregos em Risco: {summary['totals']['employees_at_risk']:,}")
    
    # Calcula score para primeira empresa
    conn = cw.get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT cnpj FROM flv_producers_rj LIMIT 1")
    first = cursor.fetchone()
    conn.close()
    
    if first:
        print(f"\n=== Score de Crédito ({first['cnpj']}) ===")
        score = cw.calculate_credit_score(first['cnpj'])
        print(f"Score 2026: {score['score']}")
        print(f"Classificação: {score['classification']}")
        print(f"Nível de Risco: {score['risk_level']}")
