"""
CEASA Consolidador — Unifica cotações de MG, GO, BA em CSV único
"""
import pandas as pd
import os
from datetime import datetime
import sqlite3

# Importar coletores
from flv.collectors.ceasa_mg import fetch_ceasa_mg
from flv.collectors.ceasa_go import fetch_ceasa_go
from flv.collectors.ceasa_ba import fetch_ceasa_ba

# Diretórios de saída
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'ceasa')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')
DB_PATH = os.path.join(DATA_DIR, 'ceasa.db')

def ensure_dirs():
    """Garante que os diretórios existam"""
    for d in [DATA_DIR, RAW_DIR, PROCESSED_DIR]:
        os.makedirs(d, exist_ok=True)

def coletar_todos():
    """Executa coleta de todas as CEASAs"""
    print("=" * 60)
    print(f"COLETA CEASA — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    resultados = {}
    
    # Coletar MG
    print("\n[1/3] Coletando CEASA-MG...")
    try:
        df_mg = fetch_ceasa_mg()
        resultados['MG'] = df_mg
        print(f"      ✓ {len(df_mg)} registros")
    except Exception as e:
        print(f"      ✗ Erro: {e}")
        resultados['MG'] = pd.DataFrame()
    
    # Coletar GO
    print("\n[2/3] Coletando CEASA-GO...")
    try:
        df_go = fetch_ceasa_go()
        resultados['GO'] = df_go
        print(f"      ✓ {len(df_go)} registros")
    except Exception as e:
        print(f"      ✗ Erro: {e}")
        resultados['GO'] = pd.DataFrame()
    
    # Coletar BA
    print("\n[3/3] Coletando CEASA-BA...")
    try:
        df_ba = fetch_ceasa_ba()
        resultados['BA'] = df_ba
        print(f"      ✓ {len(df_ba)} registros")
    except Exception as e:
        print(f"      ✗ Erro: {e}")
        resultados['BA'] = pd.DataFrame()
    
    return resultados

def consolidar(resultados):
    """Consolida todos os DataFrames em um único"""
    print("\n" + "=" * 60)
    print("CONSOLIDAÇÃO")
    print("=" * 60)
    
    # Combinar todos os DataFrames
    dfs = [df for df in resultados.values() if len(df) > 0]
    
    if not dfs:
        print("✗ Nenhum dado coletado")
        return pd.DataFrame()
    
    df_consolidado = pd.concat(dfs, ignore_index=True)
    
    # Garantir colunas padronizadas
    colunas_esperadas = ['data_coleta', 'origem', 'produto', 'embalagem', 
                         'preco_min', 'preco_comum', 'preco_max', 'regiao', 'fonte']
    
    for col in colunas_esperadas:
        if col not in df_consolidado.columns:
            df_consolidado[col] = None
    
    # Reordenar colunas
    df_consolidado = df_consolidado[colunas_esperadas]
    
    # Validar dados
    df_consolidado = validar_dados(df_consolidado)
    
    print(f"✓ Total consolidado: {len(df_consolidado)} registros")
    print(f"  - Origens: {df_consolidado['origem'].unique().tolist()}")
    print(f"  - Produtos únicos: {df_consolidado['produto'].nunique()}")
    print(f"  - Período: {df_consolidado['data_coleta'].min()} a {df_consolidado['data_coleta'].max()}")
    
    return df_consolidado

def validar_dados(df):
    """Valida e limpa os dados"""
    # Remover duplicatas
    antes = len(df)
    df = df.drop_duplicates(subset=['data_coleta', 'origem', 'produto', 'regiao'])
    if len(df) < antes:
        print(f"  - Duplicatas removidas: {antes - len(df)}")
    
    # Validar faixa de preços (R$ 0.01 a R$ 1000)
    df_valid = df[
        (df['preco_comum'].isna()) | 
        ((df['preco_comum'] >= 0.01) & (df['preco_comum'] <= 1000))
    ].copy()
    
    removidos = len(df) - len(df_valid)
    if removidos > 0:
        print(f"  - Registros com preço inválido removidos: {removidos}")
    
    # Normalizar strings
    df_valid['produto'] = df_valid['produto'].astype(str).str.upper().str.strip()
    df_valid['embalagem'] = df_valid['embalagem'].astype(str).str.upper().str.strip()
    df_valid['regiao'] = df_valid['regiao'].astype(str).str.upper().str.strip()
    
    return df_valid

def salvar_csv(df, filename=None):
    """Salva DataFrame em CSV"""
    if filename is None:
        filename = f"ceasa_consolidado_{datetime.now().strftime('%Y%m%d')}.csv"
    
    filepath = os.path.join(PROCESSED_DIR, filename)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    print(f"\n✓ CSV salvo: {filepath}")
    return filepath

def salvar_sqlite(df):
    """Salva DataFrame no banco SQLite"""
    conn = sqlite3.connect(DB_PATH)
    
    # Criar tabela se não existir
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cotacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_coleta TEXT,
            origem TEXT,
            produto TEXT,
            embalagem TEXT,
            preco_min REAL,
            preco_comum REAL,
            preco_max REAL,
            regiao TEXT,
            fonte TEXT,
            data_insercao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Inserir dados
    df.to_sql('cotacoes', conn, if_exists='append', index=False)
    
    conn.commit()
    conn.close()
    print(f"✓ Dados salvos no SQLite: {DB_PATH}")

def gerar_resumo(df):
    """Gera resumo estatístico das cotações"""
    print("\n" + "=" * 60)
    print("RESUMO ESTATÍSTICO")
    print("=" * 60)
    
    # Por origem
    print("\nPor Origem:")
    for origem in df['origem'].unique():
        df_orig = df[df['origem'] == origem]
        print(f"  {origem}: {len(df_orig)} registros, {df_orig['produto'].nunique()} produtos")
    
    # Top 10 produtos mais caros (preço comum médio)
    print("\nTop 10 Produtos - Maior Preço Médio:")
    top_caros = df.groupby('produto')['preco_comum'].mean().sort_values(ascending=False).head(10)
    for produto, preco in top_caros.items():
        print(f"  {produto}: R$ {preco:.2f}")
    
    # Produtos com maior variação de preço entre estados
    print("\nProdutos com Maior Variação Entre Estados:")
    prod_multi = df[df.groupby('produto')['origem'].transform('nunique') > 1]
    if len(prod_multi) > 0:
        var_precos = prod_multi.groupby('produto')['preco_comum'].agg(['min', 'max', 'mean'])
        var_precos['variacao_pct'] = ((var_precos['max'] - var_precos['min']) / var_precos['mean'] * 100)
        top_var = var_precos.sort_values('variacao_pct', ascending=False).head(5)
        for produto, row in top_var.iterrows():
            print(f"  {produto}: {row['variacao_pct']:.1f}% (R$ {row['min']:.2f} - R$ {row['max']:.2f})")

def run_coleta_completa():
    """Executa pipeline completo de coleta e consolidação"""
    ensure_dirs()
    
    # Coletar dados
    resultados = coletar_todos()
    
    # Consolidar
    df_consolidado = consolidar(resultados)
    
    if len(df_consolidado) == 0:
        print("\n✗ Nenhum dado para salvar")
        return None
    
    # Salvar
    csv_path = salvar_csv(df_consolidado)
    salvar_sqlite(df_consolidado)
    
    # Gerar resumo
    gerar_resumo(df_consolidado)
    
    print("\n" + "=" * 60)
    print("COLETA CONCLUÍDA")
    print("=" * 60)
    
    return csv_path

if __name__ == '__main__':
    run_coleta_completa()
