import sqlite3
conn = sqlite3.connect('nia_flv.db')
cursor = conn.cursor()

# Verificar tabelas de notícias
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print('Tabelas disponíveis:')
for t in tables:
    print(f'  - {t}')

if 'flv_news_global' in tables:
    cursor.execute("SELECT COUNT(*) FROM flv_news_global")
    count = cursor.fetchone()[0]
    print(f'\nTotal de notícias: {count}')
    
    if count == 0:
        print('\nInserindo notícias de exemplo...')
        news = [
            ('Reuters', 'Soja sobe 3% com demanda de exportação da China', 'https://reuters.com/soja', 'commodities', 'positivo', 0.8, '2026-04-26 14:30:00'),
            ('Bloomberg', 'Clima irregular afeta safra de milho no Centro-Oeste', 'https://bloomberg.com/milho', 'clima', 'negativo', -0.6, '2026-04-26 13:15:00'),
            ('BBC', 'Preço do café atinge máxima de 2 anos em Nova York', 'https://bbc.com/cafe', 'mercado', 'positivo', 0.7, '2026-04-26 12:00:00'),
            ('Reuters', 'Argentina aumenta exportações de trigo para Brasil', 'https://reuters.com/trigo', 'exportacao', 'neutro', 0.2, '2026-04-26 10:45:00'),
            ('Bloomberg', 'Fertilizantes: preços caem 12% no trimestre', 'https://bloomberg.com/fertilizantes', 'insumos', 'positivo', 0.5, '2026-04-26 09:30:00'),
        ]
        cursor.executemany("""
            INSERT INTO flv_news_global (source, title, url, category, sentiment, sentiment_score, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, news)
        conn.commit()
        print('Notícias inseridas com sucesso!')
    else:
        cursor.execute("SELECT source, title, published_at FROM flv_news_global ORDER BY published_at DESC LIMIT 3")
        print('\nÚltimas notícias:')
        for row in cursor.fetchall():
            print(f'  [{row[0]}] {row[1][:50]}... ({row[2]})')
else:
    print('\nCriando tabela flv_news_global...')
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flv_news_global (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            title TEXT,
            url TEXT,
            category TEXT,
            sentiment TEXT,
            sentiment_score REAL,
            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    print('Tabela criada!')

conn.close()
