"""
NiasAdvisorEngine — Motor de Inteligência Decisional da América do Sul.

Interpreta dados reais (clima, preços, regiões, frescor do pipeline)
e gera recomendações justificadas com tese, risco, cenário contrário
e nível de confiança. Nunca inventa dado; nunca promete retorno garantido.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════
# Constantes
# ═══════════════════════════════════════════════════════════════════════════

SCORE_WEIGHTS = {
    'trend_strength':      20,
    'data_quality':        15,
    'data_freshness':      15,
    'climate_impact':      20,
    'price_volatility':    10,
    'region_relevance':    10,
    'source_reliability':  10,
}

COUNTRIES = {
    'BR': 'Brasil',
    'AR': 'Argentina',
    'CL': 'Chile',
    'PE': 'Peru',
    'BO': 'Bolívia',
    'PY': 'Paraguai',
    'UY': 'Uruguai',
    'CO': 'Colômbia',
    'EC': 'Equador',
}

RISK_LABELS  = {0: 'baixo', 1: 'medio', 2: 'alto', 3: 'critico'}
CONF_LABELS  = {0: 'baixa', 1: 'media', 2: 'alta'}

# ═══════════════════════════════════════════════════════════════════════════
# Helpers internos
# ═══════════════════════════════════════════════════════════════════════════

def _days_ago(iso_date: Optional[str]) -> int:
    """Quantos dias atrás foi `iso_date` (YYYY-MM-DD). 999 se None."""
    if not iso_date:
        return 999
    try:
        d = date.fromisoformat(str(iso_date)[:10])
        return (date.today() - d).days
    except Exception:
        return 999


def _freshness_score(days: int) -> int:
    """0-15 baseado em quantos dias atrás foi coletado."""
    if days <= 1:  return 15
    if days <= 3:  return 10
    if days <= 7:  return 5
    return 0


def _climate_signals(w: dict) -> list[str]:
    """Detecta sinais climáticos críticos num ponto Open-Meteo."""
    signals = []
    t_max = w.get('temp_max_c')
    t_min = w.get('temp_min_c')
    prec  = w.get('precip_mm') or 0.0
    if t_max and t_max > 36:
        signals.append('calor extremo')
    if t_min is not None and t_min < 2:
        signals.append('risco de geada')
    if prec > 40:
        signals.append('chuva muito intensa')
    elif prec > 20:
        signals.append('chuva intensa')
    if prec == 0 and t_max and t_max > 30:
        signals.append('déficit hídrico')
    return signals


# ═══════════════════════════════════════════════════════════════════════════
# Engine principal
# ═══════════════════════════════════════════════════════════════════════════

class NiasAdvisorEngine:
    """
    Motor de conselho agrocomercial da América do Sul.
    Instanciar com uma conexão SQLite já aberta (WAL mode).
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._weather:    list[dict] = []
        self._prices:     list[dict] = []     # preços BR (CONAB)
        self._sa_prices:  list[dict] = []     # preços SA por país
        self._freshness:  dict = {}
        self._loaded = False

    # ── Carregamento de dados ──────────────────────────────────────────────

    def _load(self):
        if self._loaded:
            return
        self._load_weather()
        self._load_prices()
        self._load_sa_prices()
        self._load_freshness()
        self._loaded = True

    def _load_weather(self):
        try:
            from flv.sa_weather_persistence import get_latest_sa_weather
            self._weather = get_latest_sa_weather(self.conn)
        except Exception:
            self._weather = []

    def _load_prices(self):
        try:
            row = self.conn.execute(
                "SELECT MAX(price_date) as d FROM flv_ceasa_prices"
            ).fetchone()
            if not row or not row['d']:
                self._prices = []
                return
            rows = self.conn.execute("""
                SELECT c.slug, c.name_pt as product, p.terminal as market,
                       p.price_avg as price, p.price_min, p.price_max,
                       c.unit, p.price_date as date
                FROM flv_ceasa_prices p
                JOIN flv_cultures c ON c.id = p.culture_id
                WHERE p.price_date = ?
                ORDER BY c.name_pt
            """, (row['d'],)).fetchall()
            self._prices = [dict(r) for r in rows]
        except Exception:
            self._prices = []

    def _load_sa_prices(self):
        """Carrega preços SA do banco (nias_sa_prices)."""
        try:
            from flv.sa_price_persistence import get_latest_sa_prices, ensure_sa_prices_table
            ensure_sa_prices_table(self.conn)
            self._sa_prices = get_latest_sa_prices(self.conn)
        except Exception:
            self._sa_prices = []

    def _sa_price_for(self, country_code: str, product_normalized: str) -> Optional[dict]:
        """Busca preço SA para país + produto. Retorna None se não disponível."""
        cc = country_code.upper()
        pn = product_normalized.lower()
        for p in self._sa_prices:
            if p.get('country_code') == cc and p.get('product_normalized') == pn:
                return p
        return None

    def _has_sa_price(self, country_code: str) -> bool:
        """Verifica se há ao menos 1 preço real para o país."""
        cc = country_code.upper()
        return any(
            p.get('country_code') == cc and not p.get('is_fallback', 0)
            for p in self._sa_prices
        )

    def _load_freshness(self):
        try:
            from flv.scheduler import get_pipeline_freshness
            self._freshness = get_pipeline_freshness() or {}
        except Exception:
            self._freshness = {}

    # ── Score ──────────────────────────────────────────────────────────────

    def calculate_risk_return_score(self, data: dict) -> dict:
        """
        Calcula NIAS Decision Score (0-100) para um conselho.
        `data` deve ter: signals, days_old_price, days_old_weather,
                         region_importance, price_volatility_pct.
        """
        score = 0

        # Força da tendência (sinais climáticos)
        n_signals = len(data.get('signals', []))
        score += min(n_signals * 7, SCORE_WEIGHTS['trend_strength'])

        # Qualidade dos dados
        has_price   = bool(data.get('price'))
        has_weather = bool(data.get('weather'))
        dq = 0
        if has_price:   dq += 7
        if has_weather: dq += 8
        score += min(dq, SCORE_WEIGHTS['data_quality'])

        # Frescor
        days_p = data.get('days_old_price', 999)
        days_w = data.get('days_old_weather', 999)
        score += _freshness_score(min(days_p, days_w))

        # Impacto climático
        n_sig = len(data.get('signals', []))
        score += min(n_sig * 7, SCORE_WEIGHTS['climate_impact'])

        # Volatilidade de preço
        vol = data.get('price_volatility_pct', 0) or 0
        if vol > 20:   score += SCORE_WEIGHTS['price_volatility']
        elif vol > 10: score += 6
        elif vol > 5:  score += 3

        # Relevância da região
        imp = data.get('region_importance', 'normal')
        if imp == 'critico': score += SCORE_WEIGHTS['region_relevance']
        elif imp == 'alto':  score += 6
        else:                score += 3

        # Confiabilidade da fonte
        if has_price and days_p <= 3:    score += SCORE_WEIGHTS['source_reliability']
        elif has_weather and days_w <= 1: score += 6
        else:                             score += 2

        score = min(score, 100)

        if score >= 75:
            classif = 'oportunidade forte'
        elif score >= 55:
            classif = 'oportunidade moderada'
        elif score >= 35:
            classif = 'sinal a monitorar'
        else:
            classif = 'dados insuficientes'

        # Risco
        n_sig = n_signals
        if n_sig >= 3 or data.get('has_geada'):
            risco = 'alto'
        elif n_sig >= 1:
            risco = 'medio'
        else:
            risco = 'baixo'

        # Confiança
        if has_price and has_weather and days_p <= 3 and days_w <= 1:
            conf = 'alta'
        elif has_price or has_weather:
            conf = 'media'
        else:
            conf = 'baixa'

        return {
            'score':         score,
            'classificacao': classif,
            'risco':         risco,
            'confianca':     conf,
        }

    # ── Cenário contrário ──────────────────────────────────────────────────

    def generate_contrarian_scenario(self, data: dict) -> str:
        """Gera cenário contrário obrigatório para qualquer recomendação."""
        signals = data.get('signals', [])
        product = data.get('product', 'produto')
        country = data.get('country', '')
        region  = data.get('region', 'região')

        if 'risco de geada' in signals:
            return (
                f'Se a temperatura subir antes da próxima colheita em {region}, '
                f'a geada não se confirmar e a safra for preservada, '
                f'a pressão sobre a oferta se dissolve e o preço de {product} pode cair.'
            )
        if 'calor extremo' in signals:
            return (
                f'Se houver resfriamento natural ou irrigação compensar o estresse hídrico em {region}, '
                f'o impacto na oferta pode ser menor do que o sinal climático sugere.'
            )
        if 'chuva muito intensa' in signals or 'chuva intensa' in signals:
            return (
                f'Se a chuva cessar rapidamente e a colheita em {region} retomar o ritmo normal, '
                f'a oferta de {product} pode se recuperar antes que o preço se ajuste.'
            )
        if 'déficit hídrico' in signals:
            return (
                f'Se houver chuva compensatória nos próximos dias em {region} '
                f'ou irrigação suficiente, o estresse hídrico pode ser revertido.'
            )
        if country and country != 'BR':
            return (
                f'Se a oferta de {country} entrar com força no mercado brasileiro '
                f'ou o câmbio se mover desfavoravelmente, o cenário pode mudar.'
            )
        return (
            f'Se as condições climáticas se normalizarem ou a oferta de {product} '
            f'de outras regiões suprir a demanda, a oportunidade identificada pode não se confirmar.'
        )

    # ── Confiança ──────────────────────────────────────────────────────────

    def calculate_confidence(self, data: dict) -> str:
        """Retorna 'alta' | 'media' | 'baixa'."""
        score_obj = self.calculate_risk_return_score(data)
        return score_obj['confianca']

    # ── Recomendações por polo climático ──────────────────────────────────

    def _advice_from_weather_point(self, w: dict) -> Optional[dict]:
        """Gera um conselho estruturado a partir de um ponto climático SA."""
        signals = _climate_signals(w)
        if not signals:
            return None

        cc      = w.get('country_code', '??')
        region  = w.get('region_name', w.get('region', 'região'))
        country = COUNTRIES.get(cc, cc)
        today   = w.get('obs_date', date.today().isoformat())

        # Tipo de ação
        geada   = 'risco de geada' in signals
        calor   = 'calor extremo' in signals
        chuva   = any('chuva' in s for s in signals)
        deficit = 'déficit hídrico' in signals

        if geada:
            tipo   = 'alerta'
            titulo = f'Risco de geada em {region} ({country}) — alerta para produção'
            tese   = (
                f'Temperatura mínima próxima ou abaixo de 0°C em {region} pode danificar lavouras sensíveis. '
                f'Regiões produtoras sob geada enfrentam perda parcial ou total de safra, '
                f'reduzindo a oferta disponível e pressionando preços no curto prazo.'
            )
            acao   = (
                f'Monitorar oferta proveniente de {country}, verificar impacto na disponibilidade '
                f'de produtos de {region} e considerar antecipação de compras se você opera nesse mercado.'
            )
        elif calor and deficit:
            tipo   = 'monitorar'
            titulo = f'Calor extremo e déficit hídrico em {region} ({country})'
            tese   = (
                f'Temperaturas acima de 36°C combinadas com ausência de chuva em {region} '
                f'criam estresse hídrico severo. A qualidade e a quantidade da colheita '
                f'podem ser comprometidas, afetando a oferta nos próximos dias a semanas.'
            )
            acao   = (
                f'Acompanhar evolução das condições em {region}, monitorar fontes de oferta alternativas '
                f'e verificar preços de {country} no mercado regional.'
            )
        elif chuva:
            tipo   = 'monitorar'
            titulo = f'Chuva intensa em {region} ({country}) — risco de atraso de colheita'
            tese   = (
                f'Precipitação elevada em {region} pode dificultar a operação de colheita, '
                f'reduzir a qualidade pós-campo e atrasar entregas. '
                f'Quando ocorre em polo relevante, a oferta de produto de qualidade diminui temporariamente.'
            )
            acao   = (
                f'Monitorar logística de saída de {region}, verificar estoque disponível '
                f'e considerar antecipação de negociação se o preço ainda não refletiu o risco.'
            )
        else:
            tipo   = 'monitorar'
            titulo = f'Sinal climático em {region} ({country}): {", ".join(signals)}'
            tese   = (
                f'Condições climáticas atípicas detectadas em {region} ({country}): {", ".join(signals)}. '
                f'O impacto na produção e oferta depende da duração e intensidade do evento.'
            )
            acao   = f'Monitorar evolução das condições climáticas em {region} e impacto na oferta regional.'

        # Score
        score_data = {
            'signals':          signals,
            'weather':          True,
            'price':            False,
            'days_old_weather': _days_ago(today),
            'days_old_price':   999,
            'has_geada':        geada,
        }
        score_obj = self.calculate_risk_return_score(score_data)

        contrario = self.generate_contrarian_scenario({
            'signals': signals,
            'product': 'produtos da região',
            'country': cc,
            'region':  region,
        })

        # ── Price gating: sem preço real → máximo 'monitorar', não 'comprar'/'vender' ──
        has_price = self._has_sa_price(cc) if cc != 'BR' else bool(self._prices)
        if tipo not in ('monitorar', 'alerta') and not has_price:
            tipo = 'monitorar'

        # Reduzir score e confiança quando não há preço confirmado
        if not has_price:
            score_obj['score']      = min(score_obj['score'], 64)
            score_obj['confianca']  = 'baixa' if score_obj['confianca'] == 'alta' else score_obj['confianca']
            score_obj['classificacao'] = 'sinal a monitorar'

        price_note = (
            'Preço local disponível no banco.' if has_price
            else 'Sem preço local persistido — recomendação limitada a monitoramento.'
        )

        return {
            'titulo':            titulo,
            'tipo':              tipo,
            'produto':           'produtos agrícolas da região',
            'pais':              cc,
            'pais_nome':         country,
            'regiao':            region,
            'horizonte':         '1 a 7 dias',
            'tese':              tese,
            'dados_usados':      ['clima Open-Meteo', 'preços SA' if has_price else 'clima apenas'],
            'justificativa':     tese,
            'cenario_contrario': contrario,
            'risco':             score_obj['risco'],
            'confianca':         score_obj['confianca'],
            'score':             score_obj['score'],
            'classificacao':     score_obj['classificacao'],
            'acao_recomendada':  acao,
            'sinais_climaticos': signals,
            'temp_max_c':        w.get('temp_max_c'),
            'temp_min_c':        w.get('temp_min_c'),
            'precip_mm':         w.get('precip_mm'),
            'fontes':            ['Open-Meteo'] + (['nias_sa_prices'] if has_price else []),
            'price_signal':      'disponível' if has_price else 'sem preço local persistido',
            'has_price':         has_price,
            'price_gate_note':   price_note,
            'atualizado_em':     today,
            'scope':             'south_america',
        }

    def _advice_from_price_trend(self, price_rows: list[dict]) -> list[dict]:
        """Gera conselhos a partir de tendência de preços brasileiros."""
        if not price_rows:
            return []

        # Agrupa por produto
        by_product: dict[str, list] = {}
        for r in price_rows:
            key = r.get('slug') or r.get('product', '')
            by_product.setdefault(key, []).append(r)

        # Busca histórico de preços para detectar tendência
        advices = []
        try:
            hist_rows = self.conn.execute("""
                SELECT c.slug, c.name_pt as product, p.price_avg, p.price_date
                FROM flv_ceasa_prices p
                JOIN flv_cultures c ON c.id = p.culture_id
                WHERE p.price_date >= date('now', '-30 days')
                ORDER BY c.slug, p.price_date
            """).fetchall()
        except Exception:
            hist_rows = []

        hist_by_product: dict[str, list] = {}
        for r in hist_rows:
            hist_by_product.setdefault(r['slug'], []).append(r)

        for slug, rows in by_product.items():
            latest = rows[0]
            price  = latest.get('price') or 0
            hist   = hist_by_product.get(slug, [])

            if len(hist) < 3:
                continue

            prices_hist = [h['price_avg'] for h in hist if h['price_avg']]
            if not prices_hist:
                continue

            oldest = prices_hist[0]
            newest = prices_hist[-1]
            if oldest == 0:
                continue

            var_pct = ((newest - oldest) / oldest) * 100

            if abs(var_pct) < 5:
                continue  # variação irrelevante

            product   = latest.get('product', slug)
            market    = latest.get('market', 'Nacional')
            price_min = latest.get('price_min')
            price_max = latest.get('price_max')
            unit      = latest.get('unit', 'R$/kg')
            date_str  = latest.get('date', date.today().isoformat())
            days_old  = _days_ago(date_str)

            if var_pct > 0:
                tipo   = 'monitorar'
                titulo = f'{product} com tendência de alta de {var_pct:.0f}% nos últimos 30 dias'
                tese   = (
                    f'{product} apresenta alta de {var_pct:.1f}% em 30 dias no mercado {market}. '
                    f'O preço mais recente é {unit} {price:.2f}. '
                    f'A tendência pode indicar redução de oferta, aumento de demanda '
                    f'ou impacto sazonal. Monitorar se a alta se sustenta.'
                )
                contrario = (
                    f'Se a oferta do produto aumentar com novas safras chegando ao mercado '
                    f'ou com entrada de produto importado, a tendência de alta pode reverter.'
                )
                acao = (
                    f'Avaliar se vale antecipar compra antes de novo ajuste. '
                    f'Verificar fontes de oferta alternativas e monitorar CEASAs das principais praças.'
                )
            else:
                tipo   = 'monitorar'
                titulo = f'{product} com queda de {abs(var_pct):.0f}% nos últimos 30 dias'
                tese   = (
                    f'{product} apresenta queda de {abs(var_pct):.1f}% em 30 dias no mercado {market}. '
                    f'O preço mais recente é {unit} {price:.2f}. '
                    f'A queda pode indicar excesso de oferta, perda de qualidade pós-campo '
                    f'ou retração de demanda sazonal.'
                )
                contrario = (
                    f'Se a demanda por {product} se recuperar ou a oferta cair com fim de safra, '
                    f'o preço pode voltar a subir rapidamente.'
                )
                acao = (
                    f'Evitar estoque excessivo do produto enquanto a tendência de queda persiste. '
                    f'Verificar se a queda é sazonal ou estrutural antes de ajustar posição.'
                )

            score_data = {
                'signals':              [],
                'weather':              False,
                'price':                True,
                'days_old_price':       days_old,
                'days_old_weather':     999,
                'price_volatility_pct': abs(var_pct),
                'region_importance':    'alto' if abs(var_pct) > 20 else 'normal',
            }
            score_obj = self.calculate_risk_return_score(score_data)

            advices.append({
                'titulo':            titulo,
                'tipo':              tipo,
                'produto':           product,
                'slug':              slug,
                'pais':              'BR',
                'pais_nome':         'Brasil',
                'regiao':            market,
                'horizonte':         '7 a 30 dias',
                'tese':              tese,
                'dados_usados':      ['CONAB/PROHORT', 'histórico de preços'],
                'justificativa':     tese,
                'cenario_contrario': contrario,
                'risco':             score_obj['risco'],
                'confianca':         score_obj['confianca'],
                'score':             score_obj['score'],
                'classificacao':     score_obj['classificacao'],
                'acao_recomendada':  acao,
                'variacao_pct':      round(var_pct, 1),
                'preco_atual':       round(price, 2),
                'preco_min':         round(price_min, 2) if price_min else None,
                'preco_max':         round(price_max, 2) if price_max else None,
                'unidade':           unit,
                'fontes':            ['CONAB/PROHORT'],
                'atualizado_em':     date_str,
                'scope':             'brazil',
            })

        advices.sort(key=lambda x: -x['score'])
        return advices[:10]

    # ── API pública ────────────────────────────────────────────────────────

    def generate_advice(self) -> list[dict]:
        """Gera todos os conselhos disponíveis (clima SA + preços BR)."""
        self._load()
        advices = []

        # 1. Conselhos baseados em clima sul-americano
        for w in self._weather:
            a = self._advice_from_weather_point(w)
            if a:
                advices.append(a)

        # 2. Conselhos baseados em tendência de preço BR
        advices.extend(self._advice_from_price_trend(self._prices))

        # Ordenar por score desc
        advices.sort(key=lambda x: -x.get('score', 0))
        return advices

    def rank_opportunities(self) -> list[dict]:
        """Retorna conselhos classificados como oportunidade (score >= 55)."""
        all_advice = self.generate_advice()
        return [a for a in all_advice if a.get('score', 0) >= 55]

    def build_investment_thesis(self, product: str, region: str) -> dict:
        """
        Constrói tese de investimento/operação para produto × região específicos.
        Cruza clima + preço quando disponível.
        """
        self._load()
        product_l = product.lower()
        region_l  = region.lower()

        # Buscar preço do produto
        price_match = next(
            (p for p in self._prices
             if product_l in (p.get('product') or '').lower()
             or product_l in (p.get('slug') or '').lower()),
            None
        )

        # Buscar clima da região
        weather_match = next(
            (w for w in self._weather
             if region_l in (w.get('region_name') or '').lower()
             or region_l in (w.get('country_code') or '').lower()),
            None
        )

        signals = _climate_signals(weather_match) if weather_match else []
        score_data = {
            'signals':              signals,
            'weather':              bool(weather_match),
            'price':                bool(price_match),
            'days_old_price':       _days_ago(price_match.get('date')) if price_match else 999,
            'days_old_weather':     _days_ago(weather_match.get('obs_date')) if weather_match else 999,
            'price_volatility_pct': 0,
        }
        score_obj = self.calculate_risk_return_score(score_data)
        contrario = self.generate_contrarian_scenario({
            'signals': signals,
            'product': product,
            'region':  region,
        })

        if not price_match and not weather_match:
            return {
                'status':   'insuficiente',
                'produto':  product,
                'regiao':   region,
                'mensagem': (
                    'Ainda não há dados suficientes para uma recomendação confiável. '
                    'O NIAS encontrou sinais iniciais, mas precisa de atualização de '
                    'preço, clima ou logística para confirmar a tese.'
                ),
                'score': score_obj,
            }

        dados_usados = []
        if price_match:
            dados_usados.append(f'CONAB/PROHORT — {price_match["date"]}')
        if weather_match:
            dados_usados.append(f'Open-Meteo — {weather_match.get("obs_date")}')

        tese = (
            f'Análise de {product} em {region}. '
        )
        if price_match:
            tese += (
                f'Preço atual: R$ {price_match["price"]:.2f}/{price_match.get("unit","kg")} '
                f'(mercado {price_match.get("market","Nacional")}). '
            )
        if signals:
            tese += f'Sinais climáticos: {", ".join(signals)}. '
        if not signals and weather_match:
            tese += 'Condições climáticas normais na região. '

        return {
            'status':            'ok',
            'produto':           product,
            'regiao':            region,
            'tese':              tese,
            'dados_usados':      dados_usados,
            'cenario_contrario': contrario,
            'score':             score_obj,
            'preco':             price_match,
            'clima':             weather_match,
            'sinais_climaticos': signals,
            'fontes':            ['CONAB/PROHORT', 'Open-Meteo'],
            'atualizado_em':     datetime.now().isoformat(),
        }

    def explain_recommendation(self, data: dict) -> str:
        """
        Gera texto explicativo em linguagem empresarial clara para um conselho.
        Nunca retorna apenas números.
        """
        product  = data.get('produto', 'produto')
        region   = data.get('regiao', 'região')
        country  = data.get('pais_nome', data.get('pais', ''))
        signals  = data.get('sinais_climaticos', [])
        var_pct  = data.get('variacao_pct')
        tipo     = data.get('tipo', 'monitorar')
        conf     = data.get('confianca', 'media')
        score    = data.get('score', 0)

        prefix = f'{product} em {region}'
        if country:
            prefix += f' ({country})'

        if signals:
            signal_str = ', '.join(signals)
            text = (
                f'{prefix} apresenta sinais climáticos relevantes: {signal_str}. '
                f'Quando esses eventos ocorrem em polos produtivos importantes, '
                f'a oferta disponível tende a diminuir temporariamente, '
                f'o que pode pressionar preços no curto prazo. '
            )
            if tipo == 'alerta':
                text += (
                    f'O NIAS classifica este como um alerta prioritário (score {score}/100). '
                )
            else:
                text += (
                    f'O NIAS recomenda monitoramento ativo (score {score}/100). '
                )
        elif var_pct is not None:
            direction = 'alta' if var_pct > 0 else 'queda'
            text = (
                f'{prefix} mostra tendência de {direction} de {abs(var_pct):.0f}% '
                f'nos últimos 30 dias, com base em dados CONAB/PROHORT. '
                f'Essa variação pode refletir mudanças sazonais de oferta ou pressão de demanda. '
            )
        else:
            text = (
                f'{prefix}: situação monitorada pelo NIAS. '
                f'Os dados disponíveis indicam necessidade de acompanhamento. '
            )

        conf_text = {
            'alta':  'A confiança da análise é alta — dados completos e recentes.',
            'media': 'A confiança é média — dependente de confirmação nas próximas cotações.',
            'baixa': 'A confiança é baixa — dados parciais. Recomenda-se aguardar mais informações.',
        }.get(conf, '')

        if conf_text:
            text += conf_text

        return text

    def generate_executive_summary(self) -> dict:
        """
        Resumo executivo: contagem de oportunidades, riscos e alertas.
        Linguagem clara, não robótica.
        """
        self._load()
        all_advice = self.generate_advice()

        oportunidades = [a for a in all_advice if a.get('score', 0) >= 55]
        riscos        = [a for a in all_advice if 'risco de geada' in a.get('sinais_climaticos', [])
                         or 'calor extremo' in a.get('sinais_climaticos', [])]
        alertas       = [a for a in all_advice if a.get('tipo') == 'alerta']

        # Freshness
        days_price   = _days_ago(self._freshness.get('prices'))
        days_weather = _days_ago(self._freshness.get('climate'))
        data_ok      = days_price <= 7 or days_weather <= 1

        if len(oportunidades) >= 3 and data_ok:
            resumo = (
                f'Hoje o NIAS identifica {len(oportunidades)} oportunidade(s) relevante(s), '
                f'{len(riscos)} risco(s) climático(s) e {len(alertas)} alerta(s) prioritário(s) '
                f'no mercado agrocomercial da América do Sul.'
            )
            conf = 'media'
        elif len(all_advice) > 0:
            resumo = (
                f'O NIAS identificou {len(all_advice)} sinal(is) de atenção. '
                f'Dados climáticos coletados há {days_weather} dia(s), '
                f'preços há {days_price} dia(s). '
                f'Rode o pipeline para atualizar a análise.'
            )
            conf = 'baixa'
        else:
            resumo = (
                'O NIAS ainda não tem dados suficientes para gerar análise completa. '
                'Execute o pipeline para coletar clima e preços antes de usar o Conselheiro.'
            )
            conf = 'baixa'

        return {
            'resumo':           resumo,
            'total_conselhos':  len(all_advice),
            'oportunidades':    len(oportunidades),
            'riscos_climaticos': len(riscos),
            'alertas':          len(alertas),
            'confianca':        conf,
            'freshness': {
                'prices_days_old':  days_price,
                'weather_days_old': days_weather,
            },
            'scope': 'south_america',
            'atualizado_em': datetime.now().isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════════════════════

def get_advisor(conn: sqlite3.Connection) -> NiasAdvisorEngine:
    """Retorna instância do advisor para a conexão fornecida."""
    return NiasAdvisorEngine(conn)
