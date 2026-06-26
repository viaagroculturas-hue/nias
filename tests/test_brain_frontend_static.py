"""
Testes: estrutura estática do frontend — panel-brain em index.html.
Valida presença de elementos, scripts e integração com a navegação.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'index.html')


@pytest.fixture(scope='module')
def html():
    with open(HTML_PATH, encoding='utf-8') as f:
        return f.read()


# ─── Estrutura do panel-brain ─────────────────────────────────────────────────

def test_panel_brain_exists(html):
    assert 'id="panel-brain"' in html, 'panel-brain ausente no index.html'


def test_panel_brain_has_header(html):
    assert 'CÉREBRO NIAS' in html or 'CEREBRO NIAS' in html or 'CÉREBRO' in html


def test_panel_brain_has_pulse_section(html):
    assert 'brain-pulse-sources' in html, 'Seção de pulso ausente'


def test_panel_brain_has_events_section(html):
    assert 'brain-events-list' in html, 'Seção de eventos ausente'


def test_panel_brain_has_cards_section(html):
    assert 'brain-cards-grid' in html, 'Grade de cartões ausente'


def test_panel_brain_has_radar_section(html):
    assert 'brain-radar-view' in html, 'Seção de radar ausente'


def test_panel_brain_has_command_section(html):
    assert 'brain-cmd-input' in html, 'Campo de comando ausente'
    assert 'brain-cmd-result' in html, 'Área de resultado do comando ausente'


def test_panel_brain_has_radar_horizon_buttons(html):
    for h in ('agora', '24h', '48h', '3d', '7d', '15d', '30d'):
        assert f"showRadarHorizon('{h}')" in html, f"Botão de horizonte {h!r} ausente"


def test_panel_brain_has_card_filter_buttons(html):
    for f in ('alerta', 'comprar', 'monitorar'):
        assert f"brainFilterCards('{f}')" in html, f"Filtro de card {f!r} ausente"


# ─── Navegação ────────────────────────────────────────────────────────────────

def test_nav_has_brain_button(html):
    assert "showPanel('brain')" in html, "Botão nav para panel-brain ausente"


def test_nav_brain_is_not_chat_alias(html):
    # O botão de CÉREBRO não deve apontar para 'chat'
    brain_button_area = html[html.find("CÉREBRO NIAS"):html.find("CÉREBRO NIAS")+300] if "CÉREBRO NIAS" in html else ''
    assert "showPanel('chat')" not in brain_button_area or brain_button_area == ''


def test_panel_chat_still_exists(html):
    """panel-chat deve existir — apenas rebaixado, não removido."""
    assert 'id="panel-chat"' in html, 'panel-chat não deve ser removido — apenas rebaixado'


# ─── JavaScript do brain ──────────────────────────────────────────────────────

def test_loadBrain_function_exists(html):
    assert 'window.loadBrain' in html or 'loadBrain = function' in html


def test_sendBrainCommand_function_exists(html):
    assert 'window.sendBrainCommand' in html or 'sendBrainCommand = function' in html


def test_showRadarHorizon_function_exists(html):
    assert 'window.showRadarHorizon' in html or 'showRadarHorizon = function' in html


def test_brainFilterCards_function_exists(html):
    assert 'window.brainFilterCards' in html or 'brainFilterCards = function' in html


def test_initBrainPanel_function_exists(html):
    assert 'window.initBrainPanel' in html or 'initBrainPanel = function' in html


# ─── showPanel hook ───────────────────────────────────────────────────────────

def test_showpanel_has_brain_hook(html):
    assert "id === 'brain'" in html, 'showPanel não tem hook para brain'


def test_showpanel_calls_loadBrain(html):
    assert 'loadBrain' in html


# ─── Comando estratégico ──────────────────────────────────────────────────────

def test_command_not_chat(html):
    """Comando estratégico NÃO deve ter interface de chat tradicional."""
    # O panel-brain não deve ter bubbles de chat
    brain_start = html.find('id="panel-brain"')
    brain_end   = html.find('id="panel-chat"')
    if brain_start < 0 or brain_end < 0:
        return
    brain_section = html[brain_start:brain_end]
    assert 'msg-bubble' not in brain_section, 'panel-brain não deve ter msg-bubble (interface de chat)'
    assert 'chat-messages' not in brain_section, 'panel-brain não deve ter chat-messages'


def test_command_ctrl_enter_hint(html):
    """Deve indicar Ctrl+Enter como atalho para executar comando."""
    assert 'Ctrl+Enter' in html or 'ctrlKey' in html


# ─── API endpoints referenciados ─────────────────────────────────────────────

def test_brain_api_pulse_called(html):
    assert '/api/nias/brain/pulse' in html


def test_brain_api_events_called(html):
    assert '/api/nias/brain/events' in html


def test_brain_api_decisions_called(html):
    assert '/api/nias/brain/decisions' in html


def test_brain_api_radar_called(html):
    assert '/api/nias/brain/radar' in html


def test_brain_api_command_called(html):
    assert '/api/nias/brain/command' in html


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
