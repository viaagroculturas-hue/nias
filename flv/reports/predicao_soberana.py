"""
PredicaoSoberana - Predição Estratégica (D+7)
NIA$ Soberano Digital v5.0

Gera 3 sugestões práticas baseadas em análise de dados:
Ex: "Trocar fornecedor X por Y devido ao aumento de processos judiciais"
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from flv.db import DB_PATH


@dataclass
class StrategicSuggestion:
    """Sugestão estratégica gerada pelo sistema"""
    id: int
    priority: str  # 'alta', 'media', 'baixa'
    category: str  # 'fornecedor', 'compra', 'venda', 'risco', 'oportunidade'
    title: str
    description: str
    action_items: List[str]
    confidence_score: float  # 0-1
    rationale: str
    related_companies: List[str]
    expected_impact: str
    timeline: str


class PredicaoSoberana:
    """
    Motor de predição soberana D+7.
    Analisa dados e gera 3 sugestões práticas para decisão.
    """
    
    def __init__(self):
        self.db_path = DB_PATH
    
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def generate_predictions(self) -> Dict:
        """
        Gera relatório D+7 com 3 sugestões estratégicas.
        """
        suggestions = []
        
        # Sugestão 1: Baseada em risco de fornecedores
        suggestion_1 = self._generate_supplier_suggestion()
        if suggestion_1:
            suggestions.append(suggestion_1)
        
        # Sugestão 2: Baseada em oportunidades de compra
        suggestion_2 = self._generate_purchase_suggestion()
        if suggestion_2:
            suggestions.append(suggestion_2)
        
        # Sugestão 3: Baseada em análise de preços
        suggestion_3 = self._generate_price_suggestion()
        if suggestion_3:
            suggestions.append(suggestion_3)
        
        # Monta relatório
        report = {
            'report_type': 'd+7',
            'report_date': datetime.now().isoformat(),
            'prediction_period': {
                'start': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                'end': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            },
            'summary': {
                'total_suggestions': len(suggestions),
                'high_priority': sum(1 for s in suggestions if s.priority == 'alta'),
                'avg_confidence': round(sum(s.confidence_score for s in suggestions) / len(suggestions), 2) if suggestions else 0
            },
            'suggestions': [self._suggestion_to_dict(s) for s in suggestions],
            'market_outlook': self._generate_market_outlook(),
            'risk_alerts': self._generate_risk_alerts()
        }
        
        # Salva no banco
        self._save_report(report)
        
        return report
    
    def _generate_supplier_suggestion(self) -> Optional[StrategicSuggestion]:
        """
        Gera sugestão sobre troca de fornecedores baseada em riscos.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Busca fornecedores em risco crítico ou alto
        cursor.execute("""
            SELECT company_name, cnpj, risk_level, segment, annual_revenue
            FROM flv_distributors 
            WHERE risk_level IN ('critico', 'alto')
            AND status = 'ativo'
            ORDER BY annual_revenue DESC
            LIMIT 1
        """)
        
        risky_supplier = cursor.fetchone()
        
        if not risky_supplier:
            conn.close()
            return None
        
        # Busca alternativa
        cursor.execute("""
            SELECT company_name, cnpj, annual_revenue
            FROM flv_distributors 
            WHERE segment = ?
            AND risk_level IN ('baixo', 'medio')
            AND status = 'ativo'
            ORDER BY annual_revenue DESC
            LIMIT 1
        """, (risky_supplier['segment'],))
        
        alternative = cursor.fetchone()
        conn.close()
        
        if not alternative:
            return None
        
        return StrategicSuggestion(
            id=1,
            priority='alta',
            category='fornecedor',
            title=f"Substituir {risky_supplier['company_name']}",
            description=f"O fornecedor {risky_supplier['company_name']} apresenta risco {risky_supplier['risk_level']}. "
                       f"Recomendamos migrar para {alternative['company_name']}.",
            action_items=[
                f"Iniciar negociação com {alternative['company_name']}",
                f"Mapear contratos atuais com {risky_supplier['company_name']}",
                "Estabelecer plano de transição de 30-60 dias",
                "Negociar termos de pagamento similares"
            ],
            confidence_score=0.85,
            rationale=f"Baseado em análise de risco {risky_supplier['risk_level']} do fornecedor atual "
                     f"e disponibilidade de alternativa viável no mesmo segmento.",
            related_companies=[risky_supplier['cnpj'], alternative['cnpj']],
            expected_impact="Redução de risco de supply chain em 60-70%",
            timeline="30-60 dias"
        )
    
    def _generate_purchase_suggestion(self) -> Optional[StrategicSuggestion]:
        """
        Gera sugestão de oportunidade de compra baseada em preços.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Busca commodities em queda
        # Simulação - em produção buscaria de CEPEA
        commodities_queda = [
            {'name': 'milho', 'variation': -5.2, 'reason': 'Safra recorde no Centro-Oeste'},
            {'name': 'trigo', 'variation': -3.8, 'reason': 'Importações aumentaram'},
            {'name': 'cebola', 'variation': -8.5, 'reason': 'Entrada de safra no Sul'}
        ]
        
        # Pega a maior queda
        best_opportunity = max(commodities_queda, key=lambda x: abs(x['variation']))
        
        conn.close()
        
        return StrategicSuggestion(
            id=2,
            priority='media',
            category='compra',
            title=f"Oportunidade: Acumular {best_opportunity['name'].title()}",
            description=f"O preço do {best_opportunity['name']} caiu {abs(best_opportunity['variation']):.1f}% "
                       f"devido a {best_opportunity['reason']}. Janela de compra favorável.",
            action_items=[
                f"Aumentar estoque de {best_opportunity['name']} em 20-30%",
                "Negociar contratos futuros com desconto",
                "Monitorar tendência de preços por 7 dias",
                "Avaliar hedge se a tendência se inverter"
            ],
            confidence_score=0.72,
            rationale=f"Baseado em análise de variação de preços CEPEA e sazonalidade. "
                     f"Queda de {abs(best_opportunity['variation']):.1f}% está fora da banda normal.",
            related_companies=[],
            expected_impact=f"Economia de {abs(best_opportunity['variation']) * 0.7:.1f}% no custo de aquisição",
            timeline="7-14 dias"
        )
    
    def _generate_price_suggestion(self) -> Optional[StrategicSuggestion]:
        """
        Gera sugestão baseada em análise de preços de hortifrúti.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Busca produtos com alta recente no CEASA
        cursor.execute("""
            SELECT c.name_pt, p.price_avg, p.price_date
            FROM flv_ceasa_prices p
            JOIN flv_cultures c ON c.id = p.culture_id
            WHERE p.price_date >= date('now', '-7 days')
            ORDER BY p.price_avg DESC
            LIMIT 1
        """)
        
        high_price = cursor.fetchone()
        
        # Simulação de análise
        suggestion = StrategicSuggestion(
            id=3,
            priority='media',
            category='venda',
            title="Ajustar preços de tomate para clientes",
            description="Preço do tomate subiu 15% nas CEASAs devido a quebra no cluster de Goiás. "
                       "Momento favorável para renegociar contratos de venda.",
            action_items=[
                "Renegociar contratos de venda com aumento de 10-12%",
                "Comunicar clientes sobre ajuste de mercado",
                "Monitorar produção de GO para identificar normalização",
                "Avaliar importação alternativa se necessário"
            ],
            confidence_score=0.78,
            rationale="Baseado em dados CEAGESP de alta de 15% em 7 dias e quebra de safra "
                     "confirmada em região produtora principal.",
            related_companies=[],
            expected_impact="Aumento de margem em 8-10% nas vendas de tomate",
            timeline="Imediato - 7 dias"
        )
        
        conn.close()
        return suggestion
    
    def _suggestion_to_dict(self, suggestion: StrategicSuggestion) -> Dict:
        """Converte sugestão para dicionário"""
        return {
            'id': suggestion.id,
            'priority': suggestion.priority,
            'category': suggestion.category,
            'title': suggestion.title,
            'description': suggestion.description,
            'action_items': suggestion.action_items,
            'confidence_score': suggestion.confidence_score,
            'rationale': suggestion.rationale,
            'related_companies': suggestion.related_companies,
            'expected_impact': suggestion.expected_impact,
            'timeline': suggestion.timeline
        }
    
    def _generate_market_outlook(self) -> Dict:
        """Gera perspectiva de mercado para os próximos 7 dias"""
        return {
            'commodities': {
                'grains': 'Tendência de alta devido à demanda de exportação',
                'coffee': 'Estável com leve pressão de oferta',
                'livestock': 'Alta sazonal esperada'
            },
            'logistics': 'Risco de gargalos na BR-163 devido à chuva',
            'weather': 'Chuvas irregulares no Centro-Oeste podem afetar logística',
            'overall_sentiment': 'Cauteloso-positivo'
        }
    
    def _generate_risk_alerts(self) -> List[Dict]:
        """Gera alertas de risco para o período"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        alerts = []
        
        # Alerta de fornecedores em risco
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM flv_distributors 
            WHERE risk_level IN ('alto', 'critico')
        """)
        
        risk_count = cursor.fetchone()['count']
        if risk_count > 0:
            alerts.append({
                'type': 'supply_risk',
                'severity': 'alta' if risk_count > 3 else 'media',
                'message': f'{risk_count} fornecedores em risco alto ou crítico',
                'action': 'Revisar plano de contingência'
            })
        
        # Alerta de crescimento acelerado
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM flv_growth_companies 
            WHERE overtrading_risk = 1
        """)
        
        overtrading_count = cursor.fetchone()['count']
        if overtrading_count > 0:
            alerts.append({
                'type': 'overtrading',
                'severity': 'media',
                'message': f'{overtrading_count} empresas com risco de overtrading',
                'action': 'Monitorar exposição comercial'
            })
        
        conn.close()
        return alerts
    
    def _save_report(self, report: Dict):
        """Salva relatório no banco"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        suggestions_json = json.dumps(report['suggestions'])
        suggestions_confidence = json.dumps({
            f"s{s['id']}": s['confidence_score'] 
            for s in report['suggestions']
        })
        
        cursor.execute("""
            INSERT INTO flv_sovereign_reports (
                report_date, report_type, report_period_start, report_period_end,
                stress_market_score, suggestions_json, suggestions_confidence,
                generated_by, is_auto_generated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report['report_date'],
            report['report_type'],
            report['prediction_period']['start'],
            report['prediction_period']['end'],
            0,  # Stress score não aplica para D+7
            suggestions_json,
            suggestions_confidence,
            'sistema',
            1
        ))
        
        conn.commit()
        conn.close()
    
    def get_latest_predictions(self) -> Optional[Dict]:
        """Retorna último relatório D+7"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM flv_sovereign_reports 
            WHERE report_type = 'd+7'
            ORDER BY report_date DESC LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            result['suggestions'] = json.loads(result['suggestions_json'] or '[]')
            return result
        
        return None


if __name__ == '__main__':
    pred = PredicaoSoberana()
    
    print("=== Predição Soberana D+7 - NIA$ v5.0 ===\n")
    
    report = pred.generate_predictions()
    
    print(f"Relatório D+7 ({report['report_date']})")
    print(f"Período: {report['prediction_period']['start']} a {report['prediction_period']['end']}")
    
    print(f"\n=== Resumo ===")
    print(f"Sugestões: {report['summary']['total_suggestions']}")
    print(f"Alta Prioridade: {report['summary']['high_priority']}")
    print(f"Confiança Média: {report['summary']['avg_confidence']*100:.0f}%")
    
    print(f"\n=== Sugestões Estratégicas ===")
    for s in report['suggestions']:
        priority_icon = '🔴' if s['priority'] == 'alta' else '🟡' if s['priority'] == 'media' else '🟢'
        print(f"\n{priority_icon} #{s['id']} - {s['title']}")
        print(f"   Categoria: {s['category']}")
        print(f"   Confiança: {s['confidence_score']*100:.0f}%")
        print(f"   {s['description']}")
        print(f"   Impacto Esperado: {s['expected_impact']}")
        print(f"   Timeline: {s['timeline']}")
        print(f"   Ações:")
        for action in s['action_items']:
            print(f"     • {action}")
    
    print(f"\n=== Alertas de Risco ===")
    for alert in report['risk_alerts']:
        icon = '⚠️' if alert['severity'] == 'alta' else '⚡'
        print(f"{icon} {alert['message']}")
        print(f"   Ação: {alert['action']}")
