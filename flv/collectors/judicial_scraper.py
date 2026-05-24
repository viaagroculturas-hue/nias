"""
JudicialScraper - Coletor de Dados Judiciais
Scraping de Diários Oficiais e Juntas Comerciais
NIA$ Soberano Digital v5.0
"""

import json
import sqlite3
import os
import re
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nia_flv.db')


class JudicialScraper:
    """
    Coletor de dados de fontes judiciais públicas.
    Monitora Diários Oficiais, Juntas Comerciais e Tribunais.
    """
    
    # URLs base para scraping (placeholders - em produção usar APIs reais)
    SOURCES = {
        'tjsp': {
            'name': 'Tribunal de Justiça de São Paulo',
            'url': 'https://www.tjsp.jus.br/',
            'type': 'tribunal'
        },
        'tjmg': {
            'name': 'Tribunal de Justiça de Minas Gerais',
            'url': 'https://www.tjmg.jus.br/',
            'type': 'tribunal'
        },
        'tjgo': {
            'name': 'Tribunal de Justiça de Goiás',
            'url': 'https://www.tjgo.jus.br/',
            'type': 'tribunal'
        },
        'tjpr': {
            'name': 'Tribunal de Justiça do Paraná',
            'url': 'https://www.tjpr.jus.br/',
            'type': 'tribunal'
        },
        'juntasp': {
            'name': 'Junta Comercial de São Paulo',
            'url': 'https://www.jucesponline.sp.gov.br/',
            'type': 'junta_comercial'
        },
        'do_sp': {
            'name': 'Diário Oficial de São Paulo',
            'url': 'https://www.imprensaoficial.com.br/',
            'type': 'diario_oficial'
        }
    }
    
    # Palavras-chave para identificar processos relevantes
    KEYWORDS_RJ = [
        'recuperação judicial',
        'recuperacao judicial',
        'falência',
        'falencia',
        'recuperação extra-judicial',
        'decretação de falência',
        'homologação de plano',
        'autorização para venda',
        'leilão de ativos'
    ]
    
    # Segmentos do agronegócio
    AGRO_KEYWORDS = [
        'agro', 'agrícola', 'agricola', 'pecuária', 'pecuaria',
        'insumos', 'fertilizante', 'defensivo', 'semente',
        'soja', 'milho', 'café', 'cafe', 'cana', 'açúcar', 'acucar',
        'etanol', 'leite', 'carne', 'frango', 'suíno', 'suino',
        'hortifruti', 'grãos', 'graos', 'agroindústria', 'agroindustria',
        'cooperativa', 'armazém', 'armazem', 'silos'
    ]
    
    def __init__(self):
        self.db_path = DB_PATH
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def get_conn(self):
        """Obtém conexão com o banco de dados"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def search_new_processes(self, days_back: int = 7) -> List[Dict]:
        """
        Busca novos processos judiciais nas fontes configuradas.
        
        Args:
            days_back: Número de dias para buscar retroativamente
            
        Returns:
            Lista de processos encontrados
        """
        processes = []
        
        # Em produção, aqui faria scraping real dos sites
        # Por enquanto, simulação baseada em padrões conhecidos
        
        for source_id, source_config in self.SOURCES.items():
            try:
                source_processes = self._scrape_source(source_id, days_back)
                processes.extend(source_processes)
            except Exception as e:
                print(f"[JudicialScraper] Erro ao buscar {source_id}: {e}")
        
        return processes
    
    def _scrape_source(self, source_id: str, days_back: int) -> List[Dict]:
        """
        Scrape específico para cada fonte.
        """
        processes = []
        
        # Simulação de dados - em produção, implementar scraping real
        # com tratamento de CAPTCHA e rate limiting
        
        if source_id == 'tjsp':
            # Simula processos de SP
            processes.extend(self._simulate_tjsp_processes(days_back))
        elif source_id == 'tjmg':
            # Simula processos de MG
            processes.extend(self._simulate_tjmg_processes(days_back))
        elif source_id == 'tjgo':
            # Simula processos de GO
            processes.extend(self._simulate_tjgo_processes(days_back))
        
        return processes
    
    def _simulate_tjsp_processes(self, days_back: int) -> List[Dict]:
        """Simula processos do TJSP para demonstração"""
        # Dados de exemplo baseados em casos reais recentes
        sample_processes = [
            {
                'process_number': '0001234-56.2024.8.26.0100',
                'company_name': 'Agroindustrial Paulista S.A.',
                'cnpj': '12.345.678/0001-90',
                'process_type': 'rj',
                'court': '2ª Vara de Falências e Recuperações Judiciais - São Paulo/SP',
                'entry_date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                'debt_estimate': 150000000,
                'main_activity': 'Comercialização de Grãos',
                'keywords_found': ['recuperação judicial', 'soja', 'milho']
            },
            {
                'process_number': '0002345-67.2024.8.26.0100',
                'company_name': 'Fertilizantes do Interior Ltda',
                'cnpj': '23.456.789/0001-01',
                'process_type': 'falencia',
                'court': '1ª Vara de Falências - Campinas/SP',
                'entry_date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                'debt_estimate': 45000000,
                'main_activity': 'Distribuição de Insumos',
                'keywords_found': ['falência', 'fertilizantes']
            }
        ]
        
        return [p for p in sample_processes 
                if datetime.strptime(p['entry_date'], '%Y-%m-%d') >= 
                   datetime.now() - timedelta(days=days_back)]
    
    def _simulate_tjmg_processes(self, days_back: int) -> List[Dict]:
        """Simula processos do TJMG"""
        sample_processes = [
            {
                'process_number': '0003456-78.2024.8.13.0001',
                'company_name': 'Café Premium Minas S.A.',
                'cnpj': '34.567.890/0001-12',
                'process_type': 'rj',
                'court': '1ª Vara de Falências e Recuperações Judiciais - Belo Horizonte/MG',
                'entry_date': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
                'debt_estimate': 89000000,
                'main_activity': 'Exportação de Café',
                'keywords_found': ['recuperação judicial', 'café', 'exportação']
            }
        ]
        
        return [p for p in sample_processes 
                if datetime.strptime(p['entry_date'], '%Y-%m-%d') >= 
                   datetime.now() - timedelta(days=days_back)]
    
    def _simulate_tjgo_processes(self, days_back: int) -> List[Dict]:
        """Simula processos do TJGO"""
        sample_processes = [
            {
                'process_number': '0004567-89.2024.8.09.0001',
                'company_name': 'Grão Goiano Comercial Ltda',
                'cnpj': '45.678.901/0001-23',
                'process_type': 'rj',
                'court': '1ª Vara de Falências e Recuperações Judiciais - Goiânia/GO',
                'entry_date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'debt_estimate': 125000000,
                'main_activity': 'Trading de Grãos',
                'keywords_found': ['recuperação judicial', 'soja', 'milho']
            }
        ]
        
        return [p for p in sample_processes 
                if datetime.strptime(p['entry_date'], '%Y-%m-%d') >= 
                   datetime.now() - timedelta(days=days_back)]
    
    def check_corporate_changes(self, days_back: int = 7) -> List[Dict]:
        """
        Busca alterações societárias em Juntas Comerciais.
        Retorna mudanças de diretoria, sócios e administradores.
        """
        changes = []
        
        # Busca empresas monitoradas
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cnpj, company_name FROM flv_producers_rj
            UNION
            SELECT cnpj, company_name FROM flv_distributors WHERE cnpj IS NOT NULL
            LIMIT 100
        """)
        
        companies = cursor.fetchall()
        conn.close()
        
        for company in companies:
            # Simula busca de alterações
            company_changes = self._check_company_changes(
                company['cnpj'], 
                company['company_name'],
                days_back
            )
            changes.extend(company_changes)
        
        return changes
    
    def _check_company_changes(self, cnpj: str, company_name: str, days_back: int) -> List[Dict]:
        """Verifica alterações específicas de uma empresa"""
        changes = []
        
        # Simulação - em produção, consultaria APIs da Receita Federal
        # e Juntas Comerciais
        
        # Probabiliade aleatória de encontrar alteração (para demo)
        import random
        if random.random() < 0.1:  # 10% de chance
            change_types = ['diretoria', 'socio', 'administrador', 'sede']
            change_type = random.choice(change_types)
            
            change = {
                'cnpj': cnpj,
                'company_name': company_name,
                'change_type': change_type,
                'change_subtype': 'entrada' if change_type == 'diretoria' else 'alteracao',
                'old_value': 'Valor Anterior',
                'new_value': 'Novo Valor',
                'change_date': (datetime.now() - timedelta(days=random.randint(1, days_back))).strftime('%Y-%m-%d'),
                'source': 'receita_federal',
                'confidence_score': 0.95
            }
            changes.append(change)
        
        return changes
    
    def save_corporate_change(self, change: Dict) -> bool:
        """
        Salva alteração societária no banco de dados.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO flv_corporate_changes 
                (company_cnpj, company_name, change_type, change_subtype, 
                 old_value, new_value, change_date, source, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                change['cnpj'],
                change['company_name'],
                change['change_type'],
                change.get('change_subtype'),
                change.get('old_value'),
                change.get('new_value'),
                change['change_date'],
                change.get('source'),
                change.get('confidence_score', 0.5)
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"[JudicialScraper] Erro ao salvar alteração: {e}")
            conn.close()
            return False
    
    def get_judicial_timeline(self, cnpj: str) -> List[Dict]:
        """
        Retorna linha do tempo judicial de uma empresa.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Busca dados da empresa
        cursor.execute("""
            SELECT * FROM flv_producers_rj WHERE cnpj = ?
        """, (cnpj,))
        
        company = cursor.fetchone()
        if not company:
            conn.close()
            return []
        
        # Monta timeline
        timeline = []
        
        # Entrada no processo
        if company['entry_date']:
            timeline.append({
                'date': company['entry_date'],
                'type': 'entry',
                'title': 'Entrada em Recuperação Judicial',
                'description': f'Processo {company["process_number"]}',
                'court': company['court']
            })
        
        # Alterações societárias durante o processo
        cursor.execute("""
            SELECT * FROM flv_corporate_changes 
            WHERE company_cnpj = ?
            ORDER BY change_date DESC
        """, (cnpj,))
        
        for change in cursor.fetchall():
            timeline.append({
                'date': change['change_date'],
                'type': 'corporate_change',
                'change_type': change['change_type'],
                'title': f"Alteração: {change['change_type']}",
                'description': f"De '{change['old_value']}' para '{change['new_value']}'",
                'source': change['source']
            })
        
        conn.close()
        
        # Ordena por data
        timeline.sort(key=lambda x: x['date'], reverse=True)
        
        return timeline
    
    def detect_asset_auctions(self, days_back: int = 30) -> List[Dict]:
        """
        Detecta leilões de ativos de empresas em recuperação.
        """
        auctions = []
        
        # Em produção, consultaria sites de leilões (Sato, Zukerman, etc.)
        # e Diários Oficiais
        
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cnpj, company_name, city, state_uf 
            FROM flv_producers_rj 
            WHERE judicial_status IN ('em_recuperacao', 'falencia')
        """)
        
        companies = cursor.fetchall()
        conn.close()
        
        # Simulação de leilões
        import random
        for company in companies:
            if random.random() < 0.2:  # 20% de chance de ter leilão
                auction = {
                    'cnpj': company['cnpj'],
                    'company_name': company['company_name'],
                    'auction_date': (datetime.now() + timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
                    'asset_type': random.choice(['imóvel', 'máquinas', 'veículos', 'estoque']),
                    'location': f"{company['city']}/{company['state_uf']}",
                    'auctioneer': random.choice(['Sato Leilões', 'Zukerman', 'Sodré Santoro']),
                    'estimated_value': random.randint(100000, 10000000)
                }
                auctions.append(auction)
        
        return auctions
    
    def run_full_scan(self) -> Dict:
        """
        Executa scan completo de fontes judiciais.
        Retorna relatório consolidado.
        """
        print("[JudicialScraper] Iniciando scan completo...")
        
        report = {
            'scan_date': datetime.now().isoformat(),
            'new_processes': self.search_new_processes(days_back=7),
            'corporate_changes': self.check_corporate_changes(days_back=7),
            'asset_auctions': self.detect_asset_auctions(days_back=30)
        }
        
        # Salva alterações no banco
        for change in report['corporate_changes']:
            self.save_corporate_change(change)
        
        print(f"[JudicialScraper] Scan concluído:")
        print(f"  - {len(report['new_processes'])} novos processos")
        print(f"  - {len(report['corporate_changes'])} alterações societárias")
        print(f"  - {len(report['asset_auctions'])} leilões detectados")
        
        return report


if __name__ == '__main__':
    scraper = JudicialScraper()
    
    print("=== JudicialScraper - Coletor de Dados Judiciais ===\n")
    
    # Scan completo
    report = scraper.run_full_scan()
    
    print("\nNovos Processos:")
    for proc in report['new_processes']:
        print(f"  - {proc['company_name']} ({proc['process_type'].upper()})")
        print(f"    Processo: {proc['process_number']}")
        print(f"    Dívida Estimada: R$ {proc['debt_estimate']:,.2f}")
    
    print("\nLeilões de Ativos:")
    for auction in report['asset_auctions']:
        print(f"  - {auction['company_name']}")
        print(f"    Ativo: {auction['asset_type']}")
        print(f"    Data: {auction['auction_date']}")
        print(f"    Valor Estimado: R$ {auction['estimated_value']:,.2f}")
