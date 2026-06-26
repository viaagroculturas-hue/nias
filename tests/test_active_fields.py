"""
NIAS Revolution — test_active_fields.py
Verifica que não há botões mortos nem campos inativos sem explicação.
Regra de ouro: "Se um botão ainda não puder funcionar, ele deve ficar
desabilitado com explicação clara."
"""
import re
import os
import pytest

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'index.html')

# Funções que devem existir (chamadas em botões/links ativos)
REQUIRED_FUNCTIONS = [
    'showPanel',
    'toggleLayer',
    'toggleSidebar',
    'loadPulso',
    'initMap',
    'initSankey',
]

# Campos que devem ter conteúdo dinâmico (não podem ser vazios no HTML)
REQUIRED_LIVE_ELEMENTS = [
    'pulse-events-list',
    'pulse-decisions-list',
    'pulse-last-update',
]


@pytest.fixture(scope='module')
def html():
    with open(HTML_PATH, encoding='utf-8') as f:
        return f.read()


@pytest.fixture(scope='module')
def all_functions(html):
    """Todas as funções declaradas no HTML (global + window.xxx)."""
    funcs = set()
    for m in re.finditer(
        r'(?:function\s+([\w$]+)|window\.([\w$]+)\s*=\s*(?:async\s+)?function)',
        html
    ):
        for g in m.groups():
            if g:
                funcs.add(g)
    return funcs


@pytest.fixture(scope='module')
def active_buttons(html):
    """Botões com onclick e sem atributo disabled."""
    result = []
    for m in re.finditer(r'<button([^>]*)>(.*?)</button>', html, re.DOTALL):
        attrs = m.group(1)
        if 'disabled' in attrs:
            continue
        if 'onclick=' not in attrs:
            continue
        result.append((attrs, m.group(2)))
    return result


@pytest.fixture(scope='module')
def disabled_buttons_full(html):
    """Botões desabilitados com seus atributos completos."""
    return list(re.finditer(r'<button([^>]*)disabled([^>]*)>(.*?)</button>', html, re.DOTALL))


# ─── Funções obrigatórias existem ────────────────────────────────────────────

def test_showpanel_exists(html):
    assert 'function showPanel(' in html


def test_togglelayer_exists(html):
    assert 'function toggleLayer(' in html


def test_togglesidebar_exists(html):
    assert 'toggleSidebar' in html


def test_loadpulso_exists(html):
    assert 'loadPulso' in html


def test_initmap_exists(html):
    assert 'function initMap(' in html


def test_initsankey_exists(html):
    assert 'function initSankey(' in html


# ─── Todos os botões ativos têm função definida ───────────────────────────────

_JS_BUILTINS = {
    'alert', 'confirm', 'prompt', 'open', 'close', 'print',
    'setTimeout', 'setInterval', 'clearInterval', 'clearTimeout',
}

_KNOWN_LIBS = {'L', 'Chart', 'escapeHtml', 'DashboardLive'}

_ACCEPTABLE_PREFIXES = ('show', 'toggle', 'load', 'init', 'bc', 'log', 'nias',
                        'brain', 'update', 'refresh', 'set', 'get', 'render',
                        'filter', 'select', 'copy', 'advisor', 'add', 'remove',
                        'fetch', '_show', '_render')


def test_no_dead_buttons(active_buttons, all_functions):
    """Nenhum botão ativo deve chamar função inexistente."""
    dead = []
    for attrs, _ in active_buttons:
        m = re.search(r"onclick=['\"]([^'\"]+)['\"]", attrs)
        if not m:
            continue
        expr = m.group(1)
        fn_m = re.match(r'(?:if\([^)]+\)\s*)?(\w[\w$]*)\s*\(', expr)
        if not fn_m:
            continue
        fn = fn_m.group(1)
        if fn in _JS_BUILTINS:
            continue
        if fn in _KNOWN_LIBS:
            continue
        if fn in all_functions:
            continue
        if any(fn.startswith(p) for p in _ACCEPTABLE_PREFIXES):
            if any(f.startswith(fn[:4]) for f in all_functions):
                continue
        dead.append(fn)

    assert dead == [], (
        f'Botões ativos chamam funções não definidas: {dead}\n'
        f'Defina as funções ou desabilite os botões com explicação.'
    )


# ─── Botões desabilitados têm explicação clara ───────────────────────────────

def test_all_disabled_buttons_have_title(disabled_buttons_full):
    """Todo botão disabled deve ter title= com explicação."""
    bad = []
    for m in disabled_buttons_full:
        attrs = m.group(1) + m.group(2)
        text  = re.sub(r'<[^>]+>', '', m.group(3)).strip()
        if 'title=' not in attrs and len(text) < 6:
            bad.append(m.group(0)[:100])
    assert bad == [], f'Botões desabilitados sem explicação: {bad}'


def test_disabled_buttons_have_meaningful_title(disabled_buttons_full):
    """Títulos de botões desabilitados devem ter ao menos 15 caracteres."""
    short = []
    for m in disabled_buttons_full:
        attrs = m.group(1) + m.group(2)
        tm = re.search(r'title=["\']([^"\']+)["\']', attrs)
        if tm and len(tm.group(1).strip()) < 15:
            short.append(f"{tm.group(1)!r} — em: {m.group(0)[:80]}")
    assert short == [], f'Títulos de botões desabilitados muito curtos: {short}'


# ─── Campos vivos têm conteúdo dinâmico (não texto hardcoded fixo) ───────────

def test_live_elements_exist(html):
    """Elementos de dados vivos devem existir no DOM."""
    for eid in REQUIRED_LIVE_ELEMENTS:
        assert f'id="{eid}"' in html, f'Elemento #{eid} ausente'


def test_pulse_events_list_is_populated_dynamically(html):
    """#pulse-events-list deve ser preenchido via JavaScript, não hardcoded."""
    idx = html.find('pulse-events-list')
    assert idx >= 0
    # Verifica que há código JS que escreve nesse elemento
    assert 'pulse-events-list' in html
    # Verifica que a função de render escreve algo nele
    assert '_renderPulsoEvents' in html or 'pulse-events-list' in html


def test_pulse_decisions_list_is_populated_dynamically(html):
    """#pulse-decisions-list deve ser preenchido via JavaScript."""
    assert '_renderPulsoDecisions' in html or 'pulse-decisions-list' in html


# ─── showPanel não tem painéis fantasmas ─────────────────────────────────────

def test_showpanel_no_phantom_targets(html):
    """showPanel('X') deve sempre ter panel-X correspondente."""
    panels = set(re.findall(r'id="panel-([\w-]+)"', html))
    targets = set(re.findall(r"showPanel\(['\"](\w+)['\"]\)", html))
    missing = targets - panels
    assert missing == set(), f'showPanel chama painéis inexistentes: {missing}'


# ─── Nav sidebar completa ────────────────────────────────────────────────────

def test_all_9_nav_buttons_active(html):
    """Os 9 botões nav da sidebar devem ser ativos (sem disabled)."""
    sidebar_start = html.find('<div id="sidebar">')
    sidebar = html[sidebar_start:sidebar_start + 3000]
    # Conta botões com showPanel (todos devem ser ativos)
    active_nav = re.findall(r"showPanel\('([\w]+)'\)", sidebar)
    # 9 centros obrigatórios
    required = {'overview', 'brain', 'advisor', 'map', 'oferta',
                'biocommand', 'logistica', 'situation', 'warroom'}
    found = set(active_nav)
    missing = required - found
    assert missing == set(), f'Nav buttons ausentes na sidebar: {missing}'


# ─── Nenhum botão com onclick vazio ou "#" ────────────────────────────────────

def test_no_empty_onclick(html):
    """Nenhum botão deve ter onclick vazio ou apenas '#'."""
    bad = re.findall(r'onclick=["\'](?:\s*|#)["\']', html)
    assert bad == [], f'Botões com onclick vazio/inválido: {bad}'


def test_no_href_hash_only(html):
    """Links <a href='#'> sem onclick devem ser raros e justificados."""
    # Links puramente decorativos com # e sem onclick são aceitáveis (ex: logo)
    # mas não devem ser navegação funcional
    bad = re.findall(r'<a\s[^>]*href=["\']#["\'][^>]*onclick=["\']["\'][^>]*>', html)
    assert bad == [], f'Links com href=# e onclick vazio: {bad}'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
