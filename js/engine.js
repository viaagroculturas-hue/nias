/* NiasOS — Geographic Intelligence Operating System
   Nokia → iPhone moment. The map IS the intelligence.
   Signals float over the geography where they live.
   You don't navigate to data. Data navigates to you. */
var NiasOS = (function() {
  'use strict';

  // ── Geographic anchors for SA agricultural regions ────────────────
  const GEO = {
    'BR-MT': [-13.0, -55.0],   // Mato Grosso — soja/algodão
    'BR-PR': [-24.5, -51.5],   // Paraná — soja/milho/trigo
    'BR-RS': [-29.5, -52.8],   // Rio Grande do Sul — soja/arroz
    'BR-GO': [-15.5, -49.5],   // Goiás — grãos/cana
    'BR-MA': [ -5.5, -44.5],   // MATOPIBA — fronteira agrícola
    'BR-BA': [-12.5, -41.5],   // Bahia Oeste — soja/algodão
    'BR-MG': [-19.5, -44.5],   // Minas Gerais — café/hortifruti
    'BR-SP': [-22.0, -49.0],   // São Paulo — cana/laranja
    'AR':    [-33.0, -63.0],   // Pampas Argentina — trigo/soja
    'CL':    [-34.5, -71.0],   // Chile Central — frutas/vinho
    'CO':    [  4.5, -74.0],   // Colombia — café/flores
    'PE':    [-10.0, -76.5],   // Peru — quinoa/aspargo
    'BO':    [-16.5, -63.5],   // Bolívia Santa Cruz — soja
    'PY':    [-23.5, -57.5],   // Paraguai — soja
    'UY':    [-32.5, -56.0],   // Uruguai — arroz/carne
    'EC':    [ -1.5, -78.5],   // Equador — banana/cacau
  };

  // ── Signal color palette ──────────────────────────────────────────
  const COLORS = {
    critica:          { border:'#ef4444', glow:'rgba(239,68,68,0.55)',  dot:'#ef4444', badge:'rgba(239,68,68,0.2)',  text:'#ef4444' },
    alta:             { border:'#f59e0b', glow:'rgba(245,158,11,0.45)', dot:'#f59e0b', badge:'rgba(245,158,11,0.15)', text:'#f59e0b' },
    media:            { border:'#3b82f6', glow:'rgba(59,130,246,0.35)', dot:'#3b82f6', badge:'rgba(59,130,246,0.15)', text:'#3b82f6' },
    baixa:            { border:'#22c55e', glow:'rgba(34,197,94,0.3)',   dot:'#22c55e', badge:'rgba(34,197,94,0.15)', text:'#22c55e' },
    comprar:          { border:'#30d158', glow:'rgba(48,209,88,0.45)',  dot:'#30d158', badge:'rgba(48,209,88,0.15)', text:'#30d158' },
    antecipar_compra: { border:'#22c55e', glow:'rgba(34,197,94,0.4)',   dot:'#22c55e', badge:'rgba(34,197,94,0.15)', text:'#22c55e' },
    alerta:           { border:'#ef4444', glow:'rgba(239,68,68,0.45)',  dot:'#ef4444', badge:'rgba(239,68,68,0.15)', text:'#ef4444' },
    monitorar:        { border:'#ffd60a', glow:'rgba(255,214,10,0.35)',  dot:'#ffd60a', badge:'rgba(255,214,10,0.12)', text:'#ffd60a' },
    segurar:          { border:'rgba(235,235,245,0.6)', glow:'rgba(106,146,176,0.3)', dot:'rgba(235,235,245,0.6)', badge:'rgba(106,146,176,0.1)','text':'rgba(235,235,245,0.6)' },
  };

  const GLYPHS = {
    critica:'🔴', alta:'🟡', media:'🔵', baixa:'🟢',
    comprar:'🟢', antecipar_compra:'🟢', alerta:'🔴', monitorar:'🟡', segurar:'⚪'
  };

  const PANEL_LABELS = {
    overview:'PULSO', brain:'CÉREBRO', advisor:'RADAR', map:'MAPA VIVO',
    oferta:'PREÇOS', biocommand:'CLIMA', logistica:'LOGÍSTICA',
    situation:'FONTES', warroom:'WAR ROOM'
  };

  // ── State ─────────────────────────────────────────────────────────
  let _booted      = false;
  let _markers     = [];
  let _activeSheet = null;
  let _ribbonMsgs  = [];
  let _ribbonIdx   = 0;

  // ── Helpers ───────────────────────────────────────────────────────
  const _esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const $ = id => document.getElementById(id);

  // ── BOOT ─────────────────────────────────────────────────────────
  // Estratégia: NÃO mover painéis no DOM.
  // #main vira o canvas full-screen via CSS (position:fixed; top:0; bottom:60px).
  // panel-map fica dentro de #main como position:relative; flex:1 — Leaflet
  // mede o container DEPOIS do CSS ser pintado e recebe tamanho correto.
  function _dbg() {}

  function boot() {
    if (_booted) return;
    _booted = true;

    document.body.classList.add('nias-os-mode');
    const dock = $('os-dock');
    if (dock) dock.style.display = 'flex';

    // Usa setTimeout(400ms) em vez de rAF — mais confiável para layout ter
    // sido calculado antes do Leaflet medir o container
    setTimeout(_activateMapCanvas, 400);

    setTimeout(_firstLoad, 2500);
    setInterval(loadSignals, 180000);
  }

  function _activateMapCanvas() {
    const mp     = document.getElementById('panel-map');
    const mapDiv = document.getElementById('map');

    // ── 1. Força visibilidade e dimensão do panel-map ─────────────────
    if (mp) {
      const headerH = (function() {
        // Calcula a altura real dos headers somando os elementos do DOM
        const tb = document.getElementById('topbar');
        const pt = document.getElementById('price-ticker');
        const fb = document.getElementById('failsafe-bar');
        return (tb ? tb.offsetHeight : 28) +
               (pt ? pt.offsetHeight : 20) +
               (fb ? fb.offsetHeight : 18);
      })();
      const dockH  = 68;
      const panelH = Math.max(300, window.innerHeight - headerH - dockH);

      mp.style.display    = 'flex';
      mp.style.visibility = 'visible';
      mp.style.opacity    = '1';
      mp.style.position   = 'relative';
      mp.style.width      = '100%';
      mp.style.height     = panelH + 'px';
      mp.style.minHeight  = panelH + 'px';
      mp.style.overflow   = 'hidden';
      mp.style.flex       = '1 1 auto';
      mp.classList.add('active');

      _dbg('panel-map: ' + mp.offsetWidth + 'x' + mp.offsetHeight +
           '\n#map antes init: ' + (mapDiv ? mapDiv.offsetWidth + 'x' + mapDiv.offsetHeight : 'N/A') +
           '\nheaderH=' + headerH + ' dockH=' + dockH + ' panelH=' + panelH +
           '\nL definido: ' + (typeof L !== 'undefined') +
           '\n_mapInit: ' + !!window._mapInit);
    } else {
      _dbg('ERRO: panel-map nao encontrado!');
      return;
    }

    // ── 2. Inicializa o mapa ──────────────────────────────────────────
    if (!window._mapInit) {
      window._mapInit = true;
      try {
        initMap();
        _dbg('initMap() OK\nleafletMap: ' + (window.leafletMap ? 'criado' : 'FALHOU') +
             '\n#map apos init: ' + (mapDiv ? mapDiv.offsetWidth + 'x' + mapDiv.offsetHeight : 'N/A'));
      } catch(e) {
        window._mapInit = false;
        _dbg('initMap() ERRO:\n' + e.message + '\n' + (e.stack || '').split('\n')[0]);
      }
    } else {
      _dbg('_mapInit ja true — leafletMap: ' + (window.leafletMap ? 'existe' : 'null'));
    }

    // ── 3. Cascata invalidateSize ─────────────────────────────────────
    const inv = () => {
      try {
        if (window.leafletMap) {
          leafletMap.invalidateSize(true);
          // Atualiza debug com dimensões pos-invalidate
          const c = leafletMap.getContainer();
          _dbg('invalidateSize OK\ncontainer: ' + c.offsetWidth + 'x' + c.offsetHeight +
               '\nleafletMap: ' + (window.leafletMap ? 'ativo' : 'null'));
        }
      } catch(e) { _dbg('invalidateSize erro: ' + e.message); }
    };
    [150, 400, 800, 1600].forEach(d => setTimeout(inv, d));

    setTimeout(() => {
      try {
        if (window.leafletMap) {
          leafletMap.invalidateSize(true);
          leafletMap.panBy([0, 0], { animate: false });
        }
      } catch(e) {}
    }, 900);
  }

  function _firstLoad() {
    loadSignals();
    _loadRibbon();
  }

  // ── SIGNAL LOADING ───────────────────────────────────────────────
  function loadSignals() {
    Promise.all([
      fetch('/api/nias/brain/events?limit=8',    {cache:'no-store'}).then(r=>r.json()).catch(()=>null),
      fetch('/api/nias/brain/decisions?limit=6', {cache:'no-store'}).then(r=>r.json()).catch(()=>null),
      fetch('/api/nias/brain/pulse',             {cache:'no-store'}).then(r=>r.json()).catch(()=>null),
    ]).then(([evR, dcR, pulseR]) => {
      const events    = evR?.data?.events      || [];
      const decisions = dcR?.data?.decisions   || [];
      const pulse     = pulseR?.data           || null;
      _renderSignals(events, decisions);
      _updateLiveText(pulse, events, decisions);
      _updateRibbonFromData(events, decisions, pulse);
    }).catch(() => {
      _renderFallbackSignals();
    });
  }

  function _resolveLatLng(item) {
    if (item.lat  && item.lng) return [parseFloat(item.lat), parseFloat(item.lng)];
    if (item.lat  && item.lon) return [parseFloat(item.lat), parseFloat(item.lon)];
    const pais   = (item.pais   || item.country || '').toUpperCase();
    const regiao = (item.regiao || '').toUpperCase();
    // Try full region key first (e.g. BR-MT), then country prefix
    const key = Object.keys(GEO).find(k =>
      regiao.includes(k.replace('BR-','')) || k === pais || k.startsWith(pais + '-')
    );
    return key ? GEO[key] : null;
  }

  function _renderSignals(events, decisions) {
    // Remove old markers
    _markers.forEach(m => { try { m.remove(); } catch(e){} });
    _markers = [];
    if (!window.leafletMap) return;

    const seen = new Set();

    events.slice(0,6).forEach(ev => {
      const ll = _resolveLatLng(ev);
      if (!ll) return;
      const key = ll[0].toFixed(1) + ',' + ll[1].toFixed(1);
      if (seen.has(key)) return; seen.add(key);
      const c = COLORS[ev.gravidade] || COLORS.media;
      const g = GLYPHS[ev.gravidade] || '🔵';
      const m = _makeMarker(ll, {
        c, g,
        title: ev.titulo || ev.tipo || 'Evento SA',
        desc:  (ev.descricao || ev.tipo || '').slice(0, 65),
        badge: (ev.gravidade || 'info').toUpperCase(),
        action: () => showSheet('overview', 'PULSO'),
      });
      _markers.push(m);
    });

    decisions.slice(0,4).forEach(dc => {
      const ll = _resolveLatLng(dc);
      if (!ll) return;
      const jitter = [(Math.random()-.5)*1.5, (Math.random()-.5)*1.5];
      const jll = [ll[0]+jitter[0], ll[1]+jitter[1]];
      const key = jll[0].toFixed(1) + ',' + jll[1].toFixed(1);
      if (seen.has(key)) return; seen.add(key);
      const c = COLORS[dc.tipo] || COLORS.monitorar;
      const g = GLYPHS[dc.tipo] || '🟡';
      const m = _makeMarker(jll, {
        c, g,
        title: dc.titulo || dc.produto || 'Oportunidade',
        desc:  (dc.tese || dc.justificativa || '').slice(0, 65),
        badge: (dc.tipo || '').replace('_',' ').toUpperCase(),
        action: () => showSheet('advisor', 'RADAR'),
      });
      _markers.push(m);
    });

    if (_markers.length === 0) _renderFallbackSignals();
  }

  function _makeMarker(latlng, opts) {
    const { c, g, title, desc, badge, action } = opts;
    const dotAnim = (c.dot === '#ef4444' || c.dot === '#f59e0b') ? ' os-sig-dot-pulse' : '';
    const html = `
      <div class="os-sig os-sig-glow" style="
        border-color:${c.border};
        box-shadow:0 0 14px ${c.glow},0 2px 10px rgba(0,0,0,.7);
        --glow-base:0 0 10px ${c.glow};
        --glow-peak:0 0 22px ${c.glow},0 0 40px ${c.glow};
      ">
        <div class="os-sig-dot${dotAnim}" style="background:${c.dot};"></div>
        <div class="os-sig-glyph">${g}</div>
        <div class="os-sig-body">
          <div class="os-sig-title">${_esc(title)}</div>
          <div class="os-sig-desc">${_esc(desc)}${desc.length>=65?'…':''}</div>
          <span class="os-sig-badge" style="background:${c.badge};color:${c.text};">${_esc(badge)}</span>
        </div>
      </div>`;
    const icon = L.divIcon({ html, className:'', iconSize:[0,0], iconAnchor:[-4,20] });
    const marker = L.marker(latlng, { icon }).addTo(window.leafletMap);
    marker.on('click', () => {
      try { if (window.leafletMap) window.leafletMap.flyTo(latlng, 6, { duration: 1.2, easeLinearity: 0.1 }); } catch(e) {}
      if (action) action();
    });
    return marker;
  }

  function _renderFallbackSignals() {
    if (!window.leafletMap) return;
    const fallback = [
      { ll:[-13,-55], tipo:'comprar',  title:'Soja — Mato Grosso',     desc:'Janela de pré-venda safra 26/27',         badge:'COMPRAR',  action:()=>showSheet('advisor','RADAR') },
      { ll:[-24,-51], tipo:'critica',  title:'Risco Geada — Paraná',   desc:'Temperaturas críticas próximas 48h',      badge:'CRÍTICO',  action:()=>showSheet('overview','PULSO') },
      { ll:[-33,-63], tipo:'monitorar',title:'Milho — Argentina',       desc:'Safra acima do esperado, exportações ↑',  badge:'MONITORAR',action:()=>showSheet('overview','PULSO') },
      { ll:[-5,-45],  tipo:'alta',     title:'MATOPIBA — Seca',         desc:'Déficit hídrico na fronteira agrícola',   badge:'ALERTA',   action:()=>showSheet('overview','PULSO') },
      { ll:[-17,-63], tipo:'antecipar_compra', title:'Soja — Bolívia',  desc:'Preços abaixo da média histórica 5y',    badge:'OPORTUNIDADE', action:()=>showSheet('advisor','RADAR') },
    ];
    fallback.forEach(f => {
      const c = COLORS[f.tipo] || COLORS.monitorar;
      const g = GLYPHS[f.tipo] || '🟡';
      const m = _makeMarker(f.ll, { c, g, title:f.title, desc:f.desc, badge:f.badge, action:f.action });
      _markers.push(m);
    });
  }

  // ── LIVE TEXT UPDATE ─────────────────────────────────────────────
  function _updateLiveText(pulse, events, decisions) {
    const liveEl = $('os-live-text');
    if (!liveEl) return;
    const critCount = events.filter(e => e.gravidade === 'critica').length;
    const oppCount  = decisions.filter(d => d.tipo === 'comprar' || d.tipo === 'antecipar_compra').length;
    const parts = [];
    if (critCount > 0) parts.push(`${critCount} ALERTA${critCount>1?'S':''} CRÍTICO${critCount>1?'S':''}`);
    if (oppCount  > 0) parts.push(`${oppCount} OPORTUNIDADE${oppCount>1?'S':''}`);
    if (pulse?.system_health) parts.push('SISTEMA ' + String(pulse.system_health).toUpperCase());
    liveEl.textContent = parts.length > 0 ? parts.join(' · ') : 'NIAS OS · INTELIGÊNCIA ATIVA';
  }

  // ── INTELLIGENCE RIBBON ──────────────────────────────────────────
  function _loadRibbon() {
    fetch('/api/nias/brain/pulse', {cache:'no-store'}).then(r=>r.json()).then(data => {
      const d = data?.data || {};
      const msgs = [];
      if (d.market_summary) msgs.push('MERCADO: ' + d.market_summary);
      if (d.climate_summary) msgs.push('CLIMA: ' + d.climate_summary);
      if (d.top_opportunity) msgs.push('OPORTUNIDADE: ' + d.top_opportunity);
      if (d.top_risk) msgs.push('RISCO: ' + d.top_risk);
      if (msgs.length > 0) _setRibbonText(msgs.join('   ·   '));
    }).catch(() => {
      _setRibbonText('NIAS OS ATIVO · Soja MT monitorada · Clima SA em análise · 42 polos agrocomerciais online · América do Sul em tempo real');
    });
  }

  function _updateRibbonFromData(events, decisions, pulse) {
    const parts = [];
    events.slice(0,3).forEach(e => { if (e.titulo) parts.push('⚡ ' + e.titulo); });
    decisions.slice(0,2).forEach(d => { if (d.titulo || d.produto) parts.push('◈ ' + (d.titulo || d.produto) + (d.tipo ? ' [' + d.tipo.toUpperCase() + ']' : '')); });
    if (pulse?.market_summary) parts.push('📊 ' + pulse.market_summary);
    if (parts.length > 0) _setRibbonText(parts.join('   ·   '));
  }

  function _setRibbonText(txt) {
    const el = $('os-ribbon-text');
    if (el) el.textContent = txt + '   ';
  }

  // ── SHEET SYSTEM ─────────────────────────────────────────────────
  function showSheet(id, label) {
    if (_activeSheet === id) { closeSheet(); return; }

    // Close any open sheet first
    if (_activeSheet) _doClose();

    _activeSheet = id;
    label = label || PANEL_LABELS[id] || id.toUpperCase();

    // Mark all dock buttons inactive, activate this one
    document.querySelectorAll('.os-btn').forEach(b => b.classList.remove('os-active'));
    const btn = $('os-btn-' + id) || $('os-btn-' + id.split('command')[0]);
    if (btn) btn.classList.add('os-active');

    // Show the sheet title bar first
    const bar = $('os-sheet-bar');
    if (bar) {
      const titleEl = $('os-sheet-bar-title');
      if (titleEl) titleEl.textContent = '⬡ ' + label;
      bar.classList.add('visible');
    }

    // Trigger panel init via showPanel — showPanel agora aplica os-sheet-open
    // e NÃO redireciona de volta para cá (loop eliminado)
    try { window.showPanel && showPanel(id); } catch(e) {
      // Fallback: ativa panel diretamente
      const panel = $('panel-' + id);
      if (panel) panel.classList.add('active', 'os-sheet-open');
    }

    // Scroll sheet to top
    const panel = $('panel-' + id);
    setTimeout(() => { if (panel) panel.scrollTop = 0; }, 50);
  }

  function closeSheet() { _doClose(); }

  function _doClose() {
    if (_activeSheet) {
      const panel = $('panel-' + _activeSheet);
      if (panel) panel.classList.remove('os-sheet-open');
    }
    _activeSheet = null;
    document.querySelectorAll('.os-btn').forEach(b => b.classList.remove('os-active'));
    const bar = $('os-sheet-bar');
    if (bar) bar.classList.remove('visible');
    // Re-focus the map
    setTimeout(() => { try { window.leafletMap && leafletMap.invalidateSize(); } catch(e){} }, 200);
  }

  // ── COMMAND BAR ─────────────────────────────────────────────────
  function ask(text) {
    const q = text.trim();
    if (!q) return;
    const out = $('os-cmd-response');
    if (out) out.textContent = '⚙ Processando…';

    fetch('/api/nias/brain/command', {
      method:  'POST',
      headers: {'Content-Type':'application/json'},
      body:    JSON.stringify({ command: q }),
    })
    .then(r => r.json())
    .then(data => {
      const resp = data?.data?.response || data?.data?.message || data?.message || '';
      if (out) out.textContent = resp ? '◉ ' + resp.slice(0, 160) : '◉ Sem resposta disponível.';
    })
    .catch(() => {
      // Local knowledge fallback
      const ql = q.toLowerCase();
      let answer = '◉ Consulte o Cérebro NIAS para análise completa.';
      if (/soja/.test(ql))             answer = '◉ Soja: monitoramento ativo em MT, PR, RS. Toque o mapa para detalhes por polo.';
      else if (/milho/.test(ql))       answer = '◉ Milho: mercado SA em observação. Argentina e Brasil principais exportadores.';
      else if (/geada|frio/.test(ql))  answer = '◉ Clima Sul: risco de geada monitorado no PR e RS nas próximas 48h.';
      else if (/seca/.test(ql))        answer = '◉ MATOPIBA: déficit hídrico acima de 20%. Acompanhe o painel CLIMA.';
      else if (/logística|porto/.test(ql)) answer = '◉ Logística: 12 portos SA monitorados. Santos com capacidade normal.';
      if (out) out.textContent = answer;
    });
  }

  // ── PUBLIC API ────────────────────────────────────────────────────
  return { boot, loadSignals, showSheet, closeSheet, ask };
})();
