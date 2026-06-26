"""
ETAPA 11: Verifica mapas no index.html.
- Container do mapa Leaflet principal existe
- 42+ polos SA configurados via /api/nias/regions fetch
- 9 países SA cobertos
- Cada layer toggle tem correspondente em mapLayerObjs ou logMapLayers
- Portos SA (12) configurados
- Corredores internacionais SA configurados
"""
import re
import os
import pytest

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'index.html')

SA_COUNTRIES_9 = {'BR', 'AR', 'CL', 'UY', 'PY', 'BO', 'PE', 'CO', 'EC'}

SA_PORTS_REQUIRED = [
    'Santos', 'Paranaguá', 'Rio Grande', 'Suape', 'Itaqui',
    'Buenos Aires', 'Montevidéu', 'Valparaíso', 'San Antonio', 'Callao',
    'Guayaquil', 'Cartagena',
]

SA_CORRIDORS_REQUIRED = [
    'BR→AR', 'BR→PY', 'BR→UY', 'CL↔AR', 'PE↔BO', 'Bioceânica',
]


@pytest.fixture(scope='module')
def html():
    with open(HTML_PATH, encoding='utf-8') as f:
        return f.read()


# ─── Painéis e containers ────────────────────────────────────────────────────

def test_panel_map_exists(html):
    """panel-map deve existir."""
    assert 'id="panel-map"' in html


def test_panel_logistica_exists(html):
    """panel-logistica deve existir."""
    assert 'id="panel-logistica"' in html


def test_leaflet_map_container_exists(html):
    """Container do mapa Leaflet principal (#map) deve existir em panel-map."""
    assert 'id="map"' in html, "Container #map não encontrado"


def test_logmap_container_exists(html):
    """Container do logMap (#logMap) deve existir em panel-logistica."""
    assert 'id="logMap"' in html


def test_bcmap_container_exists(html):
    """Container do bcMap (#bc-map) deve existir em panel-biocommand."""
    assert 'id="bc-map"' in html or 'bcMap' in html


# ─── Inicialização dos mapas ─────────────────────────────────────────────────

def test_init_map_function_exists(html):
    """function initMap() deve existir."""
    assert 'function initMap()' in html


def test_init_sankey_function_exists(html):
    """function initSankey() deve existir (logMap)."""
    assert 'function initSankey()' in html


def test_showpanel_triggers_initmap(html):
    """showPanel('map') deve chamar initMap."""
    idx = html.find("id === 'map'")
    assert idx >= 0, "showPanel deve inicializar mapa quando id='map'"
    snippet = html[idx:idx+100]
    assert 'initMap' in snippet


def test_showpanel_triggers_initlogistica(html):
    """showPanel('logistica') deve chamar initSankey."""
    idx = html.find("id === 'logistica'")
    assert idx >= 0, "showPanel deve inicializar logMap quando id='logistica'"
    snippet = html[idx:idx+120]
    assert 'initSankey' in snippet or 'sankeyInit' in snippet


# ─── Polos SA ────────────────────────────────────────────────────────────────

def test_sa_poles_fetched_from_api(html):
    """/api/nias/regions deve ser chamado para carregar polos SA."""
    assert '/api/nias/regions' in html, "Mapa principal deve buscar polos de /api/nias/regions"


def test_sa_poles_layer_added_to_map(html):
    """sa-poles layer deve ser adicionado ao leafletMap."""
    assert "mapLayerObjs['sa-poles']" in html


def test_sa_poles_have_tooltip(html):
    """Marcadores dos polos SA devem ter tooltip."""
    idx = html.find("mapLayerObjs['sa-poles']")
    assert idx >= 0
    section = html[max(0,idx-2000):idx+200]
    assert 'bindTooltip' in section or 'tooltip' in section.lower()


def test_pole_click_shows_detail(html):
    """Clique no polo SA deve mostrar painel de detalhes."""
    assert '_showPoleDetail' in html, "Função _showPoleDetail deve existir para clique nos polos"


def test_pole_detail_has_disabled_buttons_with_explanation(html):
    """Painel de detalhes do polo deve ter botões desabilitados com explicação."""
    idx = html.find('function _showPoleDetail(')
    assert idx >= 0
    section = html[idx:idx+3000]
    assert 'disabled' in section
    assert 'title=' in section


# ─── 9 Países SA ─────────────────────────────────────────────────────────────

def test_9_countries_in_sa_regions_api(html):
    """Os 9 países SA monitorados devem ser referenciados no código."""
    for cc in SA_COUNTRIES_9:
        assert f"'{cc}'" in html or f'"{cc}"' in html, f"País {cc} não encontrado no HTML"


def test_country_borders_layer_exists(html):
    """Layer country-borders deve ser registrado."""
    assert "mapLayerObjs['country-borders']" in html


# ─── Layer toggles principais ────────────────────────────────────────────────

def test_soja_layer_registered(html):
    assert "addZones('soja'" in html or "mapLayerObjs['soja']" in html


def test_milho_layer_registered(html):
    assert "addZones('milho'" in html or "mapLayerObjs['milho']" in html


def test_portos_layer_registered(html):
    assert "mapLayerObjs['portos']" in html


def test_planet_toggle_exists(html):
    """Checkbox para camada Planet deve existir."""
    assert "toggleLayer('planet'" in html


def test_planet_layer_shows_message_not_silent(html):
    """toggleLayer deve exibir mensagem explicativa para camada planet indisponível."""
    idx = html.find('function toggleLayer(')
    assert idx >= 0
    body = html[idx:idx+800]
    assert 'planet' in body
    assert 'indisponível' in body or 'Camada' in body


# ─── Logística SA ────────────────────────────────────────────────────────────

def test_sa_corridors_in_logmap(html):
    """Corredores internacionais SA devem estar no logMap."""
    assert "logMapLayers['sa-corridors']" in html


def test_sa_portos_in_logmap(html):
    """12 portos SA devem estar no logMap."""
    assert "logMapLayers['sa-portos']" in html


def test_required_sa_ports_present(html):
    """Os 12 portos SA nomeados devem estar presentes."""
    for port in SA_PORTS_REQUIRED:
        assert port in html, f"Porto SA ausente: {port}"


def test_required_corridors_present(html):
    """Corredores internacionais SA devem estar presentes."""
    for corridor in SA_CORRIDORS_REQUIRED:
        assert corridor in html, f"Corredor SA ausente: {corridor}"


# ─── Tooltip e clique em marcadores ─────────────────────────────────────────

def test_logmap_ports_have_tooltip(html):
    """Marcadores de portos no logMap devem ter tooltip."""
    idx = html.find("logMapLayers['sa-portos']")
    assert idx >= 0
    section = html[max(0,idx-3000):idx+200]
    assert 'tooltip' in section.lower() or 'bindTooltip' in section


def test_logmap_roads_have_tooltip(html):
    """Rodovias no logMap devem ter tooltip."""
    assert 'bindTooltip' in html[html.find('logMapLayers[\'rodovias\']')-2000:html.find('logMapLayers[\'rodovias\']')+200]


# ─── showPolosMap redireciona para mapa interativo ───────────────────────────

def test_showpolosmap_navigates_to_panel_map(html):
    """showPolosMap deve chamar showPanel('map'), não mostrar PNG estático."""
    idx = html.find('function showPolosMap()')
    assert idx >= 0
    body = html[idx:idx+200]
    assert "showPanel('map')" in body, \
        "showPolosMap deve navegar para panel-map interativo, não mostrar PNG estático"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
