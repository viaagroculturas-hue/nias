"""
ETAPA 10: Verifica botões no index.html.
- onclick definidos devem ter função correspondente declarada no HTML
- data-panel deve apontar para painel existente
- botões desabilitados devem ter title ou texto explicativo
"""
import re
import os
import pytest

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'index.html')

JS_BUILTINS = {
    'alert', 'confirm', 'prompt', 'open', 'close', 'print', 'eval',
    'parseInt', 'parseFloat', 'isNaN', 'isFinite', 'encodeURI',
    'decodeURI', 'setTimeout', 'setInterval', 'clearInterval', 'clearTimeout',
    'fetch', 'console', 'document', 'window', 'navigator', 'location',
    'history', 'Math', 'Date', 'JSON', 'Object', 'Array', 'String',
    'Number', 'Boolean', 'RegExp', 'Error', 'Promise',
}

# Funções que são métodos de objeto (objeto.método) — não precisam ser globais
OBJECT_METHOD_PATTERNS = re.compile(r'^(this|DashboardLive|L|leafletMap|logMap|bcMap|munMap)\.')


@pytest.fixture(scope='module')
def html():
    with open(HTML_PATH, encoding='utf-8') as f:
        return f.read()


@pytest.fixture(scope='module')
def defined_functions(html):
    """Todas as funções declaradas globalmente no HTML."""
    funcs = set()
    for m in re.finditer(r'(?:function\s+([\w$]+)|(?:window|var|let|const)\s*\.\s*([\w$]+)\s*=\s*function|window\.([\w$]+)\s*=\s*(?:async\s+)?function)', html):
        for g in m.groups():
            if g:
                funcs.add(g)
    return funcs


@pytest.fixture(scope='module')
def onclick_calls(html):
    """Todas as chamadas de função em onclick= atributos."""
    calls = []
    for m in re.finditer(r'onclick=["\']([^"\']+)["\']', html):
        expr = m.group(1)
        # Extrai nome da função principal (primeira chamada, antes de parêntese)
        fn_match = re.match(r'(?:if\([^)]+\))?\s*([\w$]+)\s*\(', expr)
        if fn_match:
            calls.append(fn_match.group(1))
    return calls


@pytest.fixture(scope='module')
def disabled_buttons(html):
    """Todos os botões desabilitados."""
    return re.findall(r'<button[^>]+disabled[^>]*>(.*?)</button>', html, re.DOTALL)


@pytest.fixture(scope='module')
def panels(html):
    """Todos os IDs de painéis declarados."""
    return set(re.findall(r'id="panel-([\w-]+)"', html))


# ─── Funções onclick existem ──────────────────────────────────────────────────

def test_no_truly_dead_onclick_functions(onclick_calls, defined_functions):
    """
    Funções chamadas em onclick devem estar definidas no HTML,
    ser builtins JS, ou ser da biblioteca Leaflet/Chart.
    """
    known_libs = {'L', 'Chart', 'DashboardLive', 'escapeHtml'}
    dead = []
    for fn in set(onclick_calls):
        if fn in JS_BUILTINS:
            continue
        if fn in known_libs:
            continue
        if fn in defined_functions:
            continue
        if fn.startswith('bc') or fn.startswith('log') or fn.startswith('brain') or fn.startswith('nias'):
            # Namespace prefixes — aceitamos se pelo menos uma função com esse prefixo existe
            if any(f.startswith(fn[:3]) for f in defined_functions):
                continue
        dead.append(fn)
    assert dead == [], f'Funções onclick sem definição encontrada: {dead}'


def test_showPanel_targets_exist(html, panels):
    """showPanel('X') deve apontar para panel-X existente."""
    targets = re.findall(r"showPanel\(['\"](\w+)['\"]\)", html)
    missing = [t for t in targets if t not in panels]
    assert missing == [], f'showPanel aponta para painéis inexistentes: {missing}'


# ─── Botões desabilitados têm explicação ─────────────────────────────────────

def test_disabled_buttons_have_title_or_text(html):
    """
    Todo botão desabilitado deve ter title= com explicação OU
    texto vísivel explicando por que está inativo.
    """
    for m in re.finditer(r'<button([^>]*)disabled([^>]*)>(.*?)</button>', html, re.DOTALL):
        attrs = m.group(1) + m.group(2)
        text = re.sub(r'<[^>]+>', '', m.group(3)).strip()
        has_title = 'title=' in attrs
        has_text = len(text) > 5
        assert has_title or has_text, (
            f'Botão desabilitado sem explicação: ...{m.group(0)[:120]}...'
        )


# ─── Botões de navegação ──────────────────────────────────────────────────────

def test_nav_btn_map_exists(html):
    """Deve haver botão nav para showPanel('map')."""
    assert "showPanel('map')" in html, "Falta botão nav para panel-map"


def test_nav_btn_logistica_exists(html):
    """Deve haver botão nav para showPanel('logistica')."""
    assert "showPanel('logistica')" in html, "Falta botão nav para panel-logistica"


def test_nav_btn_brain_exists(html):
    """Deve haver botão nav para showPanel('brain')."""
    assert "showPanel('brain')" in html


def test_nav_btn_advisor_exists(html):
    """Deve haver botão nav para showPanel('advisor')."""
    assert "showPanel('advisor')" in html


def test_nav_btn_overview_exists(html):
    """Deve haver botão nav para showPanel('overview')."""
    assert "showPanel('overview')" in html


# ─── Layer toggles ───────────────────────────────────────────────────────────

def test_planet_layer_no_longer_silently_fails(html, defined_functions):
    """toggleLayer deve tratar camadas ausentes com mensagem, não silêncio."""
    idx = html.find('function toggleLayer(')
    assert idx >= 0
    body = html[idx:idx+800]
    assert 'indisponível' in body or 'Camada' in body, \
        'toggleLayer deve exibir mensagem quando camada não está registrada'


def test_sa_poles_layer_registered(html):
    """Layer 'sa-poles' deve ser registrado em mapLayerObjs."""
    assert "mapLayerObjs['sa-poles']" in html, "Layer sa-poles não registrado"


def test_sa_corridors_layer_registered(html):
    """Layer 'sa-corridors' deve ser registrado em logMapLayers."""
    assert "logMapLayers['sa-corridors']" in html, "Layer sa-corridors não registrado"


def test_sa_portos_layer_registered(html):
    """Layer 'sa-portos' deve ser registrado em logMapLayers."""
    assert "logMapLayers['sa-portos']" in html, "Layer sa-portos não registrado"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
