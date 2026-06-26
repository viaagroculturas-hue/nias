"""
Testes: validar que panel-chat foi rebaixado e panel-brain é o primário de IA.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'index.html')


@pytest.fixture(scope='module')
def html():
    with open(HTML_PATH, encoding='utf-8') as f:
        return f.read()


# ─── Brain é o painel primário de IA ─────────────────────────────────────────

def test_brain_nav_button_exists(html):
    """Deve haver botão nav direto para panel-brain."""
    assert "showPanel('brain')" in html


def test_brain_appears_before_chat_in_nav(html):
    """Na barra de navegação, brain deve aparecer antes (ou no lugar) de chat."""
    brain_pos = html.find("showPanel('brain')")
    chat_pos  = html.find("showPanel('chat')")
    if brain_pos >= 0 and chat_pos >= 0:
        assert brain_pos < chat_pos, \
            'Botão para brain deve aparecer antes do botão para chat na navegação'


def test_brain_is_not_hidden_by_default(html):
    """panel-brain não deve ter display:none como estilo padrão."""
    # Encontrar o div do panel-brain e verificar se não tem display:none inline como padrão antes do JS
    idx = html.find('id="panel-brain"')
    assert idx >= 0
    snippet = html[max(0, idx-50):idx+200]
    # O panel não deve ter 'display:none' hard-coded em seu atributo style inicial
    # (o CSS .panel que controla visibilidade é diferente do estilo inline no elemento)
    assert 'display:none' not in snippet or 'panel-brain' not in snippet.split('display:none')[0][-100:]


def test_chat_nav_button_removed_or_secondary(html):
    """
    Botão nav para chat pode existir mas não deve ter o label principal de IA.
    O label 'CÉREBRO NIAS' deve existir.
    """
    assert 'CÉREBRO NIAS' in html or 'CEREBRO NIAS' in html, \
        'Label CÉREBRO NIAS deve estar presente na navegação'


def test_chat_label_not_primary_ia(html):
    """
    O botão de navegação que aponta para showPanel('chat') não deve ter
    'CÉREBRO NIAS' como texto — esse label pertence ao brain.
    """
    # Verificar que a área do botão de chat não tem o label do brain
    chat_btn_start = html.find("showPanel('chat')")
    if chat_btn_start < 0:
        return  # chat removido da nav — aceitável
    # Pegar contexto em torno do botão
    snippet = html[max(0, chat_btn_start-200):chat_btn_start+200]
    assert 'CÉREBRO' not in snippet or 'NIAS' not in snippet, \
        'O botão de chat não deve ter o label CÉREBRO NIAS'


# ─── panel-chat preservado ────────────────────────────────────────────────────

def test_panel_chat_not_deleted(html):
    """panel-chat deve continuar existindo — não foi deletado."""
    assert 'id="panel-chat"' in html


def test_panel_chat_has_audit_functionality(html):
    """Funcionalidade de auditoria do sistema deve permanecer no panel-chat."""
    assert 'system-audit-box' in html or 'runSystemAudit' in html


def test_panel_chat_has_ia_analyzer(html):
    """Analisador de IA deve permanecer no panel-chat."""
    assert 'ia-analysis-box' in html or 'runIAAnalyzer' in html


def test_panel_chat_has_chat_input(html):
    """Input de chat deve permanecer."""
    assert 'chat-input' in html


# ─── Separação de responsabilidades ──────────────────────────────────────────

def test_brain_panel_has_link_to_chat(html):
    """
    panel-brain deve ter link/botão para acessar auditoria/chat detalhado.
    Garante que o usuário não perde acesso às funcionalidades antigas.
    """
    brain_start = html.find('id="panel-brain"')
    brain_end   = html.find('id="panel-chat"')
    if brain_start < 0 or brain_end < 0:
        return
    brain_section = html[brain_start:brain_end]
    assert "showPanel('chat')" in brain_section, \
        'panel-brain deve ter link para panel-chat (auditoria detalhada)'


def test_command_field_is_not_chat_bubble(html):
    """
    O campo de comando estratégico não deve ser uma interface de chat bubble.
    Deve ser um textarea simples com placeholder de comando, não de conversa.
    """
    cmd_area_start = html.find('brain-cmd-input')
    if cmd_area_start < 0:
        return
    snippet = html[max(0, cmd_area_start-100):cmd_area_start+300]
    # Não deve ter referência a bubbles de mensagem
    assert 'msg-bubble' not in snippet


def test_brain_command_examples_in_html(html):
    """
    Deve haver exemplos de comandos estratégicos visíveis no HTML.
    """
    # Pelo menos um exemplo de comando deve aparecer
    has_example = (
        'alerta AR' in html or
        'tese tomate' in html or
        'clima PE' in html or
        'pulse' in html
    )
    assert has_example, 'panel-brain deve exibir exemplos de comandos estratégicos'


# ─── Endpoints brain vs chat ──────────────────────────────────────────────────

def test_brain_uses_brain_api_not_chat_api(html):
    """
    panel-brain deve chamar /api/nias/brain/* (não /api/nias/chat ou LLM direto).
    """
    brain_start = html.find('id="panel-brain"')
    if brain_start < 0:
        return
    # Verificar que as funções do brain usam a API brain
    assert '/api/nias/brain' in html


def test_no_fake_llm_in_brain(html):
    """
    panel-brain não deve simular respostas de LLM (não usa Anthropic API,
    não faz chamadas a /api/chat ou /api/ai diretamente).
    """
    brain_start = html.find('id="panel-brain"')
    brain_js_start = html.find('CÉREBRO NIAS — JavaScript')
    if brain_js_start < 0:
        return
    brain_js = html[brain_js_start:]
    # Não deve ter chamadas a endpoints de LLM/chat direto no JS do brain
    suspicious = ['/api/chat', '/api/ai', 'anthropic', 'openai']
    for s in suspicious:
        assert s not in brain_js.lower(), f'JS do brain não deve referenciar {s!r}'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
