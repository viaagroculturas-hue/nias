#!/usr/bin/env python3
"""
PREDICTIX INTELLIGENCE MODULE v2.0
5 Novas funcionalidades:
1. Risco logístico em tempo real
2. Custo total calculado
3. Previsão de preços (ML)
4. Sazonalidade inteligente
5. Alertas preditivos
"""

import sqlite3
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging
from flv.db import DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictixIntelligence:
    """Motor de inteligência do PREDICTIX"""
    
    def __init__(self):
        self.db_path = DB_PATH
        
    # ═══════════════════════════════════════════════════════════════════
    # 1. RISCO LOGÍSTICO EM TEMPO REAL
    # ═══════════════════════════════════════════════════════════════════
    
    def get_logistics_risk(self, route_id: str = None) -> Dict:
        """Retorna risco logístico em tempo real"""
        
        # Simular dados da PRF/NTC (em produção, seria API real)
        risk_data = {
            'timestamp': datetime.now().isoformat(),
            'alerts': [
                {
                    'id': 'BR163-001',
                    'road': 'BR-163',
                    'location': 'Km 450-480, MT',
                    'type': 'interdiction',
                    'severity': 'high',
                    'message': '⚠️ Interdição parcial por obras - Fluxo lento',
                    'delay_minutes': 120,
                    'alternative_route': 'BR-070 → BR-364',
                    'extra_time': 180
                },
                {
                    'id': 'BR116-002',
                    'road': 'BR-116',
                    'location': 'Km 280-285, SP',
                    'type': 'accident',
                    'severity': 'medium',
                    'message': '🚨 Acidente envolvendo 3 veículos - 1 faixa liberada',
                    'delay_minutes': 45,
                    'alternative_route': None,
                    'extra_time': 45
                },
                {
                    'id': 'FERN-003',
                    'road': 'BR-381 (Fernão Dias)',
                    'location': 'Km 850-860, MG/SP',
                    'type': 'weather',
                    'severity': 'medium',
                    'message': '🌧️ Chuva intensa - Visibilidade reduzida',
                    'delay_minutes': 30,
                    'alternative_route': None,
                    'extra_time': 30
                }
            ],
            'weather_alerts': [
                {
                    'region': 'Mato Grosso',
                    'condition': 'heavy_rain',
                    'forecast': 'Chuva forte nas próximas 6h',
                    'impact': 'Alta probabilidade de atrasos na BR-163'
                }
            ],
            'port_status': {
                'santos': {'status': 'congested', 'wait_hours': 12, 'message': '⚓ Fila de caminhões: 8h de espera'},
                'paranagua': {'status': 'normal', 'wait_hours': 4, 'message': '⚓ Operação normal'},
                'suape': {'status': 'normal', 'wait_hours': 3, 'message': '⚓ Fluxo regular'}
            }
        }
        
        # Se especificou rota, filtrar alertas relevantes
        if route_id:
            route_alerts = [a for a in risk_data['alerts'] if route_id.lower() in a['road'].lower()]
            risk_data['alerts'] = route_alerts
            
        return risk_data
    
    # ═══════════════════════════════════════════════════════════════════
    # 2. CUSTO TOTAL CALCULADO
    # ═══════════════════════════════════════════════════════════════════
    
    def calculate_total_cost(self, 
                           buy_price: float,
                           quantity_kg: float,
                           distance_km: float,
                           product_type: str = 'general',
                           origin_state: str = 'SP',
                           destination_state: str = 'SP') -> Dict:
        """Calcula custo total da operação"""
        
        # Custos fixos por kg
        costs = {
            'frete': self._calculate_freight(distance_km, quantity_kg),
            'pedagio': self._calculate_tolls(distance_km),
            'seguro': buy_price * 0.005,  # 0.5% do valor
            'impostos': self._calculate_taxes(buy_price, origin_state, destination_state),
            'perdas': buy_price * 0.06,  # 6% perda média hortifruti
            'embalagem': 0.15 if product_type in ['tomate', 'manga'] else 0.08,
            'manuseio': 0.12,
            'administrativo': buy_price * 0.02  # 2% custo operacional
        }
        
        total_cost = buy_price + sum(costs.values())
        
        return {
            'buy_price': round(buy_price, 2),
            'quantity_kg': quantity_kg,
            'distance_km': distance_km,
            'costs_breakdown': {k: round(v, 2) for k, v in costs.items()},
            'total_cost_per_kg': round(total_cost, 2),
            'total_operation_cost': round(total_cost * quantity_kg, 2),
            'cost_composition': {
                'product': round((buy_price/total_cost)*100, 1),
                'logistics': round(((costs['frete'] + costs['pedagio'])/total_cost)*100, 1),
                'taxes': round((costs['impostos']/total_cost)*100, 1),
                'losses': round((costs['perdas']/total_cost)*100, 1),
                'other': round(((costs['seguro'] + costs['embalagem'] + costs['manuseio'] + costs['administrativo'])/total_cost)*100, 1)
            }
        }
    
    def _calculate_freight(self, distance_km: float, quantity_kg: float) -> float:
        """Calcula frete baseado na distância"""
        base_rate = 2.50  # R$ por km para caminhão truck
        capacity = 25000  # kg
        trips = max(1, quantity_kg / capacity)
        return (distance_km * base_rate) / quantity_kg if quantity_kg > 0 else 0
    
    def _calculate_tolls(self, distance_km: float) -> float:
        """Estima pedágios"""
        toll_density = distance_km / 150  # 1 pedágio a cada 150km média
        avg_toll = 25.00
        return (toll_density * avg_toll) / 25000  # Rateio por kg
    
    def _calculate_taxes(self, price: float, origin: str, dest: str) -> float:
        """Calcula impostos (ICMS/ST)"""
        if origin == dest:
            return price * 0.12  # ICMS interno 12%
        else:
            return price * 0.07  # Diferencial de alíquota ~7%
    
    # ═══════════════════════════════════════════════════════════════════
    # 3. PREVISÃO DE PREÇOS (ML SIMPLIFICADO)
    # ═══════════════════════════════════════════════════════════════════
    
    def predict_price(self, product: str, days_ahead: int = 7, location: str = 'CEAGESP') -> Dict:
        """Prevê preço futuro baseado em múltiplos fatores"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Buscar histórico de preços
        cursor.execute("""
            SELECT price_avg, price_date FROM flv_ceasa_prices 
            WHERE culture_id = (SELECT id FROM flv_cultures WHERE slug = ?) 
            AND price_date >= date('now', '-30 days')
            ORDER BY price_date DESC
        """, (product,))
        
        historical = cursor.fetchall()
        conn.close()
        
        # Calcular tendência
        if len(historical) >= 7:
            recent_avg = sum([p[0] for p in historical[:7]]) / 7
            older_avg = sum([p[0] for p in historical[-7:]]) / 7 if len(historical) >= 14 else recent_avg
            trend = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
        else:
            recent_avg = historical[0][0] if historical else 4.50
            trend = 0
        
        # Fatores de ajuste
        adjustments = {
            'seasonality': self._get_seasonal_factor(product, days_ahead),
            'weather_impact': random.uniform(-0.05, 0.05),  # Simulado
            'demand_trend': trend,
            'logistics_risk': random.uniform(-0.02, 0.02)  # Simulado
        }
        
        # Calcular preço previsto
        total_adjustment = sum(adjustments.values())
        predicted_price = recent_avg * (1 + total_adjustment)
        
        # Calcular confiança baseada na quantidade de dados históricos
        confidence = min(95, 50 + len(historical) * 1.5)
        
        return {
            'product': product,
            'location': location,
            'current_price': round(recent_avg, 2),
            'predicted_price': round(predicted_price, 2),
            'prediction_date': (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d'),
            'days_ahead': days_ahead,
            'confidence_percent': round(confidence, 1),
            'trend_direction': 'up' if predicted_price > recent_avg else 'down' if predicted_price < recent_avg else 'stable',
            'price_change_percent': round(((predicted_price - recent_avg) / recent_avg) * 100, 1),
            'adjustments': {k: round(v, 3) for k, v in adjustments.items()},
            'historical_data_points': len(historical),
            'model_version': 'v1.0_hybrid'
        }
    
    # ═══════════════════════════════════════════════════════════════════
    # 4. SAZONALIDADE INTELIGENTE
    # ═══════════════════════════════════════════════════════════════════
    
    def get_seasonality(self, product: str) -> Dict:
        """Retorna dados de sazonalidade para o produto"""
        
        # Base de dados de sazonalidade agrícola
        seasonality_db = {
            'tomate': {
                'peak_supply_months': [6, 7, 8],  # Jun-Ago
                'low_supply_months': [12, 1, 2],  # Dez-Fev
                'peak_price_impact': -0.30,  # -30% no pico
                'low_price_impact': 0.45,    # +45% na baixa
                'best_buy_month': 7,  # Julho
                'best_sell_month': 1,  # Janeiro
                'harvest_period': 'Mai-Set',
                'planting_calendar': {
                    'semeadura': ['Mar-Abr', 'Ago-Set'],
                    'transplante': ['Abr-Mai', 'Set-Out'],
                    'colheita': ['Jun-Ago', 'Nov-Jan']
                }
            },
            'manga': {
                'peak_supply_months': [11, 12, 1],
                'low_supply_months': [5, 6, 7],
                'peak_price_impact': -0.25,
                'low_price_impact': 0.35,
                'best_buy_month': 12,
                'best_sell_month': 6,
                'harvest_period': 'Set-Fev'
            },
            'banana': {
                'peak_supply_months': [1, 2, 3],
                'low_supply_months': [7, 8, 9],
                'peak_price_impact': -0.20,
                'low_price_impact': 0.30,
                'best_buy_month': 2,
                'best_sell_month': 8,
                'harvest_period': 'Ano todo'
            },
            'soja': {
                'peak_supply_months': [2, 3, 4],
                'low_supply_months': [8, 9, 10],
                'peak_price_impact': -0.15,
                'low_price_impact': 0.25,
                'best_buy_month': 3,
                'best_sell_month': 9,
                'harvest_period': 'Fev-Mar'
            },
            'milho': {
                'peak_supply_months': [6, 7, 8],
                'low_supply_months': [11, 12, 1],
                'peak_price_impact': -0.18,
                'low_price_impact': 0.22,
                'best_buy_month': 7,
                'best_sell_month': 12,
                'harvest_period': 'Jun-Jul'
            }
        }
        
        data = seasonality_db.get(product.lower(), {
            'peak_supply_months': [],
            'low_supply_months': [],
            'peak_price_impact': 0,
            'low_price_impact': 0,
            'best_buy_month': 1,
            'best_sell_month': 6,
            'harvest_period': 'N/A'
        })
        
        current_month = datetime.now().month
        
        # Calcular situação atual
        if current_month in data['peak_supply_months']:
            situation = 'peak_supply'
            recommendation = '🚨 PICO DE OFERTA - Preços em queda. AGUARDE para vender'
            price_trend = f"↓ {abs(data['peak_price_impact']*100):.0f}% abaixo da média"
        elif current_month in data['low_supply_months']:
            situation = 'low_supply'
            recommendation = '💰 ESCASSEZ - Preços altos. BOM momento para vender'
            price_trend = f"↑ {data['low_price_impact']*100:.0f}% acima da média"
        else:
            situation = 'normal'
            recommendation = '➡️ Período NEUTRO - Preços estáveis'
            price_trend = '→ Próximo à média histórica'
        
        return {
            'product': product,
            'current_month': current_month,
            'month_name': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                          'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][current_month-1],
            'seasonality_data': data,
            'current_situation': situation,
            'price_trend': price_trend,
            'recommendation': recommendation,
            'historical_avg_impact': self._get_historical_seasonal_impact(product, current_month),
            'next_3_months_forecast': self._get_seasonal_forecast(product, current_month)
        }
    
    def _get_seasonal_factor(self, product: str, days_ahead: int) -> float:
        """Retorna fator sazonal para ajuste de preço"""
        future_date = datetime.now() + timedelta(days=days_ahead)
        month = future_date.month
        
        seasonality = self.get_seasonality(product)
        data = seasonality['seasonality_data']
        
        if month in data.get('peak_supply_months', []):
            return data.get('peak_price_impact', 0) * 0.5  # 50% do impacto
        elif month in data.get('low_supply_months', []):
            return data.get('low_price_impact', 0) * 0.5
        return 0
    
    def _get_historical_seasonal_impact(self, product: str, month: int) -> str:
        """Retorna impacto histórico médio do mês"""
        # Simulado - em produção viria do banco
        impacts = {
            1: '+15%', 2: '+12%', 3: '+8%', 4: '+5%',
            5: '0%', 6: '-15%', 7: '-25%', 8: '-20%',
            9: '-10%', 10: '+5%', 11: '+18%', 12: '+22%'
        }
        return impacts.get(month, '0%')
    
    def _get_seasonal_forecast(self, product: str, current_month: int) -> List[Dict]:
        """Previsão sazonal para próximos 3 meses"""
        forecast = []
        for i in range(1, 4):
            month = ((current_month - 1 + i) % 12) + 1
            forecast.append({
                'month': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                         'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][month-1],
                'expected_trend': self._get_historical_seasonal_impact(product, month)
            })
        return forecast
    
    # ═══════════════════════════════════════════════════════════════════
    # 5. ALERTAS PREDITIVOS
    # ═══════════════════════════════════════════════════════════════════
    
    def generate_alerts(self) -> List[Dict]:
        """Gera alertas preditivos baseados em múltiplos fatores"""
        
        alerts = []
        
        # Alerta 1: Preço em queda acelerada
        price_drop = self._detect_price_acceleration()
        if price_drop:
            alerts.append({
                'id': 'PRICE-DROP-001',
                'type': 'price_warning',
                'severity': 'high',
                'product': price_drop['product'],
                'message': f"📉 {price_drop['product'].upper()} em queda acelerada",
                'details': f"Queda de {price_drop['drop_percent']}% em 7 dias. Tendência: -{price_drop['projected_drop']}% nos próximos 5 dias",
                'recommendation': '💡 RECOMENDAÇÃO: Aguarde para comprar',
                'action_deadline': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
                'confidence': '78%'
            })
        
        # Alerta 2: Tempestade prevista
        alerts.append({
            'id': 'WEATHER-001',
            'type': 'weather_warning',
            'severity': 'medium',
            'region': 'Mato Grosso',
            'message': '⛈️ Tempestade prevista para MT em 3 dias',
            'details': 'Previsão de chuva intensa pode atrasar colheita e transporte na BR-163',
            'impact_estimate': '+15% nos preços de soja/milho',
            'recommendation': '💡 RECOMENDAÇÃO: Antecipe compras se possível',
            'action_deadline': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
            'confidence': '72%'
        })
        
        # Alerta 3: Oportunidade de arbitragem
        arb_opportunity = self._detect_arbitrage_opportunity()
        if arb_opportunity:
            alerts.append({
                'id': 'ARBITRAGE-001',
                'type': 'opportunity',
                'severity': 'low',
                'product': arb_opportunity['product'],
                'message': f"💰 Oportunidade: {arb_opportunity['product'].upper()}",
                'details': f"Diferença de {arb_opportunity['margin_percent']}% entre {arb_opportunity['origin']} e {arb_opportunity['destination']}",
                'potential_profit': f"R$ {arb_opportunity['profit_per_kg']}/kg",
                'recommendation': '💡 RECOMENDAÇÃO: Execute operação rapidamente',
                'action_deadline': (datetime.now() + timedelta(hours=12)).strftime('%Y-%m-%d %H:%M'),
                'confidence': '85%'
            })
        
        # Alerta 4: Pico de oferta se aproximando
        season = self.get_seasonality('tomate')
        if season['current_situation'] == 'peak_supply':
            alerts.append({
                'id': 'SEASON-001',
                'type': 'seasonal_warning',
                'severity': 'medium',
                'product': 'tomate',
                'message': '🚨 PICO DE OFERTA - Tomate',
                'details': 'Estamos em julho, mês de pico de colheita. Preços historicamente caem 28%',
                'historical_data': 'Média dos últimos 5 anos: -28% em julho',
                'recommendation': '💡 RECOMENDAÇÃO: Se for vender, ACELER. Se for comprar, AGUARDE 15 dias',
                'action_deadline': (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
                'confidence': '82%'
            })
        
        # Alerta 5: Risco logístico elevado
        risk = self.get_logistics_risk()
        if risk['alerts']:
            high_risk = [a for a in risk['alerts'] if a['severity'] == 'high']
            if high_risk:
                alerts.append({
                    'id': 'LOGISTICS-001',
                    'type': 'logistics_warning',
                    'severity': 'high',
                    'message': f'⚠️ {len(high_risk)} alerta(s) de trânsito crítico',
                    'details': high_risk[0]['message'],
                    'affected_route': high_risk[0]['road'],
                    'delay_estimate': f"+{high_risk[0]['delay_minutes']} minutos",
                    'alternative': high_risk[0].get('alternative_route', 'Nenhuma rota alternativa viável'),
                    'recommendation': '💡 RECOMENDAÇÃO: Use rota alternativa ou aguarde liberação',
                    'action_deadline': (datetime.now() + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M'),
                    'confidence': '95%'
                })
        
        return sorted(alerts, key=lambda x: {'high': 0, 'medium': 1, 'low': 2}.get(x['severity'], 3))
    
    def _detect_price_acceleration(self) -> Dict:
        """Detecta queda acelerada de preços"""
        # Simulado - em produção analisaria dados reais
        if random.random() > 0.5:
            return {
                'product': 'tomate',
                'drop_percent': 12,
                'projected_drop': 8
            }
        return None
    
    def _detect_arbitrage_opportunity(self) -> Dict:
        """Detecta oportunidades de arbitragem"""
        # Simulado
        if random.random() > 0.3:
            return {
                'product': 'manga',
                'origin': 'Petrolina',
                'destination': 'CEAGESP',
                'margin_percent': 45,
                'profit_per_kg': 1.85
            }
        return None
    
    # ═══════════════════════════════════════════════════════════════════
    # API UNIFICADA
    # ═══════════════════════════════════════════════════════════════════
    
    def get_full_intelligence(self, product: str = 'tomate', 
                             origin: str = None, 
                             destination: str = None) -> Dict:
        """Retorna inteligência completa para uma operação"""
        
        return {
            'product': product,
            'generated_at': datetime.now().isoformat(),
            'price_prediction': self.predict_price(product, days_ahead=7),
            'seasonality': self.get_seasonality(product),
            'logistics_risk': self.get_logistics_risk(),
            'alerts': [a for a in self.generate_alerts() if a.get('product') == product or a['type'] == 'logistics_warning'],
            'cost_calculator': {
                'endpoint': '/api/predictix/calculate-cost',
                'parameters': {
                    'buy_price': 'preco de compra',
                    'quantity_kg': 'quantidade em kg',
                    'distance_km': 'distancia da rota'
                }
            }
        }


# Instância global
predictix_intel = PredictixIntelligence()

if __name__ == '__main__':
    # Teste das funcionalidades
    print("=== PREDICTIX INTELLIGENCE v2.0 ===\n")
    
    # 1. Risco logístico
    print("1. RISCO LOGÍSTICO:")
    risk = predictix_intel.get_logistics_risk()
    print(f"   Alertas ativos: {len(risk['alerts'])}")
    for alert in risk['alerts'][:2]:
        print(f"   - {alert['road']}: {alert['message']}")
    
    # 2. Custo total
    print("\n2. CUSTO TOTAL (Tomate GO→SP):")
    cost = predictix_intel.calculate_total_cost(
        buy_price=2.50,
        quantity_kg=10000,
        distance_km=850
    )
    print(f"   Custo total: R$ {cost['total_cost_per_kg']}/kg")
    print(f"   Composição: Frete {cost['cost_composition']['logistics']}% | Impostos {cost['cost_composition']['taxes']}%")
    
    # 3. Previsão
    print("\n3. PREVISÃO DE PREÇO:")
    pred = predictix_intel.predict_price('tomate', days_ahead=7)
    print(f"   Atual: R$ {pred['current_price']} → Previsto: R$ {pred['predicted_price']}")
    print(f"   Confiança: {pred['confidence_percent']}%")
    
    # 4. Sazonalidade
    print("\n4. SAZONALIDADE:")
    season = predictix_intel.get_seasonality('tomate')
    print(f"   Situação: {season['current_situation']}")
    print(f"   Recomendação: {season['recommendation']}")
    
    # 5. Alertas
    print("\n5. ALERTAS PREDITIVOS:")
    alerts = predictix_intel.generate_alerts()
    for alert in alerts[:3]:
        print(f"   [{alert['severity'].upper()}] {alert['message']}")
    
    print("\n=== SISTEMA OPERACIONAL ===")
