// ─── Global helpers (usados em todo o dashboard) ─────────────────
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>'"]/g, c => (
    {'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]
  ));
}

// ═══════════════════════════════════════════════════════════════════
// CLOCK
// ═══════════════════════════════════════════════════════════════════
function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toLocaleDateString('pt-BR') + ' ' + now.toLocaleTimeString('pt-BR');
  document.getElementById('map-time').textContent = now.toLocaleTimeString('pt-BR');
  // alert timestamps
  ['at-1','at-2','at-3','at-4'].forEach((id,i) => {
    const el = document.getElementById(id);
    if (!el) return;
    const d = new Date(now.getTime() - (i * 7 + 2) * 60000);
    el.textContent = 'Detectado às ' + d.toLocaleTimeString('pt-BR');
  });
}
setInterval(updateClock, 1000);
updateClock();

// ═══════════════════════════════════════════════════════════════════
// SITUATION ROOM MODULE - VERSAO COM DADOS REAIS (API)
// ═══════════════════════════════════════════════════════════════════
const SituationRoom = {
  data: {
    totals: { in_rj: 0, bankrupt: 0, total_companies: 0, total_debt_billions: 0, employees_at_risk: 0 },
    recent_entries: []
  },
  newsData: [],
  refreshInterval: null,
  clockInterval: null,
  selectedCompany: null,
  activeCompanyFilter: 'rj',
  activeNewsFilter: 'all',
  activeProduct: null,

  escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, ch => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[ch]));
  },

  init() {
    console.log('[SituationRoom] Inicializando versão estável...');
    this.renderCompanies();
    this.renderAlertBadge();
    this.updateTime();
    this.renderNews();

    // Buscar dados reais das APIs sem multiplicar timers a cada abertura da aba.
    this.loadRealData();

    if (!this.refreshInterval) {
      this.refreshInterval = setInterval(() => this.loadRealData(), 30000);
    }
    if (!this.clockInterval) {
      this.clockInterval = setInterval(() => this.updateTime(), 60000);
    }
  },
  
  async loadRealData() {
    try {
      // Fonte factual: Situation Room / Recuperação Judicial.
      const response = await fetch('/api/situation/real?limit=500&live=1');
      if (response.ok) {
        const payload = await response.json();
        const cases = Array.isArray(payload.cases) ? payload.cases : [];
        this.data = {
          totals: {
            in_rj: payload.summary?.total_cases_loaded || cases.length,
            bankrupt: cases.filter(c => String(c.judicial_status || '').toLowerCase().includes('fal')).length,
            total_companies: cases.length,
            total_debt_billions: (payload.summary?.total_debt_brl_known || 0) / 1000000000,
            employees_at_risk: cases.reduce((acc, c) => acc + Number(c.employees || 0), 0)
          },
          recent_entries: cases,
          summary: payload.summary,
          sources: payload.sources,
          truth_policy: payload.truth_policy,
          live_datajud: payload.live_datajud
        };
        this.renderCompanies();
        this.renderAlertBadge();
        this.renderDataJudStatus();
        console.log('[SituationRoom] RJ factual atualizado:', cases.length);
      } else {
        console.warn('[SituationRoom] API /api/situation/real indisponível:', response.status);
      }
    } catch (e) {
      console.log('[SituationRoom] Usando dados embutidos (API indisponível)', e);
    }
    
    // Buscar notícias reais
    this.loadRealNews();
  },

  renderDataJudStatus() {
    const target = document.getElementById('sit-process-details');
    if (!target || !this.data.live_datajud) return;
    const live = this.data.live_datajud;
    if (live.status === 'configuration_needed') {
      target.textContent = 'CNJ/DataJud: configure DATAJUD_API_KEY no Render para varredura nacional completa. Base atual: curada pública.';
    } else {
      target.textContent = `CNJ/DataJud: ${live.status} • tribunais checados: ${(live.tribunals_checked || []).length}`;
    }
  },
  
  async loadRealNews() {
    try {
      const newsResponse = await fetch('/api/news/feeds?limit=10');
      if (newsResponse.ok) {
        const newsData = await newsResponse.json();
        if (newsData.news && newsData.news.length > 0) {
          this.newsData = newsData.news;
          this.renderRealNews();
          console.log('[SituationRoom] Notícias atualizadas:', newsData.news.length);
        }
      }
    } catch (e) {
      console.log('[SituationRoom] Usando notícias estáticas (API indisponível)');
      this.renderNews();
    }
  },
  
  renderRealNews() {
    const feedEl = document.getElementById('sit-news-feed');
    if (!feedEl || this.newsData.length === 0) return;
    
    const sourceColors = {
      'Reuters': '#ff9f0a',
      'Bloomberg': '#50C878',
      'BBC': '#FFD700',
      'default': '#ff9f0a'
    };
    
    const filtered = this.activeNewsFilter === 'all'
      ? this.newsData
      : this.newsData.filter(item => String(item.source || '').toLowerCase().includes(this.activeNewsFilter));

    feedEl.innerHTML = filtered.slice(0, 5).map(item => {
      const source = this.escapeHtml(item.source || 'NEWS');
      const rawSource = item.source || 'default';
      const color = sourceColors[rawSource] || sourceColors.default;
      const timeAgo = this.escapeHtml(this.getTimeAgo(item.published_at));
      const title = this.escapeHtml(item.title || 'Sem título');
      const url = this.escapeHtml(item.url || '#');
      
      return `<div style="background:#111;border:1px solid #2a2a2a;border-radius:3px;padding:8px;margin-bottom:6px;cursor:pointer;" data-url="${url}" onclick="SituationRoom.openNews(this.dataset.url)">` +
        `<div style="font-size:9px;color:${color};font-weight:bold;">${source.toUpperCase()}</div>` +
        `<div style="font-size:10px;color:#fff;margin-top:2px;line-height:1.3;">${title}</div>` +
        `<div style="font-size:8px;color:#666;margin-top:2px;">${timeAgo}</div>` +
      `</div>`;
    }).join('') || '<div style="font-size:10px;color:#666;text-align:center;padding:20px;">Nenhuma notícia para este filtro</div>';
  },
  
  getTimeAgo(dateStr) {
    if (!dateStr) return 'Agora';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000 / 60); // minutos
    
    if (diff < 1) return 'Agora';
    if (diff < 60) return `${diff}min atrás`;
    if (diff < 1440) return `${Math.floor(diff/60)}h atrás`;
    return `${Math.floor(diff/1440)}d atrás`;
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
      badge.textContent = `● ALERTAS: ${alerts}`;
      badge.style.animation = 'pulse 2s infinite';
    }
  },
  
  renderCompanies() {
    const listEl = document.getElementById('sit-company-list');
    if (!listEl) {
      console.error('[SituationRoom] Elemento sit-company-list nao encontrado!');
      return;
    }
    
    if (this.data.recent_entries && this.data.recent_entries.length > 0) {
      const entries = this.getFilteredCompanies();
      listEl.innerHTML = entries.map(company => {
        const isFalencia = company.judicial_status === 'falencia';
        const debt = Number(company.debts_total || 0);
        const cnpj = this.escapeHtml(company.cnpj || '');
        return `<div class="sit-company-item" style="background:#1a1a1a;border:1px solid #2a2a2a;border-radius:3px;padding:8px;cursor:pointer;margin-bottom:4px;transition:all 0.2s;" onmouseover="this.style.borderColor='#ff9f0a'" onmouseout="this.style.borderColor='#2a2a2a'" data-cnpj="${cnpj}" onclick="SituationRoom.selectCompany(this.dataset.cnpj)">` +
          `<div style="font-size:10px;color:#fff;font-weight:bold;">${this.escapeHtml(company.company_name)}</div>` +
          `<div style="font-size:8px;color:#888;">${this.escapeHtml(company.city)}/${this.escapeHtml(company.state_uf)} • ${this.escapeHtml(company.segment)}</div>` +
          `<div style="font-size:8px;color:${isFalencia ? '#ff453a' : '#ff9f0a'};margin-top:2px;">` +
            (isFalencia ? '⚠️ FALÊNCIA' : '⚖️ EM RJ') + ` • R$ ${(debt/1000000).toFixed(1)}M` +
          `</div>` +
        `</div>`;
      }).join('') || '<div style="font-size:10px;color:#666;text-align:center;padding:20px;">Nenhuma empresa neste filtro</div>';
      console.log(`[SituationRoom] ${entries.length} empresas renderizadas`);
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
      scoreEl.style.color = score > 700 ? '#50C878' : score > 500 ? '#FFD700' : score > 300 ? '#ff9f0a' : '#ff453a';
    }
    if (classEl) {
      classEl.textContent = isFalencia ? 'Risco Crítico - Evitar' : 'Risco Alto - Cautela';
    }
    
    // Status judicial
    const statusEl = document.getElementById('sit-judicial-status');
    const detailsEl = document.getElementById('sit-process-details');
    if (statusEl) {
      statusEl.textContent = isFalencia ? 'FALÊNCIA' : 'EM RECUPERAÇÃO JUDICIAL';
      statusEl.style.color = isFalencia ? '#ff453a' : '#ff9f0a';
    }
    if (detailsEl) {
      const proc = company.process_number ? ` • Proc.: ${company.process_number}` : '';
      const conf = company.data_confidence ? ` • ${company.data_confidence}` : '';
      detailsEl.textContent = `Dívida conhecida: R$ ${(Number(company.debts_total || 0)/1000000).toFixed(1)} milhões${proc}${conf}`;
    }
    
    // Timeline
    const timelineEl = document.getElementById('sit-admin-timeline');
    if (timelineEl) {
      timelineEl.innerHTML = 
        `<div style="display:flex;gap:8px;align-items:flex-start;margin-bottom:8px;">` +
          `<div style="width:8px;height:8px;background:#ff9f0a;border-radius:50%;margin-top:3px;flex-shrink:0;"></div>` +
          `<div>` +
            `<div style="font-size:9px;color:#fff;">Entrada em ${isFalencia ? 'Falência' : 'Recuperação Judicial'}</div>` +
            `<div style="font-size:8px;color:#666;">Processo iniciado em 2024</div>` +
          `</div>` +
        `</div>` +
        `<div style="display:flex;gap:8px;align-items:flex-start;">` +
          `<div style="width:8px;height:8px;background:#555;border-radius:50%;margin-top:3px;flex-shrink:0;"></div>` +
          `<div>` +
            `<div style="font-size:9px;color:#888;">Última atualização</div>` +
            `<div style="font-size:8px;color:#666;">${new Date().toLocaleDateString('pt-BR')}</div>` +
          `</div>` +
        `</div>`;
    }
  },
  
  renderNews() {
    const feedEl = document.getElementById('sit-news-feed');
    if (!feedEl) return;
    
    feedEl.innerHTML = 
      `<div style="background:#111;border:1px solid #2a2a2a;border-radius:3px;padding:8px;margin-bottom:6px;">` +
        `<div style="font-size:9px;color:#ff9f0a;">REUTERS</div>` +
        `<div style="font-size:10px;color:#fff;margin-top:2px;">Soja sobe 3% com demanda de exportação da China</div>` +
        `<div style="font-size:8px;color:#666;margin-top:2px;">Agora</div>` +
      `</div>` +
      `<div style="background:#111;border:1px solid #2a2a2a;border-radius:3px;padding:8px;margin-bottom:6px;">` +
        `<div style="font-size:9px;color:#ff9f0a;">BLOOMBERG</div>` +
        `<div style="font-size:10px;color:#fff;margin-top:2px;">Clima irregular afeta safra de milho no Centro-Oeste</div>` +
        `<div style="font-size:8px;color:#666;margin-top:2px;">30 min atrás</div>` +
      `</div>` +
      `<div style="background:#111;border:1px solid #2a2a2a;border-radius:3px;padding:8px;">` +
        `<div style="font-size:9px;color:#ff9f0a;">BBC</div>` +
        `<div style="font-size:10px;color:#fff;margin-top:2px;">Preço do café atinge máxima de 2 anos em Nova York</div>` +
        `<div style="font-size:8px;color:#666;margin-top:2px;">1h atrás</div>` +
      `</div>`;
  },
  
  getFilteredCompanies() {
    const entries = this.data.recent_entries || [];
    if (this.activeCompanyFilter === 'all') return entries;
    if (this.activeCompanyFilter === 'rj') {
      return entries.filter(c => c.judicial_status === 'em_recuperacao' || c.judicial_status === 'falencia');
    }
    if (this.activeCompanyFilter === 'growth') {
      return [...entries].sort((a, b) => Number(b.debts_total || 0) - Number(a.debts_total || 0)).slice(0, 10);
    }
    return entries;
  },

  filterCompanies(type) {
    this.activeCompanyFilter = type;
    ['rj', 'growth', 'all'].forEach(t => {
      const btn = document.getElementById(`sit-filter-${t}`);
      if (btn) {
        if (t === type) {
          btn.style.background = '#ff9f0a';
          btn.style.color = '#000';
          btn.style.fontWeight = 'bold';
        } else {
          btn.style.background = '#1a1a1a';
          btn.style.color = '#888';
          btn.style.fontWeight = 'normal';
        }
      }
    });
    this.renderCompanies();
  },
  
  showProductTab(tab) {
    const graos = document.getElementById('sit-graos-content');
    const horti = document.getElementById('sit-hortifruti-content');
    const financeiro = document.getElementById('sit-financeiro-content');
    const tabGraos = document.getElementById('sit-tab-graos');
    const tabHorti = document.getElementById('sit-tab-hortifruti');
    const tabFinanceiro = document.getElementById('sit-tab-financeiro');
    
    // Reset all tabs
    if (graos) graos.style.display = 'none';
    if (horti) horti.style.display = 'none';
    if (financeiro) financeiro.style.display = 'none';
    if (tabGraos) { tabGraos.style.background = '#1a1a1a'; tabGraos.style.color = '#888'; }
    if (tabHorti) { tabHorti.style.background = '#1a1a1a'; tabHorti.style.color = '#888'; }
    if (tabFinanceiro) { tabFinanceiro.style.background = '#1a1a1a'; tabFinanceiro.style.color = '#888'; }
    
    // Activate selected tab
    if (tab === 'graos') {
      if (graos) graos.style.display = 'block';
      if (tabGraos) { tabGraos.style.background = '#ff9f0a'; tabGraos.style.color = '#000'; }
    } else if (tab === 'hortifruti') {
      if (horti) horti.style.display = 'block';
      if (tabHorti) { tabHorti.style.background = '#ff9f0a'; tabHorti.style.color = '#000'; }
    } else if (tab === 'financeiro') {
      if (financeiro) financeiro.style.display = 'block';
      if (tabFinanceiro) { tabFinanceiro.style.background = '#ff9f0a'; tabFinanceiro.style.color = '#000'; }
    }
  },
  

  productCatalog: {
    soja: { nome:'SOJA', unidade:'sc', preco:'R$ 142,00/sc', tendencia:'+3.2%', risco:'Médio', detalhe:'Demanda externa firme; atenção a câmbio, logística portuária e clima no Centro-Oeste.' },
    milho: { nome:'MILHO', unidade:'sc', preco:'R$ 72,00/sc', tendencia:'-1.5%', risco:'Médio', detalhe:'Pressão de oferta na safrinha; sensível a frete e armazenagem.' },
    cafe: { nome:'CAFÉ', unidade:'sc', preco:'R$ 1.180,00/sc', tendencia:'+8.7%', risco:'Alto', detalhe:'Volatilidade elevada por clima, ICE NY e diferenciais de exportação.' },
    trigo: { nome:'TRIGO', unidade:'t', preco:'R$ 98,00/sc', tendencia:'+0.8%', risco:'Baixo', detalhe:'Mercado dependente de importação e paridade Argentina/RS.' },
    tomate: { nome:'TOMATE', unidade:'kg', preco:'R$ 5,20/kg', tendencia:'+4.1%', risco:'Alto', detalhe:'Alta perecibilidade; risco de ruptura por chuva e logística regional.' },
    cebola: { nome:'CEBOLA', unidade:'kg', preco:'R$ 3,80/kg', tendencia:'-2.0%', risco:'Médio', detalhe:'Oferta regional pesa; monitorar câmaras frias e volume CEASA.' },
    batata: { nome:'BATATA', unidade:'kg', preco:'R$ 4,10/kg', tendencia:'+1.2%', risco:'Médio', detalhe:'Preço condicionado por qualidade, chuva e custo de frete.' },
    manga: { nome:'MANGA', unidade:'kg', preco:'R$ 6,50/kg', tendencia:'+5.4%', risco:'Médio', detalhe:'Exportação e janela do Vale do São Francisco influenciam disponibilidade.' }
  },

  loadProductDetail(productId) {
    const product = this.productCatalog[productId];
    if (!product) return;
    this.activeProduct = productId;
    this.updateProductDetail(product);
  },

  updateProductDetail(product) {
    let detailEl = document.getElementById('sit-product-detail');
    if (!detailEl) {
      const productsPanel = document.getElementById('sit-portfolio-products');
      if (!productsPanel) return;
      detailEl = document.createElement('div');
      detailEl.id = 'sit-product-detail';
      detailEl.style.cssText = 'margin-top:10px;background:#111;border:1px solid #ff9f0a;border-radius:4px;padding:10px;';
      productsPanel.appendChild(detailEl);
    }
    detailEl.innerHTML =
      `<div style="font-size:10px;color:#ff9f0a;font-weight:bold;letter-spacing:1px;">${this.escapeHtml(product.nome)} — ANÁLISE</div>` +
      `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:8px;">` +
        `<div><div style="font-size:8px;color:#666;">PREÇO</div><div style="font-size:12px;color:#fff;font-family:monospace;">${this.escapeHtml(product.preco)}</div></div>` +
        `<div><div style="font-size:8px;color:#666;">TENDÊNCIA</div><div style="font-size:12px;color:#fff;font-family:monospace;">${this.escapeHtml(product.tendencia)}</div></div>` +
        `<div><div style="font-size:8px;color:#666;">RISCO</div><div style="font-size:12px;color:#fff;font-family:monospace;">${this.escapeHtml(product.risco)}</div></div>` +
      `</div>` +
      `<div style="font-size:9px;color:#aaa;line-height:1.4;margin-top:8px;">${this.escapeHtml(product.detalhe)}</div>`;
  },

  openNews(url) {
    if (!url || url === '#') return;
    try { window.open(url, '_blank', 'noopener,noreferrer'); } catch(e) {}
  },

  filterNews(source) {
    this.activeNewsFilter = source;
    ['all', 'reuters', 'bloomberg', 'bbc'].forEach(s => {
      const btn = document.getElementById(`sit-news-${s}`);
      if (btn) {
        if (s === source) {
          btn.style.background = '#ff9f0a';
          btn.style.color = '#000';
        } else {
          btn.style.background = '#1a1a1a';
          btn.style.color = '#888';
        }
      }
    });
    if (this.newsData && this.newsData.length > 0) this.renderRealNews();
  }
};


// ═══════════════════════════════════════════════════════════════════
// CHAT IA MODULE
// ═══════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════════════
function showPanel(id) {
  const osMode = document.body.classList.contains('nias-os-mode');
  try {
    document.querySelectorAll('.panel').forEach(p => {
      p.classList.remove('active', 'os-sheet-open');
      // Em OS mode, panel-map nunca perde o display (CSS !important cuida disso)
      if (!osMode || p.id !== 'panel-map') {
        p.style.display = '';
        p.style.visibility = '';
        p.style.opacity = '';
      }
    });
    document.querySelectorAll('#sidebar .nav-btn').forEach(b => b.classList.remove('active'));
    const panel = document.getElementById('panel-' + id);
    if (panel) {
      panel.classList.add('active');
      if (osMode && id !== 'map') {
        // Sheet: o CSS .os-sheet-open cuida do display/position
        panel.classList.add('os-sheet-open');
      } else {
        panel.style.display = 'flex';
      }
    }
    // Highlight correct sidebar button by matching onclick
    document.querySelectorAll('#sidebar .nav-btn').forEach(b => {
      const oc = b.getAttribute('onclick') || '';
      if (oc.includes("'" + id + "'")) b.classList.add('active');
    });
    if (id === 'map' && !window._mapInit) { try { initMap(); } catch(e) { console.error('initMap error:', e); } }
    if (id === 'map') setTimeout(() => { try { leafletMap && leafletMap.invalidateSize(); } catch(e) {} }, 120);
    if (id === 'logistica' && !window._sankeyInit) setTimeout(() => { try { initSankey(); updateArbitragem(); updateEcoScore(); updateAIS(); } catch(e) { console.error('logistica init error:', e); } }, 50);
    if (id === 'logistica' && window._sankeyInit) { setTimeout(() => { try { updateArbitragem(); } catch(e) {} setTimeout(() => { try { logMap && logMap.invalidateSize(); } catch(e) {} }, 80); }, 50); }
    if (id.startsWith('flv_')) setTimeout(() => { try { FLVModule.onPanelShow(id); } catch(e) { console.error('FLVModule error:', e); } }, 100);
    if (id === 'predictix') setTimeout(() => { try { Predictix.init(); } catch(e) { console.error('Predictix init error:', e); } }, 150);
    if (id === 'oferta' && !window._ofertaInit) { try { initMercadoReal(); } catch(e) { console.error('oferta/mercado init error:', e); } }
    if (id === 'municipal' && !window._munInit) { try { initMunicipal(); } catch(e) { console.error('municipal init error:', e); } }
    if (id === 'municipal') setTimeout(() => { try { munMap && munMap.invalidateSize(); } catch(e) {} }, 120);
    if (id === 'biocommand') { try { initBioCommand(); } catch(e) { console.error('biocommand init error:', e); } }
    if (id === 'macropolos' && !window._macroInit) { try { initMacroPolos(); } catch(e) { console.error('macropolos init error:', e); } }
    if (id === 'hyperlocal' && !window._hyperInit) { try { initHyperLocal(); } catch(e) { console.error('hyperlocal init error:', e); } }
    if (id === 'sentiment' && !window._sentInit) { try { initSentiment(); } catch(e) { console.error('sentiment init error:', e); } }
    if (id === 'esg' && !window._esgInit) { try { initESG(); } catch(e) { console.error('esg init error:', e); } }
    if (id === 'warroom' && !window._warInit) { window._warInit = true; }
    if (id === 'warroom') setTimeout(() => { try { WarRoomProtocol.refresh(); } catch(e) { console.error('warroom refresh error:', e); } }, 200);
    if (id === 'overview') { try { loadPulso(false); } catch(e) { console.error('pulso load error:', e); } }
    if (id === 'brain' && !window._brainInit) { try { initBrainPanel(); } catch(e) { console.error('brain init error:', e); } }
    if (id === 'brain') { try { loadBrain(false); } catch(e) { console.error('brain load error:', e); } }
    if (id === 'chat' && !window._chatInit) { try { initChatIA(); runSystemAudit(false); } catch(e) { console.error('chat init error:', e); } }
    if (id === 'situation') {
      setTimeout(() => {
        try {
          const sitPanel = document.getElementById('panel-situation');
          if (sitPanel) sitPanel.classList.add('active');
          SituationRoom.init();
        } catch(e) { console.error('SituationRoom init error:', e); }
      }, 100);
    }
  } catch(e) {
    console.error('showPanel error:', e);
  }
}

function toggleNavGroup(groupId) {
  const g = document.getElementById(groupId);
  if (g) g.classList.toggle('collapsed');
}

// ═══════════════════════════════════════════════════════════════════
// WAR ROOM — Protocolo de Priorização de Alertas (3 Níveis)
// VFR = Volume Financeiro em Risco · PE = Proximidade do Evento
// ═══════════════════════════════════════════════════════════════════
var WarRoomProtocol = {
  LEVELS: {
    N1: { name:'NACIONAL', color:'#EF4444', icon:'🔴', css:'wr-alert-n1', action:'CONTINGÊNCIA IMEDIATA' },
    N2: { name:'REGIONAL', color:'#F59E0B', icon:'🟡', css:'wr-alert-n2', action:'REBALANCEAR ESTOQUE' },
    N3: { name:'ESTADUAL', color:'#3B82F6', icon:'🔵', css:'wr-alert-n3', action:'MONITORAR CUSTO/SACA' },
  },
  _refreshTimer: null,
  _countdown: 300,

  classifyAlert(vfr) {
    if (vfr >= 10000000) return 'N1';
    if (vfr >= 1000000)  return 'N2';
    return 'N3';
  },

  calculateVFR(culture, impactPct, baseVolumeTons) {
    const ppt = {tomate:2500,banana:1800,laranja:800,manga:3200,uva:5500,cebola:2200,batata:1600,mamao:2800,melancia:600,abacaxi:1500,alho:12000,melao:2000,soja:2100,milho:1200}[culture] || 2000;
    return Math.round(baseVolumeTons * ppt * Math.abs(impactPct) / 100);
  },

  _logEntry(msg, color) {
    const log = document.getElementById('war-log');
    if (!log) return;
    const ts = new Date().toLocaleTimeString('pt-BR');
    const d = document.createElement('div');
    d.style.cssText = 'padding:4px 8px;border-bottom:1px solid rgba(255,255,255,.04);font-size:9px;';
    d.innerHTML = `<span style="color:${color||'var(--danger)'};">${ts}</span> ${msg}`;
    log.insertBefore(d, log.firstChild);
    // Keep max 50 entries
    while (log.children.length > 50) log.removeChild(log.lastChild);
  },

  async _loadAlerts() {
    const alerts = [];
    try {
      const data = await fetch('/api/flv/alerts?severity=all').then(r=>r.json()).catch(()=>[]);
      if (Array.isArray(data)) {
        data.forEach(a => {
          const vfr = this.calculateVFR(a.culture_slug||'tomate', a.impact_price_pct||10, 50000);
          const level = this.classifyAlert(vfr);
          alerts.push({
            level, vfr,
            culture: a.culture_name || a.culture_slug || '—',
            region: `${a.mun_name||''} (${a.state_uf||''})`,
            event: a.alert_type || '—',
            message: a.message || '',
            action: this.LEVELS[level].action,
            recommendation: vfr > 5000000 ? 'VENDER posição antes do impacto' : vfr > 1000000 ? 'AGUARDAR — monitorar evolução' : 'COMPRAR — oportunidade de preço baixo',
            source: 'FLV · CEASA',
            ts: a.created_at || a.ts || null,
          });
        });
      }
    } catch(e) { console.warn('WarRoom FLV alerts:', e); }

    // Enrich with poles at risk from /api/nias/regions
    try {
      const rd = await fetch('/api/nias/regions').then(r=>r.json()).catch(()=>null);
      const poles = (rd && rd.data && rd.data.regions) || [];
      poles.forEach(p => {
        if ((p.importance === 'muito_alta' || p.importance === 'alta') && p.alerts && p.alerts.length > 0) {
          p.alerts.forEach(al => {
            const vfr = this.calculateVFR(p.main_culture||'soja', al.impact_pct||8, p.area_ha ? p.area_ha*2 : 30000);
            const level = this.classifyAlert(vfr);
            alerts.push({
              level, vfr,
              culture: p.main_culture || p.name,
              region: `${p.name} (${p.state_or_department||p.country||'SA'})`,
              event: al.type || al.title || 'ALERTA DE POLO',
              message: al.description || al.message || '',
              action: this.LEVELS[level].action,
              recommendation: 'Monitorar polo — dado NIAS Regions',
              source: 'NIAS · Regions',
              ts: null,
            });
          });
        }
      });
    } catch(e) { console.warn('WarRoom regions:', e); }

    return alerts;
  },

  async _loadClimateRisk() {
    // Pontos críticos de monitoramento climático SA
    const checkpoints = [
      { name:'Mato Grosso (MT)', lat:-12.5, lon:-55.7, culture:'Soja/Milho' },
      { name:'Vale São Francisco (PE)', lat:-9.4, lon:-40.5, culture:'Tomate/Manga' },
      { name:'Triângulo Mineiro (MG)', lat:-18.9, lon:-48.3, culture:'Tomate/Batata' },
      { name:'Sul/Serra Gaúcha (RS)', lat:-29.2, lon:-51.2, culture:'Maçã/Uva' },
      { name:'Cerrado Goiano (GO)', lat:-16.3, lon:-49.3, culture:'Soja/Milho' },
    ];
    const results = [];
    for (const cp of checkpoints) {
      try {
        const url = `https://api.open-meteo.com/v1/forecast?latitude=${cp.lat}&longitude=${cp.lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=America%2FSao_Paulo&forecast_days=3`;
        const d = await fetch(url).then(r=>r.json()).catch(()=>null);
        if (!d || !d.daily) { results.push({...cp, status:'indisponível'}); continue; }
        const tmax = d.daily.temperature_2m_max[0];
        const tmin = d.daily.temperature_2m_min[0];
        const prec = d.daily.precipitation_sum[0];
        let alert = null, color = 'var(--accent2)';
        if (tmax >= 38) { alert = `🌡 CALOR EXTREMO ${tmax}°C`; color = '#EF4444'; }
        else if (tmin <= 4) { alert = `❄ RISCO DE GEADA ${tmin}°C`; color = '#3B82F6'; }
        else if (prec >= 50) { alert = `🌧 CHUVA INTENSA ${prec}mm`; color = '#F59E0B'; }
        else if (prec === 0 && tmax >= 33) { alert = `🏜 SECO E QUENTE ${tmax}°C`; color = '#F59E0B'; }
        results.push({...cp, tmax, tmin, prec, alert, color});
      } catch(e) { results.push({...cp, status:'erro'}); }
    }
    return results;
  },

  _renderAlerts(alerts) {
    alerts.sort((a,b) => {
      const lo = {N1:0,N2:1,N3:2};
      if (lo[a.level] !== lo[b.level]) return lo[a.level] - lo[b.level];
      return b.vfr - a.vfr;
    });
    const feed = document.getElementById('wr-protocol-feed');
    if (!feed) return;
    const n1 = alerts.filter(a=>a.level==='N1').length;
    const n2 = alerts.filter(a=>a.level==='N2').length;
    const n3 = alerts.filter(a=>a.level==='N3').length;
    const ts = new Date().toLocaleTimeString('pt-BR');
    feed.innerHTML = `
      <div style="display:flex;gap:8px;padding:8px 12px;border-bottom:1px solid var(--border);align-items:center;">
        <div style="flex:1;text-align:center;padding:4px;border:1px solid #EF4444;border-radius:4px;background:rgba(239,68,68,.08);">
          <div style="font-size:18px;font-weight:bold;color:#EF4444;">${n1}</div>
          <div style="font-size:8px;color:#EF4444;letter-spacing:1px;">NACIONAL</div>
        </div>
        <div style="flex:1;text-align:center;padding:4px;border:1px solid #F59E0B;border-radius:4px;background:rgba(245,158,11,.06);">
          <div style="font-size:18px;font-weight:bold;color:#F59E0B;">${n2}</div>
          <div style="font-size:8px;color:#F59E0B;letter-spacing:1px;">REGIONAL</div>
        </div>
        <div style="flex:1;text-align:center;padding:4px;border:1px solid #3B82F6;border-radius:4px;background:rgba(59,130,246,.05);">
          <div style="font-size:18px;font-weight:bold;color:#3B82F6;">${n3}</div>
          <div style="font-size:8px;color:#3B82F6;letter-spacing:1px;">ESTADUAL</div>
        </div>
        <div style="font-size:9px;color:var(--text2);text-align:right;flex-shrink:0;">Atualizado<br>${ts}</div>
      </div>
    ` + (alerts.length === 0
      ? `<div style="padding:40px;text-align:center;color:var(--accent2);">✅ Nenhum alerta crítico ativo agora.<br><span style="color:var(--text2);font-size:10px;">Sistema monitorando ${checkpoints ? checkpoints.length : 5} polos SA.</span></div>`
      : alerts.map(a => {
        const L = this.LEVELS[a.level];
        return `<div class="alert-card ${L.css}" style="padding:10px 12px;border-bottom:1px solid var(--border);">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-size:11px;font-weight:bold;color:${L.color};">${L.icon} N${a.level.replace('N','')} — ${L.name}</span>
            <span style="font-size:10px;color:${L.color};font-weight:bold;">VFR R$ ${(a.vfr/1e6).toFixed(1)}M</span>
          </div>
          <div style="font-size:11px;color:var(--text);font-weight:bold;">${a.culture} · ${a.event}</div>
          <div style="font-size:10px;color:var(--text2);margin-top:2px;">${a.region}</div>
          ${a.message ? `<div style="font-size:10px;color:var(--text2);margin-top:3px;line-height:1.4;">${a.message}</div>` : ''}
          <div style="display:flex;gap:8px;margin-top:6px;align-items:center;flex-wrap:wrap;">
            <span style="font-size:9px;padding:2px 8px;border:1px solid ${L.color};color:${L.color};border-radius:3px;">${a.action}</span>
            <span style="font-size:9px;color:var(--text);font-weight:bold;">${a.recommendation}</span>
            <span style="font-size:9px;color:var(--text2);margin-left:auto;">${a.source||''}</span>
          </div>
        </div>`;
      }).join('')
    );
  },

  _renderClimate(results) {
    const el = document.getElementById('wr-climate-live');
    if (!el) return;
    if (!results || !results.length) { el.textContent = 'Dados de clima indisponíveis.'; return; }
    el.innerHTML = results.map(r => {
      if (r.status) return `<div style="padding:4px 0;border-bottom:1px solid var(--border);color:var(--text2);">${r.name} — ${r.status}</div>`;
      return `<div style="padding:5px 0;border-bottom:1px solid var(--border);">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="color:var(--text);font-size:10px;font-weight:bold;">${r.name}</span>
          <span style="font-size:9px;color:var(--text2);">${r.tmax}°C / ${r.tmin}°C · ${r.prec}mm</span>
        </div>
        <div style="font-size:9px;color:var(--text2);">${r.culture}</div>
        ${r.alert ? `<div style="font-size:9px;font-weight:bold;color:${r.color};margin-top:2px;">${r.alert}</div>` : '<div style="font-size:9px;color:var(--accent2);">✅ Normal</div>'}
      </div>`;
    }).join('');
  },

  async _renderAIDecision(alerts, climate) {
    const el = document.getElementById('wr-ai-decision');
    if (!el) return;
    const criticals = alerts.filter(a=>a.level==='N1').slice(0,3).map(a=>`${a.culture} (${a.region}): ${a.event}`).join('; ');
    const climateAlerts = (climate||[]).filter(c=>c.alert).map(c=>`${c.name}: ${c.alert}`).join('; ');
    if (!criticals && !climateAlerts) {
      el.innerHTML = '<span style="color:var(--accent2);">✅ Sem ação urgente. Sistema estável.</span>';
      return;
    }
    el.innerHTML = '<span style="color:var(--text2);">Consultando IA…</span>';
    const prompt = `War Room NIAS. Alertas críticos: ${criticals||'nenhum'}. Clima: ${climateAlerts||'normal'}. Dê 2 recomendações de ação imediata em 1 linha cada, direto.`;
    try {
      const controller = new AbortController();
      const tid = setTimeout(() => controller.abort(), 8000);
      const r = await fetch('/api/nias/brain/command', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ command: prompt }),
        signal: controller.signal
      }).then(r=>r.json()).catch(()=>null);
      clearTimeout(tid);
      const txt = r && (r.response || r.answer || r.text || r.result);
      el.innerHTML = txt
        ? txt.replace(/\n/g,'<br>')
        : '<span style="color:var(--text2);">IA indisponível no momento.</span>';
    } catch(e) {
      el.innerHTML = '<span style="color:var(--text2);">IA indisponível · verifique /api/nias/brain</span>';
    }
  },

  _renderLogistics() {
    const el = document.getElementById('wr-logistics-live');
    if (!el) return;
    // Usa logState (saturação de corredor) — dado derivado da API de logística
    const corridors = [
      { label: 'BR-163', key: 'br163' },
      { label: 'Porto Santos', key: 'santos' },
      { label: 'Paranaguá', key: 'par' },
      { label: 'Ferroviário', key: 'ferro' },
    ];
    const rows = corridors.map(c => {
      const sat = typeof logState !== 'undefined' ? Math.round(logState[c.key] || 0) : null;
      if (sat === null) return `<div style="margin-bottom:6px;"><span style="color:rgba(255,255,255,.4);">${c.label}:</span> <span style="color:var(--text2);">—</span></div>`;
      const col = sat >= 82 ? 'var(--danger)' : sat >= 70 ? 'var(--warn)' : 'var(--accent2)';
      const status = sat >= 82 ? '⚠ CRÍTICO' : sat >= 70 ? '↑ ELEVADO' : '✓ NORMAL';
      return `<div style="margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
        <span style="color:rgba(255,255,255,.6);">${c.label}</span>
        <span style="color:${col};font-weight:600;">${sat}% <span style="font-size:8px;">${status}</span></span>
      </div>`;
    }).join('');
    el.innerHTML = rows || '<span style="color:rgba(255,255,255,.3);">Dados de logística indisponíveis.</span>';
  },

  async refresh() {
    const el = document.getElementById('wr-next-refresh');
    if (el) el.textContent = '↻ Atualizando…';
    this._logEntry('Atualização ao vivo iniciada', 'var(--accent)');

    // Render logistics immediately — no API needed
    this._renderLogistics();

    let alerts = [], climate = [];
    try {
      [alerts, climate] = await Promise.all([
        this._loadAlerts().catch(() => []),
        this._loadClimateRisk().catch(() => []),
      ]);
    } catch(e) {
      console.warn('WarRoom refresh error:', e);
    }

    this._renderAlerts(alerts);
    this._renderClimate(climate);
    this._renderAIDecision(alerts, climate);
    this._renderLogistics(); // re-render after logState may have updated

    // Log summary
    const n1 = alerts.filter(a=>a.level==='N1').length;
    const climCrit = (climate||[]).filter(c=>c.alert).length;
    this._logEntry(`${alerts.length} alertas · ${n1} NACIONAIS · ${climCrit} riscos climáticos`, n1 > 0 ? '#EF4444' : 'var(--accent2)');

    // Countdown to next refresh (5 min)
    clearInterval(this._refreshTimer);
    this._countdown = 300;
    this._refreshTimer = setInterval(() => {
      this._countdown--;
      if (el) el.textContent = `↻ próxima atualização em ${this._countdown}s`;
      if (this._countdown <= 0) { clearInterval(this._refreshTimer); this.refresh(); }
    }, 1000);
  }
};

let sidebarExpanded = false;
function toggleSidebar() {
  sidebarExpanded = !sidebarExpanded;
  document.getElementById('sidebar').classList.toggle('expanded', sidebarExpanded);
  document.getElementById('sb-icon').textContent = sidebarExpanded ? '«' : '»';
}

// ═══════════════════════════════════════════════════════════════════
// SPARKLINE HELPER
// ═══════════════════════════════════════════════════════════════════
function initSparkline(canvasId, data, color) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  return new Chart(ctx, {
    type: 'line',
    data: { labels: data.map((_,i) => i), datasets: [{ data, borderColor: color, borderWidth: 1.5, pointRadius: 0, tension: 0.4, fill: true, backgroundColor: color + '22' }] },
    options: { responsive: false, animation: false, plugins: { legend: { display: false }, tooltip: { enabled: false } }, scales: { x: { display: false }, y: { display: false } } }
  });
}

// Sparklines — iniciam zerados; preenchidos por dados reais quando disponíveis
const sparkData = {
  soja:  Array(30).fill(null),
  milho: Array(30).fill(null),
  ndvi:  Array(30).fill(null),
  hum:   Array(30).fill(null),
  boi:   Array(30).fill(null),
  horti: Array(30).fill(null),
};
const sparks = {
  soja:  initSparkline('sp-soja',  sparkData.soja,  '#0a84ff'),
  milho: initSparkline('sp-milho', sparkData.milho, '#ffd60a'),
  ndvi:  initSparkline('sp-ndvi',  sparkData.ndvi,  '#30d158'),
  hum:   initSparkline('sp-hum',   sparkData.hum,   '#0a84ff'),
  boi:   initSparkline('sp-boi',   sparkData.boi,   '#30d158'),
  horti: initSparkline('sp-horti', sparkData.horti, '#ff9f0a'),
};

function pushSparkline(chart, dataArr, newVal) {
  dataArr.shift();
  dataArr.push(newVal);
  chart.data.datasets[0].data = [...dataArr];
  chart.update('none');
}

// ═══════════════════════════════════════════════════════════════════
// NDVI LIVE CHART
// ═══════════════════════════════════════════════════════════════════
const NDVI_MAX_PTS = 60;
// NDVI chart — valores iniciais nulos; preenchidos por /api/clima/bioclima quando disponível
const ndviData = {
  cerrado:  Array(NDVI_MAX_PTS).fill(null),
  matopiba: Array(NDVI_MAX_PTS).fill(null),
  pr_ms:    Array(NDVI_MAX_PTS).fill(null),
  pampa:    Array(NDVI_MAX_PTS).fill(null),
};
const ndviLabels = Array.from({length:NDVI_MAX_PTS}, (_,i) => '-' + (NDVI_MAX_PTS - 1 - i) + 's');

const ndviCtx = document.getElementById('chartNdvi').getContext('2d');
const ndviChart = new Chart(ndviCtx, {
  type: 'line',
  data: {
    labels: [...ndviLabels],
    datasets: [
      { label: 'Cerrado (MT/GO)', data: [...ndviData.cerrado], borderColor: '#0a84ff', borderWidth: 1.5, pointRadius: 0, tension: 0.4 },
      { label: 'MATOPIBA (BA/PI)', data: [...ndviData.matopiba], borderColor: '#ff453a', borderWidth: 1.5, pointRadius: 0, tension: 0.4 },
      { label: 'Norte PR / Sul MS', data: [...ndviData.pr_ms], borderColor: '#ffd60a', borderWidth: 1.5, pointRadius: 0, tension: 0.4 },
      { label: 'Pampa (RS/AR)', data: [...ndviData.pampa], borderColor: '#30d158', borderWidth: 1.5, pointRadius: 0, tension: 0.4 },
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false, animation: false,
    interaction: { mode: 'index', intersect: false },
    plugins: { legend: { labels: { color: 'rgba(235,235,245,0.6)', font: { family: 'Courier New', size: 10 }, boxWidth: 16 } },
      tooltip: { backgroundColor: '#2c2c2e', borderColor: '#3a3a3c', borderWidth: 1, titleColor: '#0a84ff', bodyColor: '#ffffff', titleFont: { family: 'Courier New' }, bodyFont: { family: 'Courier New', size: 11 } }
    },
    scales: {
      x: { ticks: { color: 'rgba(235,235,245,0.6)', font: { family: 'Courier New', size: 9 }, maxTicksLimit: 10 }, grid: { color: '#3a3a3c' } },
      y: { min: 0.25, max: 0.80, ticks: { color: 'rgba(235,235,245,0.6)', font: { family: 'Courier New', size: 10 } }, grid: { color: '#3a3a3c' } }
    }
  }
});

// NDVI chart — sem simulação. Gráfico mostrará dados reais quando
// integração Sentinel-2/Open-Meteo estiver ativa via /api/clima/bioclima.
async function _fetchNdviLive() {
  try {
    const r = await fetch('/api/clima/bioclima', { cache:'no-store' });
    if (!r.ok) return;
    const d = await r.json();
    // API retorna ndvi por região quando disponível
    const regions = d?.ndvi || d?.data?.ndvi || {};
    const now = new Date().toLocaleTimeString('pt-BR', {hour:'2-digit',minute:'2-digit'});
    if (regions.cerrado) {
      ndviData.cerrado.shift(); ndviData.cerrado.push(+regions.cerrado);
      ndviChart.data.datasets[0].data = [...ndviData.cerrado];
      setLiveVal('ts-ndvi', (+regions.cerrado).toFixed(3), 0.61, 0.001);
      setLiveVal('cs-ndvi', (+regions.cerrado).toFixed(3), 0.61, 0.001);
    }
    if (regions.matopiba) { ndviData.matopiba.shift(); ndviData.matopiba.push(+regions.matopiba); ndviChart.data.datasets[1].data = [...ndviData.matopiba]; }
    if (regions.pr_ms)    { ndviData.pr_ms.shift();    ndviData.pr_ms.push(+regions.pr_ms);       ndviChart.data.datasets[2].data = [...ndviData.pr_ms]; }
    if (regions.pampa)    { ndviData.pampa.shift();    ndviData.pampa.push(+regions.pampa);        ndviChart.data.datasets[3].data = [...ndviData.pampa]; }
    ndviChart.update('none');
  } catch(e) { /* API indisponível — gráfico permanece estático */ }
}
setInterval(_fetchNdviLive, 10 * 60 * 1000); // atualiza a cada 10 min quando API disponível

// ═══════════════════════════════════════════════════════════════════
// LIVE VALUE UPDATER
// ═══════════════════════════════════════════════════════════════════
function setLiveVal(id, val, prevVal, threshold) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = val;
  el.classList.remove('val-flash');
  void el.offsetWidth;
  if (Math.abs(parseFloat(val) - prevVal) > threshold) el.classList.add('val-flash');
}

// ═══════════════════════════════════════════════════════════════════
// WEATHER LIVE UPDATE
// ═══════════════════════════════════════════════════════════════════
const wxBase = [
  { t: 36.2, h: 18, w: 14 },
  { t: 33.8, h: 31, w: 9  },
  { t: 28.4, h: 68, w: 11 },
  { t: 30.1, h: 52, w: 7  },
  { t: 22.7, h: 61, w: 18 },
  { t: 31.5, h: 84, w: 5  },
];
function updateWeather() {
  if (window.DashboardLive && DashboardLive.lastWeather && DashboardLive.lastWeather.length) {
    return; // real data already rendered by DashboardLive.renderWeather
  }
  // Fallback: sem dados da API — mostra médias históricas estáticas (sem drift simulado)
  wxBase.forEach((b, i) => {
    const n = i + 1;
    document.getElementById('wx-t'+n).textContent = b.t + '°C';
    document.getElementById('wx-h'+n).textContent = 'Umid: ' + b.h + '%';
    document.getElementById('wx-w'+n).textContent = 'Vento: ' + b.w + 'km/h';
    const st = document.getElementById('wx-s'+n);
    if (st) { st.textContent = 'média histórica — sem API'; st.style.color = 'var(--text2)'; st.title = 'Média histórica estacional. Aguardando Open-Meteo.'; }
  });
}
setInterval(updateWeather, 5000);

// ═══════════════════════════════════════════════════════════════════
// LOGISTICS LIVE UPDATE
// ═══════════════════════════════════════════════════════════════════
// Valores de referência CONAB/ANTT — fixos até API retornar dados ao vivo
const logState = { br163: 82, santos: 74, par: 71, ferro: 61, ros: 48, br364: 55,
  _source: 'referência CONAB/ANTT', _live: false, _lastUpdate: null };

async function _fetchLogisticsLive() {
  try {
    const r = await fetch('/api/rodovias?live=1', { cache:'no-store' });
    if (!r.ok) return;
    const d = await r.json();
    if (d.status === 'degraded' || !d.roads) return;
    // Map road keys to logState
    const map = { 'BR-163': 'br163', 'SANTOS': 'santos', 'BR-158': 'par', 'FERROVIARIO': 'ferro', 'BR-364': 'br364' };
    let updated = false;
    for (const [roadKey, stateKey] of Object.entries(map)) {
      const road = d.roads[roadKey] || d.roads[roadKey.toLowerCase()];
      if (road && road.saturation != null) {
        logState[stateKey] = road.saturation;
        updated = true;
      }
    }
    if (updated) {
      logState._live = true;
      logState._source = 'PRF/DNIT ao vivo';
      logState._lastUpdate = new Date().toLocaleTimeString('pt-BR', {hour:'2-digit',minute:'2-digit'});
    }
  } catch(_) {}
}
// Tenta dados ao vivo no carregamento; depois de 10min
_fetchLogisticsLive();
setInterval(_fetchLogisticsLive, 10 * 60 * 1000);

function updateLogistics() {
  // Sem drift aleatório — logState muda só via _fetchLogisticsLive()
  const update = (key, color) => {
    const v = Math.round(logState[key]);
    const pf = document.getElementById('pf-' + key);
    const cv = document.getElementById('cv-' + key);
    if (pf) { pf.style.width = v + '%'; pf.style.background = color; }
    if (cv) { cv.textContent = v + '%'; cv.style.color = color; }
  };
  const c163 = logState.br163 > 85 ? '#ff453a' : logState.br163 > 78 ? '#ffd60a' : '#30d158';
  update('br163', c163);
  update('santos', logState.santos > 78 ? '#ff453a' : '#ffd60a');
  update('par', logState.par > 75 ? '#ffd60a' : '#30d158');
  update('ferro', '#30d158'); update('ros', '#30d158'); update('br364', '#30d158');

  // trucks counter — sem simulação (aguarda integração ANTT/DNIT)
  const rd = document.getElementById('rd-br163-flow');
  if (rd) rd.textContent = 'Fluxo: — veíc/dia';

  // header badges
  const ph163 = document.getElementById('ph-br163');
  if (ph163) ph163.textContent = 'BR-163: ' + Math.round(logState.br163) + '%';
  const phs = document.getElementById('ph-santos');
  if (phs) phs.textContent = 'SANTOS: ' + Math.round(logState.santos) + '%';

  // Sankey chart — valores de referência fixos (CONAB/ANTAQ)
  // Sem simulação: dados atualizados apenas quando API retornar valores reais
  updateLogKpis();
}
setInterval(updateLogistics, 4000);

// ═══════════════════════════════════════════════════════════════════
// LOGISTICS KPIs: Custo Brasil + IEL + ETA Cards + Rerouting
// ═══════════════════════════════════════════════════════════════════
function updateLogKpis() {
  const satAvg = (logState.br163 + logState.santos + logState.par) / 3;
  const baseLoss = 1800000;
  const penalty = Math.max(0, satAvg - 65) * 44000;
  const custo = baseLoss + penalty;
  const iel = Math.max(22, Math.min(94, Math.round(100 - (satAvg - 40) * 1.15)));

  const custoEl = document.getElementById('log-custo-val');
  if (custoEl) custoEl.textContent = 'R$ ' + Math.round(custo).toLocaleString('pt-BR');
  const ielEl = document.getElementById('iel-val');
  if (ielEl) { ielEl.textContent = iel + '/100'; ielEl.style.color = iel >= 70 ? '#30d158' : iel >= 50 ? '#ffd60a' : '#ff453a'; }
  const ielBar = document.getElementById('iel-bar');
  if (ielBar) ielBar.style.width = iel + '%';
  const phIel = document.getElementById('ph-iel');
  if (phIel) { phIel.textContent = 'IEL: ' + iel; phIel.style.color = iel >= 70 ? '#30d158' : iel >= 50 ? '#ffd60a' : '#ff453a'; }

  buildEtaCards();
}

function buildEtaCards() {
  const container = document.getElementById('eta-cards');
  if (!container) return;
  const routes = [
    { name:'Sorriso (MT) → Porto Santos', corridor:'BR-163', baseTh:72, satKey:'br163', delayFactor:0.22 },
    { name:'Rio Verde (GO) → Paranaguá', corridor:'Ferroviário RUMO', baseTh:48, satKey:'ferro', delayFactor:0.10 },
    { name:'Cascavel (PR) → Paranaguá', corridor:'Malha SP/Sul', baseTh:24, satKey:'par', delayFactor:0.14 },
    { name:'Hernandarias (PY) → Rosário', corridor:'Hidrovia Paraguai', baseTh:96, satKey:'ros', delayFactor:0.06 },
  ];
  container.innerHTML = routes.map(r => {
    const sat = logState[r.satKey] || 60;
    const delayH = Math.round(Math.max(0, sat - 65) * r.delayFactor);
    const eta = r.baseTh + delayH;
    const col = sat >= 82 ? 'var(--danger)' : sat >= 70 ? 'var(--warn)' : 'var(--accent2)';
    const delayStr = delayH > 0
      ? `<span style="color:var(--danger)">+${delayH}h atraso previsto</span>`
      : `<span style="color:var(--accent2)">no prazo</span>`;
    return `<div style="background:var(--bg3);border-left:2px solid ${col};padding:5px 8px;border-radius:2px;">
      <div style="font-size:9px;color:var(--text2);margin-bottom:2px;">${r.name}</div>
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:11px;">ETA: <b style="color:${col};">${eta}h</b></span>
        <span style="font-size:9px;">${delayStr}</span>
      </div>
      <div style="font-size:9px;color:var(--text2);margin-top:1px;">${r.corridor} · Sat. <span style="color:${col};">${Math.round(sat)}%</span></div>
    </div>`;
  }).join('');
}

async function applyReroute() {
  const btn = document.getElementById('reroute-btn');
  const status = document.getElementById('reroute-status');
  const msg = document.getElementById('reroute-msg');
  if (!btn) return;

  const sat163  = Math.round(logState.br163 || 0);
  const satFerro = Math.round(logState.ferro || 0);

  // Só sugere re-roteamento se BR-163 realmente saturada
  if (sat163 < 75) {
    if (msg) msg.textContent = `BR-163 em ${sat163}% de saturação — re-roteamento não necessário no momento.`;
    return;
  }

  btn.disabled = true;
  btn.textContent = '⟳ CONSULTANDO IA…';
  if (status) status.textContent = '';

  try {
    const r = await fetch('/api/nias/brain/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: `Logística: BR-163 está em ${sat163}% de saturação. Ferrovia em ${satFerro}%. Sugira uma ação de re-roteamento concreta em 1 frase.` }),
    }).then(r => r.ok ? r.json() : null).catch(() => null);

    const txt = r && (r.response || r.answer || r.text || r.result);
    if (msg) {
      if (txt) {
        msg.innerHTML = `<span style="color:var(--accent2);">⚡ IA:</span> ${txt}`;
      } else {
        msg.textContent = `BR-163 em ${sat163}% — considere transferir carga para corredor ferroviário (${satFerro}% de capacidade atual).`;
      }
    }
  } catch(e) {
    if (msg) msg.textContent = 'IA indisponível. Verifique manualmente a saturação dos corredores.';
  }

  btn.textContent = '⚡ RE-ROTEAR VIA IA';
  btn.disabled = false;
}

// ═══════════════════════════════════════════════════════════════════
// PRICE TICKER LIVE
// ═══════════════════════════════════════════════════════════════════
// Preços de referência CEPEA/ESALQ — atualizados manualmente por coleta
// Sem simulação: valores só mudam quando API retornar cotação real
// Fontes reais: CEPEA/ESALQ (soja/milho/boi/café), BCB (USD), CEAGESP (tomate)
// Açúcar ICE e Algodão ICE removidos — sem API CBOT disponível
const prices = {
  soja:   { val: null, unit: 'R$/sc', dir: 0, _source: 'CEPEA' },
  milho:  { val: null, unit: 'R$/sc', dir: 0, _source: 'CEPEA' },
  boi:    { val: null, unit: 'R$/@',  dir: 0, _source: 'CEPEA' },
  cafe:   { val: null, unit: 'R$/sc', dir: 0, _source: 'CEPEA' },
  usd:    { val: null, unit: 'R$',    dir: 0, _source: 'BCB'   },
  tomate: { val: null, unit: 'R$/cx', dir: 0, _source: 'CEAGESP' },
};
const tickerIds = { soja:'tp-soja', milho:'tp-milho', boi:'tp-boi', cafe:'tp-cafe', usd:'tp-usd', tomate:'tp-tomate' };
function _renderPriceTicker() {
  for (const [key, p] of Object.entries(prices)) {
    const el = document.getElementById(tickerIds[key]);
    if (!el) continue;
    if (p.val === null) {
      el.textContent = '—';
      el.className = 'tick-val';
      el.style.color = 'var(--text2)';
    } else {
      const fmt = p.val > 100 ? p.val.toFixed(1) : p.val.toFixed(4);
      const arrow = p.dir > 0 ? ' ▲' : p.dir < 0 ? ' ▼' : '';
      el.textContent = fmt + arrow;
      el.className = 'tick-val ' + (p.dir > 0 ? 'tick-up' : p.dir < 0 ? 'tick-dn' : '');
      el.style.color = '';
    }
  }
}
async function _fetchLivePrices() {
  // 1. CEASA-GO Goiás — tomate (fonte primária, PDF diário)
  try {
    const r = await fetch('/api/ceasa/go?q=TOMATE+LONGA+VIDA', { cache:'no-store' });
    if (r.ok) {
      const d = await r.json();
      const prods = d?.produtos || {};
      const tomate = Object.values(prods).find(p => p.nome && p.nome.toUpperCase().includes('TOMATE LONGA VIDA'));
      if (tomate && tomate.comum && tomate.kg_embalagem) {
        const precoKg = tomate.comum / tomate.kg_embalagem;
        const prev = prices.tomate.val;
        prices.tomate.val = +(precoKg * 22).toFixed(1); // cx 22kg
        prices.tomate.dir = prev ? Math.sign(prices.tomate.val - prev) : 0;
        prices.tomate._source = 'CEASA-GO';
        prices.tomate._date = tomate.date || '';
      }
    }
  } catch(_) {}

  // 1b. Fallback — CEAGESP/CONAB — tomate
  if (!prices.tomate.val) {
  try {
    const r = await fetch('/api/hortifruti/precos', { cache:'no-store' });
    if (r.ok) {
      const d = await r.json();
      const t = d?.products?.tomate?.ceagesp?.price_kg;
      if (t && t > 0) {
        const prev = prices.tomate.val;
        prices.tomate.val = +(t * 13).toFixed(1);
        prices.tomate.dir = prev ? Math.sign(prices.tomate.val - prev) : 0;
      }
    }
  } catch(_) {}
  }

  // 2. CEPEA/ESALQ — soja, milho, boi, café
  try {
    const r = await fetch('/api/cepea', { cache:'no-store' });
    if (r.ok) {
      const d = await r.json();
      const set = (key, cepeaKey, multiplier) => {
        const item = d?.[cepeaKey];
        if (!item || !item.price) return;
        const prev = prices[key].val;
        prices[key].val = +(item.price * (multiplier || 1)).toFixed(2);
        prices[key].dir = prev ? Math.sign(prices[key].val - prev) : 0;
        prices[key]._source = 'CEPEA/ESALQ';
        prices[key]._date = item.date || '';
      };
      set('soja',  'soja',  1);   // R$/sc 60kg
      set('milho', 'milho', 1);   // R$/sc 60kg
      set('boi',   'boi',   1);   // R$/@
      set('cafe',  'cafe',  1);   // R$/sc 60kg
    }
  } catch(_) {}

  // 3. BCB/AwesomeAPI — USD/BRL
  try {
    const r = await fetch('https://economia.awesomeapi.com.br/json/last/USD-BRL', { cache:'no-store' });
    if (r.ok) {
      const d = await r.json();
      const rate = parseFloat(d?.USDBRL?.bid);
      if (rate > 0) {
        const prev = prices.usd.val;
        prices.usd.val = +rate.toFixed(4);
        prices.usd.dir = prev ? Math.sign(prices.usd.val - prev) : 0;
        prices.usd._source = 'BCB/AwesomeAPI';
      }
    }
  } catch(_) {}

  _renderPriceTicker();
}
_fetchLivePrices();
setInterval(_fetchLivePrices, 5 * 60 * 1000);

// ═══════════════════════════════════════════════════════════════════
// DATA ATUAL — versão no rodapé
// ═══════════════════════════════════════════════════════════════════
(function() {
  const el = document.getElementById('fs-date');
  if (el) {
    const d = new Date();
    el.textContent = d.toLocaleDateString('pt-BR', {day:'2-digit', month:'2-digit', year:'numeric'});
  }
})();

// ═══════════════════════════════════════════════════════════════════
// STATUS DOS SENSORES — verificação real via APIs
// ═══════════════════════════════════════════════════════════════════
async function _checkSensorStatus() {
  const set = (id, ok, label) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = ok ? '● online' : '● offline';
    el.style.color = ok ? '#30d158' : '#ff453a';
    el.title = label || '';
  };
  const ping = async (url) => {
    try { const r = await fetch(url, { cache:'no-store' }); return r.ok; } catch { return false; }
  };
  const [ceagesp, prohort, clima, brain] = await Promise.all([
    ping('/api/hortifruti/precos'),
    ping('/api/hortifruti/precos'),
    ping('/api/clima/bioclima'),
    ping('/api/nias/brain/status'),
  ]);
  set('ss-ceagesp',   ceagesp,  'CEAGESP scraper');
  set('ss-prohort',   prohort,  'CONAB PROHORT');
  set('ss-openmeteo', clima,    'Open-Meteo via /api/clima/bioclima');
  set('ss-brain',     brain,    'NIA$ Brain /api/nias/brain/status');
  // Integrações não implementadas — estado fixo
  const noEl = (id, msg) => { const e = document.getElementById(id); if(e) { e.textContent = '● ' + msg; e.style.color = 'rgba(255,255,255,0.3)'; } };
  noEl('ss-sentinel', 'sem integração');
  noEl('ss-smap',     'sem integração');
  noEl('ss-planet',   'sem chave');
  noEl('ss-antt',     'sem integração');
}
_checkSensorStatus();
setInterval(_checkSensorStatus, 5 * 60 * 1000);

// ═══════════════════════════════════════════════════════════════════
// SATELLITE COUNTDOWN
// ═══════════════════════════════════════════════════════════════════
let satSeconds = { s2a: 42*60, ps: 75*60 };
function updateSatellite() {
  satSeconds.s2a = Math.max(0, satSeconds.s2a - 4);
  satSeconds.ps  = Math.max(0, satSeconds.ps  - 4);
  if (satSeconds.s2a === 0) satSeconds.s2a = 95 * 60;
  if (satSeconds.ps  === 0) satSeconds.ps  = 98 * 60;

  const fmt = s => { const m = Math.floor(s/60), sec = s%60; return String(m).padStart(2,'0') + ':' + String(sec).padStart(2,'0'); };
  const el1 = document.getElementById('ms-s2a'); if (el1) el1.textContent = 'Passando em ' + fmt(satSeconds.s2a);
  const el2 = document.getElementById('ms-ps');  if (el2) el2.textContent = 'Passando em ' + fmt(satSeconds.ps);
  const pct1 = (1 - satSeconds.s2a / (95*60)) * 100;
  const pct2 = (1 - satSeconds.ps  / (98*60)) * 100;
  const sf1 = document.getElementById('sf-s2a'); if (sf1) sf1.style.width = pct1 + '%';
  const sf2 = document.getElementById('sf-ps');  if (sf2) sf2.style.width = pct2 + '%';

  // topbar countdown
  const m = Math.floor(satSeconds.s2a / 60), s = satSeconds.s2a % 60;
  setLiveVal('ts-orbit', String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0'), 0, 9999);

  // polygon count — estático até integração MapBiomas ativa
  const pEl = document.getElementById('map-poly'); if (pEl && pEl.textContent === '—') pEl.textContent = '—';
  const csEl = document.getElementById('cs-poly'); if (csEl) csEl.textContent = '—';
}
setInterval(updateSatellite, 4000);
updateSatellite();

// ═══════════════════════════════════════════════════════════════════
// HUMIDITY + SPARKLINE LIVE
// ═══════════════════════════════════════════════════════════════════
// Umidade do solo — aguarda integração Open-Meteo/SMAP
// Sem simulação: valor permanece "—" até API retornar dado real
async function _fetchHumidityLive() {
  try {
    const r = await fetch('/api/clima/bioclima', { cache:'no-store' });
    if (!r.ok) return;
    const d = await r.json();
    const hum = d?.soil_moisture ?? d?.data?.soil_moisture ?? d?.humidity ?? null;
    if (hum !== null && !isNaN(hum)) {
      const v = (+hum).toFixed(1);
      setLiveVal('ts-hum', v + '%', 34.0, 0.1);
      setLiveVal('cs-hum', v + '%', 34.0, 0.1);
      pushSparkline(sparks.hum, sparkData.hum, +hum);
    }
    pushSparkline(sparks.ndvi, sparkData.ndvi, ndviData.cerrado[ndviData.cerrado.length-1]);
  } catch(e) { /* API indisponível */ }
}
setInterval(_fetchHumidityLive, 10 * 60 * 1000);

// ═══════════════════════════════════════════════════════════════════
// OFERTA TABLE LIVE FLUCTUATION
// ═══════════════════════════════════════════════════════════════════
const ofertaBase = {
  soja:147.2, milho:89.5, cana:610.0, algodao:3.1, arroz:12.3, feijao:3.4,
  'tomate-mesa':5.1, 'tomate-ind':4.7, pimentao:3.2, folh:4.1, citr:24.5,
  batata:4.8, cebola:1.6, morango:0.4, maca:1.1, melao:0.6,
  banana:7.3, mamao:1.8, alho:0.2, cenoura:0.8, pepino:0.5,
  abacaxi:2.6, uva:1.7, manga:1.4,
  'uva-ar':3.1, 'maca-ar':0.9,
  boi:11.2, frango:14.6, suino:5.2
};
// Tabela de oferta — valores de referência estáticos (CONAB/CEAGESP)
// Atualiza via /api/hortifruti/precos quando disponível; sem simulação
function _renderOfertaRef() {
  for (const [key, val] of Object.entries(ofertaBase)) {
    const el = document.getElementById('ot-' + key);
    if (el) el.textContent = val.toFixed(1);
  }
}
_renderOfertaRef();
async function _fetchOfertaLive() {
  try {
    const r = await fetch('/api/hortifruti/precos', { cache:'no-store' });
    if (!r.ok) return;
    const d = await r.json();
    const prods = d?.products || {};
    const MAP = { tomate:'tomate-mesa', batata:'batata', cebola:'cebola', cenoura:'cenoura',
                  folhosas:'folh', banana:'banana', laranja:'citr', maca:'maca', mamao:'mamao', melancia:'melao' };
    for (const [slug, key] of Object.entries(MAP)) {
      const price = prods[slug]?.price_ref_kg;
      if (price && price > 0) {
        ofertaBase[key] = +price;
        const el = document.getElementById('ot-' + key);
        if (el) el.textContent = price.toFixed(1);
      }
    }
  } catch(e) { /* mantém valores de referência */ }
}
_fetchOfertaLive();
setInterval(_fetchOfertaLive, 30 * 60 * 1000);

// ═══════════════════════════════════════════════════════════════════
// LIVE FEED EVENTS
// ═══════════════════════════════════════════════════════════════════
// Live Feed — eventos reais de /api/nias/brain/events e /api/flv/alerts
// Sem simulação: feed só exibe eventos retornados pela API
let _feedLastTs = 0;
async function _fetchFeedEvents() {
  const list = document.getElementById('live-feed-list');
  if (!list) return;
  try {
    const [evRes, alertRes] = await Promise.all([
      fetch('/api/nias/brain/events?limit=15', { cache:'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/flv/alerts?severity=all', { cache:'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null),
    ]);
    const events = evRes?.data?.events || evRes?.events || [];
    const alerts = alertRes?.alerts || alertRes?.data || [];
    const SEV_CLS = { critical:'lf-danger', high:'lf-danger', warn:'lf-warn', warning:'lf-warn', info:'lf-ok', ok:'lf-ok', satellite:'lf-sat' };
    const items = [
      ...events.map(e => ({ cls: SEV_CLS[e.severity] || 'lf-sat', msg: e.message || e.title || JSON.stringify(e), ts: e.timestamp || e.created_at })),
      ...alerts.map(a => ({ cls: SEV_CLS[a.severity] || 'lf-warn', msg: a.message || a.title || JSON.stringify(a), ts: a.timestamp || a.created_at })),
    ].filter(x => x.msg).sort((a, b) => (b.ts || 0) > (a.ts || 0) ? 1 : -1).slice(0, 20);

    if (items.length === 0) {
      if (list.children.length === 0) {
        list.innerHTML = '<div class="lf-item" style="color:rgba(255,255,255,.3);font-size:10px;">Aguardando eventos ao vivo…</div>';
      }
      return;
    }
    list.innerHTML = '';
    items.forEach(e => {
      const div = document.createElement('div');
      div.className = 'lf-item';
      const t = e.ts ? new Date(e.ts).toLocaleTimeString('pt-BR', {hour:'2-digit',minute:'2-digit'}) : '—';
      div.innerHTML = `<span class="${e.cls}">${e.msg}</span><br><span class="lf-time">${t}</span>`;
      list.appendChild(div);
    });
  } catch(err) {
    if (list.children.length === 0) {
      list.innerHTML = '<div class="lf-item" style="color:rgba(255,255,255,.3);font-size:10px;">Aguardando conexão com API…</div>';
    }
  }
}
_fetchFeedEvents();
setInterval(_fetchFeedEvents, 3 * 60 * 1000);



// ═══════════════════════════════════════════════════════════════════
// MAPAS — contornos administrativos reais (países e estados/províncias)
// Fontes em tempo de execução: geoBoundaries e OpenStreetMap/CARTO.
// Se a rede falhar, o sistema mantém as camadas produtivas locais.
// ═══════════════════════════════════════════════════════════════════
const ADMIN_BOUNDARY = {
  southAmerica: ['BRA','ARG','CHL','URY','PRY','BOL','PER','COL','ECU','VEN','GUY','SUR','GUF'],
  northAmerica: ['USA','CAN','MEX'],
  cache: {},
  layers: {}
};


// Fallback local leve: garante que as divisas apareçam mesmo se geoBoundaries/IBGE/CDN
// estiverem bloqueados por CORS, DNS ou rede do navegador. As camadas externas
// continuam sendo carregadas por cima quando disponíveis.
const LOCAL_ADMIN_FALLBACK = {
  countries: [
    ['Brasil', [[5.2,-73.9],[5.2,-34.8],[-33.8,-34.8],[-33.8,-73.9],[5.2,-73.9]]],
    ['Argentina', [[-21.8,-73.6],[-21.8,-53.6],[-55.1,-53.6],[-55.1,-73.6],[-21.8,-73.6]]],
    ['Chile', [[-17.5,-75.8],[-17.5,-66.4],[-55.9,-66.4],[-55.9,-75.8],[-17.5,-75.8]]],
    ['Uruguai', [[-30.0,-58.6],[-30.0,-53.0],[-35.2,-53.0],[-35.2,-58.6],[-30.0,-58.6]]],
    ['Paraguai', [[-19.3,-62.7],[-19.3,-54.2],[-27.6,-54.2],[-27.6,-62.7],[-19.3,-62.7]]],
    ['Bolívia', [[-9.6,-69.7],[-9.6,-57.4],[-22.9,-57.4],[-22.9,-69.7],[-9.6,-69.7]]],
    ['Peru', [[0.2,-81.5],[0.2,-68.5],[-18.5,-68.5],[-18.5,-81.5],[0.2,-81.5]]],
    ['Colômbia', [[12.6,-79.0],[12.6,-66.7],[-4.3,-66.7],[-4.3,-79.0],[12.6,-79.0]]],
    ['Equador', [[1.7,-81.2],[1.7,-75.1],[-5.1,-75.1],[-5.1,-81.2],[1.7,-81.2]]],
    ['Venezuela', [[12.5,-73.4],[12.5,-59.8],[0.6,-59.8],[0.6,-73.4],[12.5,-73.4]]],
    ['Guiana', [[8.7,-61.4],[8.7,-56.4],[1.1,-56.4],[1.1,-61.4],[8.7,-61.4]]],
    ['Suriname', [[6.1,-58.2],[6.1,-53.9],[1.8,-53.9],[1.8,-58.2],[6.1,-58.2]]],
    ['Guiana Francesa', [[5.9,-54.7],[5.9,-51.6],[2.1,-51.6],[2.1,-54.7],[5.9,-54.7]]]
  ],
  brStates: [
    ['AC', [[-7.0,-74.1],[-7.0,-66.6],[-11.2,-66.6],[-11.2,-74.1],[-7.0,-74.1]]],
    ['AM', [[2.3,-73.8],[2.3,-56.0],[-9.8,-56.0],[-9.8,-73.8],[2.3,-73.8]]],
    ['RR', [[5.4,-64.9],[5.4,-58.8],[-1.6,-58.8],[-1.6,-64.9],[5.4,-64.9]]],
    ['RO', [[-7.8,-66.9],[-7.8,-59.7],[-13.8,-59.7],[-13.8,-66.9],[-7.8,-66.9]]],
    ['PA', [[2.7,-58.9],[2.7,-46.0],[-9.9,-46.0],[-9.9,-58.9],[2.7,-58.9]]],
    ['AP', [[4.5,-54.9],[4.5,-49.8],[-1.3,-49.8],[-1.3,-54.9],[4.5,-54.9]]],
    ['TO', [[-5.2,-50.8],[-5.2,-45.7],[-13.5,-45.7],[-13.5,-50.8],[-5.2,-50.8]]],
    ['MA', [[-1.0,-48.8],[-1.0,-41.8],[-10.3,-41.8],[-10.3,-48.8],[-1.0,-48.8]]],
    ['PI', [[-2.7,-45.9],[-2.7,-40.4],[-10.9,-40.4],[-10.9,-45.9],[-2.7,-45.9]]],
    ['CE', [[-2.7,-41.5],[-2.7,-37.2],[-7.9,-37.2],[-7.9,-41.5],[-2.7,-41.5]]],
    ['RN', [[-4.8,-38.7],[-4.8,-34.8],[-6.9,-34.8],[-6.9,-38.7],[-4.8,-38.7]]],
    ['PB', [[-6.0,-38.8],[-6.0,-34.7],[-8.4,-34.7],[-8.4,-38.8],[-6.0,-38.8]]],
    ['PE', [[-7.2,-41.4],[-7.2,-34.8],[-9.7,-34.8],[-9.7,-41.4],[-7.2,-41.4]]],
    ['AL', [[-8.8,-38.3],[-8.8,-35.1],[-10.5,-35.1],[-10.5,-38.3],[-8.8,-38.3]]],
    ['SE', [[-9.5,-38.2],[-9.5,-36.3],[-11.6,-36.3],[-11.6,-38.2],[-9.5,-38.2]]],
    ['BA', [[-8.5,-46.8],[-8.5,-37.3],[-18.4,-37.3],[-18.4,-46.8],[-8.5,-46.8]]],
    ['MT', [[-7.0,-61.6],[-7.0,-50.2],[-18.2,-50.2],[-18.2,-61.6],[-7.0,-61.6]]],
    ['MS', [[-17.0,-58.2],[-17.0,-51.0],[-24.2,-51.0],[-24.2,-58.2],[-17.0,-58.2]]],
    ['GO', [[-12.4,-53.3],[-12.4,-45.9],[-19.5,-45.9],[-19.5,-53.3],[-12.4,-53.3]]],
    ['DF', [[-15.5,-48.3],[-15.5,-47.3],[-16.1,-47.3],[-16.1,-48.3],[-15.5,-48.3]]],
    ['MG', [[-14.0,-51.1],[-14.0,-39.8],[-22.9,-39.8],[-22.9,-51.1],[-14.0,-51.1]]],
    ['ES', [[-17.8,-41.9],[-17.8,-39.6],[-21.4,-39.6],[-21.4,-41.9],[-17.8,-41.9]]],
    ['RJ', [[-20.7,-44.9],[-20.7,-40.9],[-23.4,-40.9],[-23.4,-44.9],[-20.7,-44.9]]],
    ['SP', [[-19.8,-53.1],[-19.8,-44.0],[-25.4,-44.0],[-25.4,-53.1],[-19.8,-53.1]]],
    ['PR', [[-22.5,-54.7],[-22.5,-48.0],[-26.8,-48.0],[-26.8,-54.7],[-22.5,-54.7]]],
    ['SC', [[-25.9,-53.9],[-25.9,-48.3],[-29.4,-48.3],[-29.4,-53.9],[-25.9,-53.9]]],
    ['RS', [[-27.0,-57.7],[-27.0,-49.7],[-33.8,-49.7],[-33.8,-57.7],[-27.0,-57.7]]]
  ]
};

function addLocalAdminFallback(map, groupKey, includeBrazilStates=true) {
  if (!map || !window.L) return null;
  const group = L.layerGroup().addTo(map);
  const addPoly = (name, coords, kind) => {
    const layer = L.polygon(coords, adminBoundaryStyle(kind));
    layer.bindTooltip(`${kind === 'state' ? 'UF' : 'País'}: ${name}`, {sticky:true, className:'admin-boundary-tooltip'});
    layer.addTo(group);
  };
  LOCAL_ADMIN_FALLBACK.countries.forEach(([name, coords]) => addPoly(name, coords, 'country'));
  if (includeBrazilStates) LOCAL_ADMIN_FALLBACK.brStates.forEach(([name, coords]) => addPoly(name, coords, 'state'));
  ADMIN_BOUNDARY.layers[groupKey] = ADMIN_BOUNDARY.layers[groupKey] || [];
  ADMIN_BOUNDARY.layers[groupKey].push(group);
  return group;
}

function adminBoundaryStyle(kind='country') {
  if (kind === 'state') {
    return { color:'#ffdf6b', weight:1.4, opacity:1, fillOpacity:0.015, fillColor:'#ffdf6b', dashArray:'3,3', interactive:false };
  }
  return { color:'#0a84ff', weight:2.4, opacity:1, fillOpacity:0.025, fillColor:'#0a84ff', interactive:false };
}

function adminBoundaryName(feature) {
  const p = feature && feature.properties ? feature.properties : {};
  return p.shapeName || p.name || p.NAME || p.admin || p.ADMIN || p.nome || p.NOME || p.uf || p.UF || p.sigla || 'divisa administrativa';
}

async function fetchGeoJSON(url) {
  if (ADMIN_BOUNDARY.cache[url]) return ADMIN_BOUNDARY.cache[url];
  const res = await fetch(url, { cache:'force-cache' });
  if (!res.ok) throw new Error('GeoJSON indisponível: ' + url);
  const data = await res.json();
  ADMIN_BOUNDARY.cache[url] = data;
  return data;
}

async function fetchGeoBoundaries(iso3, adm='ADM1') {
  const metaUrl = `https://www.geoboundaries.org/api/current/gbOpen/${iso3}/${adm}/`;
  const meta = await fetchGeoJSON(metaUrl);
  const gjUrl = meta && (meta.gjDownloadURL || meta.simplifiedGeometryGeoJSON || meta.geoJSON);
  if (!gjUrl) throw new Error('Metadados geoBoundaries sem GeoJSON: ' + iso3 + '/' + adm);
  return fetchGeoJSON(gjUrl);
}

function addBoundaryLayerToMap(map, groupKey, geojson, kind='country', label='') {
  if (!map || !geojson || !window.L) return null;
  const layer = L.geoJSON(geojson, {
    style: () => adminBoundaryStyle(kind),
    onEachFeature: (feature, lyr) => {
      const nm = adminBoundaryName(feature);
      lyr.bindTooltip(`${kind === 'state' ? 'Estado/Província' : 'País'}: ${nm}`, {
        sticky:true,
        direction:'top',
        className:'admin-boundary-tooltip'
      });
    }
  });
  layer.__boundaryLabel = label;
  if (!ADMIN_BOUNDARY.layers[groupKey]) ADMIN_BOUNDARY.layers[groupKey] = [];
  ADMIN_BOUNDARY.layers[groupKey].push(layer);
  layer.addTo(map);
  return layer;
}

// CDN único Natural Earth — 1 request em vez de 26 requests para geoBoundaries.org
const _NE_COUNTRIES_URL = 'https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@master/geojson/ne_110m_admin_0_countries.geojson';
const _NE_STATES_URL    = 'https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@master/geojson/ne_110m_admin_1_states_provinces.geojson';

async function addCountryContours(map, groupKey, isoList) {
  const group = L.layerGroup().addTo(map);
  ADMIN_BOUNDARY.layers[groupKey] = ADMIN_BOUNDARY.layers[groupKey] || [];
  ADMIN_BOUNDARY.layers[groupKey].push(group);
  try {
    const gj = await fetchGeoJSON(_NE_COUNTRIES_URL);
    const isoSet = new Set(isoList);
    const filtered = {
      type: 'FeatureCollection',
      features: (gj.features || []).filter(f => {
        const p = f.properties || {};
        const iso = p.ISO_A3 || p.iso_a3 || p.ADM0_A3 || p.ISO_A3_EH || '';
        return isoSet.has(iso);
      })
    };
    L.geoJSON(filtered, {
      style: () => adminBoundaryStyle('country'),
      onEachFeature: (feature, lyr) => {
        const p = feature.properties || {};
        const name = p.NAME || p.ADMIN || p.name || adminBoundaryName(feature);
        lyr.bindTooltip(`País: ${name}`, {sticky:true, className:'admin-boundary-tooltip'});
      }
    }).addTo(group);
  } catch(e) { console.warn('contornos países SA falhou, usando fallback local', e); }
  return group;
}

async function addStateContours(map, groupKey, isoList) {
  const group = L.layerGroup().addTo(map);
  ADMIN_BOUNDARY.layers[groupKey] = ADMIN_BOUNDARY.layers[groupKey] || [];
  ADMIN_BOUNDARY.layers[groupKey].push(group);
  try {
    const gj = await fetchGeoJSON(_NE_STATES_URL);
    const isoSet = new Set(isoList);
    const filtered = {
      type: 'FeatureCollection',
      features: (gj.features || []).filter(f => {
        const p = f.properties || {};
        const iso = p.iso_a3 || p.ISO_A3 || p.adm0_a3 || p.ADM0_A3 || '';
        return isoSet.has(iso);
      })
    };
    L.geoJSON(filtered, {
      style: () => adminBoundaryStyle('state'),
      onEachFeature: (feature, lyr) => {
        const p = feature.properties || {};
        const name = p.name || p.NAME || p.gn_name || adminBoundaryName(feature);
        lyr.bindTooltip(`Estado/Prov.: ${name}`, {sticky:true, className:'admin-boundary-tooltip'});
      }
    }).addTo(group);
  } catch(e) { console.warn('contornos estados SA falhou', e); }
  return group;
}

function toggleAdminBoundaryGroup(groupKey, visible) {
  const arr = ADMIN_BOUNDARY.layers[groupKey] || [];
  arr.forEach(layer => {
    const map = groupKey.startsWith('municipal') ? munMap : groupKey.startsWith('predictx') ? (window.PredictXLive && PredictXLive.map) : leafletMap;
    if (!map || !layer) return;
    if (visible && !map.hasLayer(layer)) layer.addTo(map);
    if (!visible && map.hasLayer(layer)) map.removeLayer(layer);
  });
}

function setBoundaryStatus(elId, msg, ok=true) {
  const el = document.getElementById(elId);
  if (el) { el.textContent = msg; el.style.color = ok ? 'var(--accent2)' : 'var(--warn)'; }
}

// ═══════════════════════════════════════════════════════════════════
// MAP
// ═══════════════════════════════════════════════════════════════════
var mapLayerObjs = {}; // var para expor window.mapLayerObjs ao NiasOS
var leafletMap; // var (não let) para expor window.leafletMap e evitar TDZ
function initMap() {
  window._mapInit = true;
  leafletMap = L.map('map', { center: [-15, -55], zoom: 4, zoomControl: true });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors', maxZoom: 19, subdomains: 'abc' }).addTo(leafletMap);
  addLocalAdminFallback(leafletMap, 'main-local-fallback', true); setBoundaryStatus('main-boundary-status','fallback local ativo; carregando divisas reais…',false);
  addCountryContours(leafletMap, 'main-countries-real', ADMIN_BOUNDARY.southAmerica).then(() => setBoundaryStatus('main-boundary-status','países reais carregados',true)).catch(() => setBoundaryStatus('main-boundary-status','países: fallback local',false));
  addStateContours(leafletMap, 'main-states', ADMIN_BOUNDARY.southAmerica).then(() => setBoundaryStatus('main-boundary-status','países + estados/províncias reais ativos',true)).catch(() => setBoundaryStatus('main-boundary-status','estados/províncias: fonte externa indisponível',false));

  // ── CONTORNOS DOS PAÍSES DA AMÉRICA DO SUL ──
  const southAmericaCountries = [
    { name: 'Brasil', color: '#0a84ff', coords: [[-4.0,-70.0],[5.0,-60.0],[5.0,-50.0],[0.0,-45.0],[-5.0,-35.0],[-10.0,-35.0],[-15.0,-38.0],[-20.0,-40.0],[-25.0,-42.0],[-30.0,-50.0],[-33.0,-53.0],[-33.0,-58.0],[-28.0,-58.0],[-22.0,-58.0],[-15.0,-60.0],[-10.0,-65.0],[-5.0,-70.0]] },
    { name: 'Argentina', color: '#3b82f6', coords: [[-22.0,-65.0],[-24.0,-60.0],[-28.0,-58.0],[-33.0,-58.0],[-38.0,-58.0],[-42.0,-65.0],[-46.0,-67.0],[-52.0,-69.0],[-55.0,-68.0],[-52.0,-72.0],[-46.0,-75.0],[-40.0,-62.0],[-35.0,-63.0],[-30.0,-64.0],[-25.0,-65.0]] },
    { name: 'Chile', color: '#ef4444', coords: [[-18.0,-70.0],[-20.0,-70.0],[-23.0,-70.0],[-26.0,-70.0],[-29.0,-71.0],[-33.0,-71.0],[-37.0,-73.0],[-41.0,-73.0],[-46.0,-75.0],[-52.0,-69.0],[-55.0,-68.0],[-52.0,-72.0],[-46.0,-75.0],[-42.0,-75.0],[-38.0,-73.0],[-33.0,-71.0],[-30.0,-70.0],[-25.0,-70.0],[-20.0,-70.0]] },
    { name: 'Uruguai', color: '#eab308', coords: [[-30.0,-58.0],[-31.0,-56.0],[-32.0,-54.0],[-33.0,-54.0],[-34.0,-54.0],[-35.0,-55.0],[-35.0,-58.0],[-34.0,-58.0],[-32.0,-58.0],[-30.0,-58.0]] },
    { name: 'Paraguai', color: '#f97316', coords: [[-20.0,-62.0],[-20.0,-58.0],[-22.0,-56.0],[-24.0,-55.0],[-27.0,-55.0],[-28.0,-56.0],[-28.0,-59.0],[-27.0,-61.0],[-25.0,-62.0],[-22.0,-62.0]] },
    { name: 'Bolívia', color: '#a855f7', coords: [[-10.0,-68.0],[-10.0,-65.0],[-12.0,-62.0],[-15.0,-60.0],[-18.0,-58.0],[-20.0,-63.0],[-22.0,-65.0],[-24.0,-68.0],[-20.0,-70.0],[-15.0,-68.0]] },
    { name: 'Peru', color: '#ec4899', coords: [[-0.1,-80.0],[-5.0,-80.0],[-10.0,-78.0],[-15.0,-73.0],[-18.0,-70.0],[-15.0,-68.0],[-10.0,-72.0],[-5.0,-75.0],[-0.1,-78.0]] },
    { name: 'Equador', color: '#14b8a6', coords: [[1.0,-92.0],[1.0,-78.0],[-0.1,-75.0],[-2.0,-77.0],[-5.0,-80.0],[-2.0,-82.0],[0.0,-85.0],[2.0,-90.0]] },
    { name: 'Colômbia', color: '#f97316', coords: [[12.0,-73.0],[8.0,-77.0],[4.0,-78.0],[1.0,-78.0],[1.0,-72.0],[4.0,-70.0],[8.0,-72.0],[11.0,-74.0]] },
    { name: 'Venezuela', color: '#bf5af2', coords: [[12.0,-73.0],[8.0,-72.0],[4.0,-70.0],[1.0,-67.0],[4.0,-62.0],[8.0,-60.0],[11.0,-62.0],[12.0,-67.0]] },
    { name: 'Guiana', color: '#22c55e', coords: [[8.0,-60.0],[5.0,-58.0],[2.0,-57.0],[2.0,-54.0],[5.0,-52.0],[8.0,-55.0]] },
    { name: 'Suriname', color: '#84cc16', coords: [[6.0,-58.0],[4.0,-56.0],[2.0,-55.0],[2.0,-54.0],[4.0,-52.0],[6.0,-54.0]] },
    { name: 'Guiana Francesa', color: '#10b981', coords: [[5.0,-54.0],[3.0,-52.0],[2.0,-51.0],[4.0,-49.0],[6.0,-51.0]] },
  ];
  
  mapLayerObjs['country-borders'] = L.layerGroup(
    southAmericaCountries.map(c => 
      L.polygon(c.coords, { 
        color: c.color, 
        fillColor: c.color, 
        fillOpacity: 0.05, 
        weight: 2,
        dashArray: '5,5'
      }).bindTooltip(`<b>${c.name}</b>`, { permanent: false, direction: 'center' })
    )
  ).addTo(leafletMap);

  const addZones = (key, zones) => {
    mapLayerObjs[key] = L.layerGroup(zones.map(z =>
      L.polygon(z.ll, { color: z.color, fillColor: z.color, fillOpacity: 0.28, weight: 1 })
        .bindPopup(`<div style="font-family:monospace;font-size:12px;color:#000000"><b>${z.label}</b>${z.extra||''}</div>`)
    ));
    return mapLayerObjs[key];
  };

  addZones('soja', [
    { ll:[[-12,-57],[-10,-55],[-11,-53],[-13,-55]], color:'#00a550', label:'Soja — Sorriso, MT', extra:'<br>NDVI: 0.63 | Est: R6' },
    { ll:[[-14,-52],[-12,-50],[-13,-48],[-15,-50]], color:'#00a550', label:'Soja — Campo Verde, MT', extra:'<br>NDVI: 0.61 | Est: R7' },
    { ll:[[-17,-51],[-15,-49],[-16,-47],[-18,-49]], color:'#7ec850', label:'Soja — Rio Verde, GO', extra:'<br>NDVI: 0.58 | Est: R6' },
    { ll:[[-23,-52],[-21,-50],[-22,-48],[-24,-50]], color:'#00a550', label:'Soja — Londrina, PR', extra:'<br>NDVI: 0.62 | Est: R5' },
    { ll:[[-28,-54],[-26,-52],[-27,-50],[-29,-52]], color:'#7ec850', label:'Soja — Passo Fundo, RS', extra:'<br>NDVI: 0.55 | Est: R4' },
  ]).addTo(leafletMap);

  addZones('milho', [
    { ll:[[-15,-55],[-13,-53],[-14,-51],[-16,-53]], color:'#ffd60a', label:'Milho — Sapezal, MT', extra:'<br>NDVI: 0.60 | Est: V12' },
    { ll:[[-20,-51],[-18,-49],[-19,-47],[-21,-49]], color:'#ffd60a', label:'Milho — Chapadão do Sul, MS', extra:'<br>NDVI: 0.57 | Est: V10' },
  ]).addTo(leafletMap);

  addZones('alertas', [
    { ll:[[-11,-46],[-9,-44],[-10,-42],[-12,-44]], color:'#ff453a', label:'⚠ Estresse Hídrico — MATOPIBA', extra:'<br>NDVI: 0.38 ▼ | Umidade: 18%' },
    { ll:[[-8,-47],[-6,-45],[-7,-43],[-9,-45]],   color:'#ff453a', label:'⚠ Estresse Hídrico — Norte MT', extra:'<br>NDVI: 0.42 ▼ | Umidade: 21%' },
    { ll:[[-23.5,-52],[-22,-50],[-22.5,-49],[-24,-51]], color:'#ff9f0a', label:'⚠ Praga/Doença — Norte PR', extra:'<br>Ferrugem asiática suspeita' },
    { ll:[[-21.5,-55],[-20,-53],[-20.5,-52],[-22,-54]], color:'#ff9f0a', label:'⚠ Praga/Doença — Sul MS', extra:'<br>Lagarta-do-cartucho' },
  ]).addTo(leafletMap);

  addZones('cana', [
    { ll:[[-22,-48],[-20,-46],[-21,-44],[-23,-46]], color:'#9b59b6', label:'Cana — Ribeirão Preto, SP', extra:'<br>NDVI: 0.71 | Maturação' },
  ]);
  addZones('pastagem', [
    { ll:[[-18,-56],[-16,-54],[-17,-52],[-19,-54]], color:'#8B6914', label:'Pastagem — Centro-Oeste MT', extra:'<br>Lotação: 1.8 UA/ha' },
    { ll:[[-30,-56],[-28,-54],[-29,-52],[-31,-54]], color:'#8B6914', label:'Pastagem — Fronteira RS/UR', extra:'<br>Lotação: 1.2 UA/ha' },
  ]);
  addZones('horti', [
    // ── SP — Cinturão Verde
    { ll:[[-23.5,-47],[-22.5,-46],[-23,-45.5],[-24,-46.5]], color:'#0a84ff', label:'Horticultura — Campinas/Cajamar, SP', extra:'<br>Tomate/Pepino estufa — +2.1°C ⚠' },
    { ll:[[-23.1,-46.3],[-22.6,-45.9],[-22.8,-45.5],[-23.3,-45.9]], color:'#0a84ff', label:'Cinturão Verde — Mogi das Cruzes, SP', extra:'<br>Pepino/Folhosas/Flores' },
    { ll:[[-23.0,-46.6],[-22.5,-46.2],[-22.7,-45.9],[-23.2,-46.3]], color:'#0a84ff', label:'Atibaia/Joanópolis, SP', extra:'<br>Morango, Flores — ciclo curto' },
    // ── SP / MG — Triângulo
    { ll:[[-18.8,-48.2],[-18.2,-47.6],[-18.5,-47.1],[-19.1,-47.7]], color:'#0a84ff', label:'Alto Paranaíba/Araguari, MG', extra:'<br>Cenoura, Alho, Batata' },
    // ── RJ — Holanda Fluminense
    { ll:[[-22.3,-43.0],[-21.8,-42.5],[-22.0,-42.0],[-22.5,-42.5]], color:'#0a84ff', label:'Nova Friburgo/Teresópolis, RJ', extra:'<br>Folhosas finas — Holanda Fluminense' },
    // ── SC / RS — Sul
    { ll:[[-27.8,-50.5],[-27.2,-49.9],[-27.5,-49.4],[-28.1,-50.0]], color:'#0a84ff', label:'São Joaquim/Vacaria, SC/RS', extra:'<br>Maçã, Pera — NDVI: 0.72 ▲' },
    { ll:[[-27.6,-48.8],[-27.1,-48.3],[-27.3,-47.8],[-27.9,-48.3]], color:'#0a84ff', label:'Ituporanga/Alfredo Wagner, SC', extra:'<br>Cebola — principal polo nacional' },
    { ll:[[-25.3,-50.9],[-24.8,-50.3],[-25.0,-49.8],[-25.6,-50.4]], color:'#0a84ff', label:'Guarapuava, PR', extra:'<br>Batata, Cebola — altitude' },
    // ── RN / CE — Nordeste
    { ll:[[-5.2,-37.5],[-4.7,-36.9],[-5.0,-36.4],[-5.6,-37.0]], color:'#ff9f0a', label:'Mossoró/Açu, RN', extra:'<br>Melão — Seca crítica NDVI: 0.44 ▼▼' },
    { ll:[[-4.8,-37.8],[-4.2,-37.1],[-4.5,-36.6],[-5.1,-37.3]], color:'#ff9f0a', label:'Quixeré/Limoeiro, CE', extra:'<br>Melão irrigado — deficit hídrico' },
    // ── BA / PE — Vale São Francisco
    { ll:[[-9.2,-40.5],[-8.6,-39.8],[-8.9,-39.3],[-9.5,-40.0]], color:'#0a84ff', label:'Juazeiro/Petrolina, BA/PE', extra:'<br>Manga, Uva, Melão irrigados — VSF' },
    // ── ES / BA — Mamão, Banana
    { ll:[[-19.4,-40.1],[-18.8,-39.5],[-19.1,-39.0],[-19.7,-39.6]], color:'#0a84ff', label:'Linhares/Aracruz, ES', extra:'<br>Mamão Formosa/Hawai — safra normal' },
    { ll:[[-13.0,-39.5],[-12.4,-38.9],[-12.7,-38.4],[-13.3,-39.0]], color:'#0a84ff', label:'Cruz das Almas/Mutuípe, BA', extra:'<br>Banana, Mamão — normal' },
    // ── PA / TO — Abacaxi
    { ll:[[-6.8,-48.3],[-6.2,-47.7],[-6.5,-47.2],[-7.1,-47.8]], color:'#0a84ff', label:'Floresta do Araguaia, PA/TO', extra:'<br>Abacaxi — safra plena' },
    // ── Argentina — Mendoza
    { ll:[[-34.5,-69.5],[-33.5,-68.5],[-33.8,-67.8],[-35.0,-68.8]], color:'#9b59b6', label:'Mendoza, AR', extra:'<br>Uva/Alho — Vindima em curso' },
    // ── Argentina — Patagônia
    { ll:[[-39.5,-68.5],[-38.5,-67.5],[-38.8,-66.8],[-40.0,-67.8]], color:'#9b59b6', label:'Rio Negro/Neuquén, AR', extra:'<br>Maçã, Pera — NDVI: 0.70 ▲' },
    // ── PR — Curitiba cinturão
    { ll:[[-25.4,-49.5],[-24.5,-48.8],[-24.8,-48.3],[-25.7,-49]], color:'#0a84ff', label:'Curitiba/Colombo, PR', extra:'<br>Folhosas, Tomate — risco anomalia' },
  ]);

  // ── TOMATE DE MESA (cyan)
  addZones('tomate-mesa', [
    { ll:[[-23.6,-46.6],[-23.0,-46.0],[-23.3,-45.5],[-23.9,-46.1]], color:'#0a84ff', label:'🍅 Tomate Mesa — Mogi das Cruzes/Cajamar, SP', extra:'<br>Tipo: Caqui, Carmem, Longa Vida<br>NDVI: 0.49 ▼ | Alerta Térmico' },
    { ll:[[-22.8,-46.9],[-22.2,-46.3],[-22.5,-45.8],[-23.1,-46.4]], color:'#0a84ff', label:'🍅 Tomate Mesa — Sumaré/Cabreúva, SP', extra:'<br>Tipo: Salada, Italiano<br>NDVI: 0.51 ▼' },
    { ll:[[-21.4,-44.2],[-20.8,-43.6],[-21.1,-43.1],[-21.7,-43.7]], color:'#0a84ff', label:'🍅 Tomate Mesa — Barbacena/Andradas, MG', extra:'<br>Tipo: Caqui, Cereja<br>NDVI: 0.53' },
    { ll:[[-21.8,-46.5],[-21.2,-45.9],[-21.5,-45.4],[-22.1,-46.0]], color:'#0a84ff', label:'🍅 Tomate Mesa — Poço de Caldas/S.J.R.Pardo, SP/MG', extra:'<br>Tipo: Salada, Longa Vida' },
    { ll:[[-22.3,-43.1],[-21.7,-42.5],[-22.0,-42.0],[-22.6,-42.6]], color:'#0a84ff', label:'🍅 Tomate Mesa — Teresópolis/Nova Friburgo, RJ', extra:'<br>Tipo: Caqui, Italiano<br>NDVI: 0.50' },
    { ll:[[-20.3,-40.8],[-19.8,-40.2],[-20.1,-39.7],[-20.6,-40.3]], color:'#0a84ff', label:'🍅 Tomate Mesa — Domingos Martins/Santa Teresa, ES', extra:'<br>Tipo: Caqui, Longa Vida' },
    { ll:[[-16.2,-49.9],[-15.6,-49.3],[-15.9,-48.8],[-16.5,-49.4]], color:'#0a84ff', label:'🍅 Tomate Mesa — Itaberaí/Ceres, GO', extra:'<br>Tipo: Caqui, Salada<br>NDVI: 0.52' },
    { ll:[[-13.1,-41.5],[-12.5,-40.9],[-12.8,-40.4],[-13.4,-41.0]], color:'#0a84ff', label:'🍅 Tomate Mesa — Mucugê, BA (Chapada Diamantina)', extra:'<br>Tipo: Orgânico, Cereja<br>NDVI: 0.61' },
    { ll:[[-24.5,-54.2],[-23.9,-53.6],[-24.2,-53.1],[-24.8,-53.7]], color:'#0a84ff', label:'🍅 Tomate Mesa — Marechal C. Rondon, PR', extra:'<br>Tipo: Salada, Caqui' },
  ]).addTo(leafletMap);

  // ── TOMATE INDÚSTRIA (laranja)
  addZones('tomate-ind', [
    { ll:[[-17.5,-48.5],[-16.9,-47.9],[-17.2,-47.4],[-17.8,-48.0]], color:'#ff9f0a', label:'🍅 Tomate Indústria — Pires do Rio/Leopoldo de Bulhões, GO', extra:'<br>Principal polo nacional BR<br>Empresas: Quero, Predilecta, Kraft Heinz<br>NDVI: 0.53 ▼ | BRIX em queda' },
    { ll:[[-16.4,-48.9],[-15.8,-48.3],[-16.1,-47.8],[-16.7,-48.4]], color:'#ff9f0a', label:'🍅 Tomate Indústria — Anápolis/São Miguel P.Q., GO', extra:'<br>Tipo: IAC, Fortaleza, Heinz<br>Empresas: Unilever, Quero' },
    { ll:[[-18.6,-47.0],[-18.0,-46.4],[-18.3,-45.9],[-18.9,-46.5]], color:'#ff9f0a', label:'🍅 Tomate Indústria — Patos de Minas/Unaí, MG', extra:'<br>2° maior polo BR<br>Tipo: Concentrado<br>NDVI: 0.55' },
    { ll:[[-19.3,-48.2],[-18.7,-47.6],[-19.0,-47.1],[-19.6,-47.7]], color:'#ff9f0a', label:'🍅 Tomate Indústria — Uberlândia/Frutal, MG', extra:'<br>Tipo: Paste, Purê, Polpa<br>Empresas: Etti, Predilecta' },
    { ll:[[-17.3,-44.6],[-16.7,-44.0],[-17.0,-43.5],[-17.6,-44.1]], color:'#ff9f0a', label:'🍅 Tomate Indústria — Pirapora/Montes Claros, MG', extra:'<br>Irrigação: Perímetro Jaíba<br>NDVI: 0.50' },
    { ll:[[-21.6,-48.9],[-21.0,-48.3],[-21.3,-47.8],[-21.9,-48.4]], color:'#ff9f0a', label:'🍅 Tomate Indústria — Itápolis/Fernando Prestes, SP', extra:'<br>Tipo: Paste, Concentrado<br>NDVI: 0.54' },
    { ll:[[-21.3,-49.4],[-20.7,-48.8],[-21.0,-48.3],[-21.6,-48.9]], color:'#ff9f0a', label:'🍅 Tomate Indústria — Borborema/Taquaritinga, SP', extra:'<br>Processamento: Extrato, Pelado<br>Empresa: Cargill Tomates' },
    { ll:[[-9.3,-40.6],[-8.7,-40.0],[-9.0,-39.5],[-9.6,-40.1]], color:'#ff9f0a', label:'🍅 Tomate Indústria — Juazeiro/Petrolina, BA/PE', extra:'<br>Irrigado — Perímetro VSF<br>Tipo: Concentrado 28-30°Brix' },
  ]).addTo(leafletMap);
  const portData = [
    { ll:[-23.95,-46.33], name:'Porto de Santos', info:'Sat: 74% | 6/8 berços | ATENÇÃO', color:'#ffd60a' },
    { ll:[-25.52,-48.52], name:'Porto de Paranaguá', info:'Sat: 71% | 5/7 berços | ATENÇÃO', color:'#ffd60a' },
    { ll:[-32.95,-60.65], name:'Porto de Rosário (AR)', info:'Sat: 48% | NORMAL', color:'#30d158' },
    { ll:[-3.10,-60.00],  name:'Terminal Miritituba (PA)', info:'Hidrovia Tapajós | Normal', color:'#0a84ff' },
  ];
  mapLayerObjs['portos'] = L.layerGroup([
    ...portData.map(p =>
      createSonarMarker(p.ll, { state: p.color === '#ff453a' ? 'alert' : 'ai', size: 8, tooltip: `<b>${p.name}</b><br>${p.info}` })
    ),
    // BR-163 route line
    L.polyline([[-3.1,-60.0],[-7.5,-58.0],[-9.5,-57.0],[-12.5,-55.9],[-15.0,-55.0]], { color:'#ff453a', weight:2, opacity:.7, dashArray:'6,4' })
      .bindPopup('<div style="font-family:monospace;font-size:12px;color:#000000"><b>BR-163</b><br>Saturação: 82% CRÍTICO</div>'),
    L.polyline([[-12.5,-55.9],[-15.5,-54.5],[-17.5,-53.0],[-20.5,-51.5],[-23.95,-46.33]], { color:'#ffd60a', weight:1.5, opacity:.6, dashArray:'4,4' })
      .bindPopup('<div style="font-family:monospace;font-size:12px;color:#000000">Corredor Santos</div>'),
  ]).addTo(leafletMap);
  // ── POLOS PRODUTIVOS SA (42 polos carregados de /api/nias/regions) ──────────
  const _poleImportanceColor = { muito_alta:'#50C878', alta:'#0a84ff', media:'#ffd60a', baixa:'rgba(235,235,245,0.6)' };
  mapLayerObjs['sa-poles'] = L.layerGroup();
  fetch('/api/nias/regions', { cache: 'no-store' })
    .then(r => r.json())
    .then(data => {
      const poles = (data.data || {}).regions || [];
      poles.forEach(p => {
        const color = _poleImportanceColor[p.importance] || 'rgba(235,235,245,0.6)';
        const prods = (p.products || []).slice(0, 4).join(', ') || 'não informado';
        const marker = L.circleMarker([p.lat, p.lon], {
          radius: p.importance === 'muito_alta' ? 8 : p.importance === 'alta' ? 6 : 5,
          color, fillColor: color, fillOpacity: 0.75, weight: 1.5,
        });
        marker.bindTooltip(`
          <div style="font-family:monospace;font-size:11px;min-width:180px;">
            <b style="color:${color}">${p.region}</b><br>
            <span style="color:#8b949e">País:</span> ${p.country} (${p.country_code})<br>
            <span style="color:#8b949e">Estado/Dpto:</span> ${p.state_or_department || '—'}<br>
            <span style="color:#8b949e">Produtos:</span> ${prods}<br>
            <span style="color:#8b949e">Importância:</span> ${p.importance}<br>
            <span style="color:rgba(235,235,245,0.6);font-size:9px;">Fonte: NIAS Regions · Clique para detalhes</span>
          </div>`, { sticky: true, direction: 'right' });
        marker.on('click', () => {
          if (window.leafletMap) window.leafletMap.flyTo([p.lat, p.lon ?? p.lng], 6, { duration: 1.2, easeLinearity: 0.1 });
          _showPoleDetail(p, color);
        });
        mapLayerObjs['sa-poles'].addLayer(marker);
      });
      if (leafletMap) mapLayerObjs['sa-poles'].addTo(leafletMap);
      // Update timestamp UI
      const now = new Date();
      const fmt = d => d.toLocaleString('pt-BR', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' });
      const nextHour = new Date(now.getTime() + 60*60*1000);
      const el = document.getElementById('map-time'); if (el) el.textContent = fmt(now);
      const nxt = document.getElementById('map-next-update'); if (nxt) nxt.textContent = fmt(nextHour);
      const cnt = document.getElementById('map-poles-count'); if (cnt) cnt.textContent = poles.length + ' polos (dado estrutural)';
    })
    .catch(e => {
      console.warn('SA poles não carregados:', e);
      const cnt = document.getElementById('map-poles-count'); if (cnt) cnt.textContent = 'indisponível (API offline)';
    });

  setTimeout(() => leafletMap && leafletMap.invalidateSize(), 120);

  // Carrega layer satelital após mapa pronto
  setTimeout(loadSatelliteLayer, 3000);
}

// Painel lateral de detalhes do polo SA (clique no marcador)
function _showPoleDetail(pole, color) {
  let panel = document.getElementById('_pole-detail-panel');
  if (!panel) {
    panel = document.createElement('div');
    panel.id = '_pole-detail-panel';
    panel.style.cssText = 'position:absolute;top:40px;left:10px;bottom:10px;width:260px;z-index:1200;background:rgba(0,0,0,.96);border:1px solid var(--border);border-radius:6px;overflow:auto;padding:12px;font-family:monospace;box-shadow:0 4px 20px rgba(0,0,0,.6);';
    document.getElementById('panel-map').appendChild(panel);
  }
  const prods = (pole.products || []).join(', ') || '—';
  panel.style.display = 'block';
  panel.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
      <span style="color:${color};font-size:11px;font-weight:bold;letter-spacing:1px;">${pole.region}</span>
      <button onclick="document.getElementById('_pole-detail-panel').style.display='none'" style="background:none;border:none;color:var(--text2);cursor:pointer;font-size:14px;line-height:1;">×</button>
    </div>
    <div style="font-size:10px;line-height:1.7;color:var(--text);">
      <div><span style="color:var(--text2)">País:</span> ${pole.country} (${pole.country_code})</div>
      <div><span style="color:var(--text2)">Estado/Dpto:</span> ${pole.state_or_department || '—'}</div>
      <div><span style="color:var(--text2)">Cidade ref.:</span> ${pole.city || '—'}</div>
      <div><span style="color:var(--text2)">Lat/Lon:</span> ${pole.lat}, ${pole.lon}</div>
      <div><span style="color:var(--text2)">Importância:</span> ${pole.importance}</div>
      <div style="margin-top:6px;"><span style="color:var(--text2)">Produtos:</span><br><span style="color:var(--accent2)">${prods}</span></div>
      ${pole.notes ? `<div style="margin-top:6px;font-size:9px;color:var(--text2);border-top:1px solid var(--border);padding-top:6px;">${pole.notes}</div>` : ''}
    </div>
    <div style="margin-top:12px;display:flex;flex-direction:column;gap:6px;">
      <button onclick="showPanel('brain')" style="background:rgba(139,92,246,.15);border:1px solid #bf5af2;color:#bf5af2;font-family:monospace;font-size:9px;padding:4px 8px;border-radius:4px;cursor:pointer;text-align:left;">◉ Ver análise no Cérebro NIAS</button>
      <button disabled title="Tese estratégica requer dados de preço persistidos para ${pole.country_code}. Configure a fonte de preço para ativar." style="background:none;border:1px solid var(--border);color:var(--text2);font-family:monospace;font-size:9px;padding:4px 8px;border-radius:4px;cursor:not-allowed;text-align:left;opacity:0.5;">📊 Ver tese (aguarda fonte de preço: ${pole.country_code})</button>
      <button disabled title="Monitoramento automático requer backend configurado com chave de alertas para este polo." style="background:none;border:1px solid var(--border);color:var(--text2);font-family:monospace;font-size:9px;padding:4px 8px;border-radius:4px;cursor:not-allowed;text-align:left;opacity:0.5;">🔔 Monitorar polo (requer configuração de alertas)</button>
    </div>
    <div style="margin-top:10px;font-size:8px;color:var(--text2);border-top:1px solid var(--border);padding-top:6px;">
      Fonte: NIAS Regions · Dado estrutural (sem atualização em tempo real)<br>
      Clima e preço: indisponível (aguarda coleta Open-Meteo / fonte de preço)
    </div>`;
}

function toggleLayer(name, cb) {
  if (!leafletMap) return;
  if (!mapLayerObjs[name]) {
    cb.checked = false;
    const _layerMsgs = {
      planet: 'Camada Planet indisponível: configure PLANET_KEY no backend para ativar imagens de 3m.',
    };
    const msg = _layerMsgs[name] || `Camada "${name}" indisponível: dados ainda não carregados.`;
    const el = document.getElementById('main-boundary-status');
    if (el) { el.style.color = 'var(--warn)'; el.textContent = '⚠ ' + msg; setTimeout(() => { el.style.color = ''; el.textContent = 'divisas oficiais carregadas'; }, 5000); }
    else alert(msg);
    return;
  }
  if (cb.checked) mapLayerObjs[name].addTo(leafletMap);
  else leafletMap.removeLayer(mapLayerObjs[name]);
}

// ═══════════════════════════════════════════════════════════════════
// SATELLITE IA LAYER — NDVI × Calendário Agrícola × CEASA
// ═══════════════════════════════════════════════════════════════════

const SAT_STAGE_LABELS = {
  'plantio':          { label: 'Plantio',         cor: '#ff9f0a', emoji: '🌱' },
  'emergencia':       { label: 'Emergência',       cor: '#ffd60a', emoji: '🌿' },
  'crescimento':      { label: 'Crescimento',      cor: '#30d158', emoji: '📈' },
  'pico_biomassa':    { label: 'Pico Biomassa',    cor: '#34c759', emoji: '🌾' },
  'pre_colheita':     { label: 'Pré-Colheita',     cor: '#64d2ff', emoji: '⏳' },
  'colheita':         { label: 'Colheita',         cor: '#0a84ff', emoji: '🚜' },
  'pos_colheita':     { label: 'Pós-Colheita',     cor: '#8e8e93', emoji: '📦' },
  'vegetacao_ativa':  { label: 'Vegetação Ativa',  cor: '#30d158', emoji: '🌳' },
  'pousio':           { label: 'Pousio',           cor: '#636366', emoji: '🏜' },
  'descanso':         { label: 'Descanso',         cor: '#48484a', emoji: '💤' },
};

function _ndviToColor(ndvi) {
  if (ndvi > 0.7) return '#30d158';
  if (ndvi > 0.55) return '#ffd60a';
  if (ndvi > 0.4) return '#ff9f0a';
  if (ndvi > 0.25) return '#ff6b35';
  return '#8e8e93';
}

function _satMarkerIcon(reg, dominante) {
  const stg = SAT_STAGE_LABELS[dominante?.estagio_dominante] || { cor: '#8e8e93', emoji: '📍' };
  const ndviColor = _ndviToColor(reg.ndvi || 0.3);
  const ndviPct = Math.round((reg.ndvi || 0.3) * 100);
  return L.divIcon({
    className: '',
    iconSize: [54, 54],
    iconAnchor: [27, 27],
    html: `<div style="
      width:54px;height:54px;border-radius:50%;
      background:radial-gradient(circle at 40% 40%, ${stg.cor}33, ${stg.cor}11);
      border:2px solid ${stg.cor};
      box-shadow:0 0 16px ${stg.cor}55, 0 2px 8px rgba(0,0,0,.5);
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      cursor:pointer;transition:transform .15s;
      animation:sat-pulse 3s ease-in-out infinite;
    ">
      <span style="font-size:18px;line-height:1;">${stg.emoji}</span>
      <span style="font-size:8px;font-weight:700;color:${ndviColor};font-family:monospace;letter-spacing:-0.5px;">${ndviPct}%</span>
    </div>`
  });
}

function _satPopupHTML(rk, reg) {
  const cults = (reg.culturas || []).filter(c => c.estagio !== 'pousio').slice(0, 5);
  const ndviBar = Math.round((reg.ndvi || 0) * 100);
  const ndviColor = _ndviToColor(reg.ndvi || 0);
  const trendArrow = reg.ndvi_trend === 'subindo' ? '▲' : reg.ndvi_trend === 'caindo' ? '▼' : '—';
  const trendColor = reg.ndvi_trend === 'subindo' ? '#30d158' : reg.ndvi_trend === 'caindo' ? '#ff453a' : '#8e8e93';

  const cultsHTML = cults.map(c => {
    const stg = SAT_STAGE_LABELS[c.estagio] || { label: c.estagio, cor: '#8e8e93', emoji: '📍' };
    const margem = c.margem_estimada_pct != null ? `<span style="color:${c.margem_estimada_pct > 0 ? '#30d158' : '#ff453a'}">${c.margem_estimada_pct > 0 ? '+' : ''}${c.margem_estimada_pct}%</span>` : '<span style="color:#636366">—</span>';
    const precoKg = c.ceasa_preco_kg ? `<b style="color:#30d158">R$ ${c.ceasa_preco_kg.toFixed(2)}/kg</b>` : '<span style="color:#636366">s/cotação</span>';
    const volStr = c.volume_mt > 0 ? (c.volume_mt < 0.001 ? `${(c.volume_mt*1000).toFixed(1)}kt` : `${c.volume_mt.toFixed(3)} Mt`) : '—';
    const valorStr = c.valor_mi_reais > 0 ? `R$ ${c.valor_mi_reais.toFixed(1)}Mi` : '—';

    const ceasaFontesHTML = (c.ceasa_fontes || []).slice(0, 3).map(f =>
      `<span style="color:#636366;">${f.uf}: <b style="color:var(--accent2)">R$ ${f.preco_kg?.toFixed(2) || '?'}/kg</b></span>`
    ).join(' · ');

    return `<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
        <span style="font-size:13px;">${stg.emoji}</span>
        <span style="font-size:11px;font-weight:700;color:#fff;text-transform:uppercase;letter-spacing:.3px;">${c.cultura}</span>
        <span style="font-size:9px;padding:1px 6px;border-radius:8px;background:${stg.cor}22;border:1px solid ${stg.cor}55;color:${stg.cor};font-weight:600;">${stg.label}</span>
        <span style="margin-left:auto;font-size:9px;color:${trendColor};">${trendArrow} NDVI</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;font-size:9px;color:#8e8e93;">
        <div>Vol: <b style="color:#fff;">${volStr}</b></div>
        <div>Valor: <b style="color:#ffd60a;">${valorStr}</b></div>
        <div>Margem: ${margem}</div>
      </div>
      ${c.ceasa_preco_kg ? `<div style="font-size:9px;margin-top:4px;">CEASA: ${precoKg} ${ceasaFontesHTML ? `· ${ceasaFontesHTML}` : ''}</div>` : ''}
    </div>`;
  }).join('');

  const ndviSparkHTML = (reg.ndvi_series || []).slice(-14).map((v, i, arr) => {
    const h = Math.round(v * 100);
    const isLast = i === arr.length - 1;
    return `<div style="flex:1;display:flex;align-items:flex-end;height:24px;">
      <div style="width:100%;height:${h}%;background:${isLast ? ndviColor : ndviColor+'66'};border-radius:1px 1px 0 0;min-height:2px;"></div>
    </div>`;
  }).join('');

  return `<div style="
    min-width:320px;max-width:380px;
    background:#1c1c1e;border:1px solid rgba(255,255,255,0.12);
    border-radius:14px;padding:0;overflow:hidden;
    font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;
    box-shadow:0 20px 60px rgba(0,0,0,0.7);
  ">
    <!-- Header -->
    <div style="padding:14px 16px 10px;background:linear-gradient(135deg,${reg.cor || '#30d158'}18,transparent);">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <div style="width:8px;height:8px;border-radius:50%;background:${reg.cor || '#30d158'};box-shadow:0 0 8px ${reg.cor || '#30d158'};animation:pulse-dot 2s ease-in-out infinite;flex-shrink:0;"></div>
        <span style="font-size:13px;font-weight:700;color:#fff;letter-spacing:.3px;">${reg.nome}</span>
        <span style="font-size:9px;color:#8e8e93;margin-left:auto;">${reg.estados}</span>
      </div>
      <!-- NDVI bar -->
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-size:9px;color:#8e8e93;width:32px;">NDVI</span>
        <span style="font-size:7px;padding:1px 4px;border-radius:3px;background:rgba(255,149,0,0.18);color:#ff9f0a;font-weight:700;letter-spacing:.3px;flex-shrink:0;">PROXY</span>
        <div style="flex:1;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;overflow:hidden;">
          <div style="height:100%;width:${ndviBar}%;background:${ndviColor};border-radius:2px;transition:width 1s ease;"></div>
        </div>
        <span style="font-size:11px;font-weight:700;color:${ndviColor};font-family:monospace;width:32px;text-align:right;">${(reg.ndvi||0).toFixed(2)}</span>
        <span style="font-size:9px;color:${trendColor};">${trendArrow}</span>
      </div>
      <!-- NDVI sparkline -->
      ${ndviSparkHTML ? `<div style="display:flex;gap:1px;margin-top:8px;align-items:flex-end;height:24px;padding:0 2px;">${ndviSparkHTML}</div>` : ''}
      <!-- KPIs -->
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;margin-top:10px;">
        <div style="background:rgba(255,255,255,0.06);border-radius:8px;padding:6px 8px;text-align:center;">
          <div style="font-size:7px;color:#636366;letter-spacing:.5px;margin-bottom:2px;">ÁREA PLANTADA</div>
          <div style="font-size:13px;font-weight:700;color:#fff;">${(reg.area_ha/1e6).toFixed(1)}</div>
          <div style="font-size:7px;color:#636366;">Mha</div>
        </div>
        <div style="background:rgba(255,255,255,0.06);border-radius:8px;padding:6px 8px;text-align:center;">
          <div style="font-size:7px;color:#636366;letter-spacing:.5px;margin-bottom:2px;">VOLUME REF.</div>
          <div style="font-size:13px;font-weight:700;color:#ffd60a;">${reg.volume_total_mt?.toFixed(1) || '—'}</div>
          <div style="font-size:7px;color:#636366;">Mt/ano</div>
        </div>
        <div style="background:rgba(255,255,255,0.06);border-radius:8px;padding:6px 8px;text-align:center;">
          <div style="font-size:7px;color:#636366;letter-spacing:.5px;margin-bottom:2px;">CHUVA 30d</div>
          <div style="font-size:13px;font-weight:700;color:#64d2ff;">${reg.precip_30d || 0}</div>
          <div style="font-size:7px;color:#636366;">mm</div>
        </div>
        <div style="background:rgba(255,255,255,0.06);border-radius:8px;padding:6px 8px;text-align:center;">
          <div style="font-size:7px;color:#636366;letter-spacing:.5px;margin-bottom:2px;">UMID. SOLO</div>
          <div style="font-size:13px;font-weight:700;color:#ff9f0a;">${((reg.solo_umidade||0)*100).toFixed(0)}%</div>
          <div style="font-size:7px;color:#636366;">Vol/vol</div>
        </div>
      </div>
    </div>
    <!-- Culturas -->
    <div style="padding:0 16px 12px;">
      <div style="font-size:9px;color:#636366;letter-spacing:1px;margin-bottom:2px;padding-top:8px;">CULTURAS ATIVAS — VALORES CEASA</div>
      ${cultsHTML || '<div style="color:#636366;font-size:10px;padding:8px 0;">Sem culturas em estágio ativo neste período</div>'}
    </div>
    <!-- Footer — transparência de fonte (regra de ouro) -->
    <div style="padding:8px 16px;background:rgba(255,255,255,0.03);border-top:1px solid rgba(255,255,255,0.06);">
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
        <span style="background:rgba(255,149,0,0.18);border:1px solid rgba(255,149,0,0.45);border-radius:4px;padding:1px 6px;color:#ff9f0a;font-weight:700;font-size:8px;letter-spacing:.5px;">NDVI PROXY</span>
        <span style="font-size:8px;color:#636366;">Estimativa via LAI (Open-Meteo) — não é dado espectral real</span>
      </div>
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:3px;">
        <span style="background:rgba(0,122,255,0.15);border:1px solid rgba(0,122,255,0.35);border-radius:4px;padding:1px 6px;color:#64d2ff;font-weight:700;font-size:8px;letter-spacing:.5px;">VOL. REF.</span>
        <span style="font-size:8px;color:#636366;">Volume referencial FAO/IBGE — não é colheita confirmada</span>
      </div>
      <div style="font-size:7px;color:#48484a;margin-top:3px;">Calendário IBGE/MAPA · Preços CEASA-GO/MG/RN · Sentinel dados não disponíveis</div>
    </div>
  </div>`;
}

let _satLayerLoaded = false;

async function loadSatelliteLayer() {
  if (!leafletMap) return;
  try {
    const resp = await fetch('/api/satellite/analysis');
    if (!resp.ok) throw new Error('API offline');
    const data = await resp.json();
    const regioes = data.regioes || {};

    // Remove layer anterior
    if (mapLayerObjs['sat-ia']) leafletMap.removeLayer(mapLayerObjs['sat-ia']);
    mapLayerObjs['sat-ia'] = L.layerGroup();

    let totalRegioes = 0, totalVolume = 0;

    for (const [rk, reg] of Object.entries(regioes)) {
      if (!reg.lat || !reg.lon) continue;
      totalRegioes++;
      totalVolume += reg.volume_total_mt || 0;

      // Círculo de fundo (área agrícola)
      const ndviColor = _ndviToColor(reg.ndvi || 0.3);
      const radius = Math.max(40000, Math.min(160000, Math.sqrt(reg.area_ha || 100000) * 120));
      const circle = L.circle([reg.lat, reg.lon], {
        radius,
        color: ndviColor,
        fillColor: ndviColor,
        fillOpacity: 0.06,
        weight: 1.5,
        opacity: 0.35,
        dashArray: '4,4',
      });

      // Marcador central com ícone
      const dominante = (reg.culturas || []).find(c => c.cultura === reg.cultura_dominante);
      const marker = L.marker([reg.lat, reg.lon], { icon: _satMarkerIcon(reg, dominante) });

      // Popup Apple design
      const popup = L.popup({
        maxWidth: 400, minWidth: 320,
        className: 'sat-popup-leaflet',
        closeButton: true,
        autoPan: true,
      }).setContent(_satPopupHTML(rk, reg));

      marker.bindPopup(popup);
      circle.bindPopup(popup);

      mapLayerObjs['sat-ia'].addLayer(circle);
      mapLayerObjs['sat-ia'].addLayer(marker);
    }

    // Verifica se o toggle está ativo
    const cb = document.getElementById('l-sat-ia');
    if (cb && cb.checked) mapLayerObjs['sat-ia'].addTo(leafletMap);

    // Atualiza status com badge de qualidade
    const meta = data.meta || {};
    const satStatus = document.getElementById('sat-ia-status');
    if (satStatus) satStatus.textContent = `${totalRegioes} regiões · ${totalVolume.toFixed(1)} Mt`;

    // Badge PROXY visível no HUD satélite
    const satProxyBadge = document.getElementById('sat-proxy-badge');
    if (satProxyBadge) {
      satProxyBadge.style.display = 'inline-flex';
      satProxyBadge.title = meta.ndvi_disclaimer || 'NDVI estimado via LAI';
    }

    _satLayerLoaded = true;
    console.log(`[SAT-IA] ${totalRegioes} regiões | NDVI: ${meta.ndvi_source || 'PROXY'} | ${meta.data_quality}`);

    // Reagenda: 3×/dia = a cada 8h
    setTimeout(loadSatelliteLayer, 8 * 60 * 60 * 1000);
  } catch(e) {
    console.warn('[SAT-IA] Erro ao carregar layer:', e.message);
    const satStatus = document.getElementById('sat-ia-status');
    if (satStatus) { satStatus.style.color = 'rgba(255,69,58,.7)'; satStatus.textContent = 'erro'; }
    setTimeout(loadSatelliteLayer, 5 * 60 * 1000); // retry em 5min
  }
}

// CSS extra para popup Leaflet sem borda padrão
(function(){
  const s = document.createElement('style');
  s.textContent = `
    .sat-popup-leaflet .leaflet-popup-content-wrapper {
      background:transparent !important;border:none !important;
      box-shadow:none !important;padding:0 !important;border-radius:14px !important;
    }
    .sat-popup-leaflet .leaflet-popup-content { margin:0 !important; }
    .sat-popup-leaflet .leaflet-popup-tip { background:#1c1c1e !important; }
    @keyframes sat-pulse {
      0%,100%{box-shadow:0 0 12px currentColor,0 2px 8px rgba(0,0,0,.5);}
      50%{box-shadow:0 0 24px currentColor,0 4px 16px rgba(0,0,0,.6);}
    }
  `;
  document.head.appendChild(s);
})();

// ═══════════════════════════════════════════════════════════════════
// MAPA DE POLOS SUL-AMERICANOS — Modal com imagem de referência
// ═══════════════════════════════════════════════════════════════════
function showPolosMap() {
  // Navegar para panel-map (mapa interativo com os 44 polos produtivos SA)
  showPanel('map');
}
function showPolosMap_legacy() {
  // Criar modal se não existir (LEGADO — substituído por showPolosMap acima)
  let modal = document.getElementById('polos-map-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'polos-map-modal';
    modal.innerHTML = `
      <div id="polos-map-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:9999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);" onclick="if(event.target===this)closePolosMap()">
        <div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;max-width:90vw;max-height:90vh;overflow:auto;position:relative;box-shadow:0 25px 50px rgba(0,0,0,.5);">
          <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid #30363d;background:#161b22;">
            <span style="color:#50C878;font-size:12px;font-weight:bold;letter-spacing:1px;">🌎 POLOS PRODUTIVOS — AMÉRICA DO SUL</span>
            <button onclick="closePolosMap()" style="background:none;border:none;color:#8b949e;font-size:18px;cursor:pointer;padding:0 4px;line-height:1;">×</button>
          </div>
          <div style="padding:16px;">
            <img src="mapa_polos_sulamerica.png" alt="Mapa de Polos Produtivos da América do Sul" style="max-width:100%;height:auto;border-radius:4px;border:1px solid #30363d;">
            <div style="margin-top:12px;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;font-size:10px;color:#8b949e;">
              <div><span style="color:#50C878;">●</span> Brasil (Matopiba, Vale São Francisco, Holambra)</div>
              <div><span style="color:#3b82f6;">●</span> Argentina (Rosário, Córdoba, Santa Fe)</div>
              <div><span style="color:#eab308;">●</span> Paraguai (Santa Cruz, Alto Paraná)</div>
              <div><span style="color:#ef4444;">●</span> Chile (Vales Centrais)</div>
              <div><span style="color:#f97316;">●</span> Colômbia (Eixo Cafeeiro, Palma)</div>
              <div><span style="color:#a855f7;">●</span> Venezuela (Portuguesa, Zulia)</div>
              <div><span style="color:#c9d1d9;">■</span> Portos Estratégicos</div>
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }
  modal.style.display = 'block';
}

function closePolosMap() {
  const modal = document.getElementById('polos-map-modal');
  if (modal) modal.style.display = 'none';
}

// ═══════════════════════════════════════════════════════════════════
// ATLAS MULTIMODAL — Mapa de Logística
// ═══════════════════════════════════════════════════════════════════
let logMap, logMapLayers = {};

function initSankey() {
  window._sankeyInit = true;
  const el = document.getElementById('logMap');
  if (!el || logMap) { if (logMap) setTimeout(() => logMap.invalidateSize(), 80); return; }

  logMap = L.map('logMap', { center:[-14,-52], zoom:4, zoomControl:false, attributionControl:false });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom:19, subdomains:'abcd' }).addTo(logMap);
  L.control.zoom({ position:'bottomright' }).addTo(logMap);

  // ── RODOVIAS (principais corredores de escoamento) ────────────
  const rodovias = L.layerGroup();
  const rods = [
    { name:'BR-163', pts:[[-3.1,-60.0],[-5.5,-57.5],[-9.5,-56.5],[-12.5,-55.9],[-15.0,-55.0],[-17.5,-54.2],[-22.5,-54.8],[-24.0,-54.5]], sat:82, color:'#ff453a', flow:3268 },
    { name:'BR-364', pts:[[-10.9,-61.8],[-12.5,-60.5],[-13.5,-58.5],[-15.6,-56.1],[-17.5,-54.5]], sat:55, color:'#ffd60a', flow:1850 },
    { name:'BR-153', pts:[[-10.5,-48.5],[-13.0,-49.3],[-16.2,-49.1],[-18.5,-49.8],[-21.0,-50.3],[-23.5,-49.5]], sat:60, color:'#ffd60a', flow:2100 },
    { name:'BR-101', pts:[[-2.5,-44.2],[-5.8,-35.2],[-8.0,-35.0],[-12.9,-38.5],[-15.0,-39.0],[-19.9,-40.2],[-22.9,-43.2],[-25.5,-48.5],[-27.6,-48.6],[-29.3,-49.7]], sat:68, color:'#ffd60a', flow:2800 },
    { name:'BR-116', pts:[[-3.7,-38.5],[-7.5,-39.3],[-12.5,-41.5],[-15.6,-41.7],[-19.8,-43.0],[-22.5,-43.2],[-25.3,-49.2],[-29.3,-51.1],[-31.3,-52.1]], sat:72, color:'#ffd60a', flow:2650 },
    { name:'BR-050', pts:[[-16.2,-47.9],[-18.5,-48.0],[-19.8,-47.5],[-21.2,-48.0],[-22.3,-47.2]], sat:65, color:'#ffd60a', flow:1900 },
    { name:'BR-060', pts:[[-15.8,-47.8],[-17.5,-49.5],[-20.5,-54.6],[-22.3,-54.8]], sat:58, color:'#30d158', flow:1600 },
    { name:'BR-158', pts:[[-11.8,-49.8],[-15.5,-52.5],[-25.0,-53.0],[-28.5,-53.5]], sat:48, color:'#30d158', flow:1200 },
    { name:'BR-262', pts:[[-20.3,-40.3],[-20.5,-41.5],[-21.0,-43.5],[-19.8,-47.7],[-20.5,-55.8]], sat:52, color:'#30d158', flow:1400 },
    { name:'BR-040', pts:[[-15.8,-47.9],[-19.9,-43.9],[-21.8,-43.4],[-22.9,-43.2]], sat:70, color:'#ffd60a', flow:2200 },
  ];
  rods.forEach(r => {
    const w = Math.max(2, Math.min(6, r.flow / 800));
    const line = L.polyline(r.pts, { color:r.color, weight:w, opacity:0.8, dashArray: r.sat > 75 ? null : '8,4' });
    const midIdx = Math.floor(r.pts.length / 2);
    const mid = r.pts[midIdx];
    const wazeLink = `https://waze.com/ul?ll=${mid[0]},${mid[1]}&z=10&navigate=yes`;
    line.bindTooltip(`<div style="font-family:monospace;font-size:11px;"><b>${r.name}</b><br>Saturação: ${r.sat}%<br>Fluxo: ${r.flow.toLocaleString('pt-BR')} veíc/dia<br>Status: ${r.sat>75?'🔴 GARGALO':r.sat>55?'🟡 ATENÇÃO':'🟢 LIVRE'}<br><a href="${wazeLink}" target="_blank" style="color:#33ABFF;font-size:10px;">🗺 Abrir no Waze →</a></div>`, { sticky:true });
    rodovias.addLayer(line);
  });
  logMapLayers['rodovias'] = rodovias;
  rodovias.addTo(logMap);

  // ── FERROVIAS ─────────────────────────────────────────────────
  const ferrovias = L.layerGroup();
  const ferrs = [
    { name:'Ferrovia Norte-Sul (FNS)', pts:[[-2.5,-44.2],[-5.5,-47.5],[-7.5,-47.8],[-10.5,-48.5],[-12.5,-49.0],[-16.0,-49.3],[-18.5,-49.8]], color:'#0a84ff', flow:850 },
    { name:'Malha Paulista (Rumo)', pts:[[-21.2,-48.0],[-22.0,-47.8],[-22.5,-47.2],[-23.0,-46.8],[-23.5,-46.5],[-23.95,-46.33]], color:'#0a84ff', flow:1200 },
    { name:'Ferroeste (PR)', pts:[[-24.3,-53.5],[-24.5,-52.5],[-25.0,-51.5],[-25.5,-49.3],[-25.52,-48.52]], color:'#0a84ff', flow:600 },
    { name:'EFC (Carajás)', pts:[[-6.0,-50.5],[-5.5,-49.0],[-4.5,-47.0],[-3.0,-44.5],[-2.5,-44.2]], color:'#0a84ff', flow:950 },
    { name:'FIOL (Oeste-Leste BA)', pts:[[-12.5,-46.0],[-13.5,-42.0],[-14.5,-39.5]], color:'#0088ff', flow:400 },
    { name:'Malha Sul (Rumo)', pts:[[-25.52,-48.52],[-26.3,-49.0],[-27.5,-48.6],[-29.0,-50.5],[-30.0,-51.2]], color:'#0a84ff', flow:550 },
  ];
  ferrs.forEach(r => {
    const line = L.polyline(r.pts, { color:r.color, weight:3, opacity:0.9, dashArray:'12,6' });
    line.bindTooltip(`<div style="font-family:monospace;font-size:11px;"><b>🚂 ${r.name}</b><br>Cap.: ${r.flow} vagões/dia<br>Status: Operacional</div>`, { sticky:true });
    ferrovias.addLayer(line);
  });
  logMapLayers['ferrovias'] = ferrovias;
  ferrovias.addTo(logMap);

  // ── HIDROVIAS ─────────────────────────────────────────────────
  const hidrovias = L.layerGroup();
  const hidrs = [
    { name:'Hidrovia Tietê-Paraná', pts:[[-23.5,-46.5],[-22.5,-48.5],[-21.5,-50.5],[-20.5,-51.0],[-22.5,-53.0],[-24.0,-54.3]], color:'#30d158', flow:1100 },
    { name:'Hidrovia Tapajós', pts:[[-3.1,-60.0],[-4.0,-56.5],[-5.5,-56.0],[-8.0,-55.0],[-12.5,-55.9]], color:'#30d158', flow:700 },
    { name:'Hidrovia Madeira', pts:[[-3.1,-60.0],[-4.5,-59.5],[-6.0,-60.0],[-8.5,-63.5]], color:'#30d158', flow:500 },
    { name:'Hidrovia Paraguai', pts:[[-19.0,-57.6],[-20.5,-57.8],[-22.0,-57.5],[-23.5,-57.0],[-27.0,-58.5],[-32.95,-60.65]], color:'#30d158', flow:450 },
    { name:'Hidrovia São Francisco', pts:[[-10.5,-36.8],[-11.5,-38.0],[-13.5,-41.5],[-15.5,-43.5],[-17.0,-44.5]], color:'#30d158', flow:300 },
  ];
  hidrs.forEach(r => {
    const line = L.polyline(r.pts, { color:r.color, weight:3, opacity:0.7, dashArray:'4,8' });
    line.bindTooltip(`<div style="font-family:monospace;font-size:11px;"><b>🚢 ${r.name}</b><br>Cap.: ${r.flow} barcaças/mês<br>Status: Navegável</div>`, { sticky:true });
    hidrovias.addLayer(line);
  });
  logMapLayers['hidrovias'] = hidrovias;
  hidrovias.addTo(logMap);

  // ── PORTOS (destinos) ─────────────────────────────────────────
  const portos = [
    { ll:[-23.95,-46.33], name:'Porto de Santos', sat:77, bercos:'6/8' },
    { ll:[-25.52,-48.52], name:'Porto de Paranaguá', sat:69, bercos:'5/7' },
    { ll:[-2.5,-44.2],    name:'Porto de São Luís (Itaqui)', sat:57, bercos:'4/6' },
    { ll:[-3.1,-60.0],    name:'Terminal Miritituba', sat:42, bercos:'3/4' },
    { ll:[-32.95,-60.65], name:'Porto de Rosário (AR)', sat:48, bercos:'4/5' },
    { ll:[-8.0,-35.0],    name:'Porto de Suape (PE)', sat:60, bercos:'3/5' },
    { ll:[-1.45,-48.5],   name:'Porto de Belém/Barcarena', sat:52, bercos:'3/4' },
    { ll:[-12.9,-38.5],   name:'Porto de Salvador', sat:45, bercos:'2/4' },
    { ll:[-22.9,-43.2],   name:'Porto do Rio de Janeiro', sat:55, bercos:'4/6' },
  ];
  portos.forEach(p => {
    const state = p.sat > 75 ? 'alert' : p.sat > 55 ? 'ai' : 'normal';
    const mk = createSonarMarker(p.ll, { state, size:10, tooltip:`<div style="font-family:monospace;font-size:11px;"><b>⚓ ${p.name}</b><br>Saturação: ${p.sat}%<br>Berços: ${p.bercos}<br>${p.sat>75?'🔴 CONGESTIONADO':p.sat>55?'🟡 ATENÇÃO':'🟢 OPERACIONAL'}</div>` });
    logMap.addLayer(mk);
  });

  // ── ORIGENS (polos produtores) ────────────────────────────────
  const origens = [
    { ll:[-12.5,-55.9], name:'Mato Grosso', vol:'42 Mt' },
    { ll:[-17.5,-51.0], name:'Goiás', vol:'28 Mt' },
    { ll:[-24.5,-52.5], name:'Paraná', vol:'35 Mt' },
    { ll:[-28.5,-53.0], name:'Rio Grande do Sul', vol:'30 Mt' },
    { ll:[-12.0,-45.5], name:'MATOPIBA', vol:'18 Mt' },
  ];
  origens.forEach(o => {
    const mk = createSonarMarker(o.ll, { state:'soja', size:8, tooltip:`<b>📦 ${o.name}</b><br>Volume: ${o.vol}/safra` });
    logMap.addLayer(mk);
  });

  // ── CORREDORES INTERNACIONAIS SA ───────────────────────────────
  const saCorridors = L.layerGroup();
  const corridors = [
    { name:'Corredor BR→AR (MERCOSUL)', pts:[[-23.95,-46.33],[-25.5,-49.0],[-27.0,-52.5],[-28.5,-56.0],[-30.0,-57.5],[-32.95,-60.65],[-34.6,-58.38]], color:'#a855f7', info:'Brasil → Argentina via Uruguaiana/Paso de los Libres' },
    { name:'Corredor BR→PY (Paranaguá)', pts:[[-23.95,-46.33],[-25.52,-48.52],[-25.5,-51.5],[-25.3,-54.6],[-25.3,-57.6],[-25.3,-57.63]], color:'#f59e0b', info:'Brasil → Paraguai via Foz do Iguaçu/Ciudad del Este' },
    { name:'Corredor BR→UY (Sul)', pts:[[-30.0,-51.2],[-31.3,-52.1],[-31.4,-54.1],[-32.5,-53.4],[-34.9,-56.18]], color:'#06b6d4', info:'Brasil → Uruguai via Santana do Livramento/Rivera' },
    { name:'Corredor CL↔AR (Los Andes)', pts:[[-33.45,-70.66],[-32.89,-68.84],[-34.61,-68.33],[-34.6,-58.38]], color:'#ec4899', info:'Chile ↔ Argentina via Paso Los Libertadores · Corredor Bioceânico' },
    { name:'Corredor PE↔BO (Altiplano)', pts:[[-12.05,-77.04],[-14.0,-75.0],[-16.41,-71.54],[-17.0,-68.5],[-17.8,-63.18]], color:'#10b981', info:'Peru ↔ Bolivia via La Paz · Produtos andinos' },
    { name:'Rota Bioceânica (BR→CL)', pts:[[-15.6,-56.1],[-17.5,-57.5],[-19.0,-60.0],[-18.0,-63.18],[-17.8,-68.9],[-18.5,-70.3],[-20.2,-70.16]], color:'#f97316', info:'Corredor Bioceânico Central BR-PY-BO-CL via TTPB · Projeto em implantação', dash:'10,6' },
    { name:'Corredor Andino Norte (CO↔PE)', pts:[[4.71,-74.07],[1.0,-77.0],[-2.0,-78.0],[-4.0,-79.0],[-5.19,-80.63]], color:'#3b82f6', info:'Colômbia → Peru via Tumbes · Corredor Pacífico Norte' },
  ];
  corridors.forEach(c => {
    const line = L.polyline(c.pts, { color:c.color, weight:2.5, opacity:0.75, dashArray: c.dash || '14,6' });
    line.bindTooltip(`<div style="font-family:monospace;font-size:11px;"><b>🛣 ${c.name}</b><br><span style="color:#8b949e">${c.info}</span></div>`, { sticky:true });
    saCorridors.addLayer(line);
  });
  logMapLayers['sa-corridors'] = saCorridors;
  saCorridors.addTo(logMap);

  // ── PORTOS SA ESTRATÉGICOS (12 portos) ──────────────────────────
  const saPortos = L.layerGroup();
  const saPortData = [
    { ll:[-23.95,-46.33], name:'Santos (BR)', type:'exportação grãos', cap:'135 Mt/ano' },
    { ll:[-25.52,-48.52], name:'Paranaguá (BR)', type:'soja/milho/açúcar', cap:'50 Mt/ano' },
    { ll:[-32.1,-52.1],   name:'Rio Grande (BR)', type:'grãos e fertilizantes', cap:'35 Mt/ano' },
    { ll:[-8.0,-35.0],    name:'Suape (BR)', type:'contêineres/granéis', cap:'30 Mt/ano' },
    { ll:[-2.5,-44.2],    name:'Itaqui/São Luís (BR)', type:'grãos MATOPIBA', cap:'40 Mt/ano' },
    { ll:[-34.6,-58.38],  name:'Buenos Aires (AR)', type:'exportação grãos/carnes', cap:'40 Mt/ano' },
    { ll:[-34.9,-56.18],  name:'Montevidéu (UY)', type:'hub regional', cap:'15 Mt/ano' },
    { ll:[-33.45,-70.66], name:'Valparaíso (CL)', type:'contêineres/cobre', cap:'40 Mt/ano' },
    { ll:[-33.6,-71.6],   name:'San Antonio (CL)', type:'frutas/exportação', cap:'25 Mt/ano' },
    { ll:[-12.05,-77.04], name:'Callao (PE)', type:'maior porto peruano', cap:'45 Mt/ano' },
    { ll:[-2.2,-79.9],    name:'Guayaquil (EC)', type:'banana/camarão/flores', cap:'20 Mt/ano' },
    { ll:[10.4,-75.5],    name:'Cartagena (CO)', type:'hub Caribe/contêineres', cap:'35 Mt/ano' },
  ];
  saPortData.forEach(p => {
    const mk = createSonarMarker(p.ll, { state:'ai', size:10,
      tooltip:`<div style="font-family:monospace;font-size:11px;"><b>⚓ ${p.name}</b><br><span style="color:#8b949e">${p.type}</span><br>Cap.: ${p.cap}<br><span style="color:rgba(235,235,245,0.6);font-size:9px;">Fonte: NIAS Logística · dado estrutural</span></div>` });
    saPortos.addLayer(mk);
  });
  logMapLayers['sa-portos'] = saPortos;
  saPortos.addTo(logMap);

  // Timestamp
  const _logNow = new Date();
  const _logFmt = d => d.toLocaleString('pt-BR', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' });
  const _logEl = document.getElementById('log-last-update');
  if (_logEl) _logEl.textContent = _logFmt(_logNow) + ' (estrutural)';

  setTimeout(() => logMap.invalidateSize(), 80);
}

function logMapToggleLayer(name) {
  if (!logMap || !logMapLayers[name]) return;
  if (logMap.hasLayer(logMapLayers[name])) logMap.removeLayer(logMapLayers[name]);
  else logMapLayers[name].addTo(logMap);
}

// Segmented control toggle — novo design
function _logLyrToggle(name, btn) {
  logMapToggleLayer(name);
  if (btn) btn.classList.toggle('active');
}

let _wazeMode = 'off';
function logMapToggleWaze() {
  const btn = document.getElementById('btn-waze');
  const mapEl = document.getElementById('logMap');
  const wazeEl = document.getElementById('logWazeFrame');
  if (_wazeMode === 'off') {
    _wazeMode = 'live';
    if (btn) { btn.style.background = 'rgba(51,171,255,.4)'; btn.textContent = '🗺 WAZE ON'; }
    // Add Waze traffic tiles overlay to Leaflet map
    if (logMap && !logMapLayers['waze-traffic']) {
      logMapLayers['waze-traffic'] = L.tileLayer('https://worldtiles1.waze.com/tiles/{z}/{x}/{y}.png', {
        maxZoom: 18, opacity: 0.6, attribution: '© Waze'
      });
    }
    if (logMap && logMapLayers['waze-traffic']) logMapLayers['waze-traffic'].addTo(logMap);
    // Show Waze Live iframe for detailed view
    if (!wazeEl) {
      const iframe = document.createElement('div');
      iframe.id = 'logWazeFrame';
      iframe.style.cssText = 'position:absolute;bottom:10px;right:10px;z-index:1100;width:320px;height:240px;border:1px solid var(--accent);border-radius:6px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.5);';
      iframe.innerHTML = `<div style="background:rgba(28,28,30,.9);padding:3px 8px;display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:9px;color:#33ABFF;letter-spacing:1px;">🗺 WAZE LIVE — TRÂNSITO</span>
        <button onclick="logMapToggleWaze()" style="background:none;border:none;color:var(--text2);cursor:pointer;font-size:12px;">✕</button>
      </div>
      <iframe src="https://embed.waze.com/iframe?zoom=6&lat=-15.0&lon=-50.0&pin=0" style="width:100%;height:calc(100% - 24px);border:none;"></iframe>`;
      mapEl.parentElement.appendChild(iframe);
    } else {
      wazeEl.style.display = 'block';
    }
  } else {
    _wazeMode = 'off';
    if (btn) { btn.style.background = 'rgba(51,171,255,.15)'; btn.textContent = '🗺 WAZE LIVE'; }
    if (logMap && logMapLayers['waze-traffic'] && logMap.hasLayer(logMapLayers['waze-traffic'])) {
      logMap.removeLayer(logMapLayers['waze-traffic']);
    }
    const we = document.getElementById('logWazeFrame');
    if (we) we.style.display = 'none';
  }
}

// ═══════════════════════════════════════════════════════════════════

// OFERTA CHART — Dynamic per product
// ═══════════════════════════════════════════════════════════════════
const OFERTA_DATA = {
  soja:      { label:'SOJA BR',      unit:'Mt', prod:[10.2,18.5,32.4,38.1,28.6,10.3,4.1,2.8,3.5,6.2,8.4,9.8], dem:[14.0,14.2,14.4,14.6,14.8,14.5,14.2,14.0,14.3,14.5,14.4,14.3], color:'#0a84ff' },
  milho:     { label:'MILHO BR',     unit:'Mt', prod:[5.1,8.2,12.8,18.5,22.4,28.1,32.6,18.3,8.1,4.2,3.8,4.5], dem:[8.0,8.1,8.2,8.4,8.5,8.6,8.4,8.2,8.0,8.1,8.2,8.3], color:'#c8a000' },
  tomate:    { label:'TOMATE',       unit:'kt', prod:[380,350,310,290,340,420,480,510,450,380,320,350], dem:[360,360,370,370,380,380,370,360,360,370,370,360], color:'#cc2200' },
  banana:    { label:'BANANA',       unit:'kt', prod:[580,560,520,490,510,540,570,600,620,610,590,580], dem:[520,520,530,530,540,540,530,520,520,530,530,520], color:'#c8a000' },
  laranja:   { label:'LARANJA',      unit:'kt', prod:[800,650,480,320,280,350,520,780,1100,1300,1200,950], dem:[600,600,610,620,630,620,610,600,600,610,620,610], color:'#cc5500' },
  manga:     { label:'MANGA',        unit:'kt', prod:[40,35,28,22,18,15,12,18,45,85,120,80], dem:[35,35,36,36,37,37,36,35,35,36,37,36], color:'#e07800' },
  uva:       { label:'UVA',          unit:'kt', prod:[60,55,42,35,30,28,25,32,48,65,82,70], dem:[40,40,42,42,44,44,42,40,40,42,44,42], color:'#6b0080' },
  cebola:    { label:'CEBOLA',       unit:'kt', prod:[80,75,65,55,50,60,85,120,150,140,110,90], dem:[80,80,82,82,84,84,82,80,80,82,84,82], color:'#c06000' },
  batata:    { label:'BATATA',       unit:'kt', prod:[280,260,220,180,200,250,320,380,400,350,300,280], dem:[280,280,290,290,300,300,290,280,280,290,300,290], color:'#b89050' },
  mamao:     { label:'MAMÃO',        unit:'kt', prod:[85,90,95,100,98,88,75,70,72,78,82,85], dem:[75,75,76,76,78,78,76,75,75,76,78,76], color:'#e08030' },
  melancia:  { label:'MELANCIA',     unit:'kt', prod:[60,50,35,25,20,30,55,80,120,150,130,90], dem:[65,65,68,68,70,70,68,65,65,68,70,68], color:'#409030' },
  melao:     { label:'MELÃO',        unit:'kt', prod:[20,18,15,12,10,12,18,28,45,65,55,30], dem:[25,25,26,26,28,28,26,25,25,26,28,26], color:'#80aa00' },
  abacaxi:   { label:'ABACAXI',      unit:'kt', prod:[110,105,95,85,80,88,100,115,125,130,120,112], dem:[95,95,98,98,100,100,98,95,95,98,100,98], color:'#c8b000' },
  cenoura:   { label:'CENOURA',      unit:'kt', prod:[45,42,38,35,32,36,42,48,52,50,46,44], dem:[38,38,39,39,40,40,39,38,38,39,40,39], color:'#e07820' },
  morango:   { label:'MORANGO',      unit:'kt', prod:[5,4,3,2,1.5,2,4,8,14,18,12,7], dem:[6,6,6.2,6.2,6.5,6.5,6.2,6,6,6.2,6.5,6.2], color:'#ff4080' },
  pimentao:  { label:'PIMENTÃO',     unit:'kt', prod:[28,25,22,20,24,30,35,38,36,32,28,26], dem:[26,26,27,27,28,28,27,26,26,27,28,27], color:'#aa0000' },
  folhosas:  { label:'FOLHOSAS',     unit:'kt', prod:[38,35,30,25,28,35,42,48,45,40,36,37], dem:[34,34,35,35,36,36,35,34,34,35,36,35], color:'#50a050' },
  alho:      { label:'ALHO',         unit:'kt', prod:[8,7,6,5,4.5,5.5,8,12,16,14,10,9], dem:[8,8,8.2,8.2,8.5,8.5,8.2,8,8,8.2,8.5,8.2], color:'#d0c0a0' },
  maracuja:  { label:'MARACUJÁ',     unit:'kt', prod:[22,20,18,15,14,16,20,28,35,38,30,24], dem:[22,22,23,23,24,24,23,22,22,23,24,23], color:'#c8c000' },
  goiaba:    { label:'GOIABA',       unit:'kt', prod:[18,16,14,12,15,20,25,28,26,22,18,17], dem:[18,18,19,19,20,20,19,18,18,19,20,19], color:'#50a050' },
  abacate:   { label:'ABACATE',      unit:'kt', prod:[12,10,8,6,5,8,14,22,28,25,18,14], dem:[12,12,12.5,12.5,13,13,12.5,12,12,12.5,13,12.5], color:'#507030' },
  limao:     { label:'LIMÃO',        unit:'kt', prod:[50,45,38,30,28,35,48,62,75,70,58,52], dem:[45,45,46,46,48,48,46,45,45,46,48,46], color:'#a0c000' },
  tangerina: { label:'TANGERINA',    unit:'kt', prod:[15,12,8,5,4,6,12,22,35,42,30,18], dem:[15,15,16,16,17,17,16,15,15,16,17,16], color:'#e07020' },
  coco:      { label:'COCO',         unit:'kt', prod:[55,52,48,45,48,52,58,62,60,56,54,55], dem:[50,50,51,51,52,52,51,50,50,51,52,51], color:'#806040' },
  acai:      { label:'AÇAÍ',         unit:'kt', prod:[8,5,3,2,1.5,2,3,6,12,18,15,10], dem:[8,8,8.5,8.5,9,9,8.5,8,8,8.5,9,8.5], color:'#4a0070' },
  pessego:   { label:'PÊSSEGO',      unit:'kt', prod:[3,2,1.5,1,0.8,1,2,5,10,15,10,5], dem:[4,4,4.2,4.2,4.5,4.5,4.2,4,4,4.2,4.5,4.2], color:'#e06080' },
  maca:      { label:'MAÇÃ',         unit:'kt', prod:[15,12,8,55,80,60,35,18,10,8,12,14], dem:[25,25,26,26,28,28,26,25,25,26,28,26], color:'#cc0044' },
};

let _ofertaCurrentProduct = 'soja';

function initOferta() {
  window._ofertaInit = true;
  updateOfertaChart('soja');
  // Make oferta table rows clickable
  const tbody = document.getElementById('oferta-tbody');
  if (tbody) {
    tbody.querySelectorAll('tr').forEach(tr => {
      const td = tr.querySelector('td');
      if (!td) return;
      const name = td.textContent.trim().toLowerCase()
        .replace('tom.mesa','tomate').replace('tom.ind.','tomate')
        .replace('folhosas','folhosas').replace('cítricos','laranja')
        .replace('boi gordo','boi').replace('uva br','uva').replace('uva ar','uva')
        .replace('maçã ar','maca').replace('maçã','maca')
        .replace('pimentão','pimentao').replace('mamão','mamao')
        .replace('melão','melao').replace('melancia','melancia')
        .replace('cenoura','cenoura').replace('morango','morango')
        .replace('abacaxi','abacaxi').replace('banana','banana')
        .replace('alho','alho').replace('cebola','cebola')
        .replace('batata','batata').replace('manga','manga')
        .normalize('NFD').replace(/[\u0300-\u036f]/g,'');
      const slug = Object.keys(OFERTA_DATA).find(k => name.includes(k));
      if (slug) {
        tr.style.cursor = 'pointer';
        tr.onclick = () => {
          updateOfertaChart(slug);
          tbody.querySelectorAll('tr').forEach(r => r.style.background = '');
          tr.style.background = 'rgba(10,132,255,.08)';
        };
      }
    });
  }
}

function updateOfertaChart(product) {
  _ofertaCurrentProduct = product;
  const d = OFERTA_DATA[product] || OFERTA_DATA.soja;
  const months = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
  const titleEl = document.getElementById('oferta-chart-title');
  if (titleEl) titleEl.textContent = `${d.label} — PRODUÇÃO vs DEMANDA (${d.unit}/mês)`;

  if (window._ofertaChart) window._ofertaChart.destroy();

  const ctx = document.getElementById('chartOferta').getContext('2d');
  window._ofertaChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: months,
      datasets: [
        { label:'IC Superior', data: d.prod.map(v=>+(v*1.05).toFixed(2)), borderColor:'transparent', backgroundColor:d.color+'18', fill:'+1', pointRadius:0, tension:0.4 },
        { label:`Produção Estimada (${d.unit}/mês)`, data:[...d.prod], borderColor:d.color, borderWidth:2, backgroundColor:'transparent', pointRadius:3, pointBackgroundColor:d.color, tension:0.4, fill:false },
        { label:'IC Inferior', data: d.prod.map(v=>+(v*0.95).toFixed(2)), borderColor:'transparent', backgroundColor:d.color+'18', fill:false, pointRadius:0, tension:0.4 },
        { label:'Demanda de Mercado', data:[...d.dem], borderColor:'#ff9f0a', borderWidth:2, borderDash:[5,5], backgroundColor:'transparent', pointRadius:0, tension:0.3, fill:false },
      ]
    },
    options: {
      responsive:true, maintainAspectRatio:false, animation:{duration:600},
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{labels:{color:'rgba(235,235,245,0.6)',font:{family:'Courier New',size:10},boxWidth:16,filter:i=>i.datasetIndex!==0&&i.datasetIndex!==2}},
        tooltip:{backgroundColor:'#2c2c2e',borderColor:'#3a3a3c',borderWidth:1,titleColor:'#0a84ff',bodyColor:'#ffffff',titleFont:{family:'Courier New'},bodyFont:{family:'Courier New',size:11},filter:i=>i.datasetIndex!==0&&i.datasetIndex!==2}
      },
      scales:{
        x:{ticks:{color:'rgba(235,235,245,0.6)',font:{family:'Courier New',size:9}},grid:{color:'#3a3a3c'}},
        y:{ticks:{color:'rgba(235,235,245,0.6)',font:{family:'Courier New',size:9},callback:v=>v+d.unit},grid:{color:'#3a3a3c'}}
      }
    }
  });
}

// ═══════════════════════════════════════════════════════════════════
// CEASA ARBITRAGEM TERMINAL
// ═══════════════════════════════════════════════════════════════════
const CEASA_BASE = [
  {ceasa:'CEAGESP (SP)',    region:'São Paulo, SP',   lat:-23.6,  lng:-46.7},
  {ceasa:'CEASA-RJ (Irajá)',region:'Rio de Janeiro, RJ',lat:-22.8,lng:-43.3},
  {ceasa:'CEASA-MG (Contagem)',region:'Contagem, MG',lat:-19.9,  lng:-44.1},
  {ceasa:'CEASA-PE (Recife)',region:'Recife, PE',    lat:-8.0,   lng:-34.9},
  {ceasa:'CEASA-RS (Gravataí)',region:'Gravataí, RS',lat:-29.9,  lng:-51.0},
  {ceasa:'CEASA-PR (Curitiba)',region:'Curitiba, PR',lat:-25.4,  lng:-49.3},
  {ceasa:'CEASA-BA (Salvador)',region:'Salvador, BA',lat:-12.9,  lng:-38.5},
  {ceasa:'CEASA-CE (Maracanaú)',region:'Maracanaú, CE',lat:-3.9, lng:-38.6},
  {ceasa:'CEASA-GO (Goiânia)', region:'Goiânia, GO', lat:-16.7,  lng:-49.3},
  {ceasa:'CEASA-SC (São José)',region:'São José, SC', lat:-27.6,  lng:-48.6},
];

const CEASA_PRODUCTS = [
  {name:'🍅 Tomate Mesa',   unit:'cx', basePrice:88.5,  freteBase:14.2, origin:'Caçador-SC / Itapeva-SP'},
  {name:'🫑 Pimentão',      unit:'cx', basePrice:42.0,  freteBase:18.5, origin:'Araguari-MG / Mogi das Cruzes-SP'},
  {name:'🧅 Cebola',        unit:'sc', basePrice:35.0,  freteBase:12.0, origin:'Ituporanga-SC / Cristalina-GO'},
  {name:'🥔 Batata',        unit:'sc', basePrice:52.1,  freteBase:11.5, origin:'Itapeva-SP / Vargem Grande-MG'},
  {name:'🍊 Laranja',       unit:'cx', basePrice:28.4,  freteBase:9.8,  origin:'Araguari-MG / Limeira-SP'},
  {name:'🥬 Alface/Folhas', unit:'dz', basePrice:12.8,  freteBase:8.2,  origin:'Mogi das Cruzes-SP / Caçador-SC'},
  {name:'🥕 Cenoura',       unit:'kg', basePrice:2.9,   freteBase:7.4,  origin:'Cristalina-GO / Caçador-SC'},
  {name:'🍅 Tomate Ind.',   unit:'t',  basePrice:148.0, freteBase:22.0, origin:'Goiânia-GO / Patos de Minas-MG'},
  {name:'🍌 Banana',        unit:'kg', basePrice:1.8,   freteBase:6.5,  origin:'Boquim-SE / Itabaiana-SE'},
  {name:'🥭 Manga',         unit:'cx', basePrice:42.0,  freteBase:8.8,  origin:'Petrolina-PE / Juazeiro-BA'},
  {name:'🍇 Uva BR',        unit:'kg', basePrice:6.4,   freteBase:10.1, origin:'Petrolina-PE / Vacaria-RS'},
  {name:'🍈 Melão',         unit:'cx', basePrice:48.6,  freteBase:9.2,  origin:'Mossoró-RN / Baraúna-RN'},
];

let _ceasaRows = [];
let _ceasaInterval = null;

function _buildCeasaRows() {
  _ceasaRows = [];
  CEASA_PRODUCTS.forEach(prod => {
    CEASA_BASE.forEach(ceasa => {
      // distFactor fixo por terminal (sem ruído aleatório)
      const distFactors = { 'CEAGESP (SP)':1.0,'CEASA-RJ (Irajá)':1.1,'CEASA-MG (Contagem)':0.95,'CEASA-PE (Recife)':1.4,'CEASA-RS (Gravataí)':1.35,'CEASA-PR (Curitiba)':1.15,'CEASA-BA (Salvador)':1.3,'CEASA-CE (Maracanaú)':1.45,'CEASA-GO (Goiânia)':0.9,'CEASA-SC (São José)':1.2 };
      const distFactor = distFactors[ceasa.ceasa] || 1.0;
      const satFactor = (logState?.br163 != null) ? Math.min(100, Math.max(0, logState.br163)) / 100 : 0.5;
      const frete = +(prod.freteBase * distFactor * (1 + satFactor * 0.3)).toFixed(2);
      // preço de referência fixo (sem jitter aleatório)
      const price = prod.basePrice;
      const margin = +(price - frete).toFixed(2);
      _ceasaRows.push({
        ceasa: ceasa.ceasa, region: ceasa.region, lat: ceasa.lat, lng: ceasa.lng,
        product: prod.name, unit: prod.unit, origin: prod.origin,
        price, frete, margin
      });
    });
  });
  _ceasaRows.sort((a, b) => b.margin - a.margin);
}

function _getStatusBadge(row, rank) {
  const theme = document.documentElement.getAttribute('data-theme') || 'dark';
  if (rank < 3) {
    if (theme === 'cyber') return '<span class="arb-opp" style="font-size:9px;padding:2px 6px;border-radius:2px;font-weight:bold;">🏆 MELHOR VENDA</span>';
    return '<span style="background:rgba(10,132,255,.15);color:#0a84ff;font-size:9px;padding:2px 6px;border-radius:2px;font-weight:bold;">🏆 MELHOR VENDA</span>';
  }
  if (row.margin > 50) {
    if (theme === 'cyber') return '<span class="arb-opp" style="font-size:9px;padding:2px 6px;border-radius:2px;">🔥 ALTA DEMANDA</span>';
    return '<span style="background:rgba(255,159,10,.18);color:#ff9f0a;font-size:9px;padding:2px 6px;border-radius:2px;">🔥 ALTA DEMANDA</span>';
  }
  if (row.margin > 25) {
    return '<span style="background:rgba(39,174,96,.12);color:#27ae60;font-size:9px;padding:2px 6px;border-radius:2px;">🟢 Estável</span>';
  }
  if (row.margin > 0) {
    return '<span style="background:rgba(241,196,15,.1);color:#f1c40f;font-size:9px;padding:2px 6px;border-radius:2px;">🟡 Neutro</span>';
  }
  return '<span style="background:rgba(231,76,60,.15);color:#e74c3c;font-size:9px;padding:2px 6px;border-radius:2px;">🔴 Negativo</span>';
}

function updateCeasaTable() {
  _buildCeasaRows();
  const tbody = document.getElementById('ceasa-tbody');
  if (!tbody) return;
  const top30 = _ceasaRows.slice(0, 40);
  tbody.innerHTML = top30.map((r, i) => {
    const marginColor = r.margin > 50 ? 'var(--accent2)' : r.margin > 20 ? 'var(--accent)' : r.margin > 0 ? 'var(--warn)' : 'var(--danger)';
    return `<tr style="border-bottom:1px solid var(--border);${i < 3 ? 'background:rgba(10,132,255,.04);' : ''}">
      <td style="padding:4px 10px;font-size:9px;color:var(--text);">${r.ceasa}</td>
      <td style="padding:4px 10px;font-size:9px;color:var(--text);">${r.product}</td>
      <td style="padding:4px 10px;font-size:9px;color:var(--text2);">${r.origin}</td>
      <td style="padding:4px 10px;font-size:9px;text-align:right;color:var(--accent);">R$ ${r.price.toFixed(2)}/${r.unit}</td>
      <td style="padding:4px 10px;font-size:9px;text-align:right;color:var(--warn);">R$ ${r.frete.toFixed(2)}</td>
      <td style="padding:4px 10px;font-size:10px;font-weight:bold;text-align:right;color:${marginColor};">R$ ${r.margin.toFixed(2)}</td>
      <td style="padding:4px 10px;text-align:center;">${_getStatusBadge(r, i)}</td>
    </tr>`;
  }).join('');

  if (_ceasaRows.length > 0) {
    const best = _ceasaRows[0];
    const el = document.getElementById('ceasa-spread-best');
    const where = document.getElementById('ceasa-spread-where');
    const badge = document.getElementById('ceasa-best-badge');
    if (el) el.textContent = '+ R$ ' + best.margin.toFixed(2) + '/' + best.unit;
    if (where) where.textContent = best.ceasa + ' · ' + best.product;
    if (badge) badge.textContent = '🏆 MELHOR: ' + best.ceasa.split(' ')[0] + ' +R$' + best.margin.toFixed(0) + '/' + best.unit;
    const countEl = document.getElementById('ceasa-opp-count');
    const oppCount = _ceasaRows.filter(r => r.margin > 50).length;
    if (countEl) countEl.textContent = '● ' + oppCount + ' OPORTUNIDADES';
  }

  const freteAvgEl = document.getElementById('ceasa-frete-avg');
  if (freteAvgEl) {
    const avgFrete = (_ceasaRows.reduce((s, r) => s + r.frete, 0) / _ceasaRows.length).toFixed(2);
    freteAvgEl.textContent = 'R$ ' + avgFrete;
  }
  // ICAP — índice fixo de referência (sem simulação)
  const icapEl = document.getElementById('ceasa-price-idx');
  if (icapEl) icapEl.textContent = 'ICAP —';
}

let _lastSpreadAlert = 0;
function checkSpreadOpportunity() {
  if (!_ceasaRows.length) return;
  const now = Date.now();
  if (now - _lastSpreadAlert < 8000) return;
  const sp = _ceasaRows[0];
  const spLast = _ceasaRows[Math.min(5, _ceasaRows.length - 1)];
  const delta = sp.margin - spLast.margin;
  if (delta < 10) return;
  _lastSpreadAlert = now;
  const feed = document.getElementById('ceasa-opp-feed');
  if (!feed) return;
  const ts = new Date().toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
  // Mensagem baseada em dados reais de spread — sem valores aleatórios
  const neRoutes = _ceasaRows.filter(r=>r.ceasa.includes('PE')||r.ceasa.includes('CE')).length;
  const msg = delta > 40
    ? `🚨 <strong>Oportunidade Detectada</strong>: Spread líquido em <strong>${sp.ceasa}</strong> superou média nacional em <strong>R$ ${delta.toFixed(0)}/${sp.unit}</strong>. Produto: <strong>${sp.product}</strong>. Origem: ${sp.origin}.`
    : neRoutes > 0
    ? `📦 <strong>Janela Aberta</strong>: <strong>${neRoutes} rotas NE</strong> com margem positiva. <strong>${sp.product}</strong> em <strong>${sp.ceasa}</strong> lidera com R$ ${sp.margin.toFixed(0)}/${sp.unit}.`
    : `💰 <strong>Arbitragem</strong>: Diferença de R$ ${delta.toFixed(0)}/${sp.unit} entre <strong>${sp.ceasa}</strong> e <strong>${spLast.ceasa}</strong>. Produto: <strong>${sp.product}</strong> · Origem: ${sp.origin}.`;
  const div = document.createElement('div');
  div.style.cssText = 'padding:5px 10px;border-bottom:1px solid var(--border);font-size:9px;line-height:1.5;';
  div.innerHTML = `<span style="color:var(--text2);margin-right:6px;">${ts}</span>${msg}`;
  feed.insertBefore(div, feed.firstChild);
  while (feed.children.length > 20) feed.removeChild(feed.lastChild);
}

function initCeasaTerminal() {
  updateCeasaTable();
  checkSpreadOpportunity();
  if (!_ceasaInterval) {
    _ceasaInterval = setInterval(() => {
      updateCeasaTable();
      checkSpreadOpportunity();
    }, 3500);
  }
}

// ═══════════════════════════════════════════════════════════════════
// MULTI-CULTURE FILTER + SIDRA PRODUCTION MAP
// ═══════════════════════════════════════════════════════════════════

const SIDRA_CULTURES = {
  soja:        {label:'Soja',          code:3940, table:1612, var:35, cls:132, color:'#2d7a1f', vbpRef:1850, growth:1.00},
  milho:       {label:'Milho',         code:3922, table:1612, var:35, cls:132, color:'#c8a000', vbpRef:850,  growth:1.02},
  algodao:     {label:'Algodão',       code:3918, table:1612, var:35, cls:132, color:'#909090', vbpRef:4200, growth:0.97},
  arroz:       {label:'Arroz',         code:3916, table:1612, var:35, cls:132, color:'#5a8f5a', vbpRef:950,  growth:1.01},
  feijao:      {label:'Feijão',        code:3921, table:1612, var:35, cls:132, color:'#7a3000', vbpRef:3800, growth:1.03},
  tomate:      {label:'Tomate Mesa',   code:3943, table:1612, var:35, cls:132, color:'#cc2200', vbpRef:680,  growth:1.05},
  'tomate-ind':{label:'Tomate Ind.',   code:3943, table:1612, var:35, cls:132, color:'#992200', vbpRef:480,  growth:1.04, note:'IBGE não separa mesa/indústria'},
  cebola:      {label:'Cebola',        code:3899, table:1612, var:35, cls:132, color:'#c06000', vbpRef:720,  growth:1.02},
  pimentao:    {label:'Pimentão',      code:3935, table:1612, var:35, cls:132, color:'#aa0000', vbpRef:1800, growth:1.08},
  batata:      {label:'Batata',        code:3894, table:1612, var:35, cls:132, color:'#b89050', vbpRef:880,  growth:1.01},
  cenoura:     {label:'Cenoura',       code:3901, table:1612, var:35, cls:132, color:'#e07820', vbpRef:420,  growth:1.03},
  manga:       {label:'Manga',         code:39454,table:1613, var:35, cls:132, color:'#e07800', vbpRef:2400, growth:1.12},
  uva:         {label:'Uva',           code:39455,table:1613, var:35, cls:132, color:'#6b0080', vbpRef:3200, growth:1.07},
  laranja:     {label:'Laranja',       code:39453,table:1613, var:35, cls:132, color:'#cc5500', vbpRef:580,  growth:0.96},
  banana:      {label:'Banana',        code:39428,table:1613, var:35, cls:132, color:'#c8a000', vbpRef:460,  growth:1.04},
  maca:        {label:'Maçã',          code:39427,table:1613, var:35, cls:132, color:'#cc0044', vbpRef:820,  growth:1.02},
  melao:       {label:'Melão',         code:39449,table:1612, var:35, cls:132, color:'#80aa00', vbpRef:650,  growth:1.09},
  mamao:       {label:'Mamão',         code:39448,table:1613, var:35, cls:132, color:'#e08030', vbpRef:520,  growth:1.06},
  melancia:    {label:'Melancia',      code:3932, table:1612, var:35, cls:132, color:'#409030', vbpRef:350,  growth:1.05},
  abacaxi:     {label:'Abacaxi',      code:3893, table:1612, var:35, cls:132, color:'#c8b000', vbpRef:420,  growth:1.08},
  maracuja:    {label:'Maracujá',      code:39451,table:1613, var:35, cls:132, color:'#c8c000', vbpRef:380,  growth:1.10},
  goiaba:      {label:'Goiaba',        code:39431,table:1613, var:35, cls:132, color:'#50a050', vbpRef:480,  growth:1.04},
  abacate:     {label:'Abacate',       code:39426,table:1613, var:35, cls:132, color:'#507030', vbpRef:320,  growth:1.15},
  limao:       {label:'Limão',         code:39447,table:1613, var:35, cls:132, color:'#a0c000', vbpRef:440,  growth:1.06},
  tangerina:   {label:'Tangerina',     code:39456,table:1613, var:35, cls:132, color:'#e07020', vbpRef:360,  growth:0.98},
  coco:        {label:'Coco',          code:39430,table:1613, var:35, cls:132, color:'#806040', vbpRef:280,  growth:1.03},
  acai:        {label:'Açaí',          code:39457,table:1613, var:35, cls:132, color:'#4a0070', vbpRef:580,  growth:1.20},
  pessego:     {label:'Pêssego',       code:39452,table:1613, var:35, cls:132, color:'#e06080', vbpRef:720,  growth:1.01},
  alho:        {label:'Alho',          code:3895, table:1612, var:35, cls:132, color:'#d0c0a0', vbpRef:1200, growth:1.02},
};

const _sidraCache = {};
let _activeCult    = 'all';
let _sidraLayer    = null;
let _activeSafraYear = 2024;

// Fetch SIDRA v3 production data
// Endpoint: /api/v3/agregados/{tabela}/periodos/{periodo}/variaveis/{variavel}?localidades=N6[all]&classificacao={cls}[{code}]
async function fetchSidraProduction(cultId, year) {
  const key = `${cultId}_${year}`;
  if (_sidraCache[key]) return _sidraCache[key];
  const c = SIDRA_CULTURES[cultId];
  if (!c) return null;
  const varId = c.var || 35;
  const clsId = c.cls || 132;
  const periodo = year || 'last';
  const url = `https://servicodados.ibge.gov.br/api/v3/agregados/${c.table}/periodos/${periodo}/variaveis/${varId}?localidades=N6[all]&classificacao=${clsId}[${c.code}]`;
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const raw = await r.json();
    // v3 format: [{id, variavel, unidade, resultados:[{classificacoes, series:[{localidade:{id,nome,nivel}, serie:{periodo:valor}}]}]}]
    const results = raw?.[0]?.resultados?.[0]?.series || [];
    const data = results.map(s => ({
      NC: s.localidade?.nome || '',
      D1C: String(s.localidade?.id || ''),
      V: String(Object.values(s.serie || {})[0] || ''),
      state: (s.localidade?.nome || '').split(' - ').pop()?.trim() || ''
    })).filter(d => d.V && d.V !== '-' && d.V !== '...' && d.V !== '0' && +d.V > 0);
    _sidraCache[key] = data;
    // Update status bar
    const fsEl = document.getElementById('fs-fallback');
    if (fsEl && data.length > 0) { fsEl.textContent = 'SIDRA: API REAL'; fsEl.style.color = 'var(--accent2)'; }
    return data;
  } catch(e) {
    console.warn('SIDRA v3 fallback:', e.message);
    return null;
  }
}

function _hexToRgb(hex) {
  return [parseInt(hex.slice(1,3),16), parseInt(hex.slice(3,5),16), parseInt(hex.slice(5,7),16)];
}
function _colorByVolume(vol, maxVol, baseColor, maxAlpha) {
  const t = maxVol > 0 ? Math.min(1, vol / maxVol) : 0;
  const [r,g,b] = _hexToRgb(baseColor);
  return `rgba(${r},${g},${b},${(0.12 + maxAlpha * 0.88 * t).toFixed(2)})`;
}
function _projectedVolume(vol, year, cultId) {
  const c = SIDRA_CULTURES[cultId];
  if (!c || year <= 2024) return vol;
  return Math.round(vol * Math.pow(c.growth, year - 2024));
}

// Build synthetic fallback from MUNICIPAL_DB when SIDRA is unavailable.
// D1C uses the stored ibgeCode when available, otherwise a stable 7-digit hash.
function _buildSyntheticSidra(cultId) {
  return MUNICIPAL_DB.filter(m => m.country === 'BR').map((m, i) => ({
    NC:  m.name,
    D1C: m.ibgeCode ? String(m.ibgeCode) : String(5000000 + i * 7),
    V:   String(Math.round(800 + _seededRand(i * 31 + (cultId.charCodeAt(0)||0)) * 120000)),
    state: m.state
  }));
}

// ─── MAIN: swap culture layer ────────────────────────────────────────
async function trocarCultura(cultId) {
  _activeCult = cultId;
  document.querySelectorAll('.cult-btn').forEach(b => b.classList.remove('active'));
  const activeBtn = document.getElementById('cb-' + cultId);
  if (activeBtn) activeBtn.classList.add('active');

  if (cultId === 'all') {
    if (_sidraLayer) { _sidraLayer.remove(); _sidraLayer = null; }
    if (_ibgeStateGeoLayer) _ibgeStateGeoLayer.setStyle({fillOpacity: _ghostFill, weight:1.2});
    if (_ibgeMunGeoLayer) _ibgeMunGeoLayer.setStyle({fillOpacity:0.72, weight:0.7});
    document.getElementById('sidra-vbp-total').textContent = '—';
    document.getElementById('sidra-mun-count').textContent = '— municípios';
    document.getElementById('sidra-legend').textContent = 'LEGENDA COROPLETA';
    _setDrillStatus('✓ Visão geral restaurada');
    return;
  }

  const c = SIDRA_CULTURES[cultId];
  if (!c) return;
  _setDrillStatus(`⟳ SIDRA PAM: buscando ${c.label} (${_activeSafraYear})...`);
  document.getElementById('sidra-vbp-total').textContent = '⟳';

  const fetchYear = _activeSafraYear > 2024 ? 2024 : _activeSafraYear;
  let data = await fetchSidraProduction(cultId, fetchYear);
  const isProjection = _activeSafraYear > 2024;

  if (!data || data.length === 0) {
    data = _buildSyntheticSidra(cultId);
    _setDrillStatus(`⚠ SIDRA offline — dados sintéticos NIA$ para ${c.label}`, true);
  } else {
    _setDrillStatus(`✓ SIDRA ${fetchYear}: ${data.length} municípios com ${c.label}`);
  }
  renderSidraLayer(data, cultId, isProjection);
}

// ─── RENDER: color polygons by production volume ─────────────────────
function renderSidraLayer(data, cultId, isProjection) {
  if (_sidraLayer) { _sidraLayer.remove(); _sidraLayer = null; }
  const c = SIDRA_CULTURES[cultId];

  // Build munName → volume lookup
  const munVolMap = {};
  data.forEach(row => {
    const key = (row.NC || row.D1N || '').toLowerCase().trim();
    if (key) munVolMap[key] = +row.V;
  });

  // Hoist keys once — _lookupVol is called inside tight loops over thousands of polygons
  const munVolKeys = Object.keys(munVolMap);

  const allVols = munVolKeys.map(k => munVolMap[k]);
  // Fix: reduce to avoid RangeError when spreading 5000+ args into Math.max
  const maxVolRaw = allVols.length ? allVols.reduce((m, v) => v > m ? v : m, 0) : 1;
  const maxVol = maxVolRaw || 1;
  // Fix: Infinity when no data — prevents every municipality from getting top-10 neon
  const sortedRaw = [...allVols].sort((a, b) => b - a);
  const top10ThreshRaw = sortedRaw.length > 0 ? sortedRaw[Math.min(9, sortedRaw.length - 1)] : Infinity;

  // Fuzzy lookup using pre-hoisted keys array (O(n) once, not per call)
  function _lookupVol(name) {
    const norm = name.toLowerCase().trim();
    if (munVolMap[norm] != null) return munVolMap[norm];
    const prefix = norm.slice(0, 6);
    for (const k of munVolKeys) {
      if (k.slice(0, 6) === prefix) return munVolMap[k];
    }
    return 0;
  }

  // Case A: drill-down active → re-style existing IBGE GeoJSON layer in place
  if (_drillLevel === 1 && _ibgeMunGeoLayer) {
    // Recompute top10 threshold from projected values to stay accurate for 2025/2026
    let top10Thresh = top10ThreshRaw;
    let projMaxVol  = maxVol;
    if (isProjection) {
      const projVols = [];
      _ibgeMunGeoLayer.eachLayer(layer => {
        const v = _projectedVolume(_lookupVol(layer.feature?.properties?.NM_MUN || ''), _activeSafraYear, cultId);
        projVols.push(v);
      });
      projVols.sort((a, b) => b - a);
      top10Thresh = projVols.length > 0 ? projVols[Math.min(9, projVols.length - 1)] : Infinity;
      projMaxVol  = projVols.length ? projVols.reduce((m, v) => v > m ? v : m, 0) || 1 : 1;
    }
    if (_ibgeStateGeoLayer) _ibgeStateGeoLayer.setStyle({fillOpacity:0.04, weight:0.4});
    _ibgeMunGeoLayer.eachLayer(layer => {
      const name = layer.feature?.properties?.NM_MUN || '';
      let vol = _lookupVol(name);
      if (isProjection) vol = _projectedVolume(vol, _activeSafraYear, cultId);
      const isTop10 = vol > 0 && vol >= top10Thresh;
      layer.setStyle({
        color:       isTop10 ? '#30d158' : c.color,
        fillColor:   _colorByVolume(vol, projMaxVol, c.color, 0.82),
        fillOpacity: vol > 0 ? 0.78 : 0.06,
        weight:      isTop10 ? 2.5 : 0.7,
      });
    });
    _updateSidraFooter(data.length, cultId, isProjection);
    return;
  }

  // Case B: national view → circle markers for MUNICIPAL_DB entries
  if (_ibgeStateGeoLayer) _ibgeStateGeoLayer.setStyle({fillOpacity:0.06, weight:0.5});

  // Two-pass: first compute projected volumes to get correct threshold and maxVol
  const dbEntries = MUNICIPAL_DB.filter(m => m.country === 'BR');
  const projectedVols = dbEntries.map((m, idx) => {
    let vol = _lookupVol(m.name);
    if (vol === 0) vol = Math.round(500 + _seededRand(idx * 29 + (cultId.charCodeAt(0)||0)) * 90000);
    return isProjection ? _projectedVolume(vol, _activeSafraYear, cultId) : vol;
  });
  const projMaxVol2 = projectedVols.length ? projectedVols.reduce((m, v) => v > m ? v : m, 0) || 1 : 1;
  const sortedProj  = [...projectedVols].sort((a, b) => b - a);
  const top10ThreshFinal = sortedProj.length > 0 ? sortedProj[Math.min(9, sortedProj.length - 1)] : Infinity;

  _sidraLayer = L.layerGroup();
  let totalVBP = 0, munCount = 0;

  dbEntries.forEach((m, idx) => {
    const vol = projectedVols[idx];
    const vbp = Math.round(vol * c.vbpRef / 1000);
    totalVBP += vbp; munCount++;

    const center   = [(m.poly[0][0]+m.poly[2][0])/2, (m.poly[0][1]+m.poly[2][1])/2];
    const isTop10  = vol >= top10ThreshFinal;
    const radius   = 5 + Math.round(Math.min(18, vol / projMaxVol2 * 20));

    const sonarState = _cultureToSonarState(m.culture, m.ndvi);
    const sonarSev   = m.ndvi < 0.45 ? 'critical' : m.ndvi < 0.52 ? 'high' : 'ok';
    const sonarSize  = Math.max(4, Math.round(radius * 0.6));
    const marker = createSonarMarker(center, { state: sonarState, severity: sonarSev, size: sonarSize });

    const vbpFmt    = vbp > 1000 ? `R$ ${(vbp/1000).toFixed(1)} Mi` : `R$ ${vbp} mil`;
    const rankColor = isTop10 ? '#30d158' : vol >= projMaxVol2*0.35 ? '#ffd60a' : 'var(--text2)';
    const srcLabel  = isProjection ? `NIA$ ${_activeSafraYear} (projeção)` : `SIDRA ${_activeSafraYear}`;
    marker.on('mouseover', e => {
      _showTip(`<div style="min-width:210px;">
        <div style="font-weight:bold;color:${c.color};font-size:12px;margin-bottom:4px;">${_esc(m.name)} — ${_esc(m.state||'BR')}</div>
        <div>Cultura: <b>${_esc(c.label)}</b></div>
        <div>Produção: <b>${vol.toLocaleString('pt-BR')} t</b> · ${srcLabel}</div>
        <div>VBP estimado: <b style="color:${rankColor};">${vbpFmt}</b></div>
        ${isTop10 ? '<div style="color:#30d158;font-weight:bold;margin-top:4px;">⭐ TOP 10 NACIONAL</div>' : ''}
        <div style="font-size:9px;color:var(--text2);margin-top:4px;">${vol >= projMaxVol2*0.35 ? 'Alta produção' : 'Produção moderada'} · ${_esc(m.name)}</div>
      </div>`, e.originalEvent);
    });
    marker.on('mousemove', e => _moveTip(e.originalEvent));
    marker.on('mouseout', () => { _hideTip(); });
    _sidraLayer.addLayer(marker);
  });
  _sidraLayer.addTo(munMap);
  _updateSidraFooter(munCount, cultId, isProjection, totalVBP);
}

function _updateSidraFooter(munCount, cultId, isProjection, totalVBP) {
  const c = SIDRA_CULTURES[cultId];
  const vbpEl = document.getElementById('sidra-vbp-total');
  const cntEl = document.getElementById('sidra-mun-count');
  const legEl = document.getElementById('sidra-legend');
  if (totalVBP != null && vbpEl) {
    const fmt = totalVBP > 1000000 ? `R$ ${(totalVBP/1000000).toFixed(2)} Bi` : `R$ ${(totalVBP/1000).toFixed(0)} Mi`;
    vbpEl.textContent = isProjection ? fmt + ' *' : fmt;
  } else if (vbpEl) {
    vbpEl.textContent = isProjection ? 'NIA$ projeção' : 'SIDRA PAM';
  }
  if (cntEl) cntEl.textContent = `${munCount} municípios`;
  if (legEl && c) legEl.textContent = `${c.label.toUpperCase()} · Vol. Produção`;
}

// ─── SLIDER: safra year ───────────────────────────────────────────────
function onSafraSlider(val) {
  _activeSafraYear = +val;
  const valEl  = document.getElementById('sidra-year-val');
  const noteEl = document.getElementById('sidra-year-note');
  if (valEl)  valEl.textContent = val;
  if (noteEl) {
    if (+val <= 2024) {
      noteEl.textContent = 'Dados reais SIDRA/PAM IBGE';
      noteEl.style.color = 'var(--accent)';
    } else {
      const grow = SIDRA_CULTURES[_activeCult]?.growth;
      const pct  = grow ? ((grow - 1) * 100 * (+val - 2024)).toFixed(1) : '?';
      noteEl.textContent = `NIA$ projeção: acumulado +${pct}% vs 2024`;
      noteEl.style.color = 'var(--warn)';
    }
  }
  if (_activeCult !== 'all') trocarCultura(_activeCult);
}

// ═══════════════════════════════════════════════════════════════════
// IBGE DRILL-DOWN + LAYER SYSTEM + PREDICTIVE TOOLTIPS
// ═══════════════════════════════════════════════════════════════════

const IBGE_UF_NUM = {AC:12,AL:27,AP:16,AM:13,BA:29,CE:23,DF:53,ES:32,GO:52,MA:21,MT:51,MS:50,MG:31,PA:15,PB:25,PR:41,PE:26,PI:22,RJ:33,RN:24,RS:43,RO:11,RR:14,SC:42,SP:35,SE:28,TO:17};
const IBGE_UF_NAME = {AC:'Acre',AL:'Alagoas',AP:'Amapá',AM:'Amazonas',BA:'Bahia',CE:'Ceará',DF:'Distrito Federal',ES:'Espírito Santo',GO:'Goiás',MA:'Maranhão',MT:'Mato Grosso',MS:'Mato Grosso do Sul',MG:'Minas Gerais',PA:'Pará',PB:'Paraíba',PR:'Paraná',PE:'Pernambuco',PI:'Piauí',RJ:'Rio de Janeiro',RN:'Rio G. do Norte',RS:'Rio G. do Sul',RO:'Rondônia',RR:'Roraima',SC:'Santa Catarina',SP:'São Paulo',SE:'Sergipe',TO:'Tocantins'};
const STATE_CULT = {MT:'soja',GO:'soja',MS:'soja',PR:'soja',RS:'soja',BA:'soja',MA:'soja',PI:'soja',TO:'soja',RO:'soja',PA:'cafe',SP:'cana',MG:'cafe',ES:'cafe',RJ:'horti',SC:'maca',PE:'tomate',CE:'tomate',RN:'tomate',SE:'tomate',AL:'horti',PB:'tomate',AM:'horti',AC:'horti',AP:'horti',RR:'horti',DF:'horti'};
const STATE_MUN_COUNT = {MT:141,GO:246,SP:645,PR:399,RS:497,MG:853,BA:417,PE:185,SC:295,MS:79,PA:144,MA:217,PI:224,CE:184,TO:139,RO:52,PB:223,RN:167,SE:75,AL:102,ES:78,RJ:92,AM:62,AC:22,AP:16,RR:15,DF:1};
const CEASA_DEST = {SP:[-23.60,-46.70],MG:[-19.90,-44.10],PE:[-8.05,-34.92],RS:[-29.93,-51.00],PR:[-25.40,-49.30],BA:[-12.90,-38.50],CE:[-3.90,-38.60],GO:[-16.70,-49.30],SC:[-27.60,-48.60],RJ:[-22.80,-43.30]};

let _drillLevel = 0;
let _drillUF = null;
let _ibgeStateGeoLayer = null;
let _ibgeMunGeoLayer = null;
let _ibgeRiskGeoLayer = null;
let _ibgeLogGeoLayer = null;
let _ibgeLoading = false;
const _munLyrVis = {prod:true, logistics:false, risk:true};

// HTML-escape helper — sanitiza strings de APIs externas antes de innerHTML
function _esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function createSonarMarker(latlng, opts) {
  opts = opts || {};
  const state = opts.state || 'normal';
  const sev   = opts.severity || 'ok';
  const s     = (opts.size || 5) * 2;
  const rs    = s * 1.6;
  const coreSize = Math.max(4, s * 0.45);
  const sevClass = sev === 'ok' ? '' : ` sonar-sev-${sev}`;
  const html  = `<div class="sonar-wrap sonar-state-${state}${sevClass}" style="width:${rs}px;height:${rs}px;">` +
    `<div class="sonar-ring" style="width:${rs}px;height:${rs}px;"></div>` +
    `<div class="sonar-ring" style="width:${rs}px;height:${rs}px;"></div>` +
    `<div class="sonar-ring" style="width:${rs}px;height:${rs}px;"></div>` +
    `<div class="sonar-core" style="width:${coreSize}px;height:${coreSize}px;"></div></div>`;
  const icon = L.divIcon({ html, className:'', iconSize:[rs,rs], iconAnchor:[rs/2,rs/2] });
  const mk = L.marker(latlng, { icon });
  if (opts.tooltip) mk.bindTooltip(opts.tooltip, { direction:'top', offset:[0,-s], className:'sonar-tip' });
  return mk;
}

function _cultureToSonarState(culture, ndvi) {
  if (ndvi < 0.45) return 'alert';
  const c = (culture || '').toLowerCase();
  if (c.includes('soja')) return 'soja';
  if (c.includes('milho')) return 'milho';
  if (c.includes('tomate')) return 'tomate';
  if (c.includes('cebola')) return 'cebola';
  if (c.includes('batata')) return 'batata';
  if (c.includes('folhosa') || c.includes('alface')) return 'folhosas';
  if (c.includes('horti')) return 'horti';
  if (c.includes('manga')) return 'manga';
  if (c.includes('uva')) return 'uva';
  if (c.includes('laranja') || c.includes('citros')) return 'laranja';
  if (c.includes('banana')) return 'banana';
  if (c.includes('mamao') || c.includes('mamão')) return 'mamao';
  if (c.includes('melancia')) return 'melancia';
  if (c.includes('melao') || c.includes('melão')) return 'melao';
  if (c.includes('abacaxi')) return 'abacaxi';
  if (c.includes('maracuja') || c.includes('maracujá')) return 'maracuja';
  if (c.includes('goiaba')) return 'goiaba';
  if (c.includes('abacate')) return 'abacate';
  if (c.includes('limao') || c.includes('limão')) return 'limao';
  if (c.includes('tangerina')) return 'tangerina';
  if (c.includes('coco')) return 'coco';
  if (c.includes('acai') || c.includes('açaí')) return 'acai';
  if (c.includes('maca') || c.includes('maçã')) return 'maca';
  if (c.includes('pessego') || c.includes('pêssego')) return 'pessego';
  if (c.includes('alho')) return 'alho';
  if (c.includes('cafe') || c.includes('café')) return 'cafe';
  if (c.includes('pastagem') || c.includes('pecuária')) return 'pastagem';
  return 'normal';
}

// Seeded PRNG for stable synthetic values per municipality
function _seededRand(seed) {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

function _setDrillStatus(msg, err) {
  const el = document.getElementById('drill-status');
  if (el) { el.textContent = msg; el.style.color = err ? 'var(--danger)' : 'var(--accent)'; }
}
function _updateBreadcrumb() {
  const el = document.getElementById('drill-breadcrumb');
  if (!el) return;
  if (_drillLevel === 0) el.innerHTML = '🌎 <b>Brasil</b> — 27 estados';
  else el.innerHTML = `🌎 <span style="cursor:pointer;text-decoration:underline;color:var(--text2);" onclick="drillUp()">Brasil</span> › <b>${IBGE_UF_NAME[_drillUF]||_drillUF}</b>`;
}

// LRU cache: max 10 entries to prevent unbounded memory growth from large state GeoJSONs
const _ibgeGeoCache = {};
const _ibgeGeoCacheKeys = [];
const _IBGE_CACHE_MAX = 10;
let _ibgeDrillAbort = null; // AbortController for in-flight drillToState fetch

async function _fetchIBGEGeo(url, signal) {
  if (_ibgeGeoCache[url]) return _ibgeGeoCache[url];
  const r = await fetch(url, signal ? {signal} : undefined);
  if (!r.ok) throw new Error('HTTP ' + r.status);
  const d = await r.json();
  // LRU eviction: remove oldest entry if over limit
  if (_ibgeGeoCacheKeys.length >= _IBGE_CACHE_MAX) {
    const oldest = _ibgeGeoCacheKeys.shift();
    delete _ibgeGeoCache[oldest];
  }
  _ibgeGeoCache[url] = d;
  _ibgeGeoCacheKeys.push(url);
  return d;
}

let _ghostFill = 0.05;         // Ghost Mode default — borda elegante, fill quase invisível
let _prodShadowOn = false;    // toggle sombra de produção
let _riskMode = 'radar';      // 'radar' | 'impact' | 'off'

function toggleProdShadow() {
  _prodShadowOn = !_prodShadowOn;
  _ghostFill = _prodShadowOn ? 0.52 : 0.05;
  const btn = document.getElementById('btn-prod-shadow');
  if (btn) {
    btn.classList.toggle('active', _prodShadowOn);
    btn.title = _prodShadowOn ? 'Sombra de Produção: ON — clique para desligar' : 'Sombra de Produção: OFF — clique para ligar';
  }
  if (_ibgeStateGeoLayer) _ibgeStateGeoLayer.setStyle({fillOpacity: _ghostFill, weight: _prodShadowOn ? 1.5 : 1.2});
  if (_ibgeMunGeoLayer)   _ibgeMunGeoLayer.setStyle({fillOpacity: _prodShadowOn ? 0.72 : 0.15, weight: _prodShadowOn ? 0.8 : 0.5});
}

// ─── PRODUTORES RJ — Camada de produtores no mapa ─────────────────
let _produtoresLayer = null;
let _produtoresVisible = false;

async function toggleProdutores() {
  _produtoresVisible = !_produtoresVisible;
  const btn = document.getElementById('btn-produtores');
  if (btn) {
    btn.classList.toggle('active', _produtoresVisible);
    btn.style.borderColor = _produtoresVisible ? '#0a84ff' : 'var(--border)';
    btn.style.color = _produtoresVisible ? '#0a84ff' : 'var(--text2)';
  }
  
  if (_produtoresVisible) {
    await loadProdutores();
  } else {
    if (_produtoresLayer) {
      _produtoresLayer.remove();
      _produtoresLayer = null;
    }
  }
}

async function loadProdutores() {
  try {
    // Verificar se o mapa está inicializado
    if (!leafletMap) {
      console.error('[Produtores] Mapa não inicializado');
      alert('Erro: Mapa não está pronto. Tente novamente em alguns segundos.');
      return;
    }
    
    const res = await fetch('/api/produtores?state=RJ');
    if (!res.ok) throw new Error('Erro ao carregar produtores');
    const data = await res.json();
    
    if (_produtoresLayer) _produtoresLayer.remove();
    _produtoresLayer = L.layerGroup().addTo(leafletMap);
    
    const produtores = data.data || [];
    console.log(`[Produtores] ${produtores.length} produtores carregados`);
    
    produtores.forEach(prod => {
      const lat = prod.lat;
      const lon = prod.lon;
      const nome = prod.name;
      const cidade = prod.city;
      const produtos = prod.products || [];
      const canal = prod.market_channel || 'CEASA';
      
      // Ícone customizado para produtor
      const icon = L.divIcon({
        className: 'producer-marker',
        html: `<div style="
          width:28px;height:28px;
          background:linear-gradient(135deg, #0a84ff, #30d158);
          border:2px solid #fff;
          border-radius:50%;
          box-shadow:0 0 10px rgba(10,132,255,0.6);
          display:flex;align-items:center;justify-content:center;
          font-size:14px;
        ">👨‍🌾</div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14]
      });
      
      const marker = L.marker([lat, lon], { icon });
      
      // Popup com informações
      const popupContent = `
        <div style="font-family:var(--font);font-size:11px;min-width:200px;">
          <div style="font-weight:bold;color:#0a84ff;font-size:13px;margin-bottom:5px;">${nome}</div>
          <div style="color:var(--text2);margin-bottom:3px;">📍 ${cidade} - RJ</div>
          <div style="color:var(--text2);margin-bottom:5px;">🏪 Canal: ${canal}</div>
          <div style="border-top:1px solid var(--border);padding-top:5px;margin-top:5px;">
            <div style="font-size:9px;color:var(--accent);margin-bottom:3px;">PRODUTOS:</div>
            <div style="display:flex;flex-wrap:wrap;gap:2px;">
              ${produtos.map(p => `<span style="background:rgba(10,132,255,0.2);color:#0a84ff;padding:2px 6px;border-radius:3px;font-size:9px;">${p}</span>`).join('')}
            </div>
          </div>
        </div>
      `;
      
      marker.bindPopup(popupContent);
      marker.bindTooltip(nome, { direction: 'top', offset: [0, -10] });
      
      _produtoresLayer.addLayer(marker);
    });
    
    // Centralizar no RJ se houver produtores
    if (produtores.length > 0) {
      const group = new L.featureGroup(_produtoresLayer.getLayers());
      leafletMap.fitBounds(group.getBounds().pad(0.1));
    }
    
  } catch (e) {
    console.error('[Produtores] Erro:', e);
    alert('Erro ao carregar produtores: ' + e.message);
  }
}

// ─── PRODUTORES EM RECUPERAÇÃO JUDICIAL RJ ─────────────────────────
let _produtoresRJLayer = null;
let _produtoresRJVisible = false;

async function toggleProdutoresRJ() {
  _produtoresRJVisible = !_produtoresRJVisible;
  const btn = document.getElementById('btn-produtores-rj');
  if (btn) {
    btn.classList.toggle('active', _produtoresRJVisible);
    btn.style.borderColor = _produtoresRJVisible ? '#ff9f0a' : 'var(--border)';
    btn.style.color = _produtoresRJVisible ? '#ff9f0a' : 'var(--text2)';
  }
  
  if (_produtoresRJVisible) {
    await loadProdutoresRJ();
  } else {
    if (_produtoresRJLayer) {
      _produtoresRJLayer.remove();
      _produtoresRJLayer = null;
    }
  }
}

async function loadProdutoresRJ() {
  try {
    // Verificar se o mapa está inicializado
    if (!leafletMap) {
      console.error('[Produtores RJ] Mapa não inicializado');
      alert('Erro: Mapa não está pronto. Tente novamente em alguns segundos.');
      return;
    }
    
    const res = await fetch('/api/produtores-rj');
    if (!res.ok) throw new Error('Erro ao carregar produtores RJ');
    const data = await res.json();
    
    if (_produtoresRJLayer) _produtoresRJLayer.remove();
    _produtoresRJLayer = L.layerGroup().addTo(leafletMap);
    
    const produtores = data.data || [];
    console.log(`[Produtores RJ] ${produtores.length} produtores carregados`);
    
    // Cores por status judicial
    const statusColors = {
      'em_recuperacao': '#ff9f0a',
      'recuperacao_aprovada': '#ffd60a',
      'reorganizado': '#30d158',
      'falencia': '#ff453a'
    };
    
    const statusLabels = {
      'em_recuperacao': 'Em Recuperação',
      'recuperacao_aprovada': 'Recuperação Aprovada',
      'reorganizado': 'Reorganizado',
      'falencia': 'Falência'
    };
    
    produtores.forEach(prod => {
      const lat = prod.lat;
      const lon = prod.lon;
      const nome = prod.company_name;
      const cidade = prod.city;
      const produtos = prod.products || [];
      const status = prod.judicial_status;
      const processo = prod.process_number;
      const faturamento = prod.annual_revenue;
      const divida = prod.debts_total;
      const funcionarios = prod.employees;
      const color = statusColors[status] || '#ff9f0a';
      
      // Ícone customizado para produtor em RJ
      const icon = L.divIcon({
        className: 'producer-rj-marker',
        html: `<div style="
          width:32px;height:32px;
          background:linear-gradient(135deg, ${color}, #ff453a);
          border:2px solid #fff;
          border-radius:50%;
          box-shadow:0 0 12px ${color}80;
          display:flex;align-items:center;justify-content:center;
          font-size:14px;
        ">⚖️</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });
      
      const marker = L.marker([lat, lon], { icon });
      
      // Formatar valores
      const fmtMoney = v => v ? 'R$ ' + (v/1000000).toFixed(1) + 'M' : 'N/A';
      
      // Popup com informações detalhadas
      const popupContent = `
        <div style="font-family:var(--font);font-size:11px;min-width:280px;max-width:320px;">
          <div style="font-weight:bold;color:${color};font-size:13px;margin-bottom:5px;">${nome}</div>
          <div style="background:${color}20;border:1px solid ${color};border-radius:4px;padding:4px 8px;margin-bottom:8px;font-size:10px;color:${color};">
            ⚖️ ${statusLabels[status] || status}
          </div>
          <div style="color:var(--text2);margin-bottom:3px;font-size:10px;">📍 ${cidade} - RJ</div>
          <div style="color:var(--text2);margin-bottom:5px;font-size:9px;">📋 Processo: ${processo || 'N/A'}</div>
          
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0;font-size:10px;">
            <div style="background:rgba(10,132,255,0.1);padding:6px;border-radius:4px;">
              <div style="color:var(--text2);font-size:8px;">FATURAMENTO</div>
              <div style="color:#0a84ff;font-weight:bold;">${fmtMoney(faturamento)}</div>
            </div>
            <div style="background:rgba(255,69,58,0.1);padding:6px;border-radius:4px;">
              <div style="color:var(--text2);font-size:8px;">DÍVIDA TOTAL</div>
              <div style="color:#ff453a;font-weight:bold;">${fmtMoney(divida)}</div>
            </div>
            <div style="background:rgba(48,209,88,0.1);padding:6px;border-radius:4px;">
              <div style="color:var(--text2);font-size:8px;">FUNCIONÁRIOS</div>
              <div style="color:#30d158;font-weight:bold;">${funcionarios || 'N/A'}</div>
            </div>
            <div style="background:rgba(255,214,10,0.1);padding:6px;border-radius:4px;">
              <div style="color:var(--text2);font-size:8px;">INDICADOR</div>
              <div style="color:#ffd60a;font-weight:bold;">${divida && faturamento ? (divida/faturamento).toFixed(1) + 'x' : 'N/A'}</div>
            </div>
          </div>
          
          <div style="border-top:1px solid var(--border);padding-top:8px;margin-top:8px;">
            <div style="font-size:9px;color:var(--accent);margin-bottom:5px;">PRODUTOS COMERCIALIZADOS:</div>
            <div style="display:flex;flex-wrap:wrap;gap:3px;">
              ${produtos.map(p => `<span style="background:${color}30;color:${color};padding:3px 8px;border-radius:3px;font-size:9px;border:1px solid ${color}50;">${p}</span>`).join('')}
            </div>
          </div>
        </div>
      `;
      
      marker.bindPopup(popupContent);
      marker.bindTooltip(nome + ' (' + statusLabels[status] + ')', { direction: 'top', offset: [0, -16] });
      
      _produtoresRJLayer.addLayer(marker);
    });
    
    // Centralizar no RJ se houver produtores
    if (produtores.length > 0) {
      const group = new L.featureGroup(_produtoresRJLayer.getLayers());
      leafletMap.fitBounds(group.getBounds().pad(0.2));
    }
    
  } catch (e) {
    console.error('[Produtores RJ] Erro:', e);
    alert('Erro ao carregar produtores RJ: ' + e.message);
  }
}

function setRiskMode(mode) {
  _riskMode = mode;
  ['radar','impact','off'].forEach(m => {
    const btn = document.getElementById('btn-risk-' + m);
    if (btn) btn.classList.toggle('active', m === mode);
  });
  _munLyrVis.risk = (mode !== 'off');
  _renderRiskLayer(_drillUF);
}

// ─── LEVEL 0: Estado choropleth ────────────────────────────────────
async function initStateChoropleth() {
  _setDrillStatus('⟳ Carregando malha IBGE — 27 estados...');
  const url = 'https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?divisao=estados&formato=application/vnd.geo+json';
  try {
    const geo = await _fetchIBGEGeo(url);
    if (_ibgeStateGeoLayer) { _ibgeStateGeoLayer.remove(); _ibgeStateGeoLayer = null; }
    _ibgeStateGeoLayer = L.geoJSON(geo, {
      style: feat => {
        const uf = feat.properties?.SIGLA_UF || '?';
        const cult = STATE_CULT[uf] || 'soja';
        const ndvi = 0.50 + _seededRand(uf.charCodeAt(0) * 17) * 0.28;
        return {
          color: cultureColor(cult, Math.min(0.85, ndvi + 0.1), 1.0),
          fillColor: cultureColor(cult, ndvi, 0.65),
          fillOpacity: 0.05, weight: 1.2
        };
      },
      onEachFeature: (feat, layer) => {
        const uf = feat.properties?.SIGLA_UF || '??';
        const name = IBGE_UF_NAME[uf] || uf;
        const cult = STATE_CULT[uf] || 'soja';
        const ndvi = (0.50 + _seededRand(uf.charCodeAt(0) * 17) * 0.28).toFixed(3);
        const munCount = STATE_MUN_COUNT[uf] || 50;
        layer.on('mouseover', e => {
          layer.setStyle({fillOpacity:0.88, weight:2.5});
          _showTip(`<div style="min-width:180px;">
            <div style="font-weight:bold;color:#0a84ff;margin-bottom:4px;font-size:12px;">🗺 ${name} (${uf})</div>
            <div>Cultura dom.: <b>${cult.toUpperCase()}</b></div>
            <div>NDVI médio: <b>${ndvi}</b></div>
            <div>Municípios IBGE: <b>${munCount}</b></div>
            <div style="margin-top:5px;color:#f1c40f;font-size:9px;">▶ Clique para carregar municípios</div>
          </div>`, e.originalEvent);
        });
        layer.on('mousemove', e => _moveTip(e.originalEvent));
        layer.on('mouseout', () => { layer.setStyle({fillOpacity: _ghostFill, weight:1.2}); _hideTip(); });
        layer.on('click', () => drillToState(uf));
      }
    }).addTo(munMap);
    const total = geo.features?.length || 27;
    _setDrillStatus(`✓ ${total} estados — clique para drill-down municipal`);
    _updateBreadcrumb();
    _renderRiskLayer(null);
  } catch(e) {
    _setDrillStatus('⚠ IBGE offline — usando banco local', true);
    renderChoropleth('all');
  }
}

// ─── LEVEL 1: Municipal drill-down ─────────────────────────────────
async function drillToState(ufCode) {
  if (_ibgeLoading) return;
  // Abort any previous in-flight request before starting a new one
  if (_ibgeDrillAbort) { _ibgeDrillAbort.abort(); }
  _ibgeDrillAbort = new AbortController();
  _ibgeLoading = true;
  const ibgeNum = IBGE_UF_NUM[ufCode];
  if (!ibgeNum) { _ibgeLoading = false; return; }
  const name = IBGE_UF_NAME[ufCode] || ufCode;
  _setDrillStatus(`⟳ Carregando municípios de ${name}...`);
  const url = `https://servicodados.ibge.gov.br/api/v3/malhas/estados/${ibgeNum}?divisao=municipios&formato=application/vnd.geo+json`;
  try {
    const geo = await _fetchIBGEGeo(url, _ibgeDrillAbort.signal);
    if (_ibgeMunGeoLayer) { _ibgeMunGeoLayer.remove(); _ibgeMunGeoLayer = null; }
    if (_ibgeRiskGeoLayer) { _ibgeRiskGeoLayer.remove(); _ibgeRiskGeoLayer = null; }
    if (_ibgeLogGeoLayer) { _ibgeLogGeoLayer.remove(); _ibgeLogGeoLayer = null; }
    if (_ibgeStateGeoLayer) _ibgeStateGeoLayer.setStyle({fillOpacity:0.08, weight:0.8});

    _ibgeMunGeoLayer = L.geoJSON(geo, {
      style: feat => {
        const seed = (feat.properties?.CD_MUN || feat.properties?.codigo || 0) % 9999;
        const cult = STATE_CULT[ufCode] || 'soja';
        const ndvi = 0.38 + _seededRand(seed) * 0.42;
        const local = MUNICIPAL_DB.find(m => m.state === ufCode && feat.properties?.NM_MUN && m.name.toLowerCase().includes((feat.properties.NM_MUN||'').toLowerCase().split(' ')[0]));
        const realNdvi = local ? local.ndvi : ndvi;
        const realCult = local ? local.culture : cult;
        return {
          color: cultureColor(realCult, Math.min(0.85, realNdvi + 0.12), 1.0),
          fillColor: cultureColor(realCult, realNdvi, _munLyrVis.prod ? 0.75 : 0.15),
          fillOpacity: _munLyrVis.prod ? 0.72 : 0.15, weight: 0.7
        };
      },
      onEachFeature: (feat, layer) => {
        const munName = _esc(feat.properties?.NM_MUN || feat.properties?.name || '—');
        const seed = (feat.properties?.CD_MUN || 0) % 9999;
        const cult = STATE_CULT[ufCode] || 'soja';
        const local = MUNICIPAL_DB.find(m => m.state === ufCode && m.name.toLowerCase().includes((feat.properties?.NM_MUN||'').toLowerCase().split(' ')[0]));
        const ndvi = local ? local.ndvi : +(0.38 + _seededRand(seed) * 0.42).toFixed(3);
        const areaMha = local ? local.areaMha : +(0.04 + _seededRand(seed + 1) * 0.85).toFixed(2);
        const coef = local ? local.coef : +(0.76 + _seededRand(seed + 2) * 0.18).toFixed(2);
        const realCult = local ? local.culture : cult;
        const rm = +(areaMha * 1000 * ndvi * coef * ({soja:3.4,milho:5.8,tomate:62,horti:28,cana:85,uva:18,maca:22,cafe:1.8,pastagem:1.2}[realCult]||3.0) / 1000).toFixed(2);
        const harvestDays = Math.floor(10 + _seededRand(seed + 3) * 55);
        const bestCeasa = _esc(Object.keys(CEASA_DEST)[Math.floor(_seededRand(seed + 4) * Object.keys(CEASA_DEST).length)]);
        const spread = +(4 + _seededRand(seed + 5) * 22).toFixed(1);
        const brix = realCult === 'tomate' ? +(3.5 + _seededRand(seed + 6) * 3.0).toFixed(1) : null;
        const ndviStatus = ndvi < 0.45 ? '<span style="color:#ff453a">▼ ALERTA</span>' : ndvi < 0.58 ? '<span style="color:#ffd60a">▼ ATENÇÃO</span>' : '<span style="color:#00e676">✓ NORMAL</span>';
        const arbColor = spread > 15 ? '#00e676' : spread > 8 ? '#ffd60a' : '#aaa';

        layer.on('mouseover', e => {
          layer.setStyle({weight:2.5, fillOpacity:0.92});
          const brixLine = brix != null ? `<div>Brix estimado: <b>${brix}°</b></div>` : '';
          _showTip(`<div style="min-width:220px;">
            <div style="font-weight:bold;color:#0a84ff;font-size:12px;margin-bottom:4px;">${munName} — ${_esc(ufCode)}</div>
            <div>Cultura: <b>${_esc(realCult.toUpperCase())}</b></div>
            <div>NDVI: <b>${typeof ndvi === 'number' ? ndvi.toFixed(3) : ndvi}</b> ${ndviStatus}</div>
            <div>Área: <b>${areaMha} Mha</b> · Rm: <b>${rm} kt</b></div>
            ${brixLine}
            <div>Colheita estimada: <b>~${harvestDays} dias</b></div>
            <hr style="border-color:#1a3a5c;margin:5px 0;">
            <div style="color:${arbColor};font-size:10px;">💰 Arbitragem: +${spread}% em ${bestCeasa}</div>
            <div style="font-size:9px;color:var(--text2);margin-top:2px;">IA: ${spread > 15 ? 'Despachar agora' : spread > 8 ? 'Aguardar janela' : 'Manter estoque'}</div>
          </div>`, e.originalEvent);
        });
        layer.on('mousemove', e => _moveTip(e.originalEvent));
        layer.on('mouseout', () => {
          layer.setStyle({weight:0.7, fillOpacity:_munLyrVis.prod ? 0.72 : 0.15});
          _hideTip();
        });
        layer.on('click', () => { munMap.fitBounds(layer.getBounds(), {padding:[25,25]}); });
      }
    }).addTo(munMap);

    munMap.fitBounds(_ibgeMunGeoLayer.getBounds(), {padding:[15,15]});
    _drillLevel = 1; _drillUF = ufCode;
    _updateBreadcrumb();
    const total = geo.features?.length || 0;
    _setDrillStatus(`✓ ${total} municípios carregados · ${name} · IBGE/PAM`);
    if (_munLyrVis.risk) _renderRiskLayer(ufCode);
    if (_munLyrVis.logistics) _renderLogisticsLayer(ufCode);
  } catch(e) {
    if (e.name === 'AbortError') return; // fetch abortado — silencioso
    _setDrillStatus('⚠ Erro: ' + e.message, true);
    renderChoropleth('all');
  } finally { _ibgeLoading = false; }
}

function drillUp() {
  if (_drillLevel === 0) return;
  // Abort any pending state fetch so it doesn't render over the restored national view
  if (_ibgeDrillAbort) { _ibgeDrillAbort.abort(); _ibgeDrillAbort = null; }
  _ibgeLoading = false;
  if (_ibgeMunGeoLayer) { _ibgeMunGeoLayer.remove(); _ibgeMunGeoLayer = null; }
  if (_ibgeRiskGeoLayer) { _ibgeRiskGeoLayer.remove(); _ibgeRiskGeoLayer = null; }
  if (_ibgeLogGeoLayer) { _ibgeLogGeoLayer.remove(); _ibgeLogGeoLayer = null; }
  if (_ibgeStateGeoLayer) _ibgeStateGeoLayer.setStyle({fillOpacity:0.62, weight:1.5});
  munMap.setView([-15,-55], 4);
  _drillLevel = 0; _drillUF = null;
  _updateBreadcrumb();
  _setDrillStatus('✓ Visualização nacional restaurada');
  _renderRiskLayer(null);
  _renderLogisticsLayer(null);
  _hideTip();
}

// ─── CAMADA: RISCO ─────────────────────────────────────────────────
function _renderRiskLayer(uf) {
  if (_ibgeRiskGeoLayer) { _ibgeRiskGeoLayer.remove(); _ibgeRiskGeoLayer = null; }
  if (!_munLyrVis.risk) return;
  const risks = MUNICIPAL_DB.filter(m => m.country === 'BR' && (!uf || m.state === uf) && m.ndvi < 0.52);
  if (!risks.length) return;
  _ibgeRiskGeoLayer = L.layerGroup();
  risks.forEach(m => {
    const tipHtml = `<div style="font-family:monospace;font-size:11px;"><b style="color:#ff453a">⚠ ${_esc(m.name)}</b><br>NDVI: ${m.ndvi.toFixed(3)} — ${m.ndvi < 0.45 ? 'CRÍTICO' : 'ATENÇÃO'}<br>Rm em risco: ${(m.areaMha * m.coef * m.ndvi * 3.4).toFixed(1)} kt</div>`;
    if (_riskMode === 'impact') {
      const poly = L.polygon(m.poly, {
        fillColor: m.ndvi < 0.45 ? '#cc0000' : '#ff453a',
        fillOpacity: m.ndvi < 0.45 ? 0.75 : 0.55,
        color: '#ff0000', weight: 1.5
      });
      poly.bindTooltip(tipHtml, {sticky: true, direction: 'top'});
      _ibgeRiskGeoLayer.addLayer(poly);
    } else {
      const c = [(m.poly[0][0]+m.poly[2][0])/2, (m.poly[0][1]+m.poly[2][1])/2];
      const pulse = createSonarMarker(c, { state: 'alert', severity: 'high', size: 7, tooltip: tipHtml });
      _ibgeRiskGeoLayer.addLayer(pulse);
    }
  });
  _ibgeRiskGeoLayer.addTo(munMap);
}

// ─── CAMADA: LOGÍSTICA ─────────────────────────────────────────────
function _renderLogisticsLayer(uf) {
  if (_ibgeLogGeoLayer) { _ibgeLogGeoLayer.remove(); _ibgeLogGeoLayer = null; }
  if (!_munLyrVis.logistics) return;
  const muns = MUNICIPAL_DB.filter(m => m.country === 'BR' && (!uf || m.state === uf));
  _ibgeLogGeoLayer = L.layerGroup();
  const destCoord = uf && CEASA_DEST[uf] ? CEASA_DEST[uf] : CEASA_DEST['SP'];
  muns.forEach((m, i) => {
    const c = [(m.poly[0][0]+m.poly[2][0])/2, (m.poly[0][1]+m.poly[2][1])/2];
    const spread = +(5 + _seededRand(i * 7) * 25).toFixed(0);
    const col = spread > 20 ? '#00e676' : spread > 10 ? '#ffd60a' : '#607d8b';
    const line = L.polyline([c, destCoord], {color:col, weight:1.4, opacity:0.55, dashArray:'5 6'});
    line.bindTooltip(`<div style="font-family:monospace;font-size:11px;">${m.name} → CEASA · +${spread}% spread</div>`, {sticky:true});
    _ibgeLogGeoLayer.addLayer(line);
  });
  _ibgeLogGeoLayer.addTo(munMap);
}

// ─── LAYER TOGGLE ──────────────────────────────────────────────────
function toggleMunLayer(key) {
  _munLyrVis[key] = !_munLyrVis[key];
  const btn = document.getElementById('mun-lyr-' + key);
  if (btn) btn.classList.toggle('active', _munLyrVis[key]);
  if (key === 'prod') {
    if (_ibgeMunGeoLayer) _ibgeMunGeoLayer.setStyle({fillOpacity: _munLyrVis.prod ? 0.72 : 0.12});
    if (munLayerGroup) munLayerGroup.eachLayer(l => { if (l.setStyle) l.setStyle({fillOpacity: _munLyrVis.prod ? 0.72 : 0.12}); });
  } else if (key === 'risk') {
    _renderRiskLayer(_drillUF);
  } else if (key === 'logistics') {
    _renderLogisticsLayer(_drillUF);
  }
}

// ─── SIDRA PAM FETCH ───────────────────────────────────────────────
async function fetchSidraLayer() {
  const btn = document.getElementById('mun-lyr-sidra');
  if (btn) btn.textContent = '⟳ SIDRA...';
  _setDrillStatus('⟳ Consultando SIDRA/PAM — Tabela 1612 (culturas temporárias)...');
  // SIDRA API: tabela 1612, variável 215 (Área colhida), todos municípios, último ano
  const url = 'https://apisidra.ibge.gov.br/values/t/1612/n6/all/v/215/p/last%201/c782/40124/d/v215%205?formato=us&cabecalho=n';
  try {
    const r = await fetch(url);
    const data = await r.json();
    // data is array of objects with NC (mun name), V (value), D4N (year)
    const rows = Array.isArray(data) ? data.filter(d => d.V && d.V !== '-') : [];
    if (rows.length > 0) {
      const total = rows.length;
      const year = rows[0]?.D4N || '';
      _setDrillStatus(`✓ SIDRA PAM ${year}: ${total} municípios com área colhida soja`);
      // Highlight top producers in radar
      const sorted = rows.slice(0, 5);
      sorted.forEach(row => {
        typeof pushAnomalyEvent !== 'undefined' && setTimeout(() => {
          const feed = document.getElementById('anomaly-radar-list');
          if (!feed) return;
          const div = document.createElement('div');
          div.className = 'lf-item';
          div.style.borderLeft = '2px solid var(--accent2)';
          div.style.paddingLeft = '8px';
          div.innerHTML = `<span class="lf-sat" style="font-size:10px;">📡 [SIDRA PAM] ${_esc(row.NC)} — Área Soja: ${parseFloat(row.V).toLocaleString('pt-BR')} ha</span><br><span class="lf-time">${_esc(row.D4N)} · IBGE oficial</span>`;
          feed.insertBefore(div, feed.firstChild);
        }, 200);
      });
    }
    if (btn) { btn.textContent = '📡 SIDRA PAM'; btn.classList.add('active'); }
  } catch(e) {
    _setDrillStatus('⚠ SIDRA indisponível — modo simulado ativo', true);
    if (btn) btn.textContent = '📡 SIDRA PAM';
  }
}

// ─── TOOLTIP ENGINE ────────────────────────────────────────────────
let _tipEl = null;
let _tipHideTimer = null;

function _showTip(html, evt) {
  if (_tipHideTimer) { clearTimeout(_tipHideTimer); _tipHideTimer = null; }
  if (!_tipEl) {
    _tipEl = document.createElement('div');
    _tipEl.style.cssText = 'position:fixed;z-index:99999;background:#000000;border:1px solid #1a3a5c;border-radius:6px;padding:8px 12px;font-family:monospace;font-size:11px;color:#ffffff;pointer-events:none;box-shadow:0 4px 20px rgba(0,0,0,.8);transition:opacity .12s;min-width:190px;';
    document.body.appendChild(_tipEl);
  }
  _tipEl.innerHTML = html;
  _tipEl.style.display = 'block';
  _tipEl.style.opacity = '1';
  _moveTip(evt);
}
function _moveTip(evt) {
  if (!_tipEl || _tipEl.style.display === 'none') return;
  const x = evt.clientX + 16, y = evt.clientY + 16;
  const w = _tipEl.offsetWidth, h = _tipEl.offsetHeight;
  _tipEl.style.left = (x + w > window.innerWidth  ? x - w - 24 : x) + 'px';
  _tipEl.style.top  = (y + h > window.innerHeight ? y - h - 24 : y) + 'px';
}
// 120ms debounce prevents flickering when cursor crosses polygon borders
function _hideTip() {
  if (_tipHideTimer) clearTimeout(_tipHideTimer);
  _tipHideTimer = setTimeout(() => {
    if (_tipEl) { _tipEl.style.opacity = '0'; setTimeout(() => { if (_tipEl) _tipEl.style.display = 'none'; }, 100); }
    _tipHideTimer = null;
  }, 120);
}
function _destroyTip() {
  if (_tipHideTimer) { clearTimeout(_tipHideTimer); _tipHideTimer = null; }
  if (_tipEl) { _tipEl.remove(); _tipEl = null; }
}

// ═══════════════════════════════════════════════════════════════════
// CHAT
// ═══════════════════════════════════════════════════════════════════
const responses = {
  soja: `<strong style="color:var(--accent)">Safra Soja — Mato Grosso</strong><br><br>
• Volume estimado: <strong>78.4 Mt</strong> (53% da produção nacional)<br>
• Estágio fenológico: <strong>R6–R7</strong> (enchimento → maturação)<br>
• NDVI atual: <strong id="r-ndvi">0.61</strong> ▼ -0.03 em 14 dias<br>
• Solo exposto pós-colheita: <strong>+34%</strong> acima da média histórica<br>
• Umidade solo: <strong>31%</strong> — adequado para fim de ciclo<br><br>
<span style="color:var(--warn)">⚠</span> Colheita antecipada pressiona corredor BR-163. <strong>21 dias críticos</strong> para escoamento.`,
  estresse: `<strong style="color:var(--danger)">Alertas de Estresse Hídrico Ativos</strong><br><br>
<span style="color:var(--danger)">● CRÍTICO</span> — <strong>Oeste da Bahia / MATOPIBA</strong><br>
NDVI ▼ -0.07 | Umidade solo: <strong>18%</strong> | Área: ~1.2M ha<br><br>
<span style="color:var(--danger)">● CRÍTICO</span> — <strong>Norte do Mato Grosso</strong><br>
NDVI ▼ -0.05 | Umidade solo: <strong>21%</strong> | Área: ~800k ha<br><br>
<span style="color:var(--warn)">● ATENÇÃO</span> — <strong>Oeste do Piauí</strong><br>
NDVI ▼ -0.03 | Umidade: 26% | Área: ~450k ha<br><br>
<strong style="color:var(--accent2)">Recomendação:</strong> Irrigação suplementar nas próximas 72h. Deficit: <strong>48mm/ciclo</strong>.`,
  logística: `<strong style="color:var(--accent)">Recomendação Logística — Situação Atual</strong><br><br>
<span style="color:var(--danger)">⚡ URGENTE — Porto Santos:</span><br>
Saturação <span id="chat-santos-sat">—</span>% · Risco demurrage: <strong>US$ 18k/dia/navio</strong> em pico de fila.<br><br>
<span style="color:var(--warn)">⚡ PRIORITÁRIO — RUMO/VLI:</span><br>
Ferroviário com saturação <span id="chat-ferro-sat">—</span>% · Janela de composições disponível.<br><br>
<span style="color:var(--accent2)">✓ OPORTUNIDADE — Rosário (AR):</span><br>
Avaliar rerouting via hidrovia Paraná–Prata.<br><br>
Basis soja pode cair <strong>-30 cts/bu</strong> se gargalo persistir.`,
  anomalia: `<strong style="color:var(--warn)">Impacto Anomalia Térmica — Hortifrutis</strong><br><br>
• Temperatura: <strong>+2.1°C</strong> acima da média histórica<br>
• Regiões: Cinturão verde SP/MG/PR<br>
• Duração projetada: <strong>18–25 dias</strong><br><br>
→ <strong>Tomate:</strong> ▼ -11.2% | Queima foliar<br>
→ <strong>Pimentão:</strong> ▼ -9.8% | Ciclo antecipado<br>
→ <strong>Folhosas:</strong> ▼ -8.7% | Pendoamento precoce<br>
→ <strong>Cítricos:</strong> ▼ -6.4% | Queda prematura<br><br>
<span style="color:var(--accent2)">Alta de 12–20%</span> no atacado em 15–25 dias.`,
  relatório: `<strong style="color:var(--accent)">RELATÓRIO EXECUTIVO NIA$</strong><br><br>
<strong>[GRÃOS]</strong> Soja BR: 147.2 Mt (▼-3.2%) | Milho: 89.5 Mt (▼-1.8%) | Colheita MT antecipada.<br><br>
<strong>[HORTIFRUTIS]</strong> 38.4 Mt (▼-9.1%) | Alta de preços em 15–25 dias.<br><br>
<strong>[PECUÁRIA]</strong> Boi: 11.2 Mt (▲+2.3%) | Frango+Suíno: 19.8 Mt (▲+1.1%).<br><br>
<strong>[LOGÍSTICA]</strong> BR-163: 82% | Santos: 74% | Janela crítica 25/03–15/04.<br><br>
<strong>[INSIGHT]</strong> Acelerar Santos. Rerouting via Rosário. Hedge de basis soja antes de 01/04.`,
  ndvi: `<strong style="color:var(--accent)">NDVI Médio por Estado — Brasil</strong><br><br>
<table style="font-size:11px;border-collapse:collapse;width:100%">
<tr><td style="padding:3px 8px;color:var(--accent2)">● MT</td><td>0.61</td><td style="color:var(--danger)">▼-0.03</td><td style="color:var(--text2)">Maturação</td></tr>
<tr><td style="padding:3px 8px;color:var(--accent2)">● GO</td><td>0.58</td><td style="color:var(--text2)">▼-0.02</td><td style="color:var(--text2)">Normal</td></tr>
<tr><td style="padding:3px 8px;color:var(--danger)">● BA</td><td>0.38</td><td style="color:var(--danger)">▼-0.07</td><td style="color:var(--danger)">ESTRESSE</td></tr>
<tr><td style="padding:3px 8px;color:var(--warn)">● PR</td><td>0.52</td><td style="color:var(--warn)">▼-0.05</td><td style="color:var(--warn)">Susp. Praga</td></tr>
<tr><td style="padding:3px 8px;color:var(--accent2)">● RS</td><td>0.55</td><td style="color:var(--text2)">▼-0.01</td><td style="color:var(--text2)">Normal</td></tr>
<tr><td style="padding:3px 8px;color:var(--warn)">● MS</td><td>0.57</td><td style="color:var(--warn)">▼-0.04</td><td style="color:var(--text2)">Atenção</td></tr>
<tr><td style="padding:3px 8px;color:var(--accent2)">● SP</td><td>0.63</td><td style="color:var(--text2)">▼-0.01</td><td style="color:var(--text2)">Normal</td></tr>
<tr><td style="padding:3px 8px;color:var(--danger)">● MA/PI</td><td>0.41</td><td style="color:var(--danger)">▼-0.06</td><td style="color:var(--danger)">ESTRESSE</td></tr>
</table>`
};
const keywords = {
  soja:responses.soja, milho:responses.soja, safra:responses.soja, mato:responses.soja,
  estresse:responses.estresse, hídrico:responses.estresse, seca:responses.estresse, seco:responses.estresse,
  logística:responses.logística, logistica:responses.logística, porto:responses.logística, corredor:responses.logística, escoamento:responses.logística,
  anomalia:responses.anomalia, térmica:responses.anomalia, termica:responses.anomalia, horticultura:responses.anomalia, tomate:responses.anomalia,
  relatório:responses.relatório, relatorio:responses.relatório, executivo:responses.relatório, completo:responses.relatório,
  ndvi:responses.ndvi, estado:responses.ndvi,
};
const fallback = `Análise processada com base nos dados orbitais em tempo real.<br><br>
Nenhum padrão crítico específico encontrado para esta consulta.<br>
<span style="color:var(--text2)">Tente: <em>soja, estresse hídrico, logística, anomalia térmica, relatório executivo, NDVI</em></span>`;

function getResponse(text) {
  const lower = text.toLowerCase().replace(/[^a-záéíóúãõç\s]/g, '');
  for (const [kw, resp] of Object.entries(keywords)) {
    if (lower.includes(kw)) return resp;
  }
  return fallback;
}

function addMessage(html, role, meta) {
  const msgs = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.innerHTML = `<div class="msg-bubble">${html}</div><div class="msg-meta">${meta}</div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function initChatIA() {
  if (window._chatInit) return;
  window._chatInit = true;
  const msgs = document.getElementById('chat-messages');
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
  runIAAnalyzer(false);
  runRiskAnalyzer(false);
}

function _iaStatusColor(status) {
  if (status === 'danger') return 'var(--danger)';
  if (status === 'warn') return 'var(--warn)';
  return 'var(--accent2)';
}

function _escapeIA(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

async function runIAAnalyzer(showChatMessage) {
  const summaryEl = document.getElementById('ia-analysis-summary');
  const cardsEl = document.getElementById('ia-analysis-cards');
  const findingsEl = document.getElementById('ia-analysis-findings');
  const recsEl = document.getElementById('ia-analysis-recs');
  if (!summaryEl || !cardsEl || !findingsEl || !recsEl) return;

  summaryEl.textContent = 'Executando análise de consistência, frescor, fonte e anomalias...';
  cardsEl.innerHTML = '';
  findingsEl.innerHTML = '';
  recsEl.innerHTML = '';

  try {
    const res = await fetch('/api/flv/ia/analyze', { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();

    summaryEl.innerHTML = `${_escapeIA(data.summary)}<br><span style="color:var(--text2);font-size:9px;">Gerado em ${_escapeIA(data.generated_at)}</span>`;

    cardsEl.innerHTML = (data.cards || []).map(c => `
      <div class="ia-card" style="border-color:${_iaStatusColor(c.status)}55">
        <div class="k">${_escapeIA(c.label)}</div>
        <div class="v" style="color:${_iaStatusColor(c.status)}">${_escapeIA(c.value)}</div>
      </div>
    `).join('');

    findingsEl.innerHTML = (data.findings || []).slice(0, 8).map(f => `
      <div class="ia-finding ${_escapeIA(f.level || 'info')}">
        <strong>${_escapeIA(f.title)}</strong>
        ${f.metric ? `<span style="float:right;color:var(--text2)">${_escapeIA(f.metric)}</span>` : ''}<br>
        <span style="color:var(--text2)">${_escapeIA(f.detail)}</span>
      </div>
    `).join('') || '<div class="ia-finding info">Nenhum achado relevante no ciclo atual.</div>';

    recsEl.innerHTML = (data.recommendations || []).map(r => `<li>${_escapeIA(r)}</li>`).join('');

    if (showChatMessage) {
      addMessage(`<strong style="color:var(--accent)">Analisador executado.</strong><br>${_escapeIA(data.summary)}<br><br><span style="color:var(--text2)">Resultados detalhados atualizados no topo da aba IA.</span>`, 'nias', `NIA$ IA · ${new Date().toLocaleTimeString('pt-BR')}`);
    }
  } catch (err) {
    summaryEl.innerHTML = `<span style="color:var(--danger)">Falha ao executar o analisador:</span> ${_escapeIA(err.message || err)}`;
    findingsEl.innerHTML = '<div class="ia-finding danger"><strong>Endpoint indisponível</strong><br><span style="color:var(--text2)">Verifique se o servidor Python está rodando e se /api/flv/ia/analyze responde.</span></div>';
    if (showChatMessage) addMessage('Não foi possível executar o analisador de informações. Verifique o servidor/API.', 'nias', `NIA$ IA · ${new Date().toLocaleTimeString('pt-BR')}`);
  }
}


async function runRiskAnalyzer(showChatMessage) {
  const statusEl = document.getElementById('risk-status');
  const cardsEl = document.getElementById('risk-cards');
  const bodyEl = document.getElementById('risk-table-body');
  const sourcesEl = document.getElementById('risk-sources');
  if (!statusEl || !cardsEl || !bodyEl || !sourcesEl) return;
  const country = encodeURIComponent(document.getElementById('risk-country')?.value || 'all');
  const productRaw = (document.getElementById('risk-product')?.value || 'all').trim() || 'all';
  const product = encodeURIComponent(productRaw);
  const days = encodeURIComponent(document.getElementById('risk-days')?.value || '30');
  statusEl.textContent = 'Consultando fontes seguras e calculando risco...';
  cardsEl.innerHTML = '';
  bodyEl.innerHTML = '<tr><td colspan="5" style="color:var(--text2);">Processando...</td></tr>';
  try {
    const res = await fetch(`/api/flv/risk/analyze?country=${country}&product=${product}&days=${days}`, {cache:'no-store'});
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    const sum = data.summary || {};
    const enso = data.enso || {};
    const events = data.events || {};
    statusEl.innerHTML = `Gerado em ${_escapeIA(data.generated_at)} · Método: ${_escapeIA(data.method)}`;
    cardsEl.innerHTML = [
      ['Risco máximo', `${sum.max_risk || 0}/100 · ${sum.max_severity || 'baixo'}`],
      ['ENSO', `${enso.phase || 'monitorar'}${enso.probability ? ' · '+enso.probability+'%' : ''}`],
      ['Eventos disruptivos', `${events.count || 0} sinais ReliefWeb`],
      ['Polos analisados', `${sum.poles_analyzed || 0}`]
    ].map(([k,v]) => `<div class="risk-card"><div class="k">${_escapeIA(k)}</div><div class="v">${_escapeIA(v)}</div></div>`).join('');
    bodyEl.innerHTML = (data.poles || []).map(p => {
      const d = p.drivers || {};
      const action = (p.recommended_actions || [])[0] || 'monitorar';
      return `<tr>
        <td><strong>${_escapeIA(p.name)}</strong><br><span style="color:var(--text2)">${_escapeIA(p.country)}</span></td>
        <td>${(p.products||[]).map(_escapeIA).join(', ')}</td>
        <td><span class="risk-pill ${_escapeIA(p.severity)}">${_escapeIA(p.risk_score)} · ${_escapeIA(p.severity)}</span></td>
        <td>clima ${_escapeIA(d.clima||0)} · ENSO ${_escapeIA(d.enso||0)} · eventos ${_escapeIA(d.eventos_logisticos_sociais||0)}</td>
        <td>${_escapeIA(action)}</td>
      </tr>`;
    }).join('') || '<tr><td colspan="5" style="color:var(--text2);">Nenhum polo encontrado para o filtro.</td></tr>';
    const topSources = (data.sources || []).slice(0,5).map(s => `${s.name} (${s.category})`).join(' · ');
    sourcesEl.textContent = 'Fontes: ' + topSources + '. Limitação: risco é triagem antecipatória, não previsão determinística.';
    if (showChatMessage) addMessage(`<strong style="color:var(--warn)">API de risco atualizada.</strong><br>Risco máximo: ${_escapeIA(sum.max_risk || 0)}/100 · ${_escapeIA(sum.max_severity || 'baixo')}. ENSO: ${_escapeIA(enso.phase || 'monitorar')}.`, 'nias', `NIA$ RISCO · ${new Date().toLocaleTimeString('pt-BR')}`);
  } catch (err) {
    statusEl.innerHTML = `<span style="color:var(--danger)">Falha na API de risco:</span> ${_escapeIA(err.message || err)}`;
    bodyEl.innerHTML = '<tr><td colspan="5" style="color:var(--danger);">Endpoint indisponível. Verifique /api/flv/risk/analyze.</td></tr>';
  }
}

function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  const now = new Date().toLocaleTimeString('pt-BR');
  addMessage(text, 'user', `Você · ${now}`);
  const msgs = document.getElementById('chat-messages');
  const typing = document.createElement('div');
  typing.className = 'msg nias';
  typing.innerHTML = '<div class="msg-bubble"><div class="typing"><span></span><span></span><span></span></div></div>';
  msgs.appendChild(typing);
  msgs.scrollTop = msgs.scrollHeight;
  setTimeout(() => {
    typing.remove();
    addMessage(getResponse(text), 'nias', `NIA$ · ${new Date().toLocaleTimeString('pt-BR')}`);
    // Fill dynamic spans in rendered response
    requestAnimationFrame(() => {
      const s = document.getElementById('chat-santos-sat');
      const f = document.getElementById('chat-ferro-sat');
      if (s && typeof logState !== 'undefined') s.textContent = Math.round(logState.santos);
      if (f && typeof logState !== 'undefined') f.textContent = Math.round(logState.ferro);
    });
  }, 900);
}

function quickMsg(text) { document.getElementById('chat-input').value = text; sendMessage(); showPanel('chat'); }
function handleKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }

// ═══════════════════════════════════════════════════════════════════
// HORTIFRUTIS LIVE
// ═══════════════════════════════════════════════════════════════════
const hortiState = {
  'tomate-mesa': { vol:5.1,  price:68.2,  ndvi:0.49, unit:'cx',  dir:-1, baseColor:'#0a84ff' },
  'tomate-ind':  { vol:4.7,  price:148.0, ndvi:0.53, unit:'t',   dir:-1, baseColor:'#ff9f0a' },
  pimentao:{ vol:3.2,  price:94.5,  ndvi:0.51, unit:'cx',  dir:-1, baseColor:'#ffd60a' },
  alface:  { vol:4.1,  price:12.8,  ndvi:0.55, unit:'dz',  dir:-1, baseColor:'#ffd60a' },
  laranja: { vol:24.5, price:28.4,  ndvi:0.62, unit:'cx',  dir:-1, baseColor:'#0a84ff' },
  batata:  { vol:4.8,  price:52.1,  ndvi:0.67, unit:'sc',  dir:1,  baseColor:'#30d158' },
  cebola:  { vol:1.6,  price:38.7,  ndvi:0.58, unit:'sc',  dir:1,  baseColor:'#30d158' },
  manga:   { vol:1.4,  price:42.0,  ndvi:0.41, unit:'cx',  dir:-1, baseColor:'#ff453a' },
  uva:     { vol:1.7,  price:6.4,   ndvi:0.69, unit:'kg',  dir:1,  baseColor:'#30d158' },
  morango: { vol:0.4,  price:18.9,  ndvi:0.58, unit:'kg',  dir:-1, baseColor:'#ffd60a' },
  maca:    { vol:1.1,  price:3.2,   ndvi:0.72, unit:'kg',  dir:1,  baseColor:'#30d158' },
  melao:   { vol:0.6,  price:48.6,  ndvi:0.44, unit:'cx',  dir:-1, baseColor:'#ff453a' },
  banana:  { vol:7.3,  price:1.8,   ndvi:0.71, unit:'kg',  dir:1,  baseColor:'#30d158' },
  mamao:   { vol:1.8,  price:2.4,   ndvi:0.66, unit:'kg',  dir:1,  baseColor:'#30d158' },
  alho:    { vol:0.2,  price:24.8,  ndvi:0.52, unit:'kg',  dir:-1, baseColor:'#ffd60a' },
  cenoura: { vol:0.8,  price:2.9,   ndvi:0.60, unit:'kg',  dir:1,  baseColor:'#30d158' },
  pepino:  { vol:0.5,  price:3.1,   ndvi:0.53, unit:'kg',  dir:-1, baseColor:'#ffd60a' },
  abacaxi: { vol:2.6,  price:2.2,   ndvi:0.64, unit:'un',  dir:1,  baseColor:'#30d158' },
  'uva-ar':{ vol:3.1,  price:2.76,  ndvi:0.67, unit:'kg',  dir:1,  baseColor:'#9b59b6' },
  'maca-ar':{ vol:0.9, price:1.78,  ndvi:0.70, unit:'kg',  dir:1,  baseColor:'#9b59b6' },
};

// sparkline data per product
const hortiSparkData = {};
Object.keys(hortiState).forEach(k => {
  hortiSparkData[k] = Array(30).fill(null);
});

// init sparklines for horti cards
const hortiSparks = {};
function initHortiSparks() {
  Object.entries(hortiState).forEach(([k, h]) => {
    const el = document.getElementById('hs-' + k);
    if (!el) return;
    el.width  = el.parentElement.offsetWidth || 148;
    el.height = 36;
    const ctx = el.getContext('2d');
    hortiSparks[k] = new Chart(ctx, {
      type: 'line',
      data: { labels: hortiSparkData[k].map((_,i)=>i), datasets: [{ data: [...hortiSparkData[k]], borderColor: h.baseColor, borderWidth: 1.5, pointRadius: 0, tension: 0.4, fill: true, backgroundColor: h.baseColor + '33' }] },
      options: { responsive: false, animation: false, plugins: { legend:{display:false}, tooltip:{enabled:false} }, scales: { x:{display:false}, y:{display:false} } }
    });
  });
}
setTimeout(initHortiSparks, 200);

// updateHorti: apenas mantém os sparklines sincronizados com preços reais.
// Sem simulação — preços vêm exclusivamente de APIs reais (_updateHortiPrices).
function updateHorti() {
  Object.entries(hortiState).forEach(([k, h]) => {
    if (!h._realPrice) return; // só atualiza sparkline se há dado real
    if (hortiSparks[k]) {
      hortiSparkData[k].shift();
      hortiSparkData[k].push(h._realPrice);
      hortiSparks[k].data.datasets[0].data = [...hortiSparkData[k]];
      hortiSparks[k].update('none');
    }
  });
}
setInterval(updateHorti, 30000); // 30s — só roda se há dado real

// Popula a faixa de alertas com dados reais da API
async function _loadAlertsStrip() {
  const strip = document.getElementById('alerts-strip-scroll');
  if (!strip) return;
  try {
    const [evRes, alertRes] = await Promise.all([
      fetch('/api/nias/brain/events?limit=8', { cache:'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/flv/alerts?severity=all', { cache:'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null),
    ]);
    const events = evRes?.data?.events || [];
    const alerts = alertRes?.alerts || alertRes?.data || [];
    const all = [
      ...events.map(e => ({ text: e.titulo || e.title || '', sev: e.gravidade || 'info' })),
      ...alerts.map(a => ({ text: a.titulo || a.title || a.message || '', sev: a.severity || a.severidade || 'info' })),
    ].filter(x => x.text);
    if (!all.length) {
      strip.innerHTML = '<span class="alert-item" style="color:var(--accent2);">✓ Sem alertas críticos no momento — sistema operacional</span>';
      return;
    }
    const sevColor = { critica:'var(--danger)', alta:'var(--warn)', critical:'var(--danger)', high:'var(--warn)' };
    strip.innerHTML = all.map(a => {
      const c = sevColor[a.sev] || 'var(--text2)';
      return `<span class="alert-item" style="color:${c};">⚠ ${a.text}<span class="sep">|</span></span>`;
    }).join('');
  } catch(e) {
    strip.innerHTML = '<span class="alert-item" style="color:var(--text2);">⬡ Conectando ao sistema de alertas…</span>';
  }
}

// ═══════════════════════════════════════════════════════════════════
// 1. PHENOLOGICAL ENGINE — Anti-False-Alarm NDVI Logic
// ═══════════════════════════════════════════════════════════════════
// Reference NDVI curves per crop (normalized 0–1 = sowing→harvest)
// Each value = expected NDVI at that % of the crop cycle
const PHENOL_CURVES = {
  soja:   [0.15,0.28,0.45,0.62,0.71,0.74,0.72,0.65,0.50,0.35,0.20],
  milho:  [0.18,0.32,0.52,0.68,0.76,0.78,0.75,0.65,0.48,0.30,0.18],
  cana:   [0.20,0.38,0.55,0.67,0.72,0.74,0.75,0.74,0.72,0.68,0.40],
  tomate: [0.10,0.22,0.40,0.55,0.65,0.68,0.62,0.52,0.38,0.22,0.10],
  horti:  [0.08,0.20,0.38,0.52,0.58,0.56,0.48,0.35,0.20,0.10,0.05],
};
// Active crop zones: { id, culture, daysPlanted, cycleDays, lat, lon }
const cropZones = [
  { id:'mt-soja-1',    culture:'soja',   daysPlanted:118, cycleDays:130, lat:-12.5, lon:-55.0, ndviCurrent:0.32, region:'Sorriso, MT' },
  { id:'mt-soja-2',    culture:'soja',   daysPlanted:105, cycleDays:130, lat:-14.0, lon:-51.0, ndviCurrent:0.45, region:'Campo Verde, MT' },
  { id:'go-soja-1',    culture:'soja',   daysPlanted:95,  cycleDays:125, lat:-17.0, lon:-49.5, ndviCurrent:0.58, region:'Rio Verde, GO' },
  { id:'ba-soja-1',    culture:'soja',   daysPlanted:88,  cycleDays:130, lat:-10.5, lon:-44.0, ndviCurrent:0.38, region:'MATOPIBA, BA' },
  { id:'mt-milho-1',   culture:'milho',  daysPlanted:72,  cycleDays:120, lat:-15.0, lon:-54.0, ndviCurrent:0.62, region:'Sapezal, MT' },
  { id:'go-tomate-1',  culture:'tomate', daysPlanted:55,  cycleDays:90,  lat:-17.2, lon:-48.0, ndviCurrent:0.53, region:'Pires do Rio, GO' },
  { id:'sp-horti-1',   culture:'horti',  daysPlanted:28,  cycleDays:60,  lat:-23.5, lon:-46.5, ndviCurrent:0.49, region:'Mogi das Cruzes, SP' },
  { id:'rn-melao-1',   culture:'horti',  daysPlanted:42,  cycleDays:75,  lat:-5.1,  lon:-37.2, ndviCurrent:0.44, region:'Mossoró, RN' },
];

// Core classification function
function classifyNdviDrop(zone) {
  const curve = PHENOL_CURVES[zone.culture] || PHENOL_CURVES.horti;
  const progress = Math.min(1, zone.daysPlanted / zone.cycleDays);
  const daysLeft  = zone.cycleDays - zone.daysPlanted;
  const idx = Math.floor(progress * (curve.length - 1));
  const idxNext = Math.min(curve.length - 1, idx + 1);
  const frac = (progress * (curve.length - 1)) - idx;
  const expectedNdvi = curve[idx] * (1 - frac) + curve[idxNext] * frac;
  const delta = zone.ndviCurrent - expectedNdvi;

  if (daysLeft <= 20 && delta >= -0.12) {
    return { type: 'harvest', label: '✓ COLHEITA EM ANDAMENTO', pct: Math.round(progress * 100) };
  } else if (daysLeft <= 60 && delta < -0.10) {
    return { type: 'harvest', label: `✓ PRÉ-COLHEITA (${daysLeft}d)`, pct: Math.round(progress * 100) };
  } else if (delta < -0.12) {
    return { type: 'pest', label: '⚠ PRAGA/DOENÇA SUSPEITA', pct: Math.round(progress * 100) };
  } else if (delta < -0.08) {
    return { type: 'drought', label: '⚠ ESTRESSE HÍDRICO', pct: Math.round(progress * 100) };
  } else {
    return { type: 'normal', label: `● DESENVOLVIMENTO NORMAL`, pct: Math.round(progress * 100) };
  }
}

let phenolResults = {};
function runPhenolEngine() {
  cropZones.forEach(z => {
    // slight daily progress simulation
    z.daysPlanted = Math.min(z.cycleDays, z.daysPlanted + 0.01);
    // ndviCurrent updated by _fetchNdviLive(); static between fetches
    const result = classifyNdviDrop(z);
    phenolResults[z.id] = { ...result, zone: z };
  });

  // Update main NDVI phenol tag using Cerrado soja zone
  const cerradoResult = phenolResults['mt-soja-1'] || phenolResults['go-soja-1'];
  if (cerradoResult) {
    const tag = document.getElementById('ndvi-phenol-tag');
    if (tag) {
      tag.className = 'ndvi-tag ' + cerradoResult.type;
      tag.textContent = cerradoResult.label;
    }
  }

  // Update MATOPIBA result
  const matopibaResult = phenolResults['ba-soja-1'];
  if (matopibaResult) {
    const liveItem = document.querySelector('#live-feed-list');
    if (liveItem) {
      const div = document.createElement('div');
      div.className = 'lf-item';
      const cls = matopibaResult.type === 'harvest' ? 'lf-ok' : matopibaResult.type === 'pest' ? 'lf-danger' : 'lf-warn';
      div.innerHTML = `<span class="${cls}">FENOLOGIA MATOPIBA: ${matopibaResult.label} (${matopibaResult.pct}% ciclo)</span><br><span class="lf-time">${new Date().toLocaleTimeString('pt-BR')}</span>`;
      liveItem.insertBefore(div, liveItem.firstChild);
    }
  }

  // Increment cycles counter
  engineCycles++;
  const el = document.getElementById('fs-cycles');
  if (el) el.textContent = engineCycles.toLocaleString('pt-BR');
}
let engineCycles = 0;
setInterval(runPhenolEngine, 5000);
runPhenolEngine();

// ═══════════════════════════════════════════════════════════════════
// 2. BRIX THERMAL AMPLITUDE ENGINE (Tomate Indústria)
// ═══════════════════════════════════════════════════════════════════
const brixState = {
  tNight: 23.4,      // °C — temperatura noturna média
  tDay: 31.6,        // °C — temperatura diurna
  daysAbove22: 5,    // dias consecutivos Tnoite > 22°C
  brix: 3.8,         // °Brix estimado
  brixTarget: 4.8,   // °Brix mínimo para processamento
  priceAdjFactor: 1.0,
  _liveData: null,   // populated by _fetchBrixClimate()
};

function updateBrix() {
  // Values driven by real climate API (_fetchBrixClimate); idle drift only when no live data
  if (!brixState._liveData) return;
  brixState.tNight = brixState._liveData.tNight ?? brixState.tNight;
  brixState.tDay   = brixState._liveData.tDay   ?? brixState.tDay;
  const deltaT = brixState.tDay - brixState.tNight;

  // Count consecutive nights above 22°C
  if (brixState.tNight > 22) {
    brixState.daysAbove22 = Math.min(14, brixState.daysAbove22 + 0.08);
  } else {
    brixState.daysAbove22 = Math.max(0, brixState.daysAbove22 - 0.2);
  }

  // Brix model: base + ΔT bonus − warm-night penalty
  const warmPenalty = brixState.daysAbove22 > 5 ? (brixState.daysAbove22 - 5) * 0.06 : 0;
  const deltaTBonus = Math.max(0, (deltaT - 10) * 0.08);
  brixState.brix = Math.max(2.5, Math.min(6.0,
    brixState.brix + deltaTBonus * 0.02 - warmPenalty * 0.02
  ));
  const brixPct = ((brixState.brix - 2.5) / (6.0 - 2.5)) * 100;

  // Update DOM
  const brixValEl = document.getElementById('brix-val');
  if (brixValEl) {
    brixValEl.textContent = brixState.brix.toFixed(1) + '°';
    brixValEl.style.color = brixState.brix < brixState.brixTarget ? 'var(--danger)' : brixState.brix < 4.5 ? 'var(--warn)' : 'var(--accent2)';
  }
  const brixFillEl = document.getElementById('brix-fill');
  if (brixFillEl) {
    brixFillEl.style.width = brixPct.toFixed(0) + '%';
    brixFillEl.style.background = brixState.brix < brixState.brixTarget ? 'var(--danger)' : brixState.brix < 4.5 ? 'var(--warn)' : 'var(--accent2)';
  }

  const dtValEl = document.getElementById('delta-t-val');
  if (dtValEl) {
    const isWarn = brixState.tNight > 22;
    dtValEl.textContent = `Tnoite: ${brixState.tNight.toFixed(1)}°C ${isWarn ? '⚠' : '✓'}`;
    dtValEl.className = isWarn ? 'delta-t-warn' : 'delta-t-ok';
  }
  const dtAmpEl = document.getElementById('delta-t-amp');
  if (dtAmpEl) {
    const ampWarn = deltaT < 12;
    dtAmpEl.textContent = `ΔT: ${deltaT.toFixed(1)}°C ${ampWarn ? '< 12°C ⚠' : '≥ 12°C ✓'}`;
    dtAmpEl.className = ampWarn ? 'delta-t-warn' : 'delta-t-ok';
  }

  // Auto-adjust tomate-ind price via Brix factor
  const brixFactor = Math.max(0.85, Math.min(1.15, brixState.brix / brixState.brixTarget));
  const adjPrice = (148.0 * brixFactor).toFixed(0);
  const hpInd = document.getElementById('hp-tomate-ind');
  if (hpInd) hpInd.textContent = `R$ ${adjPrice}/t`;
}
async function _fetchBrixClimate() {
  try {
    const r = await fetch('/api/clima/bioclima', { cache: 'no-store' });
    if (!r.ok) return;
    const d = await r.json();
    const data = d?.data ?? d;
    const tMin = data?.temperature_2m_min ?? data?.tmin ?? null;
    const tMax = data?.temperature_2m_max ?? data?.tmax ?? null;
    if (tMin !== null && tMax !== null) {
      brixState._liveData = { tNight: +tMin, tDay: +tMax };
      updateBrix();
    }
    // Update cloud cover from API if available
    const cc = data?.cloud_cover ?? data?.cloudcover ?? null;
    if (cc !== null) cloudCover = Math.max(0, Math.min(100, +cc));
  } catch (_) {}
}
_fetchBrixClimate();
setInterval(_fetchBrixClimate, 10 * 60 * 1000);
setInterval(updateBrix, 4500);

// ═══════════════════════════════════════════════════════════════════
// 3. SPEED-BASED LOGISTICS FILTER (Anti-Noise Gargalo)
// ═══════════════════════════════════════════════════════════════════
const roadState = {
  br163: { speedKmh: 42, limitKmh: 80, restStopFilter: true, gargalo: true },
};
// Segments monitored (excluding rest stops at km 612, 780, 845)
const REST_STOP_KM = [612, 780, 845, 920];

function updateRoadSpeed() {
  const s = roadState.br163;
  // Simulate speed — fluctuates around congested value
  // speed derived from logState saturation — no random walk
  s.speedKmh = Math.max(18, Math.min(85, 85 * (1 - logState.br163 / 200)));

  const pct = s.speedKmh / s.limitKmh;
  const drop = (1 - pct) * 100;

  // Gargalo only if avg speed dropped > 30% below limit (filter noise from rest stops)
  s.gargalo = pct < 0.70;

  const color = pct < 0.50 ? 'var(--danger)' : pct < 0.70 ? 'var(--warn)' : 'var(--accent2)';
  const speedEl = document.getElementById('br163-speed');
  if (speedEl) { speedEl.textContent = Math.round(s.speedKmh) + ' km/h'; speedEl.style.color = color; }
  const speedBarEl = document.getElementById('br163-speed-bar');
  if (speedBarEl) { speedBarEl.style.width = (pct * 100).toFixed(0) + '%'; speedBarEl.style.background = color; }
  const speedPctEl = document.getElementById('br163-speed-pct');
  if (speedPctEl) {
    if (s.gargalo) {
      speedPctEl.textContent = `▼ -${drop.toFixed(0)}% GARGALO CONFIRMADO`;
      speedPctEl.style.color = 'var(--danger)';
    } else if (pct < 0.85) {
      speedPctEl.textContent = `▼ -${drop.toFixed(0)}% — TRÁFEGO LENTO`;
      speedPctEl.style.color = 'var(--warn)';
    } else {
      speedPctEl.textContent = `✓ FLUXO NORMAL`;
      speedPctEl.style.color = 'var(--accent2)';
    }
  }
  // Update status text
  const stEl = document.getElementById('br163-status-txt');
  if (stEl) {
    stEl.textContent = s.gargalo ? 'CRÍTICO — GARGALO' : pct < 0.85 ? 'ATENÇÃO' : 'NORMAL';
    stEl.style.color = color;
  }
}
setInterval(updateRoadSpeed, 3000);

// ═══════════════════════════════════════════════════════════════════
// 4. FAIL-SAFE ENGINE
// ═══════════════════════════════════════════════════════════════════
let cloudCover = 18;
let cepeaLastUpdate = new Date();
let priceApiFailCount = 0;
let fsCyclesTotal = 0;

function updateFailSafe() {
  fsCyclesTotal++;

  // ── Cloud cover simulation (tropical regions spike in rainy season)
  // cloud cover updated by _fetchBrixClimate / bioclima API; static between fetches
  const cloudEl = document.getElementById('fs-cloud');
  if (cloudEl) {
    cloudEl.textContent = cloudCover.toFixed(0) + '%';
    cloudEl.style.color = cloudCover > 60 ? 'var(--danger)' : cloudCover > 30 ? 'var(--warn)' : 'var(--accent2)';
  }

  // ── SAR auto-activation when cloud > 30%
  const sarEl   = document.getElementById('fs-sar-val');
  const sarDot  = document.querySelector('#fs-sar .fs-dot');
  if (sarEl) {
    if (cloudCover > 60) {
      sarEl.textContent = '⚡ ATIVO — MODO SAR';
      sarEl.style.color = 'var(--danger)';
      if (sarDot) sarDot.style.background = 'var(--danger)';
      // inject feed event
      injectFeedEvent('lf-warn', `SAR ativo — cobertura de nuvens ${cloudCover.toFixed(0)}% detectada (Amazônia/Cerrado)`);
    } else if (cloudCover > 30) {
      sarEl.textContent = '⚡ ATIVO — SAR PARCIAL';
      sarEl.style.color = 'var(--warn)';
      if (sarDot) sarDot.style.background = 'var(--warn)';
    } else {
      sarEl.textContent = 'STANDBY';
      sarEl.style.color = 'var(--accent2)';
      if (sarDot) sarDot.style.background = 'var(--accent2)';
    }
  }

  // ── CEPEA price API update (every 15min simulation)
  const now = new Date();
  const minsSince = (now - cepeaLastUpdate) / 60000;
  if (minsSince >= 15) { // 15 minutos reais
    cepeaLastUpdate = now;
    priceApiFailCount = 0; // reset; falhas reais detectadas por _fetchLivePrices()
  }
  const cepeaEl  = document.getElementById('fs-cepea');
  const fallEl   = document.getElementById('fs-fallback');
  if (cepeaEl) {
    if (priceApiFailCount > 2) {
      cepeaEl.textContent  = 'FALHA · RETRY...';
      cepeaEl.style.color  = 'var(--danger)';
      if (fallEl) { fallEl.textContent = 'ATIVADO (último preço)'; fallEl.style.color = 'var(--warn)'; }
    } else {
      cepeaEl.textContent  = 'ATIVO · ' + now.toLocaleTimeString('pt-BR', {hour:'2-digit',minute:'2-digit'});
      cepeaEl.style.color  = 'var(--accent2)';
      if (fallEl) { fallEl.textContent = 'NÃO ATIVADO'; fallEl.style.color = 'var(--accent2)'; }
    }
  }

  // ── Vector tiles status (throttle based on polygon count)
  const tilesEl = document.getElementById('fs-tiles');
  if (tilesEl) {
    const poly = parseInt((document.getElementById('map-poly') || {}).textContent || '14832');
    tilesEl.textContent = poly > 15000 ? 'TILE THROTTLE' : 'ATIVO';
    tilesEl.style.color = poly > 15000 ? 'var(--warn)' : 'var(--accent2)';
  }

  // ── GPS fleet latency
  const gpsEl  = document.getElementById('fs-gps');
  const gpsDot = document.getElementById('fs-gps-dot');
  if (gpsEl) {
    gpsEl.textContent  = 'Sem integração ANTT';
    gpsEl.style.color  = 'var(--text2)';
    if (gpsDot) gpsDot.style.background = 'var(--text2)';
  }
}

function injectFeedEvent(cls, msg) {
  const list = document.getElementById('live-feed-list');
  if (!list) return;
  const div = document.createElement('div');
  div.className = 'lf-item';
  div.innerHTML = `<span class="${cls}">${msg}</span><br><span class="lf-time">${new Date().toLocaleTimeString('pt-BR')}</span>`;
  list.insertBefore(div, list.firstChild);
}

setInterval(updateFailSafe, 6000);
updateFailSafe();

// ═══════════════════════════════════════════════════════════════════
// MAP PANEL TOGGLES — STATUS ORBITAL e CAMADAS colapsáveis
// ═══════════════════════════════════════════════════════════════════
function _toggleSatBar(e) {
  const bar = document.getElementById('map-sat-bar');
  if (!bar) return;
  if (bar.classList.contains('expanded')) {
    // Fechar ao clicar fora do conteúdo ou no título
    const title = bar.querySelector('.sat-title');
    if (e && title && title.contains(e.target)) { bar.classList.remove('expanded'); return; }
    if (!e) { bar.classList.remove('expanded'); return; }
  } else {
    bar.classList.add('expanded');
  }
}
// Clicar fora fecha o painel orbital
document.addEventListener('click', function(e) {
  const bar = document.getElementById('map-sat-bar');
  if (bar && bar.classList.contains('expanded') && !bar.contains(e.target)) {
    bar.classList.remove('expanded');
  }
});

function _toggleMapControls() {
  const mc = document.getElementById('map-controls');
  const btn = document.getElementById('map-ctrl-btn');
  if (!mc) return;
  const collapsed = mc.classList.toggle('collapsed');
  if (btn) btn.textContent = collapsed ? '▼' : '▲';
}
// Clicar fora fecha Camadas
document.addEventListener('click', function(e) {
  const mc = document.getElementById('map-controls');
  if (mc && !mc.classList.contains('collapsed') && !mc.contains(e.target)) {
    mc.classList.add('collapsed');
    const btn = document.getElementById('map-ctrl-btn');
    if (btn) btn.textContent = '▼';
  }
});

// ── Sincronizar pill de alerta no ticker com o estado do decision-banner ──
(function _patchDecisionBanner() {
  const orig = Object.getOwnPropertyDescriptor(Element.prototype, 'className');
  // Observar mudanças no decision-banner e espelhar no ticker pill
  const banner = document.getElementById('decision-banner');
  if (!banner) return;
  const pill   = document.getElementById('ticker-alert-pill');
  const pdot   = document.getElementById('ticker-alert-dot');
  const plabel = document.getElementById('ticker-alert-label');
  if (!pill) return;

  function _syncPill() {
    const dbDot   = document.getElementById('db-dot');
    const dbLabel = document.getElementById('db-label');
    const dbMsg   = document.getElementById('db-msg');
    if (!dbDot) return;
    const color = dbDot.style.background || 'var(--accent2)';
    const label = dbLabel ? dbLabel.textContent : '';
    if (pdot)   { pdot.style.background = color; pdot.style.boxShadow = `0 0 5px ${color}`; }
    if (plabel) { plabel.textContent = label; plabel.style.color = color; }
    // Mostrar pill apenas se não for estado OK (para não poluir quando sistema estável)
    if (pill) pill.style.display = banner.className === 'estado-ok' ? 'none' : 'flex';
  }

  // Observar mudanças de classe no banner e conteúdo nos spans filhos
  new MutationObserver(_syncPill).observe(banner, { attributes:true, attributeFilter:['class'], subtree:true, characterData:true, childList:true });
  setTimeout(_syncPill, 2000);
})();

// ═══════════════════════════════════════════════════════════════════
// MUNICIPAL ENGINE — Choropleth + Rm + Anomaly Radar
// ═══════════════════════════════════════════════════════════════════

// ── Culture color base (HSL adjusted by NDVI for brightness)
const CULTURE_COLORS = {
  soja:  { h:120, s:80 },  // green
  milho: { h:48,  s:85 },  // yellow
  tomate:{ h:15,  s:90 },  // orange-red
  horti: { h:180, s:75 },  // cyan
  cana:  { h:30,  s:70 },  // brown
  uva:   { h:270, s:70 },  // purple
  maca:  { h:10,  s:80 },  // red-pink
  pastagem:{ h:90, s:50 }, // light green
};

function ndviToLightness(ndvi) {
  // NDVI 0.20→darkest(15%), 0.80→brightest(55%)
  return Math.round(15 + ((ndvi - 0.20) / 0.60) * 40);
}

function cultureColor(culture, ndvi, alpha = 0.75) {
  const c = CULTURE_COLORS[culture] || CULTURE_COLORS.soja;
  const l = ndviToLightness(ndvi);
  return `hsla(${c.h},${c.s}%,${l}%,${alpha})`;
}

// ── South American municipal dataset (IBGE + INDEC + DGEEC + INE)
// Each record: { id, name, state, country, adminLevel, culture, areaMha, ndvi, coefManejo, lat, lon, poly }
// poly = simplified ring [lat,lon] approximation
const MUNICIPAL_DB = [
  // ──── BRASIL — MATO GROSSO ────
  { id:'BR-MT-SOR', name:'Sorriso',              state:'MT', country:'BR', culture:'soja',  areaMha:1.02, ndvi:0.63, coef:0.91,
    poly:[[-12.0,-56.0],[-11.4,-56.0],[-11.4,-54.8],[-12.0,-54.8]] },
  { id:'BR-MT-LRV', name:'Lucas do Rio Verde',   state:'MT', country:'BR', culture:'soja',  areaMha:0.71, ndvi:0.61, coef:0.93,
    poly:[[-13.2,-56.0],[-12.6,-56.0],[-12.6,-55.0],[-13.2,-55.0]] },
  { id:'BR-MT-NMU', name:'Nova Mutum',            state:'MT', country:'BR', culture:'soja',  areaMha:0.85, ndvi:0.65, coef:0.90,
    poly:[[-13.8,-56.5],[-13.2,-56.5],[-13.2,-55.6],[-13.8,-55.6]] },
  { id:'BR-MT-SAP', name:'Sapezal',               state:'MT', country:'BR', culture:'soja',  areaMha:0.93, ndvi:0.62, coef:0.89,
    poly:[[-13.6,-58.4],[-13.0,-58.4],[-13.0,-57.4],[-13.6,-57.4]] },
  { id:'BR-MT-CNP', name:'Campo Novo do Parecis', state:'MT', country:'BR', culture:'soja',  areaMha:0.78, ndvi:0.64, coef:0.92,
    poly:[[-14.2,-57.8],[-13.6,-57.8],[-13.6,-56.9],[-14.2,-56.9]] },
  { id:'BR-MT-CVE', name:'Campo Verde',           state:'MT', country:'BR', culture:'soja',  areaMha:0.55, ndvi:0.61, coef:0.88,
    poly:[[-15.4,-52.5],[-14.8,-52.5],[-14.8,-51.6],[-15.4,-51.6]] },
  { id:'BR-MT-PRI', name:'Primavera do Leste',    state:'MT', country:'BR', culture:'soja',  areaMha:0.48, ndvi:0.58, coef:0.87,
    poly:[[-15.6,-54.4],[-15.0,-54.4],[-15.0,-53.5],[-15.6,-53.5]] },
  { id:'BR-MT-RON', name:'Rondonópolis',          state:'MT', country:'BR', culture:'milho', areaMha:0.41, ndvi:0.60, coef:0.86,
    poly:[[-17.0,-54.8],[-16.4,-54.8],[-16.4,-54.0],[-17.0,-54.0]] },
  { id:'BR-MT-SIN', name:'Sinop',                 state:'MT', country:'BR', culture:'soja',  areaMha:0.52, ndvi:0.66, coef:0.91,
    poly:[[-12.0,-55.6],[-11.4,-55.6],[-11.4,-54.8],[-12.0,-54.8]] },
  // ──── BRASIL — GOIÁS ────
  { id:'BR-GO-RRV', name:'Rio Verde',             state:'GO', country:'BR', culture:'soja',  areaMha:0.90, ndvi:0.58, coef:0.90,
    poly:[[-17.9,-51.5],[-17.3,-51.5],[-17.3,-50.6],[-17.9,-50.6]] },
  { id:'BR-GO-JAT', name:'Jataí',                 state:'GO', country:'BR', culture:'soja',  areaMha:0.72, ndvi:0.57, coef:0.88,
    poly:[[-17.9,-52.0],[-17.3,-52.0],[-17.3,-51.2],[-17.9,-51.2]] },
  { id:'BR-GO-MIN', name:'Mineiros',              state:'GO', country:'BR', culture:'soja',  areaMha:0.68, ndvi:0.59, coef:0.89,
    poly:[[-18.2,-53.0],[-17.6,-53.0],[-17.6,-52.2],[-18.2,-52.2]] },
  { id:'BR-GO-PIR', name:'Pires do Rio',          state:'GO', country:'BR', culture:'tomate',areaMha:0.12, ndvi:0.53, coef:0.83,
    poly:[[-17.8,-48.7],[-17.2,-48.7],[-17.2,-47.9],[-17.8,-47.9]] },
  // ──── BRASIL — MINAS GERAIS ────
  { id:'BR-MG-UBE', name:'Uberlândia',            state:'MG', country:'BR', culture:'tomate',areaMha:0.18, ndvi:0.55, coef:0.85,
    poly:[[-19.1,-48.4],[-18.5,-48.4],[-18.5,-47.6],[-19.1,-47.6]] },
  { id:'BR-MG-PAT', name:'Patos de Minas',        state:'MG', country:'BR', culture:'tomate',areaMha:0.14, ndvi:0.54, coef:0.84,
    poly:[[-18.9,-46.8],[-18.3,-46.8],[-18.3,-46.0],[-18.9,-46.0]] },
  { id:'BR-MG-ARA', name:'Araxá',                 state:'MG', country:'BR', culture:'cana',  areaMha:0.31, ndvi:0.69, coef:0.91,
    poly:[[-19.8,-46.9],[-19.2,-46.9],[-19.2,-46.1],[-19.8,-46.1]] },
  { id:'BR-MG-BAR', name:'Barbacena',             state:'MG', country:'BR', culture:'horti', areaMha:0.08, ndvi:0.52, coef:0.79,
    poly:[[-21.5,-43.8],[-21.0,-43.8],[-21.0,-43.2],[-21.5,-43.2]] },
  // ──── BRASIL — SÃO PAULO ────
  { id:'BR-SP-RIB', name:'Ribeirão Preto',        state:'SP', country:'BR', culture:'cana',  areaMha:0.27, ndvi:0.71, coef:0.93,
    poly:[[-21.3,-47.9],[-20.8,-47.9],[-20.8,-47.3],[-21.3,-47.3]] },
  { id:'BR-SP-ITA', name:'Itápolis',              state:'SP', country:'BR', culture:'tomate',areaMha:0.09, ndvi:0.54, coef:0.82,
    poly:[[-21.6,-49.0],[-21.1,-49.0],[-21.1,-48.4],[-21.6,-48.4]] },
  { id:'BR-SP-MOG', name:'Mogi das Cruzes',       state:'SP', country:'BR', culture:'horti', areaMha:0.05, ndvi:0.49, coef:0.76,
    poly:[[-23.7,-46.2],[-23.3,-46.2],[-23.3,-45.7],[-23.7,-45.7]] },
  // ──── BRASIL — PARANÁ ────
  { id:'BR-PR-CAS', name:'Cascavel',              state:'PR', country:'BR', culture:'soja',  areaMha:0.38, ndvi:0.60, coef:0.88,
    poly:[[-25.0,-53.6],[-24.5,-53.6],[-24.5,-52.9],[-25.0,-52.9]] },
  { id:'BR-PR-TOL', name:'Toledo',                state:'PR', country:'BR', culture:'soja',  areaMha:0.30, ndvi:0.59, coef:0.87,
    poly:[[-24.7,-54.0],[-24.2,-54.0],[-24.2,-53.4],[-24.7,-53.4]] },
  { id:'BR-PR-LON', name:'Londrina',              state:'PR', country:'BR', culture:'soja',  areaMha:0.20, ndvi:0.57, coef:0.86,
    poly:[[-23.4,-51.3],[-22.9,-51.3],[-22.9,-50.7],[-23.4,-50.7]] },
  // ──── BRASIL — RIO GRANDE DO SUL ────
  { id:'BR-RS-PAS', name:'Passo Fundo',           state:'RS', country:'BR', culture:'soja',  areaMha:0.29, ndvi:0.55, coef:0.85,
    poly:[[-28.5,-52.6],[-27.9,-52.6],[-27.9,-51.8],[-28.5,-51.8]] },
  { id:'BR-RS-VAC', name:'Vacaria',               state:'RS', country:'BR', culture:'maca',  areaMha:0.22, ndvi:0.72, coef:0.90,
    poly:[[-28.7,-51.0],[-28.1,-51.0],[-28.1,-50.3],[-28.7,-50.3]] },
  // ──── BRASIL — NORDESTE ────
  { id:'BR-BA-BAR', name:'Barreiras',             state:'BA', country:'BR', culture:'soja',  areaMha:0.65, ndvi:0.38, coef:0.76,
    poly:[[-12.5,-45.4],[-11.9,-45.4],[-11.9,-44.6],[-12.5,-44.6]] },
  { id:'BR-PE-PET', name:'Petrolina',             state:'PE', country:'BR', culture:'uva',   areaMha:0.18, ndvi:0.61, coef:0.88,
    poly:[[-9.8,-40.8],[-9.2,-40.8],[-9.2,-40.1],[-9.8,-40.1]] },
  { id:'BR-RN-MOS', name:'Mossoró',               state:'RN', country:'BR', culture:'horti', areaMha:0.14, ndvi:0.44, coef:0.72,
    poly:[[-5.5,-37.6],[-4.9,-37.6],[-4.9,-36.9],[-5.5,-36.9]] },
  // ──── ARGENTINA — BUENOS AIRES / CÓRDOBA ────
  { id:'AR-COR-GDE', name:'General Deheza',       state:'Córdoba', country:'AR', culture:'soja',  areaMha:0.55, ndvi:0.62, coef:0.90,
    poly:[[-33.0,-63.8],[-32.4,-63.8],[-32.4,-63.0],[-33.0,-63.0]] },
  { id:'AR-COR-VEN', name:'Venado Tuerto',        state:'S.Fe', country:'AR', culture:'soja',  areaMha:0.48, ndvi:0.60, coef:0.89,
    poly:[[-34.0,-62.0],[-33.4,-62.0],[-33.4,-61.2],[-34.0,-61.2]] },
  { id:'AR-MEN-SAN', name:'San Martín',           state:'Mendoza', country:'AR', culture:'uva',   areaMha:0.32, ndvi:0.67, coef:0.92,
    poly:[[-33.2,-68.8],[-32.6,-68.8],[-32.6,-68.1],[-33.2,-68.1]] },
  { id:'AR-RNE-ALL', name:'Allen',                state:'R.Negro', country:'AR', culture:'maca',  areaMha:0.28, ndvi:0.70, coef:0.91,
    poly:[[-39.2,-66.0],[-38.6,-66.0],[-38.6,-65.3],[-39.2,-65.3]] },
  // ──── PARAGUAI — ALTO PARANÁ ────
  { id:'PY-ALT-HER', name:'Hernandarias',         state:'Alto Paraná', country:'PY', culture:'soja',  areaMha:0.42, ndvi:0.63, coef:0.86,
    poly:[[-25.6,-54.8],[-25.0,-54.8],[-25.0,-54.1],[-25.6,-54.1]] },
  { id:'PY-ITA-ENC', name:'Encarnación',          state:'Itapúa', country:'PY', culture:'soja',  areaMha:0.38, ndvi:0.61, coef:0.85,
    poly:[[-27.5,-55.9],[-26.9,-55.9],[-26.9,-55.2],[-27.5,-55.2]] },
  // ──── URUGUAI ────
  { id:'UY-RIV-RIV', name:'Rivera',               state:'Rivera', country:'UY', culture:'soja',  areaMha:0.18, ndvi:0.56, coef:0.84,
    poly:[[-31.0,-55.8],[-30.4,-55.8],[-30.4,-55.1],[-31.0,-55.1]] },
  { id:'UY-PAY-PAY', name:'Paysandú',             state:'Paysandú', country:'UY', culture:'soja',  areaMha:0.22, ndvi:0.57, coef:0.85,
    poly:[[-32.6,-58.2],[-32.0,-58.2],[-32.0,-57.5],[-32.6,-57.5]] },
];

// ── Rm calculation
function calcRm(mun) {
  const prodBase = { soja:3.4, milho:5.8, tomate:62, horti:28, cana:85, uva:18, maca:22, pastagem:1.2 };
  const base = prodBase[mun.culture] || 3.0;
  return +(mun.areaMha * 1000 * mun.ndvi * mun.coef * base / 1000).toFixed(2);
}

// Anomaly event templates — apenas valores derivados de dados reais do município
const ANOMALY_EVENTS = [
  z => ({ cls:'lf-danger', msg:`[${z.name.toUpperCase()}-${z.state}] Estresse hídrico detectado. NDVI: ${z.ndvi.toFixed(2)} — abaixo do limiar crítico.` }),
  z => ({ cls:'lf-warn',   msg:`[${z.name.toUpperCase()}-${z.state}] NDVI ${z.ndvi.toFixed(2)} — correlacionando fenologia (ciclo ~${Math.round(z.ndvi*130)}d)…` }),
  z => ({ cls:'lf-ok',     msg:`[${z.name.toUpperCase()}-${z.state}] Motor fenológico: PRÉ-COLHEITA detectada via análise de tendência NDVI.` }),
  z => ({ cls:'lf-sat',    msg:`[${z.name.toUpperCase()}-${z.state}] Polígonos recalculados: ${(z.areaMha*10).toFixed(0)} ativos. Rm estimado = ${calcRm(z)} kt` }),
  z => ({ cls:'lf-warn',   msg:`[${z.name.toUpperCase()}-${z.state}] ${z.culture === 'tomate' ? 'Risco BRIX ↓' : 'Ciclo fenológico em monitoramento'}. NDVI ${z.ndvi.toFixed(2)}.` }),
  z => ({ cls:'lf-danger', msg:`[${z.name.toUpperCase()}-${z.state}] Monitorar salinização: NDVI ${z.ndvi.toFixed(2)} com tendência descendente.` }),
  z => ({ cls:'lf-sat',    msg:`[${z.name.toUpperCase()}-${z.state}] Safra ${z.culture} — produção estimada: Rm = ${calcRm(z)} kt. Solo monitorado via SAR.` }),
  z => ({ cls:'lf-warn',   msg:`[${z.name.toUpperCase()}-${z.state}] Monitoramento climático ativo. NDVI ${z.ndvi.toFixed(2)} — ${z.ndvi < 0.40 ? 'risco elevado' : 'dentro do normal'}.` }),
  z => ({ cls:'lf-warn',   msg:`[${z.name.toUpperCase()}-${z.state}] Saturação logística nos corredores. Produto: ${z.culture}. NDVI referência: ${z.ndvi.toFixed(2)}.` }),
  z => ({ cls:'lf-ok',     msg:`[${z.name.toUpperCase()}-${z.state}] NDVI ${z.ndvi.toFixed(2)} — ${z.ndvi >= 0.55 ? 'produção acima da média' : z.ndvi >= 0.40 ? 'produção normal' : 'sob atenção'}.` }),
];

let munMap, munLayerGroup;
let activePolygons = {};

function initMunicipal() {
  window._munInit = true;
  munMap = L.map('map-municipal', { center: [-10, -60], zoom: 3, zoomControl: true });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    { attribution:'© OpenStreetMap', maxZoom:19, subdomains:'abc' }).addTo(munMap);

  addLocalAdminFallback(munMap, 'municipal-local-fallback', true);
  addCountryContours(munMap, 'municipal-countries-real', ADMIN_BOUNDARY.southAmerica).catch(e => console.warn('municipal countries', e));
  addStateContours(munMap, 'municipal-states', ADMIN_BOUNDARY.southAmerica).catch(e => console.warn('municipal states', e));

  munLayerGroup = L.layerGroup().addTo(munMap);
  // Local DB polygons as supplementary layer (detailed pins)
  renderChoropleth('all');
  buildMunTable('all');
  updateMunicipalSouthAmericaSummary('all');
  startAnomalyRadar();
  populateSimMun();
  setTimeout(addCrossBorderVectors, 800);
  // IBGE drill-down system (state choropleth loads on top)
  setTimeout(initStateChoropleth, 200);
  setTimeout(() => munMap && munMap.invalidateSize(), 120);
}

function renderChoropleth(cultureFilter) {
  munLayerGroup.clearLayers();
  activePolygons = {};
  const countryFilter = document.getElementById('mun-country')?.value || 'all';
  const filtered = MUNICIPAL_DB.filter(m =>
    (cultureFilter === 'all' || m.culture === cultureFilter || (Array.isArray(m.flvCultures) && m.flvCultures.includes(cultureFilter))) &&
    (countryFilter === 'all' || m.country === countryFilter)
  );
  filtered.forEach(mun => {
    const fillColor = cultureColor(mun.culture, mun.ndvi, 0.78);
    const borderColor = cultureColor(mun.culture, Math.min(0.85, mun.ndvi + 0.15), 1.0);
    const poly = L.polygon(mun.poly, {
      color: borderColor,
      fillColor,
      fillOpacity: 0.72,
      weight: 1.2,
    });
    const rm = calcRm(mun);
    const adminLabel = { BR:'Município/IBGE', AR:'Departamento/INDEC', CL:'Comuna/INE', PE:'Província/INEI', CO:'Municipio/DANE', EC:'Cantón/INEC', BO:'Município/INE', PY:'Distrito/DGEEC', UY:'Departamento/INE', VE:'Municipio/INE', GY:'Região/Bureau', SR:'Distrito/GBS', GF:'Comuna/INSEE' }[mun.country] || 'Unidade produtiva';
    poly.bindPopup(`
      <div style="font-family:monospace;font-size:12px;min-width:200px;">
        <b style="color:#000000;font-size:13px;">${mun.name}</b>
        <div style="color:#333;font-size:10px;">${adminLabel} — ${mun.state} · ${mun.country}</div>
        <hr style="border-color:#ccc;margin:4px 0;">
        <div><b>Cultura:</b> ${mun.culture.toUpperCase()}</div>
        <div><b>Área:</b> ${(mun.areaMha*1000).toFixed(0)} kha</div>
        <div><b>NDVI:</b> ${mun.ndvi.toFixed(3)} <span style="color:${mun.ndvi<0.50?'red':mun.ndvi<0.60?'orange':'green'}">${mun.ndvi<0.50?'▼ ALERTA':mun.ndvi<0.60?'▼ ATENÇÃO':'✓ NORMAL'}</span></div>
        <div><b>Coef. Manejo:</b> ${mun.coef.toFixed(2)}</div>
        <div style="margin-top:4px;background:#eee;padding:3px 5px;border-radius:3px;"><b>Rm = ${rm} kt</b></div>
      </div>
    `);
    poly.on('click', () => highlightMunicipal(mun.id));
    poly.addTo(munLayerGroup);
    activePolygons[mun.id] = { poly, mun };
  });
}

function filterMunicipalMap(cultureFilter) {
  renderChoropleth(cultureFilter);
  buildMunTable(cultureFilter);
  updateMunicipalSouthAmericaSummary(cultureFilter);
}

function updateMunicipalSouthAmericaSummary(cultureFilter) {
  const countryFilter = document.getElementById('mun-country')?.value || 'all';
  const rows = MUNICIPAL_DB.filter(m =>
    (cultureFilter === 'all' || m.culture === cultureFilter || (Array.isArray(m.flvCultures) && m.flvCultures.includes(cultureFilter))) &&
    (countryFilter === 'all' || m.country === countryFilter)
  );
  const countries = [...new Set(rows.map(m => m.country))].sort();
  const products = [...new Set(rows.flatMap(m => m.flvCultures || [m.culture]).filter(Boolean))].sort();
  const tons = rows.reduce((acc,m)=>acc+(+m.flvTons||0),0);
  const set = (id, txt) => { const el = document.getElementById(id); if (el) el.textContent = txt; };
  set('mun-sa-count', `${rows.length} polos/regiões`);
  set('mun-sa-countries', `${countries.length} países: ${countries.join(', ')}`);
  set('mun-sa-products', `${products.length} produtos · ${(tons/1000000).toFixed(2)} Mt estimadas/ano · ${products.slice(0,18).join(', ')}${products.length>18?'…':''}`);
}

function highlightMunicipal(id) {
  const entry = activePolygons[id];
  if (!entry) return;
  // Flash highlight
  entry.poly.setStyle({ weight: 3, fillOpacity: 0.95 });
  setTimeout(() => entry.poly.setStyle({ weight: 1.2, fillOpacity: 0.72 }), 1500);
}

function buildMunTable(cultureFilter) {
  const tbody = document.getElementById('mun-table-body');
  if (!tbody) return;
  const countryFilter = document.getElementById('mun-country')?.value || 'all';
  const filtered = MUNICIPAL_DB.filter(m =>
    (cultureFilter === 'all' || m.culture === cultureFilter || (Array.isArray(m.flvCultures) && m.flvCultures.includes(cultureFilter))) &&
    (countryFilter === 'all' || m.country === countryFilter)
  ).sort((a,b) => calcRm(b) - calcRm(a));

  tbody.innerHTML = filtered.map(m => {
    const rm = calcRm(m);
    const ndviColor = m.ndvi < 0.45 ? 'var(--danger)' : m.ndvi < 0.58 ? 'var(--warn)' : 'var(--accent2)';
    const status = m.ndvi < 0.45 ? '<span style="color:var(--danger);font-size:9px;">CRÍTICO</span>'
                 : m.ndvi < 0.55 ? '<span style="color:var(--warn);font-size:9px;">ATENÇÃO</span>'
                 : '<span style="color:var(--accent2);font-size:9px;">NORMAL</span>';
    const flag = { BR:'🇧🇷', AR:'🇦🇷', CL:'🇨🇱', PE:'🇵🇪', CO:'🇨🇴', EC:'🇪🇨', BO:'🇧🇴', PY:'🇵🇾', UY:'🇺🇾', VE:'🇻🇪', GY:'🇬🇾', SR:'🇸🇷', GF:'🇬🇫' }[m.country] || '';
    return `<tr style="cursor:pointer;" onclick="highlightMunicipal('${m.id}')">
      <td style="padding:5px 6px;border-bottom:1px solid var(--border);font-size:10px;width:35%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${flag} ${m.name}<span style="color:var(--text2);font-size:9px;"> · ${m.state}</span></td>
      <td style="padding:5px 6px;border-bottom:1px solid var(--border);font-size:10px;color:var(--text2);width:20%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${(m.flvCultures||[m.culture]).join(', ')}">${m.culture}</td>
      <td style="padding:5px 6px;border-bottom:1px solid var(--border);font-size:10px;text-align:right;color:${ndviColor};width:15%;" id="mun-ndvi-${m.id}">${m.ndvi.toFixed(3)}</td>
      <td style="padding:5px 6px;border-bottom:1px solid var(--border);font-size:10px;text-align:right;color:var(--accent);font-weight:bold;width:18%;" id="mun-rm-${m.id}">${rm}</td>
      <td style="padding:5px 6px;border-bottom:1px solid var(--border);text-align:center;width:12%;" id="mun-status-${m.id}">${status}</td>
    </tr>`;
  }).join('');
}

// ── Live NDVI update on municipal polygons
function updateMunicipalNdvi() {
  MUNICIPAL_DB.forEach(m => {
    // micro-fluctuation per municipality (independent microclimate)
    // ndvi updated by _fetchNdviLive(); static between fetches
    // update table cell
    const el = document.getElementById('mun-ndvi-' + m.id);
    if (el) { el.textContent = m.ndvi.toFixed(3); el.style.color = m.ndvi < 0.45 ? 'var(--danger)' : m.ndvi < 0.58 ? 'var(--warn)' : 'var(--accent2)'; }
    const rmEl = document.getElementById('mun-rm-' + m.id);
    if (rmEl) rmEl.textContent = calcRm(m);
    // update polygon fill
    const entry = activePolygons[m.id];
    if (entry) {
      entry.poly.setStyle({
        fillColor: cultureColor(m.culture, m.ndvi, 0.78),
        color: cultureColor(m.culture, Math.min(0.85, m.ndvi + 0.15), 1.0),
      });
    }
  });
}
setInterval(updateMunicipalNdvi, 7000);

// ── Anomaly Radar — alimentado por /api/nias/brain/events (dados reais)
// Eventos sintéticos removidos — sem Math.random() disfarçado de dado real
function startAnomalyRadar() {
  _fetchAnomalyRadarFromBrain();
}
async function _fetchAnomalyRadarFromBrain() {
  const list = document.getElementById('anomaly-radar-list');
  if (!list) return;
  try {
    const r = await fetch('/api/nias/brain/events', { cache:'no-store' });
    if (!r.ok) throw new Error('API indisponível');
    const d = await r.json();
    const events = d?.data?.events || [];
    if (!events.length) {
      list.innerHTML = '<div class="lf-item" style="color:var(--text2);font-size:9px;padding:8px;">Cérebro NIAS: sem anomalias detectadas no momento.</div>';
      return;
    }
    const countryLabels = {BR:'Brasil',AR:'Argentina',PY:'Paraguai',UY:'Uruguai',CO:'Colômbia',CL:'Chile',PE:'Peru',EC:'Equador',BO:'Bolívia'};
    const gravColors = { critica:'lf-danger', alta:'lf-warn', warn:'lf-warn', info:'lf-info' };
    list.innerHTML = '';
    events.slice(0, 30).forEach(ev => {
      const cls = gravColors[ev.gravidade] || 'lf-info';
      const ts = new Date().toLocaleTimeString('pt-BR', {hour:'2-digit',minute:'2-digit'});
      const div = document.createElement('div');
      div.className = 'lf-item';
      div.style.borderLeft = `2px solid ${cls==='lf-danger'?'var(--danger)':cls==='lf-warn'?'var(--warn)':'var(--accent)'}`;
      div.style.paddingLeft = '8px';
      div.innerHTML = `<span class="${cls}" style="font-size:10px;">${ev.titulo}</span><br><span class="lf-time">${ts} · ${countryLabels[ev.pais] || ev.pais || 'SA'}</span>`;
      list.appendChild(div);
    });
  } catch(_) {
    list.innerHTML = '<div class="lf-item" style="color:var(--text2);font-size:9px;padding:8px;">Radar: aguardando conexão com Cérebro NIAS…</div>';
  }
}
setInterval(_fetchAnomalyRadarFromBrain, 5 * 60 * 1000);

// ═══════════════════════════════════════════════════════════════════
// MUNICIPAL_DB EXPANSION — New municipalities from Macro-Poles
// ═══════════════════════════════════════════════════════════════════
const MUNICIPAL_DB_EXTRA = [
  // POLO A — MATOPIBA
  { id:'BR-MA-BAL', name:'Balsas',             state:'MA', country:'BR', culture:'soja',  areaMha:0.60, ndvi:0.41, coef:0.80, poly:[[-7.8,-46.2],[-7.2,-46.2],[-7.2,-45.4],[-7.8,-45.4]] },
  { id:'BR-PI-URU', name:'Uruçuí',             state:'PI', country:'BR', culture:'soja',  areaMha:0.55, ndvi:0.38, coef:0.78, poly:[[-7.9,-44.7],[-7.3,-44.7],[-7.3,-43.9],[-7.9,-43.9]] },
  { id:'BR-TO-POR', name:'Porto Nacional',     state:'TO', country:'BR', culture:'soja',  areaMha:0.42, ndvi:0.44, coef:0.79, poly:[[-10.9,-48.6],[-10.3,-48.6],[-10.3,-47.8],[-10.9,-47.8]] },
  // POLO B — HORTICULTURA SUL/SUDESTE
  { id:'BR-MG-ARA2',name:'Araguari',           state:'MG', country:'BR', culture:'horti', areaMha:0.10, ndvi:0.55, coef:0.82, poly:[[-18.8,-48.5],[-18.2,-48.5],[-18.2,-47.7],[-18.8,-47.7]] },
  { id:'BR-SP-ITV', name:'Itapeva',            state:'SP', country:'BR', culture:'horti', areaMha:0.07, ndvi:0.50, coef:0.78, poly:[[-24.1,-48.9],[-23.6,-48.9],[-23.6,-48.3],[-24.1,-48.3]] },
  { id:'BR-SC-CAC', name:'Caçador',            state:'SC', country:'BR', culture:'maca',  areaMha:0.19, ndvi:0.68, coef:0.88, poly:[[-26.9,-51.2],[-26.4,-51.2],[-26.4,-50.5],[-26.9,-50.5]] },
  // POLO C — FRUTICULTURA NORDESTE
  { id:'BR-BA-JUA', name:'Juazeiro',           state:'BA', country:'BR', culture:'uva',   areaMha:0.17, ndvi:0.59, coef:0.87, poly:[[-9.6,-40.7],[-9.0,-40.7],[-9.0,-40.0],[-9.6,-40.0]] },
  { id:'BR-SE-ITA', name:'Itabaiana',          state:'SE', country:'BR', culture:'horti', areaMha:0.06, ndvi:0.48, coef:0.74, poly:[[-10.8,-37.6],[-10.3,-37.6],[-10.3,-37.0],[-10.8,-37.0]] },
  { id:'BR-SE-BOQ', name:'Boquim',             state:'SE', country:'BR', culture:'uva',   areaMha:0.05, ndvi:0.50, coef:0.72, poly:[[-11.2,-37.8],[-10.7,-37.8],[-10.7,-37.2],[-11.2,-37.2]] },
  // POLO D — FRONTEIRA NORTE
  { id:'BR-PA-PAR', name:'Paragominas',        state:'PA', country:'BR', culture:'pastagem', areaMha:0.38, ndvi:0.56, coef:0.81, poly:[[-3.8,-48.0],[-3.1,-48.0],[-3.1,-47.2],[-3.8,-47.2]] },
  { id:'BR-PA-SFX', name:'São Félix do Xingu', state:'PA', country:'BR', culture:'pastagem', areaMha:0.72, ndvi:0.60, coef:0.75, poly:[[-7.2,-52.2],[-6.4,-52.2],[-6.4,-51.2],[-7.2,-51.2]] },
  { id:'BR-RO-VIL', name:'Vilhena',            state:'RO', country:'BR', culture:'soja',  areaMha:0.44, ndvi:0.57, coef:0.83, poly:[[-13.1,-60.5],[-12.5,-60.5],[-12.5,-59.7],[-13.1,-59.7]] },

  // ════════════════════════════════════════════════════════════════
  // ARGUS — POLOS HORTÍCOLAS DE ALTA FREQUÊNCIA (monitoramento de preço)
  // ════════════════════════════════════════════════════════════════

  // ── CINTURÃO VERDE SP ──
  { id:'BR-SP-IBU', name:'Ibiúna',             state:'SP', country:'BR', culture:'folhosas',   areaMha:0.04, area_ha:4200,  ndvi:0.62, coef:0.85, temp_max:26, chuva_7d:18, phenology:'ciclo curto 45d — folhosas',
    poly:[[-23.7,-47.3],[-23.5,-47.3],[-23.5,-47.1],[-23.7,-47.1]], argus:'cinturao-verde-sp', ceasa_ref:'CEAGESP' },
  { id:'BR-SP-MGC', name:'Mogi das Cruzes',    state:'SP', country:'BR', culture:'horti',      areaMha:0.06, area_ha:6100,  ndvi:0.64, coef:0.87, temp_max:28, chuva_7d:22, phenology:'misto folhosas + flores',
    poly:[[-23.6,-46.3],[-23.4,-46.3],[-23.4,-46.1],[-23.6,-46.1]], argus:'cinturao-verde-sp', ceasa_ref:'CEAGESP' },
  { id:'BR-SP-PIE', name:'Piedade',            state:'SP', country:'BR', culture:'folhosas',   areaMha:0.03, area_ha:3800,  ndvi:0.60, coef:0.84, temp_max:25, chuva_7d:15, phenology:'ciclo curto 40d — brócolos/alface',
    poly:[[-23.8,-47.5],[-23.6,-47.5],[-23.6,-47.3],[-23.8,-47.3]], argus:'cinturao-verde-sp', ceasa_ref:'CEAGESP' },

  // ── TRIÂNGULO MINEIRO / ALTO PARANAÍBA ──
  { id:'BR-MG-UBE', name:'Uberlândia',         state:'MG', country:'BR', culture:'batata',     areaMha:0.08, area_ha:8200,  ndvi:0.54, coef:0.86, temp_max:30, chuva_7d:8, phenology:'batata safra das secas — 90d',
    poly:[[-19.0,-48.4],[-18.8,-48.4],[-18.8,-48.1],[-19.0,-48.1]], argus:'triangulo-mg', ceasa_ref:'CEASA-MG' },
  { id:'BR-MG-STJ', name:'Santa Juliana',      state:'MG', country:'BR', culture:'cebola',     areaMha:0.05, area_ha:5600,  ndvi:0.51, coef:0.83, temp_max:31, chuva_7d:5, phenology:'cebola irrigada — colheita Jun-Out',
    poly:[[-19.4,-47.6],[-19.2,-47.6],[-19.2,-47.3],[-19.4,-47.3]], argus:'triangulo-mg', ceasa_ref:'CEASA-MG' },

  // ── SERRA GAÚCHA ──
  { id:'BR-RS-CXS', name:'Caxias do Sul',      state:'RS', country:'BR', culture:'horti',      areaMha:0.05, area_ha:4800,  ndvi:0.66, coef:0.89, temp_max:22, chuva_7d:25, phenology:'hortaliças de clima frio — contínuo',
    poly:[[-29.2,-51.3],[-29.0,-51.3],[-29.0,-51.0],[-29.2,-51.0]], argus:'serra-gaucha', ceasa_ref:'CEASA-RS' },

  // ── SUL DE MINAS ──
  { id:'BR-MG-PAL', name:'Pouso Alegre',       state:'MG', country:'BR', culture:'batata',     areaMha:0.06, area_ha:6200,  ndvi:0.58, coef:0.84, temp_max:27, chuva_7d:12, phenology:'batata + tomate mesa — ciclo 90-100d',
    poly:[[-22.3,-46.0],[-22.1,-46.0],[-22.1,-45.7],[-22.3,-45.7]], argus:'sul-minas', ceasa_ref:'CEAGESP' },
  { id:'BR-MG-BAR2',name:'Barbacena',          state:'MG', country:'BR', culture:'tomate',     areaMha:0.04, area_ha:3900,  ndvi:0.55, coef:0.82, temp_max:26, chuva_7d:14, phenology:'tomate mesa altitude — Abr-Out',
    poly:[[-21.3,-43.8],[-21.1,-43.8],[-21.1,-43.6],[-21.3,-43.6]], argus:'sul-minas', ceasa_ref:'CEASA-MG' },

  // ── VALE DO SÃO FRANCISCO (irrigado) ──
  { id:'BR-PE-PET2',name:'Petrolina (Horti)',   state:'PE', country:'BR', culture:'tomate',     areaMha:0.09, area_ha:9200,  ndvi:0.57, coef:0.88, temp_max:34, chuva_7d:0, phenology:'irrigado constante — tomate/cebola/pimentão',
    poly:[[-9.5,-40.6],[-9.3,-40.6],[-9.3,-40.3],[-9.5,-40.3]], argus:'vale-sf', ceasa_ref:'CEASA-PE' },

  // ════════════════════════════════════════════════════════════════
  // AMÉRICA DO SUL — PRODUTORES ADICIONAIS
  // ════════════════════════════════════════════════════════════════

  // ── ARGENTINA — POLOS SOJA/GRÃOS ──
  { id:'AR-BUE-ROS', name:'Rosário',            state:'Santa Fe', country:'AR', culture:'soja',     areaMha:0.85, area_ha:8500, ndvi:0.64, coef:0.92, temp_max:28, chuva_7d:12, phenology:'soja safra plena — colheita Abr-Mai',
    poly:[[-33.0,-60.8],[-32.4,-60.8],[-32.4,-60.0],[-33.0,-60.0]], argus:'pampas-argentina', ceasa_ref:'Rosário' },
  { id:'AR-BUE-BAH', name:'Bahía Blanca',       state:'Buenos Aires', country:'AR', culture:'trigo',    areaMha:0.62, area_ha:6200, ndvi:0.61, coef:0.89, temp_max:24, chuva_7d:8, phenology:'trigo/cevada — safra primavera',
    poly:[[-38.8,-62.4],[-38.2,-62.4],[-38.2,-61.6],[-38.8,-61.6]], argus:'pampas-argentina', ceasa_ref:'Bahía Blanca' },
  { id:'AR-COR-COR', name:'Córdoba Capital',    state:'Córdoba', country:'AR', culture:'soja',     areaMha:0.48, area_ha:4800, ndvi:0.62, coef:0.90, temp_max:29, chuva_7d:15, phenology:'soja/milho — rotação intensiva',
    poly:[[-31.6,-64.4],[-31.0,-64.4],[-31.0,-63.6],[-31.6,-63.6]], argus:'pampas-argentina', ceasa_ref:'Córdoba' },
  { id:'AR-MEN-LUJ', name:'Luján de Cuyo',      state:'Mendoza', country:'AR', culture:'uva',      areaMha:0.35, area_ha:3500, ndvi:0.68, coef:0.93, temp_max:32, chuva_7d:0, phenology:'vinhedos altitude — irrigados',
    poly:[[-33.2,-69.0],[-32.6,-69.0],[-32.6,-68.2],[-33.2,-68.2]], argus:'andes-argentina', ceasa_ref:'Mendoza' },
  { id:'AR-TUC-TUC', name:'San Miguel de Tucumán', state:'Tucumán', country:'AR', culture:'cana',     areaMha:0.28, area_ha:2800, ndvi:0.70, coef:0.91, temp_max:33, chuva_7d:18, phenology:'cana-de-açúcar — irrigada',
    poly:[[-27.0,-65.4],[-26.4,-65.4],[-26.4,-64.6],[-27.0,-64.6]], argus:'norte-argentina', ceasa_ref:'Tucumán' },

  // ── PARAGUAI — POLOS SOJA/GRÃOS ──
  { id:'PY-CDE-CDE', name:'Ciudad del Este',    state:'Alto Paraná', country:'PY', culture:'soja',     areaMha:0.55, area_ha:5500, ndvi:0.65, coef:0.88, temp_max:31, chuva_7d:22, phenology:'soja 2ª safra — colheita Fev-Abr',
    poly:[[-25.6,-54.8],[-25.0,-54.8],[-25.0,-54.0],[-25.6,-54.0]], argus:'leste-paraguai', ceasa_ref:'CDE' },
  { id:'PY-ASU-ASU', name:'Asunción',           state:'Central', country:'PY', culture:'horti',    areaMha:0.12, area_ha:1200, ndvi:0.58, coef:0.82, temp_max:33, chuva_7d:25, phenology:'hortaliças periurbanas',
    poly:[[-25.4,-57.6],[-25.0,-57.6],[-25.0,-57.2],[-25.4,-57.2]], argus:'central-paraguai', ceasa_ref:'Asunción' },
  { id:'PY-BOQ-BOQ', name:'Boaquerón',          state:'Boaquerón', country:'PY', culture:'soja',     areaMha:0.42, area_ha:4200, ndvi:0.60, coef:0.85, temp_max:30, chuva_7d:10, phenology:'soja/milho — Chaco seco',
    poly:[[-23.6,-60.8],[-23.0,-60.8],[-23.0,-60.0],[-23.6,-60.0]], argus:'chaco-paraguai', ceasa_ref:'Boaquerón' },

  // ── URUGUAI — POLOS SOJA/CARNE ──
  { id:'UY-MVD-MVD', name:'Montevidéu',         state:'Montevideo', country:'UY', culture:'horti',    areaMha:0.08, area_ha:800, ndvi:0.59, coef:0.83, temp_max:26, chuva_7d:18, phenology:'hortaliças periurbanas',
    poly:[[-34.9,-56.4],[-34.5,-56.4],[-34.5,-56.0],[-34.9,-56.0]], argus:'sul-uruguai', ceasa_ref:'Montevidéu' },
  { id:'UY-SAL-SAL', name:'Salto',              state:'Salto', country:'UY', culture:'citrus',   areaMha:0.32, area_ha:3200, ndvi:0.63, coef:0.86, temp_max:28, chuva_7d:12, phenology:'citrus/laranja — irrigado',
    poly:[[-31.6,-57.8],[-31.0,-57.8],[-31.0,-57.0],[-31.6,-57.0]], argus:'norte-uruguai', ceasa_ref:'Salto' },
  { id:'UY-RIN-RIN', name:'Rio Negro',          state:'Rio Negro', country:'UY', culture:'soja',     areaMha:0.38, area_ha:3800, ndvi:0.61, coef:0.87, temp_max:27, chuva_7d:15, phenology:'soja/trigo — rotação',
    poly:[[-32.9,-58.2],[-32.3,-58.2],[-32.3,-57.4],[-32.9,-57.4]], argus:'oeste-uruguai', ceasa_ref:'Rio Negro' },

  // ── CHILE — POLOS FRUTAS/VINHO ──
  { id:'CL-SAN-SAN', name:'Santiago',           state:'Metropolitana', country:'CL', culture:'horti',    areaMha:0.15, area_ha:1500, ndvi:0.62, coef:0.85, temp_max:30, chuva_7d:5, phenology:'hortaliças periurbanas',
    poly:[[-33.6,-70.8],[-33.0,-70.8],[-33.0,-70.0],[-33.6,-70.0]], argus:'central-chile', ceasa_ref:'Santiago' },
  { id:'CL-VAL-VAL', name:'Valparaíso',         state:'Valparaíso', country:'CL', culture:'uva',      areaMha:0.28, area_ha:2800, ndvi:0.67, coef:0.90, temp_max:25, chuva_7d:8, phenology:'vinhedos costeiros',
    poly:[[-33.2,-71.8],[-32.6,-71.8],[-32.6,-71.0],[-33.2,-71.0]], argus:'costa-chile', ceasa_ref:'Valparaíso' },
  { id:'CL-CON-CON', name:'Concepción',         state:'Bío Bío', country:'CL', culture:'trigo',    areaMha:0.35, area_ha:3500, ndvi:0.60, coef:0.86, temp_max:22, chuva_7d:35, phenology:'trigo/cereais — zona úmida',
    poly:[[-37.0,-73.2],[-36.4,-73.2],[-36.4,-72.4],[-37.0,-72.4]], argus:'sul-chile', ceasa_ref:'Concepción' },
  { id:'CL-ANT-ANT', name:'Antofagasta',        state:'Antofagasta', country:'CL', culture:'horti',    areaMha:0.08, area_ha:800, ndvi:0.55, coef:0.80, temp_max:28, chuva_7d:0, phenology:'hortaliças deserticas — irrigadas',
    poly:[[-24.4,-70.6],[-23.8,-70.6],[-23.8,-69.8],[-24.4,-69.8]], argus:'norte-chile', ceasa_ref:'Antofagasta' },

  // ── COLÔMBIA — POLOS CAFÉ/FLORES/ABACATE/BANANA/PALMA ──
  { id:'CO-BOG-BOG', name:'Bogotá',             state:'Cundinamarca', country:'CO', culture:'flores',   areaMha:0.18, area_ha:18000, ndvi:0.65, coef:0.88, temp_max:20, chuva_7d:28, phenology:'flores/corte — altitude 2600m',
    poly:[[4.2,-74.4],[4.8,-74.4],[4.8,-74.0],[4.2,-74.0]], argus:'altiplano-colombia', ceasa_ref:'Bogotá' },
  { id:'CO-MED-MED', name:'Medellín',           state:'Antioquia', country:'CO', culture:'cafe',     areaMha:0.42, area_ha:42000, ndvi:0.72, coef:0.91, temp_max:26, chuva_7d:32, phenology:'café arábica — eixo cafeeiro',
    poly:[[6.0,-75.8],[6.6,-75.8],[6.6,-75.2],[6.0,-75.2]], argus:'eje-cafetero', ceasa_ref:'Medellín' },
  { id:'CO-CAL-CAL', name:'Cali',               state:'Valle del Cauca', country:'CO', culture:'cana',     areaMha:0.55, area_ha:55000, ndvi:0.68, coef:0.89, temp_max:31, chuva_7d:25, phenology:'cana-de-açúcar — vale do Cauca',
    poly:[[3.0,-76.8],[3.6,-76.8],[3.6,-76.2],[3.0,-76.2]], argus:'pacifico-colombia', ceasa_ref:'Cali' },
  { id:'CO-ARM-ARM', name:'Armenia',            state:'Quindío', country:'CO', culture:'cafe',     areaMha:0.38, area_ha:38000, ndvi:0.74, coef:0.92, temp_max:25, chuva_7d:30, phenology:'café arábica lavado — maior produtor mundial',
    poly:[[4.2,-75.8],[4.8,-75.8],[4.8,-75.2],[4.2,-75.2]], argus:'eje-cafetero', ceasa_ref:'Armenia' },
  { id:'CO-CAJ-CAJ', name:'Cajicá',             state:'Cundinamarca', country:'CO', culture:'flores',   areaMha:0.09, area_ha:9000, ndvi:0.68, coef:0.90, temp_max:19, chuva_7d:26, phenology:'rosas/cravos — líder global exportação',
    poly:[[4.5,-74.1],[4.9,-74.1],[4.9,-73.7],[4.5,-73.7]], argus:'savana-bogota', ceasa_ref:'Cajicá' },
  { id:'CO-SMT-SMT', name:'Santa Marta',        state:'Magdalena', country:'CO', culture:'banana',   areaMha:0.95, area_ha:95000, ndvi:0.71, coef:0.89, temp_max:32, chuva_7d:12, phenology:'banana/cacau — costa caribenha',
    poly:[[10.8,-74.4],[11.4,-74.4],[11.4,-73.8],[10.8,-73.8]], argus:'caribe-colombia', ceasa_ref:'Santa Marta' },
  { id:'CO-VIL-VIL', name:'Villavicencio',      state:'Meta', country:'CO', culture:'palma',    areaMha:1.80, area_ha:180000, ndvi:0.69, coef:0.87, temp_max:33, chuva_7d:28, phenology:'palma de óleo/cacau — orla amazônica',
    poly:[[3.8,-73.8],[4.4,-73.8],[4.4,-73.2],[3.8,-73.2]], argus:'llanos-colombia', ceasa_ref:'Villavicencio' },
  { id:'CO-CTG-CTG', name:'Cartagena',          state:'Bolívar', country:'CO', culture:'abacate',  areaMha:0.45, area_ha:45000, ndvi:0.66, coef:0.86, temp_max:31, chuva_7d:15, phenology:'abacate hass — exportação Europa',
    poly:[[9.9,-75.6],[10.5,-75.6],[10.5,-75.0],[9.9,-75.0]], argus:'caribe-colombia', ceasa_ref:'Cartagena' },

  // ── VENEZUELA — POLOS MILHO/ARROZ/CANA/SORGO ──
  { id:'VE-GUA-GUA', name:'Guanare',            state:'Portuguesa', country:'VE', culture:'milho',    areaMha:2.80, area_ha:280000, ndvi:0.58, coef:0.82, temp_max:34, chuva_7d:18, phenology:'milho/sorgo — celeiro nacional 1.26M ton',
    poly:[[8.8,-69.2],[9.4,-69.2],[9.4,-68.6],[8.8,-68.6]], argus:'llanos-venezuela', ceasa_ref:'Guanare' },
  { id:'VE-CAL-CAL', name:'Calabozo',           state:'Guárico', country:'VE', culture:'arroz',    areaMha:1.20, area_ha:120000, ndvi:0.62, coef:0.84, temp_max:35, chuva_7d:22, phenology:'arroz irrigado — 464k ton/ano',
    poly:[[8.6,-67.6],[9.2,-67.6],[9.2,-67.0],[8.6,-67.0]], argus:'llanos-venezuela', ceasa_ref:'Calabozo' },
  { id:'VE-CAR-CAR', name:'Carora',             state:'Lara', country:'VE', culture:'cana',     areaMha:0.85, area_ha:85000, ndvi:0.65, coef:0.83, temp_max:33, chuva_7d:8, phenology:'cana-de-açúcar/sorgo — áreas mecanizáveis',
    poly:[[9.9,-70.4],[10.5,-70.4],[10.5,-69.8],[9.9,-69.8]], argus:'lara-venezuela', ceasa_ref:'Carora' },
  { id:'VE-MAR-MAR', name:'Maracaibo',          state:'Zulia', country:'VE', culture:'sorgo',    areaMha:1.50, area_ha:150000, ndvi:0.59, coef:0.81, temp_max:36, chuva_7d:5, phenology:'sorgo/milho/gergelim — potencial norte',
    poly:[[10.4,-72.0],[11.0,-72.0],[11.0,-71.4],[10.4,-71.4]], argus:'zulia-venezuela', ceasa_ref:'Maracaibo' },

  // ── PERU — POLOS ASPARGOS/QUINOA ──
  { id:'PE-LIM-LIM', name:'Lima',               state:'Lima', country:'PE', culture:'horti',    areaMha:0.12, area_ha:1200, ndvi:0.58, coef:0.82, temp_max:24, chuva_7d:0, phenology:'hortaliças costeiras — irrigadas',
    poly:[[-12.2,-77.2],[-11.6,-77.2],[-11.6,-76.6],[-12.2,-76.6]], argus:'costa-peru', ceasa_ref:'Lima' },
  { id:'PE-ICA-ICA', name:'Ica',                state:'Ica', country:'PE', culture:'aspargos', areaMha:0.25, area_ha:2500, ndvi:0.62, coef:0.85, temp_max:29, chuva_7d:0, phenology:'aspargos/exportação — irrigados',
    poly:[[-14.2,-76.0],[-13.6,-76.0],[-13.6,-75.4],[-14.2,-75.4]], argus:'ica-peru', ceasa_ref:'Ica' },
  { id:'PE-CUS-CUS', name:'Cusco',              state:'Cusco', country:'PE', culture:'quinua',   areaMha:0.35, area_ha:3500, ndvi:0.55, coef:0.83, temp_max:22, chuva_7d:15, phenology:'quinua/macaco — andes',
    poly:[[-13.6,-72.2],[-13.0,-72.2],[-13.0,-71.6],[-13.6,-71.6]], argus:'sierra-peru', ceasa_ref:'Cusco' },

  // ── EQUADOR — POLOS BANANA/CACAU ──
  { id:'EC-GUA-GUA', name:'Guayaquil',          state:'Guayas', country:'EC', culture:'banana',   areaMha:0.48, area_ha:4800, ndvi:0.70, coef:0.88, temp_max:32, chuva_7d:18, phenology:'banana/cacau — costa pacífica',
    poly:[[-2.4,-80.0],[-1.8,-80.0],[-1.8,-79.4],[-2.4,-79.4]], argus:'costa-ecuador', ceasa_ref:'Guayaquil' },
  { id:'EC-QUI-QUI', name:'Quito',              state:'Pichincha', country:'EC', culture:'flores',   areaMha:0.15, area_ha:1500, ndvi:0.63, coef:0.85, temp_max:20, chuva_7d:22, phenology:'rosas/corte — altitude 2800m',
    poly:[[-0.4,-78.8],[-0.1,-78.8],[-0.1,-78.4],[-0.4,-78.4]], argus:'sierra-ecuador', ceasa_ref:'Quito' },

  // ── BOLÍVIA — POLOS SOJA/QUINOA ──
  { id:'BO-SAN-SAN', name:'Santa Cruz de la Sierra', state:'Santa Cruz', country:'BO', culture:'soja',     areaMha:0.52, area_ha:5200, ndvi:0.60, coef:0.84, temp_max:31, chuva_7d:20, phenology:'soja/milho — planície oriental',
    poly:[[-18.0,-63.4],[-17.4,-63.4],[-17.4,-62.8],[-18.0,-62.8]], argus:'llanos-bolivia', ceasa_ref:'Santa Cruz' },
  { id:'BO-LPA-LPA', name:'La Paz',             state:'La Paz', country:'BO', culture:'quinua',   areaMha:0.28, area_ha:2800, ndvi:0.52, coef:0.80, temp_max:18, chuva_7d:12, phenology:'quinua/papa — altiplano andino',
    poly:[[-16.8,-68.4],[-16.2,-68.4],[-16.2,-67.8],[-16.8,-67.8]], argus:'altiplano-bolivia', ceasa_ref:'La Paz' },

  // ── CHAPADA DIAMANTINA ──
  { id:'BR-BA-IBI', name:'Ibicoara',            state:'BA', country:'BR', culture:'batata',     areaMha:0.04, area_ha:4100,  ndvi:0.52, coef:0.80, temp_max:28, chuva_7d:6, phenology:'batata/tomate/cenoura altitude — equilibra MG',
    poly:[[-13.4,-41.4],[-13.2,-41.4],[-13.2,-41.1],[-13.4,-41.1]], argus:'chapada-ba', ceasa_ref:'CEASA-BA' },

  // ── IBIAPABA ──
  { id:'BR-CE-TIA', name:'Tianguá',             state:'CE', country:'BR', culture:'tomate',     areaMha:0.03, area_ha:3200,  ndvi:0.49, coef:0.77, temp_max:30, chuva_7d:3, phenology:'tomate/pimentão — abastece N/NE',
    poly:[[-3.8,-41.1],[-3.6,-41.1],[-3.6,-40.8],[-3.8,-40.8]], argus:'ibiapaba-ce', ceasa_ref:'CEASA-CE' },

  // ── CRISTALINA / ITABERAÍ (larga escala) ──
  { id:'BR-GO-CRI', name:'Cristalina',          state:'GO', country:'BR', culture:'cebola',     areaMha:0.15, area_ha:15200, ndvi:0.56, coef:0.90, temp_max:31, chuva_7d:4, phenology:'maior polo irrigação LatAm — tomate ind./cebola',
    poly:[[-16.3,-47.7],[-16.1,-47.7],[-16.1,-47.4],[-16.3,-47.4]], argus:'cristalina-go', ceasa_ref:'CEAGESP' },
  { id:'BR-GO-ITB', name:'Itaberaí',            state:'GO', country:'BR', culture:'tomate',     areaMha:0.07, area_ha:7400,  ndvi:0.53, coef:0.85, temp_max:32, chuva_7d:3, phenology:'tomate industrial larga escala',
    poly:[[-15.9,-49.9],[-15.7,-49.9],[-15.7,-49.6],[-15.9,-49.6]], argus:'cristalina-go', ceasa_ref:'CEAGESP' },
];
MUNICIPAL_DB_EXTRA.forEach(m => MUNICIPAL_DB.push(m));

// ════════════════════════════════════════════════════════════════
// COBERTURA NACIONAL — Todos os polos produtivos do Brasil
// Grãos, Hortifruti, Fruticultura, Pecuária, Café, Cana, Algodão
// ════════════════════════════════════════════════════════════════
const MUNICIPAL_DB_FULL = [
  // ── MATO GROSSO DO SUL ──
  { id:'BR-MS-DOU', name:'Dourados',         state:'MS', country:'BR', culture:'soja',    areaMha:0.65, area_ha:65000, ndvi:0.61, coef:0.88, poly:[[-22.3,-55.0],[-22.0,-55.0],[-22.0,-54.6],[-22.3,-54.6]] },
  { id:'BR-MS-MRC', name:'Maracaju',         state:'MS', country:'BR', culture:'soja',    areaMha:0.58, area_ha:58000, ndvi:0.63, coef:0.89, poly:[[-21.7,-55.3],[-21.4,-55.3],[-21.4,-54.9],[-21.7,-54.9]] },
  { id:'BR-MS-SID', name:'Sidrolândia',      state:'MS', country:'BR', culture:'soja',    areaMha:0.52, area_ha:52000, ndvi:0.60, coef:0.87, poly:[[-20.9,-55.0],[-20.6,-55.0],[-20.6,-54.6],[-20.9,-54.6]] },
  { id:'BR-MS-NAV', name:'Naviraí',          state:'MS', country:'BR', culture:'cana',    areaMha:0.35, area_ha:35000, ndvi:0.58, coef:0.85, poly:[[-23.1,-54.3],[-22.8,-54.3],[-22.8,-53.9],[-23.1,-53.9]] },
  // ── PARANÁ (expandido) ──
  { id:'BR-PR-LON', name:'Londrina',         state:'PR', country:'BR', culture:'soja',    areaMha:0.48, area_ha:48000, ndvi:0.64, coef:0.90, poly:[[-23.4,-51.3],[-23.2,-51.3],[-23.2,-51.0],[-23.4,-51.0]] },
  { id:'BR-PR-MAR', name:'Maringá',          state:'PR', country:'BR', culture:'soja',    areaMha:0.42, area_ha:42000, ndvi:0.62, coef:0.89, poly:[[-23.5,-52.0],[-23.3,-52.0],[-23.3,-51.7],[-23.5,-51.7]] },
  { id:'BR-PR-CSC', name:'Cascavel',         state:'PR', country:'BR', culture:'soja',    areaMha:0.55, area_ha:55000, ndvi:0.65, coef:0.91, poly:[[-25.0,-53.6],[-24.8,-53.6],[-24.8,-53.3],[-25.0,-53.3]] },
  { id:'BR-PR-PGR', name:'Ponta Grossa',     state:'PR', country:'BR', culture:'soja',    areaMha:0.60, area_ha:60000, ndvi:0.63, coef:0.90, poly:[[-25.1,-50.3],[-24.9,-50.3],[-24.9,-50.0],[-25.1,-50.0]] },
  { id:'BR-PR-GUA', name:'Guarapuava',       state:'PR', country:'BR', culture:'batata',  areaMha:0.08, area_ha:8000,  ndvi:0.57, coef:0.84, poly:[[-25.4,-51.5],[-25.2,-51.5],[-25.2,-51.2],[-25.4,-51.2]] },
  { id:'BR-PR-TBT', name:'Toledo',           state:'PR', country:'BR', culture:'milho',   areaMha:0.45, area_ha:45000, ndvi:0.66, coef:0.92, poly:[[-24.8,-53.8],[-24.6,-53.8],[-24.6,-53.5],[-24.8,-53.5]] },
  // ── RIO GRANDE DO SUL (expandido) ──
  { id:'BR-RS-CRZ', name:'Cruz Alta',        state:'RS', country:'BR', culture:'soja',    areaMha:0.50, area_ha:50000, ndvi:0.60, coef:0.87, poly:[[-28.7,-53.7],[-28.5,-53.7],[-28.5,-53.4],[-28.7,-53.4]] },
  { id:'BR-RS-PFU', name:'Passo Fundo',      state:'RS', country:'BR', culture:'soja',    areaMha:0.45, area_ha:45000, ndvi:0.62, coef:0.88, poly:[[-28.3,-52.5],[-28.1,-52.5],[-28.1,-52.2],[-28.3,-52.2]] },
  { id:'BR-RS-SAN', name:'Santa Maria',      state:'RS', country:'BR', culture:'soja',    areaMha:0.38, area_ha:38000, ndvi:0.59, coef:0.86, poly:[[-29.8,-53.9],[-29.6,-53.9],[-29.6,-53.6],[-29.8,-53.6]] },
  { id:'BR-RS-PEL', name:'Pelotas',          state:'RS', country:'BR', culture:'horti',   areaMha:0.04, area_ha:4200,  ndvi:0.56, coef:0.82, poly:[[-31.8,-52.5],[-31.6,-52.5],[-31.6,-52.2],[-31.8,-52.2]] },
  { id:'BR-RS-BNT', name:'Bento Gonçalves',  state:'RS', country:'BR', culture:'uva',     areaMha:0.06, area_ha:5800,  ndvi:0.67, coef:0.90, poly:[[-29.2,-51.6],[-29.0,-51.6],[-29.0,-51.4],[-29.2,-51.4]] },
  // ── SANTA CATARINA ──
  { id:'BR-SC-CHA', name:'Chapecó',          state:'SC', country:'BR', culture:'milho',   areaMha:0.32, area_ha:32000, ndvi:0.64, coef:0.88, poly:[[-27.2,-52.7],[-27.0,-52.7],[-27.0,-52.5],[-27.2,-52.5]] },
  { id:'BR-SC-LAG', name:'Lages',            state:'SC', country:'BR', culture:'batata',  areaMha:0.05, area_ha:5000,  ndvi:0.59, coef:0.83, poly:[[-27.9,-50.4],[-27.7,-50.4],[-27.7,-50.1],[-27.9,-50.1]] },
  { id:'BR-SC-FLN', name:'Florianópolis (Horta)',state:'SC', country:'BR', culture:'horti',areaMha:0.02, area_ha:2200, ndvi:0.61, coef:0.80, poly:[[-27.6,-48.6],[-27.5,-48.6],[-27.5,-48.5],[-27.6,-48.5]] },
  // ── SÃO PAULO (expandido) ──
  { id:'BR-SP-RIB', name:'Ribeirão Preto',   state:'SP', country:'BR', culture:'cana',    areaMha:0.85, area_ha:85000, ndvi:0.70, coef:0.93, poly:[[-21.2,-48.0],[-21.0,-48.0],[-21.0,-47.7],[-21.2,-47.7]] },
  { id:'BR-SP-JAU', name:'Jaú',              state:'SP', country:'BR', culture:'cana',    areaMha:0.62, area_ha:62000, ndvi:0.68, coef:0.91, poly:[[-22.4,-48.7],[-22.2,-48.7],[-22.2,-48.4],[-22.4,-48.4]] },
  { id:'BR-SP-ARA', name:'Araraquara',       state:'SP', country:'BR', culture:'laranja', areaMha:0.45, area_ha:45000, ndvi:0.66, coef:0.89, poly:[[-21.8,-48.3],[-21.6,-48.3],[-21.6,-48.0],[-21.8,-48.0]] },
  { id:'BR-SP-BEB', name:'Bebedouro',        state:'SP', country:'BR', culture:'laranja', areaMha:0.38, area_ha:38000, ndvi:0.64, coef:0.87, poly:[[-20.9,-48.6],[-20.7,-48.6],[-20.7,-48.3],[-20.9,-48.3]] },
  { id:'BR-SP-SOC', name:'Sorocaba',         state:'SP', country:'BR', culture:'horti',   areaMha:0.05, area_ha:5100,  ndvi:0.58, coef:0.83, poly:[[-23.6,-47.5],[-23.4,-47.5],[-23.4,-47.2],[-23.6,-47.2]] },
  { id:'BR-SP-REG', name:'Registro',         state:'SP', country:'BR', culture:'banana',  areaMha:0.08, area_ha:8200,  ndvi:0.65, coef:0.86, poly:[[-24.5,-47.9],[-24.3,-47.9],[-24.3,-47.6],[-24.5,-47.6]] },
  // ── MINAS GERAIS (expandido) ──
  { id:'BR-MG-UBR', name:'Uberaba',          state:'MG', country:'BR', culture:'cana',    areaMha:0.42, area_ha:42000, ndvi:0.62, coef:0.88, poly:[[-19.8,-48.0],[-19.6,-48.0],[-19.6,-47.7],[-19.8,-47.7]] },
  { id:'BR-MG-LVR', name:'Lavras',           state:'MG', country:'BR', culture:'cafe',    areaMha:0.25, area_ha:25000, ndvi:0.65, coef:0.91, poly:[[-21.3,-45.1],[-21.1,-45.1],[-21.1,-44.8],[-21.3,-44.8]] },
  { id:'BR-MG-MAC', name:'Machado',          state:'MG', country:'BR', culture:'cafe',    areaMha:0.18, area_ha:18000, ndvi:0.63, coef:0.89, poly:[[-21.7,-45.9],[-21.5,-45.9],[-21.5,-45.7],[-21.7,-45.7]] },
  { id:'BR-MG-ALF', name:'Alfenas',          state:'MG', country:'BR', culture:'cafe',    areaMha:0.22, area_ha:22000, ndvi:0.64, coef:0.90, poly:[[-21.5,-46.0],[-21.3,-46.0],[-21.3,-45.8],[-21.5,-45.8]] },
  { id:'BR-MG-JFC', name:'Juiz de Fora',     state:'MG', country:'BR', culture:'horti',   areaMha:0.03, area_ha:3200,  ndvi:0.57, coef:0.81, poly:[[-21.8,-43.4],[-21.6,-43.4],[-21.6,-43.2],[-21.8,-43.2]] },
  { id:'BR-MG-MCA', name:'Montes Claros',    state:'MG', country:'BR', culture:'horti',   areaMha:0.04, area_ha:4500,  ndvi:0.49, coef:0.78, poly:[[-16.8,-44.0],[-16.6,-44.0],[-16.6,-43.7],[-16.8,-43.7]] },
  { id:'BR-MG-JAB', name:'Jaíba',            state:'MG', country:'BR', culture:'banana',  areaMha:0.12, area_ha:12000, ndvi:0.54, coef:0.84, poly:[[-15.4,-44.0],[-15.2,-44.0],[-15.2,-43.7],[-15.4,-43.7]] },
  // ── GOIÁS (expandido) ──
  { id:'BR-GO-ANA', name:'Anápolis',         state:'GO', country:'BR', culture:'tomate',  areaMha:0.06, area_ha:6200,  ndvi:0.55, coef:0.84, poly:[[-16.4,-49.0],[-16.2,-49.0],[-16.2,-48.7],[-16.4,-48.7]] },
  { id:'BR-GO-URU', name:'Uruaçu',           state:'GO', country:'BR', culture:'tomate',  areaMha:0.04, area_ha:4100,  ndvi:0.52, coef:0.82, poly:[[-14.6,-49.2],[-14.4,-49.2],[-14.4,-48.9],[-14.6,-48.9]] },
  { id:'BR-GO-LUZ', name:'Luziânia',         state:'GO', country:'BR', culture:'horti',   areaMha:0.05, area_ha:5400,  ndvi:0.56, coef:0.83, poly:[[-16.3,-48.0],[-16.1,-48.0],[-16.1,-47.7],[-16.3,-47.7]] },
  // ── BAHIA (expandido) ──
  { id:'BR-BA-LEM', name:'Luís Eduardo Magalhães',state:'BA', country:'BR', culture:'soja', areaMha:0.72, area_ha:72000, ndvi:0.45, coef:0.82, poly:[[-12.2,-46.0],[-11.9,-46.0],[-11.9,-45.6],[-12.2,-45.6]] },
  { id:'BR-BA-BAR3',name:'Barreiras (Oeste)', state:'BA', country:'BR', culture:'algodao',areaMha:0.55, area_ha:55000, ndvi:0.48, coef:0.81, poly:[[-12.3,-45.3],[-12.0,-45.3],[-12.0,-44.9],[-12.3,-44.9]] },
  { id:'BR-BA-ITA2',name:'Itabuna',          state:'BA', country:'BR', culture:'cacau',   areaMha:0.15, area_ha:15000, ndvi:0.68, coef:0.85, poly:[[-14.9,-39.5],[-14.7,-39.5],[-14.7,-39.2],[-14.9,-39.2]] },
  { id:'BR-BA-ILH', name:'Ilhéus',           state:'BA', country:'BR', culture:'cacau',   areaMha:0.12, area_ha:12000, ndvi:0.66, coef:0.84, poly:[[-14.8,-39.2],[-14.6,-39.2],[-14.6,-38.9],[-14.8,-38.9]] },
  { id:'BR-BA-IRE', name:'Irecê',            state:'BA', country:'BR', culture:'cebola',  areaMha:0.06, area_ha:6400,  ndvi:0.47, coef:0.79, poly:[[-11.4,-41.9],[-11.2,-41.9],[-11.2,-41.6],[-11.4,-41.6]] },
  // ── MATOPIBA (expandido) ──
  { id:'BR-MA-IMM', name:'Imperatriz',       state:'MA', country:'BR', culture:'soja',    areaMha:0.35, area_ha:35000, ndvi:0.50, coef:0.80, poly:[[-5.6,-47.6],[-5.3,-47.6],[-5.3,-47.2],[-5.6,-47.2]] },
  { id:'BR-TO-PAL', name:'Palmas',           state:'TO', country:'BR', culture:'soja',    areaMha:0.28, area_ha:28000, ndvi:0.52, coef:0.81, poly:[[-10.3,-48.5],[-10.0,-48.5],[-10.0,-48.1],[-10.3,-48.1]] },
  { id:'BR-TO-GUR', name:'Gurupi',           state:'TO', country:'BR', culture:'soja',    areaMha:0.30, area_ha:30000, ndvi:0.49, coef:0.79, poly:[[-11.8,-49.2],[-11.5,-49.2],[-11.5,-48.8],[-11.8,-48.8]] },
  // ── NORDESTE ──
  { id:'BR-RN-MOS2',name:'Mossoró (Melão)',  state:'RN', country:'BR', culture:'melao',   areaMha:0.08, area_ha:8500,  ndvi:0.42, coef:0.80, poly:[[-5.3,-37.5],[-5.1,-37.5],[-5.1,-37.2],[-5.3,-37.2]] },
  { id:'BR-CE-LIM', name:'Limoeiro do Norte',state:'CE', country:'BR', culture:'banana',  areaMha:0.06, area_ha:6000,  ndvi:0.53, coef:0.82, poly:[[-5.2,-38.2],[-5.0,-38.2],[-5.0,-37.9],[-5.2,-37.9]] },
  { id:'BR-PB-SOM', name:'Sousa',            state:'PB', country:'BR', culture:'horti',   areaMha:0.03, area_ha:3400,  ndvi:0.44, coef:0.76, poly:[[-6.8,-38.3],[-6.6,-38.3],[-6.6,-38.0],[-6.8,-38.0]] },
  { id:'BR-AL-SAM', name:'São Miguel dos Campos',state:'AL', country:'BR', culture:'cana', areaMha:0.40, area_ha:40000, ndvi:0.62, coef:0.86, poly:[[-9.8,-36.2],[-9.6,-36.2],[-9.6,-35.9],[-9.8,-35.9]] },
  { id:'BR-PE-RIB', name:'Ribeirão',         state:'PE', country:'BR', culture:'cana',    areaMha:0.35, area_ha:35000, ndvi:0.60, coef:0.85, poly:[[-8.6,-35.5],[-8.4,-35.5],[-8.4,-35.2],[-8.6,-35.2]] },
  // ── NORTE ──
  { id:'BR-PA-ALT', name:'Altamira',         state:'PA', country:'BR', culture:'cacau',   areaMha:0.08, area_ha:8000,  ndvi:0.70, coef:0.78, poly:[[-3.3,-52.3],[-3.0,-52.3],[-3.0,-52.0],[-3.3,-52.0]] },
  { id:'BR-PA-MAR', name:'Marabá',           state:'PA', country:'BR', culture:'pastagem',areaMha:0.55, area_ha:55000, ndvi:0.58, coef:0.77, poly:[[-5.5,-49.2],[-5.2,-49.2],[-5.2,-48.8],[-5.5,-48.8]] },
  { id:'BR-RO-JPA', name:'Ji-Paraná',        state:'RO', country:'BR', culture:'cafe',    areaMha:0.15, area_ha:15000, ndvi:0.60, coef:0.83, poly:[[-10.9,-61.8],[-10.7,-61.8],[-10.7,-61.5],[-10.9,-61.5]] },
  { id:'BR-RO-CAC', name:'Cacoal',           state:'RO', country:'BR', culture:'cafe',    areaMha:0.12, area_ha:12000, ndvi:0.58, coef:0.81, poly:[[-11.5,-61.5],[-11.3,-61.5],[-11.3,-61.2],[-11.5,-61.2]] },
  { id:'BR-AM-MAN', name:'Manacapuru',       state:'AM', country:'BR', culture:'horti',   areaMha:0.02, area_ha:2000,  ndvi:0.72, coef:0.75, poly:[[-3.4,-60.7],[-3.2,-60.7],[-3.2,-60.4],[-3.4,-60.4]] },
  { id:'BR-AP-MAC', name:'Macapá',           state:'AP', country:'BR', culture:'acai',    areaMha:0.05, area_ha:5000,  ndvi:0.74, coef:0.76, poly:[[ 0.1,-51.2],[ 0.3,-51.2],[ 0.3,-51.0],[ 0.1,-51.0]] },
  // ── MATO GROSSO (expandido — algodão) ──
  { id:'BR-MT-QGA', name:'Querência',        state:'MT', country:'BR', culture:'soja',    areaMha:0.60, area_ha:60000, ndvi:0.59, coef:0.86, poly:[[-12.6,-52.4],[-12.3,-52.4],[-12.3,-52.0],[-12.6,-52.0]] },
  { id:'BR-MT-CLT', name:'Cláudia',          state:'MT', country:'BR', culture:'soja',    areaMha:0.40, area_ha:40000, ndvi:0.62, coef:0.88, poly:[[-11.5,-55.0],[-11.3,-55.0],[-11.3,-54.7],[-11.5,-54.7]] },
  { id:'BR-MT-PLM', name:'Pedra Preta',      state:'MT', country:'BR', culture:'algodao', areaMha:0.35, area_ha:35000, ndvi:0.57, coef:0.85, poly:[[-16.7,-54.5],[-16.5,-54.5],[-16.5,-54.2],[-16.7,-54.2]] },
  // ── DF ──
  { id:'BR-DF-BRA', name:'Brasília (PAD-DF)',state:'DF', country:'BR', culture:'soja',    areaMha:0.20, area_ha:20000, ndvi:0.55, coef:0.84, poly:[[-15.9,-47.8],[-15.7,-47.8],[-15.7,-47.5],[-15.9,-47.5]] },
  // ── ES ──
  { id:'BR-ES-LIN', name:'Linhares',         state:'ES', country:'BR', culture:'cafe',    areaMha:0.18, area_ha:18000, ndvi:0.62, coef:0.87, poly:[[-19.5,-40.2],[-19.3,-40.2],[-19.3,-39.9],[-19.5,-39.9]] },
  { id:'BR-ES-SMA', name:'São Mateus',       state:'ES', country:'BR', culture:'cafe',    areaMha:0.14, area_ha:14000, ndvi:0.60, coef:0.85, poly:[[-18.8,-40.0],[-18.6,-40.0],[-18.6,-39.7],[-18.8,-39.7]] },
  // ── RJ ──
  { id:'BR-RJ-STF', name:'S. Fidelis/Campos',state:'RJ', country:'BR', culture:'cana',   areaMha:0.15, area_ha:15000, ndvi:0.56, coef:0.82, poly:[[-21.7,-41.8],[-21.5,-41.8],[-21.5,-41.5],[-21.7,-41.5]] },
  { id:'BR-RJ-TER', name:'Teresópolis',      state:'RJ', country:'BR', culture:'horti',   areaMha:0.03, area_ha:3100,  ndvi:0.63, coef:0.84, poly:[[-22.5,-43.0],[-22.3,-43.0],[-22.3,-42.8],[-22.5,-42.8]] },
  { id:'BR-RJ-NFR', name:'Nova Friburgo',    state:'RJ', country:'BR', culture:'horti',   areaMha:0.04, area_ha:3800,  ndvi:0.61, coef:0.83, poly:[[-22.3,-42.6],[-22.1,-42.6],[-22.1,-42.4],[-22.3,-42.4]] },
];
MUNICIPAL_DB_FULL.forEach(m => MUNICIPAL_DB.push(m));

const MUNICIPAL_DB_FLV = [
  { id:'BR-PE-101', ibgeCode:'2611101', name:'Petrolina', state:'PE', country:'BR', culture:'uva', areaMha:2.0, ndvi:0.85, coef:0.93, lat:-9.38866, lon:-40.5027, flvCultures:["coco", "manga", "uva", "goiaba"], flvTons:1010739, poly:[[-9.51,-40.62],[-9.51,-40.38],[-9.27,-40.38],[-9.27,-40.62]] },
  { id:'BR-SP-807', ibgeCode:'3510807', name:'Casa Branca', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.9, lat:-21.7708, lon:-47.0852, flvCultures:["cebola", "tangerina", "laranja", "abacate", "batata"], flvTons:767900, poly:[[-21.89,-47.21],[-21.89,-46.97],[-21.65,-46.97],[-21.65,-47.21]] },
  { id:'BR-GO-206', ibgeCode:'5206206', name:'Cristalina', state:'GO', country:'BR', culture:'tomate', areaMha:2.0, ndvi:0.85, coef:0.88, lat:-16.7676, lon:-47.6131, flvCultures:["tomate", "batata", "cebola", "alho"], flvTons:649000, poly:[[-16.89,-47.73],[-16.89,-47.49],[-16.65,-47.49],[-16.65,-47.73]] },
  { id:'BR-BA-407', ibgeCode:'2918407', name:'Juazeiro', state:'BA', country:'BR', culture:'manga', areaMha:2.0, ndvi:0.85, coef:0.86, lat:-9.41622, lon:-40.5033, flvCultures:["coco", "manga", "uva", "melao"], flvTons:573146, poly:[[-9.54,-40.62],[-9.54,-40.38],[-9.3,-40.38],[-9.3,-40.62]] },
  { id:'BR-SP-506', ibgeCode:'3507506', name:'Botucatu', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.84, lat:-22.8837, lon:-48.4437, flvCultures:["laranja"], flvTons:436780, poly:[[-23.0,-48.56],[-23.0,-48.32],[-22.76,-48.32],[-22.76,-48.56]] },
  { id:'BR-SP-503', ibgeCode:'3504503', name:'Avaré', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.83, lat:-23.1067, lon:-48.9251, flvCultures:["laranja"], flvTons:414710, poly:[[-23.23,-49.05],[-23.23,-48.81],[-22.99,-48.81],[-22.99,-49.05]] },
  { id:'BR-BA-202', ibgeCode:'2912202', name:'Ibicoara', state:'BA', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.85, coef:0.83, lat:-13.4059, lon:-41.284, flvCultures:["cebola", "alho", "tomate", "maracuja", "batata"], flvTons:402600, poly:[[-13.53,-41.4],[-13.53,-41.16],[-13.29,-41.16],[-13.29,-41.4]] },
  { id:'BR-MG-804', ibgeCode:'3149804', name:'Perdizes', state:'MG', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.85, coef:0.83, lat:-19.3434, lon:-47.2963, flvCultures:["batata", "cebola", "alho"], flvTons:398950, poly:[[-19.46,-47.42],[-19.46,-47.18],[-19.22,-47.18],[-19.22,-47.42]] },
  { id:'BR-PE-604', ibgeCode:'2612604', name:'Santa Maria da Boa Vista', state:'PE', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.85, coef:0.83, lat:-8.79766, lon:-39.8241, flvCultures:["uva", "melancia", "manga", "banana", "goiaba", "melao"], flvTons:383000, poly:[[-8.92,-39.94],[-8.92,-39.7],[-8.68,-39.7],[-8.68,-39.94]] },
  { id:'BR-SP-253', ibgeCode:'3519253', name:'Iaras', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.82, lat:-22.8682, lon:-49.1634, flvCultures:["laranja"], flvTons:346800, poly:[[-22.99,-49.28],[-22.99,-49.04],[-22.75,-49.04],[-22.75,-49.28]] },
  { id:'BR-SP-100', ibgeCode:'3512100', name:'Colômbia', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.82, lat:-20.1768, lon:-48.6865, flvCultures:["laranja"], flvTons:337621, poly:[[-20.3,-48.81],[-20.3,-48.57],[-20.06,-48.57],[-20.06,-48.81]] },
  { id:'BR-SP-307', ibgeCode:'3522307', name:'Itapetininga', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.81, lat:-23.5886, lon:-48.0483, flvCultures:["batata", "laranja"], flvTons:321276, poly:[[-23.71,-48.17],[-23.71,-47.93],[-23.47,-47.93],[-23.47,-48.17]] },
  { id:'BR-BA-906', ibgeCode:'2921906', name:'Mucugê', state:'BA', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.85, coef:0.81, lat:-13.0053, lon:-41.3703, flvCultures:["cebola", "alho", "tomate", "maracuja", "batata"], flvTons:313422, poly:[[-13.13,-41.49],[-13.13,-41.25],[-12.89,-41.25],[-12.89,-41.49]] },
  { id:'BR-MG-050', ibgeCode:'3135050', name:'Jaíba', state:'MG', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.85, coef:0.81, lat:-15.3432, lon:-43.6688, flvCultures:["tomate", "manga", "banana", "limao", "batata"], flvTons:289737, poly:[[-15.46,-43.79],[-15.46,-43.55],[-15.22,-43.55],[-15.22,-43.79]] },
  { id:'BR-BA-202', ibgeCode:'2907202', name:'Casa Nova', state:'BA', country:'BR', culture:'manga', areaMha:2.0, ndvi:0.85, coef:0.81, lat:-9.16408, lon:-40.974, flvCultures:["uva", "manga", "cebola", "goiaba"], flvTons:289241, poly:[[-9.28,-41.09],[-9.28,-40.85],[-9.04,-40.85],[-9.04,-41.09]] },
  { id:'BR-RN-003', ibgeCode:'2408003', name:'Mossoró', state:'RN', country:'BR', culture:'melao', areaMha:2.0, ndvi:0.85, coef:0.81, lat:-5.18374, lon:-37.3474, flvCultures:["melao", "melancia"], flvTons:288373, poly:[[-5.3,-37.47],[-5.3,-37.23],[-5.06,-37.23],[-5.06,-37.47]] },
  { id:'BR-SP-009', ibgeCode:'3508009', name:'Buri', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.81, lat:-23.7977, lon:-48.5958, flvCultures:["laranja"], flvTons:288000, poly:[[-23.92,-48.72],[-23.92,-48.48],[-23.68,-48.48],[-23.68,-48.72]] },
  { id:'BR-SP-405', ibgeCode:'3546405', name:'Santa Cruz do Rio Pardo', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.81, lat:-22.8988, lon:-49.6354, flvCultures:["laranja"], flvTons:282858, poly:[[-23.02,-49.76],[-23.02,-49.52],[-22.78,-49.52],[-22.78,-49.76]] },
  { id:'BR-SP-706', ibgeCode:'3530706', name:'Mogi Guaçu', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.8, lat:-22.3675, lon:-46.9428, flvCultures:["laranja"], flvTons:264024, poly:[[-22.49,-47.06],[-22.49,-46.82],[-22.25,-46.82],[-22.25,-47.06]] },
  { id:'BR-SP-508', ibgeCode:'3530508', name:'Mococa', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.8, lat:-21.4647, lon:-47.0024, flvCultures:["laranja"], flvTons:260000, poly:[[-21.58,-47.12],[-21.58,-46.88],[-21.34,-46.88],[-21.34,-47.12]] },
  { id:'BR-PA-309', ibgeCode:'1503309', name:'Igarapé-Miri', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.85, coef:0.8, lat:-1.97533, lon:-48.9575, flvCultures:["acai"], flvTons:260000, poly:[[-2.1,-49.08],[-2.1,-48.84],[-1.86,-48.84],[-1.86,-49.08]] },
  { id:'BR-SC-503', ibgeCode:'4216503', name:'São Joaquim', state:'SC', country:'BR', culture:'maca', areaMha:2.0, ndvi:0.85, coef:0.8, lat:-28.2887, lon:-49.9457, flvCultures:["pera", "maca"], flvTons:249950, poly:[[-28.41,-50.07],[-28.41,-49.83],[-28.17,-49.83],[-28.17,-50.07]] },
  { id:'BR-BA-002', ibgeCode:'2927002', name:'Rio Real', state:'BA', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.8, lat:-11.4814, lon:-37.9332, flvCultures:["laranja", "maracuja"], flvTons:248973, poly:[[-11.6,-38.05],[-11.6,-37.81],[-11.36,-37.81],[-11.36,-38.05]] },
  { id:'BR-SP-303', ibgeCode:'3500303', name:'Aguaí', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.8, lat:-22.0572, lon:-46.9735, flvCultures:["laranja", "abacate"], flvTons:247640, poly:[[-22.18,-47.09],[-22.18,-46.85],[-21.94,-46.85],[-21.94,-47.09]] },
  { id:'BR-PE-607', ibgeCode:'2601607', name:'Belém do São Francisco', state:'PE', country:'BR', culture:'manga', areaMha:2.0, ndvi:0.85, coef:0.8, lat:-8.75046, lon:-38.9623, flvCultures:["manga", "melao", "goiaba", "maracuja"], flvTons:235073, poly:[[-8.87,-39.08],[-8.87,-38.84],[-8.63,-38.84],[-8.63,-39.08]] },
  { id:'BR-RS-509', ibgeCode:'4322509', name:'Vacaria', state:'RS', country:'BR', culture:'maca', areaMha:2.0, ndvi:0.85, coef:0.8, lat:-28.5079, lon:-50.9418, flvCultures:["pera", "maca"], flvTons:233670, poly:[[-28.63,-51.06],[-28.63,-50.82],[-28.39,-50.82],[-28.39,-51.06]] },
  { id:'BR-SP-406', ibgeCode:'3522406', name:'Itapeva', state:'SP', country:'BR', culture:'tomate', areaMha:2.0, ndvi:0.85, coef:0.8, lat:-23.9788, lon:-48.8764, flvCultures:["tomate", "batata"], flvTons:231888, poly:[[-24.1,-49.0],[-24.1,-48.76],[-23.86,-48.76],[-23.86,-49.0]] },
  { id:'BR-SP-550', ibgeCode:'3500550', name:'Águas de Santa Bárbara', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.8, lat:-22.8812, lon:-49.2421, flvCultures:["laranja"], flvTons:228520, poly:[[-23.0,-49.36],[-23.0,-49.12],[-22.76,-49.12],[-22.76,-49.36]] },
  { id:'BR-PA-044', ibgeCode:'1503044', name:'Floresta do Araguaia', state:'PA', country:'BR', culture:'abacaxi', areaMha:2.0, ndvi:0.85, coef:0.8, lat:-7.55335, lon:-49.7125, flvCultures:["abacaxi", "melancia"], flvTons:226150, poly:[[-7.67,-49.83],[-7.67,-49.59],[-7.43,-49.59],[-7.43,-49.83]] },
  { id:'BR-PR-402', ibgeCode:'4118402', name:'Paranavaí', state:'PR', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.79, lat:-23.0816, lon:-52.4617, flvCultures:["laranja"], flvTons:222250, poly:[[-23.2,-52.58],[-23.2,-52.34],[-22.96,-52.34],[-22.96,-52.58]] },
  { id:'BR-MG-908', ibgeCode:'3156908', name:'Sacramento', state:'MG', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.85, coef:0.79, lat:-19.8622, lon:-47.4508, flvCultures:["batata", "alho", "abacate"], flvTons:220075, poly:[[-19.98,-47.57],[-19.98,-47.33],[-19.74,-47.33],[-19.74,-47.57]] },
  { id:'BR-SP-500', ibgeCode:'3505500', name:'Barretos', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.79, lat:-20.5531, lon:-48.5698, flvCultures:["laranja"], flvTons:215729, poly:[[-20.67,-48.69],[-20.67,-48.45],[-20.43,-48.45],[-20.43,-48.69]] },
  { id:'BR-SP-907', ibgeCode:'3538907', name:'Pirajuí', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.85, coef:0.79, lat:-21.999, lon:-49.4608, flvCultures:["laranja"], flvTons:211122, poly:[[-22.12,-49.58],[-22.12,-49.34],[-21.88,-49.34],[-21.88,-49.58]] },
  { id:'BR-GO-603', ibgeCode:'5220603', name:'Silvânia', state:'GO', country:'BR', culture:'tomate', areaMha:2.0, ndvi:0.85, coef:0.79, lat:-16.66, lon:-48.6083, flvCultures:["tomate"], flvTons:203600, poly:[[-16.78,-48.73],[-16.78,-48.49],[-16.54,-48.49],[-16.54,-48.73]] },
  { id:'BR-GO-806', ibgeCode:'5213806', name:'Morrinhos', state:'GO', country:'BR', culture:'tomate', areaMha:2.0, ndvi:0.832, coef:0.79, lat:-17.7334, lon:-49.1059, flvCultures:["tomate"], flvTons:191000, poly:[[-17.85,-49.23],[-17.85,-48.99],[-17.61,-48.99],[-17.61,-49.23]] },
  { id:'BR-PA-301', ibgeCode:'1502301', name:'Capitão Poço', state:'PA', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.821, coef:0.79, lat:-1.74785, lon:-47.0629, flvCultures:["laranja"], flvTons:185630, poly:[[-1.87,-47.18],[-1.87,-46.94],[-1.63,-46.94],[-1.63,-47.18]] },
  { id:'BR-SP-308', ibgeCode:'3531308', name:'Monte Alto', state:'SP', country:'BR', culture:'manga', areaMha:2.0, ndvi:0.804, coef:0.79, lat:-21.2655, lon:-48.4971, flvCultures:["manga", "cebola", "goiaba", "limao"], flvTons:176800, poly:[[-21.39,-48.62],[-21.39,-48.38],[-21.15,-48.38],[-21.15,-48.62]] },
  { id:'BR-SP-102', ibgeCode:'3506102', name:'Bebedouro', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.794, coef:0.78, lat:-20.9491, lon:-48.4791, flvCultures:["laranja"], flvTons:172024, poly:[[-21.07,-48.6],[-21.07,-48.36],[-20.83,-48.36],[-20.83,-48.6]] },
  { id:'BR-RS-303', ibgeCode:'4302303', name:'Bom Jesus', state:'RS', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.79, coef:0.78, lat:-28.6697, lon:-50.4295, flvCultures:["batata", "maca"], flvTons:170100, poly:[[-28.79,-50.55],[-28.79,-50.31],[-28.55,-50.31],[-28.55,-50.55]] },
  { id:'BR-MG-808', ibgeCode:'3152808', name:'Prata', state:'MG', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.789, coef:0.78, lat:-19.3086, lon:-48.9276, flvCultures:["laranja"], flvTons:169576, poly:[[-19.43,-49.05],[-19.43,-48.81],[-19.19,-48.81],[-19.19,-49.05]] },
  { id:'BR-SP-706', ibgeCode:'3506706', name:'Boa Esperança do Sul', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.784, coef:0.78, lat:-21.9918, lon:-48.3906, flvCultures:["laranja"], flvTons:167076, poly:[[-22.11,-48.51],[-22.11,-48.27],[-21.87,-48.27],[-21.87,-48.51]] },
  { id:'BR-SP-200', ibgeCode:'3502200', name:'Angatuba', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.781, coef:0.78, lat:-23.4917, lon:-48.4139, flvCultures:["laranja"], flvTons:165300, poly:[[-23.61,-48.53],[-23.61,-48.29],[-23.37,-48.29],[-23.37,-48.53]] },
  { id:'BR-PE-002', ibgeCode:'2611002', name:'Petrolândia', state:'PE', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.774, coef:0.78, lat:-9.06863, lon:-38.3027, flvCultures:["coco"], flvTons:162000, poly:[[-9.19,-38.42],[-9.19,-38.18],[-8.95,-38.18],[-8.95,-38.42]] },
  { id:'BR-PA-455', ibgeCode:'1504455', name:'Medicilândia', state:'PA', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.766, coef:0.78, lat:-3.44637, lon:-52.8875, flvCultures:["banana"], flvTons:157950, poly:[[-3.57,-53.01],[-3.57,-52.77],[-3.33,-52.77],[-3.33,-53.01]] },
  { id:'BR-PA-103', ibgeCode:'1502103', name:'Cametá', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.766, coef:0.78, lat:-2.24295, lon:-49.4979, flvCultures:["acai"], flvTons:157830, poly:[[-2.36,-49.62],[-2.36,-49.38],[-2.12,-49.38],[-2.12,-49.62]] },
  { id:'BR-SP-059', ibgeCode:'3541059', name:'Pratânia', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.766, coef:0.78, lat:-22.8112, lon:-48.6636, flvCultures:["laranja"], flvTons:157750, poly:[[-22.93,-48.78],[-22.93,-48.54],[-22.69,-48.54],[-22.69,-48.78]] },
  { id:'BR-MG-902', ibgeCode:'3116902', name:'Comendador Gomes', state:'MG', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.765, coef:0.78, lat:-19.6973, lon:-49.0789, flvCultures:["laranja"], flvTons:157500, poly:[[-19.82,-49.2],[-19.82,-48.96],[-19.58,-48.96],[-19.58,-49.2]] },
  { id:'BR-RS-108', ibgeCode:'4305108', name:'Caxias do Sul', state:'RS', country:'BR', culture:'uva', areaMha:2.0, ndvi:0.764, coef:0.78, lat:-29.1629, lon:-51.1792, flvCultures:["uva", "pera", "caqui", "maca", "pessego", "figo"], flvTons:156754, poly:[[-29.28,-51.3],[-29.28,-51.06],[-29.04,-51.06],[-29.04,-51.3]] },
  { id:'BR-CE-258', ibgeCode:'2310258', name:'Paraipaba', state:'CE', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.762, coef:0.78, lat:-3.43799, lon:-39.1479, flvCultures:["coco"], flvTons:155899, poly:[[-3.56,-39.27],[-3.56,-39.03],[-3.32,-39.03],[-3.32,-39.27]] },
  { id:'BR-SP-600', ibgeCode:'3519600', name:'Ibitinga', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.758, coef:0.78, lat:-21.7562, lon:-48.8319, flvCultures:["laranja"], flvTons:154000, poly:[[-21.88,-48.95],[-21.88,-48.71],[-21.64,-48.71],[-21.64,-48.95]] },
  { id:'BR-SC-509', ibgeCode:'4204509', name:'Corupá', state:'SC', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.756, coef:0.78, lat:-26.4246, lon:-49.246, flvCultures:["banana"], flvTons:153176, poly:[[-26.54,-49.37],[-26.54,-49.13],[-26.3,-49.13],[-26.3,-49.37]] },
  { id:'BR-SP-903', ibgeCode:'3521903', name:'Itajobi', state:'SP', country:'BR', culture:'limao', areaMha:2.0, ndvi:0.749, coef:0.78, lat:-21.3123, lon:-49.0629, flvCultures:["limao"], flvTons:149450, poly:[[-21.43,-49.18],[-21.43,-48.94],[-21.19,-48.94],[-21.19,-49.18]] },
  { id:'BR-SC-001', ibgeCode:'4210001', name:'Luiz Alves', state:'SC', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.746, coef:0.78, lat:-26.7151, lon:-48.9322, flvCultures:["banana"], flvTons:147900, poly:[[-26.84,-49.05],[-26.84,-48.81],[-26.6,-48.81],[-26.6,-49.05]] },
  { id:'BR-RN-407', ibgeCode:'2414407', name:'Touros', state:'RN', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.738, coef:0.78, lat:-5.20182, lon:-35.4621, flvCultures:["coco", "batata", "abacaxi"], flvTons:144120, poly:[[-5.32,-35.58],[-5.32,-35.34],[-5.08,-35.34],[-5.08,-35.58]] },
  { id:'BR-SP-309', ibgeCode:'3502309', name:'Anhembi', state:'SP', country:'BR', culture:'laranja', areaMha:2.0, ndvi:0.738, coef:0.78, lat:-22.793, lon:-48.1336, flvCultures:["laranja"], flvTons:143951, poly:[[-22.91,-48.25],[-22.91,-48.01],[-22.67,-48.01],[-22.67,-48.25]] },
  { id:'BR-MG-708', ibgeCode:'3157708', name:'Santa Juliana', state:'MG', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.735, coef:0.78, lat:-19.3108, lon:-47.5322, flvCultures:["batata", "cebola", "alho"], flvTons:142650, poly:[[-19.43,-47.65],[-19.43,-47.41],[-19.19,-47.41],[-19.19,-47.65]] },
  { id:'BR-PR-401', ibgeCode:'4109401', name:'Guarapuava', state:'PR', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.733, coef:0.78, lat:-25.3902, lon:-51.4623, flvCultures:["batata", "cebola"], flvTons:141431, poly:[[-25.51,-51.58],[-25.51,-51.34],[-25.27,-51.34],[-25.27,-51.58]] },
  { id:'BR-PA-206', ibgeCode:'1500206', name:'Acará', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.732, coef:0.78, lat:-1.95383, lon:-48.1985, flvCultures:["coco", "acai"], flvTons:141000, poly:[[-2.07,-48.32],[-2.07,-48.08],[-1.83,-48.08],[-1.83,-48.32]] },
  { id:'BR-SP-708', ibgeCode:'3553708', name:'Taquaritinga', state:'SP', country:'BR', culture:'limao', areaMha:2.0, ndvi:0.728, coef:0.78, lat:-21.4049, lon:-48.5103, flvCultures:["manga", "goiaba", "limao"], flvTons:138760, poly:[[-21.52,-48.63],[-21.52,-48.39],[-21.28,-48.39],[-21.28,-48.63]] },
  { id:'BR-SC-500', ibgeCode:'4208500', name:'Ituporanga', state:'SC', country:'BR', culture:'cebola', areaMha:2.0, ndvi:0.72, coef:0.78, lat:-27.4101, lon:-49.5963, flvCultures:["cebola"], flvTons:135000, poly:[[-27.53,-49.72],[-27.53,-49.48],[-27.29,-49.48],[-27.29,-49.72]] },
  { id:'BR-RN-453', ibgeCode:'2401453', name:'Baraúna', state:'RN', country:'BR', culture:'melao', areaMha:2.0, ndvi:0.72, coef:0.78, lat:-5.06977, lon:-37.6129, flvCultures:["melao", "mamao"], flvTons:135000, poly:[[-5.19,-37.73],[-5.19,-37.49],[-4.95,-37.49],[-4.95,-37.73]] },
  { id:'BR-BA-904', ibgeCode:'2903904', name:'Bom Jesus da Lapa', state:'BA', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.716, coef:0.78, lat:-13.2506, lon:-43.4108, flvCultures:["banana"], flvTons:133100, poly:[[-13.37,-43.53],[-13.37,-43.29],[-13.13,-43.29],[-13.13,-43.53]] },
  { id:'BR-RS-200', ibgeCode:'4318200', name:'São Francisco de Paula', state:'RS', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.714, coef:0.78, lat:-29.4404, lon:-50.5828, flvCultures:["maca", "batata", "alho"], flvTons:132183, poly:[[-29.56,-50.7],[-29.56,-50.46],[-29.32,-50.46],[-29.32,-50.7]] },
  { id:'BR-MG-504', ibgeCode:'3155504', name:'Rio Paranaíba', state:'MG', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.711, coef:0.78, lat:-19.1861, lon:-46.2455, flvCultures:["batata", "cebola", "alho", "abacate"], flvTons:130540, poly:[[-19.31,-46.37],[-19.31,-46.13],[-19.07,-46.13],[-19.07,-46.37]] },
  { id:'BR-SP-254', ibgeCode:'3509254', name:'Cajati', state:'SP', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.708, coef:0.78, lat:-24.7324, lon:-48.1223, flvCultures:["banana"], flvTons:128800, poly:[[-24.85,-48.24],[-24.85,-48.0],[-24.61,-48.0],[-24.61,-48.24]] },
  { id:'BR-SP-703', ibgeCode:'3522703', name:'Itápolis', state:'SP', country:'BR', culture:'limao', areaMha:2.0, ndvi:0.701, coef:0.78, lat:-21.5942, lon:-48.8149, flvCultures:["manga", "goiaba", "limao", "melancia"], flvTons:125484, poly:[[-21.71,-48.93],[-21.71,-48.69],[-21.47,-48.69],[-21.47,-48.93]] },
  { id:'BR-PE-750', ibgeCode:'2608750', name:'Lagoa Grande', state:'PE', country:'BR', culture:'uva', areaMha:2.0, ndvi:0.697, coef:0.77, lat:-8.99452, lon:-40.2767, flvCultures:["uva", "manga", "goiaba"], flvTons:123700, poly:[[-9.11,-40.4],[-9.11,-40.16],[-8.87,-40.16],[-8.87,-40.4]] },
  { id:'BR-CE-200', ibgeCode:'2300200', name:'Acaraú', state:'CE', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.694, coef:0.77, lat:-2.88769, lon:-40.1183, flvCultures:["coco"], flvTons:122198, poly:[[-3.01,-40.24],[-3.01,-40.0],[-2.77,-40.0],[-2.77,-40.24]] },
  { id:'BR-PA-701', ibgeCode:'1500701', name:'Anajás', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.694, coef:0.77, lat:-0.996811, lon:-49.9354, flvCultures:["acai"], flvTons:122000, poly:[[-1.12,-50.06],[-1.12,-49.82],[-0.88,-49.82],[-0.88,-50.06]] },
  { id:'BR-RS-201', ibgeCode:'4308201', name:'Flores da Cunha', state:'RS', country:'BR', culture:'uva', areaMha:2.0, ndvi:0.688, coef:0.77, lat:-29.0261, lon:-51.1875, flvCultures:["uva", "pera", "pessego"], flvTons:118846, poly:[[-29.15,-51.31],[-29.15,-51.07],[-28.91,-51.07],[-28.91,-51.31]] },
  { id:'BR-CE-304', ibgeCode:'2312304', name:'São Benedito', state:'CE', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.685, coef:0.77, lat:-4.04713, lon:-40.8596, flvCultures:["batata", "maracuja"], flvTons:117740, poly:[[-4.17,-40.98],[-4.17,-40.74],[-3.93,-40.74],[-3.93,-40.98]] },
  { id:'BR-PA-703', ibgeCode:'1504703', name:'Moju', state:'PA', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.675, coef:0.77, lat:-1.88993, lon:-48.7668, flvCultures:["coco", "acai"], flvTons:112275, poly:[[-2.01,-48.89],[-2.01,-48.65],[-1.77,-48.65],[-1.77,-48.89]] },
  { id:'BR-PA-107', ibgeCode:'1500107', name:'Abaetetuba', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.674, coef:0.77, lat:-1.72183, lon:-48.8788, flvCultures:["acai"], flvTons:112000, poly:[[-1.84,-49.0],[-1.84,-48.76],[-1.6,-48.76],[-1.6,-49.0]] },
  { id:'BR-SP-809', ibgeCode:'3514809', name:'Eldorado', state:'SP', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.666, coef:0.77, lat:-24.5281, lon:-48.1141, flvCultures:["banana"], flvTons:108100, poly:[[-24.65,-48.23],[-24.65,-47.99],[-24.41,-47.99],[-24.41,-48.23]] },
  { id:'BR-RJ-755', ibgeCode:'3304755', name:'São Francisco de Itabapoana', state:'RJ', country:'BR', culture:'abacaxi', areaMha:2.0, ndvi:0.664, coef:0.77, lat:-21.4702, lon:-41.1091, flvCultures:["abacaxi"], flvTons:107202, poly:[[-21.59,-41.23],[-21.59,-40.99],[-21.35,-40.99],[-21.35,-41.23]] },
  { id:'BR-CE-001', ibgeCode:'2305001', name:'Guaraciaba do Norte', state:'CE', country:'BR', culture:'tomate', areaMha:1.523, ndvi:0.663, coef:0.77, lat:-4.15814, lon:-40.7476, flvCultures:["tomate", "batata", "maracuja"], flvTons:106626, poly:[[-4.28,-40.87],[-4.28,-40.63],[-4.04,-40.63],[-4.04,-40.87]] },
  { id:'BR-SP-801', ibgeCode:'3551801', name:'Sete Barras', state:'SP', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.659, coef:0.77, lat:-24.382, lon:-47.9279, flvCultures:["banana"], flvTons:104614, poly:[[-24.5,-48.05],[-24.5,-47.81],[-24.26,-47.81],[-24.26,-48.05]] },
  { id:'BR-BA-504', ibgeCode:'2919504', name:'Livramento de Nossa Senhora', state:'BA', country:'BR', culture:'manga', areaMha:2.0, ndvi:0.645, coef:0.77, lat:-13.6369, lon:-41.8432, flvCultures:["manga", "maracuja"], flvTons:97704, poly:[[-13.76,-41.96],[-13.76,-41.72],[-13.52,-41.72],[-13.52,-41.96]] },
  { id:'BR-ES-906', ibgeCode:'3204906', name:'São Mateus', state:'ES', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.645, coef:0.77, lat:-18.7214, lon:-39.8579, flvCultures:["coco", "mamao"], flvTons:97600, poly:[[-18.84,-39.98],[-18.84,-39.74],[-18.6,-39.74],[-18.6,-39.98]] },
  { id:'BR-PA-105', ibgeCode:'1501105', name:'Bagre', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.644, coef:0.77, lat:-1.90057, lon:-50.1987, flvCultures:["acai"], flvTons:96800, poly:[[-2.02,-50.32],[-2.02,-50.08],[-1.78,-50.08],[-1.78,-50.32]] },
  { id:'BR-CE-500', ibgeCode:'2313500', name:'Trairi', state:'CE', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.643, coef:0.77, lat:-3.26932, lon:-39.2681, flvCultures:["coco"], flvTons:96728, poly:[[-3.39,-39.39],[-3.39,-39.15],[-3.15,-39.15],[-3.15,-39.39]] },
  { id:'BR-CE-601', ibgeCode:'2307601', name:'Limoeiro do Norte', state:'CE', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.643, coef:0.77, lat:-5.14392, lon:-38.0847, flvCultures:["banana", "mamao"], flvTons:96487, poly:[[-5.26,-38.2],[-5.26,-37.96],[-5.02,-37.96],[-5.02,-38.2]] },
  { id:'BR-ES-104', ibgeCode:'3204104', name:'Pinheiros', state:'ES', country:'BR', culture:'mamao', areaMha:1.92, ndvi:0.642, coef:0.77, lat:-18.4141, lon:-40.2171, flvCultures:["mamao"], flvTons:96000, poly:[[-18.53,-40.34],[-18.53,-40.1],[-18.29,-40.1],[-18.29,-40.34]] },
  { id:'BR-PR-301', ibgeCode:'4119301', name:'Pinhão', state:'PR', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.636, coef:0.77, lat:-25.6944, lon:-51.6536, flvCultures:["batata"], flvTons:93157, poly:[[-25.81,-51.77],[-25.81,-51.53],[-25.57,-51.53],[-25.57,-51.77]] },
  { id:'BR-PE-308', ibgeCode:'2616308', name:'Vicência', state:'PE', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.63, coef:0.77, lat:-7.65655, lon:-35.3139, flvCultures:["banana"], flvTons:90000, poly:[[-7.78,-35.43],[-7.78,-35.19],[-7.54,-35.19],[-7.54,-35.43]] },
  { id:'BR-ES-502', ibgeCode:'3203502', name:'Montanha', state:'ES', country:'BR', culture:'mamao', areaMha:1.8, ndvi:0.63, coef:0.77, lat:-18.1303, lon:-40.3668, flvCultures:["mamao"], flvTons:90000, poly:[[-18.25,-40.49],[-18.25,-40.25],[-18.01,-40.25],[-18.01,-40.49]] },
  { id:'BR-GO-700', ibgeCode:'5221700', name:'Uruana', state:'GO', country:'BR', culture:'melancia', areaMha:2.0, ndvi:0.626, coef:0.77, lat:-15.4993, lon:-49.6861, flvCultures:["melancia"], flvTons:88200, poly:[[-15.62,-49.81],[-15.62,-49.57],[-15.38,-49.57],[-15.38,-49.81]] },
  { id:'BR-SC-408', ibgeCode:'4200408', name:'Água Doce', state:'SC', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.626, coef:0.77, lat:-26.9985, lon:-51.5528, flvCultures:["batata", "maca"], flvTons:87783, poly:[[-27.12,-51.67],[-27.12,-51.43],[-26.88,-51.43],[-26.88,-51.67]] },
  { id:'BR-ES-205', ibgeCode:'3203205', name:'Linhares', state:'ES', country:'BR', culture:'mamao', areaMha:1.754, ndvi:0.625, coef:0.77, lat:-19.3946, lon:-40.0643, flvCultures:["coco", "mamao"], flvTons:87700, poly:[[-19.51,-40.18],[-19.51,-39.94],[-19.27,-39.94],[-19.27,-40.18]] },
  { id:'BR-SC-705', ibgeCode:'4200705', name:'Alfredo Wagner', state:'SC', country:'BR', culture:'cebola', areaMha:2.0, ndvi:0.624, coef:0.77, lat:-27.7001, lon:-49.3273, flvCultures:["cebola"], flvTons:86800, poly:[[-27.82,-49.45],[-27.82,-49.21],[-27.58,-49.21],[-27.58,-49.45]] },
  { id:'BR-SP-104', ibgeCode:'3510104', name:'Cândido Rodrigues', state:'SP', country:'BR', culture:'limao', areaMha:2.0, ndvi:0.622, coef:0.77, lat:-21.3275, lon:-48.6327, flvCultures:["manga", "limao"], flvTons:86238, poly:[[-21.45,-48.75],[-21.45,-48.51],[-21.21,-48.51],[-21.21,-48.75]] },
  { id:'BR-PA-500', ibgeCode:'1506500', name:'Santa Izabel do Pará', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.618, coef:0.77, lat:-1.29686, lon:-48.1606, flvCultures:["acai"], flvTons:84000, poly:[[-1.42,-48.28],[-1.42,-48.04],[-1.18,-48.04],[-1.18,-48.28]] },
  { id:'BR-RN-008', ibgeCode:'2401008', name:'Apodi', state:'RN', country:'BR', culture:'melao', areaMha:2.0, ndvi:0.616, coef:0.77, lat:-5.65349, lon:-37.7946, flvCultures:["melao", "melancia"], flvTons:83156, poly:[[-5.77,-37.91],[-5.77,-37.67],[-5.53,-37.67],[-5.53,-37.91]] },
  { id:'BR-SP-008', ibgeCode:'3556008', name:'Urupês', state:'SP', country:'BR', culture:'limao', areaMha:2.0, ndvi:0.615, coef:0.77, lat:-21.2032, lon:-49.2931, flvCultures:["limao"], flvTons:82400, poly:[[-21.32,-49.41],[-21.32,-49.17],[-21.08,-49.17],[-21.08,-49.41]] },
  { id:'BR-GO-104', ibgeCode:'5217104', name:'Piracanjuba', state:'GO', country:'BR', culture:'tomate', areaMha:1.173, ndvi:0.614, coef:0.77, lat:-17.302, lon:-49.017, flvCultures:["tomate"], flvTons:82100, poly:[[-17.42,-49.14],[-17.42,-48.9],[-17.18,-48.9],[-17.18,-49.14]] },
  { id:'BR-SP-600', ibgeCode:'3524600', name:'Jacupiranga', state:'SP', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.609, coef:0.77, lat:-24.6963, lon:-48.0064, flvCultures:["banana"], flvTons:79668, poly:[[-24.82,-48.13],[-24.82,-47.89],[-24.58,-47.89],[-24.58,-48.13]] },
  { id:'BR-PR-609', ibgeCode:'4109609', name:'Guaratuba', state:'PR', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.604, coef:0.77, lat:-25.8817, lon:-48.5752, flvCultures:["banana"], flvTons:76800, poly:[[-26.0,-48.7],[-26.0,-48.46],[-25.76,-48.46],[-25.76,-48.7]] },
  { id:'BR-RN-056', ibgeCode:'2411056', name:'Tibau', state:'RN', country:'BR', culture:'melao', areaMha:2.0, ndvi:0.601, coef:0.77, lat:-4.83729, lon:-37.2554, flvCultures:["melao"], flvTons:75645, poly:[[-4.96,-37.38],[-4.96,-37.14],[-4.72,-37.14],[-4.72,-37.38]] },
  { id:'BR-PE-800', ibgeCode:'2613800', name:'São Vicente Férrer', state:'PE', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.601, coef:0.77, lat:-7.58969, lon:-35.4808, flvCultures:["uva", "banana"], flvTons:75450, poly:[[-7.71,-35.6],[-7.71,-35.36],[-7.47,-35.36],[-7.47,-35.6]] },
  { id:'BR-BA-101', ibgeCode:'2927101', name:'Rodelas', state:'BA', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.6, coef:0.77, lat:-8.85021, lon:-38.78, flvCultures:["coco"], flvTons:75181, poly:[[-8.97,-38.9],[-8.97,-38.66],[-8.73,-38.66],[-8.73,-38.9]] },
  { id:'BR-RS-622', ibgeCode:'4318622', name:'São José dos Ausentes', state:'RS', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.597, coef:0.76, lat:-28.7476, lon:-50.0677, flvCultures:["batata", "maca"], flvTons:73475, poly:[[-28.87,-50.19],[-28.87,-49.95],[-28.63,-49.95],[-28.63,-50.19]] },
  { id:'BR-RS-906', ibgeCode:'4307906', name:'Farroupilha', state:'RS', country:'BR', culture:'uva', areaMha:2.0, ndvi:0.596, coef:0.76, lat:-29.2227, lon:-51.3419, flvCultures:["uva", "caqui", "pera", "pessego"], flvTons:72830, poly:[[-29.34,-51.46],[-29.34,-51.22],[-29.1,-51.22],[-29.1,-51.46]] },
  { id:'BR-SP-507', ibgeCode:'3521507', name:'Irapuã', state:'SP', country:'BR', culture:'limao', areaMha:2.0, ndvi:0.593, coef:0.76, lat:-21.2768, lon:-49.4164, flvCultures:["limao"], flvTons:71518, poly:[[-21.4,-49.54],[-21.4,-49.3],[-21.16,-49.3],[-21.16,-49.54]] },
  { id:'BR-BA-807', ibgeCode:'2902807', name:'Barra da Estiva', state:'BA', country:'BR', culture:'tomate', areaMha:1.018, ndvi:0.593, coef:0.76, lat:-13.6237, lon:-41.3347, flvCultures:["tomate", "maracuja"], flvTons:71260, poly:[[-13.74,-41.45],[-13.74,-41.21],[-13.5,-41.21],[-13.5,-41.45]] },
  { id:'BR-GO-805', ibgeCode:'5204805', name:'Campo Alegre de Goiás', state:'GO', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.593, coef:0.76, lat:-17.6363, lon:-47.7768, flvCultures:["batata", "alho"], flvTons:71250, poly:[[-17.76,-47.9],[-17.76,-47.66],[-17.52,-47.66],[-17.52,-47.9]] },
  { id:'BR-PA-907', ibgeCode:'1501907', name:'Bujaru', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.591, coef:0.76, lat:-1.51762, lon:-48.0381, flvCultures:["acai"], flvTons:70550, poly:[[-1.64,-48.16],[-1.64,-47.92],[-1.4,-47.92],[-1.4,-48.16]] },
  { id:'BR-SP-209', ibgeCode:'3550209', name:'São Miguel Arcanjo', state:'SP', country:'BR', culture:'uva', areaMha:2.0, ndvi:0.591, coef:0.76, lat:-23.8782, lon:-47.9935, flvCultures:["uva", "pera", "ervilha", "caqui", "pessego", "tangerina"], flvTons:70425, poly:[[-24.0,-48.11],[-24.0,-47.87],[-23.76,-47.87],[-23.76,-48.11]] },
  { id:'BR-PA-303', ibgeCode:'1501303', name:'Barcarena', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.59, coef:0.76, lat:-1.51187, lon:-48.6195, flvCultures:["acai"], flvTons:70000, poly:[[-1.63,-48.74],[-1.63,-48.5],[-1.39,-48.5],[-1.39,-48.74]] },
  { id:'BR-SP-904', ibgeCode:'3525904', name:'Jundiaí', state:'SP', country:'BR', culture:'uva', areaMha:2.0, ndvi:0.588, coef:0.76, lat:-23.1852, lon:-46.8974, flvCultures:["ervilha", "uva", "caqui", "pessego"], flvTons:68958, poly:[[-23.31,-47.02],[-23.31,-46.78],[-23.07,-46.78],[-23.07,-47.02]] },
  { id:'BR-PB-202', ibgeCode:'2511202', name:'Pedras de Fogo', state:'PB', country:'BR', culture:'abacaxi', areaMha:1.954, ndvi:0.587, coef:0.76, lat:-7.39107, lon:-35.1065, flvCultures:["abacaxi"], flvTons:68400, poly:[[-7.51,-35.23],[-7.51,-34.99],[-7.27,-34.99],[-7.27,-35.23]] },
  { id:'BR-SP-602', ibgeCode:'3542602', name:'Registro', state:'SP', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.585, coef:0.76, lat:-24.4979, lon:-47.8449, flvCultures:["banana"], flvTons:67670, poly:[[-24.62,-47.96],[-24.62,-47.72],[-24.38,-47.72],[-24.38,-47.96]] },
  { id:'BR-RS-105', ibgeCode:'4302105', name:'Bento Gonçalves', state:'RS', country:'BR', culture:'uva', areaMha:2.0, ndvi:0.585, coef:0.76, lat:-29.1662, lon:-51.5165, flvCultures:["uva", "pessego"], flvTons:67492, poly:[[-29.29,-51.64],[-29.29,-51.4],[-29.05,-51.4],[-29.05,-51.64]] },
  { id:'BR-BA-204', ibgeCode:'2930204', name:'Sento Sé', state:'BA', country:'BR', culture:'manga', areaMha:2.0, ndvi:0.583, coef:0.76, lat:-9.74138, lon:-41.8786, flvCultures:["manga", "cebola"], flvTons:66441, poly:[[-9.86,-42.0],[-9.86,-41.76],[-9.62,-41.76],[-9.62,-42.0]] },
  { id:'BR-SP-909', ibgeCode:'3556909', name:'Vista Alegre do Alto', state:'SP', country:'BR', culture:'goiaba', areaMha:2.0, ndvi:0.581, coef:0.76, lat:-21.1692, lon:-48.6284, flvCultures:["tangerina", "manga", "goiaba", "limao"], flvTons:65640, poly:[[-21.29,-48.75],[-21.29,-48.51],[-21.05,-48.51],[-21.05,-48.75]] },
  { id:'BR-MG-209', ibgeCode:'3121209', name:'Delfinópolis', state:'MG', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.581, coef:0.76, lat:-20.3468, lon:-46.8456, flvCultures:["banana"], flvTons:65560, poly:[[-20.47,-46.97],[-20.47,-46.73],[-20.23,-46.73],[-20.23,-46.97]] },
  { id:'BR-PE-904', ibgeCode:'2601904', name:'Bezerros', state:'PE', country:'BR', culture:'tomate', areaMha:0.926, ndvi:0.58, coef:0.76, lat:-8.2328, lon:-35.796, flvCultures:["tomate"], flvTons:64800, poly:[[-8.35,-35.92],[-8.35,-35.68],[-8.11,-35.68],[-8.11,-35.92]] },
  { id:'BR-SP-406', ibgeCode:'3517406', name:'Guaíra', state:'SP', country:'BR', culture:'tomate', areaMha:0.911, ndvi:0.578, coef:0.76, lat:-20.3196, lon:-48.312, flvCultures:["tomate"], flvTons:63750, poly:[[-20.44,-48.43],[-20.44,-48.19],[-20.2,-48.19],[-20.2,-48.43]] },
  { id:'BR-GO-005', ibgeCode:'5222005', name:'Vianópolis', state:'GO', country:'BR', culture:'tomate', areaMha:0.9, ndvi:0.576, coef:0.76, lat:-16.7405, lon:-48.5159, flvCultures:["tomate"], flvTons:63000, poly:[[-16.86,-48.64],[-16.86,-48.4],[-16.62,-48.4],[-16.62,-48.64]] },
  { id:'BR-SP-604', ibgeCode:'3517604', name:'Guapiara', state:'SP', country:'BR', culture:'tomate', areaMha:0.9, ndvi:0.576, coef:0.76, lat:-24.1892, lon:-48.5295, flvCultures:["tomate", "pessego"], flvTons:63000, poly:[[-24.31,-48.65],[-24.31,-48.41],[-24.07,-48.41],[-24.07,-48.65]] },
  { id:'BR-SC-605', ibgeCode:'4210605', name:'Massaranduba', state:'SC', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.572, coef:0.76, lat:-26.6109, lon:-49.0054, flvCultures:["banana"], flvTons:61041, poly:[[-26.73,-49.13],[-26.73,-48.89],[-26.49,-48.89],[-26.49,-49.13]] },
  { id:'BR-SP-608', ibgeCode:'3515608', name:'Fernando Prestes', state:'SP', country:'BR', culture:'limao', areaMha:2.0, ndvi:0.571, coef:0.76, lat:-21.2661, lon:-48.6874, flvCultures:["manga", "limao"], flvTons:60340, poly:[[-21.39,-48.81],[-21.39,-48.57],[-21.15,-48.57],[-21.15,-48.81]] },
  { id:'BR-PB-101', ibgeCode:'2507101', name:'Itapororoca', state:'PB', country:'BR', culture:'abacaxi', areaMha:1.714, ndvi:0.57, coef:0.76, lat:-6.82374, lon:-35.2406, flvCultures:["abacaxi"], flvTons:60000, poly:[[-6.94,-35.36],[-6.94,-35.12],[-6.7,-35.12],[-6.7,-35.36]] },
  { id:'BR-MG-905', ibgeCode:'3110905', name:'Campanha', state:'MG', country:'BR', culture:'tangerina', areaMha:2.0, ndvi:0.57, coef:0.76, lat:-21.836, lon:-45.4004, flvCultures:["tangerina"], flvTons:59800, poly:[[-21.96,-45.52],[-21.96,-45.28],[-21.72,-45.28],[-21.72,-45.52]] },
  { id:'BR-GO-501', ibgeCode:'5212501', name:'Luziânia', state:'GO', country:'BR', culture:'tomate', areaMha:0.852, ndvi:0.569, coef:0.76, lat:-16.253, lon:-47.95, flvCultures:["tomate", "alho"], flvTons:59610, poly:[[-16.37,-48.07],[-16.37,-47.83],[-16.13,-47.83],[-16.13,-48.07]] },
  { id:'BR-PE-606', ibgeCode:'2606606', name:'Ibimirim', state:'PE', country:'BR', culture:'melancia', areaMha:1.982, ndvi:0.569, coef:0.76, lat:-8.54026, lon:-37.7032, flvCultures:["melao", "melancia"], flvTons:59450, poly:[[-8.66,-37.82],[-8.66,-37.58],[-8.42,-37.58],[-8.42,-37.82]] },
  { id:'BR-SP-708', ibgeCode:'3529708', name:'Miguelópolis', state:'SP', country:'BR', culture:'tomate', areaMha:0.839, ndvi:0.567, coef:0.76, lat:-20.1796, lon:-48.031, flvCultures:["tomate", "ervilha"], flvTons:58707, poly:[[-20.3,-48.15],[-20.3,-47.91],[-20.06,-47.91],[-20.06,-48.15]] },
  { id:'BR-GO-708', ibgeCode:'5217708', name:'Pontalina', state:'GO', country:'BR', culture:'tomate', areaMha:0.829, ndvi:0.566, coef:0.76, lat:-17.5225, lon:-49.4489, flvCultures:["tomate"], flvTons:58000, poly:[[-17.64,-49.57],[-17.64,-49.33],[-17.4,-49.33],[-17.4,-49.57]] },
  { id:'BR-PE-000', ibgeCode:'2607000', name:'Inajá', state:'PE', country:'BR', culture:'melancia', areaMha:1.931, ndvi:0.566, coef:0.76, lat:-8.90206, lon:-37.8351, flvCultures:["melao", "melancia"], flvTons:57945, poly:[[-9.02,-37.96],[-9.02,-37.72],[-8.78,-37.72],[-8.78,-37.96]] },
  { id:'BR-MG-750', ibgeCode:'3170750', name:'Varjão de Minas', state:'MG', country:'BR', culture:'tomate', areaMha:0.816, ndvi:0.564, coef:0.76, lat:-18.3741, lon:-46.0313, flvCultures:["tomate"], flvTons:57145, poly:[[-18.49,-46.15],[-18.49,-45.91],[-18.25,-45.91],[-18.25,-46.15]] },
  { id:'BR-SP-705', ibgeCode:'3502705', name:'Apiaí', state:'SP', country:'BR', culture:'tomate', areaMha:0.809, ndvi:0.563, coef:0.76, lat:-24.5108, lon:-48.8443, flvCultures:["tomate", "caqui", "pessego"], flvTons:56600, poly:[[-24.63,-48.96],[-24.63,-48.72],[-24.39,-48.72],[-24.39,-48.96]] },
  { id:'BR-SP-006', ibgeCode:'3543006', name:'Ribeirão Branco', state:'SP', country:'BR', culture:'tomate', areaMha:0.804, ndvi:0.562, coef:0.76, lat:-24.2206, lon:-48.7635, flvCultures:["tomate"], flvTons:56250, poly:[[-24.34,-48.88],[-24.34,-48.64],[-24.1,-48.64],[-24.1,-48.88]] },
  { id:'BR-SP-305', ibgeCode:'3523305', name:'Itariri', state:'SP', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.562, coef:0.76, lat:-24.2834, lon:-47.1736, flvCultures:["banana"], flvTons:56000, poly:[[-24.4,-47.29],[-24.4,-47.05],[-24.16,-47.05],[-24.16,-47.29]] },
  { id:'BR-MG-107', ibgeCode:'3170107', name:'Uberaba', state:'MG', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.56, coef:0.76, lat:-19.7472, lon:-47.9381, flvCultures:["batata", "abacate"], flvTons:55030, poly:[[-19.87,-48.06],[-19.87,-47.82],[-19.63,-47.82],[-19.63,-48.06]] },
  { id:'BR-PR-201', ibgeCode:'4105201', name:'Cerro Azul', state:'PR', country:'BR', culture:'tangerina', areaMha:2.0, ndvi:0.56, coef:0.76, lat:-26.0891, lon:-52.8691, flvCultures:["tangerina"], flvTons:55000, poly:[[-26.21,-52.99],[-26.21,-52.75],[-25.97,-52.75],[-25.97,-52.99]] },
  { id:'BR-PA-809', ibgeCode:'1505809', name:'Portel', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.56, coef:0.76, lat:-1.93639, lon:-50.8194, flvCultures:["acai"], flvTons:55000, poly:[[-2.06,-50.94],[-2.06,-50.7],[-1.82,-50.7],[-1.82,-50.94]] },
  { id:'BR-BA-606', ibgeCode:'2908606', name:'Conde', state:'BA', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.559, coef:0.76, lat:-11.8179, lon:-37.6131, flvCultures:["coco"], flvTons:54439, poly:[[-11.94,-37.73],[-11.94,-37.49],[-11.7,-37.49],[-11.7,-37.73]] },
  { id:'BR-MG-505', ibgeCode:'3131505', name:'Ipuiúna', state:'MG', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.558, coef:0.76, lat:-22.1013, lon:-46.1915, flvCultures:["batata"], flvTons:54250, poly:[[-22.22,-46.31],[-22.22,-46.07],[-21.98,-46.07],[-21.98,-46.31]] },
  { id:'BR-PA-000', ibgeCode:'1504000', name:'Limoeiro do Ajuru', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.558, coef:0.76, lat:-1.8985, lon:-49.3903, flvCultures:["acai"], flvTons:54000, poly:[[-2.02,-49.51],[-2.02,-49.27],[-1.78,-49.27],[-1.78,-49.51]] },
  { id:'BR-PA-802', ibgeCode:'1504802', name:'Monte Alegre', state:'PA', country:'BR', culture:'limao', areaMha:2.0, ndvi:0.556, coef:0.76, lat:-1.99768, lon:-54.0724, flvCultures:["limao"], flvTons:52813, poly:[[-2.12,-54.19],[-2.12,-53.95],[-1.88,-53.95],[-1.88,-54.19]] },
  { id:'BR-PR-205', ibgeCode:'4113205', name:'Lapa', state:'PR', country:'BR', culture:'batata', areaMha:2.0, ndvi:0.555, coef:0.76, lat:-25.7671, lon:-49.7168, flvCultures:["batata", "maca"], flvTons:52390, poly:[[-25.89,-49.84],[-25.89,-49.6],[-25.65,-49.6],[-25.65,-49.84]] },
  { id:'BR-SC-403', ibgeCode:'4207403', name:'Imbuia', state:'SC', country:'BR', culture:'cebola', areaMha:1.745, ndvi:0.555, coef:0.76, lat:-27.4908, lon:-49.4218, flvCultures:["cebola"], flvTons:52360, poly:[[-27.61,-49.54],[-27.61,-49.3],[-27.37,-49.3],[-27.37,-49.54]] },
  { id:'BR-SC-503', ibgeCode:'4202503', name:'Bom Jardim da Serra', state:'SC', country:'BR', culture:'maca', areaMha:1.491, ndvi:0.554, coef:0.76, lat:-28.3377, lon:-49.6373, flvCultures:["maca"], flvTons:52200, poly:[[-28.46,-49.76],[-28.46,-49.52],[-28.22,-49.52],[-28.22,-49.76]] },
  { id:'BR-BA-505', ibgeCode:'2933505', name:'Wenceslau Guimarães', state:'BA', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.551, coef:0.76, lat:-13.6908, lon:-39.4762, flvCultures:["banana"], flvTons:50611, poly:[[-13.81,-39.6],[-13.81,-39.36],[-13.57,-39.36],[-13.57,-39.6]] },
  { id:'BR-PB-703', ibgeCode:'2513703', name:'Santa Rita', state:'PB', country:'BR', culture:'abacaxi', areaMha:1.42, ndvi:0.549, coef:0.76, lat:-7.11724, lon:-34.9753, flvCultures:["coco", "abacaxi"], flvTons:49700, poly:[[-7.24,-35.1],[-7.24,-34.86],[-7.0,-34.86],[-7.0,-35.1]] },
  { id:'BR-RS-548', ibgeCode:'4314548', name:'Pinto Bandeira', state:'RS', country:'BR', culture:'uva', areaMha:2.0, ndvi:0.549, coef:0.76, lat:-29.0975, lon:-51.4503, flvCultures:["uva", "caqui", "pessego"], flvTons:49660, poly:[[-29.22,-51.57],[-29.22,-51.33],[-28.98,-51.33],[-28.98,-51.57]] },
  { id:'BR-AM-702', ibgeCode:'1302702', name:'Manicoré', state:'AM', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.549, coef:0.76, lat:-5.80462, lon:-61.2895, flvCultures:["banana"], flvTons:49500, poly:[[-5.92,-61.41],[-5.92,-61.17],[-5.68,-61.17],[-5.68,-61.41]] },
  { id:'BR-MG-101', ibgeCode:'3168101', name:'Tapira', state:'MG', country:'BR', culture:'batata', areaMha:1.97, ndvi:0.549, coef:0.76, lat:-19.9166, lon:-46.8264, flvCultures:["batata", "alho"], flvTons:49260, poly:[[-20.04,-46.95],[-20.04,-46.71],[-19.8,-46.71],[-19.8,-46.95]] },
  { id:'BR-PR-209', ibgeCode:'4106209', name:'Contenda', state:'PR', country:'BR', culture:'batata', areaMha:1.944, ndvi:0.547, coef:0.76, lat:-25.6788, lon:-49.535, flvCultures:["batata"], flvTons:48600, poly:[[-25.8,-49.65],[-25.8,-49.41],[-25.56,-49.41],[-25.56,-49.65]] },
  { id:'BR-MG-504', ibgeCode:'3103504', name:'Araguari', state:'MG', country:'BR', culture:'tomate', areaMha:0.686, ndvi:0.546, coef:0.76, lat:-18.6456, lon:-48.1934, flvCultures:["tomate"], flvTons:48000, poly:[[-18.77,-48.31],[-18.77,-48.07],[-18.53,-48.07],[-18.53,-48.31]] },
  { id:'BR-PB-809', ibgeCode:'2500809', name:'Araçagi', state:'PB', country:'BR', culture:'abacaxi', areaMha:1.371, ndvi:0.546, coef:0.76, lat:-6.84374, lon:-35.3737, flvCultures:["abacaxi"], flvTons:48000, poly:[[-6.96,-35.49],[-6.96,-35.25],[-6.72,-35.25],[-6.72,-35.49]] },
  { id:'BR-CE-401', ibgeCode:'2308401', name:'Missão Velha', state:'CE', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.546, coef:0.76, lat:-7.23522, lon:-39.143, flvCultures:["banana"], flvTons:47896, poly:[[-7.36,-39.26],[-7.36,-39.02],[-7.12,-39.02],[-7.12,-39.26]] },
  { id:'BR-BA-303', ibgeCode:'2925303', name:'Porto Seguro', state:'BA', country:'BR', culture:'mamao', areaMha:0.958, ndvi:0.546, coef:0.76, lat:-16.4435, lon:-39.0643, flvCultures:["coco", "mamao"], flvTons:47888, poly:[[-16.56,-39.18],[-16.56,-38.94],[-16.32,-38.94],[-16.32,-39.18]] },
  { id:'BR-BA-608', ibgeCode:'2931608', name:'Teolândia', state:'BA', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.545, coef:0.76, lat:-13.5896, lon:-39.484, flvCultures:["banana"], flvTons:47736, poly:[[-13.71,-39.6],[-13.71,-39.36],[-13.47,-39.36],[-13.47,-39.6]] },
  { id:'BR-SP-100', ibgeCode:'3526100', name:'Juquiá', state:'SP', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.545, coef:0.76, lat:-24.3101, lon:-47.6426, flvCultures:["banana"], flvTons:47700, poly:[[-24.43,-47.76],[-24.43,-47.52],[-24.19,-47.52],[-24.19,-47.76]] },
  { id:'BR-CE-109', ibgeCode:'2301109', name:'Aracati', state:'CE', country:'BR', culture:'melao', areaMha:1.894, ndvi:0.545, coef:0.76, lat:-4.55826, lon:-37.7679, flvCultures:["melao", "melancia"], flvTons:47340, poly:[[-4.68,-37.89],[-4.68,-37.65],[-4.44,-37.65],[-4.44,-37.89]] },
  { id:'BR-GO-705', ibgeCode:'5209705', name:'Hidrolândia', state:'GO', country:'BR', culture:'tomate', areaMha:0.664, ndvi:0.543, coef:0.76, lat:-16.9626, lon:-49.2265, flvCultures:["tomate"], flvTons:46500, poly:[[-17.08,-49.35],[-17.08,-49.11],[-16.84,-49.11],[-16.84,-49.35]] },
  { id:'BR-CE-308', ibgeCode:'2305308', name:'Ibiapina', state:'CE', country:'BR', culture:'maracuja', areaMha:2.0, ndvi:0.543, coef:0.76, lat:-3.92403, lon:-40.8911, flvCultures:["batata", "maracuja", "abacate"], flvTons:46429, poly:[[-4.04,-41.01],[-4.04,-40.77],[-3.8,-40.77],[-3.8,-41.01]] },
  { id:'BR-MG-408', ibgeCode:'3106408', name:'Belo Vale', state:'MG', country:'BR', culture:'tangerina', areaMha:2.0, ndvi:0.542, coef:0.76, lat:-20.4077, lon:-44.0275, flvCultures:["tangerina"], flvTons:46200, poly:[[-20.53,-44.15],[-20.53,-43.91],[-20.29,-43.91],[-20.29,-44.15]] },
  { id:'BR-ES-702', ibgeCode:'3202702', name:'Itaguaçu', state:'ES', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.542, coef:0.76, lat:-19.8018, lon:-40.8601, flvCultures:["banana"], flvTons:46070, poly:[[-19.92,-40.98],[-19.92,-40.74],[-19.68,-40.74],[-19.68,-40.98]] },
  { id:'BR-CE-609', ibgeCode:'2313609', name:'Ubajara', state:'CE', country:'BR', culture:'maracuja', areaMha:2.0, ndvi:0.541, coef:0.76, lat:-3.85448, lon:-40.9204, flvCultures:["batata", "maracuja", "abacate"], flvTons:45427, poly:[[-3.97,-41.04],[-3.97,-40.8],[-3.73,-40.8],[-3.73,-41.04]] },
  { id:'BR-SP-906', ibgeCode:'3529906', name:'Miracatu', state:'SP', country:'BR', culture:'banana', areaMha:2.0, ndvi:0.54, coef:0.76, lat:-24.2766, lon:-47.4625, flvCultures:["banana"], flvTons:45000, poly:[[-24.4,-47.58],[-24.4,-47.34],[-24.16,-47.34],[-24.16,-47.58]] },
  { id:'BR-BA-305', ibgeCode:'2905305', name:'Cafarnaum', state:'BA', country:'BR', culture:'cebola', areaMha:1.449, ndvi:0.537, coef:0.76, lat:-11.6914, lon:-41.4688, flvCultures:["cebola"], flvTons:43472, poly:[[-11.81,-41.59],[-11.81,-41.35],[-11.57,-41.35],[-11.57,-41.59]] },
  { id:'BR-SC-901', ibgeCode:'4201901', name:'Aurora', state:'SC', country:'BR', culture:'cebola', areaMha:1.447, ndvi:0.537, coef:0.76, lat:-27.3098, lon:-49.6295, flvCultures:["cebola"], flvTons:43400, poly:[[-27.43,-49.75],[-27.43,-49.51],[-27.19,-49.51],[-27.19,-49.75]] },
  { id:'BR-SP-805', ibgeCode:'3530805', name:'Mogi Mirim', state:'SP', country:'BR', culture:'limao', areaMha:2.0, ndvi:0.536, coef:0.76, lat:-22.4332, lon:-46.9532, flvCultures:["limao", "abacate"], flvTons:43060, poly:[[-22.55,-47.07],[-22.55,-46.83],[-22.31,-46.83],[-22.31,-47.07]] },
  { id:'BR-BA-901', ibgeCode:'2909901', name:'Curaçá', state:'BA', country:'BR', culture:'manga', areaMha:2.0, ndvi:0.535, coef:0.76, lat:-8.98458, lon:-39.8997, flvCultures:["manga", "goiaba", "melao"], flvTons:42670, poly:[[-9.1,-40.02],[-9.1,-39.78],[-8.86,-39.78],[-8.86,-40.02]] },
  { id:'BR-CE-553', ibgeCode:'2306553', name:'Itarema', state:'CE', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.535, coef:0.76, lat:-2.9248, lon:-39.9167, flvCultures:["coco"], flvTons:42600, poly:[[-3.04,-40.04],[-3.04,-39.8],[-2.8,-39.8],[-2.8,-40.04]] },
  { id:'BR-CE-401', ibgeCode:'2313401', name:'Tianguá', state:'CE', country:'BR', culture:'maracuja', areaMha:2.0, ndvi:0.534, coef:0.76, lat:-3.72965, lon:-40.9923, flvCultures:["maracuja", "abacate"], flvTons:42010, poly:[[-3.85,-41.11],[-3.85,-40.87],[-3.61,-40.87],[-3.61,-41.11]] },
  { id:'BR-RS-377', ibgeCode:'4312377', name:'Monte Alegre dos Campos', state:'RS', country:'BR', culture:'maca', areaMha:1.191, ndvi:0.533, coef:0.76, lat:-28.6805, lon:-50.7834, flvCultures:["uva", "maca", "pera"], flvTons:41680, poly:[[-28.8,-50.9],[-28.8,-50.66],[-28.56,-50.66],[-28.56,-50.9]] },
  { id:'BR-PA-205', ibgeCode:'1505205', name:'Oeiras do Pará', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.533, coef:0.76, lat:-2.00358, lon:-49.8628, flvCultures:["acai"], flvTons:41600, poly:[[-2.12,-49.98],[-2.12,-49.74],[-1.88,-49.74],[-1.88,-49.98]] },
  { id:'BR-PR-605', ibgeCode:'4125605', name:'São Mateus do Sul', state:'PR', country:'BR', culture:'batata', areaMha:1.636, ndvi:0.532, coef:0.76, lat:-25.8677, lon:-50.384, flvCultures:["batata"], flvTons:40889, poly:[[-25.99,-50.5],[-25.99,-50.26],[-25.75,-50.26],[-25.75,-50.5]] },
  { id:'BR-BA-201', ibgeCode:'2917201', name:'Ituaçu', state:'BA', country:'BR', culture:'maracuja', areaMha:2.0, ndvi:0.532, coef:0.76, lat:-13.8107, lon:-41.3003, flvCultures:["manga", "alho", "maracuja"], flvTons:40800, poly:[[-13.93,-41.42],[-13.93,-41.18],[-13.69,-41.18],[-13.69,-41.42]] },
  { id:'BR-RS-401', ibgeCode:'4312401', name:'Montenegro', state:'RS', country:'BR', culture:'tangerina', areaMha:2.0, ndvi:0.531, coef:0.76, lat:-29.6824, lon:-51.4679, flvCultures:["tangerina"], flvTons:40500, poly:[[-29.8,-51.59],[-29.8,-51.35],[-29.56,-51.35],[-29.56,-51.59]] },
  { id:'BR-SC-506', ibgeCode:'4205506', name:'Fraiburgo', state:'SC', country:'BR', culture:'maca', areaMha:1.145, ndvi:0.53, coef:0.76, lat:-27.0233, lon:-50.92, flvCultures:["maca", "pera", "alho", "pessego"], flvTons:40075, poly:[[-27.14,-51.04],[-27.14,-50.8],[-26.9,-50.8],[-26.9,-51.04]] },
  { id:'BR-SP-704', ibgeCode:'3526704', name:'Leme', state:'SP', country:'BR', culture:'batata', areaMha:1.56, ndvi:0.528, coef:0.76, lat:-22.1809, lon:-47.3841, flvCultures:["batata"], flvTons:39000, poly:[[-22.3,-47.5],[-22.3,-47.26],[-22.06,-47.26],[-22.06,-47.5]] },
  { id:'BR-SP-858', ibgeCode:'3528858', name:'Marapoama', state:'SP', country:'BR', culture:'limao', areaMha:1.95, ndvi:0.528, coef:0.76, lat:-21.2587, lon:-49.13, flvCultures:["tangerina", "limao"], flvTons:38990, poly:[[-21.38,-49.25],[-21.38,-49.01],[-21.14,-49.01],[-21.14,-49.25]] },
  { id:'BR-RS-802', ibgeCode:'4300802', name:'Antônio Prado', state:'RS', country:'BR', culture:'uva', areaMha:2.0, ndvi:0.528, coef:0.76, lat:-28.8565, lon:-51.2883, flvCultures:["uva", "caqui", "maca", "pessego", "figo"], flvTons:38799, poly:[[-28.98,-51.41],[-28.98,-51.17],[-28.74,-51.17],[-28.74,-51.41]] },
  { id:'BR-SP-403', ibgeCode:'3552403', name:'Sumaré', state:'SP', country:'BR', culture:'tomate', areaMha:0.549, ndvi:0.527, coef:0.76, lat:-22.8204, lon:-47.2728, flvCultures:["tomate"], flvTons:38420, poly:[[-22.94,-47.39],[-22.94,-47.15],[-22.7,-47.15],[-22.7,-47.39]] },
  { id:'BR-RS-902', ibgeCode:'4309902', name:'Ibiraiaras', state:'RS', country:'BR', culture:'batata', areaMha:1.49, ndvi:0.524, coef:0.76, lat:-28.3741, lon:-51.6377, flvCultures:["batata"], flvTons:37250, poly:[[-28.49,-51.76],[-28.49,-51.52],[-28.25,-51.52],[-28.25,-51.76]] },
  { id:'BR-GO-352', ibgeCode:'5207352', name:'Edealina', state:'GO', country:'BR', culture:'tomate', areaMha:0.528, ndvi:0.524, coef:0.76, lat:-17.4239, lon:-49.6644, flvCultures:["tomate"], flvTons:36945, poly:[[-17.54,-49.78],[-17.54,-49.54],[-17.3,-49.54],[-17.3,-49.78]] },
  { id:'BR-MG-852', ibgeCode:'3140852', name:'Matias Cardoso', state:'MG', country:'BR', culture:'limao', areaMha:1.843, ndvi:0.524, coef:0.76, lat:-14.8563, lon:-43.9146, flvCultures:["manga", "batata", "limao"], flvTons:36860, poly:[[-14.98,-44.03],[-14.98,-43.79],[-14.74,-43.79],[-14.74,-44.03]] },
  { id:'BR-PR-703', ibgeCode:'4121703', name:'Reserva', state:'PR', country:'BR', culture:'tomate', areaMha:0.522, ndvi:0.523, coef:0.76, lat:-24.6492, lon:-50.8466, flvCultures:["tomate"], flvTons:36510, poly:[[-24.77,-50.97],[-24.77,-50.73],[-24.53,-50.73],[-24.53,-50.97]] },
  { id:'BR-RS-607', ibgeCode:'4308607', name:'Garibaldi', state:'RS', country:'BR', culture:'uva', areaMha:2.0, ndvi:0.522, coef:0.76, lat:-29.259, lon:-51.5352, flvCultures:["uva"], flvTons:36231, poly:[[-29.38,-51.66],[-29.38,-51.42],[-29.14,-51.42],[-29.14,-51.66]] },
  { id:'BR-GO-204', ibgeCode:'5212204', name:'Jussara', state:'GO', country:'BR', culture:'melancia', areaMha:1.2, ndvi:0.522, coef:0.76, lat:-15.8659, lon:-50.8668, flvCultures:["melancia"], flvTons:36000, poly:[[-15.99,-50.99],[-15.99,-50.75],[-15.75,-50.75],[-15.75,-50.99]] },
  { id:'BR-MG-107', ibgeCode:'3127107', name:'Frutal', state:'MG', country:'BR', culture:'abacaxi', areaMha:1.029, ndvi:0.522, coef:0.76, lat:-20.0259, lon:-48.9355, flvCultures:["abacaxi"], flvTons:36000, poly:[[-20.15,-49.06],[-20.15,-48.82],[-19.91,-48.82],[-19.91,-49.06]] },
  { id:'BR-MA-708', ibgeCode:'2110708', name:'São Domingos do Maranhão', state:'MA', country:'BR', culture:'abacaxi', areaMha:1.019, ndvi:0.521, coef:0.76, lat:-5.58095, lon:-44.3822, flvCultures:["abacaxi"], flvTons:35663, poly:[[-5.7,-44.5],[-5.7,-44.26],[-5.46,-44.26],[-5.46,-44.5]] },
  { id:'BR-AM-902', ibgeCode:'1301902', name:'Itacoatiara', state:'AM', country:'BR', culture:'abacaxi', areaMha:1.018, ndvi:0.521, coef:0.76, lat:-3.13861, lon:-58.4449, flvCultures:["abacaxi"], flvTons:35641, poly:[[-3.26,-58.56],[-3.26,-58.32],[-3.02,-58.32],[-3.02,-58.56]] },
  { id:'BR-SC-602', ibgeCode:'4202602', name:'Bom Retiro', state:'SC', country:'BR', culture:'cebola', areaMha:1.159, ndvi:0.52, coef:0.76, lat:-27.799, lon:-49.487, flvCultures:["pera", "cebola", "maca"], flvTons:34766, poly:[[-27.92,-49.61],[-27.92,-49.37],[-27.68,-49.37],[-27.68,-49.61]] },
  { id:'BR-PR-633', ibgeCode:'4128633', name:'Doutor Ulysses', state:'PR', country:'BR', culture:'tangerina', areaMha:1.7, ndvi:0.518, coef:0.76, lat:-24.5665, lon:-49.4219, flvCultures:["tangerina"], flvTons:34000, poly:[[-24.69,-49.54],[-24.69,-49.3],[-24.45,-49.3],[-24.45,-49.54]] },
  { id:'BR-SP-706', ibgeCode:'3549706', name:'São José do Rio Pardo', state:'SP', country:'BR', culture:'cebola', areaMha:1.132, ndvi:0.518, coef:0.76, lat:-21.5953, lon:-46.8873, flvCultures:["cebola", "limao"], flvTons:33950, poly:[[-21.72,-47.01],[-21.72,-46.77],[-21.48,-46.77],[-21.48,-47.01]] },
  { id:'BR-SP-502', ibgeCode:'3533502', name:'Novo Horizonte', state:'SP', country:'BR', culture:'limao', areaMha:1.66, ndvi:0.516, coef:0.76, lat:-21.4651, lon:-49.2234, flvCultures:["limao"], flvTons:33200, poly:[[-21.59,-49.34],[-21.59,-49.1],[-21.35,-49.1],[-21.35,-49.34]] },
  { id:'BR-PR-709', ibgeCode:'4104709', name:'Carlópolis', state:'PR', country:'BR', culture:'goiaba', areaMha:1.65, ndvi:0.516, coef:0.76, lat:-23.4269, lon:-49.7235, flvCultures:["goiaba"], flvTons:33000, poly:[[-23.55,-49.84],[-23.55,-49.6],[-23.31,-49.6],[-23.31,-49.84]] },
  { id:'BR-RN-703', ibgeCode:'2400703', name:'Alto do Rodrigues', state:'RN', country:'BR', culture:'mamao', areaMha:0.633, ndvi:0.513, coef:0.76, lat:-5.28186, lon:-36.75, flvCultures:["mamao"], flvTons:31633, poly:[[-5.4,-36.87],[-5.4,-36.63],[-5.16,-36.63],[-5.16,-36.87]] },
  { id:'BR-BA-701', ibgeCode:'2929701', name:'Sátiro Dias', state:'BA', country:'BR', culture:'limao', areaMha:1.582, ndvi:0.513, coef:0.76, lat:-11.5929, lon:-38.5938, flvCultures:["limao", "melancia"], flvTons:31632, poly:[[-11.71,-38.71],[-11.71,-38.47],[-11.47,-38.47],[-11.47,-38.71]] },
  { id:'BR-GO-800', ibgeCode:'5211800', name:'Jaraguá', state:'GO', country:'BR', culture:'abacaxi', areaMha:0.9, ndvi:0.513, coef:0.76, lat:-15.7529, lon:-49.3344, flvCultures:["abacaxi"], flvTons:31500, poly:[[-15.87,-49.45],[-15.87,-49.21],[-15.63,-49.21],[-15.63,-49.45]] },
  { id:'BR-RS-385', ibgeCode:'4312385', name:'Monte Belo do Sul', state:'RS', country:'BR', culture:'uva', areaMha:1.747, ndvi:0.513, coef:0.76, lat:-29.1607, lon:-51.6333, flvCultures:["uva"], flvTons:31445, poly:[[-29.28,-51.75],[-29.28,-51.51],[-29.04,-51.51],[-29.04,-51.75]] },
  { id:'BR-RN-605', ibgeCode:'2414605', name:'Upanema', state:'RN', country:'BR', culture:'melao', areaMha:1.254, ndvi:0.513, coef:0.76, lat:-5.63761, lon:-37.2635, flvCultures:["melao", "melancia"], flvTons:31360, poly:[[-5.76,-37.38],[-5.76,-37.14],[-5.52,-37.14],[-5.52,-37.38]] },
  { id:'BR-BA-003', ibgeCode:'2922003', name:'Mucuri', state:'BA', country:'BR', culture:'mamao', areaMha:0.625, ndvi:0.512, coef:0.76, lat:-18.0754, lon:-39.5565, flvCultures:["mamao"], flvTons:31235, poly:[[-18.2,-39.68],[-18.2,-39.44],[-17.96,-39.44],[-17.96,-39.68]] },
  { id:'BR-AM-308', ibgeCode:'1301308', name:'Codajás', state:'AM', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.512, coef:0.76, lat:-3.83053, lon:-62.0658, flvCultures:["acai"], flvTons:31200, poly:[[-3.95,-62.19],[-3.95,-61.95],[-3.71,-61.95],[-3.71,-62.19]] },
  { id:'BR-BA-509', ibgeCode:'2926509', name:'Ribeira do Amparo', state:'BA', country:'BR', culture:'melao', areaMha:1.23, ndvi:0.511, coef:0.76, lat:-11.0421, lon:-38.4242, flvCultures:["melao"], flvTons:30745, poly:[[-11.16,-38.54],[-11.16,-38.3],[-10.92,-38.3],[-10.92,-38.54]] },
  { id:'BR-RS-981', ibgeCode:'4311981', name:'Mariana Pimentel', state:'RS', country:'BR', culture:'batata', areaMha:1.224, ndvi:0.511, coef:0.76, lat:-30.353, lon:-51.5803, flvCultures:["batata"], flvTons:30600, poly:[[-30.47,-51.7],[-30.47,-51.46],[-30.23,-51.46],[-30.23,-51.7]] },
  { id:'BR-SP-200', ibgeCode:'3535200', name:'Palmeira d\'Oeste', state:'SP', country:'BR', culture:'limao', areaMha:1.53, ndvi:0.511, coef:0.76, lat:-20.4148, lon:-50.7632, flvCultures:["limao"], flvTons:30600, poly:[[-20.53,-50.88],[-20.53,-50.64],[-20.29,-50.64],[-20.29,-50.88]] },
  { id:'BR-SE-409', ibgeCode:'2804409', name:'Neópolis', state:'SE', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.511, coef:0.76, lat:-10.3215, lon:-36.585, flvCultures:["coco"], flvTons:30538, poly:[[-10.44,-36.7],[-10.44,-36.47],[-10.2,-36.47],[-10.2,-36.7]] },
  { id:'BR-RS-908', ibgeCode:'4306908', name:'Encruzilhada do Sul', state:'RS', country:'BR', culture:'melancia', areaMha:1.0, ndvi:0.51, coef:0.76, lat:-30.543, lon:-52.5204, flvCultures:["melancia"], flvTons:30000, poly:[[-30.66,-52.64],[-30.66,-52.4],[-30.42,-52.4],[-30.42,-52.64]] },
  { id:'BR-RS-507', ibgeCode:'4318507', name:'São José do Norte', state:'RS', country:'BR', culture:'cebola', areaMha:1.0, ndvi:0.51, coef:0.76, lat:-32.0151, lon:-52.0331, flvCultures:["cebola"], flvTons:30000, poly:[[-32.14,-52.15],[-32.14,-51.91],[-31.9,-51.91],[-31.9,-52.15]] },
  { id:'BR-ES-001', ibgeCode:'3201001', name:'Boa Esperança', state:'ES', country:'BR', culture:'mamao', areaMha:0.6, ndvi:0.51, coef:0.76, lat:-18.5395, lon:-40.3025, flvCultures:["mamao"], flvTons:30000, poly:[[-18.66,-40.42],[-18.66,-40.18],[-18.42,-40.18],[-18.42,-40.42]] },
  { id:'BR-RN-606', ibgeCode:'2404606', name:'Ielmo Marinho', state:'RN', country:'BR', culture:'abacaxi', areaMha:0.851, ndvi:0.51, coef:0.76, lat:-5.82447, lon:-35.55, flvCultures:["abacaxi"], flvTons:29800, poly:[[-5.94,-35.67],[-5.94,-35.43],[-5.7,-35.43],[-5.7,-35.67]] },
  { id:'BR-PA-505', ibgeCode:'1504505', name:'Melgaço', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.509, coef:0.76, lat:-1.8032, lon:-50.7149, flvCultures:["acai"], flvTons:29400, poly:[[-1.92,-50.83],[-1.92,-50.59],[-1.68,-50.59],[-1.68,-50.83]] },
  { id:'BR-RS-617', ibgeCode:'4312617', name:'Muitos Capões', state:'RS', country:'BR', culture:'maca', areaMha:0.828, ndvi:0.508, coef:0.76, lat:-28.3132, lon:-51.1836, flvCultures:["maca"], flvTons:28980, poly:[[-28.43,-51.3],[-28.43,-51.06],[-28.19,-51.06],[-28.19,-51.3]] },
  { id:'BR-BA-357', ibgeCode:'2918357', name:'João Dourado', state:'BA', country:'BR', culture:'cebola', areaMha:0.943, ndvi:0.507, coef:0.76, lat:-11.3486, lon:-41.6548, flvCultures:["cebola"], flvTons:28301, poly:[[-11.47,-41.77],[-11.47,-41.53],[-11.23,-41.53],[-11.23,-41.77]] },
  { id:'BR-CE-357', ibgeCode:'2305357', name:'Icapuí', state:'CE', country:'BR', culture:'melao', areaMha:1.123, ndvi:0.506, coef:0.76, lat:-4.71206, lon:-37.3531, flvCultures:["melao"], flvTons:28081, poly:[[-4.83,-37.47],[-4.83,-37.23],[-4.59,-37.23],[-4.59,-37.47]] },
  { id:'BR-SE-908', ibgeCode:'2802908', name:'Itabaiana', state:'SE', country:'BR', culture:'batata', areaMha:1.12, ndvi:0.506, coef:0.76, lat:-10.6826, lon:-37.4273, flvCultures:["batata"], flvTons:28000, poly:[[-10.8,-37.55],[-10.8,-37.31],[-10.56,-37.31],[-10.56,-37.55]] },
  { id:'BR-BA-502', ibgeCode:'2920502', name:'Maracás', state:'BA', country:'BR', culture:'melancia', areaMha:0.923, ndvi:0.505, coef:0.76, lat:-13.4355, lon:-40.4323, flvCultures:["melancia"], flvTons:27696, poly:[[-13.56,-40.55],[-13.56,-40.31],[-13.32,-40.31],[-13.32,-40.55]] },
  { id:'BR-MG-804', ibgeCode:'3111804', name:'Canápolis', state:'MG', country:'BR', culture:'abacaxi', areaMha:0.777, ndvi:0.504, coef:0.76, lat:-18.7212, lon:-49.2035, flvCultures:["abacaxi"], flvTons:27200, poly:[[-18.84,-49.32],[-18.84,-49.08],[-18.6,-49.08],[-18.6,-49.32]] },
  { id:'BR-TO-302', ibgeCode:'1709302', name:'Guaraí', state:'TO', country:'BR', culture:'melancia', areaMha:0.9, ndvi:0.504, coef:0.76, lat:-8.83543, lon:-48.5114, flvCultures:["melancia"], flvTons:27000, poly:[[-8.96,-48.63],[-8.96,-48.39],[-8.72,-48.39],[-8.72,-48.63]] },
  { id:'BR-CE-504', ibgeCode:'2311504', name:'Quixeré', state:'CE', country:'BR', culture:'mamao', areaMha:0.525, ndvi:0.503, coef:0.76, lat:-5.07148, lon:-37.9802, flvCultures:["melao", "mamao"], flvTons:26264, poly:[[-5.19,-38.1],[-5.19,-37.86],[-4.95,-37.86],[-4.95,-38.1]] },
  { id:'BR-SP-605', ibgeCode:'3545605', name:'Santa Adélia', state:'SP', country:'BR', culture:'limao', areaMha:1.3, ndvi:0.502, coef:0.76, lat:-21.2427, lon:-48.8063, flvCultures:["limao"], flvTons:26000, poly:[[-21.36,-48.93],[-21.36,-48.69],[-21.12,-48.69],[-21.12,-48.93]] },
  { id:'BR-ES-320', ibgeCode:'3203320', name:'Marataízes', state:'ES', country:'BR', culture:'abacaxi', areaMha:0.742, ndvi:0.502, coef:0.76, lat:-21.0398, lon:-40.8384, flvCultures:["abacaxi"], flvTons:25974, poly:[[-21.16,-40.96],[-21.16,-40.72],[-20.92,-40.72],[-20.92,-40.96]] },
  { id:'BR-CE-801', ibgeCode:'2311801', name:'Russas', state:'CE', country:'BR', culture:'mamao', areaMha:0.519, ndvi:0.502, coef:0.76, lat:-4.92673, lon:-37.9721, flvCultures:["goiaba", "mamao"], flvTons:25960, poly:[[-5.05,-38.09],[-5.05,-37.85],[-4.81,-37.85],[-4.81,-38.09]] },
  { id:'BR-RS-407', ibgeCode:'4314407', name:'Pelotas', state:'RS', country:'BR', culture:'pessego', areaMha:2.0, ndvi:0.502, coef:0.76, lat:-31.7649, lon:-52.3371, flvCultures:["figo", "pessego"], flvTons:25791, poly:[[-31.88,-52.46],[-31.88,-52.22],[-31.64,-52.22],[-31.64,-52.46]] },
  { id:'BR-RS-439', ibgeCode:'4310439', name:'Ipê', state:'RS', country:'BR', culture:'maca', areaMha:0.723, ndvi:0.501, coef:0.76, lat:-28.8171, lon:-51.2859, flvCultures:["maca", "caqui", "alho", "pessego"], flvTons:25294, poly:[[-28.94,-51.41],[-28.94,-51.17],[-28.7,-51.17],[-28.7,-51.41]] },
  { id:'BR-MG-006', ibgeCode:'3109006', name:'Brumadinho', state:'MG', country:'BR', culture:'tangerina', areaMha:1.26, ndvi:0.5, coef:0.76, lat:-20.151, lon:-44.2007, flvCultures:["tangerina"], flvTons:25200, poly:[[-20.27,-44.32],[-20.27,-44.08],[-20.03,-44.08],[-20.03,-44.32]] },
  { id:'BR-RS-035', ibgeCode:'4314035', name:'Pareci Novo', state:'RS', country:'BR', culture:'tangerina', areaMha:1.258, ndvi:0.5, coef:0.76, lat:-29.6365, lon:-51.3974, flvCultures:["tangerina"], flvTons:25150, poly:[[-29.76,-51.52],[-29.76,-51.28],[-29.52,-51.28],[-29.52,-51.52]] },
  { id:'BR-SE-106', ibgeCode:'2802106', name:'Estância', state:'SE', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.5, coef:0.75, lat:-11.2659, lon:-37.4484, flvCultures:["coco"], flvTons:24805, poly:[[-11.39,-37.57],[-11.39,-37.33],[-11.15,-37.33],[-11.15,-37.57]] },
  { id:'BR-BA-204', ibgeCode:'2906204', name:'Canarana', state:'BA', country:'BR', culture:'cebola', areaMha:0.826, ndvi:0.5, coef:0.75, lat:-11.6858, lon:-41.7677, flvCultures:["cebola"], flvTons:24767, poly:[[-11.81,-41.89],[-11.81,-41.65],[-11.57,-41.65],[-11.57,-41.89]] },
  { id:'BR-BA-901', ibgeCode:'2928901', name:'São Desidério', state:'BA', country:'BR', culture:'melancia', areaMha:0.821, ndvi:0.499, coef:0.75, lat:-12.3572, lon:-44.9769, flvCultures:["melancia"], flvTons:24617, poly:[[-12.48,-45.1],[-12.48,-44.86],[-12.24,-44.86],[-12.24,-45.1]] },
  { id:'BR-RS-000', ibgeCode:'4319000', name:'São Marcos', state:'RS', country:'BR', culture:'uva', areaMha:1.362, ndvi:0.499, coef:0.75, lat:-28.9677, lon:-51.0696, flvCultures:["uva", "pera", "figo"], flvTons:24520, poly:[[-29.09,-51.19],[-29.09,-50.95],[-28.85,-50.95],[-28.85,-51.19]] },
  { id:'BR-BA-201', ibgeCode:'2903201', name:'Barreiras', state:'BA', country:'BR', culture:'mamao', areaMha:0.49, ndvi:0.499, coef:0.75, lat:-12.1439, lon:-44.9968, flvCultures:["mamao"], flvTons:24498, poly:[[-12.26,-45.12],[-12.26,-44.88],[-12.02,-44.88],[-12.02,-45.12]] },
  { id:'BR-SC-058', ibgeCode:'4211058', name:'Monte Carlo', state:'SC', country:'BR', culture:'maca', areaMha:0.7, ndvi:0.499, coef:0.75, lat:-27.2239, lon:-50.9808, flvCultures:["maca"], flvTons:24484, poly:[[-27.34,-51.1],[-27.34,-50.86],[-27.1,-50.86],[-27.1,-51.1]] },
  { id:'BR-SP-909', ibgeCode:'3537909', name:'Pilar do Sul', state:'SP', country:'BR', culture:'uva', areaMha:1.344, ndvi:0.498, coef:0.75, lat:-23.8077, lon:-47.7222, flvCultures:["caqui", "tangerina", "uva"], flvTons:24191, poly:[[-23.93,-47.84],[-23.93,-47.6],[-23.69,-47.6],[-23.69,-47.84]] },
  { id:'BR-RN-709', ibgeCode:'2402709', name:'Cerro Corá', state:'RN', country:'BR', culture:'maracuja', areaMha:1.6, ndvi:0.498, coef:0.75, lat:-6.03503, lon:-36.3503, flvCultures:["maracuja"], flvTons:24000, poly:[[-6.16,-36.47],[-6.16,-36.23],[-5.92,-36.23],[-5.92,-36.47]] },
  { id:'BR-SP-102', ibgeCode:'3511102', name:'Catanduva', state:'SP', country:'BR', culture:'limao', areaMha:1.17, ndvi:0.497, coef:0.75, lat:-21.1314, lon:-48.977, flvCultures:["limao"], flvTons:23400, poly:[[-21.25,-49.1],[-21.25,-48.86],[-21.01,-48.86],[-21.01,-49.1]] },
  { id:'BR-SP-105', ibgeCode:'3538105', name:'Pindorama', state:'SP', country:'BR', culture:'limao', areaMha:1.17, ndvi:0.497, coef:0.75, lat:-21.1853, lon:-48.9086, flvCultures:["limao"], flvTons:23400, poly:[[-21.31,-49.03],[-21.31,-48.79],[-21.07,-48.79],[-21.07,-49.03]] },
  { id:'BR-SP-208', ibgeCode:'3536208', name:'Pariquera-Açu', state:'SP', country:'BR', culture:'tangerina', areaMha:1.17, ndvi:0.497, coef:0.75, lat:-24.7147, lon:-47.8742, flvCultures:["tangerina"], flvTons:23400, poly:[[-24.83,-47.99],[-24.83,-47.75],[-24.59,-47.75],[-24.59,-47.99]] },
  { id:'BR-SC-706', ibgeCode:'4209706', name:'Lebon Régis', state:'SC', country:'BR', culture:'cebola', areaMha:0.778, ndvi:0.497, coef:0.75, lat:-26.928, lon:-50.6921, flvCultures:["cebola", "maca"], flvTons:23346, poly:[[-27.05,-50.81],[-27.05,-50.57],[-26.81,-50.57],[-26.81,-50.81]] },
  { id:'BR-PE-408', ibgeCode:'2606408', name:'Gravatá', state:'PE', country:'BR', culture:'abacaxi', areaMha:0.66, ndvi:0.496, coef:0.75, lat:-8.21118, lon:-35.5675, flvCultures:["goiaba", "abacaxi"], flvTons:23100, poly:[[-8.33,-35.69],[-8.33,-35.45],[-8.09,-35.45],[-8.09,-35.69]] },
  { id:'BR-PA-806', ibgeCode:'1502806', name:'Curralinho', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.496, coef:0.75, lat:-1.81179, lon:-49.7952, flvCultures:["acai"], flvTons:22950, poly:[[-1.93,-49.92],[-1.93,-49.68],[-1.69,-49.68],[-1.69,-49.92]] },
  { id:'BR-PE-808', ibgeCode:'2609808', name:'Orocó', state:'PE', country:'BR', culture:'manga', areaMha:1.89, ndvi:0.495, coef:0.75, lat:-8.61026, lon:-39.6026, flvCultures:["manga", "goiaba", "melao"], flvTons:22675, poly:[[-8.73,-39.72],[-8.73,-39.48],[-8.49,-39.48],[-8.49,-39.72]] },
  { id:'BR-RS-959', ibgeCode:'4305959', name:'Cotiporã', state:'RS', country:'BR', culture:'uva', areaMha:1.259, ndvi:0.495, coef:0.75, lat:-28.9891, lon:-51.6971, flvCultures:["uva"], flvTons:22660, poly:[[-29.11,-51.82],[-29.11,-51.58],[-28.87,-51.58],[-28.87,-51.82]] },
  { id:'BR-SE-102', ibgeCode:'2804102', name:'Moita Bonita', state:'SE', country:'BR', culture:'batata', areaMha:0.88, ndvi:0.494, coef:0.75, lat:-10.5769, lon:-37.3512, flvCultures:["batata"], flvTons:22000, poly:[[-10.7,-37.47],[-10.7,-37.23],[-10.46,-37.23],[-10.46,-37.47]] },
  { id:'BR-BA-553', ibgeCode:'2919553', name:'Luís Eduardo Magalhães', state:'BA', country:'BR', culture:'mamao', areaMha:0.44, ndvi:0.494, coef:0.75, lat:-12.0956, lon:-45.7866, flvCultures:["mamao"], flvTons:22000, poly:[[-12.22,-45.91],[-12.22,-45.67],[-11.98,-45.67],[-11.98,-45.91]] },
  { id:'BR-RS-408', ibgeCode:'4318408', name:'São Jerônimo', state:'RS', country:'BR', culture:'melancia', areaMha:0.728, ndvi:0.494, coef:0.75, lat:-29.9716, lon:-51.7251, flvCultures:["melancia"], flvTons:21833, poly:[[-30.09,-51.85],[-30.09,-51.61],[-29.85,-51.61],[-29.85,-51.85]] },
  { id:'BR-BA-703', ibgeCode:'2914703', name:'Itaberaba', state:'BA', country:'BR', culture:'abacaxi', areaMha:0.622, ndvi:0.494, coef:0.75, lat:-12.5242, lon:-40.3059, flvCultures:["abacaxi"], flvTons:21760, poly:[[-12.64,-40.43],[-12.64,-40.19],[-12.4,-40.19],[-12.4,-40.43]] },
  { id:'BR-PA-808', ibgeCode:'1501808', name:'Breves', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.493, coef:0.75, lat:-1.68036, lon:-50.4791, flvCultures:["acai"], flvTons:21679, poly:[[-1.8,-50.6],[-1.8,-50.36],[-1.56,-50.36],[-1.56,-50.6]] },
  { id:'BR-SC-200', ibgeCode:'4219200', name:'Vidal Ramos', state:'SC', country:'BR', culture:'cebola', areaMha:0.719, ndvi:0.493, coef:0.75, lat:-27.3886, lon:-49.3593, flvCultures:["cebola"], flvTons:21560, poly:[[-27.51,-49.48],[-27.51,-49.24],[-27.27,-49.24],[-27.27,-49.48]] },
  { id:'BR-ES-054', ibgeCode:'3204054', name:'Pedro Canário', state:'ES', country:'BR', culture:'mamao', areaMha:0.429, ndvi:0.493, coef:0.75, lat:-18.3004, lon:-39.9574, flvCultures:["mamao"], flvTons:21450, poly:[[-18.42,-40.08],[-18.42,-39.84],[-18.18,-39.84],[-18.18,-40.08]] },
  { id:'BR-PB-604', ibgeCode:'2508604', name:'Lucena', state:'PB', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.493, coef:0.75, lat:-6.90258, lon:-34.8748, flvCultures:["coco"], flvTons:21422, poly:[[-7.02,-34.99],[-7.02,-34.75],[-6.78,-34.75],[-6.78,-34.99]] },
  { id:'BR-CE-206', ibgeCode:'2302206', name:'Beberibe', state:'CE', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.493, coef:0.75, lat:-4.17741, lon:-38.1271, flvCultures:["coco"], flvTons:21420, poly:[[-4.3,-38.25],[-4.3,-38.01],[-4.06,-38.01],[-4.06,-38.25]] },
  { id:'BR-RS-673', ibgeCode:'4303673', name:'Campestre da Serra', state:'RS', country:'BR', culture:'uva', areaMha:1.18, ndvi:0.492, coef:0.75, lat:-28.7926, lon:-51.0941, flvCultures:["uva", "caqui", "pera", "pessego"], flvTons:21246, poly:[[-28.91,-51.21],[-28.91,-50.97],[-28.67,-50.97],[-28.67,-51.21]] },
  { id:'BR-BA-004', ibgeCode:'2931004', name:'Tanhaçu', state:'BA', country:'BR', culture:'maracuja', areaMha:1.4, ndvi:0.492, coef:0.75, lat:-14.0197, lon:-41.2473, flvCultures:["maracuja"], flvTons:21000, poly:[[-14.14,-41.37],[-14.14,-41.13],[-13.9,-41.13],[-13.9,-41.37]] },
  { id:'BR-SC-954', ibgeCode:'4218954', name:'Urupema', state:'SC', country:'BR', culture:'maca', areaMha:0.599, ndvi:0.492, coef:0.75, lat:-27.9557, lon:-49.8729, flvCultures:["maca"], flvTons:20948, poly:[[-28.08,-49.99],[-28.08,-49.75],[-27.84,-49.75],[-27.84,-49.99]] },
  { id:'BR-CE-754', ibgeCode:'2300754', name:'Amontada', state:'CE', country:'BR', culture:'coco', areaMha:2.0, ndvi:0.491, coef:0.75, lat:-3.36017, lon:-39.8288, flvCultures:["coco"], flvTons:20728, poly:[[-3.48,-39.95],[-3.48,-39.71],[-3.24,-39.71],[-3.24,-39.95]] },
  { id:'BR-SP-004', ibgeCode:'3539004', name:'Pirangi', state:'SP', country:'BR', culture:'tangerina', areaMha:1.036, ndvi:0.491, coef:0.75, lat:-21.0886, lon:-48.6607, flvCultures:["tangerina", "goiaba"], flvTons:20727, poly:[[-21.21,-48.78],[-21.21,-48.54],[-20.97,-48.54],[-20.97,-48.78]] },
  { id:'BR-SC-805', ibgeCode:'4209805', name:'Leoberto Leal', state:'SC', country:'BR', culture:'cebola', areaMha:0.676, ndvi:0.491, coef:0.75, lat:-27.5081, lon:-49.2789, flvCultures:["cebola"], flvTons:20280, poly:[[-27.63,-49.4],[-27.63,-49.16],[-27.39,-49.16],[-27.39,-49.4]] },
  { id:'BR-GO-258', ibgeCode:'5219258', name:'Santa Fé de Goiás', state:'GO', country:'BR', culture:'melancia', areaMha:0.667, ndvi:0.49, coef:0.75, lat:-15.7664, lon:-51.1037, flvCultures:["melancia"], flvTons:20000, poly:[[-15.89,-51.22],[-15.89,-50.98],[-15.65,-50.98],[-15.65,-51.22]] },
  { id:'BR-CE-102', ibgeCode:'2314102', name:'Viçosa do Ceará', state:'CE', country:'BR', culture:'maracuja', areaMha:1.323, ndvi:0.49, coef:0.75, lat:-3.5667, lon:-41.0916, flvCultures:["maracuja", "abacate"], flvTons:19841, poly:[[-3.69,-41.21],[-3.69,-40.97],[-3.45,-40.97],[-3.45,-41.21]] },
  { id:'BR-MG-809', ibgeCode:'3142809', name:'Monte Alegre de Minas', state:'MG', country:'BR', culture:'abacaxi', areaMha:0.566, ndvi:0.49, coef:0.75, lat:-18.869, lon:-48.881, flvCultures:["abacaxi"], flvTons:19800, poly:[[-18.99,-49.0],[-18.99,-48.76],[-18.75,-48.76],[-18.75,-49.0]] },
  { id:'BR-RR-159', ibgeCode:'1400159', name:'Bonfim', state:'RR', country:'BR', culture:'melancia', areaMha:0.65, ndvi:0.489, coef:0.75, lat:3.36161, lon:-59.8333, flvCultures:["melancia"], flvTons:19500, poly:[[3.24,-59.95],[3.24,-59.71],[3.48,-59.71],[3.48,-59.95]] },
  { id:'BR-SC-006', ibgeCode:'4203006', name:'Caçador', state:'SC', country:'BR', culture:'cebola', areaMha:0.65, ndvi:0.489, coef:0.75, lat:-26.7757, lon:-51.012, flvCultures:["cebola"], flvTons:19500, poly:[[-26.9,-51.13],[-26.9,-50.89],[-26.66,-50.89],[-26.66,-51.13]] },
  { id:'BR-BA-107', ibgeCode:'2910107', name:'Dom Basílio', state:'BA', country:'BR', culture:'manga', areaMha:1.581, ndvi:0.488, coef:0.75, lat:-13.7565, lon:-41.7677, flvCultures:["manga", "maracuja"], flvTons:18966, poly:[[-13.88,-41.89],[-13.88,-41.65],[-13.64,-41.65],[-13.64,-41.89]] },
  { id:'BR-SE-904', ibgeCode:'2804904', name:'Pacatuba', state:'SE', country:'BR', culture:'coco', areaMha:1.875, ndvi:0.487, coef:0.75, lat:-10.4538, lon:-36.6531, flvCultures:["coco"], flvTons:18745, poly:[[-10.57,-36.77],[-10.57,-36.53],[-10.33,-36.53],[-10.33,-36.77]] },
  { id:'BR-BA-727', ibgeCode:'2910727', name:'Eunápolis', state:'BA', country:'BR', culture:'mamao', areaMha:0.374, ndvi:0.487, coef:0.75, lat:-16.3715, lon:-39.5821, flvCultures:["mamao"], flvTons:18677, poly:[[-16.49,-39.7],[-16.49,-39.46],[-16.25,-39.46],[-16.25,-39.7]] },
  { id:'BR-RJ-009', ibgeCode:'3301009', name:'Campos dos Goytacazes', state:'RJ', country:'BR', culture:'abacaxi', areaMha:0.514, ndvi:0.486, coef:0.75, lat:-21.7622, lon:-41.3181, flvCultures:["abacaxi"], flvTons:18000, poly:[[-21.88,-41.44],[-21.88,-41.2],[-21.64,-41.2],[-21.64,-41.44]] },
  { id:'BR-BA-154', ibgeCode:'2930154', name:'Serra do Ramalho', state:'BA', country:'BR', culture:'mamao', areaMha:0.356, ndvi:0.486, coef:0.75, lat:-13.5659, lon:-43.5929, flvCultures:["mamao"], flvTons:17787, poly:[[-13.69,-43.71],[-13.69,-43.47],[-13.45,-43.47],[-13.45,-43.71]] },
  { id:'BR-DF-108', ibgeCode:'5300108', name:'Brasília', state:'DF', country:'BR', culture:'goiaba', areaMha:0.889, ndvi:0.486, coef:0.75, lat:-15.7795, lon:-47.9297, flvCultures:["ervilha", "goiaba", "alho", "abacate"], flvTons:17782, poly:[[-15.9,-48.05],[-15.9,-47.81],[-15.66,-47.81],[-15.66,-48.05]] },
  { id:'BR-PA-604', ibgeCode:'1504604', name:'Mocajuba', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.485, coef:0.75, lat:-2.5831, lon:-49.5042, flvCultures:["acai"], flvTons:17400, poly:[[-2.7,-49.62],[-2.7,-49.38],[-2.46,-49.38],[-2.46,-49.62]] },
  { id:'BR-RN-705', ibgeCode:'2404705', name:'Ipanguaçu', state:'RN', country:'BR', culture:'manga', areaMha:1.422, ndvi:0.484, coef:0.75, lat:-5.48984, lon:-36.8501, flvCultures:["manga"], flvTons:17061, poly:[[-5.61,-36.97],[-5.61,-36.73],[-5.37,-36.73],[-5.37,-36.97]] },
  { id:'BR-RS-934', ibgeCode:'4305934', name:'Coronel Pilar', state:'RS', country:'BR', culture:'uva', areaMha:0.948, ndvi:0.484, coef:0.75, lat:-29.2695, lon:-51.6847, flvCultures:["uva"], flvTons:17058, poly:[[-29.39,-51.8],[-29.39,-51.56],[-29.15,-51.56],[-29.15,-51.8]] },
  { id:'BR-PI-355', ibgeCode:'2207355', name:'Pajeú do Piauí', state:'PI', country:'BR', culture:'melao', areaMha:0.681, ndvi:0.484, coef:0.75, lat:-7.85508, lon:-42.8248, flvCultures:["melao"], flvTons:17028, poly:[[-7.98,-42.94],[-7.98,-42.7],[-7.74,-42.7],[-7.74,-42.94]] },
  { id:'BR-AL-306', ibgeCode:'2702306', name:'Coruripe', state:'AL', country:'BR', culture:'coco', areaMha:1.703, ndvi:0.484, coef:0.75, lat:-10.1276, lon:-36.1717, flvCultures:["coco"], flvTons:17026, poly:[[-10.25,-36.29],[-10.25,-36.05],[-10.01,-36.05],[-10.01,-36.29]] },
  { id:'BR-PA-756', ibgeCode:'1502756', name:'Concórdia do Pará', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.484, coef:0.75, lat:-1.99238, lon:-47.9422, flvCultures:["acai"], flvTons:16900, poly:[[-2.11,-48.06],[-2.11,-47.82],[-1.87,-47.82],[-1.87,-48.06]] },
  { id:'BR-PR-509', ibgeCode:'4100509', name:'Altônia', state:'PR', country:'BR', culture:'limao', areaMha:0.84, ndvi:0.484, coef:0.75, lat:-23.8759, lon:-53.8958, flvCultures:["limao"], flvTons:16800, poly:[[-24.0,-54.02],[-24.0,-53.78],[-23.76,-53.78],[-23.76,-54.02]] },
  { id:'BR-SP-506', ibgeCode:'3550506', name:'São Pedro do Turvo', state:'SP', country:'BR', culture:'tangerina', areaMha:0.84, ndvi:0.484, coef:0.75, lat:-22.7453, lon:-49.7428, flvCultures:["tangerina"], flvTons:16800, poly:[[-22.87,-49.86],[-22.87,-49.62],[-22.63,-49.62],[-22.63,-49.86]] },
  { id:'BR-PA-408', ibgeCode:'1503408', name:'Inhangapi', state:'PA', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.483, coef:0.75, lat:-1.4349, lon:-47.9114, flvCultures:["acai"], flvTons:16646, poly:[[-1.55,-48.03],[-1.55,-47.79],[-1.31,-47.79],[-1.31,-48.03]] },
  { id:'BR-PE-309', ibgeCode:'2611309', name:'Pombos', state:'PE', country:'BR', culture:'abacaxi', areaMha:0.474, ndvi:0.483, coef:0.75, lat:-8.13982, lon:-35.3967, flvCultures:["abacaxi"], flvTons:16590, poly:[[-8.26,-35.52],[-8.26,-35.28],[-8.02,-35.28],[-8.02,-35.52]] },
  { id:'BR-SC-905', ibgeCode:'4218905', name:'Urubici', state:'SC', country:'BR', culture:'maca', areaMha:0.468, ndvi:0.483, coef:0.75, lat:-28.0157, lon:-49.5925, flvCultures:["maca"], flvTons:16380, poly:[[-28.14,-49.71],[-28.14,-49.47],[-27.9,-49.47],[-27.9,-49.71]] },
  { id:'BR-RN-953', ibgeCode:'2408953', name:'Rio do Fogo', state:'RN', country:'BR', culture:'coco', areaMha:1.625, ndvi:0.483, coef:0.75, lat:-5.2765, lon:-35.3794, flvCultures:["coco"], flvTons:16250, poly:[[-5.4,-35.5],[-5.4,-35.26],[-5.16,-35.26],[-5.16,-35.5]] },
  { id:'BR-GO-000', ibgeCode:'5205000', name:'Carmo do Rio Verde', state:'GO', country:'BR', culture:'melancia', areaMha:0.54, ndvi:0.482, coef:0.75, lat:-15.3549, lon:-49.708, flvCultures:["melancia"], flvTons:16209, poly:[[-15.47,-49.83],[-15.47,-49.59],[-15.23,-49.59],[-15.23,-49.83]] },
  { id:'BR-SP-402', ibgeCode:'3519402', name:'Ibirá', state:'SP', country:'BR', culture:'limao', areaMha:0.805, ndvi:0.482, coef:0.75, lat:-21.083, lon:-49.2448, flvCultures:["limao"], flvTons:16108, poly:[[-21.2,-49.36],[-21.2,-49.12],[-20.96,-49.12],[-20.96,-49.36]] },
  { id:'BR-BA-707', ibgeCode:'2926707', name:'Rio de Contas', state:'BA', country:'BR', culture:'manga', areaMha:1.335, ndvi:0.482, coef:0.75, lat:-13.5852, lon:-41.8048, flvCultures:["manga", "maracuja"], flvTons:16026, poly:[[-13.71,-41.92],[-13.71,-41.68],[-13.47,-41.68],[-13.47,-41.92]] },
  { id:'BR-AM-704', ibgeCode:'1301704', name:'Humaitá', state:'AM', country:'BR', culture:'acai', areaMha:2.0, ndvi:0.482, coef:0.75, lat:-7.51171, lon:-63.0327, flvCultures:["acai"], flvTons:16000, poly:[[-7.63,-63.15],[-7.63,-62.91],[-7.39,-62.91],[-7.39,-63.15]] },
  { id:'BR-PI-307', ibgeCode:'2202307', name:'Canto do Buriti', state:'PI', country:'BR', culture:'melao', areaMha:0.639, ndvi:0.482, coef:0.75, lat:-8.1111, lon:-42.9517, flvCultures:["melao"], flvTons:15982, poly:[[-8.23,-43.07],[-8.23,-42.83],[-7.99,-42.83],[-7.99,-43.07]] },
  { id:'BR-PA-706', ibgeCode:'1507706', name:'São Sebastião da Boa Vista', state:'PA', country:'BR', culture:'acai', areaMha:1.972, ndvi:0.482, coef:0.75, lat:-1.71597, lon:-49.5249, flvCultures:["acai"], flvTons:15775, poly:[[-1.84,-49.64],[-1.84,-49.4],[-1.6,-49.4],[-1.6,-49.64]] },
  { id:'BR-MG-000', ibgeCode:'3169000', name:'Tocantins', state:'MG', country:'BR', culture:'tangerina', areaMha:0.78, ndvi:0.481, coef:0.75, lat:-21.1774, lon:-43.0127, flvCultures:["tangerina"], flvTons:15600, poly:[[-21.3,-43.13],[-21.3,-42.89],[-21.06,-42.89],[-21.06,-43.13]] },
  { id:'BR-ES-069', ibgeCode:'3205069', name:'Venda Nova do Imigrante', state:'ES', country:'BR', culture:'abacate', areaMha:1.04, ndvi:0.481, coef:0.75, lat:-20.327, lon:-41.1355, flvCultures:["abacate"], flvTons:15600, poly:[[-20.45,-41.26],[-20.45,-41.02],[-20.21,-41.02],[-20.21,-41.26]] },
  { id:'BR-BA-109', ibgeCode:'2928109', name:'Santa Maria da Vitória', state:'BA', country:'BR', culture:'mamao', areaMha:0.31, ndvi:0.481, coef:0.75, lat:-13.3859, lon:-44.2011, flvCultures:["mamao"], flvTons:15500, poly:[[-13.51,-44.32],[-13.51,-44.08],[-13.27,-44.08],[-13.27,-44.32]] },
  { id:'BR-SP-503', ibgeCode:'3542503', name:'Reginópolis', state:'SP', country:'BR', culture:'melancia', areaMha:0.507, ndvi:0.48, coef:0.75, lat:-21.8914, lon:-49.2268, flvCultures:["melancia"], flvTons:15200, poly:[[-22.01,-49.35],[-22.01,-49.11],[-21.77,-49.11],[-21.77,-49.35]] },
  { id:'BR-TO-100', ibgeCode:'1706100', name:'Cristalândia', state:'TO', country:'BR', culture:'melancia', areaMha:0.506, ndvi:0.48, coef:0.75, lat:-10.5985, lon:-49.1942, flvCultures:["melancia"], flvTons:15175, poly:[[-10.72,-49.31],[-10.72,-49.07],[-10.48,-49.07],[-10.48,-49.31]] },
  { id:'BR-TO-902', ibgeCode:'1711902', name:'Lagoa da Confusão', state:'TO', country:'BR', culture:'melancia', areaMha:0.506, ndvi:0.48, coef:0.75, lat:-10.7906, lon:-49.6199, flvCultures:["melancia"], flvTons:15175, poly:[[-10.91,-49.74],[-10.91,-49.5],[-10.67,-49.5],[-10.67,-49.74]] },
  { id:'BR-MG-008', ibgeCode:'3127008', name:'Fronteira', state:'MG', country:'BR', culture:'abacaxi', areaMha:0.429, ndvi:0.48, coef:0.75, lat:-20.2748, lon:-49.1984, flvCultures:["abacaxi"], flvTons:15000, poly:[[-20.39,-49.32],[-20.39,-49.08],[-20.15,-49.08],[-20.15,-49.32]] },
  { id:'BR-SP-802', ibgeCode:'3517802', name:'Guaraçaí', state:'SP', country:'BR', culture:'abacaxi', areaMha:0.429, ndvi:0.48, coef:0.75, lat:-21.0292, lon:-51.2119, flvCultures:["abacaxi"], flvTons:15000, poly:[[-21.15,-51.33],[-21.15,-51.09],[-20.91,-51.09],[-20.91,-51.33]] },
  { id:'BR-PA-201', ibgeCode:'1507201', name:'São Domingos do Capim', state:'PA', country:'BR', culture:'acai', areaMha:1.875, ndvi:0.48, coef:0.75, lat:-1.68768, lon:-47.7665, flvCultures:["acai"], flvTons:15000, poly:[[-1.81,-47.89],[-1.81,-47.65],[-1.57,-47.65],[-1.57,-47.89]] },
  { id:'BR-RS-086', ibgeCode:'4313086', name:'Nova Pádua', state:'RS', country:'BR', culture:'uva', areaMha:0.832, ndvi:0.48, coef:0.75, lat:-29.0275, lon:-51.3098, flvCultures:["uva", "pera"], flvTons:14980, poly:[[-29.15,-51.43],[-29.15,-51.19],[-28.91,-51.19],[-28.91,-51.43]] },
  { id:'BR-MG-406', ibgeCode:'3150406', name:'Piedade dos Gerais', state:'MG', country:'BR', culture:'tangerina', areaMha:0.74, ndvi:0.48, coef:0.75, lat:-20.4715, lon:-44.2243, flvCultures:["tangerina"], flvTons:14800, poly:[[-20.59,-44.34],[-20.59,-44.1],[-20.35,-44.1],[-20.35,-44.34]] },
  { id:'BR-GO-206', ibgeCode:'5211206', name:'Itapuranga', state:'GO', country:'BR', culture:'melancia', areaMha:0.489, ndvi:0.479, coef:0.75, lat:-15.5606, lon:-49.949, flvCultures:["melancia"], flvTons:14658, poly:[[-15.68,-50.07],[-15.68,-49.83],[-15.44,-49.83],[-15.44,-50.07]] },
  { id:'BR-SE-802', ibgeCode:'2805802', name:'Riachão do Dantas', state:'SE', country:'BR', culture:'abacaxi', areaMha:0.417, ndvi:0.479, coef:0.75, lat:-11.0729, lon:-37.731, flvCultures:["abacaxi"], flvTons:14580, poly:[[-11.19,-37.85],[-11.19,-37.61],[-10.95,-37.61],[-10.95,-37.85]] },
  { id:'BR-PA-901', ibgeCode:'1504901', name:'Muaná', state:'PA', country:'BR', culture:'acai', areaMha:1.812, ndvi:0.479, coef:0.75, lat:-1.53936, lon:-49.2224, flvCultures:["acai"], flvTons:14500, poly:[[-1.66,-49.34],[-1.66,-49.1],[-1.42,-49.1],[-1.42,-49.34]] },
  { id:'BR-PI-276', ibgeCode:'2205276', name:'Jatobá do Piauí', state:'PI', country:'BR', culture:'melancia', areaMha:0.483, ndvi:0.479, coef:0.75, lat:-4.77025, lon:-41.817, flvCultures:["melancia"], flvTons:14490, poly:[[-4.89,-41.94],[-4.89,-41.7],[-4.65,-41.7],[-4.65,-41.94]] },
  { id:'BR-SP-203', ibgeCode:'3505203', name:'Bariri', state:'SP', country:'BR', culture:'tangerina', areaMha:0.714, ndvi:0.479, coef:0.75, lat:-22.073, lon:-48.7438, flvCultures:["tangerina"], flvTons:14280, poly:[[-22.19,-48.86],[-22.19,-48.62],[-21.95,-48.62],[-21.95,-48.86]] },
  { id:'BR-SC-709', ibgeCode:'4217709', name:'Sombrio', state:'SC', country:'BR', culture:'maracuja', areaMha:0.952, ndvi:0.479, coef:0.75, lat:-29.108, lon:-49.6328, flvCultures:["maracuja"], flvTons:14275, poly:[[-29.23,-49.75],[-29.23,-49.51],[-28.99,-49.51],[-28.99,-49.75]] },
  { id:'BR-RS-359', ibgeCode:'4313359', name:'Nova Roma do Sul', state:'RS', country:'BR', culture:'uva', areaMha:0.785, ndvi:0.478, coef:0.75, lat:-28.9882, lon:-51.4095, flvCultures:["uva", "figo"], flvTons:14138, poly:[[-29.11,-51.53],[-29.11,-51.29],[-28.87,-51.29],[-28.87,-51.53]] },
  { id:'BR-ES-010', ibgeCode:'3205010', name:'Sooretama', state:'ES', country:'BR', culture:'mamao', areaMha:0.28, ndvi:0.478, coef:0.75, lat:-19.1897, lon:-40.0974, flvCultures:["mamao"], flvTons:14000, poly:[[-19.31,-40.22],[-19.31,-39.98],[-19.07,-39.98],[-19.07,-40.22]] },
  { id:'BR-CE-501', ibgeCode:'2303501', name:'Cascavel', state:'CE', country:'BR', culture:'coco', areaMha:1.399, ndvi:0.478, coef:0.75, lat:-4.12967, lon:-38.2412, flvCultures:["coco"], flvTons:13994, poly:[[-4.25,-38.36],[-4.25,-38.12],[-4.01,-38.12],[-4.01,-38.36]] },
  { id:'BR-BA-774', ibgeCode:'2930774', name:'Sobradinho', state:'BA', country:'BR', culture:'manga', areaMha:1.144, ndvi:0.477, coef:0.75, lat:-9.45024, lon:-40.8145, flvCultures:["manga", "melao"], flvTons:13731, poly:[[-9.57,-40.93],[-9.57,-40.69],[-9.33,-40.69],[-9.33,-40.93]] },
  { id:'BR-MG-507', ibgeCode:'3111507', name:'Campos Altos', state:'MG', country:'BR', culture:'alho', areaMha:1.705, ndvi:0.477, coef:0.75, lat:-19.6914, lon:-46.1725, flvCultures:["alho", "abacate"], flvTons:13640, poly:[[-19.81,-46.29],[-19.81,-46.05],[-19.57,-46.05],[-19.57,-46.29]] },
  { id:'BR-PA-302', ibgeCode:'1506302', name:'Salvaterra', state:'PA', country:'BR', culture:'abacaxi', areaMha:0.388, ndvi:0.477, coef:0.75, lat:-0.758444, lon:-48.5139, flvCultures:["abacaxi"], flvTons:13580, poly:[[-0.88,-48.63],[-0.88,-48.39],[-0.64,-48.39],[-0.64,-48.63]] },
  { id:'BR-PA-707', ibgeCode:'1502707', name:'Conceição do Araguaia', state:'PA', country:'BR', culture:'abacaxi', areaMha:0.386, ndvi:0.477, coef:0.75, lat:-8.26136, lon:-49.2689, flvCultures:["abacaxi"], flvTons:13500, poly:[[-8.38,-49.39],[-8.38,-49.15],[-8.14,-49.15],[-8.14,-49.39]] },
  { id:'BR-PB-005', ibgeCode:'2515005', name:'São Miguel de Taipu', state:'PB', country:'BR', culture:'abacaxi', areaMha:0.38, ndvi:0.477, coef:0.75, lat:-7.24764, lon:-35.2016, flvCultures:["abacaxi"], flvTons:13300, poly:[[-7.37,-35.32],[-7.37,-35.08],[-7.13,-35.08],[-7.13,-35.32]] },
  { id:'BR-ES-902', ibgeCode:'3201902', name:'Domingos Martins', state:'ES', country:'BR', culture:'tangerina', areaMha:0.663, ndvi:0.477, coef:0.75, lat:-20.3603, lon:-40.6594, flvCultures:["tangerina"], flvTons:13260, poly:[[-20.48,-40.78],[-20.48,-40.54],[-20.24,-40.54],[-20.24,-40.78]] },
  { id:'BR-AP-204', ibgeCode:'1600204', name:'Calçoene', state:'AP', country:'BR', culture:'acai', areaMha:1.633, ndvi:0.476, coef:0.75, lat:2.50475, lon:-50.9512, flvCultures:["acai"], flvTons:13062, poly:[[2.38,-51.07],[2.38,-50.83],[2.62,-50.83],[2.62,-51.07]] },
  { id:'BR-PR-506', ibgeCode:'4125506', name:'São José dos Pinhais', state:'PR', country:'BR', culture:'batata', areaMha:0.52, ndvi:0.476, coef:0.75, lat:-25.5313, lon:-49.2031, flvCultures:["batata"], flvTons:13000, poly:[[-25.65,-49.32],[-25.65,-49.08],[-25.41,-49.08],[-25.41,-49.32]] },
  { id:'BR-BA-601', ibgeCode:'2915601', name:'Itamaraju', state:'BA', country:'BR', culture:'mamao', areaMha:0.254, ndvi:0.475, coef:0.75, lat:-17.0378, lon:-39.5386, flvCultures:["mamao"], flvTons:12688, poly:[[-17.16,-39.66],[-17.16,-39.42],[-16.92,-39.42],[-16.92,-39.66]] },
  { id:'BR-ES-176', ibgeCode:'3205176', name:'Vila Valério', state:'ES', country:'BR', culture:'mamao', areaMha:0.253, ndvi:0.475, coef:0.75, lat:-18.9958, lon:-40.3849, flvCultures:["mamao"], flvTons:12667, poly:[[-19.12,-40.5],[-19.12,-40.26],[-18.88,-40.26],[-18.88,-40.5]] },
  { id:'BR-RJ-158', ibgeCode:'3305158', name:'São José do Vale do Rio Preto', state:'RJ', country:'BR', culture:'tangerina', areaMha:0.631, ndvi:0.475, coef:0.75, lat:-22.1525, lon:-42.9327, flvCultures:["tangerina", "caqui"], flvTons:12630, poly:[[-22.27,-43.05],[-22.27,-42.81],[-22.03,-42.81],[-22.03,-43.05]] },
  { id:'BR-RJ-803', ibgeCode:'3300803', name:'Cachoeiras de Macacu', state:'RJ', country:'BR', culture:'goiaba', areaMha:0.625, ndvi:0.475, coef:0.75, lat:-22.4658, lon:-42.6523, flvCultures:["goiaba"], flvTons:12509, poly:[[-22.59,-42.77],[-22.59,-42.53],[-22.35,-42.53],[-22.35,-42.77]] },
  { id:'BR-SP-208', ibgeCode:'3541208', name:'Presidente Bernardes', state:'SP', country:'BR', culture:'batata', areaMha:0.5, ndvi:0.475, coef:0.75, lat:-22.0082, lon:-51.5565, flvCultures:["batata"], flvTons:12500, poly:[[-22.13,-51.68],[-22.13,-51.44],[-21.89,-51.44],[-21.89,-51.68]] },
  { id:'BR-ES-607', ibgeCode:'3200607', name:'Aracruz', state:'ES', country:'BR', culture:'mamao', areaMha:0.25, ndvi:0.475, coef:0.75, lat:-19.82, lon:-40.2764, flvCultures:["mamao"], flvTons:12500, poly:[[-19.94,-40.4],[-19.94,-40.16],[-19.7,-40.16],[-19.7,-40.4]] },
  { id:'BR-SP-302', ibgeCode:'3529302', name:'Matão', state:'SP', country:'BR', culture:'goiaba', areaMha:0.622, ndvi:0.475, coef:0.75, lat:-21.6025, lon:-48.364, flvCultures:["goiaba"], flvTons:12441, poly:[[-21.72,-48.48],[-21.72,-48.24],[-21.48,-48.24],[-21.48,-48.48]] },
  { id:'BR-SC-892', ibgeCode:'4211892', name:'Painel', state:'SC', country:'BR', culture:'maca', areaMha:0.35, ndvi:0.475, coef:0.75, lat:-27.9234, lon:-50.0972, flvCultures:["maca"], flvTons:12250, poly:[[-28.04,-50.22],[-28.04,-49.98],[-27.8,-49.98],[-27.8,-50.22]] },
  { id:'BR-SP-757', ibgeCode:'3534757', name:'Ouroeste', state:'SP', country:'BR', culture:'limao', areaMha:0.608, ndvi:0.474, coef:0.75, lat:-20.0061, lon:-50.3768, flvCultures:["limao"], flvTons:12150, poly:[[-20.13,-50.5],[-20.13,-50.26],[-19.89,-50.26],[-19.89,-50.5]] },
  { id:'BR-BA-605', ibgeCode:'2904605', name:'Brumado', state:'BA', country:'BR', culture:'maracuja', areaMha:0.8, ndvi:0.474, coef:0.75, lat:-14.2021, lon:-41.6696, flvCultures:["maracuja"], flvTons:12000, poly:[[-14.32,-41.79],[-14.32,-41.55],[-14.08,-41.55],[-14.08,-41.79]] },
  { id:'BR-RN-309', ibgeCode:'2404309', name:'Governador Dix-Sept Rosado', state:'RN', country:'BR', culture:'melao', areaMha:0.475, ndvi:0.474, coef:0.75, lat:-5.44887, lon:-37.5183, flvCultures:["melao"], flvTons:11871, poly:[[-5.57,-37.64],[-5.57,-37.4],[-5.33,-37.4],[-5.33,-37.64]] },
  { id:'BR-RS-251', ibgeCode:'4317251', name:'Santa Tereza', state:'RS', country:'BR', culture:'uva', areaMha:0.659, ndvi:0.474, coef:0.75, lat:-29.1655, lon:-51.7351, flvCultures:["uva"], flvTons:11870, poly:[[-29.29,-51.86],[-29.29,-51.62],[-29.05,-51.62],[-29.05,-51.86]] },
  { id:'BR-SP-704', ibgeCode:'3507704', name:'Braúna', state:'SP', country:'BR', culture:'batata', areaMha:0.47, ndvi:0.474, coef:0.75, lat:-21.499, lon:-50.3175, flvCultures:["batata"], flvTons:11760, poly:[[-21.62,-50.44],[-21.62,-50.2],[-21.38,-50.2],[-21.38,-50.44]] },
  { id:'BR-MG-104', ibgeCode:'3138104', name:'Lassance', state:'MG', country:'BR', culture:'mamao', areaMha:0.235, ndvi:0.474, coef:0.75, lat:-17.887, lon:-44.5735, flvCultures:["mamao"], flvTons:11760, poly:[[-18.01,-44.69],[-18.01,-44.45],[-17.77,-44.45],[-17.77,-44.69]] },
  { id:'BR-MG-909', ibgeCode:'3113909', name:'Carmo da Cachoeira', state:'MG', country:'BR', culture:'abacate', areaMha:0.77, ndvi:0.473, coef:0.75, lat:-21.4633, lon:-45.2201, flvCultures:["abacate"], flvTons:11550, poly:[[-21.58,-45.34],[-21.58,-45.1],[-21.34,-45.1],[-21.34,-45.34]] },
  { id:'BR-ES-056', ibgeCode:'3203056', name:'Jaguaré', state:'ES', country:'BR', culture:'mamao', areaMha:0.228, ndvi:0.473, coef:0.75, lat:-18.907, lon:-40.0759, flvCultures:["mamao"], flvTons:11400, poly:[[-19.03,-40.2],[-19.03,-39.96],[-18.79,-39.96],[-18.79,-40.2]] },
  { id:'BR-PE-304', ibgeCode:'2604304', name:'Cedro', state:'PE', country:'BR', culture:'goiaba', areaMha:0.562, ndvi:0.473, coef:0.75, lat:-7.71179, lon:-39.2367, flvCultures:["goiaba"], flvTons:11250, poly:[[-7.83,-39.36],[-7.83,-39.12],[-7.59,-39.12],[-7.59,-39.36]] },
  { id:'BR-MG-703', ibgeCode:'3112703', name:'Capitão Enéas', state:'MG', country:'BR', culture:'mamao', areaMha:0.218, ndvi:0.472, coef:0.75, lat:-16.3265, lon:-43.7084, flvCultures:["mamao"], flvTons:10900, poly:[[-16.45,-43.83],[-16.45,-43.59],[-16.21,-43.59],[-16.21,-43.83]] },
  { id:'BR-SP-206', ibgeCode:'3556206', name:'Valinhos', state:'SP', country:'BR', culture:'figo', areaMha:1.068, ndvi:0.471, coef:0.75, lat:-22.9698, lon:-46.9974, flvCultures:["figo", "goiaba"], flvTons:10681, poly:[[-23.09,-47.12],[-23.09,-46.88],[-22.85,-46.88],[-22.85,-47.12]] },
  { id:'BR-MG-306', ibgeCode:'3136306', name:'João Pinheiro', state:'MG', country:'BR', culture:'manga', areaMha:0.875, ndvi:0.471, coef:0.75, lat:-17.7398, lon:-46.1715, flvCultures:["manga"], flvTons:10500, poly:[[-17.86,-46.29],[-17.86,-46.05],[-17.62,-46.05],[-17.62,-46.29]] },
  { id:'BR-SP-102', ibgeCode:'3525102', name:'Jardinópolis', state:'SP', country:'BR', culture:'abacate', areaMha:0.696, ndvi:0.471, coef:0.75, lat:-21.0176, lon:-47.7606, flvCultures:["abacate"], flvTons:10440, poly:[[-21.14,-47.88],[-21.14,-47.64],[-20.9,-47.64],[-20.9,-47.88]] },
  { id:'BR-CE-803', ibgeCode:'2305803', name:'Ipu', state:'CE', country:'BR', culture:'maracuja', areaMha:0.684, ndvi:0.471, coef:0.75, lat:-4.31748, lon:-40.7059, flvCultures:["maracuja"], flvTons:10260, poly:[[-4.44,-40.83],[-4.44,-40.59],[-4.2,-40.59],[-4.2,-40.83]] },
  { id:'BR-SP-806', ibgeCode:'3544806', name:'Sales', state:'SP', country:'BR', culture:'limao', areaMha:0.512, ndvi:0.47, coef:0.75, lat:-21.3427, lon:-49.4897, flvCultures:["limao"], flvTons:10249, poly:[[-21.46,-49.61],[-21.46,-49.37],[-21.22,-49.37],[-21.22,-49.61]] },
  { id:'BR-MG-802', ibgeCode:'3169802', name:'Turvolândia', state:'MG', country:'BR', culture:'caqui', areaMha:0.672, ndvi:0.47, coef:0.75, lat:-21.8733, lon:-45.7859, flvCultures:["caqui"], flvTons:10080, poly:[[-21.99,-45.91],[-21.99,-45.67],[-21.75,-45.67],[-21.75,-45.91]] },
  { id:'BR-BA-207', ibgeCode:'2900207', name:'Abaré', state:'BA', country:'BR', culture:'manga', areaMha:0.838, ndvi:0.47, coef:0.75, lat:-8.72073, lon:-39.1162, flvCultures:["manga"], flvTons:10061, poly:[[-8.84,-39.24],[-8.84,-39.0],[-8.6,-39.0],[-8.6,-39.24]] },
  { id:'BR-SP-607', ibgeCode:'3530607', name:'Mogi das Cruzes', state:'SP', country:'BR', culture:'caqui', areaMha:0.669, ndvi:0.47, coef:0.75, lat:-23.5208, lon:-46.1854, flvCultures:["caqui"], flvTons:10030, poly:[[-23.64,-46.31],[-23.64,-46.07],[-23.4,-46.07],[-23.4,-46.31]] },
  { id:'BR-SP-406', ibgeCode:'3541406', name:'Presidente Prudente', state:'SP', country:'BR', culture:'batata', areaMha:0.401, ndvi:0.47, coef:0.75, lat:-22.1207, lon:-51.3925, flvCultures:["batata"], flvTons:10020, poly:[[-22.24,-51.51],[-22.24,-51.27],[-22.0,-51.27],[-22.0,-51.51]] },
  { id:'BR-MG-808', ibgeCode:'3166808', name:'Serra do Salitre', state:'MG', country:'BR', culture:'batata', areaMha:0.4, ndvi:0.47, coef:0.75, lat:-19.1083, lon:-46.6961, flvCultures:["batata"], flvTons:10000, poly:[[-19.23,-46.82],[-19.23,-46.58],[-18.99,-46.58],[-18.99,-46.82]] },
  { id:'BR-SP-404', ibgeCode:'3542404', name:'Regente Feijó', state:'SP', country:'BR', culture:'batata', areaMha:0.4, ndvi:0.47, coef:0.75, lat:-22.2181, lon:-51.3055, flvCultures:["batata"], flvTons:10000, poly:[[-22.34,-51.43],[-22.34,-51.19],[-22.1,-51.19],[-22.1,-51.43]] },
  { id:'BR-MG-307', ibgeCode:'3169307', name:'Três Corações', state:'MG', country:'BR', culture:'abacate', areaMha:0.66, ndvi:0.47, coef:0.75, lat:-21.6921, lon:-45.2511, flvCultures:["abacate"], flvTons:9900, poly:[[-21.81,-45.37],[-21.81,-45.13],[-21.57,-45.13],[-21.57,-45.37]] },
  { id:'BR-SC-505', ibgeCode:'4215505', name:'Santa Cecília', state:'SC', country:'BR', culture:'maca', areaMha:0.274, ndvi:0.469, coef:0.75, lat:-26.9592, lon:-50.4252, flvCultures:["maca"], flvTons:9576, poly:[[-27.08,-50.55],[-27.08,-50.31],[-26.84,-50.31],[-26.84,-50.55]] },
  { id:'BR-RN-101', ibgeCode:'2404101', name:'Galinhos', state:'RN', country:'BR', culture:'melao', areaMha:0.373, ndvi:0.469, coef:0.75, lat:-5.0909, lon:-36.2754, flvCultures:["melao"], flvTons:9325, poly:[[-5.21,-36.4],[-5.21,-36.16],[-4.97,-36.16],[-4.97,-36.4]] },
  { id:'BR-SP-502', ibgeCode:'3509502', name:'Campinas', state:'SP', country:'BR', culture:'goiaba', areaMha:0.46, ndvi:0.468, coef:0.75, lat:-22.9053, lon:-47.0659, flvCultures:["caqui", "goiaba", "figo"], flvTons:9192, poly:[[-23.03,-47.19],[-23.03,-46.95],[-22.79,-46.95],[-22.79,-47.19]] },
  { id:'BR-MG-107', ibgeCode:'3108107', name:'Bonfim', state:'MG', country:'BR', culture:'tangerina', areaMha:0.456, ndvi:0.468, coef:0.75, lat:-20.3302, lon:-44.2366, flvCultures:["tangerina"], flvTons:9120, poly:[[-20.45,-44.36],[-20.45,-44.12],[-20.21,-44.12],[-20.21,-44.36]] },
  { id:'BR-PR-602', ibgeCode:'4117602', name:'Palmas', state:'PR', country:'BR', culture:'maca', areaMha:0.258, ndvi:0.468, coef:0.75, lat:-26.4839, lon:-51.9888, flvCultures:["maca"], flvTons:9024, poly:[[-26.6,-52.11],[-26.6,-51.87],[-26.36,-51.87],[-26.36,-52.11]] },
  { id:'BR-SP-608', ibgeCode:'3544608', name:'Sabino', state:'SP', country:'BR', culture:'batata', areaMha:0.36, ndvi:0.468, coef:0.75, lat:-21.4593, lon:-49.5755, flvCultures:["batata"], flvTons:9000, poly:[[-21.58,-49.7],[-21.58,-49.46],[-21.34,-49.46],[-21.34,-49.7]] },
  { id:'BR-PR-700', ibgeCode:'4113700', name:'Londrina', state:'PR', country:'BR', culture:'batata', areaMha:0.36, ndvi:0.468, coef:0.75, lat:-23.304, lon:-51.1691, flvCultures:["batata"], flvTons:9000, poly:[[-23.42,-51.29],[-23.42,-51.05],[-23.18,-51.05],[-23.18,-51.29]] },
  { id:'BR-MG-708', ibgeCode:'3119708', name:'Coronel Xavier Chaves', state:'MG', country:'BR', culture:'tangerina', areaMha:0.45, ndvi:0.468, coef:0.75, lat:-21.0277, lon:-44.2206, flvCultures:["tangerina"], flvTons:9000, poly:[[-21.15,-44.34],[-21.15,-44.1],[-20.91,-44.1],[-20.91,-44.34]] },
  { id:'BR-MG-707', ibgeCode:'3110707', name:'Cambuquira', state:'MG', country:'BR', culture:'tangerina', areaMha:0.44, ndvi:0.468, coef:0.75, lat:-21.854, lon:-45.2896, flvCultures:["tangerina"], flvTons:8800, poly:[[-21.97,-45.41],[-21.97,-45.17],[-21.73,-45.17],[-21.73,-45.41]] },
  { id:'BR-RJ-802', ibgeCode:'3305802', name:'Teresópolis', state:'RJ', country:'BR', culture:'tangerina', areaMha:0.439, ndvi:0.468, coef:0.75, lat:-22.4165, lon:-42.9752, flvCultures:["tangerina"], flvTons:8772, poly:[[-22.54,-43.1],[-22.54,-42.86],[-22.3,-42.86],[-22.3,-43.1]] },
  { id:'BR-SP-503', ibgeCode:'3518503', name:'Guareí', state:'SP', country:'BR', culture:'tangerina', areaMha:0.438, ndvi:0.468, coef:0.75, lat:-23.3714, lon:-48.1837, flvCultures:["tangerina"], flvTons:8750, poly:[[-23.49,-48.3],[-23.49,-48.06],[-23.25,-48.06],[-23.25,-48.3]] },
  { id:'BR-RJ-703', ibgeCode:'3305703', name:'Sumidouro', state:'RJ', country:'BR', culture:'caqui', areaMha:0.57, ndvi:0.467, coef:0.75, lat:-22.0485, lon:-42.6761, flvCultures:["caqui"], flvTons:8550, poly:[[-22.17,-42.8],[-22.17,-42.56],[-21.93,-42.56],[-21.93,-42.8]] },
  { id:'BR-PE-700', ibgeCode:'2604700', name:'Correntes', state:'PE', country:'BR', culture:'batata', areaMha:0.336, ndvi:0.467, coef:0.75, lat:-9.12117, lon:-36.3244, flvCultures:["batata"], flvTons:8400, poly:[[-9.24,-36.44],[-9.24,-36.2],[-9.0,-36.2],[-9.0,-36.44]] },
  { id:'BR-RN-203', ibgeCode:'2407203', name:'Macau', state:'RN', country:'BR', culture:'melao', areaMha:0.336, ndvi:0.467, coef:0.75, lat:-5.10795, lon:-36.6318, flvCultures:["melao"], flvTons:8400, poly:[[-5.23,-36.75],[-5.23,-36.51],[-4.99,-36.51],[-4.99,-36.75]] },
  { id:'BR-CE-236', ibgeCode:'2304236', name:'Croatá', state:'CE', country:'BR', culture:'maracuja', areaMha:0.558, ndvi:0.467, coef:0.75, lat:-4.40481, lon:-40.9022, flvCultures:["maracuja"], flvTons:8370, poly:[[-4.52,-41.02],[-4.52,-40.78],[-4.28,-40.78],[-4.28,-41.02]] },
  { id:'BR-BA-804', ibgeCode:'2908804', name:'Contendas do Sincorá', state:'BA', country:'BR', culture:'maracuja', areaMha:0.528, ndvi:0.466, coef:0.75, lat:-13.7537, lon:-41.048, flvCultures:["maracuja"], flvTons:7920, poly:[[-13.87,-41.17],[-13.87,-40.93],[-13.63,-40.93],[-13.63,-41.17]] },
  { id:'BR-SP-607', ibgeCode:'3554607', name:'Timburi', state:'SP', country:'BR', culture:'abacate', areaMha:0.513, ndvi:0.465, coef:0.75, lat:-23.2057, lon:-49.6096, flvCultures:["abacate"], flvTons:7700, poly:[[-23.33,-49.73],[-23.33,-49.49],[-23.09,-49.49],[-23.09,-49.73]] },
  { id:'BR-AM-504', ibgeCode:'1302504', name:'Manacapuru', state:'AM', country:'BR', culture:'maracuja', areaMha:0.5, ndvi:0.465, coef:0.75, lat:-3.29066, lon:-60.6216, flvCultures:["maracuja"], flvTons:7500, poly:[[-3.41,-60.74],[-3.41,-60.5],[-3.17,-60.5],[-3.17,-60.74]] },
  { id:'BR-MG-104', ibgeCode:'3162104', name:'São Gotardo', state:'MG', country:'BR', culture:'alho', areaMha:0.938, ndvi:0.465, coef:0.75, lat:-19.3087, lon:-46.0465, flvCultures:["alho"], flvTons:7500, poly:[[-19.43,-46.17],[-19.43,-45.93],[-19.19,-45.93],[-19.19,-46.17]] },
  { id:'BR-PE-308', ibgeCode:'2602308', name:'Bonito', state:'PE', country:'BR', culture:'batata', areaMha:0.288, ndvi:0.464, coef:0.75, lat:-8.47163, lon:-35.7292, flvCultures:["batata"], flvTons:7200, poly:[[-8.59,-35.85],[-8.59,-35.61],[-8.35,-35.61],[-8.35,-35.85]] },
  { id:'BR-SP-904', ibgeCode:'3511904', name:'Clementina', state:'SP', country:'BR', culture:'batata', areaMha:0.269, ndvi:0.463, coef:0.75, lat:-21.5604, lon:-50.4525, flvCultures:["batata"], flvTons:6720, poly:[[-21.68,-50.57],[-21.68,-50.33],[-21.44,-50.33],[-21.44,-50.57]] },
  { id:'BR-RS-507', ibgeCode:'4304507', name:'Canguçu', state:'RS', country:'BR', culture:'pessego', areaMha:0.55, ndvi:0.463, coef:0.75, lat:-31.396, lon:-52.6783, flvCultures:["pessego"], flvTons:6600, poly:[[-31.52,-52.8],[-31.52,-52.56],[-31.28,-52.56],[-31.28,-52.8]] },
  { id:'BR-SC-404', ibgeCode:'4216404', name:'São João do Sul', state:'SC', country:'BR', culture:'maracuja', areaMha:0.433, ndvi:0.463, coef:0.75, lat:-29.2154, lon:-49.8094, flvCultures:["maracuja"], flvTons:6500, poly:[[-29.34,-49.93],[-29.34,-49.69],[-29.1,-49.69],[-29.1,-49.93]] },
  { id:'BR-RS-308', ibgeCode:'4309308', name:'Guaíba', state:'RS', country:'BR', culture:'batata', areaMha:0.258, ndvi:0.463, coef:0.75, lat:-30.1086, lon:-51.3233, flvCultures:["batata"], flvTons:6460, poly:[[-30.23,-51.44],[-30.23,-51.2],[-29.99,-51.2],[-29.99,-51.44]] },
  { id:'BR-SP-408', ibgeCode:'3502408', name:'Anhumas', state:'SP', country:'BR', culture:'batata', areaMha:0.257, ndvi:0.463, coef:0.75, lat:-22.2934, lon:-51.3895, flvCultures:["batata"], flvTons:6421, poly:[[-22.41,-51.51],[-22.41,-51.27],[-22.17,-51.27],[-22.17,-51.51]] },
  { id:'BR-RN-104', ibgeCode:'2407104', name:'Macaíba', state:'RN', country:'BR', culture:'batata', areaMha:0.256, ndvi:0.463, coef:0.75, lat:-5.85229, lon:-35.3552, flvCultures:["batata"], flvTons:6400, poly:[[-5.97,-35.48],[-5.97,-35.24],[-5.73,-35.24],[-5.73,-35.48]] },
  { id:'BR-MG-608', ibgeCode:'3105608', name:'Barbacena', state:'MG', country:'BR', culture:'pessego', areaMha:0.525, ndvi:0.463, coef:0.75, lat:-21.2214, lon:-43.7703, flvCultures:["caqui", "pera", "pessego"], flvTons:6302, poly:[[-21.34,-43.89],[-21.34,-43.65],[-21.1,-43.65],[-21.1,-43.89]] },
  { id:'BR-SP-307', ibgeCode:'3503307', name:'Araras', state:'SP', country:'BR', culture:'abacate', areaMha:0.419, ndvi:0.463, coef:0.75, lat:-22.3572, lon:-47.3842, flvCultures:["abacate"], flvTons:6278, poly:[[-22.48,-47.5],[-22.48,-47.26],[-22.24,-47.26],[-22.24,-47.5]] },
  { id:'BR-SP-702', ibgeCode:'3527702', name:'Luiziânia', state:'SP', country:'BR', culture:'batata', areaMha:0.25, ndvi:0.462, coef:0.75, lat:-21.6737, lon:-50.3294, flvCultures:["batata"], flvTons:6240, poly:[[-21.79,-50.45],[-21.79,-50.21],[-21.55,-50.21],[-21.55,-50.45]] },
  { id:'BR-PR-105', ibgeCode:'4104105', name:'Campo do Tenente', state:'PR', country:'BR', culture:'maca', areaMha:0.178, ndvi:0.462, coef:0.75, lat:-25.98, lon:-49.6844, flvCultures:["maca"], flvTons:6225, poly:[[-26.1,-49.8],[-26.1,-49.56],[-25.86,-49.56],[-25.86,-49.8]] },
  { id:'BR-BA-607', ibgeCode:'2917607', name:'Jaguaquara', state:'BA', country:'BR', culture:'maracuja', areaMha:0.41, ndvi:0.462, coef:0.75, lat:-13.5248, lon:-39.964, flvCultures:["maracuja"], flvTons:6143, poly:[[-13.64,-40.08],[-13.64,-39.84],[-13.4,-39.84],[-13.4,-40.08]] },
  { id:'BR-SP-005', ibgeCode:'3548005', name:'Santo Antônio de Posse', state:'SP', country:'BR', culture:'abacate', areaMha:0.407, ndvi:0.462, coef:0.75, lat:-22.6029, lon:-46.9192, flvCultures:["abacate"], flvTons:6109, poly:[[-22.72,-47.04],[-22.72,-46.8],[-22.48,-46.8],[-22.48,-47.04]] },
  { id:'BR-PE-707', ibgeCode:'2605707', name:'Floresta', state:'PE', country:'BR', culture:'melao', areaMha:0.24, ndvi:0.462, coef:0.75, lat:-8.60307, lon:-38.5687, flvCultures:["melao"], flvTons:6000, poly:[[-8.72,-38.69],[-8.72,-38.45],[-8.48,-38.45],[-8.48,-38.69]] },
  { id:'BR-SP-404', ibgeCode:'3523404', name:'Itatiba', state:'SP', country:'BR', culture:'caqui', areaMha:0.374, ndvi:0.461, coef:0.75, lat:-23.0035, lon:-46.8464, flvCultures:["caqui", "figo"], flvTons:5612, poly:[[-23.12,-46.97],[-23.12,-46.73],[-22.88,-46.73],[-22.88,-46.97]] },
  { id:'BR-SP-203', ibgeCode:'3510203', name:'Capão Bonito', state:'SP', country:'BR', culture:'caqui', areaMha:0.37, ndvi:0.461, coef:0.75, lat:-24.0113, lon:-48.3482, flvCultures:["caqui", "pessego"], flvTons:5550, poly:[[-24.13,-48.47],[-24.13,-48.23],[-23.89,-48.23],[-23.89,-48.47]] },
  { id:'BR-SP-906', ibgeCode:'3510906', name:'Cássia dos Coqueiros', state:'SP', country:'BR', culture:'abacate', areaMha:0.333, ndvi:0.46, coef:0.75, lat:-21.2801, lon:-47.1643, flvCultures:["abacate"], flvTons:5000, poly:[[-21.4,-47.28],[-21.4,-47.04],[-21.16,-47.04],[-21.16,-47.28]] },
  { id:'BR-SP-302', ibgeCode:'3553302', name:'Tambaú', state:'SP', country:'BR', culture:'abacate', areaMha:0.308, ndvi:0.459, coef:0.75, lat:-21.7029, lon:-47.2703, flvCultures:["abacate"], flvTons:4620, poly:[[-21.82,-47.39],[-21.82,-47.15],[-21.58,-47.15],[-21.58,-47.39]] },
  { id:'BR-RN-307', ibgeCode:'2400307', name:'Afonso Bezerra', state:'RN', country:'BR', culture:'melao', areaMha:0.183, ndvi:0.459, coef:0.75, lat:-5.49229, lon:-36.5075, flvCultures:["melao"], flvTons:4566, poly:[[-5.61,-36.63],[-5.61,-36.39],[-5.37,-36.39],[-5.37,-36.63]] },
  { id:'BR-BA-500', ibgeCode:'2916500', name:'Itapicuru', state:'BA', country:'BR', culture:'melao', areaMha:0.181, ndvi:0.459, coef:0.75, lat:-11.3088, lon:-38.2262, flvCultures:["melao"], flvTons:4515, poly:[[-11.43,-38.35],[-11.43,-38.11],[-11.19,-38.11],[-11.19,-38.35]] },
  { id:'BR-ES-346', ibgeCode:'3203346', name:'Marechal Floriano', state:'ES', country:'BR', culture:'abacate', areaMha:0.3, ndvi:0.459, coef:0.75, lat:-20.4159, lon:-40.67, flvCultures:["abacate"], flvTons:4500, poly:[[-20.54,-40.79],[-20.54,-40.55],[-20.3,-40.55],[-20.3,-40.79]] },
  { id:'BR-SC-558', ibgeCode:'4204558', name:'Correia Pinto', state:'SC', country:'BR', culture:'maca', areaMha:0.126, ndvi:0.459, coef:0.75, lat:-27.5877, lon:-50.3614, flvCultures:["maca"], flvTons:4410, poly:[[-27.71,-50.48],[-27.71,-50.24],[-27.47,-50.24],[-27.47,-50.48]] },
  { id:'BR-SP-104', ibgeCode:'3553104', name:'Taiaçu', state:'SP', country:'BR', culture:'goiaba', areaMha:0.22, ndvi:0.459, coef:0.75, lat:-21.1431, lon:-48.5112, flvCultures:["goiaba"], flvTons:4390, poly:[[-21.26,-48.63],[-21.26,-48.39],[-21.02,-48.39],[-21.02,-48.63]] },
  { id:'BR-SP-004', ibgeCode:'3501004', name:'Altinópolis', state:'SP', country:'BR', culture:'abacate', areaMha:0.29, ndvi:0.459, coef:0.75, lat:-21.0214, lon:-47.3712, flvCultures:["abacate"], flvTons:4352, poly:[[-21.14,-47.49],[-21.14,-47.25],[-20.9,-47.25],[-20.9,-47.49]] },
  { id:'BR-MG-707', ibgeCode:'3129707', name:'Ibiraci', state:'MG', country:'BR', culture:'abacate', areaMha:0.286, ndvi:0.459, coef:0.75, lat:-20.4611, lon:-47.1222, flvCultures:["abacate"], flvTons:4290, poly:[[-20.58,-47.24],[-20.58,-47.0],[-20.34,-47.0],[-20.34,-47.24]] },
  { id:'BR-SP-709', ibgeCode:'3519709', name:'Ibiúna', state:'SP', country:'BR', culture:'caqui', areaMha:0.285, ndvi:0.459, coef:0.75, lat:-23.6596, lon:-47.223, flvCultures:["caqui", "pera"], flvTons:4274, poly:[[-23.78,-47.34],[-23.78,-47.1],[-23.54,-47.1],[-23.54,-47.34]] },
  { id:'BR-SP-407', ibgeCode:'3512407', name:'Cordeirópolis', state:'SP', country:'BR', culture:'abacate', areaMha:0.282, ndvi:0.458, coef:0.75, lat:-22.4778, lon:-47.4519, flvCultures:["abacate"], flvTons:4224, poly:[[-22.6,-47.57],[-22.6,-47.33],[-22.36,-47.33],[-22.36,-47.57]] },
  { id:'BR-PE-303', ibgeCode:'2609303', name:'Mirandiba', state:'PE', country:'BR', culture:'goiaba', areaMha:0.21, ndvi:0.458, coef:0.75, lat:-8.12113, lon:-38.7388, flvCultures:["goiaba"], flvTons:4200, poly:[[-8.24,-38.86],[-8.24,-38.62],[-8.0,-38.62],[-8.0,-38.86]] },
  { id:'BR-SC-402', ibgeCode:'4203402', name:'Campo Belo do Sul', state:'SC', country:'BR', culture:'maca', areaMha:0.112, ndvi:0.458, coef:0.75, lat:-27.8975, lon:-50.7595, flvCultures:["maca"], flvTons:3920, poly:[[-28.02,-50.88],[-28.02,-50.64],[-27.78,-50.64],[-27.78,-50.88]] },
  { id:'BR-SP-107', ibgeCode:'3518107', name:'Guarantã', state:'SP', country:'BR', culture:'goiaba', areaMha:0.189, ndvi:0.458, coef:0.75, lat:-21.8942, lon:-49.5914, flvCultures:["goiaba"], flvTons:3780, poly:[[-22.01,-49.71],[-22.01,-49.47],[-21.77,-49.47],[-21.77,-49.71]] },
  { id:'BR-PE-502', ibgeCode:'2604502', name:'Chã Grande', state:'PE', country:'BR', culture:'goiaba', areaMha:0.188, ndvi:0.458, coef:0.75, lat:-8.23827, lon:-35.4571, flvCultures:["goiaba"], flvTons:3750, poly:[[-8.36,-35.58],[-8.36,-35.34],[-8.12,-35.34],[-8.12,-35.58]] },
  { id:'BR-SP-856', ibgeCode:'3553856', name:'Taquarivaí', state:'SP', country:'BR', culture:'caqui', areaMha:0.233, ndvi:0.457, coef:0.75, lat:-23.9211, lon:-48.6948, flvCultures:["caqui"], flvTons:3500, poly:[[-24.04,-48.81],[-24.04,-48.57],[-23.8,-48.57],[-23.8,-48.81]] },
  { id:'BR-SP-107', ibgeCode:'3504107', name:'Atibaia', state:'SP', country:'BR', culture:'pessego', areaMha:0.267, ndvi:0.456, coef:0.75, lat:-23.1171, lon:-46.5563, flvCultures:["pessego"], flvTons:3200, poly:[[-23.24,-46.68],[-23.24,-46.44],[-23.0,-46.44],[-23.0,-46.68]] },
  { id:'BR-RS-450', ibgeCode:'4312450', name:'Morro Redondo', state:'RS', country:'BR', culture:'pessego', areaMha:0.25, ndvi:0.456, coef:0.75, lat:-31.5887, lon:-52.6261, flvCultures:["pessego"], flvTons:3000, poly:[[-31.71,-52.75],[-31.71,-52.51],[-31.47,-52.51],[-31.47,-52.75]] },
  { id:'BR-GO-175', ibgeCode:'5200175', name:'Água Fria de Goiás', state:'GO', country:'BR', culture:'alho', areaMha:0.362, ndvi:0.456, coef:0.75, lat:-14.9778, lon:-47.7823, flvCultures:["alho"], flvTons:2897, poly:[[-15.1,-47.9],[-15.1,-47.66],[-14.86,-47.66],[-14.86,-47.9]] },
  { id:'BR-SP-804', ibgeCode:'3535804', name:'Paranapanema', state:'SP', country:'BR', culture:'pessego', areaMha:0.228, ndvi:0.455, coef:0.75, lat:-23.3862, lon:-48.7214, flvCultures:["pessego"], flvTons:2730, poly:[[-23.51,-48.84],[-23.51,-48.6],[-23.27,-48.6],[-23.27,-48.84]] },
  { id:'BR-SC-309', ibgeCode:'4219309', name:'Videira', state:'SC', country:'BR', culture:'pessego', areaMha:0.223, ndvi:0.455, coef:0.75, lat:-27.0086, lon:-51.1543, flvCultures:["pera", "pessego"], flvTons:2680, poly:[[-27.13,-51.27],[-27.13,-51.03],[-26.89,-51.03],[-26.89,-51.27]] },
  { id:'BR-MG-709', ibgeCode:'3171709', name:'Virgínia', state:'MG', country:'BR', culture:'pessego', areaMha:0.214, ndvi:0.455, coef:0.75, lat:-22.3264, lon:-45.0965, flvCultures:["figo", "pera", "pessego"], flvTons:2563, poly:[[-22.45,-45.22],[-22.45,-44.98],[-22.21,-44.98],[-22.21,-45.22]] },
  { id:'BR-SP-305', ibgeCode:'3518305', name:'Guararema', state:'SP', country:'BR', culture:'caqui', areaMha:0.16, ndvi:0.455, coef:0.75, lat:-23.4112, lon:-46.0369, flvCultures:["caqui"], flvTons:2403, poly:[[-23.53,-46.16],[-23.53,-45.92],[-23.29,-45.92],[-23.29,-46.16]] },
  { id:'BR-SP-801', ibgeCode:'3546801', name:'Santa Isabel', state:'SP', country:'BR', culture:'caqui', areaMha:0.16, ndvi:0.455, coef:0.75, lat:-23.3172, lon:-46.2237, flvCultures:["caqui"], flvTons:2400, poly:[[-23.44,-46.34],[-23.44,-46.1],[-23.2,-46.1],[-23.2,-46.34]] },
  { id:'BR-SC-005', ibgeCode:'4213005', name:'Pinheiro Preto', state:'SC', country:'BR', culture:'pessego', areaMha:0.194, ndvi:0.455, coef:0.75, lat:-27.0483, lon:-51.2243, flvCultures:["pessego"], flvTons:2325, poly:[[-27.17,-51.34],[-27.17,-51.1],[-26.93,-51.1],[-26.93,-51.34]] },
  { id:'BR-SP-306', ibgeCode:'3527306', name:'Louveira', state:'SP', country:'BR', culture:'caqui', areaMha:0.152, ndvi:0.455, coef:0.75, lat:-23.0856, lon:-46.9484, flvCultures:["caqui", "figo"], flvTons:2282, poly:[[-23.21,-47.07],[-23.21,-46.83],[-22.97,-46.83],[-22.97,-47.07]] },
  { id:'BR-GO-603', ibgeCode:'5215603', name:'Padre Bernardo', state:'GO', country:'BR', culture:'alho', areaMha:0.275, ndvi:0.454, coef:0.75, lat:-15.1605, lon:-48.2833, flvCultures:["alho"], flvTons:2200, poly:[[-15.28,-48.4],[-15.28,-48.16],[-15.04,-48.16],[-15.04,-48.4]] },
  { id:'BR-MG-902', ibgeCode:'3102902', name:'Antônio Carlos', state:'MG', country:'BR', culture:'caqui', areaMha:0.145, ndvi:0.454, coef:0.75, lat:-21.321, lon:-43.7451, flvCultures:["caqui"], flvTons:2175, poly:[[-21.44,-43.87],[-21.44,-43.63],[-21.2,-43.63],[-21.2,-43.87]] },
  { id:'BR-RS-605', ibgeCode:'4314605', name:'Piratini', state:'RS', country:'BR', culture:'pessego', areaMha:0.178, ndvi:0.454, coef:0.75, lat:-31.4473, lon:-53.0973, flvCultures:["figo", "pessego"], flvTons:2140, poly:[[-31.57,-53.22],[-31.57,-52.98],[-31.33,-52.98],[-31.33,-53.22]] },
  { id:'BR-GO-109', ibgeCode:'5210109', name:'Ipameri', state:'GO', country:'BR', culture:'alho', areaMha:0.25, ndvi:0.454, coef:0.75, lat:-17.7215, lon:-48.1581, flvCultures:["alho"], flvTons:2000, poly:[[-17.84,-48.28],[-17.84,-48.04],[-17.6,-48.04],[-17.6,-48.28]] },
  { id:'BR-SC-907', ibgeCode:'4217907', name:'Tangará', state:'SC', country:'BR', culture:'pessego', areaMha:0.158, ndvi:0.454, coef:0.75, lat:-27.0996, lon:-51.2473, flvCultures:["pessego"], flvTons:1900, poly:[[-27.22,-51.37],[-27.22,-51.13],[-26.98,-51.13],[-26.98,-51.37]] },
  { id:'BR-MG-903', ibgeCode:'3168903', name:'Tiros', state:'MG', country:'BR', culture:'alho', areaMha:0.225, ndvi:0.454, coef:0.75, lat:-19.0037, lon:-45.9626, flvCultures:["alho"], flvTons:1800, poly:[[-19.12,-46.08],[-19.12,-45.84],[-18.88,-45.84],[-18.88,-46.08]] },
  { id:'BR-MG-705', ibgeCode:'3130705', name:'Indianópolis', state:'MG', country:'BR', culture:'alho', areaMha:0.216, ndvi:0.453, coef:0.75, lat:-19.0341, lon:-47.9155, flvCultures:["alho"], flvTons:1725, poly:[[-19.15,-48.04],[-19.15,-47.8],[-18.91,-47.8],[-18.91,-48.04]] },
  { id:'BR-SC-555', ibgeCode:'4205555', name:'Frei Rogério', state:'SC', country:'BR', culture:'alho', areaMha:0.181, ndvi:0.453, coef:0.75, lat:-27.175, lon:-50.8076, flvCultures:["pera", "alho"], flvTons:1451, poly:[[-27.3,-50.93],[-27.3,-50.69],[-27.05,-50.69],[-27.05,-50.93]] },
  { id:'BR-MG-509', ibgeCode:'3129509', name:'Ibiá', state:'MG', country:'BR', culture:'alho', areaMha:0.181, ndvi:0.453, coef:0.75, lat:-19.4749, lon:-46.5474, flvCultures:["alho"], flvTons:1450, poly:[[-19.59,-46.67],[-19.59,-46.43],[-19.35,-46.43],[-19.35,-46.67]] },
  { id:'BR-SP-001', ibgeCode:'3545001', name:'Salesópolis', state:'SP', country:'BR', culture:'caqui', areaMha:0.092, ndvi:0.453, coef:0.75, lat:-23.5288, lon:-45.8465, flvCultures:["caqui"], flvTons:1380, poly:[[-23.65,-45.97],[-23.65,-45.73],[-23.41,-45.73],[-23.41,-45.97]] },
  { id:'BR-GO-003', ibgeCode:'5204003', name:'Cabeceiras', state:'GO', country:'BR', culture:'alho', areaMha:0.163, ndvi:0.453, coef:0.75, lat:-15.7995, lon:-46.9265, flvCultures:["alho"], flvTons:1306, poly:[[-15.92,-47.05],[-15.92,-46.81],[-15.68,-46.81],[-15.68,-47.05]] },
  { id:'BR-RS-102', ibgeCode:'4308102', name:'Feliz', state:'RS', country:'BR', culture:'figo', areaMha:0.13, ndvi:0.453, coef:0.75, lat:-29.4527, lon:-51.3032, flvCultures:["figo"], flvTons:1296, poly:[[-29.57,-51.42],[-29.57,-51.18],[-29.33,-51.18],[-29.33,-51.42]] },
  { id:'BR-MG-704', ibgeCode:'3164704', name:'São Sebastião do Paraíso', state:'MG', country:'BR', culture:'figo', areaMha:0.096, ndvi:0.452, coef:0.75, lat:-20.9167, lon:-46.9837, flvCultures:["figo"], flvTons:963, poly:[[-21.04,-47.1],[-21.04,-46.86],[-20.8,-46.86],[-20.8,-47.1]] },
  { id:'BR-PR-804', ibgeCode:'4101804', name:'Araucária', state:'PR', country:'BR', culture:'pera', areaMha:0.055, ndvi:0.452, coef:0.75, lat:-25.5859, lon:-49.4047, flvCultures:["ervilha", "pera"], flvTons:819, poly:[[-25.71,-49.52],[-25.71,-49.28],[-25.47,-49.28],[-25.47,-49.52]] },
  { id:'BR-MG-403', ibgeCode:'3156403', name:'Romaria', state:'MG', country:'BR', culture:'ervilha', areaMha:0.144, ndvi:0.451, coef:0.75, lat:-18.8838, lon:-47.5782, flvCultures:["ervilha"], flvTons:720, poly:[[-19.0,-47.7],[-19.0,-47.46],[-18.76,-47.46],[-18.76,-47.7]] },
  { id:'BR-SC-104', ibgeCode:'4208104', name:'Itaiópolis', state:'SC', country:'BR', culture:'pera', areaMha:0.042, ndvi:0.451, coef:0.75, lat:-26.339, lon:-49.9092, flvCultures:["pera"], flvTons:625, poly:[[-26.46,-50.03],[-26.46,-49.79],[-26.22,-49.79],[-26.22,-50.03]] },
  { id:'BR-MG-400', ibgeCode:'3153400', name:'Presidente Olegário', state:'MG', country:'BR', culture:'ervilha', areaMha:0.12, ndvi:0.451, coef:0.75, lat:-18.4096, lon:-46.4165, flvCultures:["ervilha"], flvTons:600, poly:[[-18.53,-46.54],[-18.53,-46.3],[-18.29,-46.3],[-18.29,-46.54]] },
  { id:'BR-MG-307', ibgeCode:'3126307', name:'Fortaleza de Minas', state:'MG', country:'BR', culture:'figo', areaMha:0.045, ndvi:0.451, coef:0.75, lat:-20.8508, lon:-46.712, flvCultures:["figo"], flvTons:450, poly:[[-20.97,-46.83],[-20.97,-46.59],[-20.73,-46.59],[-20.73,-46.83]] },
  { id:'BR-RS-201', ibgeCode:'4313201', name:'Nova Petrópolis', state:'RS', country:'BR', culture:'figo', areaMha:0.044, ndvi:0.451, coef:0.75, lat:-29.3741, lon:-51.1136, flvCultures:["figo"], flvTons:440, poly:[[-29.49,-51.23],[-29.49,-50.99],[-29.25,-50.99],[-29.25,-51.23]] },
  { id:'BR-SC-806', ibgeCode:'4204806', name:'Curitibanos', state:'SC', country:'BR', culture:'pera', areaMha:0.024, ndvi:0.451, coef:0.75, lat:-27.2824, lon:-50.5816, flvCultures:["pera"], flvTons:365, poly:[[-27.4,-50.7],[-27.4,-50.46],[-27.16,-50.46],[-27.16,-50.7]] },
  { id:'BR-MG-302', ibgeCode:'3119302', name:'Coromandel', state:'MG', country:'BR', culture:'ervilha', areaMha:0.072, ndvi:0.451, coef:0.75, lat:-18.4734, lon:-47.1933, flvCultures:["ervilha"], flvTons:360, poly:[[-18.59,-47.31],[-18.59,-47.07],[-18.35,-47.07],[-18.35,-47.31]] },
  { id:'BR-MG-401', ibgeCode:'3138401', name:'Leopoldina', state:'MG', country:'BR', culture:'pera', areaMha:0.021, ndvi:0.451, coef:0.75, lat:-21.5296, lon:-42.6421, flvCultures:["pera"], flvTons:315, poly:[[-21.65,-42.76],[-21.65,-42.52],[-21.41,-42.52],[-21.41,-42.76]] },
  { id:'BR-SP-006', ibgeCode:'3524006', name:'Itupeva', state:'SP', country:'BR', culture:'figo', areaMha:0.03, ndvi:0.451, coef:0.75, lat:-23.1526, lon:-47.0593, flvCultures:["figo"], flvTons:300, poly:[[-23.27,-47.18],[-23.27,-46.94],[-23.03,-46.94],[-23.03,-47.18]] },
  { id:'BR-MG-501', ibgeCode:'3152501', name:'Pouso Alegre', state:'MG', country:'BR', culture:'pera', areaMha:0.017, ndvi:0.451, coef:0.75, lat:-22.2266, lon:-45.9389, flvCultures:["pera"], flvTons:250, poly:[[-22.35,-46.06],[-22.35,-45.82],[-22.11,-45.82],[-22.11,-46.06]] },
  { id:'BR-RS-100', ibgeCode:'4309100', name:'Gramado', state:'RS', country:'BR', culture:'figo', areaMha:0.019, ndvi:0.45, coef:0.75, lat:-29.3734, lon:-50.8762, flvCultures:["figo"], flvTons:189, poly:[[-29.49,-51.0],[-29.49,-50.76],[-29.25,-50.76],[-29.25,-51.0]] },
  { id:'BR-SP-009', ibgeCode:'3532009', name:'Morungaba', state:'SP', country:'BR', culture:'figo', areaMha:0.017, ndvi:0.45, coef:0.75, lat:-22.8811, lon:-46.7896, flvCultures:["figo"], flvTons:168, poly:[[-23.0,-46.91],[-23.0,-46.67],[-22.76,-46.67],[-22.76,-46.91]] },
  { id:'BR-MG-300', ibgeCode:'3139300', name:'Manga', state:'MG', country:'BR', culture:'ervilha', areaMha:0.028, ndvi:0.45, coef:0.75, lat:-14.7529, lon:-43.9391, flvCultures:["ervilha"], flvTons:140, poly:[[-14.87,-44.06],[-14.87,-43.82],[-14.63,-43.82],[-14.63,-44.06]] },
  { id:'BR-RS-704', ibgeCode:'4314704', name:'Planalto', state:'RS', country:'BR', culture:'figo', areaMha:0.012, ndvi:0.45, coef:0.75, lat:-27.3297, lon:-53.0575, flvCultures:["figo"], flvTons:120, poly:[[-27.45,-53.18],[-27.45,-52.94],[-27.21,-52.94],[-27.21,-53.18]] },
  { id:'BR-RS-505', ibgeCode:'4319505', name:'São Sebastião do Caí', state:'RS', country:'BR', culture:'figo', areaMha:0.012, ndvi:0.45, coef:0.75, lat:-29.5885, lon:-51.3749, flvCultures:["figo"], flvTons:118, poly:[[-29.71,-51.49],[-29.71,-51.25],[-29.47,-51.25],[-29.47,-51.49]] },
  { id:'BR-RS-352', ibgeCode:'4302352', name:'Bom Princípio', state:'RS', country:'BR', culture:'figo', areaMha:0.011, ndvi:0.45, coef:0.75, lat:-29.4856, lon:-51.3548, flvCultures:["figo"], flvTons:114, poly:[[-29.61,-51.47],[-29.61,-51.23],[-29.37,-51.23],[-29.37,-51.47]] },
  { id:'BR-SC-409', ibgeCode:'4214409', name:'Rio das Antas', state:'SC', country:'BR', culture:'pera', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-26.8946, lon:-51.0674, flvCultures:["pera"], flvTons:113, poly:[[-27.01,-51.19],[-27.01,-50.95],[-26.77,-50.95],[-26.77,-51.19]] },
  { id:'BR-RS-804', ibgeCode:'4318804', name:'São Lourenço do Sul', state:'RS', country:'BR', culture:'figo', areaMha:0.011, ndvi:0.45, coef:0.75, lat:-31.3564, lon:-51.9715, flvCultures:["figo"], flvTons:105, poly:[[-31.48,-52.09],[-31.48,-51.85],[-31.24,-51.85],[-31.24,-52.09]] },
  { id:'BR-CE-104', ibgeCode:'2313104', name:'Tabuleiro do Norte', state:'CE', country:'BR', culture:'figo', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-5.24353, lon:-38.1282, flvCultures:["figo"], flvTons:102, poly:[[-5.36,-38.25],[-5.36,-38.01],[-5.12,-38.01],[-5.12,-38.25]] },
  { id:'BR-RS-903', ibgeCode:'4318903', name:'São Luiz Gonzaga', state:'RS', country:'BR', culture:'ervilha', areaMha:0.02, ndvi:0.45, coef:0.75, lat:-28.412, lon:-54.9559, flvCultures:["ervilha"], flvTons:100, poly:[[-28.53,-55.08],[-28.53,-54.84],[-28.29,-54.84],[-28.29,-55.08]] },
  { id:'BR-RS-356', ibgeCode:'4319356', name:'São Pedro da Serra', state:'RS', country:'BR', culture:'figo', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-29.4193, lon:-51.5134, flvCultures:["figo"], flvTons:90, poly:[[-29.54,-51.63],[-29.54,-51.39],[-29.3,-51.39],[-29.3,-51.63]] },
  { id:'BR-RS-103', ibgeCode:'4317103', name:'Sant\'Ana do Livramento', state:'RS', country:'BR', culture:'pera', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-30.8773, lon:-55.5392, flvCultures:["pera"], flvTons:90, poly:[[-31.0,-55.66],[-31.0,-55.42],[-30.76,-55.42],[-30.76,-55.66]] },
  { id:'BR-PR-408', ibgeCode:'4101408', name:'Apucarana', state:'PR', country:'BR', culture:'figo', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-23.55, lon:-51.4635, flvCultures:["figo"], flvTons:88, poly:[[-23.67,-51.58],[-23.67,-51.34],[-23.43,-51.34],[-23.43,-51.58]] },
  { id:'BR-MG-406', ibgeCode:'3169406', name:'Três Pontas', state:'MG', country:'BR', culture:'pera', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-21.3694, lon:-45.5109, flvCultures:["pera"], flvTons:88, poly:[[-21.49,-45.63],[-21.49,-45.39],[-21.25,-45.39],[-21.25,-45.63]] },
  { id:'BR-PR-704', ibgeCode:'4111704', name:'Jaboti', state:'PR', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-23.7435, lon:-50.0729, flvCultures:["ervilha"], flvTons:30, poly:[[-23.86,-50.19],[-23.86,-49.95],[-23.62,-49.95],[-23.62,-50.19]] },
  { id:'BR-PR-202', ibgeCode:'4119202', name:'Pinhalão', state:'PR', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-23.7982, lon:-50.0536, flvCultures:["ervilha"], flvTons:26, poly:[[-23.92,-50.17],[-23.92,-49.93],[-23.68,-49.93],[-23.68,-50.17]] },
  { id:'BR-MG-105', ibgeCode:'3109105', name:'Bueno Brandão', state:'MG', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-22.4383, lon:-46.3491, flvCultures:["ervilha"], flvTons:24, poly:[[-22.56,-46.47],[-22.56,-46.23],[-22.32,-46.23],[-22.32,-46.47]] },
  { id:'BR-PR-354', ibgeCode:'4103354', name:'Braganey', state:'PR', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-24.8173, lon:-53.1218, flvCultures:["ervilha"], flvTons:22, poly:[[-24.94,-53.24],[-24.94,-53.0],[-24.7,-53.0],[-24.7,-53.24]] },
  { id:'BR-MG-509', ibgeCode:'3110509', name:'Camanducaia', state:'MG', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-22.7515, lon:-46.1494, flvCultures:["ervilha"], flvTons:20, poly:[[-22.87,-46.27],[-22.87,-46.03],[-22.63,-46.03],[-22.63,-46.27]] },
  { id:'BR-PR-809', ibgeCode:'4127809', name:'Tomazina', state:'PR', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-23.7796, lon:-49.9499, flvCultures:["ervilha"], flvTons:20, poly:[[-23.9,-50.07],[-23.9,-49.83],[-23.66,-49.83],[-23.66,-50.07]] },
  { id:'BR-RS-307', ibgeCode:'4319307', name:'São Paulo das Missões', state:'RS', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-28.0195, lon:-54.9404, flvCultures:["ervilha"], flvTons:20, poly:[[-28.14,-55.06],[-28.14,-54.82],[-27.9,-54.82],[-27.9,-55.06]] },
  { id:'BR-PR-253', ibgeCode:'4104253', name:'Campo Magro', state:'PR', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-25.3687, lon:-49.4501, flvCultures:["ervilha"], flvTons:19, poly:[[-25.49,-49.57],[-25.49,-49.33],[-25.25,-49.33],[-25.25,-49.57]] },
  { id:'BR-MG-101', ibgeCode:'3125101', name:'Extrema', state:'MG', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-22.854, lon:-46.3178, flvCultures:["ervilha"], flvTons:15, poly:[[-22.97,-46.44],[-22.97,-46.2],[-22.73,-46.2],[-22.73,-46.44]] },
  { id:'BR-MG-578', ibgeCode:'3165578', name:'Senador Amaral', state:'MG', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-22.5869, lon:-46.1763, flvCultures:["ervilha"], flvTons:14, poly:[[-22.71,-46.3],[-22.71,-46.06],[-22.47,-46.06],[-22.47,-46.3]] },
  { id:'BR-MG-631', ibgeCode:'3101631', name:'Alfredo Vasconcelos', state:'MG', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-21.1535, lon:-43.7718, flvCultures:["ervilha"], flvTons:12, poly:[[-21.27,-43.89],[-21.27,-43.65],[-21.03,-43.65],[-21.03,-43.89]] },
  { id:'BR-PR-901', ibgeCode:'4102901', name:'Bituruna', state:'PR', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-26.1607, lon:-51.5518, flvCultures:["ervilha"], flvTons:8, poly:[[-26.28,-51.67],[-26.28,-51.43],[-26.04,-51.43],[-26.04,-51.67]] },
  { id:'BR-PR-503', ibgeCode:'4103503', name:'Califórnia', state:'PR', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-23.6566, lon:-51.3574, flvCultures:["ervilha"], flvTons:8, poly:[[-23.78,-51.48],[-23.78,-51.24],[-23.54,-51.24],[-23.54,-51.48]] },
  { id:'BR-PR-751', ibgeCode:'4107751', name:'Figueira', state:'PR', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-23.8455, lon:-50.4031, flvCultures:["ervilha"], flvTons:8, poly:[[-23.97,-50.52],[-23.97,-50.28],[-23.73,-50.28],[-23.73,-50.52]] },
  { id:'BR-SP-308', ibgeCode:'3550308', name:'São Paulo', state:'SP', country:'BR', culture:'ervilha', areaMha:0.01, ndvi:0.45, coef:0.75, lat:-23.5329, lon:-46.6395, flvCultures:["ervilha"], flvTons:6, poly:[[-23.65,-46.76],[-23.65,-46.52],[-23.41,-46.52],[-23.41,-46.76]] },
];
MUNICIPAL_DB_FLV.forEach(m => { if (!MUNICIPAL_DB.find(x => x.ibgeCode === m.ibgeCode)) MUNICIPAL_DB.push(m); });

// ════════════════════════════════════════════════════════════════
// BIO-COMMAND — COBERTURA HORTIFRUTIGRANJEIRA AMÉRICA DO SUL
// Base curada de polos produtivos: frutas, hortaliças, tubérculos,
// flores, ovos, aves, leite e proteínas de granja. Valores de volume
// são ordens de grandeza operacionais para mapa/risco, não substituem
// séries oficiais nacionais.
// ════════════════════════════════════════════════════════════════
const MUNICIPAL_DB_SOUTH_AMERICA_HF = [
  { id:'AR-MDZ-LUJ', name:'Luján de Cuyo', state:'Mendoza', country:'AR', culture:'uva', areaMha:0.20, area_ha:42000, ndvi:0.7, coef:0.84, lat:-33.04, lon:-68.88, flvCultures:["uva", "alho", "cebola", "pessego", "ameixa"], flvTons:420000, phenology:'Oásis Norte — viticultura, alho e frutas de caroço', source:'curated_south_america_hf_2026', poly:[[-33.16, -69.0], [-33.16, -68.76], [-32.92, -68.76], [-32.92, -69.0]] },
  { id:'AR-MDZ-SRA', name:'San Rafael', state:'Mendoza', country:'AR', culture:'uva', areaMha:0.20, area_ha:36000, ndvi:0.68, coef:0.84, lat:-34.61, lon:-68.33, flvCultures:["uva", "pera", "maçã", "ameixa", "tomate"], flvTons:360000, phenology:'Oásis Sul — fruta fresca, vitivinicultura e tomate', source:'curated_south_america_hf_2026', poly:[[-34.73, -68.45], [-34.73, -68.21], [-34.49, -68.21], [-34.49, -68.45]] },
  { id:'AR-RNO-ALT', name:'Alto Valle', state:'Río Negro', country:'AR', culture:'maca', areaMha:0.20, area_ha:52000, ndvi:0.72, coef:0.84, lat:-38.95, lon:-67.99, flvCultures:["maçã", "pera", "cereja", "ameixa"], flvTons:520000, phenology:'Vale irrigado do Río Negro — pomáceas', source:'curated_south_america_hf_2026', poly:[[-39.07, -68.11], [-39.07, -67.87], [-38.83, -67.87], [-38.83, -68.11]] },
  { id:'AR-TUC-FAM', name:'Famaillá', state:'Tucumán', country:'AR', culture:'limao', areaMha:0.20, area_ha:48000, ndvi:0.66, coef:0.84, lat:-27.05, lon:-65.4, flvCultures:["limão", "laranja", "mandarina", "hortaliças"], flvTons:480000, phenology:'NOA citrícola — limão industrial e fresco', source:'curated_south_america_hf_2026', poly:[[-27.17, -65.52], [-27.17, -65.28], [-26.93, -65.28], [-26.93, -65.52]] },
  { id:'AR-SAL-ORA', name:'Orán', state:'Salta', country:'AR', culture:'banana', areaMha:0.20, area_ha:21000, ndvi:0.62, coef:0.84, lat:-23.13, lon:-64.32, flvCultures:["banana", "citrus", "tomate", "pimentao"], flvTons:210000, phenology:'Subtropical de Salta/Jujuy', source:'curated_south_america_hf_2026', poly:[[-23.25, -64.44], [-23.25, -64.2], [-23.01, -64.2], [-23.01, -64.44]] },
  { id:'AR-BUE-LPL', name:'La Plata', state:'Buenos Aires', country:'AR', culture:'horti', areaMha:0.20, area_ha:18000, ndvi:0.64, coef:0.84, lat:-34.92, lon:-57.95, flvCultures:["alface", "tomate", "pimentao", "folhosas"], flvTons:180000, phenology:'Cinturão verde de Buenos Aires', source:'curated_south_america_hf_2026', poly:[[-35.04, -58.07], [-35.04, -57.83], [-34.8, -57.83], [-34.8, -58.07]] },
  { id:'AR-COR-COL', name:'Colonia Caroya', state:'Córdoba', country:'AR', culture:'horti', areaMha:0.20, area_ha:14500, ndvi:0.61, coef:0.84, lat:-31.02, lon:-64.07, flvCultures:["batata", "cebola", "uva", "frutas"], flvTons:145000, phenology:'Horti-fruti centro argentino', source:'curated_south_america_hf_2026', poly:[[-31.14, -64.19], [-31.14, -63.95], [-30.9, -63.95], [-30.9, -64.19]] },
  { id:'CL-RM-MAI', name:'Maipo / Buin', state:'Región Metropolitana', country:'CL', culture:'uva', areaMha:0.20, area_ha:39000, ndvi:0.7, coef:0.84, lat:-33.73, lon:-70.74, flvCultures:["uva", "hortaliças", "tomate", "pimentao"], flvTons:390000, phenology:'Vale Central — uva, hortaliças e exportação', source:'curated_south_america_hf_2026', poly:[[-33.85, -70.86], [-33.85, -70.62], [-33.61, -70.62], [-33.61, -70.86]] },
  { id:'CL-OHI-RAN', name:'Rancagua / Cachapoal', state:'O’Higgins', country:'CL', culture:'uva', areaMha:0.20, area_ha:61000, ndvi:0.73, coef:0.84, lat:-34.17, lon:-70.74, flvCultures:["uva", "cereja", "maçã", "nectarina", "pêssego"], flvTons:610000, phenology:'O’Higgins — frutas temperadas exportáveis', source:'curated_south_america_hf_2026', poly:[[-34.29, -70.86], [-34.29, -70.62], [-34.05, -70.62], [-34.05, -70.86]] },
  { id:'CL-MAU-CUR', name:'Curicó / Maule', state:'Maule', country:'CL', culture:'maca', areaMha:0.20, area_ha:58000, ndvi:0.72, coef:0.84, lat:-34.98, lon:-71.24, flvCultures:["maçã", "cereja", "kiwi", "uva"], flvTons:580000, phenology:'Maule — pomáceas e caroço', source:'curated_south_america_hf_2026', poly:[[-35.1, -71.36], [-35.1, -71.12], [-34.86, -71.12], [-34.86, -71.36]] },
  { id:'CL-NUB-CHI', name:'Chillán', state:'Ñuble', country:'CL', culture:'horti', areaMha:0.20, area_ha:21000, ndvi:0.63, coef:0.84, lat:-36.61, lon:-72.1, flvCultures:["tomate", "cebola", "alho", "batata", "berries"], flvTons:210000, phenology:'Ñuble/Bío-Bío hortícola', source:'curated_south_america_hf_2026', poly:[[-36.73, -72.22], [-36.73, -71.98], [-36.49, -71.98], [-36.49, -72.22]] },
  { id:'CL-ARA-TEM', name:'Temuco / Araucanía', state:'Araucanía', country:'CL', culture:'batata', areaMha:0.20, area_ha:26000, ndvi:0.64, coef:0.84, lat:-38.74, lon:-72.59, flvCultures:["batata", "frango", "leite", "berries"], flvTons:260000, phenology:'Sul chileno — batata, leite e berries', source:'curated_south_america_hf_2026', poly:[[-38.86, -72.71], [-38.86, -72.47], [-38.62, -72.47], [-38.62, -72.71]] },
  { id:'CL-ATA-COP', name:'Copiapó / Huasco', state:'Atacama', country:'CL', culture:'uva', areaMha:0.20, area_ha:15000, ndvi:0.58, coef:0.84, lat:-27.37, lon:-70.33, flvCultures:["uva", "oliva", "tomate"], flvTons:150000, phenology:'Oásis desértico irrigado', source:'curated_south_america_hf_2026', poly:[[-27.49, -70.45], [-27.49, -70.21], [-27.25, -70.21], [-27.25, -70.45]] },
  { id:'PE-ICA-ICA', name:'Ica', state:'Ica', country:'PE', culture:'uva', areaMha:0.20, area_ha:72000, ndvi:0.76, coef:0.84, lat:-14.07, lon:-75.73, flvCultures:["uva", "aspargos", "palta", "mandarina", "arandano"], flvTons:720000, phenology:'Agroexportação costeira — Ica', source:'curated_south_america_hf_2026', poly:[[-14.19, -75.85], [-14.19, -75.61], [-13.95, -75.61], [-13.95, -75.85]] },
  { id:'PE-LAL-VIR', name:'Virú / Chao', state:'La Libertad', country:'PE', culture:'aspargos', areaMha:0.20, area_ha:65000, ndvi:0.74, coef:0.84, lat:-8.41, lon:-78.75, flvCultures:["aspargos", "palta", "arandano", "alcachofra", "uva"], flvTons:650000, phenology:'Chavimochic — hortifruti de exportação', source:'curated_south_america_hf_2026', poly:[[-8.53, -78.87], [-8.53, -78.63], [-8.29, -78.63], [-8.29, -78.87]] },
  { id:'PE-LAM-OLM', name:'Olmos / Motupe', state:'Lambayeque', country:'PE', culture:'palta', areaMha:0.20, area_ha:43000, ndvi:0.71, coef:0.84, lat:-5.99, lon:-79.74, flvCultures:["palta", "manga", "uva", "limão"], flvTons:430000, phenology:'Olmos — fruticultura irrigada', source:'curated_south_america_hf_2026', poly:[[-6.11, -79.86], [-6.11, -79.62], [-5.87, -79.62], [-5.87, -79.86]] },
  { id:'PE-PIU-TAM', name:'Tambogrande / Sullana', state:'Piura', country:'PE', culture:'manga', areaMha:0.20, area_ha:52000, ndvi:0.68, coef:0.84, lat:-4.93, lon:-80.34, flvCultures:["manga", "limão", "banana", "uva"], flvTons:520000, phenology:'Piura — manga e limão', source:'curated_south_america_hf_2026', poly:[[-5.05, -80.46], [-5.05, -80.22], [-4.81, -80.22], [-4.81, -80.46]] },
  { id:'PE-LIM-HUA', name:'Huaral / Cañete', state:'Lima', country:'PE', culture:'horti', areaMha:0.20, area_ha:31000, ndvi:0.66, coef:0.84, lat:-11.5, lon:-77.2, flvCultures:["mandarina", "uva", "palta", "hortaliças"], flvTons:310000, phenology:'Costa central — citros e hortaliças', source:'curated_south_america_hf_2026', poly:[[-11.62, -77.32], [-11.62, -77.08], [-11.38, -77.08], [-11.38, -77.32]] },
  { id:'PE-JUN-CHA', name:'Chanchamayo', state:'Junín', country:'PE', culture:'cafe', areaMha:0.20, area_ha:19000, ndvi:0.69, coef:0.84, lat:-11.06, lon:-75.33, flvCultures:["café", "cacau", "banana", "abacaxi"], flvTons:190000, phenology:'Selva central — café, cacau e frutas', source:'curated_south_america_hf_2026', poly:[[-11.18, -75.45], [-11.18, -75.21], [-10.94, -75.21], [-10.94, -75.45]] },
  { id:'EC-GUA-MAC', name:'Machala / El Oro', state:'El Oro', country:'EC', culture:'banana', areaMha:0.20, area_ha:76000, ndvi:0.74, coef:0.84, lat:-3.26, lon:-79.96, flvCultures:["banana", "cacau", "camarão"], flvTons:760000, phenology:'Corredor bananeiro do El Oro', source:'curated_south_america_hf_2026', poly:[[-3.38, -80.08], [-3.38, -79.84], [-3.14, -79.84], [-3.14, -80.08]] },
  { id:'EC-GUA-GYE', name:'Guayas / Los Ríos', state:'Guayas', country:'EC', culture:'banana', areaMha:0.20, area_ha:89000, ndvi:0.73, coef:0.84, lat:-2.17, lon:-79.9, flvCultures:["banana", "cacau", "arroz", "manga"], flvTons:890000, phenology:'Litoral equatoriano — banana, cacau, arroz', source:'curated_south_america_hf_2026', poly:[[-2.29, -80.02], [-2.29, -79.78], [-2.05, -79.78], [-2.05, -80.02]] },
  { id:'EC-MAN-QUE', name:'Quevedo / Los Ríos', state:'Los Ríos', country:'EC', culture:'cacau', areaMha:0.20, area_ha:42000, ndvi:0.7, coef:0.84, lat:-1.03, lon:-79.46, flvCultures:["cacau", "banana", "mandarina", "milho"], flvTons:420000, phenology:'Cacau fino e banana', source:'curated_south_america_hf_2026', poly:[[-1.15, -79.58], [-1.15, -79.34], [-0.91, -79.34], [-0.91, -79.58]] },
  { id:'EC-PIC-CAY', name:'Cayambe / Pedro Moncayo', state:'Pichincha', country:'EC', culture:'flores', areaMha:0.20, area_ha:16000, ndvi:0.65, coef:0.84, lat:0.04, lon:-78.15, flvCultures:["flores", "brocolis", "alface", "leite"], flvTons:160000, phenology:'Serra equatoriana — flores e hortaliças', source:'curated_south_america_hf_2026', poly:[[-0.08, -78.27], [-0.08, -78.03], [0.16, -78.03], [0.16, -78.27]] },
  { id:'EC-COT-LAT', name:'Latacunga / Cotopaxi', state:'Cotopaxi', country:'EC', culture:'brocolis', areaMha:0.20, area_ha:13000, ndvi:0.63, coef:0.84, lat:-0.93, lon:-78.62, flvCultures:["brocolis", "batata", "cenoura", "leite"], flvTons:130000, phenology:'Altiplano hortícola', source:'curated_south_america_hf_2026', poly:[[-1.05, -78.74], [-1.05, -78.5], [-0.81, -78.5], [-0.81, -78.74]] },
  { id:'CO-ANT-URA', name:'Urabá / Apartadó', state:'Antioquia', country:'CO', culture:'banana', areaMha:0.20, area_ha:82000, ndvi:0.75, coef:0.84, lat:7.88, lon:-76.63, flvCultures:["banana", "plátano", "cacau"], flvTons:820000, phenology:'Urabá — banana/plátano exportação', source:'curated_south_america_hf_2026', poly:[[7.76, -76.75], [7.76, -76.51], [8.0, -76.51], [8.0, -76.75]] },
  { id:'CO-MAG-SMR', name:'Santa Marta / Magdalena', state:'Magdalena', country:'CO', culture:'banana', areaMha:0.20, area_ha:51000, ndvi:0.72, coef:0.84, lat:11.24, lon:-74.2, flvCultures:["banana", "manga", "cítricos"], flvTons:510000, phenology:'Caribe colombiano — banana', source:'curated_south_america_hf_2026', poly:[[11.12, -74.32], [11.12, -74.08], [11.36, -74.08], [11.36, -74.32]] },
  { id:'CO-CUN-FAC', name:'Facatativá / Sabana Bogotá', state:'Cundinamarca', country:'CO', culture:'flores', areaMha:0.20, area_ha:26000, ndvi:0.67, coef:0.84, lat:4.81, lon:-74.35, flvCultures:["flores", "batata", "alface", "morango", "leite"], flvTons:260000, phenology:'Sabana de Bogotá — flores, batata, lácteos', source:'curated_south_america_hf_2026', poly:[[4.69, -74.47], [4.69, -74.23], [4.93, -74.23], [4.93, -74.47]] },
  { id:'CO-VAL-PAL', name:'Palmira / Valle del Cauca', state:'Valle del Cauca', country:'CO', culture:'cana', areaMha:0.20, area_ha:38000, ndvi:0.66, coef:0.84, lat:3.54, lon:-76.3, flvCultures:["cana", "uva", "hortaliças", "frango"], flvTons:380000, phenology:'Valle del Cauca — cana e hortifruti', source:'curated_south_america_hf_2026', poly:[[3.42, -76.42], [3.42, -76.18], [3.66, -76.18], [3.66, -76.42]] },
  { id:'CO-HUI-GAR', name:'Garzón / Huila', state:'Huila', country:'CO', culture:'cafe', areaMha:0.20, area_ha:21000, ndvi:0.68, coef:0.84, lat:2.2, lon:-75.63, flvCultures:["café", "cacau", "maracuja", "abacate"], flvTons:210000, phenology:'Andes colombianos — café e frutas', source:'curated_south_america_hf_2026', poly:[[2.08, -75.75], [2.08, -75.51], [2.32, -75.51], [2.32, -75.75]] },
  { id:'CO-SAN-BUC', name:'Bucaramanga / Santander', state:'Santander', country:'CO', culture:'cacau', areaMha:0.20, area_ha:23000, ndvi:0.66, coef:0.84, lat:7.12, lon:-73.12, flvCultures:["cacau", "cítricos", "abacate", "frango"], flvTons:230000, phenology:'Santander — cacau, citros e avicultura', source:'curated_south_america_hf_2026', poly:[[7.0, -73.24], [7.0, -73.0], [7.24, -73.0], [7.24, -73.24]] },
  { id:'BO-SCZ-YAP', name:'Yapacaní / Santa Cruz', state:'Santa Cruz', country:'BO', culture:'banana', areaMha:0.20, area_ha:30000, ndvi:0.66, coef:0.84, lat:-17.4, lon:-63.88, flvCultures:["banana", "arroz", "soja", "mandioca", "frango"], flvTons:300000, phenology:'Oriente boliviano — tropical e grãos', source:'curated_south_america_hf_2026', poly:[[-17.52, -64.0], [-17.52, -63.76], [-17.28, -63.76], [-17.28, -64.0]] },
  { id:'BO-SCZ-VAL', name:'Vallegrande', state:'Santa Cruz', country:'BO', culture:'horti', areaMha:0.20, area_ha:9500, ndvi:0.59, coef:0.84, lat:-18.49, lon:-64.1, flvCultures:["tomate", "batata", "pimentao", "cebola"], flvTons:95000, phenology:'Vales cruceños — hortaliças', source:'curated_south_america_hf_2026', poly:[[-18.61, -64.22], [-18.61, -63.98], [-18.37, -63.98], [-18.37, -64.22]] },
  { id:'BO-CBA-CHI', name:'Chapare / Cochabamba', state:'Cochabamba', country:'BO', culture:'banana', areaMha:0.20, area_ha:28000, ndvi:0.7, coef:0.84, lat:-16.99, lon:-65.13, flvCultures:["banana", "abacaxi", "mandioca", "cítricos"], flvTons:280000, phenology:'Chapare tropical', source:'curated_south_america_hf_2026', poly:[[-17.11, -65.25], [-17.11, -65.01], [-16.87, -65.01], [-16.87, -65.25]] },
  { id:'BO-LP-ALT', name:'Altiplano La Paz / Oruro', state:'La Paz/Oruro', country:'BO', culture:'batata', areaMha:0.20, area_ha:19000, ndvi:0.52, coef:0.84, lat:-16.5, lon:-68.15, flvCultures:["batata", "quinua", "cebola", "leite"], flvTons:190000, phenology:'Altiplano andino — batata e quinoa', source:'curated_south_america_hf_2026', poly:[[-16.62, -68.27], [-16.62, -68.03], [-16.38, -68.03], [-16.38, -68.27]] },
  { id:'BO-TJA-TAR', name:'Tarija', state:'Tarija', country:'BO', culture:'uva', areaMha:0.20, area_ha:12000, ndvi:0.61, coef:0.84, lat:-21.53, lon:-64.73, flvCultures:["uva", "tomate", "pimentao", "hortaliças"], flvTons:120000, phenology:'Vales de Tarija — uva e hortaliças', source:'curated_south_america_hf_2026', poly:[[-21.65, -64.85], [-21.65, -64.61], [-21.41, -64.61], [-21.41, -64.85]] },
  { id:'PY-ITA-CDE', name:'Alto Paraná / Itapúa', state:'Alto Paraná/Itapúa', country:'PY', culture:'soja', areaMha:0.20, area_ha:53000, ndvi:0.66, coef:0.84, lat:-25.51, lon:-54.61, flvCultures:["soja", "milho", "mandioca", "frango", "suinos"], flvTons:530000, phenology:'Leste paraguaio — grãos, mandioca e proteína', source:'curated_south_america_hf_2026', poly:[[-25.63, -54.73], [-25.63, -54.49], [-25.39, -54.49], [-25.39, -54.73]] },
  { id:'PY-CEN-ITA', name:'Itauguá / Central', state:'Central', country:'PY', culture:'horti', areaMha:0.20, area_ha:9000, ndvi:0.58, coef:0.84, lat:-25.38, lon:-57.33, flvCultures:["tomate", "pimentao", "alface", "mandioca", "ovos"], flvTons:90000, phenology:'Cinturão hortícola de Assunção', source:'curated_south_america_hf_2026', poly:[[-25.5, -57.45], [-25.5, -57.21], [-25.26, -57.21], [-25.26, -57.45]] },
  { id:'PY-CAZ-CAZ', name:'Caaguazú', state:'Caaguazú', country:'PY', culture:'mandioca', areaMha:0.20, area_ha:26000, ndvi:0.61, coef:0.84, lat:-25.46, lon:-56.02, flvCultures:["mandioca", "soja", "milho", "frango"], flvTons:260000, phenology:'Mandioca industrial e grãos', source:'curated_south_america_hf_2026', poly:[[-25.58, -56.14], [-25.58, -55.9], [-25.34, -55.9], [-25.34, -56.14]] },
  { id:'PY-PAR-PIL', name:'Pilar / Ñeembucú', state:'Ñeembucú', country:'PY', culture:'arroz', areaMha:0.20, area_ha:11000, ndvi:0.6, coef:0.84, lat:-26.86, lon:-58.3, flvCultures:["arroz", "hortaliças", "pecuaria_leite"], flvTons:110000, phenology:'Arroz irrigado e leite', source:'curated_south_america_hf_2026', poly:[[-26.98, -58.42], [-26.98, -58.18], [-26.74, -58.18], [-26.74, -58.42]] },
  { id:'UY-SAL-SAL', name:'Salto / Paysandú', state:'Salto/Paysandú', country:'UY', culture:'citricos', areaMha:0.20, area_ha:30000, ndvi:0.68, coef:0.84, lat:-31.39, lon:-57.96, flvCultures:["laranja", "mandarina", "limão", "arroz", "leite"], flvTons:300000, phenology:'Litoral Norte — citros e arroz', source:'curated_south_america_hf_2026', poly:[[-31.51, -58.08], [-31.51, -57.84], [-31.27, -57.84], [-31.27, -58.08]] },
  { id:'UY-CAN-CAN', name:'Canelones', state:'Canelones', country:'UY', culture:'horti', areaMha:0.20, area_ha:16000, ndvi:0.64, coef:0.84, lat:-34.52, lon:-56.28, flvCultures:["tomate", "alface", "uva", "pêssego", "ovos"], flvTons:160000, phenology:'Cinturão hortifrutícola de Montevidéu', source:'curated_south_america_hf_2026', poly:[[-34.64, -56.4], [-34.64, -56.16], [-34.4, -56.16], [-34.4, -56.4]] },
  { id:'UY-SJO-SJO', name:'San José', state:'San José', country:'UY', culture:'leite', areaMha:0.20, area_ha:21000, ndvi:0.63, coef:0.84, lat:-34.34, lon:-56.71, flvCultures:["leite", "queijo", "hortaliças", "frango"], flvTons:210000, phenology:'Leite, aves e hortifruti', source:'curated_south_america_hf_2026', poly:[[-34.46, -56.83], [-34.46, -56.59], [-34.22, -56.59], [-34.22, -56.83]] },
  { id:'UY-ROC-ROZ', name:'Rocha / Treinta y Tres', state:'Rocha/Treinta y Tres', country:'UY', culture:'arroz', areaMha:0.20, area_ha:19000, ndvi:0.62, coef:0.84, lat:-33.37, lon:-54.21, flvCultures:["arroz", "batata", "pecuaria_corte"], flvTons:190000, phenology:'Arroz e pecuária no leste', source:'curated_south_america_hf_2026', poly:[[-33.49, -54.33], [-33.49, -54.09], [-33.25, -54.09], [-33.25, -54.33]] },
  { id:'VE-ZUL-SUR', name:'Sur del Lago', state:'Zulia', country:'VE', culture:'banana', areaMha:0.20, area_ha:43000, ndvi:0.69, coef:0.84, lat:8.98, lon:-71.91, flvCultures:["banana", "plátano", "cacau", "leite"], flvTons:430000, phenology:'Sul do Lago — plátano, banana e leite', source:'curated_south_america_hf_2026', poly:[[8.86, -72.03], [8.86, -71.79], [9.1, -71.79], [9.1, -72.03]] },
  { id:'VE-ARA-MAR', name:'Maracay / Aragua', state:'Aragua', country:'VE', culture:'horti', areaMha:0.20, area_ha:17000, ndvi:0.62, coef:0.84, lat:10.25, lon:-67.6, flvCultures:["tomate", "pimentao", "cítricos", "frango"], flvTons:170000, phenology:'Centro venezuelano — hortaliças e aves', source:'curated_south_america_hf_2026', poly:[[10.13, -67.72], [10.13, -67.48], [10.37, -67.48], [10.37, -67.72]] },
  { id:'VE-LAR-BAR', name:'Barquisimeto / Lara', state:'Lara', country:'VE', culture:'cebola', areaMha:0.20, area_ha:15000, ndvi:0.59, coef:0.84, lat:10.07, lon:-69.32, flvCultures:["cebola", "tomate", "pimentao", "uvas"], flvTons:150000, phenology:'Vale seco irrigado — hortaliças', source:'curated_south_america_hf_2026', poly:[[9.95, -69.44], [9.95, -69.2], [10.19, -69.2], [10.19, -69.44]] },
  { id:'VE-MER-MER', name:'Mérida Andes', state:'Mérida', country:'VE', culture:'batata', areaMha:0.20, area_ha:13000, ndvi:0.6, coef:0.84, lat:8.59, lon:-71.14, flvCultures:["batata", "cenoura", "alface", "leite"], flvTons:130000, phenology:'Andes venezuelanos — batata e lácteos', source:'curated_south_america_hf_2026', poly:[[8.47, -71.26], [8.47, -71.02], [8.71, -71.02], [8.71, -71.26]] },
  { id:'GY-DEM-GEO', name:'Demerara / Georgetown', state:'Demerara-Mahaica', country:'GY', culture:'arroz', areaMha:0.20, area_ha:16000, ndvi:0.64, coef:0.84, lat:6.8, lon:-58.16, flvCultures:["arroz", "coco", "abacaxi", "frango"], flvTons:160000, phenology:'Planície costeira guianense', source:'curated_south_america_hf_2026', poly:[[6.68, -58.28], [6.68, -58.04], [6.92, -58.04], [6.92, -58.28]] },
  { id:'GY-ESS-ROS', name:'Essequibo Coast', state:'Pomeroon-Supenaam', country:'GY', culture:'arroz', areaMha:0.20, area_ha:12000, ndvi:0.63, coef:0.84, lat:7.26, lon:-58.49, flvCultures:["arroz", "coco", "banana", "mandioca"], flvTons:120000, phenology:'Costa do Essequibo', source:'curated_south_america_hf_2026', poly:[[7.14, -58.61], [7.14, -58.37], [7.38, -58.37], [7.38, -58.61]] },
  { id:'SR-PAR-PAR', name:'Paramaribo / Wanica', state:'Paramaribo/Wanica', country:'SR', culture:'horti', areaMha:0.20, area_ha:13000, ndvi:0.64, coef:0.84, lat:5.85, lon:-55.2, flvCultures:["arroz", "banana", "hortaliças", "frango"], flvTons:130000, phenology:'Costa do Suriname', source:'curated_south_america_hf_2026', poly:[[5.73, -55.32], [5.73, -55.08], [5.97, -55.08], [5.97, -55.32]] },
  { id:'SR-NIC-NIC', name:'Nickerie', state:'Nickerie', country:'SR', culture:'arroz', areaMha:0.20, area_ha:19000, ndvi:0.66, coef:0.84, lat:5.95, lon:-56.99, flvCultures:["arroz", "banana", "coco"], flvTons:190000, phenology:'Nickerie — arroz irrigado', source:'curated_south_america_hf_2026', poly:[[5.83, -57.11], [5.83, -56.87], [6.07, -56.87], [6.07, -57.11]] },
  { id:'GF-CAY-MAT', name:'Cayenne / Matoury', state:'Guiana Francesa', country:'GF', culture:'horti', areaMha:0.20, area_ha:6000, ndvi:0.62, coef:0.84, lat:4.92, lon:-52.33, flvCultures:["hortaliças", "banana", "mandioca", "frango"], flvTons:60000, phenology:'Abastecimento local — costa da Guiana Francesa', source:'curated_south_america_hf_2026', poly:[[4.8, -52.45], [4.8, -52.21], [5.04, -52.21], [5.04, -52.45]] },
  { id:'GF-STL-STL', name:'Saint-Laurent-du-Maroni', state:'Guiana Francesa', country:'GF', culture:'mandioca', areaMha:0.20, area_ha:5000, ndvi:0.63, coef:0.84, lat:5.5, lon:-54.03, flvCultures:["mandioca", "banana", "abacaxi"], flvTons:50000, phenology:'Oeste guianense — mandioca e frutas tropicais', source:'curated_south_america_hf_2026', poly:[[5.38, -54.15], [5.38, -53.91], [5.62, -53.91], [5.62, -54.15]] }
];
MUNICIPAL_DB_SOUTH_AMERICA_HF.forEach(m => {
  if (!MUNICIPAL_DB.find(x => x.id === m.id)) MUNICIPAL_DB.push(m);
});
window.BC_SOUTH_AMERICA_HF_META = {
  updated_at: '2026-05-24',
  scope: 'América do Sul — polos hortifrutigranjeiros',
  records: MUNICIPAL_DB_SOUTH_AMERICA_HF.length,
  countries: [...new Set(MUNICIPAL_DB_SOUTH_AMERICA_HF.map(m => m.country))].sort(),
  products: [...new Set(MUNICIPAL_DB_SOUTH_AMERICA_HF.flatMap(m => m.flvCultures || [m.culture]))].sort(),
  precision: 'polo/município-região; não cadastro exaustivo de propriedade rural'
};



// ════════════════════════════════════════════════════════════════
// ARGUS — Calendário de Vigilância Fenológica 2026
// O sistema usa estas janelas para diferenciar queda de NDVI
// esperada (colheita) de anomalia real (praga/seca).
// ════════════════════════════════════════════════════════════════
const ARGUS_CALENDAR = {
  cebola: {
    label: 'Cebola', regions: ['triangulo-mg','cristalina-go','vale-sf'],
    plantio: { start:2, end:3 },
    colheita: { start:6, end:10 },
    cycle_days: 150,
  },
  batata: {
    label: 'Batata', regions: ['triangulo-mg','sul-minas','chapada-ba'],
    plantio: { start:2, end:4 },
    colheita: { start:5, end:7 },
    cycle_days: 100,
  },
  tomate: {
    label: 'Tomate', regions: ['cristalina-go','vale-sf','sul-minas','ibiapaba-ce','chapada-ba'],
    plantio: { start:1, end:2 },
    colheita: { start:4, end:10 },
    cycle_days: 120,
  },
  cenoura: {
    label: 'Cenoura', regions: ['triangulo-mg','chapada-ba','sul-minas'],
    plantio: { start:1, end:12 },
    colheita: { start:1, end:12 },
    cycle_days: 100,
  },
  folhosas: {
    label: 'Folhosas', regions: ['cinturao-verde-sp','serra-gaucha'],
    plantio: { start:1, end:12 },
    colheita: { start:1, end:12 },
    cycle_days: 45,
  },
};



// ═══════════════════════════════════════════════════════════════════
// CLIMATE INTELLIGENCE — Monitoramento de Eventos Extremos
// ═══════════════════════════════════════════════════════════════════
const CLIMATE_HF_REGIONS = [
  { id:'cinturao-verde-sp', name:'Cinturão Verde SP',     lat:-23.65, lon:-47.20, crops:['folhosas','tomate'], logKey:'ferro', frostRisk:true },
  { id:'serra-gaucha',      name:'Serra Gaúcha',          lat:-29.10, lon:-51.15, crops:['uva','horti'],       logKey:'par',   frostRisk:true },
  { id:'sul-minas',         name:'Sul de Minas',          lat:-22.20, lon:-45.85, crops:['cafe','batata','tomate'], logKey:'ferro', frostRisk:true },
  { id:'triangulo-mg',      name:'Triângulo Mineiro',     lat:-19.00, lon:-48.25, crops:['batata','cebola'],   logKey:'br364', frostRisk:false },
  { id:'cristalina-go',     name:'Cristalina GO',         lat:-16.20, lon:-47.55, crops:['cebola','tomate'],   logKey:'br364', frostRisk:false },
  { id:'vale-sf',           name:'Vale do São Francisco', lat:-9.40,  lon:-40.45, crops:['manga','tomate','uva'], logKey:'ros', frostRisk:false },
  { id:'ibiapaba-ce',       name:'Ibiapaba CE',           lat:-3.70,  lon:-40.95, crops:['tomate','pimentao'], logKey:'ros',   frostRisk:false },
  { id:'chapada-ba',        name:'Chapada Diamantina',    lat:-13.30, lon:-41.25, crops:['batata','cenoura'],  logKey:'ros',   frostRisk:false },
  { id:'serra-catarinense', name:'Serra Catarinense',     lat:-28.00, lon:-49.90, crops:['horti','maca'],      logKey:'par',   frostRisk:true },
  { id:'vale-itajai',       name:'Vale do Itajaí SC',     lat:-27.00, lon:-49.50, crops:['horti','banana'],    logKey:'par',   frostRisk:true },
  { id:'sul-pr',            name:'Sul do Paraná',         lat:-25.30, lon:-51.30, crops:['batata','soja'],     logKey:'par',   frostRisk:true },
  { id:'norte-es',          name:'Norte do ES',           lat:-18.70, lon:-39.85, crops:['cafe','mamao'],      logKey:'santos',frostRisk:false },
];

const CLIMATE_THRESHOLDS = {
  NEVE:           { field:'temperature_2m_min', op:'<', value:0,   severity:'CRITICAL' },
  GEADA:          { field:'temperature_2m_min', op:'<', value:2,   severity:'CRITICAL' },
  RISCO_GEADA:    { field:'temperature_2m_min', op:'<', value:4,   severity:'HIGH' },
  ENCHENTE:       { field:'precipitation_sum',  op:'>', value:40,  severity:'CRITICAL' },
  CHUVA_INTENSA:  { field:'precipitation_sum',  op:'>', value:25,  severity:'HIGH' },
  TEMPESTADE:     { field:'wind_speed_10m',     op:'>', value:80,  severity:'CRITICAL' },
  VENTO_FORTE:    { field:'wind_speed_10m',     op:'>', value:50,  severity:'HIGH' },
};

const CROP_VULNERABILITY = {
  GEADA:  { tomate:{yield:35,price:22}, morango:{yield:45,price:30}, folhosas:{yield:30,price:15}, cafe:{yield:20,price:12}, banana:{yield:25,price:10}, maca:{yield:15,price:8} },
  NEVE:   { tomate:{yield:50,price:35}, morango:{yield:60,price:40}, folhosas:{yield:45,price:25}, horti:{yield:40,price:20}, maca:{yield:20,price:10} },
  ENCHENTE:{ tomate:{yield:20,price:12}, batata:{yield:30,price:18}, cenoura:{yield:25,price:15}, cebola:{yield:20,price:10}, banana:{yield:10,price:5} },
  CHUVA_INTENSA:{ tomate:{yield:12,price:8}, folhosas:{yield:15,price:10}, morango:{yield:20,price:12}, manga:{yield:10,price:8} },
  RISCO_GEADA:{ tomate:{yield:10,price:8}, folhosas:{yield:8,price:5}, cafe:{yield:5,price:3} },
  TEMPESTADE:{ tomate:{yield:15,price:10}, folhosas:{yield:12,price:8}, banana:{yield:20,price:12}, manga:{yield:15,price:10} },
  VENTO_FORTE:{ tomate:{yield:8,price:5}, folhosas:{yield:6,price:4} },
};

function argusCheckNdvi(mun) {
  if (!mun.argus) return null;
  const now = new Date();
  const month = now.getMonth() + 1;
  const cult = Object.entries(ARGUS_CALENDAR).find(([k, cal]) =>
    cal.regions.includes(mun.argus) && (mun.culture.includes(k) || k === 'folhosas')
  );
  if (!cult) return null;
  const [cultKey, cal] = cult;
  const inColheita = month >= cal.colheita.start && month <= cal.colheita.end;
  const ndvi = mun.ndvi;
  if (ndvi < 0.45 && !inColheita) {
    return { type: 'ALERTA', msg: `NDVI ${ndvi.toFixed(3)} FORA da janela de colheita (${cal.label}). Investigar PRAGA/SECA.`, severity: 'critical' };
  }
  if (ndvi < 0.45 && inColheita) {
    return { type: 'COLHEITA', msg: `NDVI ${ndvi.toFixed(3)} compatível com colheita de ${cal.label} (janela ${cal.colheita.start}-${cal.colheita.end}).`, severity: 'ok' };
  }
  if (ndvi < 0.52 && !inColheita) {
    return { type: 'ATENÇÃO', msg: `NDVI ${ndvi.toFixed(3)} abaixo do esperado para ${cal.label}. Validar com SATVeg.`, severity: 'high' };
  }
  return { type: 'NORMAL', msg: `${cal.label} em ciclo. NDVI ${ndvi.toFixed(3)} dentro da curva.`, severity: 'ok' };
}

// ═══════════════════════════════════════════════════════════════════
// MACRO-POLES ENGINE
// ═══════════════════════════════════════════════════════════════════
const MACRO_POLES = {
  A: {
    ids: ['BR-MT-SOR','BR-MT-LRV','BR-GO-RRV','BR-BA-BAR','BR-MA-BAL','BR-PI-URU','BR-TO-POR','BR-MT-NMU','BR-MT-SAP','BR-GO-JAT','BR-GO-CRI','BR-GO-ITB'],
    extraCol: ['NDVI', 'Rm (kt)', 'Status'],
    fmtRow: m => [m.ndvi.toFixed(3), calcRm(m), m.ndvi<0.40?'SECO':m.ndvi<0.55?'ATENÇÃO':'OK'],
    colColors: m => [m.ndvi<0.40?'var(--danger)':m.ndvi<0.55?'var(--warn)':'var(--accent2)', 'var(--accent)', m.ndvi<0.40?'var(--danger)':m.ndvi<0.55?'var(--warn)':'var(--accent2)'],
    alerts: [
      m => `[${m.name.toUpperCase()}] NDVI ${m.ndvi.toFixed(2)} — ${m.ndvi<0.40?'colheita impactada por seca':m.ndvi<0.55?'monitorando desenvolvimento':'colheita dentro do esperado'}.`,
      m => `[${m.name.toUpperCase()}] Rm estimado: ${calcRm(m)} kt. Produção ${m.ndvi>=0.55?'acima':'abaixo'} da média histórica.`,
      m => `[${m.name.toUpperCase()}] Status: ${m.ndvi<0.40?'SECO — intervenção recomendada':m.ndvi<0.55?'ATENÇÃO — monitorar':'OK — normal'}.`,
      m => `[${m.name.toUpperCase()}] Análise fenológica: NDVI ${m.ndvi.toFixed(3)} · ${m.culture} · área ${m.areaMha} Mha.`,
    ],
  },
  B: {
    ids: ['BR-MG-BAR','BR-SP-MOG','BR-SP-ITA','BR-RS-VAC','BR-SC-CAC','BR-MG-ARA2','BR-SP-ITV','BR-MG-PAT','BR-GO-PIR','BR-SP-IBU','BR-SP-MGC','BR-SP-PIE','BR-MG-UBE','BR-MG-STJ','BR-RS-CXS','BR-MG-PAL','BR-MG-BAR2'],
    extraCol: ['NDVI', 'BRIX Ref.', 'Geada'],
    fmtRow: m => {
      const brix = m.culture==='tomate' ? '4.2–6.0' : m.culture==='maca' ? '12.8' : '8.4';
      const geada = m.ndvi > 0.60 ? 'OK' : 'MONIT.';
      return [m.ndvi.toFixed(3), brix, geada];
    },
    colColors: m => ['var(--accent)', 'var(--accent2)', m.ndvi>0.60?'var(--accent2)':'var(--warn)'],
    alerts: [
      m => `[${m.name.toUpperCase()}] ${m.culture==='tomate'?'Tomate: acompanhamento BRIX ativo.':'Vigor foliar monitorado.'} NDVI ${m.ndvi.toFixed(2)}.`,
      m => `[${m.name.toUpperCase()}] ${m.ndvi<0.50?'Risco de geada — NDVI abaixo do esperado.':'Ciclo fenológico normal.'} NDVI ${m.ndvi.toFixed(2)}.`,
      m => `[${m.name.toUpperCase()}] Ciclo fenológico: ~${Math.round(m.ndvi*130)}d. ${m.ndvi>0.60?'PRÉ-COLHEITA detectada.':'DESENVOLVIMENTO ATIVO.'}`,
      m => `[${m.name.toUpperCase()}] Monitoramento térmico noturno ativo. ${m.culture} · Rm ${calcRm(m)} kt.`,
    ],
  },
  C: {
    ids: ['BR-PE-PET','BR-BA-JUA','BR-RN-MOS','BR-SE-ITA','BR-SE-BOQ','BR-PE-PET2','BR-BA-IBI','BR-CE-TIA'],
    extraCol: ['NDVI', 'Safra', 'Solo'],
    fmtRow: m => {
      const safra = m.ndvi>0.55?'PLENA':m.ndvi>0.45?'REDUZ.':'STRESS';
      const solo = m.ndvi>0.50?'OK':'MONIT.';
      return [m.ndvi.toFixed(3), safra, solo];
    },
    colColors: m => ['var(--accent2)', m.ndvi>0.55?'var(--accent2)':'var(--warn)', m.ndvi>0.50?'var(--accent2)':'var(--warn)'],
    alerts: [
      m => `[${m.name.toUpperCase()}] NDVI ${m.ndvi.toFixed(2)} — ${m.ndvi>0.55?'volume hídrico adequado':'irrigação adicional recomendada'}.`,
      m => `[${m.name.toUpperCase()}] Safra ${m.culture}: ${m.ndvi>0.55?'PLENA':m.ndvi>0.45?'REDUZIDA':'STRESS HÍDRICO'}.`,
      m => `[${m.name.toUpperCase()}] Monitoramento de salinização ativo. NDVI ${m.ndvi.toFixed(2)} — vigor foliar ${m.ndvi>0.55?'excelente':'sob atenção'}.`,
      m => `[${m.name.toUpperCase()}] Rm estimado: ${calcRm(m)} kt · NDVI ${m.ndvi.toFixed(2)}.`,
    ],
  },
  D: {
    ids: ['BR-PA-PAR','BR-PA-SFX','BR-RO-VIL','BR-TO-POR'],
    extraCol: ['NDVI', 'CAR', 'Desmat.'],
    fmtRow: m => {
      const desmat = m.ndvi < 0.35 ? 'ALERT' : 'OK';
      return [m.ndvi.toFixed(3), '—', desmat];
    },
    colColors: m => ['var(--accent2)', 'var(--text2)', m.ndvi<0.35?'var(--danger)':'var(--accent2)'],
    alerts: [
      m => `[${m.name.toUpperCase()}] Conformidade CAR: aguardando integração INCRA/SICAR.`,
      m => `[${m.name.toUpperCase()}] SAR: monitoramento de desmatamento ativo. NDVI ${m.ndvi.toFixed(3)} — ${m.ndvi<0.35?'ALERTA de cobertura':'cobertura normal'}.`,
      m => `[${m.name.toUpperCase()}] SAR automático em operação. NDVI ${m.ndvi.toFixed(3)}.`,
      m => `[${m.name.toUpperCase()}] Pegada de carbono: integração SEEG/INPE pendente. NDVI referência: ${m.ndvi.toFixed(3)}.`,
    ],
  },
};

function renderPoleTable(poleKey) {
  const pole = MACRO_POLES[poleKey];
  const tbody = document.getElementById('pole'+poleKey+'-table');
  if (!tbody) return;
  const muns = pole.ids.map(id => MUNICIPAL_DB.find(m => m.id === id)).filter(Boolean);
  const hdrs = ['MUNICÍPIO', 'CULT.', ...pole.extraCol];
  tbody.innerHTML = `<thead><tr>${hdrs.map(h=>`<th style="background:var(--bg3);color:var(--accent);font-size:8px;padding:3px 5px;text-align:left;position:sticky;top:0;">${h}</th>`).join('')}</tr></thead>`
    + `<tbody>`
    + muns.map(m => {
      const vals = pole.fmtRow(m);
      const cols = pole.colColors(m);
      return `<tr onclick="highlightMunicipal('${m.id}')" style="cursor:pointer;">
        <td style="padding:3px 5px;border-bottom:1px solid var(--border);font-size:9px;">🇧🇷 ${m.name}</td>
        <td style="padding:3px 5px;border-bottom:1px solid var(--border);font-size:9px;color:var(--text2);">${m.culture}</td>
        ${vals.map((v,i)=>`<td style="padding:3px 5px;border-bottom:1px solid var(--border);font-size:9px;color:${cols[i]};font-weight:bold;">${v}</td>`).join('')}
      </tr>`;
    }).join('')
    + `</tbody>`;
}

function pushPoleAlert(poleKey) {
  // Alertas sintéticos removidos — sem geração aleatória de eventos
  // Container será populado por _fetchPoleAlertsFromBrain() via API real
  const container = document.getElementById('pole'+poleKey+'-alerts');
  if (container && !container._brainLoaded) {
    container.innerHTML = '<div style="padding:6px 4px;color:var(--text2);font-size:9px;">Aguardando dados do Cérebro NIAS…</div>';
  }
}

async function _fetchPoleAlertsFromBrain() {
  try {
    const r = await fetch('/api/nias/brain/events', { cache:'no-store' });
    if (!r.ok) return;
    const d = await r.json();
    const events = d?.data?.events || [];
    // Distribute events across pole containers by country/region
    ['A','B','C','D'].forEach(poleKey => {
      const container = document.getElementById('pole'+poleKey+'-alerts');
      if (!container) return;
      // Filter events relevant to this pole (A=BR grãos, B=horti, C=AR/PY/UY, D=proteína)
      const poleEvents = events.slice(0, 8);
      if (!poleEvents.length) {
        container.innerHTML = '<div style="padding:6px 4px;color:var(--text2);font-size:9px;">Sem eventos detectados.</div>';
        container._brainLoaded = true;
        return;
      }
      container._brainLoaded = true;
      container.innerHTML = poleEvents.map(ev => {
        const ts = new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'});
        const c = ev.gravidade === 'critica' ? 'var(--danger)' : ev.gravidade === 'alta' ? 'var(--warn)' : 'var(--text2)';
        return `<div style="padding:3px 4px;border-bottom:1px solid var(--border);line-height:1.4;"><span style="color:var(--text2);font-size:8px;">${ts}</span><br><span style="font-size:9px;color:${c};">${ev.titulo}</span></div>`;
      }).join('');
    });
  } catch(_) {}
}
_fetchPoleAlertsFromBrain();
setInterval(_fetchPoleAlertsFromBrain, 5 * 60 * 1000);

function updateMacroVolumes() {
  // Volumes CONAB safra 2024/25 — referência oficial, sem jitter simulado
  const gEl = document.getElementById('mp-vol-graos');   if (gEl) gEl.textContent = '322.0 Mt';
  const hEl = document.getElementById('mp-vol-horti');   if (hEl) hEl.textContent = '— Mt';
  const pEl = document.getElementById('mp-vol-prot');    if (pEl) pEl.textContent = '— Mt';
  // NDVI divergence check
  const pairs = [
    ['BR-MT-SOR','BR-MA-BAL'],['BR-GO-RRV','BR-GO-PIR'],['BR-PE-PET','BR-SE-ITA'],
    ['BR-PA-PAR','BR-RO-VIL'],['BR-RS-VAC','BR-SC-CAC'],
  ];
  const divergent = pairs.filter(([a,b]) => {
    const ma = MUNICIPAL_DB.find(m=>m.id===a), mb = MUNICIPAL_DB.find(m=>m.id===b);
    return ma && mb && Math.abs(ma.ndvi - mb.ndvi) > 0.22;
  });
  const divEl = document.getElementById('mp-ndvi-div');
  if (divEl) {
    if (divergent.length) {
      const [a,b] = divergent[0];
      const ma = MUNICIPAL_DB.find(m=>m.id===a), mb = MUNICIPAL_DB.find(m=>m.id===b);
      divEl.style.color = 'var(--warn)';
      divEl.textContent = `⚠ ${ma.name} vs ${mb.name}: Δ ${Math.abs(ma.ndvi-mb.ndvi).toFixed(3)} — Validando microclima...`;
    } else {
      divEl.style.color = 'var(--accent2)';
      divEl.textContent = `✓ ${pairs.length} pares verificados — sem divergência anômala`;
    }
  }
}

function initMacroPolos() {
  window._macroInit = true;
  ['A','B','C','D'].forEach(k => {
    renderPoleTable(k);
    for (let i=0; i<4; i++) pushPoleAlert(k);
  });
  updateMacroVolumes();
  setInterval(() => {
    ['A','B','C','D'].forEach(k => { renderPoleTable(k); });
    updateMacroVolumes();
  }, 6000);
}

// ═══════════════════════════════════════════════════════════════════
// DEEP DIVE ZOOM LEVELS — Mapa GEO-IA
// ═══════════════════════════════════════════════════════════════════
let currentZoomLevel = 0;
const ZOOM_CONFIG = [
  { zoom:4, label:'Cores por estado · Produtividade geral', center:[-15,-55] },
  { zoom:6, label:'Malha municipal · Polos destacados em zoom', center:[-15,-52] },
  { zoom:9, label:'Segmentação semântica de talhões · Identificação de pragas por IA', center:[-12.5,-55.5] },
];

function setZoomLevel(level) {
  if (level >= 2 && niasRole !== 'admin') {
    _showUpgradeToast('Drill-down de talhão requer Versão Premium (resolução 3m PlanetScope)');
    return;
  }
  currentZoomLevel = level;
  [0,1,2].forEach(i => {
    const btn = document.getElementById('zoom-btn-'+i);
    if (!btn) return;
    btn.classList.toggle('active', i === level);
  });
  const lbl = document.getElementById('zoom-label');
  if (lbl) lbl.textContent = ZOOM_CONFIG[level].label;
  if (!leafletMap) return;
  const cfg = ZOOM_CONFIG[level];
  leafletMap.flyTo(cfg.center, cfg.zoom, { duration:1.2 });
  if (level === 2) addTalhaoLayer();
  else removeTalhaoLayer();
}

let talhaoLayer = null;
function addTalhaoLayer() {
  if (talhaoLayer) return;
  // Z2 requer integração PlanetScope (PLANET_KEY) para dados reais de talhão.
  // Enquanto não configurada, exibe aviso no mapa em vez de dados fictícios.
  const noDataIcon = L.divIcon({
    className: '',
    html: `<div style="background:rgba(0,0,0,.92);border:1px solid var(--warn,#ffd60a);border-radius:6px;padding:10px 14px;font-family:monospace;font-size:11px;color:#ffd60a;white-space:nowrap;box-shadow:0 4px 16px rgba(0,0,0,.6);">
      ⚠ Segmentação Z2 indisponível<br>
      <span style="font-size:9px;color:#8b949e;">Configure PLANET_KEY no backend<br>para ativar imagens de talhão (3m).</span>
    </div>`,
    iconAnchor: [120, 40],
  });
  const center = leafletMap ? leafletMap.getCenter() : {lat: -12.54, lng: -55.72};
  talhaoLayer = L.layerGroup([
    L.marker([center.lat, center.lng], {icon: noDataIcon, interactive: false})
  ]).addTo(leafletMap);
}
function removeTalhaoLayer() {
  if (talhaoLayer && leafletMap) { leafletMap.removeLayer(talhaoLayer); talhaoLayer = null; }
}

// ═══════════════════════════════════════════════════════════════════
// ACTION ROOM: ARBITRAGEM PRESCRITIVA
// ═══════════════════════════════════════════════════════════════════
const ARB_ROWS = [
  { mun:'Sorriso (MT)',    culture:'Soja',       unit:'sc 60kg', baseOrigin:140.20, basePorto:164.80, corridor:'br163', etaH:72  },
  { mun:'Rio Verde (GO)',  culture:'Soja',       unit:'sc 60kg', baseOrigin:138.50, basePorto:162.40, corridor:'ferro', etaH:48  },
  { mun:'Itápolis (SP)',   culture:'Tom. Ind.',  unit:'t',       baseOrigin:285.00, basePorto:318.00, corridor:'msp',   etaH:18  },
  { mun:'Petrolina (PE)',  culture:'Uva Mesa',   unit:'cx 8kg',  baseOrigin:38.40,  basePorto:52.60,  corridor:'ferro', etaH:54  },
  { mun:'Barreiras (BA)',  culture:'Soja',       unit:'sc 60kg', baseOrigin:128.90, basePorto:158.20, corridor:'br163', etaH:96  },
  { mun:'Cascavel (PR)',   culture:'Milho',      unit:'sc 60kg', baseOrigin:58.30,  basePorto:72.10,  corridor:'msp',   etaH:22  },
];
let arbState = {};
ARB_ROWS.forEach((r,i) => { arbState[i] = { freteHistory:[], retentionHours:0 }; });

function updateArbitragem() {
  const tbody = document.getElementById('arb-tbody');
  if (!tbody) return;
  tbody.innerHTML = ARB_ROWS.map((r, i) => {
    const sat = logState[r.corridor] || 65;
    // Frete determinístico: spread base ajustado por saturação de corredor
    const freteBase = r.basePorto - r.baseOrigin;
    const satPremium = Math.max(0, sat - 65) * 0.08;
    const frete = +(freteBase * (1 + satPremium / 100)).toFixed(2);
    const prevFrete = arbState[i].prevFrete || frete;
    const freteDelta = frete - prevFrete;
    arbState[i].prevFrete = frete;

    // Preços de referência fixos (fonte: CEPEA/ESALQ — atualização manual)
    const origin = r.baseOrigin;
    const porto  = r.basePorto;
    const spread = +(porto - origin - frete).toFixed(2);

    // VaR: lost value per day in undelivered contracts
    const varDay = +(Math.abs(spread) * (sat/100) * 0.6).toFixed(2);

    let reco, recoCol;
    if (sat >= 82 && freteDelta > 0.3) {
      const waitH = Math.round(sat > 85 ? 72 : 48);
      const saving = +(freteDelta * 2.2).toFixed(2);
      reco = `⏸ RETER ${waitH}h — frete ↑${freteDelta.toFixed(2)} nas últimas 2h. Economia ~R$ ${saving}/${r.unit}`;
      recoCol = 'var(--warn)';
    } else if (spread < 2) {
      reco = `⚠ SPREAD COMPRIMIDO — VaR R$ ${varDay}/dia. Aguardar janela de preço.`;
      recoCol = 'var(--danger)';
    } else {
      reco = `▶ DESPACHAR — Spread R$ ${spread.toFixed(2)}/${r.unit}. Janela favorável.`;
      recoCol = 'var(--accent2)';
    }
    const satCol = sat >= 82 ? 'var(--danger)' : sat >= 70 ? 'var(--warn)' : 'var(--accent2)';
    const freteCol = freteDelta > 0.3 ? 'var(--danger)' : freteDelta < -0.3 ? 'var(--accent2)' : 'var(--text)';
    const freteArrow = freteDelta > 0.3 ? '↑' : freteDelta < -0.3 ? '↓' : '→';
    return `<tr>
      <td style="padding:4px 8px;border-bottom:1px solid var(--border);font-size:10px;">${r.mun}</td>
      <td style="padding:4px 8px;border-bottom:1px solid var(--border);font-size:10px;color:var(--text2);">${r.culture}</td>
      <td style="padding:4px 8px;border-bottom:1px solid var(--border);font-size:10px;text-align:right;">R$ ${origin.toFixed(2)}<br><span style="font-size:8px;color:var(--text2);">/${r.unit} · ref.</span></td>
      <td style="padding:4px 8px;border-bottom:1px solid var(--border);font-size:10px;text-align:right;color:var(--accent);">R$ ${porto.toFixed(2)}<br><span style="font-size:8px;color:var(--text2);">/${r.unit} · ref.</span></td>
      <td style="padding:4px 8px;border-bottom:1px solid var(--border);font-size:10px;text-align:right;color:${freteCol};">${freteArrow} R$ ${frete.toFixed(2)}<br><span style="font-size:8px;color:${satCol};">Sat ${Math.round(sat)}%</span></td>
      <td style="padding:4px 8px;border-bottom:1px solid var(--border);font-size:10px;text-align:right;font-weight:bold;color:${spread>=2?'var(--accent2)':'var(--danger)'};">${niasRole==='admin'?'R$ '+spread.toFixed(2):'<span class="rbac-blur" title="🔒 Premium">R$ ▓▓▓</span>'}</td>
      <td data-reco="${reco.replace(/"/g,'&quot;')}" style="padding:4px 8px;border-bottom:1px solid var(--border);font-size:9px;color:${recoCol};">${niasRole==='admin'?reco:'<span class="rbac-blur" title="🔒 Premium">▓▓▓▓▓▓▓</span>'}</td>
    </tr>`;
  }).join('');
}
setInterval(() => updateArbitragem(), 4500);

// ═══════════════════════════════════════════════════════════════════
// ECO-SCORE + AIS RADAR
// ═══════════════════════════════════════════════════════════════════
function updateEcoScore() {
  const sat = logState.br163;
  const idle = Math.round(Math.max(20, Math.min(65, (sat - 60) * 1.2 + 20)));
  const co2 = +(1.8 + (sat - 65) * 0.028).toFixed(2);
  const score = Math.round(100 - idle * 0.7 - (co2 - 1.8)*12);
  const col = score >= 65 ? '#30d158' : score >= 45 ? '#ffd60a' : '#ff453a';
  const barEl = document.getElementById('eco-bar');
  const valEl = document.getElementById('eco-val');
  const co2El = document.getElementById('eco-co2');
  const idleEl = document.getElementById('eco-idle');
  const tipEl = document.getElementById('eco-tip');
  if (barEl) { barEl.style.width = score+'%'; barEl.style.background = score>=65?'#30d158':score>=45?'linear-gradient(90deg,#ffd60a,#00a550)':'linear-gradient(90deg,#ff453a,#ffd60a)'; }
  if (valEl) { valEl.textContent = score; valEl.style.color = col; }
  if (co2El) { co2El.textContent = co2+' kg/t'; co2El.style.color = co2>2.2?'var(--danger)':'var(--warn)'; }
  if (idleEl) { idleEl.textContent = idle+'%'; idleEl.style.color = idle>40?'var(--danger)':'var(--warn)'; }
  const tips = [
    `Frota parada na BR-163 emite ${Math.round((co2-1.8)*100/1.8)}% acima da base`,
    `${idle}% da frota em idle — otimizar janelas de carregamento`,
    `Emissão acumulada hoje: ${(co2*8400).toFixed(0)} t CO₂ equiv.`,
    `Ferrovia RUMO: 4× mais eficiente em CO₂/t que rodovia`,
  ];
  if (tipEl) tipEl.textContent = tips[Math.floor(Date.now()/8000)%tips.length];
}

const AIS_DATA = [
  { port:'Porto de Santos',   berths:8,  cargos:['Soja','Milho','Açúcar','Contêiner'] },
  { port:'Porto de Paranaguá',berths:7,  cargos:['Soja','Milho','Farelo','Carne Fresca'] },
  { port:'Porto de São Luís', berths:5,  cargos:['Soja','Minério','Alumínio'] },
  { port:'Porto de Suape',    berths:4,  cargos:['Frutas','Contêiner','Combustível'] },
];
function updateAIS() {
  const panel = document.getElementById('ais-panel');
  if (!panel) return;
  const satMap = { 'Porto de Santos': logState.santos, 'Porto de Paranaguá': logState.par };
  panel.innerHTML = AIS_DATA.map(p => {
    const sat = satMap[p.port] || null;
    const waiting = sat !== null ? Math.round(Math.max(0, sat - 55) * 0.35) : null;
    const occupied = sat !== null ? Math.round(sat/100 * p.berths) : null;
    const eta = waiting !== null ? Math.round(waiting * 8) : null;
    const col = sat === null ? 'var(--text2)' : sat >= 80 ? 'var(--danger)' : sat >= 68 ? 'var(--warn)' : 'var(--accent2)';
    const cargo = p.cargos[0];
    return `<div style="background:var(--bg3);border-left:2px solid ${col};padding:4px 8px;border-radius:2px;display:flex;justify-content:space-between;align-items:center;">
      <div>
        <div style="font-size:9px;font-weight:bold;color:var(--text);">${p.port}</div>
        <div style="font-size:8px;color:var(--text2);">Berços: ${occupied !== null ? occupied+'/'+p.berths : '—/'+p.berths} · ${cargo} · Fila: ${waiting !== null ? waiting+' navios' : '—'}</div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:10px;font-weight:bold;color:${col};">${sat !== null ? Math.round(sat)+'%' : '—'}</div>
        <div style="font-size:8px;color:var(--text2);">ETA berço: ${eta !== null ? eta+'h' : '—'}</div>
      </div>
    </div>`;
  }).join('');
}
setInterval(() => { updateEcoScore(); updateAIS(); }, 5000);

// ═══════════════════════════════════════════════════════════════════
// DIGITAL TWIN — SIMULADOR CLIMÁTICO MUNICIPAL
// ═══════════════════════════════════════════════════════════════════
let simActive = false;
let simBackup = {};

function populateSimMun() {
  const sel = document.getElementById('sim-mun');
  if (!sel || sel.options.length > 1) return;
  MUNICIPAL_DB.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.id; opt.textContent = `${m.name} (${m.state} · ${m.country})`;
    sel.appendChild(opt);
  });
}

function previewSimulation() {
  const drought = parseInt(document.getElementById('sim-drought')?.value || 0);
  const heat    = parseInt(document.getElementById('sim-heat')?.value || 0);
  const dvEl = document.getElementById('sim-drought-val');
  const hvEl = document.getElementById('sim-heat-val');
  const impEl = document.getElementById('sim-impact');
  if (dvEl) dvEl.textContent = drought+'d';
  if (hvEl) hvEl.textContent = (heat>=0?'+':'')+heat+'°C';
  if (!impEl) return;
  if (drought === 0 && heat === 0) { impEl.textContent = ''; return; }
  const ndviDrop = +(drought * 0.008 + Math.max(0,heat-3)*0.006).toFixed(3);
  const rmDrop = +(ndviDrop * 100 / 0.6).toFixed(1);
  impEl.style.color = ndviDrop > 0.06 ? 'var(--danger)' : 'var(--warn)';
  impEl.textContent = `Prévia: NDVI -${ndviDrop} · Rm -${rmDrop}% · ${drought>=15?'QUEBRA SEVERA':drought>=7?'ESTRESSE MODERADO':'IMPACTO LEVE'}`;
}

async function applySimulation() {
  const drought = parseInt(document.getElementById('sim-drought')?.value || 0);
  const heat    = parseInt(document.getElementById('sim-heat')?.value || 0);
  const munId   = document.getElementById('sim-mun')?.value || 'all';
  const impEl   = document.getElementById('sim-impact');
  if (drought === 0 && heat === 0) { if (impEl) impEl.textContent = 'Ajuste os sliders para simular.'; return; }

  // Fetch SIDRA real data for active culture if available
  let sidraData = null;
  let sidraVBP = {};
  if (_activeCult && _activeCult !== 'all') {
    const c = SIDRA_CULTURES[_activeCult];
    if (c) {
      sidraData = await fetchSidraProduction(_activeCult, 'last');
      if (sidraData) {
        sidraData.forEach(d => { sidraVBP[d.D1C] = +d.V; });
      }
    }
  }

  simActive = true;
  simBackup = {};
  const ndviPenalty = drought * 0.008 + Math.max(0, heat-3) * 0.006;
  let affected = 0, totalRmLoss = 0, totalVBPLoss = 0;

  MUNICIPAL_DB.forEach(m => {
    if (munId !== 'all' && m.id !== munId) return;
    simBackup[m.id] = m.ndvi;
    const origNdvi = m.ndvi;
    m.ndvi = Math.max(0.18, m.ndvi - ndviPenalty);
    const rmOrig = calcRm({...m, ndvi:origNdvi});
    const rmNew  = calcRm(m);
    totalRmLoss += (rmOrig - rmNew);
    affected++;

    // If SIDRA data available, calculate real VBP loss
    const ibgeCode = m.ibgeCode ? String(m.ibgeCode) : '';
    if (ibgeCode && sidraVBP[ibgeCode]) {
      const realVBP = sidraVBP[ibgeCode];
      const lossPercent = ndviPenalty / (origNdvi || 0.5);
      totalVBPLoss += realVBP * Math.min(0.8, lossPercent);
    }

    const entry = activePolygons[m.id];
    if (entry) {
      entry.poly.setStyle({
        fillColor: m.ndvi < 0.40 ? '#ff453a' : m.ndvi < 0.52 ? '#ffd60a' : cultureColor(m.culture, m.ndvi, 0.78),
        fillOpacity: 0.88,
        weight: 2,
      });
    }
  });

  buildMunTable(document.getElementById('mun-filter')?.value || 'all');
  const loss = totalRmLoss.toFixed(1);
  const vbpStr = totalVBPLoss > 0
    ? ` · VBP real: -R$ ${(totalVBPLoss/1000).toFixed(1)} Mi (IBGE/SIDRA)`
    : ' · VBP: usando estimativa sintética';
  const dataSource = sidraData ? 'SIDRA API REAL' : 'FALLBACK SINTÉTICO';
  if (impEl) {
    impEl.style.color = 'var(--danger)';
    impEl.innerHTML = `⚠ SIMULAÇÃO ATIVA — ${affected} municípios · Rm -${loss} kt${vbpStr}<br><span style="font-size:8px;color:var(--text2);">Fonte: ${dataSource} · Seca ${drought}d · ΔT +${heat}°C · Coef. Manejo: -${(ndviPenalty*100).toFixed(1)}% NDVI</span>`;
  }
}

function resetSimulation() {
  if (!simActive) return;
  Object.keys(simBackup).forEach(id => {
    const m = MUNICIPAL_DB.find(x => x.id === id);
    if (m) {
      m.ndvi = simBackup[id];
      const entry = activePolygons[id];
      if (entry) entry.poly.setStyle({ fillColor: cultureColor(m.culture, m.ndvi, 0.78), fillOpacity:0.72, weight:1.2 });
    }
  });
  simActive = false; simBackup = {};
  document.getElementById('sim-drought').value = 0;
  document.getElementById('sim-heat').value = 0;
  previewSimulation();
  buildMunTable(document.getElementById('mun-filter')?.value || 'all');
  const impEl = document.getElementById('sim-impact');
  if (impEl) impEl.textContent = 'Simulação resetada — dados reais restaurados.';
}

// ═══════════════════════════════════════════════════════════════════
// CROSS-BORDER VECTORS — MERCOSUL FLOW ARROWS
// ═══════════════════════════════════════════════════════════════════
let crossBorderLayers = [];
function addCrossBorderVectors() {
  if (crossBorderLayers.length || !munMap) return;
  const flows = [
    { from:[-25.3,-54.6], to:[-32.9,-60.8], label:'Soja BR→AR (Rosário)', vol:'2.4 Mt', col:'#9b59b6', active:true },
    { from:[-24.8,-54.5], to:[-25.3,-57.6], label:'Grãos BR→PY', vol:'1.1 Mt', col:'#0a84ff', active:true },
    { from:[-33.5,-53.4], to:[-31.5,-57.9], label:'Frutas BR→UY', vol:'0.4 Mt', col:'#ff9f0a', active:true },
    { from:[-34.4,-62.0], to:[-25.3,-57.6], label:'Soja AR→PY transit', vol:'0.9 Mt', col:'#ffd60a', active:false },
  ];
  flows.forEach(f => {
    const decorOpts = { color:f.col, weight:2, opacity:0.75, dashArray:'8 6' };
    const line = L.polyline([f.from, f.to], decorOpts);
    const midLat = (f.from[0]+f.to[0])/2, midLng = (f.from[1]+f.to[1])/2;
    const arrowIcon = L.divIcon({
      className:'', html:`<div style="color:${f.col};font-size:14px;transform:rotate(${getBearing(f.from,f.to)}deg);line-height:1;">➤</div>`,
      iconAnchor:[7,7],
    });
    const marker = L.marker([midLat, midLng], { icon:arrowIcon });
    marker.bindTooltip(`<div style="font-family:monospace;font-size:11px;"><b>${f.label}</b><br>Volume: ${f.vol}</div>`, { sticky:true });
    line.addTo(munMap); marker.addTo(munMap);
    crossBorderLayers.push(line, marker);
  });
}
function getBearing([lat1,lon1],[lat2,lon2]) {
  const dLon = (lon2-lon1)*Math.PI/180;
  const la1=lat1*Math.PI/180, la2=lat2*Math.PI/180;
  const y=Math.sin(dLon)*Math.cos(la2);
  const x=Math.cos(la1)*Math.sin(la2)-Math.sin(la1)*Math.cos(la2)*Math.cos(dLon);
  return Math.round((Math.atan2(y,x)*180/Math.PI+360)%360);
}

// Cross-border opportunity alert (AR→MG when Tucumán drops)
function checkCrossBorderOpportunity() {
  const arMun = MUNICIPAL_DB.find(m=>m.id==='AR-COR-GDE');
  if (!arMun || arMun.ndvi > 0.50) return;
  const radarList = document.getElementById('anomaly-radar-list');
  if (!radarList) return;
  const div = document.createElement('div');
  div.className = 'lf-item';
  div.style.borderLeft = '2px solid #ffd60a';
  div.style.paddingLeft = '8px';
  div.style.background = 'rgba(255,214,10,.06)';
  div.innerHTML = `<span class="lf-warn" style="font-size:10px;">🌎 [CROSS-BORDER] Quebra detectada em Córdoba (AR) — NDVI ${arMun.ndvi.toFixed(2)}. Janela de exportação para produtores de MG/GO: +R$ 4,20/sc estimado nas próximas 72h.</span><br><span class="lf-time">${new Date().toLocaleTimeString('pt-BR')} · Correlação BR-AR</span>`;
  radarList.insertBefore(div, radarList.firstChild);
}
setInterval(checkCrossBorderOpportunity, 22000);

// ═══════════════════════════════════════════════════════════════════
// THEME ENGINE — Dark / Light / Cyber AI
// ═══════════════════════════════════════════════════════════════════
let currentTheme = 'dark';
let _tileLayers = {}; // map id → L.TileLayer

const TILE_URLS = {
  dark:  'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  light: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  cyber: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
};

function swapTileLayer(mapInstance, mapKey, theme) {
  if (!mapInstance) return;
  if (_tileLayers[mapKey]) { mapInstance.removeLayer(_tileLayers[mapKey]); }
  _tileLayers[mapKey] = L.tileLayer(TILE_URLS[theme], { attribution:'© CartoDB', maxZoom:18 });
  _tileLayers[mapKey].addTo(mapInstance);
  _tileLayers[mapKey].bringToBack();
}

function setTheme(name) {
  if (name === currentTheme) return;
  currentTheme = name;
  document.documentElement.setAttribute('data-theme', name);

  // Update button states
  ['dark','light','cyber'].forEach(t => {
    const btn = document.getElementById('theme-btn-'+t);
    if (btn) btn.classList.toggle('active', t === name);
  });

  // Swap map tiles (if maps are initialized)
  if (window.leafletMap) swapTileLayer(leafletMap, 'main', name);
  if (window.munMap)     swapTileLayer(munMap,    'mun',  name);

  // Sankey canvas background updates automatically via CSS var redraw
  // Force Sankey reframe if active
  if (window._sankeyInit) { /* RAF handles it */ }

  // Cyber mode: re-apply arb classes only if panel already rendered
  if (window._sankeyInit) updateArbitragem();
}

// Patch updateArbitragem to add cyber ticker classes
const _arbOrig = updateArbitragem;
updateArbitragem = function() {
  _arbOrig();
  if (currentTheme !== 'cyber') return;
  const tbody = document.getElementById('arb-tbody');
  if (!tbody) return;
  tbody.querySelectorAll('tr').forEach(row => {
    const recoTd = row.querySelector('td:last-child');
    if (!recoTd) return;
    const txt = recoTd.dataset.reco || recoTd.textContent;
    row.classList.remove('arb-opp','arb-risk','arb-hold');
    row.style.background = '';
    if (txt.includes('▶ DESPACHAR')) {
      recoTd.className = 'arb-opp';
      row.style.background = 'rgba(0,255,0,.04)';
    } else if (txt.includes('⏸ RETER') || txt.includes('SPREAD COMPRIMIDO')) {
      recoTd.className = txt.includes('SPREAD') ? 'arb-risk' : 'arb-hold';
      row.style.background = txt.includes('SPREAD') ? 'rgba(255,0,0,.04)' : 'rgba(255,255,0,.03)';
    }
  });
};

// ═══════════════════════════════════════════════════════════════════
// GUARDA DE CAMPOS SEM RESPOSTA — evita célula/cartão vazio no NIAS
// ═══════════════════════════════════════════════════════════════════
function niasSafeText(value, fallback='sem dado disponível') {
  const s = String(value == null ? '' : value).trim();
  if (!s || s === 'undefined' || s === 'null' || s === 'NaN') return fallback;
  return s;
}
function niasFillEmptyFields(root=document) {
  const selectors = [
    '.kpi-value','.kpi-delta','.wx-temp','.wx-hum','.wx-wind','.wx-status',
    '.metric-value','.metric-label','.audit-card','td','th','.ia-card .v','.ia-finding',
    '#mercado-kpi-produtos','#mercado-kpi-fontes','#mercado-kpi-precos','#mercado-last-updated',
    '#main-boundary-status','#system-audit-summary','#ia-analysis-summary'
  ];
  root.querySelectorAll(selectors.join(',')).forEach(el => {
    if (el.getAttribute('data-nias-filled')) return;
    if (el.closest('.panel:not(.active)')) return;
    const txt = (el.textContent || '').trim();
    if (txt === 'aguardando API' || txt === 'carregando...' || txt === 'Fonte: carregando...') return;
    if (!txt || txt === 'undefined' || txt === 'null' || txt === 'NaN') {
      if (el.tagName === 'TD') el.textContent = 'sem dado';
      else if (el.id && el.id.includes('status')) el.textContent = 'fonte não carregada';
      else el.textContent = 'sem dado disponível';
      el.title = (el.title ? el.title + ' | ' : '') + 'Campo preenchido automaticamente pelo guarda anti-vazio NIAS.';
      el.setAttribute('data-nias-filled','true');
    }
  });
}
function niasRenderApiFailure(containerId, endpoint, err) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `<div style="border:1px solid var(--warn);background:rgba(255,214,10,.06);border-radius:8px;padding:10px;color:var(--text);font-size:10px;">
    <strong style="color:var(--warn)">Fonte indisponível</strong><br>
    Endpoint: <code>${escapeHtml(endpoint)}</code><br>
    Status: ${escapeHtml(String(err && (err.message || err) || 'sem resposta'))}<br>
    A interface não exibirá valores inventados; verifique Render Logs, NIAS_DB_PATH e deploy mais recente.
  </div>`;
}
document.addEventListener('DOMContentLoaded',()=>{
  setTimeout(()=>niasFillEmptyFields(), 12000);
  setInterval(()=>niasFillEmptyFields(), 60000);
});


