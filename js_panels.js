// ═══════════════════════════════════════════════════════════════════
// JANELA IA (CHAT) - VERSAO LIMPA
// ═══════════════════════════════════════════════════════════════════

function initChatIA() {
  if (window._chatInit) return;
  window._chatInit = true;
  
  const msgs = document.getElementById('chat-messages');
  if (msgs) {
    msgs.scrollTop = msgs.scrollHeight;
    console.log('[Chat] Inicializado');
  }
}

function addMessage(text, sender, meta) {
  const msgs = document.getElementById('chat-messages');
  if (!msgs) return;
  
  const div = document.createElement('div');
  div.className = 'msg ' + sender;
  
  const html = text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code style="background:#222;padding:2px 4px;border-radius:3px;">$1</code>')
    .replace(/\n/g, '<br>');
  
  div.innerHTML = '<div class="msg-bubble">' + html + '</div><div class="msg-meta">' + meta + '</div>';
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function getResponse(text) {
  const lower = text.toLowerCase();
  if (lower.includes('soja') || lower.includes('milho')) {
    return '**Mercado de Grãos:**\n\n• Soja: R$ 142,00/sc (+3.2%)\n• Milho: R$ 72,00/sc (-1.5%)\n• Café: R$ 1.180,00/sc (+8.7%)\n\n_Tendência de alta para soja devido à demanda de exportação._';
  }
  if (lower.includes('preço') || lower.includes('cotação')) {
    return '**Cotações Atuais:**\n\n🌾 Soja: R$ 142,00/sc\n🌽 Milho: R$ 72,00/sc\n☕ Café: R$ 1.180,00/sc\n🍅 Tomate: R$ 88,50/cx';
  }
  if (lower.includes('clima') || lower.includes('tempo')) {
    return '**Condições Climáticas:**\n\n• MATOPIBA: 36.2°C 🌡️\n• Umidade solo: 34%\n• NDVI médio: 0.61\n\n_Alerta: Chuvas irregulares no Centro-Oeste._';
  }
  if (lower.includes('rj') || lower.includes('recuperação') || lower.includes('falência')) {
    return '**Alertas de Crise:**\n\n⚠️ 3 empresas em Recuperação Judicial\n⚠️ 1 falência decretada\n\nTotal em risco: R$ 23,35 bilhões\nEmpregos afetados: 56.481';
  }
  return 'Olá! Sou o NIA$, assistente de inteligência do agronegócio.\n\nPosso ajudar com:\n• Cotações de commodities\n• Análise de mercado\n• Alertas de crise\n• Dados climáticos\n\n_O que deseja saber?_';}

function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;
  
  input.value = '';
  const now = new Date().toLocaleTimeString('pt-BR');
  addMessage(text, 'user', 'Você · ' + now);
  
  const msgs = document.getElementById('chat-messages');
  const typing = document.createElement('div');
  typing.className = 'msg nias';
  typing.innerHTML = '<div class="msg-bubble"><div class="typing"><span></span><span></span><span></span></div></div>';
  msgs.appendChild(typing);
  msgs.scrollTop = msgs.scrollHeight;
  
  setTimeout(() => {
    typing.remove();
    addMessage(getResponse(text), 'nias', 'NIA$ · ' + new Date().toLocaleTimeString('pt-BR'));
  }, 800 + Math.random() * 500);
}

function quickMsg(text) {
  document.getElementById('chat-input').value = text;
  sendMessage();
  showPanel('chat');
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

// ═══════════════════════════════════════════════════════════════════
// JANELA SITUATION ROOM - VERSAO LIMPA
// ═══════════════════════════════════════════════════════════════════

const SituationRoom = {
  data: {
    totals: { in_rj: 3, bankrupt: 1, total_companies: 4, total_debt_billions: 23.35, employees_at_risk: 56481 },
    recent_entries: [
      { company_name: 'Agroindustrial Paulista S.A.', cnpj: '12.345.678/0001-90', city: 'São Paulo', state_uf: 'SP', segment: 'Comercialização de Grãos', judicial_status: 'em_recuperacao', debts_total: 150000000 },
      { company_name: 'Café Premium Minas S.A.', cnpj: '34.567.890/0001-12', city: 'Belo Horizonte', state_uf: 'MG', segment: 'Exportação de Café', judicial_status: 'em_recuperacao', debts_total: 89000000 },
      { company_name: 'Grão Goiano Comercial Ltda', cnpj: '45.678.901/0001-23', city: 'Goiânia', state_uf: 'GO', segment: 'Trading de Grãos', judicial_status: 'em_recuperacao', debts_total: 125000000 },
      { company_name: 'Fertilizantes do Interior Ltda', cnpj: '23.456.789/0001-01', city: 'Campinas', state_uf: 'SP', segment: 'Distribuição de Insumos', judicial_status: 'falencia', debts_total: 45000000 }
    ]
  },
  
  init() {
    console.log('[SituationRoom] Inicializando...');
    this.renderCompanies();
    this.renderAlertBadge();
    this.updateTime();
    this.renderNews();
    setInterval(() => this.updateTime(), 60000);
  },
  
  updateTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    const el = document.getElementById('sit-update-time');
    if (el) el.textContent = timeStr;
  },
  
  renderAlertBadge() {
    const badge = document.getElementById('sit-alert-badge');
    if (badge && this.data.totals) {
      const alerts = (this.data.totals.in_rj || 0) + (this.data.totals.bankrupt || 0);
      badge.textContent = '● ALERTAS: ' + alerts;
    }
  },
  
  renderCompanies() {
    const listEl = document.getElementById('sit-company-list');
    if (!listEl) {
      console.error('[SituationRoom] Elemento sit-company-list nao encontrado!');
      return;
    }
    
    if (this.data.recent_entries && this.data.recent_entries.length > 0) {
      listEl.innerHTML = this.data.recent_entries.map(company => {
        const isFalencia = company.judicial_status === 'falencia';
        return '<div class="sit-company-item" style="background:#1a1a1a;border:1px solid #2a2a2a;border-radius:3px;padding:8px;cursor:pointer;margin-bottom:4px;" onclick="SituationRoom.selectCompany(\'' + company.cnpj + '\')">' +
          '<div style="font-size:10px;color:#fff;font-weight:bold;">' + company.company_name + '</div>' +
          '<div style="font-size:8px;color:#888;">' + company.city + '/' + company.state_uf + ' • ' + company.segment + '</div>' +
          '<div style="font-size:8px;color:' + (isFalencia ? '#ff3d3d' : '#ff6b35') + ';margin-top:2px;">' +
            (isFalencia ? '⚠️ FALÊNCIA' : '⚖️ EM RJ') + ' • R$ ' + (company.debts_total/1000000).toFixed(1) + 'M' +
          '</div>' +
        '</div>';
      }).join('');
      console.log('[SituationRoom] ' + this.data.recent_entries.length + ' empresas renderizadas');
    } else {
      listEl.innerHTML = '<div style="font-size:10px;color:#666;text-align:center;padding:20px;">Nenhuma empresa em monitoramento</div>';
    }
  },
  
  selectCompany(cnpj) {
    const company = this.data.recent_entries.find(c => c.cnpj === cnpj);
    if (!company) return;
    
    this.selectedCompany = cnpj;
    const isFalencia = company.judicial_status === 'falencia';
    
    // Score de credito
    const scoreEl = document.getElementById('sit-credit-score');
    const classEl = document.getElementById('sit-credit-classification');
    if (scoreEl) {
      const score = isFalencia ? 250 : 450;
      scoreEl.textContent = score;
      scoreEl.style.color = score > 700 ? '#50C878' : score > 500 ? '#FFD700' : score > 300 ? '#ff6b35' : '#ff3d3d';
    }
    if (classEl) {
      classEl.textContent = isFalencia ? 'Risco Crítico - Evitar' : 'Risco Alto - Cautela';
    }
    
    // Status judicial
    const statusEl = document.getElementById('sit-judicial-status');
    const detailsEl = document.getElementById('sit-process-details');
    if (statusEl) {
      statusEl.textContent = isFalencia ? 'FALÊNCIA' : 'EM RECUPERAÇÃO JUDICIAL';
      statusEl.style.color = isFalencia ? '#ff3d3d' : '#ff6b35';
    }
    if (detailsEl) {
      detailsEl.textContent = 'Dívida: R$ ' + (company.debts_total/1000000).toFixed(1) + ' milhões';
    }
    
    // Timeline
    const timelineEl = document.getElementById('sit-admin-timeline');
    if (timelineEl) {
      timelineEl.innerHTML = 
        '<div style="display:flex;gap:8px;align-items:flex-start;margin-bottom:8px;">' +
          '<div style="width:8px;height:8px;background:#ff6b35;border-radius:50%;margin-top:3px;flex-shrink:0;"></div>' +
          '<div>' +
            '<div style="font-size:9px;color:#fff;">Entrada em ' + (isFalencia ? 'Falência' : 'Recuperação Judicial') + '</div>' +
            '<div style="font-size:8px;color:#666;">Processo iniciado em 2024</div>' +
          '</div>' +
        '</div>' +
        '<div style="display:flex;gap:8px;align-items:flex-start;">' +
          '<div style="width:8px;height:8px;background:#555;border-radius:50%;margin-top:3px;flex-shrink:0;"></div>' +
          '<div>' +
            '<div style="font-size:9px;color:#888;">Última atualização</div>' +
            '<div style="font-size:8px;color:#666;">' + new Date().toLocaleDateString('pt-BR') + '</div>' +
          '</div>' +
        '</div>';
    }
  },
  
  renderNews() {
    const feedEl = document.getElementById('sit-news-feed');
    if (!feedEl) return;
    
    feedEl.innerHTML = 
      '<div style="background:#111;border:1px solid #2a2a2a;border-radius:3px;padding:8px;margin-bottom:6px;">' +
        '<div style="font-size:9px;color:#ff6b35;">REUTERS</div>' +
        '<div style="font-size:10px;color:#fff;margin-top:2px;">Soja sobe 3% com demanda de exportação da China</div>' +
        '<div style="font-size:8px;color:#666;margin-top:2px;">Agora</div>' +
      '</div>' +
      '<div style="background:#111;border:1px solid #2a2a2a;border-radius:3px;padding:8px;margin-bottom:6px;">' +
        '<div style="font-size:9px;color:#ff6b35;">BLOOMBERG</div>' +
        '<div style="font-size:10px;color:#fff;margin-top:2px;">Clima irregular afeta safra de milho no Centro-Oeste</div>' +
        '<div style="font-size:8px;color:#666;margin-top:2px;">30 min atrás</div>' +
      '</div>' +
      '<div style="background:#111;border:1px solid #2a2a2a;border-radius:3px;padding:8px;">' +
        '<div style="font-size:9px;color:#ff6b35;">BBC</div>' +
        '<div style="font-size:10px;color:#fff;margin-top:2px;">Preço do café atinge máxima de 2 anos em Nova York</div>' +
        '<div style="font-size:8px;color:#666;margin-top:2px;">1h atrás</div>' +
      '</div>';
  },
  
  filterCompanies(type) {
    ['rj', 'growth', 'all'].forEach(t => {
      const btn = document.getElementById('sit-filter-' + t);
      if (btn) {
        if (t === type) {
          btn.style.background = '#ff6b35';
          btn.style.color = '#000';
        } else {
          btn.style.background = '#1a1a1a';
          btn.style.color = '#888';
        }
      }
    });
  },
  
  showProductTab(tab) {
    const graos = document.getElementById('sit-graos-content');
    const horti = document.getElementById('sit-hortifruti-content');
    const tabGraos = document.getElementById('sit-tab-graos');
    const tabHorti = document.getElementById('sit-tab-hortifruti');
    
    if (tab === 'graos') {
      if (graos) graos.style.display = 'block';
      if (horti) horti.style.display = 'none';
      if (tabGraos) { tabGraos.style.background = '#ff6b35'; tabGraos.style.color = '#000'; }
      if (tabHorti) { tabHorti.style.background = '#1a1a1a'; tabHorti.style.color = '#888'; }
    } else {
      if (graos) graos.style.display = 'none';
      if (horti) horti.style.display = 'block';
      if (tabGraos) { tabGraos.style.background = '#1a1a1a'; tabGraos.style.color = '#888'; }
      if (tabHorti) { tabHorti.style.background = '#ff6b35'; tabHorti.style.color = '#000'; }
    }
  },
  
  filterNews(source) {
    ['all', 'reuters', 'bloomberg', 'bbc'].forEach(s => {
      const btn = document.getElementById('sit-news-' + s);
      if (btn) {
        if (s === source) {
          btn.style.background = '#ff6b35';
          btn.style.color = '#000';
        } else {
          btn.style.background = '#1a1a1a';
          btn.style.color = '#888';
        }
      }
    });
  }
};

console.log('[NIA$] Módulos Chat e SituationRoom carregados');
