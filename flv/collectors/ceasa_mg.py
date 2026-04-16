"""
CEASA-MG Scraper — Cotações diárias Minas Gerais
Fonte: https://minas1.ceasa.mg.gov.br/ceasainternet/cst_precosmaiscomumMG/cst_precosmaiscomumMG.php
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
import time

URL_MG = "https://minas1.ceasa.mg.gov.br/ceasainternet/cst_precosmaiscomumMG/cst_precosmaiscomumMG.php"

def fetch_ceasa_mg():
    """
    Extrai cotações da CEASA-MG.
    Retorna DataFrame com colunas: data_coleta, origem, produto, embalagem, 
    preco_comum, regiao, fonte
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(URL_MG, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        response.raise_for_status()
    except Exception as e:
        print(f"[CEASA-MG] Erro na requisição: {e}")
        return pd.DataFrame()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Encontrar a tabela de cotações
    table = soup.find('table')
    if not table:
        print("[CEASA-MG] Tabela não encontrada")
        return pd.DataFrame()
    
    # Extrair headers para identificar regiões
    thead = table.find('thead')
    headers_list = []
    if thead:
        header_cells = thead.find_all('th')
        headers_list = [th.get_text(strip=True) for th in header_cells]
    
    # Headers esperados: ['Produtos', 'Embalagens', 'Grande BH', 'Uberlândia', 'Juiz de Fora', ...]
    regioes = headers_list[2:] if len(headers_list) > 2 else ['Grande BH', 'Uberlândia', 'Juiz de Fora', 'Gov. Valadares']
    
    # Extrair dados das linhas
    rows = []
    tbody = table.find('tbody')
    if not tbody:
        print("[CEASA-MG] tbody não encontrado")
        return pd.DataFrame()
    
    data_coleta = datetime.now().strftime('%Y-%m-%d')
    
    for tr in tbody.find_all('tr'):
        cells = tr.find_all('td')
        if len(cells) < 3:
            continue
        
        produto = cells[0].get_text(strip=True).upper()
        embalagem = cells[1].get_text(strip=True).upper()
        
        # Pular linhas vazias ou de cabeçalho
        if not produto or produto in ['PRODUTOS', 'PRODUTO']:
            continue
        
        # Extrair preço para cada região
        for i, regiao in enumerate(regioes):
            if i + 2 < len(cells):
                preco_text = cells[i + 2].get_text(strip=True)
                
                # Limpar e converter preço
                preco_text = preco_text.replace('R$', '').replace('.', '').replace(',', '.').strip()
                
                # Pular valores vazios ou traços
                if not preco_text or preco_text in ['-', '----', '']:
                    continue
                
                try:
                    preco = float(preco_text)
                    if preco <= 0:
                        continue
                except ValueError:
                    continue
                
                rows.append({
                    'data_coleta': data_coleta,
                    'origem': 'MG',
                    'produto': normalize_product_name(produto),
                    'embalagem': normalize_embalagem(embalagem),
                    'preco_min': None,
                    'preco_comum': preco,
                    'preco_max': None,
                    'regiao': regiao.upper(),
                    'fonte': URL_MG
                })
    
    df = pd.DataFrame(rows)
    print(f"[CEASA-MG] {len(df)} registros extraídos")
    return df

def normalize_product_name(name):
    """Normaliza nome do produto"""
    name = name.upper().strip()
    # Remover acentos
    name = name.replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
    name = name.replace('À', 'A').replace('Ê', 'E').replace('Ô', 'O')
    name = name.replace('Ã', 'A').replace('Õ', 'O')
    name = name.replace('Ç', 'C')
    # Remover espaços extras
    name = ' '.join(name.split())
    return name

def normalize_embalagem(emb):
    """Normaliza tipo de embalagem"""
    emb = emb.upper().strip()
    mapping = {
        'KG': 'KG',
        'QUILO': 'KG',
        'DZ': 'DZ',
        'DZ.': 'DZ',
        'DÚZIA': 'DZ',
        'UN': 'UN',
        'UN.': 'UN',
        'UNID': 'UN',
        'UNID.': 'UN',
        'UNIDADE': 'UN',
        'CX': 'CX',
        'CX.': 'CX',
        'CAIXA': 'CX',
        'SC': 'SC',
        'SACA': 'SC',
    }
    return mapping.get(emb, emb)

if __name__ == '__main__':
    df = fetch_ceasa_mg()
    print(f"\nTotal de registros: {len(df)}")
    print(f"\nPrimeiros registros:")
    print(df.head(10))
    print(f"\nProdutos únicos: {df['produto'].nunique()}")
    print(f"Regiões: {df['regiao'].unique().tolist()}")
