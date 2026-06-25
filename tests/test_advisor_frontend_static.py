"""
Testes: verificações estáticas do frontend para o painel Conselheiro NIAS.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

INDEX = os.path.join(os.path.dirname(__file__), '..', 'index.html')


def _html():
    with open(INDEX, encoding='utf-8') as f:
        return f.read()


def test_panel_advisor_exists():
    """HTML deve conter o painel panel-advisor."""
    html = _html()
    assert 'id="panel-advisor"' in html, "Painel panel-advisor não encontrado no HTML"


def test_nav_btn_advisor_exists():
    """Sidebar deve ter botão que abre panel-advisor."""
    html = _html()
    assert "showPanel('advisor')" in html, \
        "Botão de navegação para advisor não encontrado"


def test_advisor_panel_has_summary_section():
    """Painel deve ter área de resumo executivo."""
    html = _html()
    assert 'advisor-summary' in html or 'resumo-executivo' in html or 'advisor_summary' in html, \
        "Painel advisor deve ter seção de resumo executivo"


def test_advisor_panel_has_cards_container():
    """Painel deve ter container de cards de recomendações."""
    html = _html()
    assert 'advisor-cards' in html or 'advisor-recommendations' in html or 'advisor_cards' in html, \
        "Painel advisor deve ter container de cards"


def test_advisor_panel_has_thesis_modal():
    """Painel deve ter área ou modal para tese detalhada."""
    html = _html()
    assert 'advisor-thesis' in html or 'advisor-modal' in html or 'tese-detalhe' in html, \
        "Painel advisor deve ter modal/área de tese detalhada"


def test_advisor_js_fetch_endpoint():
    """JavaScript deve chamar /api/nias/advisor."""
    html = _html()
    assert '/api/nias/advisor' in html, \
        "Frontend deve chamar endpoint /api/nias/advisor"


def test_navigation_existing_panels_preserved():
    """Painéis existentes não devem ser removidos."""
    html = _html()
    for panel_id in ['panel-overview', 'panel-situation', 'panel-chat',
                     'panel-oferta', 'panel-municipal', 'panel-biocommand']:
        assert f'id="{panel_id}"' in html, f"Painel {panel_id} foi removido indevidamente"


def test_existing_nav_buttons_preserved():
    """Botões de navegação existentes não devem ser removidos."""
    html = _html()
    for panel_name in ['overview', 'situation', 'chat', 'oferta', 'municipal', 'biocommand']:
        assert f"showPanel('{panel_name}')" in html, \
            f"Botão de navegação para '{panel_name}' foi removido"


def test_show_panel_function_exists():
    """Função showPanel deve existir no HTML."""
    html = _html()
    assert 'function showPanel(' in html or 'showPanel=function' in html, \
        "Função showPanel não encontrada"


def test_no_double_comma_syntax_errors():
    """Não deve haver padrão },, que cause erro de sintaxe JS."""
    html = _html()
    count = html.count('},,')
    assert count == 0, f"Encontrado }},, (double comma) {count} vez(es) — erro de sintaxe JS"


def test_escape_html_global_defined():
    """escapeHtml deve estar definida como função global."""
    html = _html()
    assert 'function escapeHtml(' in html, \
        "Função global escapeHtml não encontrada"


def test_advisor_has_confidence_display():
    """Frontend deve mostrar nível de confiança."""
    html = _html()
    assert 'confianca' in html or 'confiança' in html.lower(), \
        "Frontend deve exibir nível de confiança das recomendações"


def test_advisor_has_risk_display():
    """Frontend deve mostrar nível de risco."""
    html = _html()
    assert 'risco' in html.lower(), "Frontend deve exibir nível de risco"


def test_advisor_panel_in_scope():
    """Painel advisor deve referenciar América do Sul."""
    html = _html()
    assert 'América do Sul' in html or 'south_america' in html, \
        "Painel advisor deve referenciar escopo América do Sul"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
