"""
NiasBrainEngine — Cérebro NIAS: Inteligência Viva da América do Sul.

Sintetiza dados reais (clima, preços, pipeline, advisor) em:
  - Pulso do sistema (saúde dos dados)
  - Eventos ao vivo (o que está acontecendo agora)
  - Cartões de decisão (com validade e gatilhos de invalidação)
  - Radar temporal (agora / 24h / 7d / 15d / 30d)
  - Teses por produto/país/região
  - Processamento de comandos estratégicos (estruturado, não chat)

Nunca inventa dado. Quando dado ausente, sinaliza explicitamente.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional

_COUNTRIES = {
    'BR': 'Brasil', 'AR': 'Argentina', 'CL': 'Chile',
    'PE': 'Peru',   'BO': 'Bolívia',   'PY': 'Paraguai',
    'UY': 'Uruguai','CO': 'Colômbia',  'EC': 'Equador',
}

_RISK_HORIZONS = ['agora', '24h', '48h', '3d', '7d', '15d', '30d']


def _days_ago(iso_date: Optional[str]) -> int:
    if not iso_date:
        return 999
    try:
        d = date.fromisoformat(str(iso_date)[:10])
        return (date.today() - d).days
    except Exception:
        return 999


def _freshness_label(days: int) -> str:
    if days == 0:   return 'hoje'
    if days == 1:   return 'ontem'
    if days <= 3:   return f'{days} dias atrás'
    if days <= 7:   return f'{days} dias atrás'
    if days <= 30:  return f'{days} dias atrás'
    return f'{days} dias atrás'


def _freshness_quality(days: int) -> str:
    if days <= 1:  return 'ok'
    if days <= 3:  return 'warn'
    if days <= 7:  return 'stale'
    return 'missing'


class NiasBrainEngine:
    """
    Cérebro NIAS — sintetiza todos os fluxos de dados em inteligência estruturada.

    Não é um chatbot. Não responde perguntas abertas.
    Gera pulso, eventos, decisões, radar e teses a partir de dados reais.
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._now = datetime.now()
        self._today = date.today().isoformat()
        self._weather_data: list[dict] = []
        self._price_data: list[dict] = []
        self._advisor_advices: list[dict] = []
        self._pipeline_status: dict = {}
        self._loaded = False

    # ─────────────────────────────────────────────────────────────────
    # Carregamento de dados
    # ─────────────────────────────────────────────────────────────────

    def observe_now(self) -> 'NiasBrainEngine':
        """Carrega todos os dados disponíveis do banco. Idempotente."""
        if self._loaded:
            return self
        self._weather_data  = self._load_sa_weather()
        self._price_data    = self._load_sa_prices()
        self._advisor_advices = self._load_advisor_advices()
        self._pipeline_status = self._load_pipeline_status()
        self._loaded = True
        return self

    def _load_sa_weather(self) -> list[dict]:
        try:
            rows = self._conn.execute("""
                SELECT country_code, region_name, region_id, lat, lon, obs_date,
                       temp_max_c, temp_min_c, precip_mm, humidity_pct, wind_ms, source
                FROM flv_climate
                WHERE scope = 'south_america'
                  AND obs_date = (SELECT MAX(obs_date) FROM flv_climate WHERE scope='south_america')
                ORDER BY country_code, region_name
            """).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _load_sa_prices(self) -> list[dict]:
        try:
            rows = self._conn.execute("""
                SELECT country_code, country, market_name, product_normalized,
                       price, currency, price_per_kg, price_usd, price_date,
                       source, confidence, is_fallback
                FROM nias_sa_prices
                WHERE price_date = (SELECT MAX(price_date) FROM nias_sa_prices)
                ORDER BY country_code, product_normalized
            """).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _load_advisor_advices(self) -> list[dict]:
        try:
            from flv.advisor_engine import get_advisor
            engine = get_advisor(self._conn)
            return engine.generate_advice()
        except Exception:
            return []

    def _load_pipeline_status(self) -> dict:
        try:
            from flv.scheduler import get_pipeline_status
            return get_pipeline_status()
        except Exception:
            return {}

    # ─────────────────────────────────────────────────────────────────
    # Pulso do sistema
    # ─────────────────────────────────────────────────────────────────

    def generate_system_pulse(self) -> dict:
        """
        Status de saúde de todos os fluxos de dados do NIAS.
        Retorna métricas de frescor sem inventar indicadores.
        """
        self.observe_now()

        # Clima SA
        w_dates = [r.get('obs_date') for r in self._weather_data if r.get('obs_date')]
        w_latest = max(w_dates) if w_dates else None
        w_days   = _days_ago(w_latest)
        w_count  = len(self._weather_data)
        w_countries = len({r.get('country_code') for r in self._weather_data})

        # Preços SA
        p_dates  = [r.get('price_date') for r in self._price_data if r.get('price_date')]
        p_latest = max(p_dates) if p_dates else None
        p_days   = _days_ago(p_latest)
        p_count  = len(self._price_data)
        p_countries = len({r.get('country_code') for r in self._price_data})

        # Preços BR (CEASA)
        br_latest = None
        br_count  = 0
        try:
            row = self._conn.execute(
                "SELECT MAX(price_date) as d, COUNT(*) as n FROM flv_ceasa_prices"
            ).fetchone()
            if row:
                br_latest = row['d']
                br_count  = row['n']
        except Exception:
            pass
        br_days = _days_ago(br_latest)

        # Recomendações
        n_alerta   = sum(1 for a in self._advisor_advices if a.get('tipo') == 'alerta')
        n_comprar  = sum(1 for a in self._advisor_advices if a.get('tipo') in ('comprar', 'antecipar_compra'))
        n_monitor  = sum(1 for a in self._advisor_advices if a.get('tipo') == 'monitorar')

        # Pipeline
        pipe_last = self._pipeline_status.get('last_run') or self._pipeline_status.get('last_success')
        pipe_days = _days_ago(str(pipe_last)[:10] if pipe_last else None)

        sources = {
            'clima_sa': {
                'label':      'Clima SA (Open-Meteo)',
                'status':     _freshness_quality(w_days),
                'latest_date': w_latest,
                'freshness':  _freshness_label(w_days),
                'records':    w_count,
                'countries':  w_countries,
                'source':     'Open-Meteo',
            },
            'precos_sa': {
                'label':      'Preços SA (Mercados Oficiais)',
                'status':     _freshness_quality(p_days) if p_count else 'missing',
                'latest_date': p_latest,
                'freshness':  _freshness_label(p_days) if p_count else 'sem dados',
                'records':    p_count,
                'countries':  p_countries,
                'source':     'ODEPA / SIPSA / MIDAGRI / Mercado Central',
            },
            'precos_br': {
                'label':      'Preços BR (CONAB/PROHORT)',
                'status':     _freshness_quality(br_days) if br_count else 'missing',
                'latest_date': br_latest,
                'freshness':  _freshness_label(br_days) if br_count else 'sem dados',
                'records':    br_count,
                'source':     'CONAB/PROHORT',
            },
            'pipeline': {
                'label':      'Pipeline de coleta',
                'status':     _freshness_quality(pipe_days),
                'latest_run': str(pipe_last)[:19] if pipe_last else None,
                'freshness':  _freshness_label(pipe_days),
                'source':     'NIAS Scheduler',
            },
        }

        # Score geral de saúde
        statuses = [s['status'] for s in sources.values()]
        if all(s == 'ok' for s in statuses):
            health = 'saudavel'
        elif any(s == 'missing' for s in statuses):
            health = 'degradado'
        elif any(s == 'stale' for s in statuses):
            health = 'atencao'
        else:
            health = 'ok'

        return {
            'timestamp':       self._now.isoformat(),
            'health':          health,
            'sources':         sources,
            'recommendations': {
                'alertas':    n_alerta,
                'comprar':    n_comprar,
                'monitorar':  n_monitor,
                'total':      len(self._advisor_advices),
            },
            'coverage': {
                'weather_poles':    w_count,
                'weather_countries': w_countries,
                'price_countries':  p_countries,
                'total_countries':  9,
            },
        }

    # ─────────────────────────────────────────────────────────────────
    # Eventos ao vivo
    # ─────────────────────────────────────────────────────────────────

    def generate_live_events(self) -> list[dict]:
        """
        Lista de eventos detectados agora pelo NIAS.
        Cada evento tem tipo, descrição, região, gravidade e timestamp.
        Ordenados por gravidade decrescente.
        """
        self.observe_now()
        events = []

        # Eventos climáticos
        for w in self._weather_data:
            cc        = w.get('country_code', '')
            region    = w.get('region_name', '')
            t_max     = w.get('temp_max_c')
            t_min     = w.get('temp_min_c')
            prec      = w.get('precip_mm') or 0
            obs_date  = w.get('obs_date', '')

            if t_max and t_max >= 38:
                events.append({
                    'id':          f'heat-{cc}-{region}'.replace(' ', '_'),
                    'tipo':        'clima_extremo',
                    'gravidade':   'critica',
                    'pais':        cc,
                    'pais_nome':   _COUNTRIES.get(cc, cc),
                    'regiao':      region,
                    'titulo':      f'Calor extremo em {region}',
                    'descricao':   (
                        f'Temperatura máxima de {t_max:.1f}°C registrada em {region} ({cc}). '
                        'Nível acima de 38°C causa dano direto a hortifrutis sensíveis ao calor.'
                    ),
                    'dado':        {'temp_max_c': t_max, 'obs_date': obs_date},
                    'fonte':       w.get('source', 'Open-Meteo'),
                    'timestamp':   f'{obs_date}T00:00:00',
                    'acao':        f'Verificar oferta de produtos sensíveis ao calor em {cc}.',
                })
            elif t_max and t_max >= 36:
                events.append({
                    'id':          f'heat-warn-{cc}-{region}'.replace(' ', '_'),
                    'tipo':        'clima_atencao',
                    'gravidade':   'alta',
                    'pais':        cc,
                    'pais_nome':   _COUNTRIES.get(cc, cc),
                    'regiao':      region,
                    'titulo':      f'Calor elevado em {region}',
                    'descricao':   f'Temperatura máxima de {t_max:.1f}°C em {region} ({cc}). Monitorar desenvolvimento vegetativo.',
                    'dado':        {'temp_max_c': t_max, 'obs_date': obs_date},
                    'fonte':       w.get('source', 'Open-Meteo'),
                    'timestamp':   f'{obs_date}T00:00:00',
                    'acao':        'Monitorar produtos de baixa tolerância ao calor.',
                })

            if t_min is not None and t_min <= 0:
                events.append({
                    'id':          f'frost-{cc}-{region}'.replace(' ', '_'),
                    'tipo':        'risco_geada',
                    'gravidade':   'critica',
                    'pais':        cc,
                    'pais_nome':   _COUNTRIES.get(cc, cc),
                    'regiao':      region,
                    'titulo':      f'Geada confirmada em {region}',
                    'descricao':   (
                        f'Temperatura mínima de {t_min:.1f}°C em {region} ({cc}). '
                        'Geada causa dano irreversível em culturas não protegidas.'
                    ),
                    'dado':        {'temp_min_c': t_min, 'obs_date': obs_date},
                    'fonte':       w.get('source', 'Open-Meteo'),
                    'timestamp':   f'{obs_date}T00:00:00',
                    'acao':        f'Checar perdas em {cc}. Possível pressão de alta nos preços regionais.',
                    'invalida_se': ['Temperatura mínima voltar acima de 2°C por 3 dias consecutivos'],
                })
            elif t_min is not None and t_min < 2:
                events.append({
                    'id':          f'frost-risk-{cc}-{region}'.replace(' ', '_'),
                    'tipo':        'risco_geada',
                    'gravidade':   'alta',
                    'pais':        cc,
                    'pais_nome':   _COUNTRIES.get(cc, cc),
                    'regiao':      region,
                    'titulo':      f'Risco de geada em {region}',
                    'descricao':   f'Temperatura mínima de {t_min:.1f}°C em {region} ({cc}). Zona de risco para culturas delicadas.',
                    'dado':        {'temp_min_c': t_min, 'obs_date': obs_date},
                    'fonte':       w.get('source', 'Open-Meteo'),
                    'timestamp':   f'{obs_date}T00:00:00',
                    'acao':        'Acompanhar previsão de 48h para região.',
                    'invalida_se': ['Temperatura mínima ≥ 2°C por 2 noites seguidas'],
                })

            if prec >= 50:
                events.append({
                    'id':          f'rain-{cc}-{region}'.replace(' ', '_'),
                    'tipo':        'chuva_intensa',
                    'gravidade':   'alta',
                    'pais':        cc,
                    'pais_nome':   _COUNTRIES.get(cc, cc),
                    'regiao':      region,
                    'titulo':      f'Chuva intensa em {region}',
                    'descricao':   f'{prec:.0f}mm registrados em {region} ({cc}). Pode comprometer colheita e logística local.',
                    'dado':        {'precip_mm': prec, 'obs_date': obs_date},
                    'fonte':       w.get('source', 'Open-Meteo'),
                    'timestamp':   f'{obs_date}T00:00:00',
                    'acao':        'Verificar condições de escoamento da produção regional.',
                })

        # Eventos de preço (variações entre dias, se houver dados suficientes)
        # Por ora, reportar onde há dados de preço como evento positivo de cobertura
        countries_with_price = {r.get('country_code') for r in self._price_data}
        if countries_with_price:
            events.append({
                'id':          'price-coverage',
                'tipo':        'cobertura_preco',
                'gravidade':   'info',
                'pais':        'SA',
                'pais_nome':   'América do Sul',
                'regiao':      None,
                'titulo':      f'Preços coletados: {len(countries_with_price)} país(es)',
                'descricao':   (
                    f'Dados de preço disponíveis para: {", ".join(sorted(countries_with_price))}. '
                    f'Total de {len(self._price_data)} registros no banco.'
                ),
                'dado':        {'countries': sorted(countries_with_price), 'records': len(self._price_data)},
                'fonte':       'NIAS Price Sources',
                'timestamp':   self._now.isoformat(),
                'acao':        'Dados disponíveis para análise comparativa regional.',
            })

        # Sinalizar países sem dados de preço
        missing_price = [cc for cc in ['AR', 'CL', 'PE', 'UY', 'CO'] if cc not in countries_with_price]
        if missing_price:
            events.append({
                'id':          'price-missing',
                'tipo':        'dado_ausente',
                'gravidade':   'warn',
                'pais':        'SA',
                'pais_nome':   'América do Sul',
                'regiao':      None,
                'titulo':      f'Preços ausentes: {", ".join(missing_price)}',
                'descricao':   (
                    f'Sem dados de preço para {", ".join(missing_price)}. '
                    'Recomendações para esses países ficam limitadas ao nível de monitoramento.'
                ),
                'dado':        {'countries_missing': missing_price},
                'fonte':       'NIAS Price Sources',
                'timestamp':   self._now.isoformat(),
                'acao':        'Executar pipeline de coleta de preços para obter dados reais.',
            })

        # Ordenar: crítica > alta > warn > info
        gravity_order = {'critica': 0, 'alta': 1, 'warn': 2, 'info': 3}
        events.sort(key=lambda e: gravity_order.get(e.get('gravidade', 'info'), 9))

        return events

    # ─────────────────────────────────────────────────────────────────
    # Cartões de decisão
    # ─────────────────────────────────────────────────────────────────

    def generate_decision_cards(self) -> list[dict]:
        """
        Cartões de decisão estruturados com:
        - validade (até quando a decisão é relevante)
        - gatilhos de invalidação (o que muda o cenário)
        - dados usados
        - ação recomendada
        - cenário contrário

        Nunca emite 'comprar'/'vender' sem preço real.
        """
        self.observe_now()
        cards = []

        for advice in self._advisor_advices:
            tipo      = advice.get('tipo', 'monitorar')
            score     = advice.get('score', 0)
            confianca = advice.get('confianca', 'baixa')
            pais      = advice.get('pais', '')
            regiao    = advice.get('regiao', '')
            produto   = advice.get('produto', '')
            titulo    = advice.get('titulo', '')
            sinais    = advice.get('sinais_climaticos', [])
            has_price = advice.get('has_price', False)

            # Validade depende do tipo de sinal
            if 'risco de geada' in sinais:
                validade_dias = 2
                validade_label = '48h (evento climático agudo)'
            elif 'calor extremo' in sinais or 'calor elevado' in sinais:
                validade_dias = 3
                validade_label = '3 dias (condição climática)'
            elif tipo in ('comprar', 'antecipar_compra'):
                validade_dias = 7
                validade_label = '7 dias (janela de mercado)'
            elif tipo == 'alerta':
                validade_dias = 5
                validade_label = '5 dias (alerta ativo)'
            else:
                validade_dias = 14
                validade_label = '14 dias (monitoramento)'

            validade_ate = (date.today() + timedelta(days=validade_dias)).isoformat()

            # Gatilhos de invalidação
            invalida_se = []
            if 'risco de geada' in sinais:
                invalida_se.append('Temperatura mínima subir acima de 2°C por 2 noites seguidas')
            if 'calor extremo' in sinais:
                invalida_se.append('Temperatura máxima cair abaixo de 33°C por 3 dias')
            if tipo == 'monitorar' and not has_price:
                invalida_se.append('Dados de preço local passarem a estar disponíveis no banco')
            if tipo in ('comprar', 'antecipar_compra'):
                invalida_se.append('Preço cair mais de 15% abaixo da referência atual')
                invalida_se.append('Condição climática que originou o sinal se normalizar')
            invalida_se.append(f'Dado climático atualizado com condições diferentes em {regiao}')

            card = {
                'id':               advice.get('id', f'{pais}-{produto}-{tipo}'),
                'tipo':             tipo,
                'score':            score,
                'confianca':        confianca,
                'has_price':        has_price,
                'pais':             pais,
                'pais_nome':        _COUNTRIES.get(pais, pais),
                'regiao':           regiao,
                'produto':          produto,
                'titulo':           titulo,
                'tese':             advice.get('tese', ''),
                'justificativa':    advice.get('justificativa', ''),
                'acao_recomendada': advice.get('acao_recomendada', ''),
                'cenario_contrario': advice.get('cenario_contrario', ''),
                'risco':            advice.get('risco', 'medio'),
                'sinais_climaticos': sinais,
                'dados_usados':     advice.get('dados_usados', []),
                'fontes':           advice.get('fontes', []),
                'price_signal':     advice.get('price_signal', ''),
                'validade_ate':     validade_ate,
                'validade_label':   validade_label,
                'invalida_se':      invalida_se,
                'scope':            advice.get('scope', 'south_america'),
                'gerado_em':        self._now.isoformat(),
            }
            cards.append(card)

        # Ordenar: score decrescente
        cards.sort(key=lambda c: -(c.get('score') or 0))
        return cards

    # ─────────────────────────────────────────────────────────────────
    # Radar temporal
    # ─────────────────────────────────────────────────────────────────

    def generate_temporal_radar(self) -> dict:
        """
        Radar de risco por horizonte temporal.
        Cada horizonte lista eventos e riscos esperados com base em dados reais.
        Quando não há dado de previsão, indica explicitamente.
        """
        self.observe_now()
        events = self.generate_live_events()

        radar = {}
        for horizon in _RISK_HORIZONS:
            radar[horizon] = self._radar_horizon(horizon, events)

        return {
            'horizons':     _RISK_HORIZONS,
            'radar':        radar,
            'timestamp':    self._now.isoformat(),
            'data_note':    (
                'Radar baseado em dados climáticos atuais (Open-Meteo) e preços persistidos. '
                'Projeções para horizontes >24h usam dados do dia atual como proxy — '
                'sem modelo de previsão de preço integrado.'
            ),
        }

    def _radar_horizon(self, horizon: str, current_events: list[dict]) -> dict:
        """Constrói a visão de risco para um horizonte específico."""
        # Para "agora" e "24h": usar eventos detectados agora
        # Para horizontes maiores: reduzir confiança progressivamente
        conf_by_horizon = {
            'agora': 1.0, '24h': 0.85, '48h': 0.70,
            '3d': 0.55,   '7d': 0.40,  '15d': 0.25, '30d': 0.15,
        }
        conf_mult = conf_by_horizon.get(horizon, 0.5)
        is_current = horizon in ('agora', '24h')

        # Filtrar eventos relevantes para o horizonte
        relevant = [e for e in current_events if e.get('gravidade') in ('critica', 'alta')]
        if not is_current:
            # Para horizontes futuros, não inclui eventos específicos — só contagem e risco
            relevant = []

        # Risco agregado por país
        countries_at_risk = {}
        for e in current_events:
            if e.get('gravidade') in ('critica', 'alta'):
                cc = e.get('pais', '')
                if cc and cc != 'SA':
                    countries_at_risk[cc] = countries_at_risk.get(cc, 0) + 1

        # Nível de risco geral
        n_critical = sum(1 for e in current_events if e.get('gravidade') == 'critica')
        n_high     = sum(1 for e in current_events if e.get('gravidade') == 'alta')

        if n_critical >= 3:
            risk_level = 'critico'
        elif n_critical >= 1:
            risk_level = 'alto'
        elif n_high >= 2:
            risk_level = 'elevado'
        elif n_high >= 1:
            risk_level = 'moderado'
        else:
            risk_level = 'baixo'

        # Para horizontes futuros sem dados de previsão
        if not is_current and conf_mult < 0.5:
            return {
                'horizon':          horizon,
                'risk_level':       risk_level,
                'confidence_mult':  conf_mult,
                'events_count':     0,
                'countries_at_risk': list(countries_at_risk.keys()),
                'events':           [],
                'note': (
                    f'Horizonte {horizon}: sem dados de previsão climática estendida disponíveis. '
                    'Risco estimado a partir de condições atuais com confiança reduzida.'
                ),
            }

        return {
            'horizon':          horizon,
            'risk_level':       risk_level,
            'confidence_mult':  conf_mult,
            'events_count':     len(relevant),
            'countries_at_risk': list(countries_at_risk.keys()),
            'events':           relevant[:5],  # máx 5 por horizonte
            'note':             (
                'Baseado em dados climáticos do dia.' if is_current
                else f'Estimativa com confiança reduzida ({int(conf_mult*100)}%).'
            ),
        }

    # ─────────────────────────────────────────────────────────────────
    # Tese detalhada
    # ─────────────────────────────────────────────────────────────────

    def generate_thesis(self, product: str = '', country: str = '',
                        region: str = '') -> dict:
        """
        Tese de inteligência para produto/país/região específicos.
        Inclui todos os dados disponíveis com fontes explícitas.
        """
        self.observe_now()

        # Clima na região/país solicitado
        weather_subset = []
        for w in self._weather_data:
            cc   = w.get('country_code', '')
            reg  = w.get('region_name', '').lower()
            if country and cc != country.upper():
                continue
            if region and region.lower() not in reg:
                continue
            weather_subset.append(w)

        # Preços do produto/país
        price_subset = []
        for p in self._price_data:
            cc   = p.get('country_code', '')
            prod = p.get('product_normalized', '').lower()
            if country and cc != country.upper():
                continue
            if product and product.lower() not in prod:
                continue
            price_subset.append(p)

        # Conselhos relacionados
        advice_subset = []
        for a in self._advisor_advices:
            cc   = a.get('pais', '')
            prod = (a.get('produto') or '').lower()
            reg  = (a.get('regiao') or '').lower()
            if country and cc != country.upper():
                continue
            if product and product.lower() not in prod:
                continue
            if region and region.lower() not in reg:
                continue
            advice_subset.append(a)

        # Sinais climáticos detectados
        climate_signals = []
        for w in weather_subset:
            t_max = w.get('temp_max_c')
            t_min = w.get('temp_min_c')
            prec  = w.get('precip_mm') or 0
            reg   = w.get('region_name', '')
            if t_max and t_max > 36:
                climate_signals.append(f'Calor elevado ({t_max:.0f}°C) em {reg}')
            if t_min is not None and t_min < 2:
                climate_signals.append(f'Risco de geada ({t_min:.0f}°C) em {reg}')
            if prec > 40:
                climate_signals.append(f'Chuva intensa ({prec:.0f}mm) em {reg}')

        # Montar tese
        has_climate = bool(weather_subset)
        has_price   = bool(price_subset)
        has_advice  = bool(advice_subset)

        if not has_climate and not has_price:
            return {
                'product':  product,
                'country':  country,
                'region':   region,
                'status':   'sem_dado',
                'message':  (
                    'Não há dados climáticos ou de preço disponíveis no banco para os '
                    'filtros informados. Execute o pipeline de coleta.'
                ),
                'thesis':   None,
                'fontes':   [],
                'gerado_em': self._now.isoformat(),
            }

        best_advice = advice_subset[0] if advice_subset else None
        top_score   = best_advice.get('score', 0) if best_advice else 0

        # Texto da tese
        parts = []
        if product:
            parts.append(f'**{product.capitalize()}**')
        if country:
            parts.append(f'em **{_COUNTRIES.get(country.upper(), country)}**')
        if region:
            parts.append(f'na região **{region}**')

        subject = ' '.join(parts) or 'América do Sul'

        if climate_signals:
            climate_text = (
                f'O NIAS detectou os seguintes eventos climáticos para {subject}: '
                + '; '.join(climate_signals) + '.'
            )
        else:
            weather_count = len(weather_subset)
            climate_text = (
                f'{weather_count} polo(s) monitorado(s) em {subject} sem eventos climáticos extremos detectados no momento.'
            )

        if has_price:
            prices_text = (
                f'Preços disponíveis: {len(price_subset)} registro(s). '
                + ', '.join(
                    f'{p["product_normalized"]}: {p["price"]:.0f} {p["currency"]}/kg'
                    for p in price_subset[:3]
                ) + '.'
            )
        else:
            prices_text = (
                'Sem dados de preço local disponíveis no banco para o filtro informado. '
                'Recomendações ficam limitadas ao nível de monitoramento climático.'
            )

        main_thesis = f'{climate_text} {prices_text}'

        fontes = list({w.get('source', 'Open-Meteo') for w in weather_subset})
        fontes += list({p.get('source', '') for p in price_subset if p.get('source')})

        return {
            'product':          product or None,
            'country':          country or None,
            'region':           region or None,
            'status':           'ok',
            'thesis':           main_thesis,
            'climate_signals':  climate_signals,
            'climate_poles':    len(weather_subset),
            'price_records':    len(price_subset),
            'prices':           price_subset[:5],
            'top_advice':       best_advice,
            'all_advices_count': len(advice_subset),
            'score':            top_score,
            'has_price':        has_price,
            'has_climate':      has_climate,
            'fontes':           fontes,
            'fontes_ausentes':  [] if has_price else ['preço local'],
            'gerado_em':        self._now.isoformat(),
        }

    # ─────────────────────────────────────────────────────────────────
    # Detect changes (comparação de frescor entre ciclos)
    # ─────────────────────────────────────────────────────────────────

    def detect_changes(self) -> list[dict]:
        """
        Detecta mudanças relevantes desde a última atualização de dados.
        Compara data do dado com hoje. Apenas muda o que há nos dados reais.
        """
        self.observe_now()
        changes = []

        # Verificar se clima foi atualizado hoje
        w_dates = [r.get('obs_date') for r in self._weather_data if r.get('obs_date')]
        w_latest = max(w_dates) if w_dates else None
        if w_latest and w_latest == self._today:
            changes.append({
                'tipo':       'atualizacao_clima',
                'descricao':  f'Dados climáticos atualizados hoje ({w_latest}) para {len(self._weather_data)} polos.',
                'timestamp':  self._now.isoformat(),
                'relevancia': 'positiva',
            })
        elif w_latest:
            days = _days_ago(w_latest)
            changes.append({
                'tipo':       'clima_desatualizado',
                'descricao':  f'Dados climáticos com {days} dia(s) de atraso (última: {w_latest}).',
                'timestamp':  self._now.isoformat(),
                'relevancia': 'negativa',
            })

        # Verificar preços
        p_dates = [r.get('price_date') for r in self._price_data if r.get('price_date')]
        p_latest = max(p_dates) if p_dates else None
        if p_latest:
            days = _days_ago(p_latest)
            if days <= 1:
                changes.append({
                    'tipo':       'atualizacao_preco',
                    'descricao':  f'Preços SA atualizados recentemente ({p_latest}). {len(self._price_data)} registros.',
                    'timestamp':  self._now.isoformat(),
                    'relevancia': 'positiva',
                })
            else:
                changes.append({
                    'tipo':       'preco_desatualizado',
                    'descricao':  f'Preços SA com {days} dia(s) de atraso (última: {p_latest}).',
                    'timestamp':  self._now.isoformat(),
                    'relevancia': 'negativa',
                })
        else:
            changes.append({
                'tipo':       'preco_ausente',
                'descricao':  'Sem dados de preço SA no banco. Execute o pipeline.',
                'timestamp':  self._now.isoformat(),
                'relevancia': 'negativa',
            })

        return changes

    # ─────────────────────────────────────────────────────────────────
    # Avaliação de qualidade de dados
    # ─────────────────────────────────────────────────────────────────

    def evaluate_data_quality(self) -> dict:
        """
        Avalia a qualidade e cobertura dos dados disponíveis.
        Transparente sobre o que falta.
        """
        self.observe_now()

        countries_weather = {r.get('country_code') for r in self._weather_data}
        countries_price   = {r.get('country_code') for r in self._price_data}
        all_countries     = set(_COUNTRIES.keys())

        missing_weather = all_countries - countries_weather
        missing_price   = all_countries - countries_price

        return {
            'cobertura_clima': {
                'com_dado':  sorted(countries_weather),
                'sem_dado':  sorted(missing_weather),
                'total_polos': len(self._weather_data),
                'qualidade': 'boa' if len(countries_weather) >= 7 else 'parcial' if countries_weather else 'sem_dado',
            },
            'cobertura_preco': {
                'com_dado':  sorted(countries_price),
                'sem_dado':  sorted(missing_price),
                'total_registros': len(self._price_data),
                'qualidade': 'boa' if len(countries_price) >= 4 else 'parcial' if countries_price else 'sem_dado',
                'nota': 'BR gerenciado por CONAB/PROHORT (tabela separada).',
            },
            'conselhos': {
                'total':   len(self._advisor_advices),
                'com_preco': sum(1 for a in self._advisor_advices if a.get('has_price')),
                'sem_preco': sum(1 for a in self._advisor_advices if not a.get('has_price')),
            },
            'limitacoes': [
                l for l in [
                    'Previsão extendida (>24h) não disponível — apenas dados do dia atual.',
                    'Preços históricos limitados ao banco local.' if self._price_data else None,
                    f'Países sem preço: {", ".join(sorted(missing_price - {"BR"}))}.' if missing_price - {'BR'} else None,
                    f'Países sem clima: {", ".join(sorted(missing_weather))}.' if missing_weather else None,
                ]
                if l
            ],
        }

    # ─────────────────────────────────────────────────────────────────
    # Comando estratégico (POST — não é chat)
    # ─────────────────────────────────────────────────────────────────

    def process_command(self, command: str) -> dict:
        """
        Processa um comando estratégico e retorna análise estruturada.

        NÃO é um chatbot. NÃO gera texto livre de IA generativa.
        Interpreta o comando para identificar filtros (produto, país, tipo de análise)
        e retorna dados reais estruturados.

        Comandos reconhecidos:
          - "alerta" / "risco" → eventos e cards de risco
          - "comprar" / "oportunidade" → cards de compra ranqueados
          - "clima {pais}" → análise climática do país
          - "preco {produto}" → preços disponíveis do produto
          - "tese {produto} {pais}" → tese completa
          - "pulse" / "status" / "saude" → pulso do sistema
          - "resumo" → resumo executivo
        """
        self.observe_now()

        cmd = command.strip().lower()

        # Detectar intenção
        intent = 'unknown'
        filters = {'product': '', 'country': '', 'region': ''}

        if any(w in cmd for w in ('alerta', 'risco', 'perigo', 'geada')):
            intent = 'risks'
        elif any(w in cmd for w in ('comprar', 'oportunidade', 'compra')):
            intent = 'opportunities'
        elif any(w in cmd for w in ('vender', 'venda')):
            intent = 'sell_signals'
        elif any(w in cmd for w in ('clima', 'tempo', 'chuva', 'temperatura')):
            intent = 'climate'
        elif any(w in cmd for w in ('preco', 'preço', 'custo', 'valor')):
            intent = 'prices'
        elif any(w in cmd for w in ('tese', 'analise', 'análise', 'detalhado')):
            intent = 'thesis'
        elif any(w in cmd for w in ('pulse', 'saude', 'saúde', 'status', 'estado')):
            intent = 'pulse'
        elif any(w in cmd for w in ('resumo', 'executivo', 'hoje')):
            intent = 'summary'
        elif any(w in cmd for w in ('monitorar', 'monitoramento', 'vigilancia')):
            intent = 'monitor'

        # Detectar país no comando
        for cc, name in _COUNTRIES.items():
            if cc.lower() in cmd or name.lower() in cmd:
                filters['country'] = cc
                break

        # Detectar produto
        from flv.price_normalizer import PRODUCT_NAME_MAP
        for variant, slug in PRODUCT_NAME_MAP.items():
            if variant in cmd:
                filters['product'] = slug
                break

        # Executar análise baseada na intenção
        if intent == 'pulse':
            data = self.generate_system_pulse()
            return {
                'intent':    'pulse',
                'command':   command,
                'resultado': data,
                'tipo':      'pulso_sistema',
                'nota':      'Pulso do sistema NIAS com frescor de todas as fontes.',
            }

        if intent == 'risks':
            events = [e for e in self.generate_live_events()
                      if e.get('gravidade') in ('critica', 'alta')]
            cards  = [c for c in self.generate_decision_cards()
                      if c.get('tipo') == 'alerta']
            if filters['country']:
                events = [e for e in events if e.get('pais') == filters['country']]
                cards  = [c for c in cards  if c.get('pais') == filters['country']]
            return {
                'intent':    'risks',
                'command':   command,
                'filtros':   filters,
                'eventos':   events,
                'cards':     cards[:5],
                'total':     len(events),
                'tipo':      'analise_risco',
                'nota':      'Riscos baseados em dados climáticos reais. Nenhum dado inventado.',
            }

        if intent == 'opportunities':
            cards = [c for c in self.generate_decision_cards()
                     if c.get('tipo') in ('comprar', 'antecipar_compra') and c.get('has_price')]
            if filters['country']:
                cards = [c for c in cards if c.get('pais') == filters['country']]
            if filters['product']:
                cards = [c for c in cards if filters['product'] in (c.get('produto') or '').lower()]
            return {
                'intent':    'opportunities',
                'command':   command,
                'filtros':   filters,
                'cards':     cards[:5],
                'total':     len(cards),
                'tipo':      'oportunidades_compra',
                'nota': (
                    'Apenas oportunidades com preço real disponível são incluídas. '
                    'Sem preço → tipo máximo = monitorar.'
                ) if not cards else '',
            }

        if intent == 'climate':
            events = [e for e in self.generate_live_events()
                      if e.get('tipo') in ('clima_extremo', 'clima_atencao', 'risco_geada', 'chuva_intensa')]
            if filters['country']:
                events = [e for e in events if e.get('pais') == filters['country']]
            return {
                'intent':    'climate',
                'command':   command,
                'filtros':   filters,
                'eventos':   events,
                'polos':     len([w for w in self._weather_data
                                  if not filters['country'] or w.get('country_code') == filters['country']]),
                'tipo':      'analise_clima',
                'nota':      'Dados Open-Meteo. Apenas eventos detectados no dia atual.',
            }

        if intent == 'prices':
            prices = self._price_data
            if filters['country']:
                prices = [p for p in prices if p.get('country_code') == filters['country']]
            if filters['product']:
                prices = [p for p in prices if filters['product'] in (p.get('product_normalized') or '').lower()]
            return {
                'intent':    'prices',
                'command':   command,
                'filtros':   filters,
                'precos':    prices[:10],
                'total':     len(prices),
                'tipo':      'consulta_precos',
                'nota':      'Preços mais recentes do banco. Nenhum preço inventado.',
            }

        if intent in ('thesis', 'summary'):
            thesis = self.generate_thesis(
                product=filters['product'],
                country=filters['country'],
                region=filters['region'],
            )
            return {
                'intent':    intent,
                'command':   command,
                'filtros':   filters,
                'tese':      thesis,
                'tipo':      'tese_detalhada',
            }

        # Fallback: resumo geral
        pulse   = self.generate_system_pulse()
        events  = self.generate_live_events()
        n_crit  = sum(1 for e in events if e.get('gravidade') == 'critica')

        return {
            'intent':    'summary',
            'command':   command,
            'filtros':   filters,
            'pulso':     {'health': pulse['health'], 'sources': len(pulse['sources'])},
            'eventos': {
                'total':   len(events),
                'criticos': n_crit,
                'lista':   events[:3],
            },
            'recomendacoes': pulse.get('recommendations', {}),
            'tipo':      'resumo_geral',
            'nota':      (
                'Comando não reconhecido diretamente. Mostrando resumo geral. '
                'Use: alerta, comprar, clima, preco, tese, pulse, resumo.'
            ) if intent == 'unknown' else '',
        }


# ─── Fábrica ──────────────────────────────────────────────────────────────────

def get_brain(conn: sqlite3.Connection) -> NiasBrainEngine:
    return NiasBrainEngine(conn)
