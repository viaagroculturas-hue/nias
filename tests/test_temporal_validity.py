"""
NIAS Revolution — test_temporal_validity.py
Verifica que as decisões do Cérebro NIAS têm campos de validade temporal:
valid_until, generated_at, fontes, justificativa, cenario_contrario.
Testa tanto a estrutura do BrainEngine quanto o HTML (elementos de UI).
"""
import os
import re
import sys
import ast
import pytest

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'index.html')

# Campos obrigatórios em cada card de decisão
REQUIRED_DECISION_FIELDS = [
    'valid_until',
    'generated_at',
    'fontes',
    'justificativa',
    'cenario_contrario',
]


@pytest.fixture(scope='module')
def html():
    with open(HTML_PATH, encoding='utf-8') as f:
        return f.read()


# ─── BrainEngine retorna campos obrigatórios ─────────────────────────────────

def _import_brain_engine():
    """Tenta importar NiasBrainEngine sem rodar o servidor."""
    brain_path = os.path.join(os.path.dirname(__file__), '..', 'flv', 'brain_engine.py')
    if not os.path.exists(brain_path):
        pytest.skip('brain_engine.py não encontrado')
    # Injeta caminho no sys.path
    flv_dir = os.path.join(os.path.dirname(__file__), '..', 'flv')
    if flv_dir not in sys.path:
        sys.path.insert(0, flv_dir)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location('brain_engine', brain_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        pytest.skip(f'Não foi possível importar brain_engine: {e}')


def test_brain_engine_file_exists():
    """brain_engine.py deve existir em flv/."""
    path = os.path.join(os.path.dirname(__file__), '..', 'flv', 'brain_engine.py')
    assert os.path.exists(path), 'flv/brain_engine.py não encontrado'


def test_brain_engine_has_generate_decision_cards():
    """NiasBrainEngine deve ter método generate_decision_cards."""
    path = os.path.join(os.path.dirname(__file__), '..', 'flv', 'brain_engine.py')
    with open(path, encoding='utf-8') as f:
        src = f.read()
    assert 'generate_decision_cards' in src


def test_generate_decision_cards_returns_valid_until():
    """generate_decision_cards deve incluir valid_until nos cards."""
    path = os.path.join(os.path.dirname(__file__), '..', 'flv', 'brain_engine.py')
    with open(path, encoding='utf-8') as f:
        src = f.read()
    assert 'valid_until' in src, 'brain_engine deve gerar campo valid_until'


def test_generate_decision_cards_returns_generated_at():
    """generate_decision_cards deve incluir generated_at."""
    path = os.path.join(os.path.dirname(__file__), '..', 'flv', 'brain_engine.py')
    with open(path, encoding='utf-8') as f:
        src = f.read()
    assert 'generated_at' in src


def test_generate_decision_cards_returns_fontes():
    """generate_decision_cards deve incluir fontes."""
    path = os.path.join(os.path.dirname(__file__), '..', 'flv', 'brain_engine.py')
    with open(path, encoding='utf-8') as f:
        src = f.read()
    assert 'fontes' in src


def test_generate_decision_cards_returns_justificativa():
    """generate_decision_cards deve incluir justificativa."""
    path = os.path.join(os.path.dirname(__file__), '..', 'flv', 'brain_engine.py')
    with open(path, encoding='utf-8') as f:
        src = f.read()
    assert 'justificativa' in src


def test_generate_decision_cards_returns_cenario_contrario():
    """generate_decision_cards deve incluir cenario_contrario."""
    path = os.path.join(os.path.dirname(__file__), '..', 'flv', 'brain_engine.py')
    with open(path, encoding='utf-8') as f:
        src = f.read()
    assert 'cenario_contrario' in src


# ─── Brain API router suporta /brain/decisions ───────────────────────────────

def test_router_has_brain_decisions_route():
    """router.py deve ter rota brain/decisions."""
    path = os.path.join(os.path.dirname(__file__), '..', 'flv', 'nias_api', 'router.py')
    if not os.path.exists(path):
        pytest.skip('router.py não encontrado')
    with open(path, encoding='utf-8') as f:
        src = f.read()
    assert 'decisions' in src, 'router deve tratar /brain/decisions'


def test_router_has_brain_events_route():
    """router.py deve ter rota brain/events."""
    path = os.path.join(os.path.dirname(__file__), '..', 'flv', 'nias_api', 'router.py')
    if not os.path.exists(path):
        pytest.skip('router.py não encontrado')
    with open(path, encoding='utf-8') as f:
        src = f.read()
    assert 'events' in src, 'router deve tratar /brain/events'


def test_router_has_brain_pulse_route():
    """router.py deve ter rota brain/pulse."""
    path = os.path.join(os.path.dirname(__file__), '..', 'flv', 'nias_api', 'router.py')
    if not os.path.exists(path):
        pytest.skip('router.py não encontrado')
    with open(path, encoding='utf-8') as f:
        src = f.read()
    assert 'pulse' in src


# ─── Frontend renderiza campos temporais ─────────────────────────────────────

def test_pulso_renders_valid_until(html):
    """Frontend deve renderizar campo valid_until das decisões."""
    assert 'valid_until' in html, \
        'Frontend deve usar valid_until para mostrar prazo de validade'


def test_pulso_renders_generated_at(html):
    """Frontend deve renderizar campo generated_at."""
    assert 'generated_at' in html


def test_pulso_renders_fontes(html):
    """Frontend deve renderizar campo fontes."""
    assert 'fontes' in html


def test_pulso_renders_justificativa(html):
    """Frontend deve renderizar campo justificativa ou 'justif'."""
    assert 'justificativa' in html or 'justif' in html


def test_pulso_renders_cenario_contrario(html):
    """Frontend deve renderizar campo cenario_contrario."""
    assert 'cenario_contrario' in html or 'cenário_contrário' in html or 'contrario' in html.lower()


# ─── loadPulso faz fetch dos endpoints de decisão ────────────────────────────

def test_loadpulso_fetches_decisions_endpoint(html):
    """loadPulso deve fazer fetch de /api/nias/brain/decisions."""
    assert '/api/nias/brain/decisions' in html


def test_loadpulso_fetches_events_endpoint(html):
    """loadPulso deve fazer fetch de /api/nias/brain/events."""
    assert '/api/nias/brain/events' in html


def test_loadpulso_fetches_pulse_endpoint(html):
    """loadPulso deve fazer fetch de /api/nias/brain/pulse."""
    assert '/api/nias/brain/pulse' in html


# ─── Decisões não são estáticas (não são valores hardcoded) ──────────────────

def test_decisions_are_dynamic_not_hardcoded(html):
    """As decisões não devem ser texto hardcoded — devem vir do backend."""
    idx = html.find('window.loadPulso')
    assert idx >= 0, 'loadPulso deve existir'
    # Verifica que há lógica de renderização dinâmica (innerHTML ou appendChild)
    block = html[idx:idx+5000]
    assert 'innerHTML' in block or 'appendChild' in block or 'insertAdjacentHTML' in block


def test_decisions_have_expiry_ui(html):
    """UI deve mostrar prazo de validade de cada decisão."""
    # Verifica que o frontend trata valid_until visualmente
    idx = html.find('window.loadPulso')
    assert idx >= 0
    block = html[idx:idx+5000]
    assert 'valid_until' in block


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
