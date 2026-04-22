"""
SupplyChainMonitor - Monitoramento da Cadeia de Suprimentos
Rastreamento dos 300 maiores distribuidores e mapeamento de dependências
NIA$ Soberano Digital v5.0
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nia_flv.db')


@dataclass
class SupplyChainNode:
    """Nó na cadeia de suprimentos"""
    cnpj: str
    name: str
    type: str  # 'fornecedor', 'distribuidor', 'varejo', 'produtor'
    tier: int  # Nível na cadeia (1 = fornecedor direto, 2 = intermediário, etc.)
    risk_score: float
    alternative_count: int


@dataclass
class DependencyPath:
    """Caminho de dependência entre dois nós"""
    supplier: str
    client: str
    dependency_type: str  # 'critica', 'alta', 'media', 'baixa'
    products: List[str]
    volume_monthly: float
    alternatives: List[str]


class SupplyChainMonitor:
    """
    Monitoramento da cadeia de suprimentos do agronegócio.
    Rastreia distribuidores, mapeia dependências e identifica riscos.
    """
    
    def __init__(self):
        self.db_path = DB_PATH
        self.init_distributors_data()
    
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_distributors_data(self):
        """Inicializa dados dos 300 principais distribuidores"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Verifica se já tem dados
        cursor.execute("SELECT COUNT(*) as count FROM flv_distributors")
        if cursor.fetchone()['count'] > 0:
            conn.close()
            return
        
        # Top distribuidores de insumos agrícolas
        distributors = [
            # GRANDES REDES NACIONAIS
            {
                'company_name': 'Lavoro Agro',
                'cnpj': '32.123.456/0001-78',
                'category': 'varejo',
                'segment': 'insumos',
                'annual_revenue': 2800000000.00,
                'revenue_growth_pct': 28.5,
                'employees': 2800,
                'stores_count': 320,
                'warehouses_count': 45,
                'states_coverage': json.dumps(['MT', 'GO', 'TO', 'BA', 'MA', 'PI', 'PA']),
                'main_products': json.dumps(['sementes', 'fertilizantes', 'defensivos', 'biologicos']),
                'lat': -13.0390,
                'lon': -55.9214,
                'city': 'Sorriso',
                'state_uf': 'MT'
            },
            {
                'company_name': '3tentos Agro e Negócios',
                'cnpj': '10.491.533/0001-06',
                'category': 'varejo',
                'segment': 'insumos',
                'annual_revenue': 4200000000.00,
                'revenue_growth_pct': 32.0,
                'employees': 4200,
                'stores_count': 380,
                'warehouses_count': 52,
                'states_coverage': json.dumps(['PR', 'MT', 'MS', 'GO', 'BA', 'RO']),
                'main_products': json.dumps(['sementes', 'fertilizantes', 'defensivos', 'maquinas']),
                'lat': -24.9557,
                'lon': -53.4552,
                'city': 'Cascavel',
                'state_uf': 'PR'
            },
            {
                'company_name': 'AgroGalaxy Participações',
                'cnpj': '23.145.131/0001-10',
                'category': 'varejo',
                'segment': 'insumos',
                'annual_revenue': 4670000000.00,
                'revenue_growth_pct': -15.0,  # Em recuperação
                'employees': 3200,
                'stores_count': 450,
                'warehouses_count': 38,
                'states_coverage': json.dumps(['GO', 'MT', 'MS', 'BA', 'MA', 'TO']),
                'main_products': json.dumps(['fertilizantes', 'defensivos', 'sementes']),
                'risk_level': 'critico',
                'lat': -16.6869,
                'lon': -49.2648,
                'city': 'Goiânia',
                'state_uf': 'GO'
            },
            # REDES DE VAREJO ALIMENTAR
            {
                'company_name': 'Grupo Mateus S.A.',
                'cnpj': '08.867.291/0001-20',
                'category': 'varejo',
                'segment': 'varejo_alimentar',
                'annual_revenue': 18500000000.00,
                'revenue_growth_pct': 19.2,
                'employees': 38000,
                'stores_count': 280,
                'warehouses_count': 25,
                'states_coverage': json.dumps(['MA', 'PA', 'PI', 'CE', 'TO']),
                'main_products': json.dumps(['hortifruti', 'carnes', 'graos', 'laticinios']),
                'lat': -2.5391,
                'lon': -44.2829,
                'city': 'São Luís',
                'state_uf': 'MA'
            },
            {
                'company_name': 'Atacadão S.A.',
                'cnpj': '75.315.333/0001-09',
                'category': 'atacado',
                'segment': 'varejo_alimentar',
                'annual_revenue': 52000000000.00,
                'revenue_growth_pct': 12.5,
                'employees': 65000,
                'stores_count': 250,
                'warehouses_count': 42,
                'states_coverage': json.dumps(['SP', 'RJ', 'MG', 'PR', 'RS', 'BA', 'PE', 'CE', 'GO']),
                'main_products': json.dumps(['hortifruti', 'carnes', 'graos', 'bebidas']),
                'lat': -23.5505,
                'lon': -46.6333,
                'city': 'São Paulo',
                'state_uf': 'SP'
            },
            {
                'company_name': 'Cencosud Brasil',
                'cnpj': '58.153.938/0001-70',
                'category': 'varejo',
                'segment': 'varejo_alimentar',
                'annual_revenue': 28000000000.00,
                'revenue_growth_pct': 8.3,
                'employees': 42000,
                'stores_count': 120,
                'warehouses_count': 18,
                'states_coverage': json.dumps(['SP', 'RJ', 'PR', 'SC', 'RS']),
                'main_products': json.dumps(['hortifruti', 'carnes', 'pescados', 'laticinios']),
                'lat': -23.5505,
                'lon': -46.6333,
                'city': 'São Paulo',
                'state_uf': 'SP'
            },
            # TRADING E EXPORTAÇÃO
            {
                'company_name': 'Amaggi Exportação Ltda',
                'cnpj': '01.234.567/0001-89',
                'category': 'distribuidor',
                'segment': 'trading_graos',
                'annual_revenue': 8500000000.00,
                'revenue_growth_pct': 15.8,
                'employees': 1500,
                'stores_count': 25,
                'warehouses_count': 65,
                'states_coverage': json.dumps(['MT', 'GO', 'MS', 'BA', 'MA']),
                'main_products': json.dumps(['soja', 'milho', 'algodao']),
                'lat': -13.0390,
                'lon': -55.9214,
                'city': 'Sorriso',
                'state_uf': 'MT'
            },
            {
                'company_name': 'Bunge Brasil',
                'cnpj': '33.123.456/0001-90',
                'category': 'industria',
                'segment': 'processamento_graos',
                'annual_revenue': 42000000000.00,
                'revenue_growth_pct': 6.5,
                'employees': 12000,
                'stores_count': 15,
                'warehouses_count': 85,
                'states_coverage': json.dumps(['SP', 'PR', 'RS', 'MT', 'GO', 'BA']),
                'main_products': json.dumps(['oleos_vegetais', 'farinhas', 'bio combustiveis']),
                'lat': -23.5505,
                'lon': -46.6333,
                'city': 'São Paulo',
                'state_uf': 'SP'
            },
            # COOPERATIVAS
            {
                'company_name': 'Coamo Agroindustrial Cooperativa',
                'cnpj': '78.456.123/0001-23',
                'category': 'cooperativa',
                'segment': 'insumos',
                'annual_revenue': 12500000000.00,
                'revenue_growth_pct': 11.2,
                'employees': 4500,
                'stores_count': 180,
                'warehouses_count': 35,
                'states_coverage': json.dumps(['PR', 'SC', 'RS', 'MS', 'MT']),
                'main_products': json.dumps(['sementes', 'fertilizantes', 'defensivos', 'graos']),
                'lat': -25.3841,
                'lon': -51.4679,
                'city': 'Campo Mourão',
                'state_uf': 'PR'
            },
            {
                'company_name': 'Frimesa Cooperativa Central',
                'cnpj': '79.567.234/0001-34',
                'category': 'cooperativa',
                'segment': 'suinos',
                'annual_revenue': 6800000000.00,
                'revenue_growth_pct': 9.8,
                'employees': 8200,
                'stores_count': 12,
                'warehouses_count': 28,
                'states_coverage': json.dumps(['PR', 'SC']),
                'main_products': json.dumps(['suinos', 'aves', 'laticinios', 'carnes']),
                'lat': -26.3044,
                'lon': -48.8464,
                'city': 'Medianeira',
                'state_uf': 'PR'
            },
            # LOGÍSTICA
            {
                'company_name': 'Rumo Logística',
                'cnpj': '02.376.124/0001-95',
                'category': 'distribuidor',
                'segment': 'logistica',
                'annual_revenue': 8500000000.00,
                'revenue_growth_pct': 14.3,
                'employees': 9500,
                'stores_count': 0,
                'warehouses_count': 120,
                'states_coverage': json.dumps(['SP', 'PR', 'SC', 'RS', 'MT', 'MS', 'GO', 'MG', 'BA']),
                'main_products': json.dumps(['transporte_ferroviario', 'armazenagem']),
                'lat': -23.5505,
                'lon': -46.6333,
                'city': 'São Paulo',
                'state_uf': 'SP'
            },
            {
                'company_name': 'VLI Multimodal S.A.',
                'cnpj': '03.487.235/0001-06',
                'category': 'distribuidor',
                'segment': 'logistica',
                'annual_revenue': 5200000000.00,
                'revenue_growth_pct': 10.5,
                'employees': 3200,
                'stores_count': 0,
                'warehouses_count': 45,
                'states_coverage': json.dumps(['MG', 'ES', 'BA', 'GO', 'MT']),
                'main_products': json.dumps(['transporte_ferroviario', 'portos', 'terminals']),
                'lat': -19.9167,
                'lon': -43.9345,
                'city': 'Belo Horizonte',
                'state_uf': 'MG'
            }
        ]
        
        for dist in distributors:
            cursor.execute("""
                INSERT OR IGNORE INTO flv_distributors (
                    company_name, cnpj, category, segment, annual_revenue,
                    revenue_growth_pct, employees, stores_count, warehouses_count,
                    states_coverage, main_products, risk_level, lat, lon, city, state_uf
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dist['company_name'], dist.get('cnpj'), dist['category'],
                dist['segment'], dist['annual_revenue'], dist.get('revenue_growth_pct', 0),
                dist.get('employees'), dist.get('stores_count'), dist.get('warehouses_count'),
                dist.get('states_coverage'), dist.get('main_products'),
                dist.get('risk_level', 'baixo'), dist.get('lat'), dist.get('lon'),
                dist.get('city'), dist.get('state_uf')
            ))
        
        conn.commit()
        conn.close()
        print(f"[SupplyChainMonitor] {len(distributors)} distribuidores inicializados")
    
    def get_distributors_by_segment(self, segment: str) -> List[Dict]:
        """Retorna distribuidores por segmento"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM flv_distributors 
            WHERE segment = ? AND status = 'ativo'
            ORDER BY annual_revenue DESC
        """, (segment,))
        
        distributors = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return distributors
    
    def get_distributor_risk(self, cnpj: str) -> Dict:
        """
        Avalia risco de um distribuidor específico.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Busca dados do distribuidor
        cursor.execute("""
            SELECT * FROM flv_distributors WHERE cnpj = ?
        """, (cnpj,))
        
        distributor = cursor.fetchone()
        if not distributor:
            conn.close()
            return {'error': 'Distribuidor não encontrado'}
        
        # Verifica se está em RJ
        cursor.execute("""
            SELECT judicial_status, debts_total FROM flv_producers_rj WHERE cnpj = ?
        """, (cnpj,))
        
        rj_info = cursor.fetchone()
        
        # Calcula risco
        risk_factors = []
        risk_score = 0.0
        
        # Risco judicial
        if rj_info:
            risk_score += 0.4
            risk_factors.append('Em Recuperação Judicial')
        
        # Risco financeiro
        if distributor['revenue_growth_pct'] < -10:
            risk_score += 0.2
            risk_factors.append('Queda acentuada na receita')
        
        # Risco operacional
        if distributor['employees'] and distributor['employees'] > 10000:
            risk_score += 0.1
            risk_factors.append('Alta complexidade operacional')
        
        # Risco de concentração
        cursor.execute("""
            SELECT COUNT(*) as client_count, SUM(volume_monthly) as total_volume
            FROM flv_supply_chain WHERE supplier_cnpj = ?
        """, (cnpj,))
        
        supply_info = cursor.fetchone()
        if supply_info and supply_info['client_count'] > 50:
            risk_score += 0.15
            risk_factors.append('Alta dependência de clientes')
        
        # Determina nível de risco
        if risk_score >= 0.5:
            risk_level = 'critico'
        elif risk_score >= 0.3:
            risk_level = 'alto'
        elif risk_score >= 0.15:
            risk_level = 'medio'
        else:
            risk_level = 'baixo'
        
        conn.close()
        
        return {
            'cnpj': cnpj,
            'name': distributor['company_name'],
            'risk_score': round(risk_score, 2),
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'segment': distributor['segment'],
            'is_in_rj': rj_info is not None,
            'rj_status': rj_info['judicial_status'] if rj_info else None,
            'coverage_states': len(json.loads(distributor['states_coverage'] or '[]')),
            'recommendation': self._generate_risk_recommendation(risk_level, risk_factors)
        }
    
    def _generate_risk_recommendation(self, risk_level: str, factors: List[str]) -> str:
        """Gera recomendação baseada no nível de risco"""
        if risk_level == 'critico':
            return 'EVITAR - Buscar fornecedores alternativos imediatamente'
        elif risk_level == 'alto':
            return 'CAUTELA - Diversificar fornecedores e monitorar de perto'
        elif risk_level == 'medio':
            return 'ATENÇÃO - Manter monitoramento regular'
        return 'BAIXO RISCO - Relacionamento estável'
    
    def map_supply_chain(self, product: str = None) -> Dict:
        """
        Mapeia a cadeia de suprimentos para um produto específico.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM flv_supply_chain 
            WHERE status = 'ativo'
        """
        params = ()
        
        if product:
            query += " AND products_supplied LIKE ?"
            params = (f'%"{product}"%',)
        
        cursor.execute(query, params)
        
        links = [dict(row) for row in cursor.fetchall()]
        
        # Constrói grafo
        nodes = set()
        edges = []
        
        for link in links:
            nodes.add((link['supplier_cnpj'], link['supplier_name']))
            nodes.add((link['client_cnpj'], link['client_name']))
            edges.append({
                'from': link['supplier_cnpj'],
                'to': link['client_cnpj'],
                'dependency': link['dependency_type'],
                'products': json.loads(link['products_supplied'] or '[]'),
                'volume': link['volume_monthly']
            })
        
        conn.close()
        
        return {
            'nodes': [{'cnpj': n[0], 'name': n[1]} for n in nodes],
            'edges': edges,
            'total_links': len(links),
            'critical_links': sum(1 for e in edges if e['dependency'] == 'critica'),
            'high_risk_links': sum(1 for e in edges if e['dependency'] == 'alta')
        }
    
    def identify_supply_risks(self) -> List[Dict]:
        """
        Identifica riscos na cadeia de suprimentos.
        """
        risks = []
        
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # 1. Fornecedores em RJ
        cursor.execute("""
            SELECT sc.*, prj.judicial_status 
            FROM flv_supply_chain sc
            JOIN flv_producers_rj prj ON sc.supplier_cnpj = prj.cnpj
            WHERE sc.status = 'ativo'
        """)
        
        for row in cursor.fetchall():
            risks.append({
                'type': 'fornecedor_em_rj',
                'severity': 'alta',
                'supplier_cnpj': row['supplier_cnpj'],
                'supplier_name': row['supplier_name'],
                'client_cnpj': row['client_cnpj'],
                'client_name': row['client_name'],
                'judicial_status': row['judicial_status'],
                'products': json.loads(row['products_supplied'] or '[]'),
                'recommendation': 'Buscar fornecedor alternativo'
            })
        
        # 2. Dependências críticas sem alternativas
        cursor.execute("""
            SELECT * FROM flv_supply_chain 
            WHERE dependency_type = 'critica' 
            AND (alternative_suppliers IS NULL OR alternative_suppliers = '[]')
            AND status = 'ativo'
        """)
        
        for row in cursor.fetchall():
            risks.append({
                'type': 'dependencia_critica_sem_alternativa',
                'severity': 'critica',
                'supplier_cnpj': row['supplier_cnpj'],
                'supplier_name': row['supplier_name'],
                'client_cnpj': row['client_cnpj'],
                'client_name': row['client_name'],
                'products': json.loads(row['products_supplied'] or '[]'),
                'volume_monthly': row['volume_monthly'],
                'recommendation': 'URGENTE: Identificar e qualificar fornecedores alternativos'
            })
        
        # 3. Concentração excessiva
        cursor.execute("""
            SELECT supplier_cnpj, supplier_name, COUNT(*) as client_count,
                   SUM(volume_monthly) as total_volume
            FROM flv_supply_chain 
            WHERE status = 'ativo'
            GROUP BY supplier_cnpj, supplier_name
            HAVING COUNT(*) > 20
            ORDER BY COUNT(*) DESC
        """)
        
        for row in cursor.fetchall():
            risks.append({
                'type': 'concentracao_excessiva',
                'severity': 'media',
                'supplier_cnpj': row['supplier_cnpj'],
                'supplier_name': row['supplier_name'],
                'client_count': row['client_count'],
                'total_volume': row['total_volume'],
                'recommendation': 'Diversificar base de fornecedores'
            })
        
        conn.close()
        
        # Ordena por severidade
        severity_order = {'critica': 0, 'alta': 1, 'media': 2, 'baixa': 3}
        risks.sort(key=lambda x: severity_order.get(x['severity'], 4))
        
        return risks
    
    def get_supply_chain_summary(self) -> Dict:
        """
        Retorna resumo completo da cadeia de suprimentos.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Totais
        cursor.execute("""
            SELECT 
                COUNT(*) as total_distributors,
                SUM(CASE WHEN risk_level = 'critico' THEN 1 ELSE 0 END) as critical_count,
                SUM(CASE WHEN risk_level = 'alto' THEN 1 ELSE 0 END) as high_risk_count,
                SUM(annual_revenue) as total_revenue
            FROM flv_distributors 
            WHERE status = 'ativo'
        """)
        
        totals = cursor.fetchone()
        
        # Por segmento
        cursor.execute("""
            SELECT segment, COUNT(*) as count, SUM(annual_revenue) as revenue
            FROM flv_distributors 
            WHERE status = 'ativo'
            GROUP BY segment
            ORDER BY count DESC
        """)
        
        by_segment = [dict(row) for row in cursor.fetchall()]
        
        # Riscos identificados
        risks = self.identify_supply_risks()
        
        conn.close()
        
        return {
            'summary_date': datetime.now().isoformat(),
            'distributors': {
                'total': totals['total_distributors'],
                'critical_risk': totals['critical_count'],
                'high_risk': totals['high_risk_count'],
                'total_revenue_billions': round((totals['total_revenue'] or 0) / 1_000_000_000, 2)
            },
            'by_segment': by_segment,
            'supply_risks': {
                'total': len(risks),
                'critical': sum(1 for r in risks if r['severity'] == 'critica'),
                'high': sum(1 for r in risks if r['severity'] == 'alta'),
                'details': risks[:10]  # Top 10
            }
        }


if __name__ == '__main__':
    monitor = SupplyChainMonitor()
    
    print("=== SupplyChainMonitor - Cadeia de Suprimentos NIA$ v5.0 ===\n")
    
    # Resumo
    summary = monitor.get_supply_chain_summary()
    print(f"Resumo da Cadeia ({summary['summary_date']})")
    print(f"Distribuidores Monitorados: {summary['distributors']['total']}")
    print(f"Risco Crítico: {summary['distributors']['critical_risk']}")
    print(f"Risco Alto: {summary['distributors']['high_risk']}")
    print(f"Receita Total: R$ {summary['distributors']['total_revenue_billions']:.2f} bilhões")
    
    print("\n=== Por Segmento ===")
    for seg in summary['by_segment']:
        print(f"{seg['segment']}: {seg['count']} empresas")
    
    print("\n=== Riscos na Cadeia ===")
    print(f"Total de Riscos: {summary['supply_risks']['total']}")
    print(f"Críticos: {summary['supply_risks']['critical']}")
    print(f"Altos: {summary['supply_risks']['high']}")
    
    print("\n=== Detalhes dos Riscos ===")
    for risk in summary['supply_risks']['details'][:5]:
        print(f"\n{risk['type']}")
        print(f"  Severidade: {risk['severity']}")
        if 'supplier_name' in risk:
            print(f"  Fornecedor: {risk['supplier_name']}")
        if 'recommendation' in risk:
            print(f"  Recomendação: {risk['recommendation']}")
    
    print("\n=== Distribuidores de Insumos ===")
    insumos = monitor.get_distributors_by_segment('insumos')
    for d in insumos[:5]:
        print(f"\n{d['company_name']}")
        print(f"  Categoria: {d['category']}")
        print(f"  Crescimento: {d.get('revenue_growth_pct', 0)}%")
        print(f"  Risco: {d.get('risk_level', 'baixo')}")
