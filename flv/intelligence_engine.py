"""
NiasIntelligenceEngine — Motor de Inteligência Agrocomercial NIA$
================================================================
Responsabilidades:
1. Coletar dados reais (CEASA, clima, macro, news)
2. Validar fontes e atribuir confiança
3. Detectar anomalias e oportunidades
4. Gerar previsões com explicação humana
5. Produzir alertas acionáveis
6. Manter memória analítica (aprendizado)
7. Gerar relatório executivo diário
"""
from __future__ import annotations
import json, os, time, sqlite3
from datetime import datetime, timedelta
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.environ.get('NIAS_DB_PATH') or os.path.join(_ROOT, 'data', 'nia_flv.db')

def _conn():
    c = sqlite3.connect(_DB_PATH, check_same_thread=False, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def _ensure_tables(conn):
    """Garante tabelas do motor de inteligência."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS nias_opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto TEXT NOT NULL,
        regiao TEXT,
        tipo TEXT NOT NULL,
        score INTEGER NOT NULL,
        margem_potencial TEXT,
        urgencia TEXT DEFAULT 'media',
        risco TEXT DEFAULT 'medio',
        confianca TEXT DEFAULT 'media',
        motivos TEXT,
        acao_recomendada TEXT,
        fontes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS nias_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto TEXT NOT NULL,
        regiao TEXT,
        horizonte TEXT NOT NULL,
        tendencia TEXT NOT NULL,
        confianca TEXT DEFAULT 'media',
        explicacao TEXT,
        sinais TEXT,
        fontes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS nias_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        prioridade TEXT DEFAULT 'media',
        explicacao TEXT,
        acao_recomendada TEXT,
        confianca TEXT,
        fontes TEXT,
        lido INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS nias_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto TEXT NOT NULL,
        regiao TEXT,
        previsao_anterior TEXT,
        resultado_real TEXT,
        acerto INTEGER,
        aprendizado TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS nias_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_date TEXT NOT NULL,
        resumo TEXT,
        oportunidades TEXT,
        riscos TEXT,
        tendencias TEXT,
        acoes TEXT,
        confianca_geral TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════════
# MOTOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

class NiasIntelligenceEngine:
    """Núcleo autônomo de inteligência agrocomercial."""

    def __init__(self):
        self.conn = _conn()
        _ensure_tables(self.conn)

    # ─── COLETA E VALIDAÇÃO ───────────────────────────────────────────

    def _get_latest_prices(self) -> list[dict]:
        """Busca preços mais recentes por cultura (usa dados mais recentes disponíveis)."""
        try:
            # Primeiro descobre a data mais recente disponível
            max_date_row = self.conn.execute(
                "SELECT MAX(price_date) as md FROM flv_ceasa_prices"
            ).fetchone()
            max_date = max_date_row['md'] if max_date_row else None
            if not max_date:
                return []

            rows = self.conn.execute("""
                SELECT c.slug, c.name_pt as name, p.price_avg, p.price_min, p.price_max,
                       p.terminal, p.price_date, p.source,
                       COALESCE(p.is_synthetic, 0) as is_synthetic
                FROM flv_ceasa_prices p
                JOIN flv_cultures c ON c.id = p.culture_id
                WHERE p.price_date >= date(?, '-7 days')
                ORDER BY c.slug, p.price_date DESC
            """, (max_date,)).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _get_climate_context(self) -> dict:
        """Contexto climático recente (usa dados mais recentes disponíveis)."""
        try:
            max_row = self.conn.execute("SELECT MAX(obs_date) as md FROM flv_climate").fetchone()
            max_date = max_row['md'] if max_row else None
            if not max_date:
                return {}
            row = self.conn.execute("""
                SELECT AVG(temp_max_c) as avg_temp, AVG(precip_mm) as avg_precip,
                       MAX(temp_max_c) as max_temp, MAX(precip_mm) as max_precip,
                       COUNT(*) as obs_count
                FROM flv_climate
                WHERE obs_date >= date(?, '-7 days')
            """, (max_date,)).fetchone()
            return dict(row) if row else {}
        except Exception:
            return {}

    def _get_macro_context(self) -> dict:
        """Indicadores macro recentes."""
        try:
            row = self.conn.execute("""
                SELECT * FROM flv_macro_indicators
                ORDER BY obs_date DESC LIMIT 1
            """).fetchone()
            return dict(row) if row else {}
        except Exception:
            return {}

    def _get_news_risk(self) -> float:
        """Índice de risco de notícias (0-1)."""
        try:
            row = self.conn.execute("""
                SELECT risk_index FROM flv_news_risk_daily
                ORDER BY obs_date DESC LIMIT 1
            """).fetchone()
            return float(row['risk_index']) if row else 0.0
        except Exception:
            return 0.0

    def _get_price_history(self, slug: str, days: int = 30) -> list[dict]:
        """Histórico de preços para análise de tendência (usa dados mais recentes)."""
        try:
            max_row = self.conn.execute("""
                SELECT MAX(p.price_date) as md FROM flv_ceasa_prices p
                JOIN flv_cultures c ON c.id = p.culture_id WHERE c.slug = ?
            """, (slug,)).fetchone()
            max_date = max_row['md'] if max_row else None
            if not max_date:
                return []
            rows = self.conn.execute("""
                SELECT p.price_date as date, p.price_avg as price
                FROM flv_ceasa_prices p
                JOIN flv_cultures c ON c.id = p.culture_id
                WHERE c.slug = ? AND p.price_date >= date(?, ?)
                ORDER BY p.price_date
            """, (slug, max_date, f'-{days} days')).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    # ─── ANÁLISE DE TENDÊNCIA ─────────────────────────────────────────

    def _calculate_trend(self, prices: list[dict]) -> dict:
        """Calcula tendência com variação percentual e direção."""
        if len(prices) < 3:
            return {'direction': 'incerto', 'change_pct': 0, 'volatility': 0, 'confidence': 'baixa'}

        values = [p['price'] for p in prices if p.get('price')]
        if len(values) < 3:
            return {'direction': 'incerto', 'change_pct': 0, 'volatility': 0, 'confidence': 'baixa'}

        # Variação recente (últimos 7 vs anteriores)
        recent = values[-min(7, len(values)//2):]
        older = values[:max(3, len(values)//2)]
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        change_pct = ((avg_recent - avg_older) / avg_older * 100) if avg_older > 0 else 0

        # Volatilidade (CV%)
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = variance ** 0.5
        cv = (std / mean * 100) if mean > 0 else 0

        # Direção
        if change_pct > 5:
            direction = 'alta'
        elif change_pct < -5:
            direction = 'queda'
        else:
            direction = 'estabilidade'

        # Confiança baseada em volume de dados e consistência
        confidence = 'alta' if len(values) >= 20 and cv < 15 else 'media' if len(values) >= 7 else 'baixa'

        return {
            'direction': direction,
            'change_pct': round(change_pct, 1),
            'volatility': round(cv, 1),
            'confidence': confidence,
            'data_points': len(values)
        }

    # ─── MOTOR DE OPORTUNIDADES ───────────────────────────────────────

    def generate_opportunities(self) -> list[dict]:
        """Gera score de oportunidade por produto/região."""
        prices = self._get_latest_prices()
        climate = self._get_climate_context()
        macro = self._get_macro_context()
        news_risk = self._get_news_risk()

        # Agrupar por produto
        products = {}
        for p in prices:
            slug = p['slug']
            if slug not in products:
                products[slug] = {'name': p['name'], 'prices': [], 'terminals': set()}
            products[slug]['prices'].append(p)
            products[slug]['terminals'].add(p.get('terminal', ''))

        opportunities = []
        for slug, data in products.items():
            history = self._get_price_history(slug, 30)
            trend = self._calculate_trend(history)

            # Calcular score de oportunidade (0-100)
            score = 50  # base
            motivos = []
            tipo = 'alerta'

            # Fator: tendência de preço
            if trend['direction'] == 'alta':
                score += 15
                motivos.append(f"Tendência de alta ({trend['change_pct']:+.1f}% nos últimos dias)")
                tipo = 'venda'
            elif trend['direction'] == 'queda':
                score += 10
                motivos.append(f"Preço em queda ({trend['change_pct']:+.1f}%) — possível ponto de compra")
                tipo = 'compra'

            # Fator: volatilidade
            if trend['volatility'] > 20:
                score += 10
                motivos.append(f"Alta volatilidade ({trend['volatility']:.1f}% CV) — mercado instável")
            elif trend['volatility'] < 8:
                score -= 5

            # Fator: clima
            avg_temp = climate.get('avg_temp') or 0
            avg_precip = climate.get('avg_precip') or 0
            if avg_temp > 34:
                score += 8
                motivos.append("Estresse térmico elevado — risco para oferta")
            if avg_precip > 20:
                score += 5
                motivos.append("Chuvas acima da média — possível impacto em colheita/logística")

            # Fator: notícias
            if news_risk > 0.6:
                score += 10
                motivos.append("Índice de risco de notícias elevado — pressão externa")
            elif news_risk > 0.35:
                score += 5
                motivos.append("Risco moderado no noticiário")

            # Fator: macro (diesel/câmbio)
            diesel_chg = float(macro.get('diesel_change_pct') or 0)
            if diesel_chg > 2:
                score += 5
                motivos.append(f"Diesel em alta ({diesel_chg:+.1f}%) — pressão em frete")

            score = max(0, min(100, score))

            # Urgência e risco
            urgencia = 'alta' if score >= 75 else 'media' if score >= 50 else 'baixa'
            risco = 'alto' if trend['volatility'] > 25 else 'medio' if trend['volatility'] > 12 else 'baixo'

            # Ação recomendada
            if tipo == 'venda' and score >= 65:
                acao = f"Considerar venda de {data['name']} em praças com menor oferta. Preço em tendência de alta."
            elif tipo == 'compra' and score >= 60:
                acao = f"Oportunidade de compra de {data['name']} em queda. Monitorar reversão."
            else:
                acao = f"Monitorar {data['name']}. Dados insuficientes para recomendação forte."

            # Fontes
            fontes = []
            if any(not p.get('is_synthetic') for p in data['prices']):
                fontes.append('CEASA/CONAB (preço real)')
            else:
                fontes.append('CEASA (estimativa)')
            if climate.get('obs_count'):
                fontes.append('INMET/Open-Meteo (clima)')
            if macro.get('obs_date'):
                fontes.append('BCB/ANP (macro)')

            opp = {
                'produto': slug,
                'nome': data['name'],
                'regiao': ', '.join(t for t in data['terminals'] if t)[:60] or 'Brasil',
                'tipo': tipo,
                'score': score,
                'margem_potencial': f"{abs(trend['change_pct']):.1f}% em {trend.get('data_points',7)} dias",
                'urgencia': urgencia,
                'risco': risco,
                'confianca': trend['confidence'],
                'motivos': motivos,
                'acao_recomendada': acao,
                'fontes': fontes,
                'tendencia': trend,
                'atualizado_em': datetime.now().isoformat()
            }
            opportunities.append(opp)

        # Ordenar por score
        opportunities.sort(key=lambda x: x['score'], reverse=True)

        # Persistir top oportunidades
        for opp in opportunities[:10]:
            try:
                self.conn.execute("""
                    INSERT INTO nias_opportunities (produto, regiao, tipo, score, margem_potencial,
                        urgencia, risco, confianca, motivos, acao_recomendada, fontes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (opp['produto'], opp['regiao'], opp['tipo'], opp['score'],
                      opp['margem_potencial'], opp['urgencia'], opp['risco'], opp['confianca'],
                      json.dumps(opp['motivos'], ensure_ascii=False),
                      opp['acao_recomendada'],
                      json.dumps(opp['fontes'], ensure_ascii=False)))
            except Exception:
                pass
        try:
            self.conn.commit()
        except Exception:
            pass

        return opportunities

    # ─── MOTOR DE PREVISÃO ────────────────────────────────────────────

    def generate_predictions(self) -> list[dict]:
        """Gera previsões por produto com explicação humana."""
        predictions = []

        try:
            cultures = self.conn.execute("SELECT slug, name_pt as name FROM flv_cultures").fetchall()
        except Exception:
            return []

        climate = self._get_climate_context()
        macro = self._get_macro_context()
        news_risk = self._get_news_risk()

        for culture in cultures:
            slug = culture['slug']
            name = culture['name']
            history = self._get_price_history(slug, 30)
            trend = self._calculate_trend(history)

            if trend['direction'] == 'incerto' and len(history) < 3:
                continue

            # Sinais detectados
            sinais = []
            if trend['direction'] == 'alta':
                sinais.append(f"Preço em alta de {trend['change_pct']:+.1f}%")
            elif trend['direction'] == 'queda':
                sinais.append(f"Preço em queda de {trend['change_pct']:+.1f}%")

            avg_temp = climate.get('avg_temp') or 0
            if avg_temp > 33:
                sinais.append(f"Temperatura elevada ({avg_temp:.1f}°C)")
            avg_precip = climate.get('avg_precip') or 0
            if avg_precip > 15:
                sinais.append(f"Precipitação acima da média ({avg_precip:.1f}mm)")

            if news_risk > 0.5:
                sinais.append(f"Risco de notícias elevado ({news_risk:.2f})")

            diesel_chg = float(macro.get('diesel_change_pct') or 0)
            if abs(diesel_chg) > 1.5:
                sinais.append(f"Diesel {'em alta' if diesel_chg > 0 else 'em queda'} ({diesel_chg:+.1f}%)")

            # Gerar explicação em linguagem humana
            explicacao = self._build_human_explanation(name, trend, climate, macro, news_risk)

            # Fontes
            fontes = ['CEASA/CONAB (preços)', 'INMET (clima)']
            if macro.get('obs_date'):
                fontes.append('BCB/ANP (macro)')

            pred = {
                'produto': slug,
                'nome': name,
                'regiao': 'Brasil',
                'horizonte': '7 dias',
                'tendencia': trend['direction'],
                'variacao_esperada': f"{trend['change_pct']:+.1f}%",
                'confianca': trend['confidence'],
                'explicacao': explicacao,
                'sinais_detectados': sinais,
                'fontes': fontes,
                'data_analise': datetime.now().isoformat()
            }
            predictions.append(pred)

            # Persistir
            try:
                self.conn.execute("""
                    INSERT INTO nias_predictions (produto, regiao, horizonte, tendencia,
                        confianca, explicacao, sinais, fontes)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (slug, 'Brasil', '7 dias', trend['direction'], trend['confidence'],
                      explicacao, json.dumps(sinais, ensure_ascii=False),
                      json.dumps(fontes, ensure_ascii=False)))
            except Exception:
                pass

        try:
            self.conn.commit()
        except Exception:
            pass

        return predictions

    def _build_human_explanation(self, name: str, trend: dict, climate: dict, macro: dict, news_risk: float) -> str:
        """Traduz dados técnicos em análise clara para o usuário."""
        parts = []

        # Resumo principal
        if trend['direction'] == 'alta':
            parts.append(f"O mercado de {name} mostra sinal de valorização no curto prazo.")
        elif trend['direction'] == 'queda':
            parts.append(f"O mercado de {name} apresenta tendência de queda nos próximos dias.")
        else:
            parts.append(f"O mercado de {name} segue relativamente estável, sem pressão clara de alta ou baixa.")

        # Causa provável
        causas = []
        avg_temp = climate.get('avg_temp') or 0
        avg_precip = climate.get('avg_precip') or 0
        if avg_temp > 33:
            causas.append("calor intenso nas regiões produtoras pode comprometer a oferta")
        if avg_precip > 20:
            causas.append("chuvas excessivas dificultam a colheita e a logística")
        if news_risk > 0.5:
            causas.append("o noticiário aponta pressão em custos e cadeia de suprimento")
        diesel_chg = float(macro.get('diesel_change_pct') or 0)
        if diesel_chg > 2:
            causas.append("o diesel em alta eleva o custo de transporte")

        if causas:
            parts.append("Isso se deve a " + ", ".join(causas[:3]) + ".")
        elif trend['direction'] != 'estabilidade':
            parts.append("Os dados indicam movimento de mercado, mas sem causa climática ou macro dominante clara.")

        # Oportunidade/Risco
        if trend['direction'] == 'alta':
            parts.append("A oportunidade está em antecipar vendas ou reposicionar estoques antes de nova alta.")
            parts.append("O risco é operar com preço antigo enquanto o mercado já está virando.")
        elif trend['direction'] == 'queda':
            parts.append("Pode haver oportunidade de compra se a queda estabilizar nos próximos dias.")
            parts.append("O risco é comprar cedo demais se a tendência de baixa continuar.")

        # Confiança
        if trend['confidence'] == 'alta':
            parts.append(f"Confiança alta: baseado em {trend.get('data_points', 0)} observações com volatilidade controlada.")
        elif trend['confidence'] == 'media':
            parts.append("Confiança média: dados indicam tendência, mas dependem de confirmação nas próximas cotações.")
        else:
            parts.append("Confiança baixa: poucos dados disponíveis. Acompanhar diariamente antes de agir.")

        return " ".join(parts)

    # ─── ALERTAS INTELIGENTES ─────────────────────────────────────────

    def generate_alerts(self) -> list[dict]:
        """Gera alertas acionáveis baseados em anomalias detectadas."""
        alerts = []
        climate = self._get_climate_context()
        macro = self._get_macro_context()
        news_risk = self._get_news_risk()

        # Alerta climático
        max_temp = climate.get('max_temp') or 0
        if max_temp > 38:
            alerts.append({
                'titulo': f'Estresse térmico extremo detectado ({max_temp:.1f}°C)',
                'prioridade': 'alta',
                'explicacao': 'Temperaturas acima de 38°C prejudicam folhosas, tomate e morango. Espere redução de oferta e alta de preço em 3-5 dias.',
                'acao_recomendada': 'Antecipar compras de hortifruti perecível. Priorizar fornecedores em regiões menos afetadas.',
                'confianca': 'alta',
                'fontes': ['INMET', 'Open-Meteo']
            })

        max_precip = climate.get('max_precip') or 0
        if max_precip > 50:
            alerts.append({
                'titulo': f'Chuvas intensas ({max_precip:.0f}mm) — risco logístico',
                'prioridade': 'alta',
                'explicacao': 'Precipitação extrema pode bloquear rodovias e causar perdas em campo. Colheita prejudicada.',
                'acao_recomendada': 'Verificar status de rodovias. Considerar rotas alternativas. Antecipar pedidos.',
                'confianca': 'alta',
                'fontes': ['INMET', 'PRF']
            })

        # Alerta macro
        diesel_chg = float(macro.get('diesel_change_pct') or 0)
        if diesel_chg > 3:
            alerts.append({
                'titulo': f'Alta abrupta do diesel (+{diesel_chg:.1f}%)',
                'prioridade': 'media',
                'explicacao': 'Aumento no diesel impacta diretamente o frete. Produtos de longa distância ficam mais caros.',
                'acao_recomendada': 'Reprecificar fretes. Priorizar fornecedores próximos.',
                'confianca': 'alta',
                'fontes': ['ANP', 'NTC&Logística']
            })

        # Alerta de notícias
        if news_risk > 0.7:
            alerts.append({
                'titulo': 'Risco elevado no noticiário agrícola',
                'prioridade': 'media',
                'explicacao': 'Monitoramento de notícias indica pressão significativa (greves, geopolítica, clima). Mercado pode reagir.',
                'acao_recomendada': 'Monitorar fontes oficiais. Evitar posições agressivas até confirmação.',
                'confianca': 'media',
                'fontes': ['NewsAPI', 'Google News', 'Portais agro']
            })

        # Alertas por produto (anomalia de preço)
        try:
            # Usar data mais recente disponível
            max_row = self.conn.execute("SELECT MAX(price_date) as md FROM flv_ceasa_prices").fetchone()
            ref_date = max_row['md'] if max_row else None
            if ref_date:
                rows = self.conn.execute("""
                    SELECT c.slug, c.name_pt as name, p.price_avg,
                           (SELECT AVG(p2.price_avg) FROM flv_ceasa_prices p2
                            WHERE p2.culture_id = c.id AND p2.price_date >= date(?, '-30 days')) as avg_30d
                    FROM flv_ceasa_prices p
                    JOIN flv_cultures c ON c.id = p.culture_id
                    WHERE p.price_date >= date(?, '-2 days')
                    GROUP BY c.slug
                    HAVING p.price_avg > avg_30d * 1.20 OR p.price_avg < avg_30d * 0.80
                """, (ref_date, ref_date)).fetchall()

                for r in rows:
                    price = r['price_avg']
                    avg = r['avg_30d']
                    if price and avg and avg > 0:
                        var = ((price - avg) / avg * 100)
                        if var > 20:
                            alerts.append({
                                'titulo': f'{r["name"]}: preço {var:+.0f}% acima da média de 30 dias',
                                'prioridade': 'alta',
                                'explicacao': f'Preço atual (R$ {price:.2f}) muito acima da média (R$ {avg:.2f}). Pode indicar escassez.',
                                'acao_recomendada': f'Se é comprador: buscar alternativas ou antecipar antes de nova alta. Se é vendedor: momento oportuno.',
                                'confianca': 'alta',
                                'fontes': ['CEASA/CONAB']
                            })
                        elif var < -20:
                            alerts.append({
                                'titulo': f'{r["name"]}: preço {var:+.0f}% abaixo da média de 30 dias',
                                'prioridade': 'media',
                                'explicacao': f'Preço atual (R$ {price:.2f}) muito abaixo da média (R$ {avg:.2f}). Pode indicar excesso de oferta.',
                                'acao_recomendada': f'Se é comprador: bom momento para estocar. Se é vendedor: avaliar reter ou buscar praças com menor oferta.',
                                'confianca': 'media',
                                'fontes': ['CEASA/CONAB']
                            })
        except Exception:
            pass

        # Persistir alertas
        for a in alerts:
            try:
                self.conn.execute("""
                    INSERT INTO nias_alerts (titulo, prioridade, explicacao, acao_recomendada, confianca, fontes)
                    VALUES (?,?,?,?,?,?)
                """, (a['titulo'], a['prioridade'], a['explicacao'],
                      a['acao_recomendada'], a['confianca'],
                      json.dumps(a['fontes'], ensure_ascii=False)))
            except Exception:
                pass
        try:
            self.conn.commit()
        except Exception:
            pass

        return alerts

    # ─── RELATÓRIO EXECUTIVO ──────────────────────────────────────────

    def generate_executive_report(self) -> dict:
        """Gera relatório executivo diário em linguagem clara."""
        opportunities = self.generate_opportunities()
        predictions = self.generate_predictions()
        alerts = self.generate_alerts()

        # Top oportunidades
        top_opps = [
            f"• {o['nome']} ({o['tipo'].upper()}, score {o['score']}): {o['acao_recomendada']}"
            for o in opportunities[:5]
        ]

        # Principais riscos
        riscos = [a for a in alerts if a['prioridade'] in ('alta', 'critica')]
        top_risks = [f"• {r['titulo']}: {r['explicacao'][:100]}" for r in riscos[:3]]

        # Tendências
        altas = [p for p in predictions if p['tendencia'] == 'alta']
        quedas = [p for p in predictions if p['tendencia'] == 'queda']

        resumo_parts = []
        if altas:
            nomes_alta = ', '.join(p['nome'] for p in altas[:4])
            resumo_parts.append(f"Produtos com sinal de alta: {nomes_alta}.")
        if quedas:
            nomes_queda = ', '.join(p['nome'] for p in quedas[:4])
            resumo_parts.append(f"Produtos com sinal de queda: {nomes_queda}.")
        if alerts:
            resumo_parts.append(f"Há {len(alerts)} alertas ativos, {len(riscos)} de prioridade alta.")

        resumo = " ".join(resumo_parts) if resumo_parts else "Mercado sem movimentos significativos detectados hoje."

        # Ações recomendadas
        acoes = []
        for o in opportunities[:3]:
            if o['score'] >= 60:
                acoes.append(o['acao_recomendada'])

        # Confiança geral
        confiancas = [p['confianca'] for p in predictions]
        alta_count = confiancas.count('alta')
        confianca_geral = 'alta' if alta_count > len(confiancas) / 2 else 'media' if confiancas else 'baixa'

        report = {
            'data': datetime.now().strftime('%Y-%m-%d'),
            'hora': datetime.now().strftime('%H:%M'),
            'resumo': resumo,
            'oportunidades': top_opps,
            'riscos': top_risks if top_risks else ['Nenhum risco de alta prioridade detectado.'],
            'tendencias': {
                'alta': [{'produto': p['nome'], 'variacao': p['variacao_esperada']} for p in altas[:5]],
                'queda': [{'produto': p['nome'], 'variacao': p['variacao_esperada']} for p in quedas[:5]],
                'estavel': [p['nome'] for p in predictions if p['tendencia'] == 'estabilidade'][:5]
            },
            'acoes_recomendadas': acoes if acoes else ['Manter monitoramento. Sem oportunidade forte identificada hoje.'],
            'confianca_geral': confianca_geral,
            'total_produtos_analisados': len(predictions),
            'total_oportunidades': len(opportunities),
            'total_alertas': len(alerts),
            'fontes_consultadas': ['CEASA/CONAB', 'INMET/Open-Meteo', 'BCB/ANP', 'NewsAPI'],
            'gerado_em': datetime.now().isoformat()
        }

        # Persistir relatório
        try:
            self.conn.execute("""
                INSERT INTO nias_reports (report_date, resumo, oportunidades, riscos, tendencias, acoes, confianca_geral)
                VALUES (?,?,?,?,?,?,?)
            """, (report['data'], report['resumo'],
                  json.dumps(report['oportunidades'], ensure_ascii=False),
                  json.dumps(report['riscos'], ensure_ascii=False),
                  json.dumps(report['tendencias'], ensure_ascii=False),
                  json.dumps(report['acoes_recomendadas'], ensure_ascii=False),
                  report['confianca_geral']))
            self.conn.commit()
        except Exception:
            pass

        return report

    # ─── MEMÓRIA ANALÍTICA ────────────────────────────────────────────

    def check_prediction_accuracy(self) -> list[dict]:
        """Compara previsões anteriores com resultados reais e registra aprendizado."""
        results = []
        try:
            # Buscar previsões de 7+ dias atrás
            old_preds = self.conn.execute("""
                SELECT * FROM nias_predictions
                WHERE created_at <= datetime('now', '-7 days')
                AND produto NOT IN (SELECT produto FROM nias_memory WHERE created_at > datetime('now', '-7 days'))
                ORDER BY created_at DESC LIMIT 20
            """).fetchall()

            for pred in old_preds:
                slug = pred['produto']
                # Verificar preço atual vs tendência prevista
                history = self._get_price_history(slug, 7)
                if len(history) < 2:
                    continue

                current_trend = self._calculate_trend(history)
                predicted = pred['tendencia']
                actual = current_trend['direction']
                acerto = (predicted == actual)

                aprendizado = ""
                if acerto:
                    aprendizado = f"Previsão de {predicted} confirmada. Sinais usados estavam corretos."
                else:
                    aprendizado = f"Previsto {predicted}, resultado foi {actual}. Revisar peso dos sinais."

                memory = {
                    'produto': slug,
                    'regiao': pred['regiao'],
                    'previsao_anterior': predicted,
                    'resultado_real': actual,
                    'acerto': acerto,
                    'aprendizado': aprendizado
                }
                results.append(memory)

                self.conn.execute("""
                    INSERT INTO nias_memory (produto, regiao, previsao_anterior, resultado_real, acerto, aprendizado)
                    VALUES (?,?,?,?,?,?)
                """, (slug, pred['regiao'], predicted, actual, 1 if acerto else 0, aprendizado))

            self.conn.commit()
        except Exception:
            pass

        return results

    def get_accuracy_stats(self) -> dict:
        """Retorna estatísticas de acerto."""
        try:
            row = self.conn.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN acerto = 1 THEN 1 ELSE 0 END) as acertos
                FROM nias_memory
            """).fetchone()
            total = row['total'] or 0
            acertos = row['acertos'] or 0
            return {
                'total_verificados': total,
                'acertos': acertos,
                'taxa_acerto': f"{(acertos/total*100):.1f}%" if total > 0 else 'N/A',
                'status': 'aprendendo' if total < 20 else 'calibrado'
            }
        except Exception:
            return {'total_verificados': 0, 'acertos': 0, 'taxa_acerto': 'N/A', 'status': 'iniciando'}

    # ─── CICLO COMPLETO ───────────────────────────────────────────────

    def run_full_cycle(self) -> dict:
        """Executa ciclo completo de inteligência."""
        t0 = time.time()

        # 1. Verificar acurácia de previsões antigas
        accuracy_results = self.check_prediction_accuracy()

        # 2. Gerar relatório executivo (inclui oportunidades, previsões, alertas)
        report = self.generate_executive_report()

        # 3. Stats
        accuracy_stats = self.get_accuracy_stats()

        elapsed = time.time() - t0

        return {
            'status': 'ok',
            'cycle_time_seconds': round(elapsed, 2),
            'report': report,
            'accuracy': accuracy_stats,
            'memory_updates': len(accuracy_results),
            'timestamp': datetime.now().isoformat()
        }


# ═══════════════════════════════════════════════════════════════════════════
# API HELPER (para uso direto pelo server.py)
# ═══════════════════════════════════════════════════════════════════════════

_engine_instance = None

def get_engine() -> NiasIntelligenceEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = NiasIntelligenceEngine()
    return _engine_instance
