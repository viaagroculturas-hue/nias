"""
NIAS Revolution — test_navigation_static.py
Verifica que a navegação tem os 9 centros corretos, sem menus confusos,
sem telas duplicadas, sem chat como protagonista.
"""
import re
import os
import pytest

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'index.html')

# Os 9 centros obrigatórios do NIAS
REQUIRED_PANELS = {
    'overview': 'PULSO',
    'brain':    'CÉREBRO',
    'advisor':  'RADAR',
    'map':      'MAPA VIVO',
    'oferta':   'PREÇOS',
    'biocommand': 'CLIMA',
    'logistica':  'LOGÍSTICA',
    'situation':  'FONTES',
    'warroom':    'WAR ROOM',
}


@pytest.fixture(scope='module')
def html():
    with open(HTML_PATH, encoding='utf-8') as f:
        return f.read()


# ─── Todos os 9 painéis existem ──────────────────────────────────────────────

def test_all_9_panels_have_nav_button(html):
    """Todos os 9 centros devem ter botão nav na sidebar."""
    missing = []
    for panel_id in REQUIRED_PANELS:
        if f"showPanel('{panel_id}')" not in html:
            missing.append(panel_id)
    assert missing == [], f'Painéis sem botão nav: {missing}'


def test_all_9_panel_divs_exist(html):
    """Todos os 9 painéis devem ter div correspondente."""
    missing = []
    for panel_id in REQUIRED_PANELS:
        if f'id="panel-{panel_id}"' not in html:
            missing.append(panel_id)
    assert missing == [], f'Divs de painel ausentes: {missing}'


def test_pulso_nav_button_exists(html):
    """Deve haver botão nav para PULSO (panel-overview)."""
    assert "showPanel('overview')" in html


def test_cerebro_nav_button_exists(html):
    """Deve haver botão nav para Cérebro NIAS."""
    assert "showPanel('brain')" in html


def test_radar_nav_button_exists(html):
    """Deve haver botão nav para RADAR."""
    assert "showPanel('advisor')" in html


def test_mapa_vivo_nav_button_exists(html):
    """Deve haver botão nav para MAPA VIVO."""
    assert "showPanel('map')" in html


def test_logistica_nav_button_exists(html):
    """Deve haver botão nav para LOGÍSTICA."""
    assert "showPanel('logistica')" in html


def test_fontes_nav_button_exists(html):
    """Deve haver botão nav para FONTES."""
    assert "showPanel('situation')" in html


def test_warroom_nav_button_exists(html):
    """Deve haver botão nav para WAR ROOM."""
    assert "showPanel('warroom')" in html


# ─── Ordem lógica do menu ─────────────────────────────────────────────────────

def test_pulso_appears_before_brain_in_nav(html):
    """PULSO deve aparecer antes do Cérebro na sidebar."""
    p1 = html.find("showPanel('overview')")
    p2 = html.find("showPanel('brain')")
    assert p1 >= 0 and p2 >= 0 and p1 < p2


def test_brain_appears_before_radar_in_nav(html):
    """Cérebro deve aparecer antes do Radar na sidebar."""
    p1 = html.find("showPanel('brain')")
    p2 = html.find("showPanel('advisor')")
    assert p1 >= 0 and p2 >= 0 and p1 < p2


def test_radar_appears_before_mapa_in_nav(html):
    """Radar deve aparecer antes do Mapa Vivo na sidebar."""
    p1 = html.find("showPanel('advisor')")
    p2 = html.find("showPanel('map')")
    assert p1 >= 0 and p2 >= 0 and p1 < p2


def test_logistica_appears_before_fontes_in_nav(html):
    """Logística deve aparecer antes de Fontes na sidebar."""
    p1 = html.find("showPanel('logistica')")
    p2 = html.find("showPanel('situation')")
    assert p1 >= 0 and p2 >= 0 and p1 < p2


# ─── Painel PULSO tem conteúdo vivo ─────────────────────────────────────────

def test_pulso_panel_has_events_list(html):
    """Panel-overview deve ter lista de eventos vivos do Cérebro."""
    assert 'pulse-events-list' in html


def test_pulso_panel_has_decisions_list(html):
    """Panel-overview deve ter lista de decisões/oportunidades."""
    assert 'pulse-decisions-list' in html


def test_pulso_panel_has_brain_health(html):
    """Panel-overview deve mostrar saúde do Cérebro NIAS."""
    assert 'pulse-brain-health' in html or 'ph-brain-health' in html


def test_pulso_panel_has_last_update(html):
    """Panel-overview deve mostrar última e próxima atualização."""
    assert 'pulse-last-update' in html


def test_pulso_has_loadpulso_function(html):
    """Função loadPulso deve existir."""
    assert 'window.loadPulso' in html or 'loadPulso' in html


def test_pulso_loads_on_panel_open(html):
    """showPanel('overview') deve chamar loadPulso."""
    idx = html.find("id === 'overview'")
    assert idx >= 0, "showPanel deve ter hook para 'overview'"
    snippet = html[idx:idx+80]
    assert 'loadPulso' in snippet


# ─── Radar tem filtros por produto/país/horizonte ────────────────────────────

def test_radar_has_filter_buttons(html):
    """RADAR deve ter botões de filtro."""
    idx = html.find('id="panel-advisor"')
    assert idx >= 0
    section = html[idx:idx+5000]
    # deve ter pelo menos filtros de alerta, país, etc.
    assert 'advisorFilter' in section or 'advisor-filter' in section


def test_radar_header_is_not_conselheiro(html):
    """Header do RADAR não deve usar apenas 'CONSELHEIRO' como título principal."""
    idx = html.find('id="panel-advisor"')
    assert idx >= 0
    # Verifica que o header foi atualizado para RADAR
    header_area = html[idx:idx+600]
    assert 'RADAR' in header_area


# ─── Chat não é protagonista ─────────────────────────────────────────────────

def test_chat_not_primary_nav_button(html):
    """Não deve haver botão de navegação primário para chat."""
    sidebar_start = html.find('<div id="sidebar">')
    sidebar_end   = html.find('</div>', sidebar_start + 100)
    # Buscar a sidebar completa (até o primeiro </div> que fecha o sidebar)
    # Usar uma janela maior
    sidebar = html[sidebar_start:sidebar_start + 2000]
    # chat pode aparecer na sidebar apenas como item secundário, não primário
    chat_in_sidebar = "showPanel('chat')" in sidebar
    brain_in_sidebar = "showPanel('brain')" in sidebar
    if chat_in_sidebar and brain_in_sidebar:
        brain_pos = sidebar.find("showPanel('brain')")
        chat_pos  = sidebar.find("showPanel('chat')")
        assert brain_pos < chat_pos, "Cérebro NIAS deve vir antes de chat na nav"


def test_cerebro_nias_label_in_nav(html):
    """Label 'CÉREBRO' deve estar na navegação."""
    idx = html.find('<div id="sidebar">')
    sidebar = html[idx:idx+2500]
    assert 'CÉREBRO' in sidebar or 'CEREBRO' in sidebar


# ─── Sidebar tem estrutura correta ───────────────────────────────────────────

def test_sidebar_has_expand_button(html):
    """Sidebar deve ter botão de expandir/recolher."""
    assert 'toggleSidebar' in html


def test_sidebar_exists(html):
    """Elemento #sidebar deve existir."""
    assert 'id="sidebar"' in html


def test_main_area_exists(html):
    """Área #main deve existir."""
    assert 'id="main"' in html


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
