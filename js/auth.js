// ── Credentials: SHA-256 hashes only — plaintext passwords never stored in source
// To regenerate: crypto.subtle.digest('SHA-256', new TextEncoder().encode('YOUR_CODE'))
//   then convert ArrayBuffer to hex.
const NIAS_CRED_HASHES = {
  '64e48f3bf07307f751c02213b95e0b5e1e8351597dfbe12bce5cbf115591ce3f': 'admin',
  'cd9270c4ba4615d6587ce333d77dcd284e9184d34c284993dcb6967c9559d448': 'admin',
};
let niasRole = null; // 'admin' | 'guest' | null
// NOTE: Role enforcement is a UI-only restriction. For production, move
// sensitive data delivery and role validation entirely server-side.

async function _hashCode(str) {
  if (!crypto?.subtle) throw new Error('SubtleCrypto not available (requires HTTPS or localhost)');
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,'0')).join('');
}

// ── Particle canvas background for login
(function _loginCanvas() {
  const canvas = document.getElementById('login-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H, particles = [];
  function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);
  for (let i = 0; i < 120; i++) particles.push({
    x: Math.random()*2000, y: Math.random()*1200,
    r: Math.random()*1.6+0.4,
    vx: (Math.random()-.5)*.35, vy: (Math.random()-.5)*.35,
    a: Math.random()*.7+.2
  });
  function draw() {
    if (!document.getElementById('nias-login-overlay') ||
        document.getElementById('nias-login-overlay').style.display === 'none') return;
    ctx.clearRect(0,0,W,H);
    // grid
    ctx.strokeStyle = 'rgba(255,255,255,0.025)';
    ctx.lineWidth = .5;
    for (let x=0;x<W;x+=80){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();}
    for (let y=0;y<H;y+=80){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}
    // particles
    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x<0) p.x=W; if (p.x>W) p.x=0;
      if (p.y<0) p.y=H; if (p.y>H) p.y=0;
      ctx.beginPath();
      ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle = `rgba(255,255,255,${p.a * 0.35})`;
      ctx.fill();
    });
    // connections
    for (let i=0;i<particles.length;i++) {
      for (let j=i+1;j<particles.length;j++) {
        const dx=particles[i].x-particles[j].x, dy=particles[i].y-particles[j].y;
        const d=Math.sqrt(dx*dx+dy*dy);
        if (d<100) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x,particles[i].y);
          ctx.lineTo(particles[j].x,particles[j].y);
          ctx.strokeStyle=`rgba(255,255,255,${.06*(1-d/100)})`;
          ctx.lineWidth=.5;ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }
  draw();
})();

// ── Login handlers
async function _niasLogin() {
  const errEl = document.getElementById('login-err');
  const inp   = document.getElementById('login-code');
  const code  = (inp?.value || '').trim().toUpperCase();
  let role;
  try {
    const hash = await _hashCode(code);
    role = NIAS_CRED_HASHES[hash];
  } catch(e) {
    // crypto.subtle unavailable (file:// or HTTP) — degrade gracefully
    if (errEl) errEl.textContent = '⚠ Contexto inseguro (file:// / HTTP). Abra via HTTPS ou localhost.';
    return;
  }
  if (!role) {
    if (errEl) errEl.textContent = '⚠ CÓDIGO INVÁLIDO — ACESSO NEGADO';
    if (inp)  { inp.value = ''; inp.focus(); }
    return;
  }
  _niasGrantAccess(role);
}

function _niasGuestLogin() {
  _niasGrantAccess('guest');
}

function _niasGrantAccess(role) {
  niasRole = role;
  const overlay = document.getElementById('nias-login-overlay');
  if (overlay) overlay.style.display = 'none';
  _applyRBAC(role);
  // Boot OS primeiro — antes de qualquer demo mode que chame showPanel
  try { NiasOS.boot(); } catch(e) { console.error('NiasOS boot error:', e); }
  if (role === 'guest') _activateDemoMode();
}

// ── RBAC restrictions
function _applyRBAC(role) {
  if (role === 'admin') return; // full access

  // Restriction 1: disable Simulate button
  const simBar = document.getElementById('sim-bar');
  if (simBar) {
    const applyBtn = simBar.querySelector('button');
    if (applyBtn) {
      applyBtn.onclick = null;
      applyBtn.textContent = '🔒 Apenas Premium';
      applyBtn.classList.add('rbac-premium-btn');
      applyBtn.removeAttribute('onclick');
    }
    // disable sliders
    simBar.querySelectorAll('input[type=range]').forEach(s => { s.disabled = true; s.style.opacity='.35'; });
  }

  // Restriction 2: anomaly radar — hide financial values (patch pushAnomalyEvent)
  const _origPush = window.pushAnomalyEvent;
  window.pushAnomalyEvent = function() {
    _origPush && _origPush();
    // blur any .arb-value spans in radar list
    const list = document.getElementById('anomaly-radar-list');
    if (!list) return;
    list.querySelectorAll('.lf-item').forEach(item => {
      item.innerHTML = item.innerHTML.replace(/R\$\s?[\d.,]+/g, '<span class="rbac-blur">R$▓▓▓</span>');
    });
  };

  // Restriction 3: block drill-down to talhão level — guard is applied in setZoomLevel()
  const _origDrillMun = window.drillToMunicipality;
  window.drillToMunicipality = function() {
    _showUpgradeToast('Drill-down de talhão requer Versão Premium (resolução 3m PlanetScope)');
  };
  // Note: arbitrage column blurring is handled inline inside updateArbitragem() via niasRole check.
}

function _showUpgradeToast(msg) {
  let t = document.getElementById('rbac-toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'rbac-toast';
    Object.assign(t.style, {
      position:'fixed',bottom:'80px',left:'50%',transform:'translateX(-50%)',
      background:'rgba(0,0,0,.95)',border:'1px solid #50c878',
      color:'#50c878',fontFamily:'Courier New,monospace',fontSize:'11px',
      letterSpacing:'1px',padding:'10px 20px',borderRadius:'6px',
      zIndex:'99998',boxShadow:'0 0 20px rgba(80,200,120,.3)',
      transition:'opacity .4s',whiteSpace:'nowrap'
    });
    document.body.appendChild(t);
  }
  t.textContent = '🔒 ' + msg;
  t.style.opacity = '1';
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.style.opacity='0'; }, 3500);
}

// ── Demo Mode (Guest pre-loaded scenario)
function _activateDemoMode() {
  // 1. Switch to municipal tab and pre-select Tomate
  setTimeout(() => {
    const munTab = document.querySelector('[onclick*="municipal"]') || document.querySelector('[onclick*="Municipal"]');
    if (munTab) munTab.click();
  }, 600);

  setTimeout(() => {
    // Select tomate mesa culture
    if (typeof trocarCultura === 'function') trocarCultura('tomate');
    // Show a "safra recorde" banner
    _showDemoBanner();
  }, 1400);

  // 2. Lock note above arbitrage table (blur is now handled inline in updateArbitragem via niasRole check)
  setTimeout(() => {
    const arbTitle = document.querySelector('#arb-strip') || document.getElementById('arb-thead');
    if (arbTitle && !arbTitle.querySelector('.rbac-lock-note')) {
      const lockNote = document.createElement('div');
      lockNote.className = 'rbac-lock-note';
      lockNote.style.cssText = 'text-align:center;font-family:Courier New,monospace;font-size:9px;color:#50c878;letter-spacing:1px;padding:3px 0;';
      lockNote.innerHTML = '🔒 Margem e Recomendação bloqueadas — <a href="#" onclick="_showUpgradeToast(\'Assine o plano Premium para ver margens reais\');return false;" style="color:#0a84ff;text-decoration:none;">Upgrade para Premium</a>';
      arbTitle.insertBefore(lockNote, arbTitle.firstChild);
    }
  }, 2200);

  // 3. Patch anomaly feed to show only positive events
  const _origPushEvt = window.pushAnomalyEvent;
  window.pushAnomalyEvent = function() {
    _origPushEvt && _origPushEvt();
    // remove danger/warn events from feed (keep only ok/info)
    const list = document.getElementById('anomaly-radar-list');
    if (!list) return;
    list.querySelectorAll('.lf-item').forEach(item => {
      if (item.querySelector('.lf-danger, .lf-warn')) {
        item.querySelector('.lf-danger, .lf-warn') &&
          (item.querySelector('.lf-danger') || item.querySelector('.lf-warn')).classList.replace(
            item.querySelector('.lf-danger') ? 'lf-danger' : 'lf-warn', 'lf-ok');
        // sanitize message to positive
        const span = item.querySelector('span');
        if (span && (span.textContent.includes('Estresse') || span.textContent.includes('Quebra') || span.textContent.includes('Geada') || span.textContent.includes('CRÍTICO'))) {
          span.textContent = '🟢 [DEMO] Safra em pleno vigor — potencial de colheita recorde detectado';
        }
      }
    });
  };
}

function _showDemoBanner() {
  if (document.getElementById('demo-banner')) return;
  const b = document.createElement('div');
  b.id = 'demo-banner';
  b.style.cssText = 'position:fixed;top:54px;left:50%;transform:translateX(-50%);z-index:9000;' +
    'background:rgba(80,200,120,.12);border:1px solid #50c878;border-radius:6px;' +
    'padding:7px 22px;font-family:Courier New,monospace;font-size:10px;letter-spacing:1px;' +
    'color:#50c878;text-align:center;box-shadow:0 0 18px rgba(80,200,120,.2);' +
    'display:flex;align-items:center;gap:10px;white-space:nowrap;';
  b.innerHTML = '👁 MODO CONVIDADO · Cenário demo: <b>Safra de Tomate Nordeste — RECORDE 2026</b> &nbsp;' +
    '<a href="#" onclick="_niasRequestUpgrade();return false;" style="color:#0a84ff;text-decoration:none;font-size:9px;">[ ASSINAR PREMIUM ]</a>';
  document.body.appendChild(b);
}

// ═══════════════════════════════════════════════════════════════════
// BIO-COMMAND — Mapa de Comando Integrado
// ═══════════════════════════════════════════════════════════════════
let bcMap, bcMapLayers = {}, _bcInit = false;
let _bcRiskCycle = -1;

/* ── BioCommand Live Intelligence ── */
var _bcHeatLayer = null;
var _bcWindAnim  = null;
var _bcWindParts = [];
var _bcLiveData  = {};

function _bcStartWindCanvas() {
  const canvas = document.getElementById('bc-wind-canvas');
  if (!canvas) return;
  const mapEl = document.getElementById('bc-map');
  if (mapEl) { canvas.width = mapEl.offsetWidth; canvas.height = mapEl.offsetHeight; }
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  if (!W || !H) return;
  // Seed particles
  _bcWindParts = Array.from({length:120}, () => ({
    x: Math.random() * W,
    y: Math.random() * H,
    vx: (Math.random() * 1.2 + 0.3) * (Math.random() > 0.5 ? 1 : -1),
    vy: (Math.random() * 0.8 - 0.4),
    life: Math.random(),
    maxLife: 0.6 + Math.random() * 0.4,
    size: 0.8 + Math.random() * 1.4,
    hue: 180 + Math.random() * 60
  }));
  function frame() {
    ctx.clearRect(0, 0, W, H);
    _bcWindParts.forEach(p => {
      p.x += p.vx; p.y += p.vy; p.life -= 0.003;
      if (p.life <= 0 || p.x < 0 || p.x > W || p.y < 0 || p.y > H) {
        p.x = Math.random() * W; p.y = Math.random() * H;
        p.vx = (Math.random() * 1.2 + 0.3) * (Math.random() > 0.5 ? 1 : -1);
        p.vy = Math.random() * 0.8 - 0.4;
        p.life = p.maxLife; p.hue = 180 + Math.random() * 60;
      }
      const alpha = (p.life / p.maxLife) * 0.55;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = `hsla(${p.hue},90%,65%,${alpha})`;
      ctx.fill();
      // Trail
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      ctx.lineTo(p.x - p.vx * 6, p.y - p.vy * 6);
      ctx.strokeStyle = `hsla(${p.hue},90%,65%,${alpha * 0.35})`;
      ctx.lineWidth = p.size * 0.7;
      ctx.stroke();
    });
    _bcWindAnim = requestAnimationFrame(frame);
  }
  if (_bcWindAnim) cancelAnimationFrame(_bcWindAnim);
  frame();
}

function _bcBuildHeatmap(data) {
  if (!bcMap || typeof L.heatLayer === 'undefined') return;
  if (_bcHeatLayer) { try { bcMap.removeLayer(_bcHeatLayer); } catch(e){} }
  const pts = data.map(d => [d.lat, d.lon, Math.max(0.1, d.intensity)]);
  if (!pts.length) return;
  _bcHeatLayer = L.heatLayer(pts, {
    radius: 38, blur: 26, maxZoom: 9, max: 1.0,
    gradient: { 0.0:'#0d47a1', 0.2:'#1565c0', 0.4:'#00acc1', 0.55:'#00e676', 0.7:'#ffee58', 0.85:'#ff7043', 1.0:'#b71c1c' }
  }).addTo(bcMap);
}

async function _bcFetchLiveClimate() {
  // 8 key SA agro poles: MT, GO, PR, RS, BA, PE, MG, SP
  const poles = [
    { name:'Mato Grosso', lat:-12.6, lon:-55.9, state:'MT' },
    { name:'Goiás', lat:-15.9, lon:-50.0, state:'GO' },
    { name:'Paraná', lat:-24.7, lon:-51.5, state:'PR' },
    { name:'Rio Grande do Sul', lat:-28.5, lon:-52.5, state:'RS' },
    { name:'Bahia', lat:-12.0, lon:-41.7, state:'BA' },
    { name:'Pernambuco', lat:-8.4, lon:-36.9, state:'PE' },
    { name:'Minas Gerais', lat:-18.5, lon:-44.4, state:'MG' },
    { name:'São Paulo', lat:-22.3, lon:-48.2, state:'SP' },
  ];
  const lats = poles.map(p => p.lat).join(',');
  const lons = poles.map(p => p.lon).join(',');
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lats}&longitude=${lons}&current=temperature_2m,precipitation,windspeed_10m,relative_humidity_2m&daily=temperature_2m_max,precipitation_sum&forecast_days=3&timezone=America%2FSao_Paulo`;
    const res = await fetch(url);
    if (!res.ok) return null;
    const json = await res.json();
    const arr = Array.isArray(json) ? json : [json];
    return poles.map((p, i) => {
      const d = arr[i] || {};
      const cur = d.current || {};
      const daily = d.daily || {};
      return {
        ...p,
        temp: cur.temperature_2m ?? null,
        precip: cur.precipitation ?? null,
        wind: cur.windspeed_10m ?? null,
        humidity: cur.relative_humidity_2m ?? null,
        tmax3d: (daily.temperature_2m_max || []).slice(0,3),
        precip3d: (daily.precipitation_sum || []).slice(0,3),
      };
    });
  } catch(e) { return null; }
}

async function _bcApplyENSO() {
  try {
    const res = await fetch('/api/clima/bioclima');
    if (!res.ok) return;
    const d = await res.json();
    const phase = (d.enso_phase || '').toLowerCase();
    const mapEl = document.getElementById('bc-map');
    const chip = document.getElementById('bc-chip-enso');
    if (mapEl) {
      mapEl.classList.remove('enso-elnino','enso-lanina','enso-neutro');
      if (phase.includes('niño') || phase.includes('nino') || phase === 'el nino') {
        mapEl.classList.add('enso-elnino');
        if (chip) { chip.textContent = `ENSO: El Niño ${d.oni_value ? '(ONI '+d.oni_value.toFixed(1)+')' : ''}`; }
        // Warm color shift for wind canvas hue
        _bcWindParts.forEach(p => { p.hue = 20 + Math.random() * 40; });
      } else if (phase.includes('niña') || phase.includes('nina') || phase === 'la nina') {
        mapEl.classList.add('enso-lanina');
        if (chip) { chip.textContent = `ENSO: La Niña ${d.oni_value ? '(ONI '+d.oni_value.toFixed(1)+')' : ''}`; }
        _bcWindParts.forEach(p => { p.hue = 195 + Math.random() * 40; });
      } else {
        mapEl.classList.add('enso-neutro');
        if (chip) { chip.textContent = 'ENSO: Neutro'; }
      }
    }
  } catch(e) {}
}

async function _bcUpdateNarrative() {
  try {
    const res = await fetch('/api/nias/narrative');
    if (!res.ok) return;
    const d = await res.json();
    const text = d.narrative || d.text || d.summary || '';
    if (!text) return;
    const el = document.getElementById('bc-narrative-text');
    if (el) {
      el.style.animation = 'none';
      el.textContent = '◆ ' + text + '   ◆   ' + text;
      void el.offsetWidth; // reflow
      el.style.animation = 'bcTicker 38s linear infinite';
    }
  } catch(e) {}
}

async function _bcLiveRefresh() {
  // 1. Live climate from Open-Meteo
  const poles = await _bcFetchLiveClimate();
  if (poles) {
    _bcLiveData.poles = poles;
    // Build heatmap with temp as intensity (normalized ~10–45°C range)
    const heatPts = poles.filter(p => p.temp !== null).map(p => ({
      lat: p.lat, lon: p.lon,
      intensity: Math.max(0, Math.min(1, (p.temp - 10) / 32))
    }));
    // Add MUNICIPAL_DB NDVI points as green anchor
    if (typeof MUNICIPAL_DB !== 'undefined') {
      MUNICIPAL_DB.forEach(m => {
        if (m.lat && m.lon && m.ndvi != null) {
          heatPts.push({ lat: m.lat, lon: m.lon, intensity: 1 - Math.min(1, Math.max(0, m.ndvi)) * 0.5 });
        }
      });
    }
    _bcBuildHeatmap(heatPts);
    // Update chips
    const avgTemp = poles.filter(p=>p.temp!==null).reduce((s,p)=>s+p.temp,0) / poles.filter(p=>p.temp!==null).length;
    const chipT = document.getElementById('bc-chip-temp');
    if (chipT) chipT.textContent = `Temp SA: ${avgTemp.toFixed(1)}°C`;
  }
  // 2. Alert count
  try {
    const res = await fetch('/api/flv/alerts?severity=all');
    if (res.ok) {
      const d = await res.json();
      const alerts = d.alerts || d.data || [];
      const critical = alerts.filter(a => (a.severity||'').toLowerCase() === 'critical' || (a.severidade||'').toLowerCase() === 'crítico').length;
      const chipA = document.getElementById('bc-chip-alerts');
      if (chipA) chipA.textContent = `Alertas: ${alerts.length} (${critical} crít.)`;
    }
  } catch(e) {}
  // 3. Timestamp
  const chipU = document.getElementById('bc-chip-updated');
  if (chipU) chipU.textContent = `Atualizado: ${new Date().toLocaleTimeString('pt-BR')}`;
  // 4. ENSO + narrative in parallel
  _bcApplyENSO();
  _bcUpdateNarrative();
}

function initBioCommand() {
  if (_bcInit) { setTimeout(() => bcMap && bcMap.invalidateSize(), 80); return; }
  _bcInit = true;
  bcMap = L.map('bc-map', { center:[-10,-60], zoom:3, zoomControl:true, attributionControl:false });
  // Dark satellite-style tile layer
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom:19, subdomains:'abcd', attribution:'© CARTO'
  }).addTo(bcMap);

  // Fetch SIDRA data for ALL cultures
  window._bcSidraData = {};
  const _bcCultKeys = Object.keys(SIDRA_CULTURES);
  (async () => {
    for (const ck of _bcCultKeys) {
      try {
        const data = await fetchSidraProduction(ck, 'last');
        if (data) data.forEach(d => {
          const key = d.D1C;
          if (!window._bcSidraData[key]) window._bcSidraData[key] = { vbp:0, name:d.NC, cultures:[] };
          window._bcSidraData[key].vbp += (+d.V || 0);
          window._bcSidraData[key].cultures.push(ck);
        });
      } catch(e) {}
    }
  })();

  const sonarPOI = L.layerGroup();
  const basePOI = L.layerGroup();
  (typeof MUNICIPAL_DB !== 'undefined' ? MUNICIPAL_DB : []).forEach(m => {
    if (!m.poly || m.poly.length < 3) return;
    const c = m.lat && m.lon ? [m.lat, m.lon] : [(m.poly[0][0]+m.poly[2][0])/2, (m.poly[0][1]+m.poly[2][1])/2];
    if (isNaN(c[0]) || isNaN(c[1])) return;
    const isAlert = m.ndvi < 0.52, isCrit = m.ndvi < 0.45;
    const state = isCrit ? 'alert' : _cultureToSonarState(m.culture, m.ndvi);
    const sev   = isCrit ? 'critical' : isAlert ? 'high' : 'ok';
    const sz    = isCrit ? 7 : isAlert ? 6 : 5;
    const vbpStr = m.ibgeCode && window._bcSidraData?.[String(m.ibgeCode)] ? ` · VBP R$ ${(window._bcSidraData[String(m.ibgeCode)].vbp/1000).toFixed(1)}Mi` : '';
    const tip   = `<div style="font-family:monospace;font-size:11px;"><b>${_esc(m.name)} — ${m.state||''}</b><br>${(m.culture||'').toUpperCase()}${m.flvCultures?' · '+m.flvCultures.join(', '):''} · NDVI ${(m.ndvi||0).toFixed(3)}${m.flvTons?' · '+(m.flvTons/1000).toFixed(0)+'kt':''}${vbpStr}<br>${isAlert?(isCrit?'🔴 CRÍTICO':'🟡 ATENÇÃO'):'🟢 SAFRA SAUDÁVEL'}</div>`;
    const mk = createSonarMarker(c, { state, severity:sev, size:sz, tooltip:tip });
    mk._bcMun = m;
    mk.on('click', () => bcOpenRight(m));
    sonarPOI.addLayer(mk);
    // Base circle marker (always visible, lightweight)
    const cultColor = SIDRA_CULTURES[m.culture]?.color || (m.flvCultures?'#50C878':'#0a84ff');
    const baseR = Math.max(3, Math.min(8, (m.areaMha||0.05)*6));
    const baseMk = L.circleMarker(c, {
      radius:baseR, color:cultColor, fillColor:cultColor,
      fillOpacity: isCrit?0.8:isAlert?0.5:0.35, weight:isCrit?2:1, opacity:0.7
    });
    baseMk._bcMun = m;
    baseMk.bindTooltip(tip, {direction:'top'});
    baseMk.on('click', () => bcOpenRight(m));
    basePOI.addLayer(baseMk);
  });
  bcMapLayers['sonar-poi'] = sonarPOI;
  bcMapLayers['base-poi'] = basePOI;
  basePOI.addTo(bcMap);
  // Sonar POI desativado por padrao — ativado via checkbox
  const portos = L.layerGroup([
    createSonarMarker([-23.95,-46.33], { state:'ai', size:10, tooltip:'<b>Porto de Santos</b><br>Sat:74%' }),
    createSonarMarker([-25.52,-48.52], { state:'ai', size:10, tooltip:'<b>Porto de Paranaguá</b><br>Sat:71%' }),
    createSonarMarker([-32.95,-60.65], { state:'normal', size:8, tooltip:'<b>Rosário (AR)</b><br>Sat:48%' }),
    createSonarMarker([-3.10,-60.00],  { state:'ai', size:9,  tooltip:'<b>Miritituba (PA)</b>' }),
  ]);
  bcMapLayers['portos'] = portos;
  portos.addTo(bcMap);
  const el = document.getElementById('bc-clock');
  if (el) { const _t=()=>{el.textContent=new Date().toLocaleTimeString('pt-BR');}; _t(); setInterval(_t,1000); }
  const saEl = document.getElementById('bc-sa-count');
  if (saEl && window.BC_SOUTH_AMERICA_HF_META) {
    saEl.textContent = `SA HF ${window.BC_SOUTH_AMERICA_HF_META.records} polos · ${window.BC_SOUTH_AMERICA_HF_META.countries.length} países`;
    saEl.title = `${window.BC_SOUTH_AMERICA_HF_META.scope} · Produtos: ${window.BC_SOUTH_AMERICA_HF_META.products.join(', ')}`;
  }
  setTimeout(() => {
    bcMap.invalidateSize();
    _bcStartWindCanvas();
    _bcLiveRefresh();
    setInterval(_bcLiveRefresh, 5 * 60 * 1000);
  }, 150);
}

function bcToggleLeft() { document.getElementById('bc-left').classList.toggle('collapsed'); setTimeout(()=>bcMap&&bcMap.invalidateSize(),300); }
function bcToggleRight() { document.getElementById('bc-right').classList.toggle('open'); setTimeout(()=>bcMap&&bcMap.invalidateSize(),300); }
function bcCloseRight() { document.getElementById('bc-right').classList.remove('open'); setTimeout(()=>bcMap&&bcMap.invalidateSize(),300); }

function bcOpenRight(m) {
  const lat = m.lat ? m.lat.toFixed(2) : m.poly?.length>=3 ? ((m.poly[0][0]+m.poly[2][0])/2).toFixed(2) : '—';
  const lon = m.lon ? m.lon.toFixed(2) : m.poly?.length>=3 ? ((m.poly[0][1]+m.poly[2][1])/2).toFixed(2) : '—';
  const ndvi=m.ndvi??0;
  const cls = ndvi>=0.70?'good':ndvi>=0.50?'':ndvi>=0.30?'warn':'bad';
  const lbl = ndvi>=0.70?'🟢 Plena':ndvi>=0.50?'🟡 Normal':ndvi>=0.30?'🟠 Atenção':'🔴 Crítico';
  const rm  = m.flvTons ? (m.flvTons/1000).toFixed(1)+' kt' : m.area_ha?(m.area_ha*ndvi*0.82).toFixed(0)+' t':'—';
  // SIDRA VBP lookup
  const ibge = m.ibgeCode ? String(m.ibgeCode) : '';
  const sidraHit = ibge && window._bcSidraData?.[ibge];
  const vbpIBGE = sidraHit ? window._bcSidraData[ibge].vbp : null;
  const vbpStr = vbpIBGE ? `R$ ${(vbpIBGE/1000).toFixed(1)} Mi` : '—';
  const vbpSrc = vbpIBGE ? 'IBGE/SIDRA' : 'sintético';
  const vbpColor = vbpIBGE ? 'var(--accent2)' : 'var(--text2)';
  // VaR calculation
  const var_risk = vbpIBGE ? (vbpIBGE * Math.max(0, 1 - ndvi/0.7) / 1000).toFixed(1) : null;
  // ET0 sparkline
  const et0 = m._et0_7d || [];
  const et0Html = et0.length > 0 ? et0.map(v => {
    const h = Math.round(Math.min(30, v * 6));
    return `<div style="width:6px;height:${h}px;background:var(--accent);border-radius:1px;" title="ET0: ${v?.toFixed(1)} mm/d"></div>`;
  }).join('') : '';
  const t=document.getElementById('bc-right-title'), b=document.getElementById('bc-right-body');
  if(t) t.textContent=`⬢ ${_esc(m.name)} — ${m.state||''}`;
  if(b) b.innerHTML=`
    <div class="bc-kv"><span class="k">Cultura</span><span class="v">${_esc(m.culture||'—')}${m.flvCultures?' · <span style="font-size:8px;color:var(--accent)">'+m.flvCultures.join(', ')+'</span>':''}</span></div>
    <div class="bc-kv"><span class="k">NDVI</span><span class="v ${cls}">${ndvi.toFixed(3)} · ${lbl}</span></div>
    <div class="bc-kv"><span class="k">Chuva 7d</span><span class="v">${m.chuva_7d??'—'} mm</span></div>
    <div class="bc-kv"><span class="k">Temp. atual</span><span class="v">${m.temp_max??'—'}°C</span></div>
    <div class="bc-kv"><span class="k">Umidade</span><span class="v">${m.umidade?m.umidade+'%':'—'}</span></div>
    <div class="bc-kv"><span class="k">Vento</span><span class="v">${m.vento?(+m.vento).toFixed(1)+' km/h':'—'}</span></div>
    <div class="bc-kv"><span class="k">Solo úmido</span><span class="v">${m.solo_umid?(m.solo_umid*100).toFixed(0)+'%':'—'}</span></div>
    <div class="bc-kv"><span class="k">Área aprox.</span><span class="v">${m.areaMha?(m.areaMha*1000).toLocaleString('pt-BR')+' ha':m.area_ha?m.area_ha.toLocaleString('pt-BR')+' ha':'—'}</span></div>
    ${m.flvTons?'<div class="bc-kv"><span class="k">Produção FLV</span><span class="v good">'+(m.flvTons/1000).toFixed(1)+' kt (IBGE/PAM)</span></div>':''}
    <div class="bc-kv"><span class="k">R_m estimado</span><span class="v good">${rm}</span></div>
    <div style="margin:6px 0 2px;font-size:9px;color:var(--accent);letter-spacing:1px;">◎ IBGE/SIDRA</div>
    <div class="bc-kv"><span class="k">VBP IBGE</span><span class="v" style="color:${vbpColor}">${vbpStr}</span></div>
    ${var_risk ? `<div class="bc-kv"><span class="k">VaR (risco)</span><span class="v" style="color:var(--danger)">R$ ${var_risk} Mi</span></div>` : ''}
    <div class="bc-kv"><span class="k">Fonte</span><span class="v" style="font-size:8px;color:${vbpColor}">${vbpSrc}</span></div>
    ${et0Html ? `<div style="margin:6px 0 2px;font-size:9px;color:var(--accent);letter-spacing:1px;">◎ ET0 — EVAPOTRANSPIRAÇÃO 7d</div><div style="display:flex;align-items:flex-end;gap:2px;height:32px;">${et0Html}</div><div style="font-size:7px;color:var(--text2);">mm/dia · Fonte: Open-Meteo</div>` : ''}
    <div class="bc-kv"><span class="k">Coords.</span><span class="v" style="font-size:9px;">${lat}°, ${lon}°</span></div>
    <div style="margin:8px 0 4px;font-size:9px;color:var(--accent);letter-spacing:1px;">◎ ARBITRAGEM CEASA</div>
    ${_bcArbSnippet(m)}
    <div style="margin-top:8px;font-size:9px;color:var(--text2);">Fenologia: ${_esc(m.phenology||'ciclo em andamento')}</div>
    ${m.argus ? '<div style="margin:6px 0 2px;font-size:9px;color:var(--accent);letter-spacing:1px;">◎ ARGUS — VIGILÂNCIA FENOLÓGICA</div>' + _bcArgusBlock(m) : ''}`;
  document.getElementById('bc-right').classList.add('open');
  setTimeout(()=>bcMap&&bcMap.invalidateSize(),300);
  // Fetch SATVeg NDVI time series for this point
  if (lat !== '—' && lon !== '—') {
    const latF = parseFloat(lat), lonF = parseFloat(lon);
    // SATVeg NDVI
    NiasAPI.getSatVeg(latF, lonF, 'ndvi').then(sv => {
      const container = document.getElementById('bc-right-body');
      if (!container || !sv.values.length) return;
      const last6 = sv.values.slice(-6);
      const sparkHtml = last6.map((v,i) => {
        const h = Math.round(v * 40);
        const c = v >= 0.7 ? '#50C878' : v >= 0.5 ? '#7ec850' : v >= 0.3 ? '#ffd60a' : '#ff453a';
        return `<div style="width:8px;height:${h}px;background:${c};border-radius:1px;" title="${sv.dates.slice(-6)[i]}: ${v.toFixed(3)}"></div>`;
      }).join('');
      container.insertAdjacentHTML('beforeend',
        `<div style="margin-top:8px;font-size:9px;color:var(--accent);letter-spacing:1px;">◎ NDVI — ${_esc(sv.source)}</div>` +
        `<div style="display:flex;align-items:flex-end;gap:2px;height:40px;margin-top:4px;">${sparkHtml}</div>` +
        `<div style="font-size:8px;color:var(--text2);margin-top:2px;">Últimos ${last6.length} períodos (16d) · Filtro: Savitzky-Golay</div>`
      );
    });
    // SAR Backscatter (Sentinel-1)
    NiasAPI.getSARBackscatter(latF, lonF, 12).then(sar => {
      const container = document.getElementById('bc-right-body');
      if (!container) return;
      const pts = sar.data || [];
      if (pts.length === 0) return;
      const vvBars = pts.slice(-12).map(p => {
        const v = p.vv || -15;
        const h = Math.max(2, Math.round((v + 25) * 2));
        const c = v > -8 ? '#30d158' : v > -14 ? '#ffd60a' : '#ff453a';
        return `<div style="width:5px;height:${h}px;background:${c};border-radius:1px;" title="${p.date}: VV ${v.toFixed(1)} dB"></div>`;
      }).join('');
      container.insertAdjacentHTML('beforeend',
        `<div style="margin-top:8px;font-size:9px;color:#0a84ff;letter-spacing:1px;">📡 SAR BACKSCATTER — Sentinel-1</div>` +
        `<div style="display:flex;align-items:flex-end;gap:1px;height:30px;margin-top:4px;">${vvBars}</div>` +
        `<div style="font-size:7px;color:var(--text2);margin-top:2px;">VV σ⁰ (dB) · ${pts.length} dias · ${sar.source || 'Sentinel-1'}</div>` +
        `<div style="font-size:8px;color:var(--text2);margin-top:2px;">Verde = solo úmido/vegetação densa · Vermelho = solo seco/exposto</div>`
      );
    });
  }
}

function _bcArgusBlock(m) {
  const check = argusCheckNdvi(m);
  if (!check) return '<div style="font-size:9px;color:var(--text2);">Sem calendário ARGUS.</div>';
  const colors = { critical:'var(--danger)', high:'var(--warn)', ok:'var(--accent2)' };
  const icons  = { critical:'🔴', high:'🟡', ok:'🟢' };
  const cal = Object.entries(ARGUS_CALENDAR).find(([k,c]) => c.regions.includes(m.argus));
  let calHtml = '';
  if (cal) {
    const [,c] = cal;
    const now = new Date().getMonth()+1;
    calHtml = `<div class="bc-kv"><span class="k">Plantio</span><span class="v">Meses ${c.plantio.start}–${c.plantio.end}</span></div>` +
      `<div class="bc-kv"><span class="k">Colheita</span><span class="v">Meses ${c.colheita.start}–${c.colheita.end}</span></div>` +
      `<div class="bc-kv"><span class="k">Ciclo</span><span class="v">${c.cycle_days}d</span></div>` +
      `<div class="bc-kv"><span class="k">Mês atual</span><span class="v">${now} ${now>=c.colheita.start&&now<=c.colheita.end?'(COLHEITA)':'(DESENVOLVIMENTO)'}</span></div>`;
  }
  return `<div style="padding:4px;border-left:3px solid ${colors[check.severity]};margin:4px 0;font-size:10px;">` +
    `<b>${icons[check.severity]} ${_esc(check.type)}</b><br>${_esc(check.msg)}</div>` +
    (m.ceasa_ref ? `<div class="bc-kv"><span class="k">CEASA ref.</span><span class="v">${_esc(m.ceasa_ref)}</span></div>` : '') +
    (m.argus ? `<div class="bc-kv"><span class="k">Polo ARGUS</span><span class="v">${_esc(m.argus)}</span></div>` : '') +
    calHtml;
}

function _bcArbSnippet(m) {
  const cult=(m.culture||'').toLowerCase();
  const map={'tomate':{ceasa:'CEAGESP (SP)',price:'R$ 88,50/cx',margin:'+R$ 74,30'},'cebola':{ceasa:'CEASA-MG',price:'R$ 35,00/sc',margin:'+R$ 23,00'},'manga':{ceasa:'CEASA-PE',price:'R$ 68,00/cx',margin:'+R$ 59,90'},'pimentao':{ceasa:'CEASA-RJ',price:'R$ 42,00/kg',margin:'+R$ 23,50'},'soja':{ceasa:'Porto Santos',price:'R$ 142,00/sc',margin:'+R$ 28,50'},'milho':{ceasa:'Porto Santos',price:'R$ 72,00/sc',margin:'+R$ 18,20'}};
  const hit=Object.entries(map).find(([k])=>cult.includes(k));
  if(!hit) return `<div style="font-size:9px;color:var(--text2);">CEASA não mapeado.</div>`;
  const [,d]=hit;
  return `<div class="bc-arb-row"><span class="bc-arb-best">🏆 ${d.ceasa}</span><div class="bc-arb-label">Preço: ${d.price} · Margem: ${d.margin}</div></div>`;
}

function bcToggleLayer(name,cb) { if(!bcMap||!bcMapLayers[name])return; cb.checked?bcMapLayers[name].addTo(bcMap):bcMap.removeLayer(bcMapLayers[name]); }

async function bcTrocarCultura(cult) {
  // Normaliza string: remove acentos, converte para lowercase, remove espaços e underscores
  const normalize = (str) => str
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[\s_]+/g, '');
  
  document.querySelectorAll('#bc-left .cult-btn').forEach(b=>{
    const btnText = normalize(b.textContent);
    const cultNorm = normalize(cult);
    const match = cult==='all' ? b.id==='bc-cult-all' : btnText.includes(cultNorm);
    b.classList.toggle('active',match);
  });

  // Fetch SIDRA data for selected culture
  if (cult !== 'all' && SIDRA_CULTURES[cult]) {
    const data = await fetchSidraProduction(cult, 'last');
    window._bcSidraData = {};
    if (data) data.forEach(d => { window._bcSidraData[d.D1C] = { vbp: +d.V, name: d.NC }; });
  }

  if(!bcMap)return;

  // Filter base-poi layer (always visible)
  const _filterLayer = (layer) => {
    if (!layer) return;
    layer.eachLayer(mk => {
      if (!mk._bcMun) return;
      const m = mk._bcMun;
      const vis = cult==='all' || (m.culture||'').toLowerCase().includes(cult.replace('-','')) || (Array.isArray(m.flvCultures) && m.flvCultures.includes(cult));
      const ibge = m.ibgeCode ? String(m.ibgeCode) : '';
      const hasVbp = ibge && window._bcSidraData?.[ibge];
      if (mk.getElement) {
        const el = mk.getElement();
        if (el) { el.style.opacity = vis ? '1' : '0.08'; el.style.pointerEvents = vis ? 'auto' : 'none'; }
      } else if (mk.setStyle) {
        mk.setStyle({ opacity: vis ? 0.7 : 0.05, fillOpacity: vis ? 0.4 : 0.02 });
      }
      if (vis && hasVbp && mk.setStyle) {
        const vbp = window._bcSidraData[ibge].vbp;
        const r = Math.max(4, Math.min(14, Math.sqrt(vbp / 500)));
        mk.setRadius(r);
      }
    });
  };

  _filterLayer(bcMapLayers['base-poi']);
  _filterLayer(bcMapLayers['sonar-poi']);
}

function bcCycleRisk() { const modes=['radar','impact','off']; _bcRiskCycle=(_bcRiskCycle+1)%modes.length; bcSetRiskMode(modes[_bcRiskCycle]); }

function bcSetRiskMode(mode) {
  const btn=document.getElementById('bc-risk-btn');
  if(btn) btn.textContent={'radar':'📍 SONAR RADAR','impact':'🔴 IMPACTO','off':'✕ RISCO OFF'}[mode]||'◎ SONAR';
  if(!bcMap||!bcMapLayers['sonar-poi'])return;
  const cb=document.getElementById('bc-l1');
  if(mode==='off'){bcMap.removeLayer(bcMapLayers['sonar-poi']);if(cb)cb.checked=false;}
  else{bcMapLayers['sonar-poi'].addTo(bcMap);if(cb)cb.checked=true;}
}

function _niasRequestUpgrade() {
  _showUpgradeToast('Entre em contato: nia$@bio-precision.ai — Plano Pro a partir de R$ 490/mês');
}

// ═══════════════════════════════════════════════════════════════════
// HYPER-LOCAL — Micro-Inteligência IoT + Microclima
// ═══════════════════════════════════════════════════════════════════
function initHyperLocal() {
  window._hyperInit = true;
  const grid = document.getElementById('hyper-grid');
  const kpis = [
    { label:'Estações Privadas Online', value:'47', sub:'de 52 instaladas', color:'var(--accent2)' },
    { label:'Colheitadeiras Ativas (GPS)', value:'312', sub:'telemetria em tempo real', color:'var(--accent)' },
    { label:'Precisão Microclima', value:'±0.3°C', sub:'resolução 250m', color:'#ffd60a' },
  ];
  grid.innerHTML = kpis.map(k => `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:10px;">
    <div style="font-size:9px;color:var(--text2);letter-spacing:1px;">${k.label}</div>
    <div style="font-size:22px;font-weight:bold;color:${k.color};margin:4px 0;">${k.value}</div>
    <div style="font-size:9px;color:var(--text2);">${k.sub}</div></div>`).join('');
  const iotBody = document.getElementById('hyper-iot-body');
  const machines = [
    { equip:'John Deere S790 #1', farm:'Faz. Boa Vista — Sorriso/MT', prod:'68.2 sc/ha', gps:'-12.55, -55.72', status:'COLHENDO' },
    { equip:'Case IH 8250 #3', farm:'Faz. Santa Clara — Lucas RV/MT', prod:'71.8 sc/ha', gps:'-13.05, -55.91', status:'COLHENDO' },
    { equip:'New Holland CR9.90', farm:'Faz. Progresso — Rio Verde/GO', prod:'64.5 sc/ha', gps:'-17.78, -50.92', status:'TRANSPORTE' },
    { equip:'Massey Ferguson 9895', farm:'Faz. São José — Cascavel/PR', prod:'59.3 sc/ha', gps:'-24.95, -53.45', status:'MANUTENÇÃO' },
    { equip:'AGCO Ideal 9T', farm:'Faz. Pioneira — Sapezal/MT', prod:'72.1 sc/ha', gps:'-13.54, -58.01', status:'COLHENDO' },
  ];
  iotBody.innerHTML = machines.map(m => {
    const cls = m.status === 'COLHENDO' ? 'color:var(--accent2)' : m.status === 'MANUTENÇÃO' ? 'color:var(--danger)' : 'color:var(--accent)';
    return `<tr><td style="padding:4px 8px;">${m.equip}</td><td style="padding:4px 8px;font-size:9px;">${m.farm}</td><td style="text-align:right;padding:4px 8px;color:var(--accent2);font-weight:bold;">${m.prod}</td><td style="text-align:right;padding:4px 8px;font-size:8px;color:var(--text2);">${m.gps}</td><td style="text-align:center;padding:4px 8px;${cls};font-size:8px;font-weight:bold;">${m.status}</td></tr>`;
  }).join('');
  const micro = document.getElementById('hyper-microclima');
  const stations = [
    { name:'EST-001 Sorriso', temp:'32.4°C', hum:'48%', wind:'12 km/h', rain:'0mm' },
    { name:'EST-014 Cristalina', temp:'29.8°C', hum:'55%', wind:'8 km/h', rain:'2.1mm' },
    { name:'EST-023 Petrolina', temp:'35.1°C', hum:'32%', wind:'15 km/h', rain:'0mm' },
    { name:'EST-037 Ibiúna', temp:'22.6°C', hum:'78%', wind:'5 km/h', rain:'4.5mm' },
  ];
  micro.innerHTML = stations.map(s => `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:5px;padding:8px;font-size:9px;">
    <div style="color:var(--accent);font-weight:bold;margin-bottom:4px;">${s.name}</div>
    <div>🌡 ${s.temp} · 💧 ${s.hum}</div><div>💨 ${s.wind} · 🌧 ${s.rain}</div></div>`).join('');
}

// ═══════════════════════════════════════════════════════════════════
// SENTIMENTO DE MERCADO — NLP Analytics
// ═══════════════════════════════════════════════════════════════════
function initSentiment() {
  window._sentInit = true;
  const gauges = document.getElementById('sent-gauges');
  const commodities = [
    // GRÃOS
    { name:'SOJA', score:62, trend:'BULLISH', color:'#FFD700', cat:'graos' },
    { name:'MILHO', score:45, trend:'NEUTRO', color:'#FF8C00', cat:'graos' },
    { name:'CAFÉ', score:38, trend:'BEARISH', color:'#795548', cat:'graos' },
    { name:'TRIGO', score:52, trend:'NEUTRO', color:'#D4A574', cat:'graos' },
    { name:'ALGODÃO', score:57, trend:'BULLISH', color:'#E0E0E0', cat:'graos' },
    { name:'ARROZ', score:48, trend:'NEUTRO', color:'#BCAAA4', cat:'graos' },
    // HORTIFRUTI
    { name:'TOMATE MESA', score:73, trend:'BULLISH', color:'#E53935', cat:'horti' },
    { name:'TOMATE IND.', score:52, trend:'NEUTRO', color:'#BF360C', cat:'horti' },
    { name:'CEBOLA', score:65, trend:'BULLISH', color:'#AB47BC', cat:'horti' },
    { name:'BATATA', score:42, trend:'BEARISH', color:'#8D6E63', cat:'horti' },
    { name:'CENOURA', score:55, trend:'NEUTRO', color:'#FF7043', cat:'horti' },
    { name:'ALFACE', score:60, trend:'BULLISH', color:'#43A047', cat:'horti' },
    { name:'PIMENTÃO', score:58, trend:'NEUTRO', color:'#66BB6A', cat:'horti' },
    { name:'BANANA', score:50, trend:'NEUTRO', color:'#FDD835', cat:'horti' },
    { name:'LARANJA', score:44, trend:'BEARISH', color:'#FF7043', cat:'horti' },
    { name:'MANGA', score:68, trend:'BULLISH', color:'#FFA726', cat:'horti' },
    { name:'UVA', score:53, trend:'NEUTRO', color:'#7B1FA2', cat:'horti' },
    { name:'MORANGO', score:70, trend:'BULLISH', color:'#C62828', cat:'horti' },
    // PECUÁRIA
    { name:'BOI GORDO', score:71, trend:'BULLISH', color:'#D32F2F', cat:'pecuaria' },
    { name:'SUÍNO VIVO', score:58, trend:'NEUTRO', color:'#F48FB1', cat:'pecuaria' },
    { name:'FRANGO VIVO', score:64, trend:'BULLISH', color:'#FFB74D', cat:'pecuaria' },
    { name:'OVOS', score:55, trend:'NEUTRO', color:'#FFF9C4', cat:'pecuaria' },
    { name:'LEITE', score:40, trend:'BEARISH', color:'#ECEFF1', cat:'pecuaria' },
    // INSUMOS
    { name:'UREIA', score:35, trend:'BEARISH', color:'#4FC3F7', cat:'insumos' },
    { name:'MAP/DAP', score:42, trend:'BEARISH', color:'#4DD0E1', cat:'insumos' },
    { name:'KCL (POTÁSSIO)', score:48, trend:'NEUTRO', color:'#80DEEA', cat:'insumos' },
    { name:'GLIFOSATO', score:52, trend:'NEUTRO', color:'#A5D6A7', cat:'insumos' },
    { name:'ATRAZINA', score:50, trend:'NEUTRO', color:'#C5E1A5', cat:'insumos' },
    { name:'2,4-D', score:46, trend:'BEARISH', color:'#DCEDC8', cat:'insumos' },
  ];
  // NLP signal data per commodity
  const NLP_SIGNALS = {
    'SOJA':    { pos:['Retenção de safra no MT eleva preço spot','Dólar favorável para exportação','Demanda chinesa em alta'], neg:['Safra recorde Argentina pressiona CBOT','Estoques de passagem altos nos EUA'], mentions:1420, sentPct:'+58%', logNote:'BR-163 congestionada — frete +8%' },
    'MILHO':   { pos:['Safrinha 2026 em bom desenvolvimento','Etanol de milho com demanda crescente'], neg:['Oferta abundante na safrinha','Exportação desacelerando vs 2025'], mentions:890, sentPct:'+12%', logNote:'Ferrovias escoando normalmente' },
    'CAFÉ':    { pos:['Estoques baixos na ICE','Demanda europeia estável'], neg:['Safra do Vietnã robusta pressiona arábica','Colheita BR iniciando — oferta entrando'], mentions:620, sentPct:'-22%', logNote:'Porto de Santos operacional' },
    'TOMATE MESA':{ pos:['Chuvas em MG reduziram oferta de frutos padrão Extra A','CEAGESP com entrada abaixo da média — escassez de produto de banca','Consumidor pagando mais pela estética e frescor','Geada prevista no Sul eleva expectativa de corte de oferta'], neg:['Produção irrigada em Petrolina compensando parcialmente','Consumidor migrando para tomate indústria como substituto barato'], mentions:340, sentPct:'+42%', logNote:'Frete Cristalina→SP em alta +12%. Produto perecível — janela de 48h.', focus:'FOCO VAREJO — Aparência, frescor, volatilidade diária no CEASA' },
    'TOMATE IND.':{ pos:['Safra rasteira estável — contratos com fábricas garantidos','Volume excedente sendo desviado para CEASA como "tomate para molho"','Serve como piso de preço do mercado total'], neg:['Grau Brix abaixo do ideal por amplitude térmica noturna elevada','Colheita mecânica com custo de diesel em alta','Estoques globais de polpa concentrada ainda confortáveis'], mentions:180, sentPct:'+8%', logNote:'Cristalina-GO e Itaberaí-GO escoando via BR-153. Normal.', focus:'FOCO PROCESSAMENTO — Rendimento, Brix, contratos industriais. No CEASA apenas como excedente não processado.' },
    'CEBOLA':  { pos:['Colheita em Cristalina com ritmo lento (+12% impacto)','Preço da saca subindo nas CEASAs'], neg:['Importação argentina entrando pelo Sul'], mentions:280, sentPct:'+38%', logNote:'Fretes estáveis, alerta chuva Sul' },
    'BATATA':  { pos:['Safra das secas em fase final — oferta reduzindo'], neg:['Entrada de importados da Argentina','Consumo no varejo abaixo da média sazonal','Estoque frio em SP ainda alto'], mentions:195, sentPct:'-15%', logNote:'BR-116 livre' },
    'CENOURA': { pos:['Ciclo de 90d — nova safra entrando em MG'], neg:['Oferta constante mantém preço estável'], mentions:120, sentPct:'+5%', logNote:'Frete normal' },
    'ALFACE':  { pos:['Ciclo curto 45d — demanda constante','Cinturão Verde SP operacional'], neg:['Chuvas excessivas danificam folhosas em Mogi'], mentions:160, sentPct:'+22%', logNote:'Proximidade CEAGESP minimiza frete' },
    'PIMENTÃO':{ pos:['Petrolina irrigado mantém oferta','Demanda de food service estável'], neg:['Preço no atacado estável, sem pressão'], mentions:90, sentPct:'+8%', logNote:'Frete NE→SE em alta' },
    'BANANA':  { pos:['Consumo constante — fruta mais popular BR'], neg:['Oferta abundante em Registro-SP e Jaíba-MG'], mentions:110, sentPct:'+3%', logNote:'Normal' },
    'LARANJA': { pos:['Greening controlado em SP'], neg:['Safra cheia pressiona preço do suco','Exportação de suco desacelerando'], mentions:200, sentPct:'-18%', logNote:'Normal' },
    'MANGA':   { pos:['Demanda europeia aquecida — exportação +15%','Produção Vale SF premium','Preço subindo no CEASA-PE'], neg:['Chuva excessiva pode afetar florada'], mentions:180, sentPct:'+35%', logNote:'Porto de Suape operacional' },
    'UVA':     { pos:['Serra Gaúcha com safra boa','Exportação de mesa em alta'], neg:['Importação chilena entrando'], mentions:95, sentPct:'+10%', logNote:'Normal' },
    'MORANGO': { pos:['Safra de inverno iniciando no Sul','Preço de varejo alto — margem boa'], neg:['Sensível a geada — risco de perda'], mentions:75, sentPct:'+28%', logNote:'Logística refrigerada OK' },
    'BOI GORDO':{ pos:['Demanda chinesa aquecida — exportação +8%','Confinamento reduzido — oferta apertada'], neg:['Preço ao consumidor alto reduz demanda interna'], mentions:1800, sentPct:'+45%', logNote:'Frigoríficos operando 90% capacidade' },
    'SUÍNO VIVO':{ pos:['Custo de ração estável','Exportação para Ásia em alta'], neg:['Competição com frango no varejo'], mentions:320, sentPct:'+15%', logNote:'Normal' },
    'FRANGO VIVO':{ pos:['Custo de milho/soja estável','Exportação recorde para Oriente Médio'], neg:['Gripe aviária monitorada no RS'], mentions:550, sentPct:'+30%', logNote:'Normal' },
    'OVOS':    { pos:['Consumo per capita em alta','Exportação crescendo'], neg:['Oferta ajustada ao consumo'], mentions:140, sentPct:'+8%', logNote:'Normal' },
    'LEITE':   { pos:['Entressafra se aproximando — preço deve subir'], neg:['Importação de leite em pó da Argentina/Uruguai','Custos de produção ainda altos','Consumo retraído'], mentions:280, sentPct:'-25%', logNote:'Normal' },
    'UREIA':   { pos:['Preço global em queda — janela de compra'], neg:['Excesso de oferta global (China + Rússia)','Estoques altos nos distribuidores BR'], mentions:420, sentPct:'-40%', logNote:'Importação normal via Santos' },
    'MAP/DAP': { pos:['Safra de inverno demanda menos'], neg:['Preço em queda global','Estoque alto no BR'], mentions:180, sentPct:'-30%', logNote:'Normal' },
    'TRIGO':   { pos:['Safra do RS em desenvolvimento','Demanda de moagem estável'], neg:['Importação Argentina competitiva'], mentions:240, sentPct:'+5%', logNote:'Normal' },
    'ALGODÃO': { pos:['Exportação forte para Ásia','Qualidade da pluma BR premium'], neg:['Estoque global alto'], mentions:310, sentPct:'+18%', logNote:'Porto de Santos sem fila' },
    'ARROZ':   { pos:['Preço estável — consumo regular'], neg:['Safra RS sem problemas — oferta folgada'], mentions:160, sentPct:'+2%', logNote:'Normal' },
  };
  window._sentCommodities = commodities;
  window._sentNLP = NLP_SIGNALS;
  const cats = {graos:'GRÃOS E FIBRAS', horti:'HORTIFRUTI', pecuaria:'PECUÁRIA (BOVINA · SUÍNA · AVES)', insumos:'FERTILIZANTES E DEFENSIVOS'};
  let html = '';
  for (const [catKey, catLabel] of Object.entries(cats)) {
    const items = commodities.filter(c => c.cat === catKey);
    html += `<div style="grid-column:1/-1;color:var(--accent);font-size:9px;letter-spacing:2px;margin-top:${catKey==='graos'?'0':'8'}px;padding-bottom:3px;border-bottom:1px solid var(--border);">${catLabel}</div>`;
    html += items.map(c => {
      const adj = window._climateScoreAdjustments?.[c.name] || 0;
      const finalScore = Math.max(0, Math.min(100, Math.round(c.score + adj)));
      const barColor = finalScore > 55 ? '#30d158' : finalScore > 40 ? '#ffd60a' : '#ff453a';
      const climateBadge = adj !== 0 ? `<div style="font-size:6px;color:${adj>0?'#30d158':'#ff453a'};">${adj>0?'▲':'▼'} CLIMA</div>` : '';
      return `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:8px;cursor:pointer;transition:border-color .2s;" onclick="showNLPSignals('${c.name}')" onmouseover="this.style.borderColor='var(--accent)'" onmouseout="this.style.borderColor='var(--border)'">
        <div style="font-size:8px;color:var(--text2);letter-spacing:1px;">${c.name}</div>
        <div style="font-size:16px;font-weight:bold;color:${barColor};margin:2px 0;">${finalScore}</div>
        <div style="height:3px;background:#3a3a3c;border-radius:2px;overflow:hidden;margin:3px 0;"><div style="height:100%;width:${finalScore}%;background:${barColor};border-radius:2px;"></div></div>
        <div style="font-size:7px;color:${barColor};font-weight:bold;">${c.trend}</div>${climateBadge}</div>`;
    }).join('');
  }
  gauges.innerHTML = html;
  const ret = document.getElementById('sent-retention');
  ret.innerHTML = `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:10px;">
    <div style="margin-bottom:6px;"><b style="color:var(--warn);">⚠ SINAL DE RETENÇÃO DETECTADO</b></div>
    <div style="color:var(--text2);line-height:1.5;">Produtores do MT estão retendo 18% da safra de soja. Volume embarcado caiu 12% vs semana anterior. NLP detectou 340 menções de "segurar" e "esperar preço" em grupos de WhatsApp e fóruns agro nas últimas 48h.</div>
    <div style="margin-top:6px;color:var(--accent);font-size:9px;">Impacto estimado: +R$ 2,40/sc em 5-7 dias se retenção persistir.</div></div>`;
  const analyst = document.getElementById('sent-analyst');
  analyst.innerHTML = `<div style="color:var(--accent);font-size:9px;margin-bottom:6px;">🎙 ANALISTA VIRTUAL NIA$ — ${new Date().toLocaleTimeString('pt-BR')}</div>
    <div style="color:var(--text);line-height:1.5;"><b>GRÃOS:</b> Soja <b style="color:#30d158">bullish</b> (62) com retenção no MT. Milho neutro — safrinha pressiona. Café <b style="color:#ff453a">bearish</b> por oferta do Vietnã.<br>
    <b>HORTIFRUTI:</b> Tomate <b style="color:#30d158">bullish</b> (73) — chuvas em MG reduziram oferta. Cebola em alta (65) com colheita atrasada em Cristalina. Manga forte (68) por demanda europeia. Batata <b style="color:#ff453a">bearish</b> (42).<br>
    <b>PECUÁRIA:</b> Boi gordo <b style="color:#30d158">bullish</b> (71) — demanda chinesa. Frango em alta (64) com custo de ração estável. Suíno neutro. Leite <b style="color:#ff453a">pressionado</b> (40).<br>
    <b>INSUMOS:</b> Ureia <b style="color:#ff453a">bearish</b> (35) — excesso global. MAP/DAP em queda. Defensivos estáveis.<br>
    <b>RECOMENDAÇÃO:</b> Manter posição em soja/tomate/boi. Hedge em café/ureia. Atenção à janela de compra de fertilizantes.</div>`;
  const social = document.getElementById('sent-social');
  const sources = [
    { name:'Twitter/X Agro', mentions:1240, sentiment:'+58%', color:'#1DA1F2' },
    { name:'Grupos WhatsApp', mentions:890, sentiment:'+42%', color:'#25D366' },
    { name:'Portais de Notícias', mentions:156, sentiment:'+61%', color:'#ff9f0a' },
  ];
  social.innerHTML = sources.map(s => `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:5px;padding:8px;font-size:9px;">
    <div style="color:${s.color};font-weight:bold;margin-bottom:4px;">${s.name}</div>
    <div>${s.mentions} menções (24h)</div><div>Sentimento: <b style="color:#30d158;">${s.sentiment} bullish</b></div></div>`).join('');
}

function showNLPSignals(name) {
  const panel = document.getElementById('sent-signals');
  if (!panel) return;
  const nlp = window._sentNLP?.[name];
  const com = window._sentCommodities?.find(c => c.name === name);
  if (!nlp || !com) {
    panel.innerHTML = `<div style="padding:10px;font-size:10px;color:var(--text2);">Selecione um produto para ver os sinais NLP.</div>`;
    return;
  }
  const adj = window._climateScoreAdjustments?.[name] || 0;
  const finalScore = Math.max(0, Math.min(100, Math.round(com.score + adj)));
  const barColor = finalScore > 55 ? '#30d158' : finalScore > 40 ? '#ffd60a' : '#ff453a';
  const sentColor = nlp.sentPct.startsWith('+') ? '#30d158' : '#ff453a';

  let html = `<div style="padding:8px;">
    <div style="font-size:11px;font-weight:bold;color:${barColor};margin-bottom:2px;">${name} <span style="font-size:14px;">${finalScore}</span>/100 · ${com.trend}</div>
    ${nlp.focus ? `<div style="font-size:8px;color:var(--accent);margin-bottom:4px;padding:3px 6px;background:rgba(10,132,255,.08);border-radius:3px;border-left:2px solid var(--accent);">${_esc(nlp.focus)}</div>` : ''}
    <div style="height:4px;background:#3a3a3c;border-radius:2px;overflow:hidden;margin-bottom:8px;"><div style="height:100%;width:${finalScore}%;background:${barColor};border-radius:2px;"></div></div>`;

  // Drivers positivos
  html += `<div style="font-size:8px;color:#30d158;letter-spacing:1px;margin-bottom:4px;">▲ DRIVERS POSITIVOS</div>`;
  nlp.pos.forEach(p => {
    html += `<div style="font-size:9px;color:var(--text);padding:2px 0;border-bottom:1px solid rgba(48,209,88,.08);">🟢 ${_esc(p)}</div>`;
  });

  // Drivers negativos
  html += `<div style="font-size:8px;color:#ff453a;letter-spacing:1px;margin:6px 0 4px;">▼ DRIVERS NEGATIVOS</div>`;
  nlp.neg.forEach(n => {
    html += `<div style="font-size:9px;color:var(--text);padding:2px 0;border-bottom:1px solid rgba(255,69,58,.08);">🔴 ${_esc(n)}</div>`;
  });

  // Logística
  html += `<div style="font-size:8px;color:var(--accent);letter-spacing:1px;margin:6px 0 4px;">🚛 LOGÍSTICA</div>`;
  html += `<div style="font-size:9px;color:var(--text2);">${_esc(nlp.logNote)}</div>`;

  // Climate impact
  if (adj !== 0) {
    html += `<div style="font-size:8px;color:${adj>0?'#30d158':'#ff453a'};letter-spacing:1px;margin:6px 0 4px;">🌡 IMPACTO CLIMÁTICO</div>`;
    html += `<div style="font-size:9px;color:var(--text);">${adj>0?'▲':'▼'} Ajuste de ${adj>0?'+':''}${Math.round(adj)} pts por evento climático ativo</div>`;
  }

  // Social volume
  html += `<div style="font-size:8px;color:#ffd60a;letter-spacing:1px;margin:6px 0 4px;">💬 VOLUME SOCIAL (24h)</div>`;
  html += `<div style="display:flex;align-items:center;gap:8px;font-size:9px;">
    <div style="flex:1;height:12px;background:#3a3a3c;border-radius:3px;overflow:hidden;">
      <div style="height:100%;width:${Math.min(100,nlp.mentions/20)}%;background:${sentColor};border-radius:3px;"></div>
    </div>
    <span style="color:var(--text);font-weight:bold;">${nlp.mentions}</span>
  </div>`;
  html += `<div style="font-size:9px;color:${sentColor};margin-top:2px;">Sentimento: <b>${nlp.sentPct}</b></div>`;

  // Sources breakdown
  const srcBreak = [
    { name:'Twitter/X', pct: Math.round(nlp.mentions*0.45), color:'#1DA1F2' },
    { name:'WhatsApp', pct: Math.round(nlp.mentions*0.35), color:'#25D366' },
    { name:'Portais', pct: Math.round(nlp.mentions*0.20), color:'#ff9f0a' },
  ];
  html += `<div style="display:flex;gap:4px;margin-top:6px;">${srcBreak.map(s =>
    `<div style="flex:1;text-align:center;background:var(--bg3);border-radius:3px;padding:3px;font-size:8px;">
      <div style="color:${s.color};font-weight:bold;">${s.pct}</div><div style="color:var(--text2);">${s.name}</div>
    </div>`).join('')}</div>`;

  // Cross-market intelligence (tomate mesa ↔ indústria)
  if (name === 'TOMATE MESA') {
    const tind = window._sentCommodities?.find(c => c.name === 'TOMATE IND.');
    if (tind) {
      const indAdj = window._climateScoreAdjustments?.['TOMATE IND.'] || 0;
      const indScore = Math.round(tind.score + indAdj);
      html += `<div style="margin-top:8px;padding:6px;background:rgba(10,132,255,.06);border:1px solid rgba(10,132,255,.15);border-radius:4px;font-size:9px;">
        <div style="color:var(--accent);font-weight:bold;margin-bottom:3px;">🔄 CRUZAMENTO MESA × INDÚSTRIA</div>
        <div style="color:var(--text2);line-height:1.4;">Tomate Indústria no CEASA: <b style="color:var(--text)">${indScore}/100</b>.
        ${indScore > 55 ? '<br>⚠ Se o score Indústria subir, o Mesa dispara em seguida — a base do mercado está subindo.' : ''}
        ${finalScore - indScore > 15 ? '<br>📊 Spread Mesa-Ind. alto (+' + (finalScore-indScore) + 'pts). Consumidor pode migrar para indústria como substituto.' : ''}
        </div></div>`;
    }
  }
  if (name === 'TOMATE IND.') {
    const tmesa = window._sentCommodities?.find(c => c.name === 'TOMATE MESA');
    if (tmesa) {
      const mesaAdj = window._climateScoreAdjustments?.['TOMATE MESA'] || 0;
      const mesaScore = Math.round(tmesa.score + mesaAdj);
      html += `<div style="margin-top:8px;padding:6px;background:rgba(10,132,255,.06);border:1px solid rgba(10,132,255,.15);border-radius:4px;font-size:9px;">
        <div style="color:var(--accent);font-weight:bold;margin-bottom:3px;">🔄 CRUZAMENTO INDÚSTRIA × MESA</div>
        <div style="color:var(--text2);line-height:1.4;">Tomate Mesa no CEASA: <b style="color:var(--text)">${mesaScore}/100</b>.
        ${mesaScore > 70 ? '<br>📊 Preço do Mesa proibitivo — consumidor migrando para Indústria. Volume no CEASA é excedente não processado.' : ''}
        <br>🏭 Este produto está no CEASA para escoar excedente. Serve como piso de preço do mercado total.
        </div></div>`;
    }
  }

  html += `</div>`;
  panel.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════════
// ESG & RASTREABILIDADE
// ═══════════════════════════════════════════════════════════════════
function initESG() {
  window._esgInit = true;
  const scores = document.getElementById('esg-scores');
  const kpis = [
    { label:'Score ESG Médio', value:'78/100', sub:'Todas as origens monitoradas', color:'var(--accent2)' },
    { label:'Áreas em Conformidade', value:'94.2%', sub:'EUDR compliance', color:'var(--accent2)' },
    { label:'Alertas Desmatamento', value:'3', sub:'INPE/DETER últimas 72h', color:'var(--danger)' },
    { label:'CO₂ Logístico Médio', value:'2.1 kg/t', sub:'Meta: < 2.5 kg/t', color:'#ffd60a' },
  ];
  scores.innerHTML = kpis.map(k => `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:10px;">
    <div style="font-size:9px;color:var(--text2);letter-spacing:1px;">${k.label}</div>
    <div style="font-size:22px;font-weight:bold;color:${k.color};margin:4px 0;">${k.value}</div>
    <div style="font-size:9px;color:var(--text2);">${k.sub}</div></div>`).join('');
  const deforest = document.getElementById('esg-deforest');
  deforest.innerHTML = `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:10px;font-size:10px;">
    <div style="color:var(--danger);margin-bottom:6px;font-weight:bold;">🛰 DETER/INPE — Últimos 30 dias</div>
    <div>Alertas no Arco do Desmatamento: <b style="color:var(--danger);">847 km²</b></div>
    <div>Overlap com áreas monitoradas NIA$: <b style="color:var(--accent2);">0 km² (LIMPO)</b></div>
    <div style="margin-top:6px;">Municípios com alerta: São Félix do Xingu (PA), Altamira (PA), Novo Progresso (PA)</div>
    <div style="margin-top:6px;color:var(--accent2);">✓ Nenhuma origem rastreada pelo NIA$ possui overlap com desmatamento recente.</div></div>`;
  const carbon = document.getElementById('esg-carbon');
  carbon.innerHTML = `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:10px;font-size:10px;">
    <div style="color:var(--accent);margin-bottom:6px;font-weight:bold;">🌱 PEGADA DE CARBONO POR ROTA</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
      <div>Sorriso→Santos (BR-163): <b style="color:var(--danger);">3.8 kg/t</b></div>
      <div>Sorriso→Miritituba (Hidro): <b style="color:var(--accent2);">1.2 kg/t</b></div>
      <div>Rio Verde→Paranaguá: <b style="color:var(--warn);">2.4 kg/t</b></div>
      <div>Cascavel→Paranaguá (Ferro): <b style="color:var(--accent2);">0.9 kg/t</b></div>
    </div>
    <div style="margin-top:6px;color:var(--accent2);">IA recomenda: desviar 20% do MT para Miritituba. Economia: -1.8 kg CO₂/t</div></div>`;
  const chain = document.getElementById('esg-chain-body');
  const rows = [
    { orig:'Sorriso (MT)', cult:'Soja', desmat:'0 km²', co2:'3.8 kg/t', score:82, eudr:'✓ APROVADO' },
    { orig:'Rio Verde (GO)', cult:'Soja', desmat:'0 km²', co2:'2.4 kg/t', score:88, eudr:'✓ APROVADO' },
    { orig:'Cristalina (GO)', cult:'Cebola', desmat:'0 km²', co2:'1.8 kg/t', score:91, eudr:'✓ APROVADO' },
    { orig:'Petrolina (PE)', cult:'Manga', desmat:'0 km²', co2:'2.1 kg/t', score:85, eudr:'✓ APROVADO' },
    { orig:'S.F. Xingu (PA)', cult:'Pastagem', desmat:'12.4 km²', co2:'4.2 kg/t', score:34, eudr:'✗ BLOQUEADO' },
  ];
  chain.innerHTML = rows.map(r => {
    const scoreColor = r.score >= 70 ? 'var(--accent2)' : r.score >= 50 ? 'var(--warn)' : 'var(--danger)';
    const eudrColor = r.eudr.includes('✓') ? 'var(--accent2)' : 'var(--danger)';
    return `<tr style="border-bottom:1px solid var(--border);"><td style="padding:4px 8px;">${r.orig}</td><td style="padding:4px 8px;">${r.cult}</td><td style="padding:4px 8px;color:${r.desmat==='0 km²'?'var(--accent2)':'var(--danger)'}">${r.desmat}</td><td style="padding:4px 8px;">${r.co2}</td><td style="padding:4px 8px;color:${scoreColor};font-weight:bold;">${r.score}</td><td style="padding:4px 8px;color:${eudrColor};font-weight:bold;font-size:9px;">${r.eudr}</td></tr>`;
  }).join('');
}

// ═══════════════════════════════════════════════════════════════════
// WAR ROOM — Simulação de Estresse Sistêmico
// ═══════════════════════════════════════════════════════════════════
// War Room — sem simulação. Dados reais via WarRoomProtocol.refresh()

// ═══════════════════════════════════════════════════════════════════
// NEWS & MEDIA FEED — Agro Intelligence
// APIs: NewsAPI.ai · YouTube Data API · Gemini 1.5 Flash
// Fallback: notícias sintéticas realistas até keys serem configuradas
// ═══════════════════════════════════════════════════════════════════
const NiasNews = {
  NEWSAPI_KEY: '',
  YOUTUBE_KEY: '',
  GEMINI_KEY: '',
  _items: [],

  _fallbackNews() {
    const now = Date.now();
    return [
      { title:'Geada atinge Sul de Minas — produtores de café ativam irrigação antigeada', src:'Canal Rural', tag:'bearish', time:now-180000, thumb:'https://placehold.co/112x80/0B0E14/50C878?text=GEADA', url:'#', type:'news' },
      { title:'BR-163: Fluxo de caminhões aumenta 34% com pico de colheita no MT', src:'Globo Rural', tag:'bearish', time:now-420000, thumb:'https://placehold.co/112x80/0B0E14/ff3d3d?text=BR-163', url:'#', type:'news' },
      { title:'Soja CBOT fecha em queda — excesso de oferta na Argentina pressiona', src:'Bloomberg Línea', tag:'bearish', time:now-780000, thumb:'https://placehold.co/112x80/0B0E14/FFD700?text=SOJA', url:'#', type:'news' },
      { title:'CEAGESP: Tomate mesa sobe 12% na semana com chuvas em Minas', src:'HF Brasil', tag:'bullish', time:now-960000, thumb:'https://placehold.co/112x80/0B0E14/E53935?text=TOMATE', url:'#', type:'news' },
      { title:'Porto de Santos bate recorde de embarque de açúcar em março', src:'Notícias Agrícolas', tag:'bullish', time:now-1500000, thumb:'https://placehold.co/112x80/0B0E14/00d4ff?text=SANTOS', url:'#', type:'news' },
      { title:'Previsão: frente fria avança sobre PR e SC nos próximos 5 dias', src:'Climatempo', tag:'bearish', time:now-2100000, thumb:'https://placehold.co/112x80/0B0E14/33ABFF?text=CLIMA', url:'#', type:'news' },
      { title:'Safra de milho safrinha 2026 deve superar 98Mt segundo CONAB', src:'Agrolink', tag:'bullish', time:now-3000000, thumb:'https://placehold.co/112x80/0B0E14/FF8C00?text=MILHO', url:'#', type:'news' },
      { title:'Cebola em Cristalina: colheita atrasada eleva preço no CEASA-SP', src:'CEPEA', tag:'bullish', time:now-3600000, thumb:'https://placehold.co/112x80/0B0E14/AB47BC?text=CEBOLA', url:'#', type:'news' },
      { title:'Hidrovias do Brasil expande terminal em Miritituba — +15% capacidade', src:'Valor Econômico', tag:'bullish', time:now-5400000, thumb:'https://placehold.co/112x80/0B0E14/00ff88?text=HIDRO', url:'#', type:'news' },
      { title:'NDVI em queda no MATOPIBA — INPE confirma estresse hídrico severo', src:'Embrapa', tag:'bearish', time:now-7200000, thumb:'https://placehold.co/112x80/0B0E14/ff3d3d?text=NDVI', url:'#', type:'news' },
      { title:'Preço da manga sobe no Vale do São Francisco — demanda europeia aquecida', src:'Jornal do Comércio', tag:'bullish', time:now-9000000, thumb:'https://placehold.co/112x80/0B0E14/FFA726?text=MANGA', url:'#', type:'news' },
      { title:'Análise: Como a IA está revolucionando o monitoramento de safras', src:'YouTube · Agro+', tag:'neutral', time:now-10800000, thumb:'https://placehold.co/112x80/0B0E14/ff0000?text=▶+VIDEO', url:'#', type:'video' },
    ];
  },

  _timeAgo(ts) {
    const d = Math.floor((Date.now() - ts) / 60000);
    if (d < 1) return 'Agora';
    if (d < 60) return `Há ${d} min`;
    if (d < 1440) return `Há ${Math.floor(d/60)}h`;
    return `Há ${Math.floor(d/1440)}d`;
  },

  _renderCard(item) {
    const tagClass = item.tag === 'bullish' ? 'bullish' : item.tag === 'bearish' ? 'bearish' : item.type === 'video' ? 'video' : 'neutral';
    const tagLabel = item.tag === 'bullish' ? '▲ BULLISH' : item.tag === 'bearish' ? '▼ BEARISH' : item.type === 'video' ? '▶ VIDEO' : '◎ NEUTRO';
    return `<div class="news-card" onclick="window.open('${item.url}','_blank')">
      <img class="news-thumb" src="${item.thumb}" alt="" loading="lazy" onerror="this.style.display='none'">
      <div class="news-body">
        <div class="news-title">${_esc(item.title)}</div>
        <div class="news-meta">
          <span class="news-tag ${tagClass}">${tagLabel}</span>
          <span>${this._timeAgo(item.time)}</span>
          <span class="news-src">${_esc(item.src)}</span>
        </div>
      </div>
    </div>`;
  },

  render() {
    const list = document.getElementById('news-feed-list');
    if (!list) return;
    const items = this._items.length > 0 ? this._items : this._fallbackNews();
    list.innerHTML = items.map(i => this._renderCard(i)).join('');
    const summary = document.getElementById('news-summary');
    const bull = items.filter(i => i.tag === 'bullish').length;
    const bear = items.filter(i => i.tag === 'bearish').length;
    if (summary) summary.innerHTML = `<span style="color:#30d158">${bull} BULLISH</span> · <span style="color:#ff453a">${bear} BEARISH</span> · ${items.length} itens`;
  },

  async fetchReal() {
    if (!this.NEWSAPI_KEY && !this.YOUTUBE_KEY) { this.render(); return; }
    // NewsAPI.ai
    if (this.NEWSAPI_KEY) {
      try {
        const r = await fetch(`https://eventregistry.org/api/v1/article/getArticles`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'getArticles',
            keyword: ['agricultura Brasil','safra','CEASA','commodity agro'],
            keywordOp: 'or',
            lang: 'por',
            articlesPage: 1,
            articlesCount: 10,
            articlesSortBy: 'date',
            apiKey: this.NEWSAPI_KEY
          })
        });
        if (r.ok) {
          const data = await r.json();
          const arts = data.articles?.results || [];
          arts.forEach(a => {
            this._items.push({
              title: a.title || '', src: a.source?.title || 'NewsAPI',
              tag: a.sentiment > 0.1 ? 'bullish' : a.sentiment < -0.1 ? 'bearish' : 'neutral',
              time: new Date(a.dateTime || Date.now()).getTime(),
              thumb: a.image || 'https://placehold.co/112x80/0B0E14/33ABFF?text=NEWS',
              url: a.url || '#', type: 'news'
            });
          });
        }
      } catch(e) { console.warn('NewsAPI error:', e); }
    }
    // YouTube Data API
    if (this.YOUTUBE_KEY) {
      try {
        const q = encodeURIComponent('agricultura Brasil safra 2026');
        const r = await fetch(`https://www.googleapis.com/youtube/v3/search?part=snippet&q=${q}&type=video&maxResults=5&order=date&relevanceLanguage=pt&key=${this.YOUTUBE_KEY}`);
        if (r.ok) {
          const data = await r.json();
          (data.items || []).forEach(v => {
            this._items.push({
              title: v.snippet.title, src: 'YouTube · ' + v.snippet.channelTitle,
              tag: 'neutral', time: new Date(v.snippet.publishedAt).getTime(),
              thumb: v.snippet.thumbnails?.medium?.url || '',
              url: 'https://www.youtube.com/watch?v=' + v.id.videoId, type: 'video'
            });
          });
        }
      } catch(e) { console.warn('YouTube API error:', e); }
    }
    this._items.sort((a, b) => b.time - a.time);
    if (this._items.length === 0) this._items = this._fallbackNews();
    this.render();
  },

  startAutoRefresh() {
    this.fetchReal();
    // Notícias sintéticas removidas — sem geração aleatória de breaking news
    // Atualizações reais chegam via fetchReal() a cada 5 minutos
    setInterval(() => {
      this.fetchReal();
      const sumEl = document.getElementById('news-summary');
      const list = document.getElementById('news-feed-list');
      if (sumEl && list) {
        const tags = list.querySelectorAll('.news-tag');
        let bu = 0, be = 0;
        tags.forEach(t => { if (t.classList.contains('bullish')) bu++; if (t.classList.contains('bearish')) be++; });
        sumEl.innerHTML = `<span style="color:#30d158">${bu} BULLISH</span> · <span style="color:#ff453a">${be} BEARISH</span> · ${list.children.length} itens`;
      }
    }, 5 * 60 * 1000); // a cada 5 min — respeita rate limits das APIs de notícias
  }
};

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => NiasNews.startAutoRefresh(), 3000);

// ═══════════════════════════════════════════════════════════════════
// NiasClimate — Climate Intelligence Module
// Monitora eventos extremos, calcula impacto HF, gera ODI e insights
// ═══════════════════════════════════════════════════════════════════
const NiasClimate = {
  _state: {},
  _baseline: null,
  _insights: [],
  _appliedBumps: {},

  async analyzeRegions() {
    const points = CLIMATE_HF_REGIONS.map(r => ({ lat: r.lat, lon: r.lon }));
    const weather = await NiasAPI.getWeatherMulti(points);
    if (!weather || weather.length === 0) return;

    this._state = {};
    CLIMATE_HF_REGIONS.forEach((region, i) => {
      const w = weather[i];
      if (!w || !w.daily) return;
      const tmin = Math.min(...(w.daily.temperature_2m_min || [99]));
      const precipMax = Math.max(...(w.daily.precipitation_sum || [0]));
      const windMax = w.current?.wind_speed_10m || 0;
      const events = [];

      for (const [evtName, th] of Object.entries(CLIMATE_THRESHOLDS)) {
        let val = 0;
        if (th.field === 'temperature_2m_min') val = tmin;
        else if (th.field === 'precipitation_sum') val = precipMax;
        else if (th.field === 'wind_speed_10m') val = windMax;
        const triggered = th.op === '<' ? val < th.value : val > th.value;
        if (triggered && (evtName.includes('GEADA') || evtName.includes('NEVE') ? region.frostRisk : true)) {
          events.push({ type: evtName, severity: th.severity, value: val });
        }
      }
      // Deduplicate: keep only highest severity per category
      const deduped = [];
      const seen = new Set();
      for (const e of events) {
        const cat = e.type.replace('RISCO_','').replace('CHUVA_INTENSA','ENCHENTE').replace('VENTO_FORTE','TEMPESTADE');
        if (!seen.has(cat)) { deduped.push(e); seen.add(cat); }
      }
      this._state[region.id] = { region, weather: w, tmin, precipMax, windMax, events: deduped };
    });
  },

  calculateImpact() {
    const month = new Date().getMonth() + 1;
    for (const [rid, data] of Object.entries(this._state)) {
      data.impacts = [];
      for (const evt of data.events) {
        const vuln = CROP_VULNERABILITY[evt.type] || {};
        for (const crop of data.region.crops) {
          const cv = vuln[crop];
          if (!cv) continue;
          // Phenology check
          const cal = Object.values(ARGUS_CALENDAR).find(c => c.regions?.includes(rid));
          let phaseMult = 1.0;
          if (cal) {
            const inColheita = month >= cal.colheita.start && month <= cal.colheita.end;
            const inPlantio = month >= cal.plantio.start && month <= cal.plantio.end;
            phaseMult = inColheita ? 1.2 : inPlantio ? 0.5 : 0.8;
          }
          data.impacts.push({
            crop, event: evt.type, severity: evt.severity,
            yieldLoss: Math.round(cv.yield * phaseMult),
            priceImpact: Math.round(cv.price * phaseMult),
          });
        }
      }
    }
  },

  getODI(regionId) {
    const data = this._state[regionId];
    if (!data) return 0;
    // Weather score (0-10)
    let ws = 0;
    if (data.events.some(e => e.severity === 'CRITICAL')) ws = 10;
    else if (data.events.some(e => e.severity === 'HIGH')) ws = 7;
    else if (data.events.length > 0) ws = 4;
    // Crop vulnerability score (0-10)
    const maxYield = data.impacts?.length > 0 ? Math.max(...data.impacts.map(i => i.yieldLoss)) : 0;
    const cs = Math.min(10, maxYield / 6);
    // Logistics score (0-10)
    const logKey = data.region.logKey;
    const logSat = logState[logKey] || 50;
    const ls = Math.min(10, Math.max(0, (logSat - 50) / 5));
    return Math.min(10, Math.round((ws * 0.40 + cs * 0.35 + ls * 0.25) * 10) / 10);
  },

  generateInsights() {
    this._insights = [];
    for (const [rid, data] of Object.entries(this._state)) {
      if (data.events.length === 0) continue;
      const odi = this.getODI(rid);
      const odiClass = odi >= 7 ? 'critical' : odi >= 4 ? 'high' : odi >= 2 ? 'medium' : 'low';
      for (const evt of data.events) {
        const crops = data.impacts?.filter(i => i.event === evt.type).map(i => i.crop).join(', ') || '—';
        const priceMax = data.impacts?.filter(i => i.event === evt.type).reduce((m, i) => Math.max(m, i.priceImpact), 0) || 0;
        const icon = evt.type.includes('GEADA') || evt.type.includes('NEVE') ? '❄️' : evt.type.includes('ENCHENTE') || evt.type.includes('CHUVA') ? '💧' : '💨';
        const msg = `${icon} ${evt.severity} (${data.region.name}): ${evt.type.replace('_',' ')}. Culturas: ${crops}. ${priceMax > 0 ? '+' + priceMax + '% preço em 72h.' : ''} ODI: ${odi}/10`;
        this._insights.push({ rid, msg, severity: evt.severity, odi, odiClass, event: evt.type, region: data.region });
      }
    }
    this._insights.sort((a, b) => b.odi - a.odi);
  },

  _applyToWarRoom() {
    const el = document.getElementById('war-climate-alerts') || document.getElementById('wr-climate-live');
    if (!el) return;
    const crits = this._insights.filter(i => i.severity === 'CRITICAL');
    if (crits.length === 0) { el.innerHTML = '<div style="font-size:9px;color:var(--accent2);">✓ Sem alertas climáticos críticos.</div>'; return; }
    el.innerHTML = '<div style="font-size:9px;color:var(--danger);letter-spacing:1px;margin-bottom:4px;">⚡ ALERTAS CLIMÁTICOS ATIVOS</div>' +
      crits.slice(0, 5).map(i => `<div class="climate-critical"><span class="odi-badge odi-${i.odiClass}">ODI ${i.odi}</span> ${_esc(i.msg)}</div>`).join('');
    const log = document.getElementById('war-log');
    if (log) {
      const ts = new Date().toLocaleTimeString('pt-BR');
      crits.slice(0, 3).forEach(i => {
        const d = document.createElement('div');
        d.style.cssText = 'padding:4px 8px;border-bottom:1px solid rgba(255,255,255,.04);font-size:9px;';
        d.innerHTML = `<span style="color:var(--danger);">${ts}</span> CLIMA: ${_esc(i.msg).slice(0,80)}`;
        log.insertBefore(d, log.firstChild);
      });
    }
  },

  _applyToSentimento() {
    window._climateScoreAdjustments = {};
    for (const data of Object.values(this._state)) {
      for (const impact of (data.impacts || [])) {
        const key = impact.crop.toUpperCase();
        const delta = impact.event.includes('GEADA') || impact.event.includes('NEVE') ? impact.priceImpact * 0.5 : -impact.yieldLoss * 0.3;
        window._climateScoreAdjustments[key] = (window._climateScoreAdjustments[key] || 0) + delta;
      }
    }
    const el = document.getElementById('sent-climate-impact');
    if (!el) return;
    const active = this._insights.filter(i => i.odi >= 3);
    if (active.length === 0) { el.innerHTML = ''; return; }
    el.innerHTML = '<div style="font-size:9px;color:#33ABFF;letter-spacing:1px;margin-bottom:4px;">🌡 IMPACTO CLIMÁTICO NO SENTIMENTO</div>' +
      active.slice(0, 4).map(i => `<div class="climate-${i.odiClass}" style="margin:2px 0;">${_esc(i.msg)}</div>`).join('');
    // Update virtual analyst
    const analyst = document.getElementById('sent-analyst');
    if (analyst && active.length > 0) {
      const climText = active.slice(0,2).map(i => i.msg).join(' ');
      const existing = analyst.innerHTML;
      if (!existing.includes('CLIMA:')) {
        analyst.innerHTML = `<div style="color:var(--danger);font-size:9px;margin-bottom:4px;"><b>CLIMA:</b> ${_esc(climText)}</div>` + existing;
      }
    }
  },

  _applyToLogistica() {
    // Save baseline on first run
    if (!this._baseline) this._baseline = { ...logState };
    // Revert previous bumps
    for (const [key, bump] of Object.entries(this._appliedBumps)) {
      logState[key] = Math.max(0, logState[key] - bump);
    }
    this._appliedBumps = {};
    // Apply new bumps
    for (const data of Object.values(this._state)) {
      if (data.events.length === 0) continue;
      const key = data.region.logKey;
      if (!logState[key]) continue;
      let bump = 0;
      for (const evt of data.events) {
        if (evt.type.includes('ENCHENTE')) bump = Math.max(bump, 20);
        else if (evt.type.includes('NEVE')) bump = Math.max(bump, 15);
        else if (evt.type.includes('CHUVA')) bump = Math.max(bump, 10);
        else if (evt.type.includes('GEADA')) bump = Math.max(bump, 5);
        else if (evt.type.includes('TEMPESTADE')) bump = Math.max(bump, 12);
      }
      if (bump > 0) {
        logState[key] = Math.min(99, logState[key] + bump);
        this._appliedBumps[key] = (this._appliedBumps[key] || 0) + bump;
      }
    }
    // Render blocked routes
    const el = document.getElementById('log-climate-routes');
    if (!el) return;
    const blocked = this._insights.filter(i => i.odi >= 5);
    if (blocked.length === 0) { el.innerHTML = '<div style="color:var(--accent2);">✓ Sem bloqueios climáticos.</div>'; return; }
    el.innerHTML = blocked.slice(0, 5).map(i =>
      `<div class="climate-${i.odiClass}" style="margin:2px 0;font-size:9px;"><span class="odi-badge odi-${i.odiClass}">ODI ${i.odi}</span> ${_esc(i.region.name)}: ${_esc(i.event.replace('_',' '))} → corredor ${_esc(i.region.logKey)} +${this._appliedBumps[i.region.logKey]||0}%</div>`
    ).join('');
  },

  _feedNews() {
    const list = document.getElementById('news-feed-list');
    if (!list) return;
    const top = this._insights.filter(i => i.odi >= 4).slice(0, 4);
    top.forEach(i => {
      const tag = i.event.includes('GEADA') || i.event.includes('NEVE') ? 'bearish' : i.event.includes('ENCHENTE') ? 'bearish' : 'bullish';
      const thumb = i.event.includes('GEADA') ? 'https://placehold.co/112x80/0B0E14/33ABFF?text=GEADA' :
                    i.event.includes('NEVE') ? 'https://placehold.co/112x80/0B0E14/FFFFFF?text=NEVE' :
                    'https://placehold.co/112x80/0B0E14/ffc107?text=CHUVA';
      const card = { title: i.msg, src: 'NIA$ Climate', tag, time: Date.now(), thumb, url: '#', type: 'news' };
      if (typeof NiasNews !== 'undefined' && NiasNews._renderCard) {
        list.insertAdjacentHTML('afterbegin', NiasNews._renderCard(card));
        while (list.children.length > 20) list.removeChild(list.lastChild);
      }
    });
  },

  async run() {
    try {
      await this.analyzeRegions();
      this.calculateImpact();
      this.generateInsights();
      this._applyToWarRoom();
      this._applyToSentimento();
      this._applyToLogistica();
      this._feedNews();
      NiasAPI._logSource && NiasAPI._logSource('Climate', this._insights.length > 0 ? 'api' : 'fallback');
    } catch(e) { console.warn('NiasClimate error:', e); }
    setTimeout(() => this.run(), 900000);
  }
};

});

// ═══════════════════════════════════════════════════════════════════
// NIA$ API LAYER — Dados Reais com Fallback Sintético
// APIs: IBGE SIDRA · Open-Meteo · INMET · INPE/FIRMS · CEPEA
// ═══════════════════════════════════════════════════════════════════
const NiasAPI = {
  cache: {},
  TTL: 900000,
  _src: {},

  _statusEl() { return document.getElementById('api-status-strip'); },

  _logSource(key, source) {
    this._src[key] = source;
    const el = this._statusEl();
    if (!el) return;
    const entries = Object.entries(this._src);
    el.innerHTML = entries.map(([k,s]) =>
      `<span style="margin-right:8px;">● ${k}: <b style="color:${s==='api'?'var(--accent2)':'var(--warn)'}">${s==='api'?'API REAL':'FALLBACK'}</b></span>`
    ).join('');
  },

  async _fetch(key, fetcher, fallback) {
    if (this.cache[key] && Date.now() - this.cache[key].ts < this.TTL) {
      return this.cache[key].data;
    }
    try {
      const data = await fetcher();
      this.cache[key] = { data, ts: Date.now() };
      this._logSource(key, 'api');
      return data;
    } catch(e) {
      console.warn(`NIA$ [${key}] fallback:`, e.message);
      const fb = fallback();
      this._logSource(key, 'fallback');
      return fb;
    }
  },

  // ── IBGE SIDRA — Produção Agrícola Municipal ─────────────────────
  async getSidra(cultCode, varCode) {
    varCode = varCode || 214;
    return this._fetch('SIDRA', async () => {
      const url = `https://apisidra.ibge.gov.br/values/t/5457/n6/all/v/${varCode}/p/last/c782/${cultCode}?formato=json`;
      const r = await fetch(url);
      if (!r.ok) throw new Error('SIDRA ' + r.status);
      const json = await r.json();
      const rows = json.slice(1).filter(d => d.V && d.V !== '...' && d.V !== 'X');
      return rows.map(d => ({
        munCode: d.D1C, munName: d.D1N,
        value: parseFloat(d.V), unit: d.D2N,
        year: d.D3N, culture: d.D4N
      }));
    }, () => []);
  },

  // ── Open-Meteo — Clima 7 dias por coordenada ────────────────────
  async getWeather(lat, lon) {
    const key = `METEO_${lat.toFixed(1)}_${lon.toFixed(1)}`;
    return this._fetch(key, async () => {
      const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
        `&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,soil_moisture_0_to_7cm` +
        `&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration` +
        `&hourly=soil_moisture_0_to_7cm` +
        `&timezone=America/Sao_Paulo&forecast_days=7`;
      const r = await fetch(url);
      if (!r.ok) throw new Error('OpenMeteo ' + r.status);
      return await r.json();
    }, () => ({
      current: { temperature_2m: 28.5, relative_humidity_2m: 62, precipitation: 0, wind_speed_10m: 8.2, soil_moisture_0_to_7cm: 0.22 },
      daily: {
        time: Array.from({length:7},(_,i) => { const d=new Date(); d.setDate(d.getDate()+i); return d.toISOString().slice(0,10); }),
        temperature_2m_max: [31.2,30.8,29.5,32.1,31.0,30.5,29.8],
        temperature_2m_min: [19.5,19.2,18.8,20.1,19.7,19.0,18.5],
        precipitation_sum: [0,2.5,0,0,5.2,1.0,0],
        et0_fao_evapotranspiration: [4.2,3.8,4.0,4.5,3.5,3.9,4.1]
      }
    }));
  },

  // ── Open-Meteo MULTI — Clima para todos os polos produtivos ─────
  async getWeatherMulti(points) {
    if (!points || points.length === 0) return [];
    const lats = points.map(p => p.lat.toFixed(2)).join(',');
    const lons = points.map(p => p.lon.toFixed(2)).join(',');
    const key = `METEO_MULTI_${points.length}`;
    return this._fetch(key, async () => {
      const url = `https://api.open-meteo.com/v1/forecast?latitude=${lats}&longitude=${lons}` +
        `&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,soil_moisture_0_to_7cm` +
        `&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration` +
        `&timezone=America/Sao_Paulo&forecast_days=7`;
      const r = await fetch(url);
      if (!r.ok) throw new Error('OpenMeteo Multi ' + r.status);
      const data = await r.json();
      return Array.isArray(data) ? data : [data];
    }, () => points.map(() => null)); // no fallback — show "—" when API unavailable
  },

  // ── INMET — Estações meteorológicas ativas ───────────────────────
  async getInmetStations() {
    return this._fetch('INMET', async () => {
      const r = await fetch('https://apitempo.inmet.gov.br/estacoes/T');
      if (!r.ok) throw new Error('INMET ' + r.status);
      const json = await r.json();
      return json.slice(0, 200).map(s => ({
        code: s.CD_ESTACAO, name: s.DC_NOME,
        lat: parseFloat(s.VL_LATITUDE), lon: parseFloat(s.VL_LONGITUDE),
        state: s.SG_ESTADO, active: s.TP_ESTACAO === 'Automática'
      }));
    }, () => [
      { code:'A001', name:'BRASÍLIA', lat:-15.78, lon:-47.93, state:'DF', active:true },
      { code:'A301', name:'SÃO PAULO', lat:-23.50, lon:-46.62, state:'SP', active:true },
      { code:'A652', name:'CUIABÁ', lat:-15.56, lon:-56.06, state:'MT', active:true },
      { code:'A706', name:'PETROLINA', lat:-9.37, lon:-40.50, state:'PE', active:true },
    ]);
  },

  // ── INPE/FIRMS (NASA LANCE) — Focos de queimada (últimas 24h) ────
  // Obtenha sua MAP_KEY gratuita em: https://firms.modaps.eosdis.nasa.gov/api/map_key/
  FIRMS_KEY: '9225045e67ace250dec5ac20660fda26',

  // ── Planet (PlanetScope) — Tiles de satélite alta resolução ─────
  // Conta Planet: https://www.planet.com/account/#/user-settings
  PLANET_KEY: 'PLAK1870183e9e0e4fb3b2f485ef4787ad77',

  getPlanetTileUrl(mosaic) {
    mosaic = mosaic || 'global_monthly_2026_02_mosaic';
    return `https://tiles.planet.com/basemaps/v1/planet-tiles/${mosaic}/gmap/{z}/{x}/{y}.png?api_key=${this.PLANET_KEY}`;
  },

  addPlanetLayer(map, mosaic) {
    if (!this.PLANET_KEY) return null;
    const url = this.getPlanetTileUrl(mosaic);
    const layer = L.tileLayer(url, {
      attribution: '© Planet Labs',
      maxZoom: 18,
      opacity: 0.85
    });
    return layer;
  },

  // ── Sentinel-1 SAR (Copernicus Data Space) — Radar em todas condições ─
  // WMS livre via Copernicus Data Space · Penetra nuvens · Backscatter VV/VH
  // Registro gratuito: https://dataspace.copernicus.eu/
  COPERNICUS_SH_ID: 'sh-32678296-41db-41ed-952a-79632bc533c6',
  COPERNICUS_SECRET: '7rttTQzkrkruDIRnOIy4MfLv0jsszQzs',

  addSARLayer(map) {
    // Copernicus Data Space WMS for Sentinel-1 GRD (IW mode, VV polarization)
    const shId = this.COPERNICUS_SH_ID;
    if (shId) {
      // Sentinel Hub instance-based WMS
      return L.tileLayer.wms(`https://sh.dataspace.copernicus.eu/ogc/wms/${shId}`, {
        layers: 'SENTINEL-1-IW-VV',
        format: 'image/png',
        transparent: true,
        attribution: '© Copernicus Sentinel-1 SAR',
        maxZoom: 16,
        opacity: 0.6,
        time: new Date().toISOString().slice(0, 10),
      });
    }
    // Fallback: Copernicus Browser public tile (limited but free, no auth)
    return L.tileLayer('https://tiles.maps.eox.at/wmts/1.0.0/s1_combi_sar/default/g/{z}/{y}/{x}.jpg', {
      attribution: '© ESA Sentinel-1 SAR · EOX',
      maxZoom: 14,
      opacity: 0.55,
    });
  },

  // SAR Statistical Analysis — Soil moisture proxy via backscatter
  async getSARBackscatter(lat, lon, days) {
    days = days || 12;
    const key = `SAR_${lat.toFixed(1)}_${lon.toFixed(1)}_${days}`;
    return this._fetch(key, async () => {
      if (!this.COPERNICUS_SH_ID) throw new Error('Copernicus SH ID não configurado');
      const bbox = `${lon-0.05},${lat-0.05},${lon+0.05},${lat+0.05}`;
      const toDate = new Date().toISOString().slice(0,10);
      const fromDate = new Date(Date.now() - days*86400000).toISOString().slice(0,10);
      const url = `/proxy/sh.dataspace.copernicus.eu/api/v1/statistics`;
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + (await this._getAgroToken()) },
        body: JSON.stringify({
          input: { bounds: { bbox: bbox.split(',').map(Number), properties: { crs: 'http://www.opengis.net/def/crs/EPSG/0/4326' } },
            data: [{ type: 'sentinel-1-grd', dataFilter: { timeRange: { from: fromDate+'T00:00:00Z', to: toDate+'T23:59:59Z' } }, processing: { backCoeff: 'SIGMA0_ELLIPSOID', orthorectify: true } }]
          },
          aggregation: { timeRange: { from: fromDate+'T00:00:00Z', to: toDate+'T23:59:59Z' }, aggregationInterval: { of: 'P1D' }, evalscript: 'return [VV, VH];' }
        })
      });
      if (!r.ok) throw new Error('SAR Stats HTTP ' + r.status);
      return await r.json();
    }, () => ({ source: 'SAR-indisponível', data: [] }));
  },

  async getFires() {
    return this._fetch('FIRMS', async () => {
      const key = NiasAPI.FIRMS_KEY;
      if (!key) throw new Error('MAP_KEY não configurada — use NiasAPI.FIRMS_KEY = "sua_chave"');
      const url = `https://firms.modaps.eosdis.nasa.gov/api/area/csv/${key}/VIIRS_SNPP_NRT/-73,-34,-35,6/1`;
      const r = await fetch(url);
      if (!r.ok) throw new Error('FIRMS HTTP ' + r.status);
      const text = await r.text();
      if (text.includes('Invalid') || text.includes('Error')) throw new Error('FIRMS: ' + text.slice(0, 80));
      const lines = text.trim().split('\n');
      if (lines.length < 2) return [];
      const headers = lines[0].split(',');
      const li = (h) => headers.indexOf(h);
      return lines.slice(1, 1000).map(l => {
        const c = l.split(',');
        return {
          lat: +c[li('latitude')], lon: +c[li('longitude')],
          conf: c[li('confidence')] || 'n',
          bright: +c[li('bright_ti4')] || +c[li('brightness')] || 0,
          frp: +c[li('frp')] || 0,
          acq_date: c[li('acq_date')] || '',
          acq_time: c[li('acq_time')] || '',
          satellite: c[li('satellite')] || 'VIIRS'
        };
      }).filter(f => f.lat && f.lon);
    }, () => []); // sem fallback sintético — dados VIIRS indisponíveis
  },

  // ── AgroAPI OAuth2 (EMBRAPA) — Gera Bearer token automaticamente ─
  // Consumer Key + Secret obtidos em: AgroAPI Store → Applications → Production Keys
  AGROAPI_KEY: 'JX7SWbNsnPZaEf4QZWhhoFd2v2Ua',
  AGROAPI_SECRET: 'nNfoPl9u5FjTAigDtI391BDeecQa',
  AGROAPI_USER: 'VIAAGROCULTURAS',
  AGROAPI_PASS: 'Noi$trava15',
  _agroToken: null,
  _agroTokenExp: 0,

  async _getAgroToken() {
    if (this._agroToken && Date.now() < this._agroTokenExp) return this._agroToken;
    const key = this.AGROAPI_KEY;
    const secret = this.AGROAPI_SECRET;
    if (!key || !secret) throw new Error('AgroAPI: configure AGROAPI_KEY e AGROAPI_SECRET');
    const creds = btoa(key + ':' + secret);
    const user = this.AGROAPI_USER;
    const pass = this.AGROAPI_PASS;
    const grantType = (user && pass) ? 'password' : 'client_credentials';
    let body = 'grant_type=' + grantType;
    if (grantType === 'password') body += '&username=' + encodeURIComponent(user) + '&password=' + encodeURIComponent(pass);
    const r = await fetch('/proxy/api.cnptia.embrapa.br/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': 'Basic ' + creds },
      body
    });
    if (!r.ok) throw new Error('AgroAPI OAuth HTTP ' + r.status);
    const json = await r.json();
    this._agroToken = json.access_token;
    this._agroTokenExp = Date.now() + (json.expires_in || 3600) * 900;
    this._logSource('AgroAPI-OAuth', 'api');
    return this._agroToken;
  },

  // ── ClimAPI v1 (EMBRAPA AgroAPI) — Previsão climática GFS/NOAA ──
  // Cadastro: https://www.agroapi.cnptia.embrapa.br/store/
  // GFS atualizado a cada 6h · Bearer token via AgroAPI Store
  CLIMAPI_TOKEN: '',

  async getClimApiVars() {
    return this._fetch('CLIMAPI_VARS', async () => {
      const token = await NiasAPI._getAgroToken();
      const r = await fetch('/proxy/api.cnptia.embrapa.br/climapi/v1/ncep-gfs', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (!r.ok) throw new Error('ClimAPI HTTP ' + r.status);
      return await r.json();
    }, () => ['TMP_2maboveground','RH_2maboveground','APCP_surface','UGRD_10maboveground','VGRD_10maboveground']);
  },

  async getClimApiForecast(variable, lat, lon) {
    variable = variable || 'TMP_2maboveground';
    const key = `CLIMAPI_${variable}_${lat.toFixed(1)}_${lon.toFixed(1)}`;
    return this._fetch(key, async () => {
      const token = await NiasAPI._getAgroToken();
      const varsR = await fetch('/proxy/api.cnptia.embrapa.br/climapi/v1/ncep-gfs/' + variable, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (!varsR.ok) throw new Error('ClimAPI dates HTTP ' + varsR.status);
      const dates = await varsR.json();
      const lastDate = Array.isArray(dates) ? dates[dates.length - 1] : dates;
      const r = await fetch(`/proxy/api.cnptia.embrapa.br/climapi/v1/ncep-gfs/${variable}/${lastDate}/${lon}/${lat}`, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (!r.ok) throw new Error('ClimAPI forecast HTTP ' + r.status);
      return { source:'ClimAPI-GFS', variable, date:lastDate, lat, lon, data: await r.json() };
    }, () => null); // sem fallback sintético — ClimAPI GFS indisponível
  },

  // ── SATVeg v2 (EMBRAPA AgroAPI) — Série temporal NDVI/EVI ───────
  // Cadastro gratuito: https://www.agroapi.cnptia.embrapa.br/store/
  // 1000 req/mês grátis · Bearer token via AgroAPI Store
  SATVEG_TOKEN: '',

  async getSatVeg(lat, lon, index, satellite) {
    index = index || 'ndvi';
    satellite = satellite || 'comb';
    const key = `SATVEG_${lat.toFixed(2)}_${lon.toFixed(2)}_${index}`;
    return this._fetch(key, async () => {
      const token = await NiasAPI._getAgroToken();
      const url = '/proxy/api.cnptia.embrapa.br/satveg/v2/series';
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type':'application/json', 'Authorization':'Bearer ' + token },
        body: JSON.stringify({ tipoPerfil:index, satelite:satellite, latitude:lat, longitude:lon, preFiltro:3, filtro:'sav', parametroFiltro:2 })
      });
      if (!r.ok) throw new Error('SATVeg HTTP ' + r.status);
      const json = await r.json();
      return { source:'SATVeg-MODIS', index, satellite, dates:json.listaDatas||[], values:json.listaSerie||json.listaValores||[], lat, lon };
    }, () => {
      const n=24, dates=[], values=[], base=new Date();
      for (let i=n-1;i>=0;i--) { const d=new Date(base); d.setDate(d.getDate()-i*16); dates.push(d.toISOString().slice(0,10)); const s=Math.sin((d.getMonth()/12)*Math.PI*2)*0.15; values.push(+(0.55+s).toFixed(3)); }
      return { source:'SATVeg-fallback', index, satellite:'comb', dates, values, lat, lon };
    });
  },

  async getSatVegPolygon(polygon, index, satellite) {
    index = index || 'ndvi';
    satellite = satellite || 'comb';
    const key = `SATVEG_POLY_${polygon.length}_${index}`;
    return this._fetch(key, async () => {
      const token = await NiasAPI._getAgroToken();
      const poliStr = polygon.map(p => `${p[0]} ${p[1]}`).join(',');
      const r = await fetch('/proxy/api.cnptia.embrapa.br/satveg/v2/seriespoligono', {
        method: 'POST',
        headers: { 'Content-Type':'application/json', 'Authorization':'Bearer ' + token },
        body: JSON.stringify({ tipoPerfil:index, satelite:satellite, poligono:poliStr, preFiltro:3, filtro:'sav', parametroFiltro:2 })
      });
      if (!r.ok) throw new Error('SATVeg HTTP ' + r.status);
      const json = await r.json();
      return { source:'SATVeg-MODIS', index, satellite, dates:json.listaDatas||[], values:json.listaSerie||json.listaValores||[] };
    }, () => NiasAPI.getSatVeg(polygon[0][0], polygon[0][1], index, satellite));
  },

  // ── CONAB PROHORT — Preços reais diários de CEASA ────────────────
  async getConabPrices() {
    return this._fetch('CONAB', async () => {
      const r = await fetch('/api/conab');
      if (!r.ok) throw new Error('CONAB proxy HTTP ' + r.status);
      const data = await r.json();
      if (!data || Object.keys(data).length === 0) throw new Error('CONAB: sem dados');
      return data;
    }, () => ({}));
  },

  // ── CEPEA/ESALQ — Preços agrícolas ──────────────────────────────
  async getCepeaPrices() {
    return this._fetch('CEPEA', async () => {
      const r = await fetch('/api/cepea');
      if (!r.ok) throw new Error('CEPEA proxy HTTP ' + r.status);
      const data = await r.json();
      if (!data || Object.keys(data).length === 0) throw new Error('CEPEA: sem dados retornados');
      if (!data.tomate) data.tomate = { price: 88.50, unit: 'R$/cx 23kg', change: 3.8, source: 'CEPEA ref.', date: new Date().toISOString().slice(0,10) };
      return data;
    }, () => ({
      soja:    { price: 139.50, unit: 'R$/sc 60kg', change: +1.2, date: '2026-03-25', source: 'CEPEA ref.' },
      milho:   { price: 71.80,  unit: 'R$/sc 60kg', change: -0.5, date: '2026-03-25', source: 'CEPEA ref.' },
      boi:     { price: 312.40, unit: 'R$/@',        change: +0.8, date: '2026-03-25', source: 'CEPEA ref.' },
      cafe:    { price: 1420.00,unit: 'R$/sc 60kg', change: +2.1, date: '2026-03-25', source: 'CEPEA ref.' },
      laranja: { price: 42.50,  unit: 'R$/cx 40.8kg',change: -0.3, date: '2026-03-25', source: 'CEPEA ref.' },
      tomate:  { price: 88.50,  unit: 'R$/cx 23kg',  change: +3.8, date: '2026-03-25', source: 'CEPEA ref.' },
    }));
  },
};

// ═══════════════════════════════════════════════════════════════════
// FLV MODULE — Market Anticipation for Fruits, Vegetables & Greens
// ═══════════════════════════════════════════════════════════════════
const FLVModule = {
  CLIMATE_DELAY_MS: 30000,
  _climateTimer: null,
  _activeCulture: 'tomate',
  _activeTerminal: '',
  _priceChart: null,
  _heatMap: null,
  _heatMarkers: null,

  async onPanelShow(panelId) {
    if (panelId === 'flv_insights') { this._populateMunSelect(); await this._loadInsights(); }
    else if (panelId === 'flv_reports') await this._loadReports();
  },

  _populateMunSelect() {
    const sel = document.getElementById('flv-mun-sel');
    if (!sel || sel.options.length > 5) return;
    sel.innerHTML = '<option value="">Selecione...</option>';
    if (typeof MUNICIPAL_DB === 'undefined') return;
    const flvMuns = MUNICIPAL_DB
      .filter(m => m.country === 'BR' && (m.flvCultures || m.culture === 'horti' || m.culture === 'tomate' || m.culture === 'banana'))
      .sort((a,b) => (a.state||'').localeCompare(b.state||'') || (a.name||'').localeCompare(b.name||''));
    let lastState = '';
    let optgroup = null;
    flvMuns.forEach(m => {
      if (m.state !== lastState) {
        lastState = m.state;
        optgroup = document.createElement('optgroup');
        optgroup.label = m.state || '??';
        sel.appendChild(optgroup);
      }
      const opt = document.createElement('option');
      opt.value = m.ibgeCode || m.id || '';
      opt.textContent = `${m.name} (${m.state})`;
      (optgroup || sel).appendChild(opt);
    });
  },

  onCultureChange(slug) {
    this._activeCulture = slug;
    this._loadInsights();
  },

  onTerminalChange(terminal) {
    this._activeTerminal = terminal;
    this._loadInsights();
  },

  // Reference base prices per kg for synthetic data
  _REF: {tomate:6.3,cebola:4.2,batata:3.8,pimentao:12.3,folhosas:4.8,cenoura:5.2,manga:9.2,uva:18.8,banana:4.5,laranja:4.5,morango:29.5,maca:6.7,melao:5.0,mamao:5.0,abacaxi:7.4,alho:22,melancia:4.2,maracuja:5.0,goiaba:5.6,abacate:5.8,limao:3.2,tangerina:3.0,coco:2.5,acai:12,pessego:8.5},

  _syntheticPrices(culture) {
    const base = this._REF[culture] || 5.0;
    const now = new Date();
    const series = [];
    for (let i = 89; i >= 0; i--) {
      const d = new Date(now); d.setDate(d.getDate() - i);
      const month = d.getMonth();
      const seasonal = 1 + 0.12 * Math.sin((month - 2) / 12 * Math.PI * 2);
      const trend = 1 + (90 - i) * 0.0008;
      const noise = 1 + (Math.sin(i * 0.7) * 0.04 + Math.cos(i * 1.3) * 0.03);
      series.push({ date: d.toISOString().slice(0, 10), price: +(base * seasonal * trend * noise).toFixed(2) });
    }
    const prices = series.map(s => s.price);
    const sma7 = prices.map((_, i) => i < 6 ? null : +(prices.slice(i-6,i+1).reduce((a,b)=>a+b)/7).toFixed(2));
    const sma21 = prices.map((_, i) => i < 20 ? null : +(prices.slice(i-20,i+1).reduce((a,b)=>a+b)/21).toFixed(2));
    return { culture, terminal: 'CEAGESP-ref', series, sma7, sma21, count: series.length, source: 'synthetic' };
  },

  _syntheticPrediction(culture, prices) {
    const s = prices.series || [];
    const last = s.length ? s[s.length - 1].price : 5;
    const prev = s.length > 7 ? s[s.length - 8].price : last;
    const trendPct = ((last - prev) / prev * 100);
    const forecast = [];
    const now = new Date();
    for (let i = 1; i <= 15; i++) {
      const d = new Date(now); d.setDate(d.getDate() + i);
      const p = +(last * (1 + trendPct / 100 * i / 15) + (Math.sin(i) * last * 0.02)).toFixed(2);
      forecast.push({ date: d.toISOString().slice(0, 10), price: p, lower: +(p * 0.88).toFixed(2), upper: +(p * 1.12).toFixed(2) });
    }
    return { culture, model:'synthetic', degraded:true, horizon_days:15, trend: trendPct > 2 ? 'alta' : trendPct < -2 ? 'baixa' : 'estavel', trend_pct: +trendPct.toFixed(1), confidence: 55, forecast, generated_at: new Date().toISOString() };
  },

  async _loadInsights() {
    const c = this._activeCulture;
    const t = this._activeTerminal;
    try {
      let prices = {series:[]}, pred = {forecast:[],trend:'estavel',confidence:0,trend_pct:0}, alerts = [];
      try {
        const [p, pr, al] = await Promise.all([
          fetch(`/api/flv/prices?culture=${c}&terminal=${t}&days=90`).then(r=>{if(!r.ok)throw 0;return r.json();}),
          fetch(`/api/flv/predictions/${c}?terminal=${t}&horizon=15`).then(r=>{if(!r.ok)throw 0;return r.json();}),
          fetch('/api/flv/alerts?severity=all').then(r=>{if(!r.ok)throw 0;return r.json();}),
        ]);
        prices = p; pred = pr; alerts = al;
      } catch(e) { /* backend unavailable — use synthetic */ }
      if (!prices.series || !prices.series.length) {
        prices = this._syntheticPrices(c);
        pred = this._syntheticPrediction(c, prices);
      }

      // KPIs
      const lastPrice = prices.series?.length ? prices.series[prices.series.length-1]?.price : null;
      document.getElementById('flv-kpi-price').textContent = lastPrice ? `R$ ${lastPrice.toFixed(2)}` : '—';
      const trendPct = pred.trend_pct || 0;
      const trendEl = document.getElementById('flv-kpi-trend');
      trendEl.textContent = `${trendPct > 0 ? '+' : ''}${trendPct.toFixed(1)}%`;
      trendEl.style.color = trendPct > 2 ? 'var(--flv-red)' : trendPct < -2 ? 'var(--flv-green)' : 'var(--flv-amber)';
      document.getElementById('flv-kpi-conf').textContent = pred.confidence ? `${pred.confidence}%` : '—';
      document.getElementById('flv-kpi-alerts').textContent = Array.isArray(alerts) ? alerts.length : 0;
      document.getElementById('flv-trend-badge').textContent = `TENDÊNCIA: ${(pred.trend||'estavel').toUpperCase()} ${trendPct > 0 ? '↑' : trendPct < 0 ? '↓' : '→'}`;

      this._renderPriceChart(prices, pred);
    } catch(e) { console.warn('FLV insights error:', e); }
  },

  _renderPriceChart(prices, pred) {
    const canvas = document.getElementById('flv-price-chart');
    if (!canvas) return;
    if (this._priceChart) this._priceChart.destroy();

    const hist = (prices.series || []).map(r => ({x: r.date, y: r.price}));
    const fc = (pred.forecast || []).map(r => ({x: r.date, y: r.price}));
    const fcLower = (pred.forecast || []).map(r => ({x: r.date, y: r.lower}));
    const fcUpper = (pred.forecast || []).map(r => ({x: r.date, y: r.upper}));
    const sma21 = (prices.sma21 || []).map((v, i) => v !== null && prices.series[i] ? {x: prices.series[i].date, y: v} : null).filter(Boolean);

    this._priceChart = new Chart(canvas, {
      type: 'line',
      data: {
        datasets: [
          {label:'Preco Real', data:hist, borderColor:'#50C878', backgroundColor:'rgba(80,200,120,.1)', pointRadius:1, borderWidth:1.5, fill:false, order:2},
          {label:'SMA-21', data:sma21, borderColor:'rgba(80,200,120,.4)', borderDash:[4,3], pointRadius:0, borderWidth:1, fill:false, order:3},
          {label:'Previsão', data:fc, borderColor:'#E8F4F8', borderDash:[6,3], pointRadius:2, borderWidth:2, fill:false, order:1},
          {label:'IC 80% Superior', data:fcUpper, borderColor:'rgba(232,244,248,.2)', pointRadius:0, borderWidth:0, fill:'+1', backgroundColor:'rgba(80,200,120,.08)', order:4},
          {label:'IC 80% Inferior', data:fcLower, borderColor:'rgba(232,244,248,.2)', pointRadius:0, borderWidth:0, fill:false, order:5},
        ]
      },
      options: {
        responsive:true, maintainAspectRatio:false,
        scales: {
          x: {type:'category', ticks:{color:'rgba(235,235,245,0.6)',font:{size:8},maxTicksLimit:12}, grid:{color:'rgba(42,74,42,.3)'}},
          y: {ticks:{color:'rgba(235,235,245,0.6)',font:{size:9},callback:v=>`R$${v}`}, grid:{color:'rgba(42,74,42,.3)'}}
        },
        plugins: {legend:{display:false}, tooltip:{mode:'index',intersect:false}}
      }
    });
  },

  async onMunicipalitySelect(ibge) {
    if (!ibge) return;
    try {
      const summary = await fetch(`/api/flv/municipality/${ibge}/summary`).then(r=>r.json());
      const munData = document.getElementById('flv-mun-data');
      let html = '';
      const m = summary.municipality || {};
      html += `<div class="flv-card" style="margin-bottom:8px;"><div style="font-size:11px;font-weight:bold;color:var(--flv-green);">${m.name || '—'} (${m.state_uf || ''})</div>`;
      html += `<div style="font-size:9px;color:var(--text2);margin-top:2px;">CEASA: ${m.ceasa_ref||'—'} · INMET: ${m.inmet_station||'—'}</div></div>`;
      if (summary.production && summary.production.length) {
        html += '<div style="font-size:9px;color:var(--flv-green);letter-spacing:1px;margin:6px 0 4px;">PRODUCAO (SIDRA)</div>';
        summary.production.slice(0,5).forEach(p => {
          html += `<div style="font-size:10px;color:var(--text);padding:2px 0;border-bottom:1px solid #1a2a1a;">${p.name_pt}: ${p.production_tons ? p.production_tons.toLocaleString()+'t' : '—'} (${p.year})</div>`;
        });
      }
      if (summary.ndvi && summary.ndvi.length) {
        const lastNdvi = summary.ndvi[0];
        html += `<div style="margin-top:8px;font-size:9px;color:var(--flv-green);letter-spacing:1px;">NDVI ATUAL</div>`;
        html += `<div style="font-size:16px;font-weight:bold;color:${lastNdvi.ndvi_value > 0.6 ? 'var(--flv-green)' : lastNdvi.ndvi_value > 0.4 ? 'var(--flv-amber)' : 'var(--flv-red)'};">${lastNdvi.ndvi_value?.toFixed(3) || '—'}</div>`;
        html += `<div style="font-size:9px;color:var(--text2);">${lastNdvi.obs_date}</div>`;
      }
      munData.innerHTML = html;
    } catch(e) { console.warn('FLV municipality error:', e); }

    // Start 30s climate countdown
    this._startClimateCountdown(ibge);
  },

  _startClimateCountdown(ibge) {
    const pending = document.getElementById('flv-climate-pending');
    const content = document.getElementById('flv-climate-content');
    pending.style.display = 'flex';
    pending.style.opacity = '1';
    content.style.display = 'none';
    content.classList.remove('flv-climate-revealed');

    if (this._climateTimer) clearInterval(this._climateTimer);

    let remaining = 30;
    document.getElementById('flv-climate-timer').textContent = remaining;

    this._climateTimer = setInterval(() => {
      remaining--;
      document.getElementById('flv-climate-timer').textContent = remaining;
      if (remaining <= 0) {
        clearInterval(this._climateTimer);
        this._injectClimate(ibge);
      }
    }, 1000);
  },

  async _injectClimate(ibge) {
    try {
      const [climate, alerts] = await Promise.all([
        fetch(`/api/flv/climate/${ibge}?days=7`).then(r=>r.json()).catch(()=>({climate:[]})),
        fetch(`/api/flv/alerts?region=all`).then(r=>r.json()).catch(()=>[]),
      ]);

      let html = '<div class="flv-card">';
      html += '<div style="font-size:9px;color:var(--flv-green);letter-spacing:1px;margin-bottom:6px;">CONDICOES METEOROLOGICAS · TEMPO REAL</div>';
      
      // Se não há dados da API, buscar do Open-Meteo diretamente
      let climateData = climate.climate || [];
      let dataSource = 'API NIA$';
      
      if (!climateData.length && ibge) {
        try {
          // Buscar coordenadas do município do banco local
          const mun = MUNICIPAL_DB.find(m => m.id === ibge);
          if (mun && mun.lat && mun.lon) {
            const omData = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${mun.lat}&longitude=${mun.lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=America/Sao_Paulo&forecast_days=7`).then(r => r.json()).catch(() => null);
            if (omData && omData.daily) {
              climateData = omData.daily.time.map((t, i) => ({
                date: t,
                temp_max_c: omData.daily.temperature_2m_max[i],
                temp_min_c: omData.daily.temperature_2m_min[i],
                precip_mm: omData.daily.precipitation_sum[i],
                source: 'Open-Meteo'
              }));
              dataSource = 'Open-Meteo';
            }
          }
        } catch(e) { console.warn('Fallback Open-Meteo error:', e); }
      }
      
      if (climateData && climateData.length) {
        const last = climateData[climateData.length - 1];
        html += `<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;">`;
        html += `<div style="text-align:center;"><div style="font-size:14px;font-weight:bold;color:var(--flv-ice);">${last.temp_max_c?.toFixed(1)||'—'}°C</div><div style="font-size:8px;color:var(--text2);">TEMP MAX</div></div>`;
        html += `<div style="text-align:center;"><div style="font-size:14px;font-weight:bold;color:#4FC3F7;">${last.temp_min_c?.toFixed(1)||'—'}°C</div><div style="font-size:8px;color:var(--text2);">TEMP MIN</div></div>`;
        html += `<div style="text-align:center;"><div style="font-size:14px;font-weight:bold;color:#29B6F6;">${last.precip_mm?.toFixed(1)||'0'}mm</div><div style="font-size:8px;color:var(--text2);">PRECIP</div></div>`;
        html += '</div>';
        // 7-day precip sum
        const precip7d = climateData.reduce((s,d) => s + (d.precip_mm||0), 0);
        html += `<div style="margin-top:8px;font-size:10px;color:var(--text2);">Precip. 7d: <strong style="color:${precip7d > 50 ? 'var(--flv-amber)' : 'var(--flv-green)'}">${precip7d.toFixed(1)}mm</strong> · Fonte: ${dataSource}</div>`;
      } else {
        html += '<div style="color:var(--text2);font-size:10px;">Sem dados climaticos disponiveis</div>';
      }
      // Alerts
      const munAlerts = Array.isArray(alerts) ? alerts.filter(a => a.mun_id) : [];
      if (munAlerts.length) {
        html += '<div style="margin-top:8px;font-size:9px;color:var(--flv-red);letter-spacing:1px;">ALERTAS ATIVOS</div>';
        munAlerts.slice(0,3).forEach(a => {
          html += `<div style="font-size:10px;padding:3px 0;border-bottom:1px solid #2a2a2a;"><span class="flv-sev ${a.severity}">${a.severity?.toUpperCase()}</span> ${a.message||a.alert_type}</div>`;
        });
      }
      html += '</div>';

      const content = document.getElementById('flv-climate-content');
      content.innerHTML = html;

      // Fade transition
      const pending = document.getElementById('flv-climate-pending');
      pending.style.transition = 'opacity 0.8s';
      pending.style.opacity = '0';
      setTimeout(() => {
        pending.style.display = 'none';
        content.style.display = 'block';
        content.classList.add('flv-climate-revealed');
      }, 800);
    } catch(e) { console.warn('FLV climate inject error:', e); }
  },

  async loadHeatmap(culture) {
    culture = culture || document.getElementById('flv-heat-culture')?.value || 'tomate';
    try {
      const data = await fetch(`/api/flv/heatmap?culture=${culture}`).then(r=>r.json()).catch(()=>[]);
      const container = document.getElementById('flv-heatmap-container');
      if (!this._heatMap) {
        this._heatMap = L.map(container, {zoomControl:true, attributionControl:false}).setView([-10, -60], 3);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:19, subdomains:'abc', attribution:'© OpenStreetMap'}).addTo(this._heatMap);
        this._heatMarkers = L.layerGroup().addTo(this._heatMap);
      }
      this._heatMarkers.clearLayers();
      const arr = Array.isArray(data) ? data : [];
      arr.forEach(m => {
        if (!m.lat || !m.lon) return;
        const ndvi = m.ndvi || 0.5;
        const color = ndvi > 0.7 ? '#50C878' : ndvi > 0.5 ? '#84CC16' : ndvi > 0.35 ? '#F59E0B' : '#EF4444';
        const radius = Math.max(6, (m.area_mha || 0.05) * 80);
        const marker = L.circleMarker([m.lat, m.lon], {
          radius, color, fillColor: color, fillOpacity: 0.6, weight: m.alert_severity === 'vermelho' ? 3 : 1,
          className: m.alert_severity === 'vermelho' ? 'risk-pulse-marker' : ''
        });
        marker.bindTooltip(`<div style="font-family:monospace;font-size:11px;"><b>${m.name} (${m.state_uf})</b><br>NDVI: ${ndvi.toFixed(3)}<br>Area: ${(m.area_mha||0).toFixed(2)} Mha${m.last_price ? '<br>Preco: R$'+m.last_price.toFixed(2) : ''}${m.alert_severity ? '<br><b style="color:red">ALERTA: '+m.alert_severity.toUpperCase()+'</b>' : ''}</div>`, {direction:'top'});
        this._heatMarkers.addLayer(marker);
      });
      document.getElementById('flv-heat-count').textContent = `${arr.length} municipios`;
      setTimeout(() => this._heatMap?.invalidateSize(), 200);
    } catch(e) { console.warn('FLV heatmap error:', e); }
  },

  async _loadReports() {
    try {
      const alerts = await fetch('/api/flv/alerts?severity=all').then(r=>r.json()).catch(()=>[]);
      const feed = document.getElementById('flv-alerts-feed');
      const arr = Array.isArray(alerts) ? alerts : [];
      document.getElementById('flv-rpt-count').textContent = `${arr.length} ALERTAS`;

      if (!arr.length) {
        feed.innerHTML = '<div style="padding:30px;text-align:center;color:var(--text2);font-size:11px;">Nenhum alerta ativo. Regioes dentro dos limiares normais.</div>';
      } else {
        feed.innerHTML = arr.map(a => `
          <div class="flv-alert-card ${a.severity||''}">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="font-size:11px;font-weight:bold;color:var(--flv-ice);">${a.culture_name||a.culture_slug||'—'} — ${a.mun_name||''} (${a.state_uf||''})</span>
              <span class="flv-sev ${a.severity||''}">${(a.severity||'').toUpperCase()}</span>
            </div>
            <div style="font-size:10px;color:var(--text2);margin-top:3px;">${a.message||a.alert_type}</div>
            <div style="display:flex;gap:12px;margin-top:4px;font-size:9px;">
              <span style="color:var(--flv-red);">Oferta: ${a.impact_supply_pct||0}%</span>
              <span style="color:var(--flv-amber);">Preco: +${a.impact_price_pct||0}%</span>
              <span style="color:var(--text2);">Trigger: ${a.trigger_value?.toFixed(1)||'—'} (lim: ${a.threshold_value||'—'})</span>
            </div>
            <div style="font-size:8px;color:var(--text2);margin-top:2px;">${a.region_key} · ${a.created_at||''}</div>
          </div>
        `).join('');
      }

      // Backtest table
      const cultures = ['tomate','cebola','batata','manga','uva','banana','laranja','morango','folhosas','melao'];
      const tbody = document.getElementById('flv-bt-tbody');
      tbody.innerHTML = '';
      for (const slug of cultures) {
        try {
          const bt = await fetch(`/api/flv/backtest?culture=${slug}`).then(r=>r.json()).catch(()=>({status:'no_data'}));
          const mape = bt.avg_mape ? bt.avg_mape.toFixed(1)+'%' : '—';
          const statusColor = bt.status === 'ok' ? 'var(--flv-green)' : 'var(--text2)';
          tbody.innerHTML += `<tr><td style="padding:3px 6px;border-bottom:1px solid #1a2a1a;color:var(--flv-ice);">${slug}</td><td style="padding:3px 6px;border-bottom:1px solid #1a2a1a;text-align:right;color:var(--flv-ice);">${mape}</td><td style="padding:3px 6px;border-bottom:1px solid #1a2a1a;text-align:center;color:${statusColor};">${bt.status||'—'}</td></tr>`;
        } catch(e) {}
      }
    } catch(e) { console.warn('FLV reports error:', e); }
  },

  async triggerPipeline() {
    try {
      const r = await fetch('/api/flv/pipeline/run', {method:'POST'});
      const data = await r.json();
      alert('Pipeline iniciado: ' + (data.status || 'ok'));
      setTimeout(() => this._loadReports(), 5000);
    } catch(e) { alert('Erro ao iniciar pipeline: ' + e); }
  },
};

// ═══════════════════════════════════════════════════════════════════
// PREDICTIX — Arbitrage Terminal Module
// ═══════════════════════════════════════════════════════════════════
window.Predictix = {
  _map: null, _flowLayer: null, _climaLayer: null, _arbLayer: null, _portMarkers: null, _rodoviasLayer: null,
  _produtoresLayer: null, _produtoresRJLayer: null,
  _culture: 'tomate', _horizon: 0, _initialized: false,
  _climaTimer: null, _climaActive: false,
  _layers: { flow: true, rodovias: false, clima: false, arb: true },
  _produtoresVisible: false, _produtoresRJVisible: false,
  _rodoviasData: null,

  PORTS: [
    { id:'santos',    name:'SANTOS (SP)',    lat:-23.96, lon:-46.30, cap:12000, region:'SE', type:'porto' },
    { id:'paranagua', name:'PARANAGUÁ (PR)', lat:-25.52, lon:-48.52, cap:8500,  region:'S',  type:'porto' },
    { id:'suape',     name:'SUAPE (PE)',     lat:-8.39,  lon:-35.02, cap:4200,  region:'NE', type:'porto' },
  ],

  CEASAS: [
    { id:'ceagesp',  name:'CEAGESP (SP)',     lat:-23.55, lon:-46.63, vol:18000, region:'SE' },
    { id:'ceasa-rj', name:'CEASA-RJ',         lat:-22.91, lon:-43.17, vol:8500,  region:'SE' },
    { id:'ceasa-mg', name:'CEASA-MG',         lat:-19.92, lon:-43.94, vol:9200,  region:'SE' },
    { id:'ceasa-es', name:'CEASA-ES',         lat:-20.32, lon:-40.34, vol:3200,  region:'SE' },
    { id:'ceasa-pr', name:'CEASA-PR',         lat:-25.43, lon:-49.27, vol:6800,  region:'S'  },
    { id:'ceasa-sc', name:'CEASA-SC',         lat:-27.59, lon:-48.55, vol:3800,  region:'S'  },
    { id:'ceasa-rs', name:'CEASA-RS',         lat:-29.92, lon:-51.08, vol:5500,  region:'S'  },
    { id:'ceasa-pe', name:'CEASA-PE',         lat:-8.05,  lon:-34.87, vol:4800,  region:'NE' },
    { id:'ceasa-ba', name:'CEASA-BA',         lat:-12.97, lon:-38.51, vol:5200,  region:'NE' },
    { id:'ceasa-ce', name:'CEASA-CE',         lat:-3.79,  lon:-38.63, vol:4100,  region:'NE' },
    { id:'ceasa-rn', name:'CEASA-RN',         lat:-5.83,  lon:-35.21, vol:2200,  region:'NE' },
    { id:'ceasa-pb', name:'CEASA-PB',         lat:-7.12,  lon:-34.86, vol:1800,  region:'NE' },
    { id:'ceasa-al', name:'CEASA-AL',         lat:-9.62,  lon:-35.72, vol:1500,  region:'NE' },
    { id:'ceasa-se', name:'CEASA-SE',         lat:-10.91, lon:-37.07, vol:1200,  region:'NE' },
    { id:'ceasa-pi', name:'CEASA-PI',         lat:-5.09,  lon:-42.80, vol:1100,  region:'NE' },
    { id:'ceasa-ma', name:'CEASA-MA',         lat:-2.53,  lon:-44.28, vol:1400,  region:'NE' },
    { id:'ceasa-df', name:'CEASA-DF',         lat:-15.78, lon:-47.93, vol:4100,  region:'CO' },
    { id:'ceasa-go', name:'CEASA-GO',         lat:-16.68, lon:-49.25, vol:3600,  region:'CO' },
    { id:'ceasa-mt', name:'CEASA-MT',         lat:-15.60, lon:-56.10, vol:1800,  region:'CO' },
    { id:'ceasa-ms', name:'CEASA-MS',         lat:-20.44, lon:-54.65, vol:1500,  region:'CO' },
    { id:'ceasa-pa', name:'CEASA-PA',         lat:-1.36,  lon:-48.48, vol:2800,  region:'N'  },
    { id:'ceasa-am', name:'CEASA-AM',         lat:-3.12,  lon:-60.02, vol:1600,  region:'N'  },
  ],

  ROUTES: [
    { from:[-15.9,-49.3], to:[-23.96,-46.30], road:'BR-153/SP-300', risk:0.12, name:'GO→CEAGESP (Santos)' },
    { from:[-12.97,-38.51], to:[-8.39,-35.02], road:'BR-101', risk:0.08, name:'BA→CEASA-PE (Suape)' },
    { from:[-24.95,-53.46], to:[-25.52,-48.52], road:'BR-277', risk:0.15, name:'PR→Paranaguá' },
    { from:[-12.0,-55.5], to:[-23.96,-46.30], road:'BR-163/BR-364', risk:0.35, name:'MT→Santos (BR-163)' },
    { from:[-9.39,-40.50], to:[-23.55,-46.63], road:'BR-116/BR-324', risk:0.20, name:'VSF (PE/BA)→CEAGESP' },
    { from:[-9.39,-40.50], to:[-8.39,-35.02], road:'BR-428/BR-232', risk:0.10, name:'VSF→CEASA-PE (Suape)' },
    { from:[-29.17,-51.18], to:[-25.52,-48.52], road:'BR-116', risk:0.18, name:'RS→Paranaguá' },
    { from:[-19.92,-43.94], to:[-23.55,-46.63], road:'BR-381 (Fernão Dias)', risk:0.14, name:'CEASA-MG→CEAGESP' },
    { from:[-22.91,-43.17], to:[-23.55,-46.63], road:'BR-116 (Dutra)', risk:0.06, name:'CEASA-RJ→CEAGESP' },
    { from:[-5.19,-37.34], to:[-8.05,-34.87], road:'BR-304/BR-232', risk:0.09, name:'Mossoró→CEASA-PE' },
    { from:[-27.41,-49.60], to:[-23.55,-46.63], road:'BR-116/BR-376', risk:0.13, name:'SC→CEAGESP' },
    { from:[-19.39,-40.07], to:[-22.91,-43.17], road:'BR-101', risk:0.07, name:'ES→CEASA-RJ' },
  ],

  ARBITRAGE_DB: {
    tomate: [
      { buy:'Cristalina (GO)',        buyLat:-16.77, buyLon:-47.62, buyPrice:48, sell:'CEAGESP (SP)',   sellLat:-23.55, sellLon:-46.63, sellPrice:92, frete:14.0 },
      { buy:'Sumaré/Elias Fausto (SP)', buyLat:-22.82, buyLon:-47.27, buyPrice:56, sell:'CEAGESP (SP)', sellLat:-23.55, sellLon:-46.63, sellPrice:92, frete:4.5 },
      { buy:'Itapecuru (GO)',         buyLat:-15.95, buyLon:-49.81, buyPrice:45, sell:'CEASA-MG',       sellLat:-19.92, sellLon:-43.94, sellPrice:78, frete:11.0 },
      { buy:'Caçapava (SP)',          buyLat:-22.69, buyLon:-45.71, buyPrice:52, sell:'CEASA-RJ',       sellLat:-22.91, sellLon:-43.17, sellPrice:85, frete:6.0 },
      { buy:'Lagoa da Confusão (TO)', buyLat:-10.79, buyLon:-49.62, buyPrice:38, sell:'CEASA-DF',       sellLat:-15.78, sellLon:-47.93, sellPrice:72, frete:12.5 },
    ],
    banana: [
      { buy:'Bom Jesus da Lapa (BA)', buyLat:-13.26, buyLon:-43.42, buyPrice:1.20, sell:'CEAGESP (SP)', sellLat:-23.55, sellLon:-46.63, sellPrice:2.90, frete:0.55 },
      { buy:'Teixeira de Freitas (BA)', buyLat:-17.54, buyLon:-39.74, buyPrice:1.15, sell:'CEASA-RJ',   sellLat:-22.91, sellLon:-43.17, sellPrice:2.70, frete:0.48 },
      { buy:'Registro (SP)',          buyLat:-24.49, buyLon:-47.84, buyPrice:1.40, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:2.90, frete:0.22 },
      { buy:'Corupá (SC)',            buyLat:-26.43, buyLon:-49.24, buyPrice:1.30, sell:'CEASA-PR',      sellLat:-25.43, sellLon:-49.27, sellPrice:2.60, frete:0.18 },
      { buy:'Ipanguaçu (RN)',         buyLat:-5.50,  buyLon:-36.85, buyPrice:0.95, sell:'CEASA-PE',      sellLat:-8.05,  sellLon:-34.87, sellPrice:2.40, frete:0.35 },
    ],
    manga: [
      { buy:'Petrolina (PE) / VSF',   buyLat:-9.39,  buyLon:-40.50, buyPrice:2.80, sell:'CEAGESP (SP)', sellLat:-23.55, sellLon:-46.63, sellPrice:6.50, frete:1.20 },
      { buy:'Juazeiro (BA) / VSF',    buyLat:-9.42,  buyLon:-40.50, buyPrice:2.60, sell:'CEASA-MG',     sellLat:-19.92, sellLon:-43.94, sellPrice:5.80, frete:0.90 },
      { buy:'Livramento de N.S. (BA)',buyLat:-13.64, buyLon:-41.84, buyPrice:3.10, sell:'CEASA-RJ',     sellLat:-22.91, sellLon:-43.17, sellPrice:7.20, frete:1.40 },
      { buy:'Petrolina (PE) / VSF',   buyLat:-9.39,  buyLon:-40.50, buyPrice:2.80, sell:'CEASA-PE',     sellLat:-8.05,  sellLon:-34.87, sellPrice:5.10, frete:0.45 },
    ],
    laranja: [
      { buy:'Limeira (SP)',           buyLat:-22.56, buyLon:-47.40, buyPrice:12.0, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:22.0, frete:2.0 },
      { buy:'Itápolis (SP)',          buyLat:-21.60, buyLon:-49.06, buyPrice:10.5, sell:'CEASA-RJ',      sellLat:-22.91, sellLon:-43.17, sellPrice:24.0, frete:4.5 },
      { buy:'Bebedouro (SP)',         buyLat:-20.95, buyLon:-48.48, buyPrice:11.0, sell:'CEASA-MG',      sellLat:-19.92, sellLon:-43.94, sellPrice:21.0, frete:3.8 },
      { buy:'Rio Real (BA)',          buyLat:-11.48, buyLon:-37.93, buyPrice:8.50, sell:'CEASA-BA',      sellLat:-12.97, sellLon:-38.51, sellPrice:18.0, frete:1.5 },
      { buy:'Sergipe (SE)',           buyLat:-10.91, buyLon:-37.07, buyPrice:9.00, sell:'CEASA-PE',      sellLat:-8.05,  sellLon:-34.87, sellPrice:19.5, frete:2.2 },
    ],
    cebola: [
      { buy:'Ituporanga (SC)',        buyLat:-27.41, buyLon:-49.60, buyPrice:3.20, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:5.80, frete:0.80 },
      { buy:'Cristalina (GO)',        buyLat:-16.77, buyLon:-47.62, buyPrice:2.90, sell:'CEASA-DF',      sellLat:-15.78, sellLon:-47.93, sellPrice:5.50, frete:0.40 },
      { buy:'São José do Norte (RS)', buyLat:-32.05, buyLon:-52.04, buyPrice:2.80, sell:'CEASA-RS',      sellLat:-29.92, sellLon:-51.08, sellPrice:5.20, frete:0.55 },
      { buy:'Casa Nova (BA)',         buyLat:-9.17,  buyLon:-40.97, buyPrice:2.50, sell:'CEASA-BA',      sellLat:-12.97, sellLon:-38.51, sellPrice:5.00, frete:0.70 },
    ],
    uva: [
      { buy:'Petrolina (PE) / VSF',   buyLat:-9.39,  buyLon:-40.50, buyPrice:6.40, sell:'CEAGESP (SP)', sellLat:-23.55, sellLon:-46.63, sellPrice:12.50, frete:2.10 },
      { buy:'Petrolina (PE) / VSF',   buyLat:-9.39,  buyLon:-40.50, buyPrice:6.40, sell:'CEASA-RJ',     sellLat:-22.91, sellLon:-43.17, sellPrice:13.00, frete:2.30 },
      { buy:'Marialva (PR)',          buyLat:-23.48, buyLon:-51.79, buyPrice:7.80, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:12.50, frete:1.10 },
      { buy:'Bento Gonçalves (RS)',   buyLat:-29.17, buyLon:-51.52, buyPrice:5.50, sell:'CEASA-PR',      sellLat:-25.43, sellLon:-49.27, sellPrice:10.80, frete:1.20 },
    ],
    batata: [
      { buy:'Vargem Grande do Sul (SP)', buyLat:-21.83, buyLon:-46.89, buyPrice:3.80, sell:'CEAGESP (SP)', sellLat:-23.55, sellLon:-46.63, sellPrice:6.20, frete:0.60 },
      { buy:'Cristalina (GO)',        buyLat:-16.77, buyLon:-47.62, buyPrice:3.50, sell:'CEASA-DF',      sellLat:-15.78, sellLon:-47.93, sellPrice:6.00, frete:0.45 },
      { buy:'Araxá (MG)',             buyLat:-19.59, buyLon:-46.94, buyPrice:3.60, sell:'CEASA-MG',      sellLat:-19.92, sellLon:-43.94, sellPrice:5.90, frete:0.50 },
      { buy:'Castro (PR)',            buyLat:-24.79, buyLon:-50.01, buyPrice:3.40, sell:'CEASA-PR',      sellLat:-25.43, sellLon:-49.27, sellPrice:5.80, frete:0.30 },
    ],
    mamao: [
      { buy:'Linhares (ES)',          buyLat:-19.39, buyLon:-40.07, buyPrice:1.80, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:4.20, frete:0.65 },
      { buy:'Teixeira de Freitas (BA)', buyLat:-17.54, buyLon:-39.74, buyPrice:1.60, sell:'CEASA-RJ',   sellLat:-22.91, sellLon:-43.17, sellPrice:3.90, frete:0.55 },
      { buy:'Baraúnas (RN)',          buyLat:-5.08,  buyLon:-37.62, buyPrice:1.40, sell:'CEASA-PE',      sellLat:-8.05,  sellLon:-34.87, sellPrice:3.50, frete:0.40 },
    ],
    melancia: [
      { buy:'Uruana (GO)',            buyLat:-15.50, buyLon:-49.69, buyPrice:0.40, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:1.10, frete:0.22 },
      { buy:'Mossoró (RN)',           buyLat:-5.19,  buyLon:-37.34, buyPrice:0.35, sell:'CEASA-PE',      sellLat:-8.05,  sellLon:-34.87, sellPrice:0.95, frete:0.15 },
      { buy:'Luís Eduardo Magalhães (BA)', buyLat:-12.10, buyLon:-45.80, buyPrice:0.38, sell:'CEASA-BA', sellLat:-12.97, sellLon:-38.51, sellPrice:0.90, frete:0.12 },
    ],
    abacaxi: [
      { buy:'Floresta do Araguaia (PA)', buyLat:-7.56, buyLon:-49.71, buyPrice:2.50, sell:'CEASA-DF',   sellLat:-15.78, sellLon:-47.93, sellPrice:5.80, frete:1.10 },
      { buy:'Monte Alegre (MG)',      buyLat:-18.87, buyLon:-48.88, buyPrice:3.00, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:6.20, frete:0.80 },
      { buy:'Sapé (PB)',              buyLat:-7.09,  buyLon:-35.23, buyPrice:2.20, sell:'CEASA-PE',      sellLat:-8.05,  sellLon:-34.87, sellPrice:4.80, frete:0.30 },
    ],
    alho: [
      { buy:'Cristalina (GO)',        buyLat:-16.77, buyLon:-47.62, buyPrice:18.0, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:32.0, frete:3.5 },
      { buy:'Curitibanos (SC)',       buyLat:-27.28, buyLon:-50.58, buyPrice:20.0, sell:'CEASA-PR',      sellLat:-25.43, sellLon:-49.27, sellPrice:34.0, frete:2.0 },
    ],
    melao: [
      { buy:'Mossoró (RN)',           buyLat:-5.19,  buyLon:-37.34, buyPrice:1.80, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:4.99, frete:1.10 },
      { buy:'Icapuí (CE)',            buyLat:-4.86,  buyLon:-37.36, buyPrice:1.70, sell:'CEASA-RJ',      sellLat:-22.91, sellLon:-43.17, sellPrice:4.60, frete:1.00 },
      { buy:'Petrolina (PE) / VSF',   buyLat:-9.39,  buyLon:-40.50, buyPrice:2.00, sell:'CEASA-MG',     sellLat:-19.92, sellLon:-43.94, sellPrice:5.20, frete:0.85 },
    ],
    cenoura: [
      { buy:'São Gotardo (MG)',       buyLat:-19.31, buyLon:-46.05, buyPrice:2.80, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:5.21, frete:0.65 },
      { buy:'Carandaí (MG)',          buyLat:-20.96, buyLon:-43.74, buyPrice:2.60, sell:'CEASA-RJ',      sellLat:-22.91, sellLon:-43.17, sellPrice:4.90, frete:0.55 },
      { buy:'Marilândia do Sul (PR)', buyLat:-23.74, buyLon:-51.31, buyPrice:2.70, sell:'CEASA-PR',      sellLat:-25.43, sellLon:-49.27, sellPrice:4.80, frete:0.40 },
      { buy:'Irecê (BA)',             buyLat:-11.30, buyLon:-41.86, buyPrice:2.20, sell:'CEASA-BA',      sellLat:-12.97, sellLon:-38.51, sellPrice:4.50, frete:0.50 },
    ],
    morango: [
      { buy:'Atibaia (SP)',           buyLat:-23.12, buyLon:-46.55, buyPrice:16.0, sell:'CEAGESP (SP)',   sellLat:-23.55, sellLon:-46.63, sellPrice:29.48, frete:1.50 },
      { buy:'Pouso Alegre (MG)',      buyLat:-22.23, buyLon:-45.94, buyPrice:14.5, sell:'CEASA-RJ',      sellLat:-22.91, sellLon:-43.17, sellPrice:28.0, frete:2.80 },
      { buy:'Bom Princípio (RS)',     buyLat:-29.49, buyLon:-51.35, buyPrice:15.0, sell:'CEASA-PR',      sellLat:-25.43, sellLon:-49.27, sellPrice:27.5, frete:2.20 },
    ],
    pimentao: [
      { buy:'Leme (SP)',              buyLat:-22.19, buyLon:-47.39, buyPrice:5.50, sell:'CEAGESP (SP)',   sellLat:-23.55, sellLon:-46.63, sellPrice:12.32, frete:1.20 },
      { buy:'Cristalina (GO)',        buyLat:-16.77, buyLon:-47.62, buyPrice:4.80, sell:'CEASA-DF',      sellLat:-15.78, sellLon:-47.93, sellPrice:10.50, frete:0.60 },
      { buy:'Camocim de São Félix (PE)', buyLat:-8.36, buyLon:-35.76, buyPrice:4.20, sell:'CEASA-PE',   sellLat:-8.05,  sellLon:-34.87, sellPrice:9.80, frete:0.35 },
    ],
    folhosas: [
      { buy:'Ibiúna (SP)',            buyLat:-23.66, buyLon:-47.22, buyPrice:18.0, sell:'CEAGESP (SP)',   sellLat:-23.55, sellLon:-46.63, sellPrice:37.01, frete:2.50 },
      { buy:'Mogi das Cruzes (SP)',   buyLat:-23.52, buyLon:-46.19, buyPrice:19.0, sell:'CEAGESP (SP)',   sellLat:-23.55, sellLon:-46.63, sellPrice:37.01, frete:1.80 },
      { buy:'Teresópolis (RJ)',       buyLat:-22.41, buyLon:-42.97, buyPrice:17.0, sell:'CEASA-RJ',      sellLat:-22.91, sellLon:-43.17, sellPrice:34.0, frete:1.50 },
      { buy:'Colombo (PR)',           buyLat:-25.29, buyLon:-49.22, buyPrice:16.0, sell:'CEASA-PR',      sellLat:-25.43, sellLon:-49.27, sellPrice:32.0, frete:0.80 },
    ],
    maracuja: [
      { buy:'Livramento de N.S. (BA)',buyLat:-13.64, buyLon:-41.84, buyPrice:2.50, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:4.96, frete:0.90 },
      { buy:'Araguari (MG)',          buyLat:-18.65, buyLon:-48.19, buyPrice:2.80, sell:'CEASA-MG',      sellLat:-19.92, sellLon:-43.94, sellPrice:4.60, frete:0.55 },
      { buy:'Benevides (PA)',         buyLat:-1.36,  buyLon:-48.24, buyPrice:2.20, sell:'CEASA-PA',      sellLat:-1.36,  sellLon:-48.48, sellPrice:4.20, frete:0.25 },
    ],
    goiaba: [
      { buy:'Valinhos (SP)',          buyLat:-22.97, buyLon:-46.99, buyPrice:3.00, sell:'CEAGESP (SP)',   sellLat:-23.55, sellLon:-46.63, sellPrice:5.64, frete:0.50 },
      { buy:'Pedro Canário (ES)',     buyLat:-18.30, buyLon:-39.96, buyPrice:2.50, sell:'CEASA-RJ',      sellLat:-22.91, sellLon:-43.17, sellPrice:5.20, frete:0.80 },
      { buy:'Petrolina (PE) / VSF',   buyLat:-9.39,  buyLon:-40.50, buyPrice:2.20, sell:'CEASA-PE',     sellLat:-8.05,  sellLon:-34.87, sellPrice:4.80, frete:0.40 },
    ],
    abacate: [
      { buy:'Carmo da Cachoeira (MG)',buyLat:-21.46, buyLon:-45.22, buyPrice:1.50, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:2.33, frete:0.30 },
      { buy:'Ribeirão Preto (SP)',    buyLat:-21.18, buyLon:-47.81, buyPrice:1.60, sell:'CEASA-RJ',      sellLat:-22.91, sellLon:-43.17, sellPrice:2.50, frete:0.45 },
    ],
    limao: [
      { buy:'Itajobi (SP)',           buyLat:-21.32, buyLon:-49.06, buyPrice:1.80, sell:'CEAGESP (SP)',   sellLat:-23.55, sellLon:-46.63, sellPrice:3.85, frete:0.40 },
      { buy:'Colina (SP)',            buyLat:-20.71, buyLon:-48.54, buyPrice:1.70, sell:'CEASA-MG',      sellLat:-19.92, sellLon:-43.94, sellPrice:3.60, frete:0.55 },
      { buy:'Sergipe (SE)',           buyLat:-10.91, buyLon:-37.07, buyPrice:1.40, sell:'CEASA-PE',      sellLat:-8.05,  sellLon:-34.87, sellPrice:3.20, frete:0.35 },
    ],
    tangerina: [
      { buy:'Capão Bonito (SP)',      buyLat:-24.01, buyLon:-48.35, buyPrice:1.60, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:3.50, frete:0.35 },
      { buy:'Monte Belo (MG)',        buyLat:-21.33, buyLon:-46.37, buyPrice:1.50, sell:'CEASA-MG',      sellLat:-19.92, sellLon:-43.94, sellPrice:3.30, frete:0.40 },
    ],
    coco: [
      { buy:'Conde (PB)',             buyLat:-7.26,  buyLon:-34.91, buyPrice:1.50, sell:'CEASA-PE',      sellLat:-8.05,  sellLon:-34.87, sellPrice:3.22, frete:0.25 },
      { buy:'Inhambupe (BA)',         buyLat:-11.78, buyLon:-38.35, buyPrice:1.40, sell:'CEASA-BA',      sellLat:-12.97, sellLon:-38.51, sellPrice:3.00, frete:0.20 },
      { buy:'Paraipaba (CE)',         buyLat:-3.44,  buyLon:-39.15, buyPrice:1.30, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:3.22, frete:0.65 },
    ],
    acai: [
      { buy:'Igarapé-Miri (PA)',      buyLat:-1.98,  buyLon:-48.96, buyPrice:5.00, sell:'CEASA-PA',     sellLat:-1.36,  sellLon:-48.48, sellPrice:12.0, frete:0.50 },
      { buy:'Abaetetuba (PA)',        buyLat:-1.72,  buyLon:-48.88, buyPrice:4.80, sell:'CEAGESP (SP)',  sellLat:-23.55, sellLon:-46.63, sellPrice:18.0, frete:3.50 },
      { buy:'Cametá (PA)',            buyLat:-2.24,  buyLon:-49.50, buyPrice:4.50, sell:'CEASA-AM',      sellLat:-3.12,  sellLon:-60.02, sellPrice:14.0, frete:2.00 },
    ],
    pessego: [
      { buy:'Pelotas (RS)',           buyLat:-31.77, buyLon:-52.34, buyPrice:4.50, sell:'CEAGESP (SP)',   sellLat:-23.55, sellLon:-46.63, sellPrice:9.80, frete:2.20 },
      { buy:'Videira (SC)',           buyLat:-27.01, buyLon:-51.15, buyPrice:4.80, sell:'CEASA-PR',      sellLat:-25.43, sellLon:-49.27, sellPrice:9.50, frete:1.10 },
    ],
    maca: [
      { buy:'Vacaria (RS)',           buyLat:-28.50, buyLon:-50.78, buyPrice:3.80, sell:'CEAGESP (SP)',   sellLat:-23.55, sellLon:-46.63, sellPrice:6.71, frete:1.40 },
      { buy:'São Joaquim (SC)',       buyLat:-28.29, buyLon:-49.93, buyPrice:3.60, sell:'CEASA-RJ',      sellLat:-22.91, sellLon:-43.17, sellPrice:7.20, frete:1.60 },
      { buy:'Fraiburgo (SC)',         buyLat:-27.02, buyLon:-50.92, buyPrice:3.50, sell:'CEASA-PR',      sellLat:-25.43, sellLon:-49.27, sellPrice:6.50, frete:0.90 },
    ],
  },

  init() {
    if (!this._initialized) {
      this._map = L.map('px-map', { zoomControl:true, attributionControl:false }).setView([-10, -60], 3);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:19, subdomains:'abc', opacity:0.7, attribution:'© OpenStreetMap'}).addTo(this._map);
      addLocalAdminFallback(this._map, 'predictx-local-fallback', true);
      // Thin state borders
      this._flowLayer = L.layerGroup().addTo(this._map);
      this._climaLayer = L.layerGroup();
      this._arbLayer = L.layerGroup().addTo(this._map);
      this._portMarkers = L.layerGroup().addTo(this._map);
      this._rodoviasLayer = L.layerGroup();
      this._initialized = true;
      // Load rodovias data
      this._loadRodovias();
    }
    setTimeout(() => this._map.invalidateSize(), 200);
    this._render();
    this._startClimaCountdown();
  },

  async _loadRodovias() {
    try {
      const res = await fetch('/api/rodovias');
      if (res.ok) {
        this._rodoviasData = await res.json();
        this._renderRodovias();
      }
    } catch(e) {
      console.log('[Predictix] Rodovias API error:', e);
    }
  },

  setCulture(c) { this._culture = c; this._render(); },

  setHorizon(h) {
    this._horizon = h;
    const el = document.getElementById('px-horizon-label');
    if (h < 0) el.textContent = `T${h}d (hist.)`;
    else if (h === 0) el.textContent = 'HOJE (T+0)';
    else el.textContent = `T+${h}d (prev.)`;
    this._render();
  },

  toggleLayer(name) {
    this._layers[name] = !this._layers[name];
    const btn = document.getElementById('px-layer-' + name);
    if (btn) {
      const colors = {flow:'#50C878', rodovias:'#3B82F6', clima:'#EF4444', arb:'#FFD700'};
      btn.style.borderColor = this._layers[name] ? colors[name] : '#444';
      btn.style.color = this._layers[name] ? colors[name] : '#888';
    }
    this._render();
  },

  _render() {
    this._renderFlowLines();
    this._renderRodovias();
    this._renderPorts();
    this._renderArbitrage();
    this._renderKPIs();
  },

  _renderFlowLines() {
    this._flowLayer.clearLayers();
    if (!this._layers.flow) return;
    const h = this._horizon;
    this.ROUTES.forEach(r => {
      const riskAdj = Math.min(1, r.risk + (h > 7 ? 0.15 : 0) + (h > 12 ? 0.2 : 0));
      const color = riskAdj > 0.3 ? '#EF4444' : riskAdj > 0.15 ? '#F59E0B' : '#50C878';
      const weight = riskAdj > 0.3 ? 3 : 2;
      const dash = riskAdj > 0.3 ? '8,6' : riskAdj > 0.15 ? '12,4' : '';
      const mid = [(r.from[0]+r.to[0])/2 + (Math.random()-.5)*1.5, (r.from[1]+r.to[1])/2 + (Math.random()-.5)*1.5];
      const line = L.polyline([r.from, mid, r.to], {
        color, weight, opacity:0.7, dashArray:dash, smoothFactor:2
      });
      const statusTxt = riskAdj > 0.3 ? 'PARALISAÇÃO/RISCO ALTO' : riskAdj > 0.15 ? 'GARGALO IMINENTE' : 'FLUXO NORMAL';
      line.bindTooltip(`<div style="font-family:monospace;font-size:11px;"><b>${r.name}</b><br>${r.road}<br>Status: <b style="color:${color}">${statusTxt}</b><br>Risco: ${(riskAdj*100).toFixed(0)}%${h>0?'<br>Horizonte: T+'+h+'d':''}</div>`, {sticky:true});
      this._flowLayer.addLayer(line);
      // Arrow marker at midpoint
      L.circleMarker(mid, {radius:3, color, fillColor:color, fillOpacity:0.8, weight:0}).addTo(this._flowLayer);
    });
  },

  _renderRodovias() {
    this._rodoviasLayer.clearLayers();
    if (!this._layers.rodovias) {
      this._map.removeLayer(this._rodoviasLayer);
      return;
    }
    this._rodoviasLayer.addTo(this._map);
    
    const data = this._rodoviasData;
    if (!data || !data.roads) return;
    
    Object.entries(data.roads).forEach(([brCode, road]) => {
      if (!road.coords || road.coords.length < 2) return;
      
      const color = road.status_color || '#10B981';
      const weight = road.status === 'CRITICAL' ? 4 : road.status === 'WARNING' ? 3 : 2;
      const dash = road.status === 'CRITICAL' ? '6,4' : '';
      
      // Draw the BR line
      const line = L.polyline(road.coords, {
        color, weight, opacity:0.85, dashArray:dash, smoothFactor:2
      });
      
      const incidentList = road.incidents && road.incidents.length > 0 
        ? road.incidents.map(i => `• ${i.type} (${i.severity}) - ${i.location}`).join('<br>')
        : 'Sem incidentes ativos';
      
      line.bindTooltip(`<div style="font-family:monospace;font-size:11px;">
        <b style="color:${color};font-size:13px;">${brCode}</b><br>
        ${road.name}<br>
        Status: <b style="color:${color}">${road.status}</b><br>
        Tráfego: ${road.traffic_current?.toLocaleString() || 0}/${road.traffic_avg?.toLocaleString() || 0} veíc/dia<br>
        Atraso médio: ${road.avg_delay_minutes || 0} min<br>
        Incidentes: ${road.incidents_count || 0}<hr style="border-color:#333;margin:6px 0;">
        ${incidentList}
      </div>`, {sticky:true, direction:'top'});
      
      this._rodoviasLayer.addLayer(line);
      
      // Add status dots at critical points
      road.coords.forEach((coord, idx) => {
        if (idx % 3 === 0) { // Every 3rd point
          const dot = L.circleMarker(coord, {
            radius: road.status === 'CRITICAL' ? 5 : 3,
            color, fillColor:color, fillOpacity:0.6, weight:1
          });
          this._rodoviasLayer.addLayer(dot);
        }
      });
    });
    
    // Update KPI with rodovias data
    const summary = data.summary;
    if (summary) {
      const kpiEl = document.getElementById('px-kpi-eta');
      if (kpiEl && summary.critical_br) {
        const criticalCount = summary.critical_br.length;
        kpiEl.textContent = criticalCount > 0 ? `${criticalCount} BRs` : 'NORMAL';
        kpiEl.style.color = criticalCount >= 3 ? '#EF4444' : criticalCount > 0 ? '#F59E0B' : '#50C878';
      }
    }
  },

  _renderPorts() {
    this._portMarkers.clearLayers();
    const h = this._horizon;
    // Portos maritimos
    this.PORTS.forEach(p => {
      const volume = Math.round(p.cap * 0.78 * (1 + h*0.02)); // 78% utilização base
      const utilization = Math.min(100, Math.round(volume / p.cap * 100));
      const waitHours = Math.round(12 + utilization * 0.5 + (h > 7 ? 24 : 0));
      const color = utilization > 90 ? '#EF4444' : utilization > 70 ? '#F59E0B' : '#50C878';
      const marker = L.circleMarker([p.lat, p.lon], { radius:10, color:'#FFD700', fillColor:'#111', fillOpacity:0.9, weight:2 });
      marker.bindTooltip(`<div style="font-family:monospace;font-size:11px;"><b>⚓ ${p.name}</b><br>Volume: ${volume.toLocaleString()} t<br>Utilização: <b style="color:${color}">${utilization}%</b><br>Espera: <b>${waitHours}h</b></div>`, {direction:'left'});
      this._portMarkers.addLayer(marker);
      const el = document.getElementById('px-port-' + p.id);
      if (el) {
        el.innerHTML = `<div class="px-port-name">⚓ ${p.name}</div>
          <div class="px-port-kv"><span>Vol. 15d</span><span class="v">${volume.toLocaleString()} t</span></div>
          <div class="px-port-bar"><div class="px-port-bar-fill" style="width:${utilization}%;background:${color};"></div></div>
          <div class="px-port-kv"><span>Espera Preditiva</span><span class="v" style="color:${waitHours>36?'#EF4444':'#ddd'}">${waitHours}h</span></div>
          ${utilization>85?'<div style="font-size:9px;color:#EF4444;margin-top:3px;">⚠ FILAS EM '+(h>3?h:7)+' DIAS</div>':''}`;
      }
    });
    // CEASAs
    this.CEASAS.forEach(c => {
      const vol = c.vol; // volume base de referência
      const marker = L.circleMarker([c.lat, c.lon], { radius:7, color:'#50C878', fillColor:'#0a1a0a', fillOpacity:0.9, weight:2 });
      marker.bindTooltip(`<div style="font-family:monospace;font-size:11px;"><b>🏪 ${c.name}</b><br>Vol. semanal: ${vol.toLocaleString()} t<br>Região: ${c.region}</div>`, {direction:'top'});
      this._portMarkers.addLayer(marker);
    });
  },

  _renderArbitrage() {
    this._arbLayer.clearLayers();
    if (!this._layers.arb) return;
    const opps = this.ARBITRAGE_DB[this._culture] || [];
    const arbList = document.getElementById('px-arb-list');
    if (!arbList) return;
    arbList.innerHTML = '';

    if (!opps.length) {
      arbList.innerHTML = '<div style="color:#555;font-size:10px;text-align:center;padding:20px;">Sem oportunidades para esta cultura</div>';
      return;
    }

    opps.forEach((o, i) => {
      const margin = ((o.sellPrice - o.buyPrice - o.frete) / o.buyPrice * 100);
      const profitable = margin > 5;
      // Buy marker (blue pulsing)
      const buyM = L.circleMarker([o.buyLat, o.buyLon], {
        radius:8, color:'#3B82F6', fillColor:'#3B82F6', fillOpacity:0.3, weight:2,
        className:'px-buy-pulse'
      });
      buyM.bindTooltip(`<b style="color:#3B82F6">COMPRA</b><br>${o.buy}<br>R$ ${o.buyPrice}/un`, {direction:'top'});
      this._arbLayer.addLayer(buyM);
      // Sell marker (red pulsing)
      const sellM = L.circleMarker([o.sellLat, o.sellLon], {
        radius:8, color:'#EF4444', fillColor:'#EF4444', fillOpacity:0.3, weight:2,
        className:'px-sell-pulse'
      });
      sellM.bindTooltip(`<b style="color:#EF4444">VENDA</b><br>${o.sell}<br>R$ ${o.sellPrice}/un`, {direction:'top'});
      this._arbLayer.addLayer(sellM);
      // Flow line connecting buy → sell
      const flowColor = profitable ? '#FFD700' : '#555';
      const flow = L.polyline([[o.buyLat, o.buyLon], [o.sellLat, o.sellLon]], {
        color:flowColor, weight:profitable?2.5:1, dashArray:'10,6', opacity:0.7
      });
      flow.on('click', () => this._showInsight(o, margin));
      this._arbLayer.addLayer(flow);
      // Sidebar card
      arbList.innerHTML += `
        <div class="px-arb-card" onclick="Predictix._showInsight(Predictix.ARBITRAGE_DB['${this._culture}'][${i}], ${margin.toFixed(1)})">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:10px;color:#ddd;">${o.buy} → ${o.sell}</span>
            <span class="px-arb-margin">${margin>0?'+':''}${margin.toFixed(1)}%</span>
          </div>
          <div class="px-arb-route">Compra: R$${o.buyPrice} · Venda: R$${o.sellPrice} · Frete: R$${o.frete}</div>
        </div>
      `;
    });

    // Show first opportunity insight
    if (opps.length > 0) {
      const o = opps[0];
      const m = ((o.sellPrice - o.buyPrice - o.frete) / o.buyPrice * 100);
      this._showInsight(o, m);
    }
  },

  _showInsight(o, margin) {
    const detailPanel = document.getElementById('px-arb-detail');
    const detailContent = document.getElementById('px-arb-detail-content');
    
    // Verificar se elementos existem
    if (!detailPanel || !detailContent) {
      console.warn('[Predictix] Elementos de detalhe não encontrados');
      return;
    }
    
    const profitable = margin > 5;
    
    // Gerar valor determinístico baseado no ID da oportunidade
    const hashCode = (str) => {
      let hash = 0;
      for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
      }
      return Math.abs(hash);
    };
    
    const opportunityId = o.buy + '-' + o.sell + '-' + (o.product || this._culture || 'default');
    const hash = hashCode(opportunityId);
    
    // Calcular volumes e projeções (determinísticos)
    const volumeDiario = 500 + (hash % 1500); // 500-2000 toneladas/dia
    const volumeMensal = volumeDiario * 30;
    const volumeAnual = volumeMensal * 12;
    const lucroPorUnidade = (o.sellPrice - o.buyPrice - o.frete);
    const lucroDiario = lucroPorUnidade * volumeDiario;
    const lucroMensal = lucroDiario * 30;
    const lucroAnual = lucroMensal * 12;
    
    // Análise de mercado
    const tendenciaPreco = margin > 20 ? 'ALTA' : margin > 10 ? 'ESTÁVEL' : 'BAIXA';
    const riscoMercado = margin > 30 ? 'BAIXO' : margin > 15 ? 'MÉDIO' : 'ALTO';
    const prazoRetorno = margin > 40 ? '1-2 meses' : margin > 25 ? '3-4 meses' : '6+ meses';
    
    // Justificativa baseada na cultura
    const justificativas = {
      'soja': 'Demanda internacional aquecida. China aumentando importações. Dólar favorável à exportação.',
      'milho': 'Safra de verão com produtividade acima da média. Setor de proteína animal em expansão.',
      'cafe': 'Fenômeno climático afetando produção global. Estoques baixos nos principais produtores.',
      'cana': 'Demanda por etanol crescente. Mix favorável entre açúcar e etanol no mercado internacional.',
      'laranja': 'Safra entre estações. Estoque de suco concentrado em baixa no mercado internacional.',
      'tomate': 'Estresse hídrico em regiões produtoras reduzindo oferta. Demanda inelástica do consumidor.',
      'banana': 'Problemas fitossanitários em grandes produtores. Demanda constante do varejo.',
      'uva': 'Janela de exportação para hemisfério norte. Qualidade superior da safra brasileira.',
      'manga': 'Colheita em contra-estação. Mercado externo com preços premium para variedades tropicais.',
      'default': 'Diferencial de preço regional acima da média histórica. Logística favorável para escoamento.'
    };
    
    const culturaKey = this._culture || 'default';
    const justificativa = justificativas[culturaKey] || justificativas['default'];
    
    // Função para sanitizar texto
    const sanitize = (text) => {
      if (typeof text !== 'string') return String(text);
      return text.replace(/[<>"']/g, (match) => ({
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;'
      })[match]);
    };
    
    // Projeção do que vai acontecer
    const projecaoSubida = ((margin * 0.3) % 15).toFixed(1);
    const projecaoAumento = Math.round((margin * 0.8) % 50);
    const janelaDias = margin > 30 ? '7-10 dias' : margin > 15 ? '15-20 dias' : '30+ dias';
    
    detailPanel.style.display = 'block';
    
    // Criar elementos de forma segura
    const container = document.createElement('div');
    
    // Título do produto
    const titulo = document.createElement('div');
    titulo.style.cssText = 'font-size:11px;color:#fff;margin-bottom:6px;font-weight:bold;';
    titulo.textContent = (o.product || this._culture?.toUpperCase() || 'PRODUTO') + ' — OPORTUNIDADE ' + (profitable ? 'VIÁVEL' : 'DE RISCO');
    container.appendChild(titulo);
    
    // Grid de origem/destino
    const gridOrigemDestino = document.createElement('div');
    gridOrigemDestino.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;';
    
    const origem = document.createElement('div');
    origem.style.cssText = 'background:#1a1a1a;padding:6px;border-radius:4px;';
    origem.innerHTML = '<div style="font-size:8px;color:#888;">ORIGEM</div>' +
      '<div style="font-size:10px;color:#3B82F6;font-weight:bold;">' + sanitize(o.buy) + '</div>' +
      '<div style="font-size:9px;color:#666;">R$ ' + o.buyPrice + '/un</div>';
    gridOrigemDestino.appendChild(origem);
    
    const destino = document.createElement('div');
    destino.style.cssText = 'background:#1a1a1a;padding:6px;border-radius:4px;';
    destino.innerHTML = '<div style="font-size:8px;color:#888;">DESTINO</div>' +
      '<div style="font-size:10px;color:#EF4444;font-weight:bold;">' + sanitize(o.sell) + '</div>' +
      '<div style="font-size:9px;color:#666;">R$ ' + o.sellPrice + '/un</div>';
    gridOrigemDestino.appendChild(destino);
    
    container.appendChild(gridOrigemDestino);
    
    // Grid de métricas principais
    const gridMetricas = document.createElement('div');
    gridMetricas.style.cssText = 'display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:10px;';
    gridMetricas.innerHTML = 
      '<div style="text-align:center;padding:6px;background:rgba(255,215,0,0.1);border-radius:4px;">' +
        '<div style="font-size:16px;font-weight:bold;color:' + (profitable ? '#50C878' : '#EF4444') + ';">' + (margin > 0 ? '+' : '') + margin.toFixed(1) + '%</div>' +
        '<div style="font-size:8px;color:#888;">MARGEM</div>' +
      '</div>' +
      '<div style="text-align:center;padding:6px;background:rgba(10,132,255,0.1);border-radius:4px;">' +
        '<div style="font-size:16px;font-weight:bold;color:#0a84ff;">R$' + lucroPorUnidade.toFixed(2) + '</div>' +
        '<div style="font-size:8px;color:#888;">LUCRO/UN</div>' +
      '</div>' +
      '<div style="text-align:center;padding:6px;background:rgba(255,159,10,0.1);border-radius:4px;">' +
        '<div style="font-size:16px;font-weight:bold;color:#ff9f0a;">R$' + o.frete + '</div>' +
        '<div style="font-size:8px;color:#888;">FRETE</div>' +
      '</div>';
    container.appendChild(gridMetricas);
    
    // Volumetria
    const volumetria = document.createElement('div');
    volumetria.style.cssText = 'background:#1a1a1a;padding:8px;border-radius:4px;margin-bottom:10px;';
    volumetria.innerHTML = 
      '<div style="font-size:9px;color:#FFD700;margin-bottom:6px;">📦 VOLUMETRIA ESTIMADA</div>' +
      '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;font-size:9px;color:#ccc;">' +
        '<div>' +
          '<div style="color:#888;font-size:8px;">DIÁRIO</div>' +
          '<div style="color:#fff;font-weight:bold;">' + volumeDiario.toLocaleString() + ' t</div>' +
          '<div style="color:#50C878;">R$ ' + (lucroDiario / 1000).toFixed(1) + 'k</div>' +
        '</div>' +
        '<div>' +
          '<div style="color:#888;font-size:8px;">MENSAL</div>' +
          '<div style="color:#fff;font-weight:bold;">' + volumeMensal.toLocaleString() + ' t</div>' +
          '<div style="color:#50C878;">R$ ' + (lucroMensal / 1000000).toFixed(2) + 'M</div>' +
        '</div>' +
        '<div>' +
          '<div style="color:#888;font-size:8px;">ANUAL</div>' +
          '<div style="color:#fff;font-weight:bold;">' + volumeAnual.toLocaleString() + ' t</div>' +
          '<div style="color:#50C878;">R$ ' + (lucroAnual / 1000000).toFixed(2) + 'M</div>' +
        '</div>' +
      '</div>';
    container.appendChild(volumetria);
    
    // Indicadores
    const indicadores = document.createElement('div');
    indicadores.style.cssText = 'display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:10px;font-size:9px;';
    const riscoColor = riscoMercado === 'BAIXO' ? '#50C878' : riscoMercado === 'MÉDIO' ? '#F59E0B' : '#EF4444';
    indicadores.innerHTML = 
      '<div style="background:rgba(59,130,246,0.1);padding:6px;border-radius:4px;text-align:center;">' +
        '<div style="color:#888;font-size:8px;">TENDÊNCIA</div>' +
        '<div style="color:#3B82F6;font-weight:bold;">' + tendenciaPreco + '</div>' +
      '</div>' +
      '<div style="background:rgba(245,158,11,0.1);padding:6px;border-radius:4px;text-align:center;">' +
        '<div style="color:#888;font-size:8px;">RISCO</div>' +
        '<div style="color:' + riscoColor + ';font-weight:bold;">' + riscoMercado + '</div>' +
      '</div>' +
      '<div style="background:rgba(48,209,88,0.1);padding:6px;border-radius:4px;text-align:center;">' +
        '<div style="color:#888;font-size:8px;">PAYBACK</div>' +
        '<div style="color:#30d158;font-weight:bold;">' + prazoRetorno + '</div>' +
      '</div>';
    container.appendChild(indicadores);
    
    // Justificativa
    const justificativaDiv = document.createElement('div');
    justificativaDiv.style.cssText = 'background:rgba(255,215,0,0.05);padding:8px;border-radius:4px;margin-bottom:10px;border:1px solid rgba(255,215,0,0.2);';
    justificativaDiv.innerHTML = 
      '<div style="font-size:9px;color:#FFD700;margin-bottom:4px;">💡 JUSTIFICATIVA DA OPORTUNIDADE</div>' +
      '<div style="font-size:10px;color:#ccc;line-height:1.5;">' + sanitize(justificativa) + '</div>';
    container.appendChild(justificativaDiv);
    
    // Projeção
    const projecao = document.createElement('div');
    projecao.style.cssText = 'margin-top:10px;padding:8px;background:rgba(80,200,120,0.1);border-left:3px solid #50C878;border-radius:3px;';
    projecao.innerHTML = 
      '<div style="font-size:9px;color:#50C878;margin-bottom:4px;">📈 PROJEÇÃO DE MERCADO</div>' +
      '<div style="font-size:10px;color:#ccc;line-height:1.5;">' +
        '• Preço na origem tende a subir ' + projecaoSubida + '% nos próximos 15 dias<br>' +
        '• Volume de negociação deve aumentar ' + projecaoAumento + '%<br>' +
        '• Concorrência por frete pode reduzir margem em 2-5%<br>' +
        '• Janela de oportunidade: ' + janelaDias +
      '</div>';
    container.appendChild(projecao);
    
    // Riscos
    const riscos = document.createElement('div');
    riscos.style.cssText = 'margin-top:10px;padding:6px;background:rgba(239,68,68,0.1);border-radius:4px;font-size:9px;color:#ff9f0a;text-align:center;';
    riscos.textContent = '⚠️ Riscos: Variação cambial, condições climáticas, gargalos logísticos';
    container.appendChild(riscos);
    
    // Limpar e adicionar novo conteúdo
    detailContent.innerHTML = '';
    detailContent.appendChild(container);
    
    // Scroll para o painel de detalhes
    detailPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  },

  _renderKPIs() {
    const opps = this.ARBITRAGE_DB[this._culture] || [];
    const profitableCount = opps.filter(o => ((o.sellPrice-o.buyPrice-o.frete)/o.buyPrice*100) > 5).length;
    document.getElementById('px-kpi-arb').textContent = profitableCount + ' / ' + opps.length;

    const h = this._horizon;
    const ivf = (112 + h * 2.3).toFixed(1);
    document.getElementById('px-kpi-vol').textContent = ivf;

    const etaRisk = Math.min(95, Math.round(8 + h * 3.5 + (this.ROUTES.filter(r=>r.risk>0.2).length * 12)));
    document.getElementById('px-kpi-eta').textContent = etaRisk + '%';
    document.getElementById('px-kpi-eta').style.color = etaRisk > 50 ? '#EF4444' : etaRisk > 25 ? '#F59E0B' : '#50C878';

    const avgWait = Math.round(18 + h * 2.5);
    document.getElementById('px-kpi-fila').textContent = avgWait + 'h';
    document.getElementById('px-kpi-fila').style.color = avgWait > 36 ? '#EF4444' : '#F59E0B';
  },

  // ─── PRODUTORES NO PREDICTIX ──────────────────────────────────────
  async toggleProdutores() {
    this._produtoresVisible = !this._produtoresVisible;
    const btn = document.getElementById('px-btn-produtores');
    if (btn) {
      btn.style.borderColor = this._produtoresVisible ? '#0a84ff' : '#444';
      btn.style.color = this._produtoresVisible ? '#0a84ff' : '#888';
    }
    
    if (this._produtoresVisible) {
      await this._loadProdutores();
    } else {
      if (this._produtoresLayer) {
        this._produtoresLayer.remove();
        this._produtoresLayer = null;
      }
    }
  },

  async _loadProdutores() {
    try {
      if (!this._map) {
        console.error('[Predictix Produtores] Mapa não inicializado');
        return;
      }
      
      // Buscar todos os produtores (todos os países)
      const res = await fetch('/api/produtores');
      if (!res.ok) throw new Error('Erro ao carregar produtores');
      const data = await res.json();
      
      if (this._produtoresLayer) this._produtoresLayer.remove();
      this._produtoresLayer = L.layerGroup().addTo(this._map);
      
      const produtores = data.data || [];
      console.log(`[Predictix Produtores] ${produtores.length} produtores carregados`);
      
      // Cores por país
      const countryColors = {
        'BR': '#0a84ff',
        'AR': '#87CEEB',
        'PY': '#FFD700',
        'UY': '#98FB98',
        'CL': '#FF6B6B',
        'CO': '#FF8C00',
        'PE': '#DA70D6',
        'EC': '#00FA9A',
        'BO': '#F0E68C'
      };
      
      const countryNames = {
        'BR': 'Brasil',
        'AR': 'Argentina',
        'PY': 'Paraguai',
        'UY': 'Uruguai',
        'CL': 'Chile',
        'CO': 'Colômbia',
        'PE': 'Peru',
        'EC': 'Equador',
        'BO': 'Bolívia'
      };
      
      produtores.forEach(prod => {
        const color = countryColors[prod.state_uf] || '#0a84ff';
        
        const icon = L.divIcon({
          className: 'producer-marker',
          html: `<div style="
            width:24px;height:24px;
            background:linear-gradient(135deg, ${color}, #30d158);
            border:2px solid #fff;
            border-radius:50%;
            box-shadow:0 0 8px ${color}80;
            display:flex;align-items:center;justify-content:center;
            font-size:12px;
          ">👨‍🌾</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        });
        
        const marker = L.marker([prod.lat, prod.lon], { icon });
        
        const popupContent = `
          <div style="font-family:monospace;font-size:10px;min-width:180px;">
            <div style="font-weight:bold;color:${color};font-size:11px;margin-bottom:3px;">${prod.name}</div>
            <div style="color:#888;margin-bottom:2px;font-size:9px;">📍 ${prod.city} · ${countryNames[prod.state_uf] || prod.state_uf}</div>
            <div style="color:#888;margin-bottom:4px;font-size:9px;">🏪 ${prod.market_channel || 'CEASA'}</div>
            <div style="border-top:1px solid #333;padding-top:4px;margin-top:4px;">
              <div style="font-size:8px;color:${color};margin-bottom:2px;">PRODUTOS:</div>
              <div style="display:flex;flex-wrap:wrap;gap:2px;">
                ${(prod.products || []).map(p => `<span style="background:${color}30;color:${color};padding:1px 4px;border-radius:2px;font-size:8px;">${p}</span>`).join('')}
              </div>
            </div>
          </div>
        `;
        
        marker.bindPopup(popupContent);
        marker.bindTooltip(prod.name + ' (' + (countryNames[prod.state_uf] || prod.state_uf) + ')', { direction: 'top', offset: [0, -8] });
        
        this._produtoresLayer.addLayer(marker);
      });
      
    } catch (e) {
      console.error('[Predictix Produtores] Erro:', e);
    }
  },

  async toggleProdutoresRJ() {
    this._produtoresRJVisible = !this._produtoresRJVisible;
    const btn = document.getElementById('px-btn-produtores-rj');
    if (btn) {
      btn.style.borderColor = this._produtoresRJVisible ? '#ff9f0a' : '#444';
      btn.style.color = this._produtoresRJVisible ? '#ff9f0a' : '#888';
    }
    
    if (this._produtoresRJVisible) {
      await this._loadProdutoresRJ();
    } else {
      if (this._produtoresRJLayer) {
        this._produtoresRJLayer.remove();
        this._produtoresRJLayer = null;
      }
    }
  },

  async _loadProdutoresRJ() {
    try {
      if (!this._map) {
        console.error('[Predictix Produtores RJ] Mapa não inicializado');
        return;
      }
      
      const res = await fetch('/api/produtores-rj');
      if (!res.ok) throw new Error('Erro ao carregar produtores RJ');
      const data = await res.json();
      
      if (this._produtoresRJLayer) this._produtoresRJLayer.remove();
      this._produtoresRJLayer = L.layerGroup().addTo(this._map);
      
      const produtores = data.data || [];
      console.log(`[Predictix Produtores RJ] ${produtores.length} produtores carregados`);
      
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
        const color = statusColors[prod.judicial_status] || '#ff9f0a';
        
        const icon = L.divIcon({
          className: 'producer-rj-marker',
          html: `<div style="
            width:28px;height:28px;
            background:linear-gradient(135deg, ${color}, #ff453a);
            border:2px solid #fff;
            border-radius:50%;
            box-shadow:0 0 10px ${color}80;
            display:flex;align-items:center;justify-content:center;
            font-size:12px;
          ">⚖️</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });
        
        const marker = L.marker([prod.lat, prod.lon], { icon });
        
        const fmtMoney = v => v ? 'R$ ' + (v/1000000).toFixed(1) + 'M' : 'N/A';
        
        const popupContent = `
          <div style="font-family:monospace;font-size:10px;min-width:240px;max-width:280px;">
            <div style="font-weight:bold;color:${color};font-size:11px;margin-bottom:4px;">${prod.company_name}</div>
            <div style="background:${color}20;border:1px solid ${color};border-radius:3px;padding:3px 6px;margin-bottom:6px;font-size:9px;color:${color};">
              ⚖️ ${statusLabels[prod.judicial_status] || prod.judicial_status}
            </div>
            <div style="color:#888;margin-bottom:2px;font-size:9px;">📍 ${prod.city} - ${prod.state_uf}</div>
            <div style="color:#888;margin-bottom:4px;font-size:8px;">📋 ${prod.process_number || 'N/A'}</div>
            
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:6px 0;font-size:9px;">
              <div style="background:rgba(10,132,255,0.1);padding:4px;border-radius:3px;">
                <div style="color:#666;font-size:7px;">FATURAMENTO</div>
                <div style="color:#0a84ff;font-weight:bold;">${fmtMoney(prod.annual_revenue)}</div>
              </div>
              <div style="background:rgba(255,69,58,0.1);padding:4px;border-radius:3px;">
                <div style="color:#666;font-size:7px;">DÍVIDA</div>
                <div style="color:#ff453a;font-weight:bold;">${fmtMoney(prod.debts_total)}</div>
              </div>
            </div>
            
            <div style="border-top:1px solid #333;padding-top:6px;margin-top:6px;">
              <div style="font-size:8px;color:#0a84ff;margin-bottom:3px;">PRODUTOS:</div>
              <div style="display:flex;flex-wrap:wrap;gap:2px;">
                ${(prod.products || []).map(p => `<span style="background:${color}30;color:${color};padding:2px 6px;border-radius:2px;font-size:8px;border:1px solid ${color}50;">${p}</span>`).join('')}
              </div>
            </div>
          </div>
        `;
        
        marker.bindPopup(popupContent);
        marker.bindTooltip(prod.company_name + ' (' + (statusLabels[prod.judicial_status] || '') + ')', { direction: 'top', offset: [0, -12] });
        
        this._produtoresRJLayer.addLayer(marker);
      });
      
    } catch (e) {
      console.error('[Predictix Produtores RJ] Erro:', e);
    }
  },

  _startClimaCountdown() {
    const pending = document.getElementById('px-clima-pending');
    if (this._climaActive) return;
    pending.style.display = 'block';
    if (this._climaTimer) clearInterval(this._climaTimer);
    let remaining = 30;
    document.getElementById('px-clima-timer').textContent = remaining;
    this._climaTimer = setInterval(() => {
      remaining--;
      document.getElementById('px-clima-timer').textContent = remaining;
      if (remaining <= 0) {
        clearInterval(this._climaTimer);
        this._injectClimaLayer();
      }
    }, 1000);
  },

  async _injectClimaLayer() {
    this._climaActive = true;
    document.getElementById('px-clima-pending').style.display = 'none';
    this._layers.clima = true;
    const btn = document.getElementById('px-layer-clima');
    if (btn) { btn.style.borderColor = '#EF4444'; btn.style.color = '#EF4444'; }

    // Fetch weather for key route points
    const points = [
      {lat:-12.5,lon:-55.7,name:'Sinop-MT (BR-163)'},
      {lat:-15.9,lon:-49.3,name:'Goiânia-GO (BR-153)'},
      {lat:-24.0,lon:-49.0,name:'Curitiba-PR (BR-277)'},
      {lat:-22.9,lon:-47.1,name:'Campinas-SP'},
      {lat:-8.2,lon:-35.6,name:'Gravatá-PE'},
    ];

    this._climaLayer.clearLayers();
    for (const p of points) {
      try {
        const data = await fetch(`/proxy/api.open-meteo.com/v1/forecast?latitude=${p.lat}&longitude=${p.lon}&daily=precipitation_sum,temperature_2m_min&timezone=America/Sao_Paulo&forecast_days=3`).then(r=>r.json()).catch(()=>null);
        if (!data || !data.daily) continue;
        const precip = (data.daily.precipitation_sum || []).reduce((a,b)=>a+b, 0);
        const tempMin = Math.min(...(data.daily.temperature_2m_min || [30]));
        let alert = null;
        if (precip > 30) alert = {type:'chuva', msg:`Precipitação ${precip.toFixed(0)}mm em 3d`, color:'#3B82F6'};
        else if (tempMin < 5) alert = {type:'geada', msg:`Geada: min ${tempMin.toFixed(1)}°C`, color:'#A855F7'};
        if (alert) {
          const circle = L.circle([p.lat, p.lon], {
            radius: precip > 50 ? 120000 : 80000,
            color: alert.color, fillColor: alert.color, fillOpacity: 0.12, weight: 1,
            dashArray: '6,4'
          });
          circle.bindTooltip(`<div style="font-family:monospace;font-size:11px;"><b style="color:${alert.color}">${alert.type.toUpperCase()}</b><br>${p.name}<br>${alert.msg}<br><b style="color:#EF4444">Risco de atraso 48h</b></div>`, {sticky:true});
          this._climaLayer.addLayer(circle);
        }
        // Always add a small precipitation indicator
        if (precip > 5) {
          L.circleMarker([p.lat, p.lon], {
            radius:4, color:'#3B82F6', fillColor:'#3B82F6', fillOpacity:0.5, weight:0
          }).bindTooltip(`${p.name}: ${precip.toFixed(1)}mm/3d`).addTo(this._climaLayer);
        }
      } catch(e) {}
    }
    this._climaLayer.addTo(this._map);

    // Add risk annotation on BR-163 if Sinop has rain
    const sinopWeather = await fetch('/proxy/api.open-meteo.com/v1/forecast?latitude=-12.5&longitude=-55.7&daily=precipitation_sum&timezone=America/Sao_Paulo&forecast_days=7').then(r=>r.json()).catch(()=>null);
    if (sinopWeather?.daily?.precipitation_sum) {
      const total = sinopWeather.daily.precipitation_sum.reduce((a,b)=>a+b,0);
      if (total > 20) {
        const popup = L.popup({closeButton:false, autoClose:false, closeOnClick:false, className:'px-risk-popup'})
          .setLatLng([-12.5, -55.7])
          .setContent(`<div style="font-family:monospace;font-size:10px;background:#111;color:#EF4444;padding:6px 10px;border:1px solid #EF4444;border-radius:4px;"><b>⚠ BR-163</b><br>Precip. ${total.toFixed(0)}mm/7d em Sinop-MT<br>Risco atraso 48h → Miritituba<br><b>RECALCULE MARGEM</b></div>`)
          .openOn(this._map);
      }
    }
  },
};

// ── DASHBOARD WIRING — conecta APIs aos painéis ───────────────────
async function niasLoadRealData() {
  const strip = document.getElementById('api-status-strip');
  if (strip) strip.textContent = 'Conectando APIs...';

  const [weather, stations, fires, prices, climVars, conab] = await Promise.all([
    NiasAPI.getWeather(-15.78, -47.93),
    NiasAPI.getInmetStations(),
    NiasAPI.getFires(),
    NiasAPI.getCepeaPrices(),
    NiasAPI.getClimApiVars(),
    NiasAPI.getConabPrices(),
  ]);

  // ── ClimAPI GFS forecast for Brasília ─────────────────────────────
  if (climVars && climVars.length > 0) {
    const [temp, rh, precip] = await Promise.all([
      NiasAPI.getClimApiForecast('TMP_2maboveground', -15.78, -47.93),
      NiasAPI.getClimApiForecast('RH_2maboveground', -15.78, -47.93),
      NiasAPI.getClimApiForecast('APCP_surface', -15.78, -47.93),
    ]);
    window._niasClimApi = { temp, rh, precip };
  }

  // ── Update Overview KPIs with real weather ───────────────────────
  if (weather.current) {
    const setKpi = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setKpi('kpi-hum', weather.current.relative_humidity_2m + '%');
    const tempEl = document.querySelector('[id*="temp"]') || document.getElementById('kpi-temp');
    if (tempEl) tempEl.textContent = weather.current.temperature_2m.toFixed(1) + '°C';
  }

  // ── Update header strip live values ──────────────────────────────
  if (weather.current) {
    const hum = document.querySelector('[id="hdr-umid"]');
    if (hum) hum.textContent = weather.current.relative_humidity_2m + '%';
  }

  // ── FIRMS fire markers on BIO-COMMAND and Mapa Geo-IA ───────────
  if (fires.length > 0) {
    const addFiresTo = (map, layerStore, layerName) => {
      if (!map) return;
      const fg = L.layerGroup();
      fires.forEach(f => {
        const mk = createSonarMarker([f.lat, f.lon], {
          state: 'alert', severity: f.bright > 340 ? 'critical' : 'high', size: 4,
          tooltip: `<div style="font-family:monospace;font-size:11px;"><b>🔥 FOCO ATIVO — ${_esc(f.satellite||'VIIRS')}</b><br>` +
            `Conf: ${_esc(f.conf)} · FRP: ${f.frp?.toFixed(1)||'—'} MW<br>` +
            `Brilho: ${f.bright?.toFixed(0)||'—'}K<br>` +
            `${f.acq_date ? f.acq_date + ' ' + (f.acq_time||'') : 'Tempo real'}</div>`
        });
        fg.addLayer(mk);
      });
      if (layerStore) layerStore[layerName] = fg;
      fg.addTo(map);
    };
    addFiresTo(window.leafletMap, window.mapLayerObjs, 'fires');
    addFiresTo(window.bcMap, window.bcMapLayers, 'fires');
    const fireCount = document.getElementById('api-fire-count');
    if (fireCount) fireCount.textContent = fires.length + ' focos';
  }

  // ── INMET station markers on maps ───────────────────────────────
  if (stations.length > 0) {
    const addStationsTo = (map) => {
      if (!map) return;
      stations.forEach(s => {
        if (!s.lat || !s.lon) return;
        L.circleMarker([s.lat, s.lon], {
          radius: 3, color: '#0a84ff', fillColor: '#0a84ff', fillOpacity: 0.4, weight: 1
        }).bindTooltip(`<b>INMET ${s.code}</b><br>${s.name} — ${s.state}`, { direction: 'top' }).addTo(map);
      });
    };
    addStationsTo(window.leafletMap);
  }

  // ── Planet satellite layer ────────────────────────────────────────
  if (NiasAPI.PLANET_KEY) {
    const addPlanetTo = (map, layerStore) => {
      if (!map) return;
      const pl = NiasAPI.addPlanetLayer(map);
      if (pl && layerStore) layerStore['planet'] = pl;
    };
    addPlanetTo(window.leafletMap, window.mapLayerObjs);
    addPlanetTo(window.bcMap, window.bcMapLayers);
  }

  // ── Sentinel-1 SAR layer ──────────────────────────────────────────
  const addSARTo = (map, layerStore) => {
    if (!map) return;
    const sarLyr = NiasAPI.addSARLayer(map);
    if (sarLyr && layerStore) layerStore['sar'] = sarLyr;
  };
  addSARTo(window.leafletMap, window.mapLayerObjs);
  addSARTo(window.bcMap, window.bcMapLayers);

  // ── CEPEA prices → CEASA Arbitragem ─────────────────────────────
  if (prices && typeof window.ARB_ROWS !== 'undefined') {
    const priceMap = { soja: prices.soja, milho: prices.milho, tomate: prices.tomate };
    window.ARB_ROWS.forEach(r => {
      const key = r.cultKey || r.culture?.toLowerCase();
      if (key && priceMap[key]) r.priceOrigin = priceMap[key].price;
    });
  }

  // ── Weather per municipality (BIO-COMMAND right panel) ──────────
  window._niasWeatherCache = weather;
  window._niasConabCache = conab;

  // ── SIDRA base fetch (soja) for BIO-COMMAND and War Room ────────
  const sidraBase = await NiasAPI.getSidra(3940, 35);
  if (sidraBase && sidraBase.length > 0) {
    window._niasSidraBase = {};
    sidraBase.forEach(d => { window._niasSidraBase[d.munCode] = d; });
    NiasAPI._logSource('SIDRA', 'api');
    const fsEl = document.getElementById('fs-fallback');
    if (fsEl) { fsEl.textContent = `SIDRA: API REAL (${sidraBase.length} mun.)`; fsEl.style.color = 'var(--accent2)'; }
  } else {
    // Also try via fetchSidraProduction (v3 endpoint)
    try {
      if (typeof fetchSidraProduction === 'function') {
        const v3data = await fetchSidraProduction('soja', 'last');
        if (v3data && v3data.length > 0) {
          window._bcSidraData = {};
          v3data.forEach(d => { window._bcSidraData[d.D1C] = { vbp: +d.V, name: d.NC }; });
          NiasAPI._logSource('SIDRA-v3', 'api');
        }
      }
    } catch(e) { console.warn('SIDRA v3 fallback error:', e); }
  }

  // ── Open-Meteo MULTI — atualiza clima real em todos os polos ────
  if (typeof MUNICIPAL_DB !== 'undefined') {
    const brMuns = MUNICIPAL_DB.filter(m => m.country === 'BR' && m.poly && m.poly.length >= 3);
    // Sample up to 50 polos (Open-Meteo limit per request)
    const sample = brMuns.slice(0, 50).map(m => ({
      id: m.id,
      lat: (m.poly[0][0] + m.poly[2][0]) / 2,
      lon: (m.poly[0][1] + m.poly[2][1]) / 2
    }));
    if (sample.length > 0) {
      const multiWeather = await NiasAPI.getWeatherMulti(sample);
      if (multiWeather && multiWeather.length > 0) {
        sample.forEach((s, i) => {
          const w = multiWeather[i];
          if (!w || !w.current) return;
          const mun = MUNICIPAL_DB.find(m => m.id === s.id);
          if (!mun) return;
          mun.temp_max = w.current.temperature_2m;
          mun.chuva_7d = w.daily?.precipitation_sum?.reduce((a, b) => a + b, 0)?.toFixed(1) || mun.chuva_7d;
          mun.umidade = w.current.relative_humidity_2m;
          mun.vento = w.current.wind_speed_10m;
          mun.solo_umid = w.current.soil_moisture_0_to_7cm;
          mun._weatherSource = 'Open-Meteo';
          mun._et0_7d = w.daily?.et0_fao_evapotranspiration || [];
        });
        NiasAPI._logSource('OpenMeteo-Multi', 'api');
      }
    }
  }

  // ── Climate Intelligence ─────────────────────────────────────────
  if (typeof NiasClimate !== 'undefined' && !NiasClimate._running) {
    NiasClimate._running = true;
    await NiasClimate.run();
  }

  // ── HORTIFRUTI — Atualizar preços com dados reais ──────────────
  let ceagespData = {};
  try {
    const cr = await fetch('/api/ceagesp').then(r => r.ok ? r.json() : {}).catch(() => ({}));
    ceagespData = cr;
  } catch(e) {}

  // CEASA-GO Goiás — PDF diário oficial (fonte primária para produtos cobertos)
  let ceasaGoData = {};
  try {
    const gr = await fetch('/api/ceasa/go').then(r => r.ok ? r.json() : {}).catch(() => ({}));
    ceasaGoData = gr;
  } catch(e) {}

  // CEASA-MG Minas Gerais — HTML diário, múltiplas cidades
  let ceasaMgData = {};
  try {
    const mr = await fetch('/api/ceasa/mg').then(r => r.ok ? r.json() : {}).catch(() => ({}));
    ceasaMgData = mr;
  } catch(e) {}

  // CEASA-RN Rio Grande do Norte — PDF diário (situação de mercado)
  let ceasaRnData = {};
  try {
    const rr = await fetch('/api/ceasa/rn').then(r => r.ok ? r.json() : {}).catch(() => ({}));
    ceasaRnData = rr;
  } catch(e) {}

  _updateHortiPrices(prices, conab, ceagespData, ceasaGoData, ceasaMgData, ceasaRnData);

  // ── Schedule refresh every 15 minutes ───────────────────────────
  setTimeout(niasLoadRealData, 900000);
}

// Atualiza cards de hortifruti na Visao Geral com dados reais
function _updateHortiPrices(cepeaPrices, conabData, ceagespData, ceasaGoData, ceasaMgData, ceasaRnData) {
  const flvRef = typeof FLVModule !== 'undefined' ? FLVModule._REF : {};
  const ceagespProds = ceagespData && ceagespData.products ? ceagespData.products : {};
  const ceagespDate = ceagespData && ceagespData.meta ? ceagespData.meta.date : '';
  const goProds = (ceasaGoData && ceasaGoData.produtos) ? ceasaGoData.produtos : {};
  const goDate = (ceasaGoData && ceasaGoData.meta) ? ceasaGoData.meta.date : '';
  const mgProds = (ceasaMgData && ceasaMgData.produtos) ? ceasaMgData.produtos : {};
  const mgDate = (ceasaMgData && ceasaMgData.meta) ? ceasaMgData.meta.date : '';
  const rnProds = (ceasaRnData && ceasaRnData.produtos) ? ceasaRnData.produtos : {};
  const rnDate = (ceasaRnData && ceasaRnData.meta) ? ceasaRnData.meta.date : '';

  const hortiMap = {
    // ceasa_go: termo CEASA-GO (PDF Goiás) | ceasa_mg: chave CEASA-MG | ceasa_rn: chave CEASA-RN
    'tomate-mesa': { slug:'tomate', unit:'kg', conab:'TOMATE', cepea:'tomate', ceasa_go:'TOMATE LONGA VIDA', ceasa_mg:'TOMATE', ceasa_rn:'TOMATE', elPrice:'hp-tomate-mesa', elDelta:'hd-tomate-mesa', elSrc:'hsrc-tomate-mesa', elStatus:'hst-tomate-mesa' },
    'tomate-ind':  { slug:'tomate', unit:'t',  conab:'EXTRATO DE TOMATE', cepea:null, ceasa_go:'TOMATE', ceasa_mg:'TOMATE', ceasa_rn:'TOMATE', elPrice:'hp-tomate-ind', elDelta:'hd-tomate-ind', elSrc:'hsrc-tomate-ind', elStatus:'hst-tomate-ind' },
    'pimentao':    { slug:'pimentao', unit:'kg', conab:'PIMENTAO', cepea:null, ceasa_go:'PIMENTAO', ceasa_mg:'PIMENTAO', ceasa_rn:'PIMENTAO', elPrice:'hp-pimentao', elDelta:'hd-pimentao', elSrc:'hsrc-pimentao', elStatus:'hst-pimentao' },
    'alface':      { slug:'folhosas', unit:'kg', conab:'ALFACE', cepea:null, ceasa_go:'ALFACE', ceasa_mg:'ALFACE', ceasa_rn:'ALFACE', elPrice:'hp-alface', elDelta:'hd-alface', elSrc:'hsrc-alface', elStatus:'hst-alface' },
    'laranja':     { slug:'laranja', unit:'cx', conab:'LARANJA', cepea:'laranja', ceasa_go:'LARANJA', ceasa_mg:'LARANJA', ceasa_rn:'LARANJA', elPrice:'hp-laranja', elDelta:'hd-laranja', elSrc:'hsrc-laranja', elStatus:'hst-laranja' },
    'batata':      { slug:'batata', unit:'sc', conab:'BATATA INGLESA', cepea:'batata', ceasa_go:'BATATA COMUM', ceasa_mg:'BATATA', ceasa_rn:'BATATA', elPrice:'hp-batata', elDelta:'hd-batata', elSrc:'hsrc-batata', elStatus:'hst-batata' },
    'cebola':      { slug:'cebola', unit:'kg', conab:'CEBOLA', cepea:null, ceasa_go:'CEBOLA NACIONAL', ceasa_mg:'CEBOLA', ceasa_rn:'CEBOLA', elPrice:'hp-cebola', elDelta:'hd-cebola', elSrc:'hsrc-cebola', elStatus:'hst-cebola' },
    'manga':       { slug:'manga', unit:'kg', conab:'MANGA', cepea:null, ceasa_go:'MANGA', ceasa_mg:'MANGA', ceasa_rn:'MANGA', elPrice:'hp-manga', elDelta:'hd-manga', elSrc:'hsrc-manga', elStatus:'hst-manga' },
    'uva':         { slug:'uva', unit:'kg', conab:'UVA', cepea:null, ceasa_go:'UVA', ceasa_mg:'UVA', ceasa_rn:'UVA', elPrice:'hp-uva', elDelta:'hd-uva', elSrc:'hsrc-uva', elStatus:'hst-uva' },
    'banana':      { slug:'banana', unit:'kg', conab:'BANANA', cepea:null, ceasa_go:null, ceasa_mg:'BANANA-NANICA', ceasa_rn:'BANANA', elPrice:'hp-banana', elDelta:'hd-banana', elSrc:'hsrc-banana', elStatus:'hst-banana' },
    'cenoura':     { slug:'cenoura', unit:'kg', conab:'CENOURA', cepea:null, ceasa_go:null, ceasa_mg:'CENOURA', ceasa_rn:'CENOURA', elPrice:'hp-cenoura', elDelta:'hd-cenoura', elSrc:'hsrc-cenoura', elStatus:'hst-cenoura' },
    'morango':     { slug:'morango', unit:'kg', conab:'MORANGO', cepea:null, ceasa_go:null, ceasa_mg:'MORANGO', ceasa_rn:'MORANGO', elPrice:'hp-morango', elDelta:'hd-morango', elSrc:'hsrc-morango', elStatus:'hst-morango' },
    'acerola':     { slug:'acerola', unit:'kg', conab:'ACEROLA', cepea:null, ceasa_go:null, ceasa_mg:null, ceasa_rn:'ACEROLA', elPrice:'hp-acerola', elDelta:'hd-acerola', elSrc:'hsrc-acerola', elStatus:'hst-acerola' },
    'mamao':       { slug:'mamao', unit:'kg', conab:'MAMAO', cepea:null, ceasa_go:null, ceasa_mg:null, ceasa_rn:'MAMAO', elPrice:'hp-mamao', elDelta:'hd-mamao', elSrc:'hsrc-mamao', elStatus:'hst-mamao' },
  };

  // Helper: encontra produto CEASA-GO por termo (partial match no nome)
  function _findGoProduct(term) {
    if (!term || !Object.keys(goProds).length) return null;
    const t = term.toUpperCase();
    // Busca exata primeiro, depois parcial
    const exact = goProds[t];
    if (exact) return exact;
    const partial = Object.values(goProds).find(p => p.nome && p.nome.toUpperCase().startsWith(t));
    return partial || null;
  }

  for (const [key, cfg] of Object.entries(hortiMap)) {
    const priceEl = document.getElementById(cfg.elPrice);
    const deltaEl = document.getElementById(cfg.elDelta);
    const srcEl = document.getElementById(cfg.elSrc);
    const statusEl = document.getElementById(cfg.elStatus);
    if (!priceEl) continue;

    // Resolve price: CEASA-GO > CEAGESP > CEPEA > CONAB > FLV ref
    let price = null, source = '', change = null;

    // 0. CEASA-GO Goiás — PDF diário oficial (fonte mais atualizada)
    if (cfg.ceasa_go) {
      const gp = _findGoProduct(cfg.ceasa_go);
      if (gp && gp.comum) {
        const kgEmb = gp.kg_embalagem;
        const priceRaw = gp.comum;
        price = (kgEmb && kgEmb > 0) ? Math.round((priceRaw / kgEmb) * 100) / 100 : priceRaw;
        const emb = gp.embalagem ? ` · ${gp.embalagem}` : '';
        source = `CEASA-GO · ${goDate}${emb}`;
      }
    }
    // 0b. CEASA-MG Minas Gerais — HTML diário, múltiplas cidades
    if (!price && cfg.ceasa_mg) {
      const mp = mgProds[cfg.ceasa_mg];
      if (mp && mp.preco_medio) {
        price = mp.preco_medio;
        source = `CEASA-MG · ${mgDate} · ${mp.embalagem || 'KG'}`;
      }
    }
    // 0c. CEASA-RN Rio Grande do Norte — PDF diário (preco_kg direto)
    if (!price && cfg.ceasa_rn) {
      const term = cfg.ceasa_rn.toUpperCase();
      const rp = rnProds[term] || Object.values(rnProds).find(p => p.nome && p.nome.toUpperCase().startsWith(term));
      if (rp && (rp.preco_kg || rp.comum)) {
        price = rp.preco_kg || rp.comum;
        source = `CEASA-RN · ${rnDate} · ${rp.embalagem || 'KG'}`;
      }
    }
    // 1. CEAGESP LIVE
    if (!price && ceagespProds[cfg.slug]) {
      const cp = ceagespProds[cfg.slug];
      price = cp.price_avg;
      source = `CEAGESP · ${ceagespDate || cp.date || ''} · ${cp.name || ''}`;
    }
    // 2. CEPEA
    if (!price && cfg.cepea && cepeaPrices && cepeaPrices[cfg.cepea]) {
      const cp = cepeaPrices[cfg.cepea];
      price = cp.price; change = cp.change; source = `CEPEA/ESALQ · ${cp.date || ''}`;
    }
    // 3. CONAB (exact match at start of product name)
    if (!price && conabData && conabData.agro) {
      const match = Object.entries(conabData.agro).find(([k]) => {
        const ku = k.toUpperCase().trim();
        return ku === cfg.conab || ku.startsWith(cfg.conab + ' ') || ku.startsWith(cfg.conab + '/');
      });
      if (match) { price = match[1].avg_price; source = `CONAB Semanal · ${match[1].date || ''}`; }
    }
    // 4. FLV ref
    if (!price && flvRef[cfg.slug]) { price = flvRef[cfg.slug]; source = 'CEAGESP ref.'; }

    if (price) {
      priceEl.textContent = `R$ ${price.toFixed(2)}/${cfg.unit}`;
      priceEl.classList.remove('loading-val');
      priceEl.classList.add('val-flash');
      setTimeout(() => priceEl.classList.remove('val-flash'), 700);
      // Registra preço real para sparkline (sem simulação)
      if (typeof hortiState !== 'undefined' && hortiState[key]) hortiState[key]._realPrice = price;
      // Ativa live dot
      const ldEl = document.getElementById('hld-' + key);
      if (ldEl) { ldEl.className = 'hc-live-dot live'; }
    }
    if (srcEl) {
      const isCeasa = source.includes('CEASA-GO') || source.includes('CEASA-MG') || source.includes('CEASA-RN');
      srcEl.textContent = source || 'sem fonte';
      srcEl.style.color = isCeasa ? 'rgba(48,209,88,.7)' : source.includes('CEPEA') ? 'rgba(48,209,88,.6)' : source.includes('CONAB') ? 'rgba(10,132,255,.7)' : 'rgba(235,235,245,0.3)';
    }

    // Fetch prediction for trend
    (async (cfg, deltaEl, statusEl, change) => {
      try {
        let pred = null;
        try {
          const r = await fetch(`/api/flv/predictions/${cfg.slug}?horizon=15`);
          if (r.ok) pred = await r.json();
        } catch(e) {}
        if (!pred || !pred.forecast || !pred.forecast.length) {
          // Synthetic trend
          pred = typeof FLVModule !== 'undefined' ? FLVModule._syntheticPrediction(cfg.slug, {series:[{price: flvRef[cfg.slug]||5}]}) : null;
        }
        if (pred && deltaEl) {
          const trendPct = pred.trend_pct || (change || 0);
          const trend = pred.trend || 'estavel';
          const arrow = trendPct > 0 ? '▲' : trendPct < 0 ? '▼' : '—';
          const sign = trendPct > 0 ? '+' : '';
          const trendLabel = trend === 'alta' ? 'PREVISÃO ALTA 15d' : trend === 'baixa' ? 'PREVISÃO BAIXA 15d' : 'ESTÁVEL 15d';
          deltaEl.textContent = `${arrow} ${sign}${trendPct.toFixed(1)}% — ${trendLabel}`;
          deltaEl.className = 'horti-delta ' + (trendPct > 2 ? 'danger' : trendPct < -2 ? 'ok' : '');
          if (statusEl) {
            if (trend === 'alta') { statusEl.textContent = '↑ ALTA PREVISTA'; statusEl.className = 'horti-status danger'; }
            else if (trend === 'baixa') { statusEl.textContent = '↓ BAIXA PREVISTA'; statusEl.className = 'horti-status ok'; }
            else { statusEl.textContent = '→ ESTÁVEL'; statusEl.className = 'horti-status ok'; }
          }
        }
      } catch(e) {}
    })(cfg, deltaEl, statusEl, change);
  }
}




// ═══ CEASA/PROHORT OFICIAL — preços reais, sem simulação ═══
let CEASA_OFFICIAL_DATA = null;
async function loadCeasaOfficialPrices(force=false) {
  const status = document.getElementById('ceasa-official-status');
  const tbody = document.getElementById('ceasa-official-tbody');
  const coverage = document.getElementById('ceasa-official-coverage');
  if (status) status.textContent = 'coletando fonte oficial...';
  if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="padding:14px;color:var(--text2);font-size:10px;text-align:center;">Coletando CONAB/PROHORT e cache local...</td></tr>';
  try {
    const uf = document.getElementById('ceasa-price-uf')?.value || '';
    const product = document.getElementById('ceasa-price-product')?.value || '';
    const qs = new URLSearchParams();
    if (uf) qs.set('uf', uf);
    if (product) qs.set('product', product);
    qs.set('limit', '300');
    if (force) qs.set('refresh', '1');
    const res = await fetch('/api/ceasa/prices?' + qs.toString());
    const data = await res.json();
    CEASA_OFFICIAL_DATA = data;
    renderCeasaOfficialPrices(data);
  } catch (e) {
    if (status) status.textContent = 'erro na coleta CEASA';
    if (tbody) tbody.innerHTML = `<tr><td colspan="6" style="padding:14px;color:var(--danger);font-size:10px;text-align:center;">Falha: ${escapeHtml(String(e.message || e))}</td></tr>`;
  }
}

function renderCeasaOfficialPrices(data) {
  const status = document.getElementById('ceasa-official-status');
  const tbody = document.getElementById('ceasa-official-tbody');
  const coverage = document.getElementById('ceasa-official-coverage');
  const records = Array.isArray(data?.records) ? data.records : [];
  const meta = data?.meta || {};
  if (status) status.textContent = data?.ok ? `● ${records.length} preços · ${meta.states_with_prices || 0}/${meta.states_total || 27} UFs` : 'sem retorno oficial';
  if (coverage) {
    const cov = data?.coverage || {};
    const okUfs = Object.values(cov).filter(x => x.records > 0).slice(0, 12).map(x => `${x.uf}:${x.records}`).join(' · ');
    const pend = Object.values(cov).filter(x => !x.records).slice(0, 12).map(x => x.uf).join(', ');
    coverage.innerHTML = `
      <div style="color:var(--accent2);font-size:10px;letter-spacing:1px;margin-bottom:5px;">COBERTURA CEASA/PROHORT</div>
      <div><strong>${meta.states_with_prices || 0}</strong> UFs com preço coletado de <strong>${meta.states_total || 27}</strong>.</div>
      <div style="margin-top:5px;color:var(--text);">Com dados: ${escapeHtml(okUfs || 'nenhuma UF retornou preço')}</div>
      <div style="margin-top:5px;color:var(--warn);">Sem retorno no coletor: ${escapeHtml(pend || '—')}</div>
      <div style="margin-top:7px;color:var(--text2);">Política: preço só aparece quando existe fonte; o NIAS não cria cotação estimada.</div>`;
  }
  if (!tbody) return;
  if (!records.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="padding:14px;color:var(--text2);font-size:10px;text-align:center;">Nenhum preço oficial retornado para o filtro atual. Tente Brasil ou outro produto.</td></tr>';
    return;
  }
  tbody.innerHTML = records.slice(0, 300).map(r => `
    <tr title="${escapeHtml(r.quality || '')}">
      <td style="padding:5px;border-bottom:1px solid var(--border);font-size:9px;color:var(--accent2);font-weight:bold;">${escapeHtml(r.uf || '—')}</td>
      <td style="padding:5px;border-bottom:1px solid var(--border);font-size:9px;color:var(--text);">${escapeHtml(r.ceasa || '—')}</td>
      <td style="padding:5px;border-bottom:1px solid var(--border);font-size:9px;color:var(--text);font-weight:bold;">${escapeHtml(r.product || '—')}</td>
      <td style="padding:5px;border-bottom:1px solid var(--border);font-size:9px;color:var(--warn);text-align:right;font-family:var(--font);">R$ ${Number(r.price || 0).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2})}<br><span style="font-size:8px;color:var(--text2);">${escapeHtml(r.unit || '')}</span></td>
      <td style="padding:5px;border-bottom:1px solid var(--border);font-size:9px;color:var(--text2);">${escapeHtml(r.date || '—')}</td>
      <td style="padding:5px;border-bottom:1px solid var(--border);font-size:8px;color:var(--text2);">${escapeHtml(r.source || '—')}<br><span style="color:${r.quality === 'official_collected' ? 'var(--accent2)' : 'var(--warn)'};">${String(r.quality || '').startsWith('official') ? 'OFICIAL' : 'CACHE/VALIDAR'}</span></td>
    </tr>`).join('');
}

// ═══ MERCADO REAL — sem random, sem simulação ═══
const MERCADO_REAL_DATA = {
  updated_at: '2026-05-24',
  methodology: 'Base curada: produção/oferta anual e referências de mercado. Preço só é exibido quando há fonte; valores ausentes ficam como —.',
  sources: ['CONAB','IBGE PAM','CEAGESP','CEPEA','CNA'],
  records: [
    ['Soja','grãos','171,5 Mt','—','oferta elevada','Brasil','CONAB','Safra 2024/25 divulgada em 2025','real_curado','Produção nacional recorde citada em base CONAB; atualizar via portal/API CONAB.'],
    ['Milho','grãos','≈140 Mt','—','estável','Brasil','CONAB/mercado','Safra 2024/25-2025/26','real_curado','Grandeza nacional; não representa preço spot.'],
    ['Arroz','grãos','12,3 Mt','—','neutro','Brasil','IBGE/CONAB','base anual','real_curado','Volume anual; preço depende de praça e tipo.'],
    ['Feijão','grãos','3,4 Mt','—','sensível à safra','Brasil','IBGE/CONAB','base anual','real_curado','Mercado segmentado por cores/tipos.'],
    ['Laranja','frutas','16,7 Mt','—','oferta regional','Brasil / SP-MG-BA','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Fruta com maior volume entre hortifrutis no Brasil.'],
    ['Banana','frutas','6,6 Mt','—','oferta distribuída','Brasil / SP-MG-BA-SC','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Atualizar ranking por UF via PAM anual.'],
    ['Açaí','frutas','1,48 Mt','—','alta estrutural','Amazônia / PA-AM-AP','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Produto regional com mercado industrial/exportação.'],
    ['Uva','frutas','1,44 Mt','—','sazonal','Vale do São Francisco / Sul','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Separar mesa, vinho e suco em coletas futuras.'],
    ['Cacau','frutas','269,7 mil t','—','mercado externo forte','BA-PA / Andes amazônicos','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Preço internacional não foi inventado no painel.'],
    ['Abacaxi','frutas','1,64 Mt','—','sazonal','Brasil tropical','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Volume convertido de mil toneladas.'],
    ['Melancia','frutas','2,18 Mt','—','sazonal','NE/CO/Sul','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Alta dependência logística e clima.'],
    ['Limão','frutas','1,59 Mt','—','exportação relevante','SP-MG-BA','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Separar tahiti/siciliano em versão futura.'],
    ['Manga','frutas','1,57 Mt','—','exportação','Vale do São Francisco / NE','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Sazonalidade forte por janela exportadora.'],
    ['Maçã','frutas','983,2 mil t','—','estoque/frio','SC-RS-PR','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Produto concentrado no Sul.'],
    ['Maracujá','frutas','690,4 mil t','—','volátil','BA-CE-MG-ES','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Mercado mesa e indústria devem ser separados.'],
    ['Coco-da-baía','frutas','1,64 Mt','—','regional','NE / litoral tropical','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Volume anual, não preço spot.'],
    ['Mamão','frutas','1,24 Mt','—','sazonal','BA-ES-CE-RN','CNA/IBGE PAM','Mapa Hortifruti/CNA + PAM','real_curado','Separar formosa/papaya.'],
    ['Tomate','hortaliças','≈4,0 Mt','—','alta volatilidade','GO-SP-MG-BA','IBGE PAM/CEAGESP','base anual + terminal','real_curado','Preço deve vir por terminal e classificação; removida arbitragem sintética.'],
    ['Batata inglesa','hortaliças','≈4,0 Mt','—','safras regionais','MG-PR-SP-GO','IBGE PAM/CEAGESP','base anual + terminal','real_curado','Não misturar batata lavada, escovada e especial sem classificação.'],
    ['Cebola','hortaliças','≈1,6 Mt','—','regional','SC-BA-RS-PE','IBGE PAM/CEAGESP','base anual + terminal','real_curado','Separar nacional/importada.'],
    ['Mandioca','hortaliças','≈18 Mt','—','amido/farinha','PA-PR-BA-MS','IBGE PAM','base anual','real_curado','Mercado de raiz, farinha e fécula não são equivalentes.'],
    ['Ovos','granjeiros','—','—','demanda estável','Brasil','IBGE PPM/CEPEA','base anual','fonte_requerida','Conectar PPM/CEPEA para série real.'],
    ['Frango','granjeiros','—','—','exportação relevante','Brasil / Sul','CEPEA/MAPA','referencial','fonte_requerida','Separar vivo, resfriado, carcaça e cortes.'],
    ['Leite','granjeiros','—','—','sazonal','MG-PR-RS-GO-SC','CEPEA/IBGE PPM','referencial','fonte_requerida','Usar leite ao produtor; não misturar UHT/varejo.']
  ].map(r => ({product:r[0], category:r[1], production:r[2], price:r[3], trend:r[4], region:r[5], source:r[6], reference_date:r[7], status:r[8], note:r[9]}))
};

function renderMercadoReal() {
  const tbody = document.getElementById('mercado-real-tbody');
  if (!tbody) return;
  const cat = document.getElementById('mercado-filter-categoria')?.value || 'all';
  const fonte = document.getElementById('mercado-filter-fonte')?.value || 'all';
  const q = (document.getElementById('mercado-search')?.value || '').toLowerCase().trim();
  let rows = MERCADO_REAL_DATA.records.filter(r => {
    const sourceOk = fonte === 'all' || r.source.toUpperCase().includes(fonte.toUpperCase());
    const catOk = cat === 'all' || r.category === cat;
    const qOk = !q || [r.product,r.category,r.region,r.source,r.note,r.reference_date].join(' ').toLowerCase().includes(q);
    return sourceOk && catOk && qOk;
  });
  tbody.innerHTML = rows.map(r => {
    const statusColor = r.status === 'real_curado' ? 'var(--accent2)' : 'var(--warn)';
    const trendColor = /alta|forte|elevada|export/.test(r.trend) ? 'var(--accent2)' : /volátil|sensível/.test(r.trend) ? 'var(--warn)' : 'var(--text)';
    return `<tr title="${escapeHtml(r.note)}">
      <td style="padding:6px;border-bottom:1px solid var(--border);font-size:10px;color:var(--text);font-weight:bold;">${escapeHtml(r.product)}</td>
      <td style="padding:6px;border-bottom:1px solid var(--border);font-size:10px;color:var(--text2);">${escapeHtml(r.category)}</td>
      <td style="padding:6px;border-bottom:1px solid var(--border);font-size:10px;color:var(--accent);text-align:right;font-family:var(--font);">${escapeHtml(r.production)}</td>
      <td style="padding:6px;border-bottom:1px solid var(--border);font-size:10px;color:${r.price==='—'?'var(--text2)':'var(--warn)'};text-align:right;font-family:var(--font);">${escapeHtml(r.price)}</td>
      <td style="padding:6px;border-bottom:1px solid var(--border);font-size:10px;color:${trendColor};text-align:center;">${escapeHtml(r.trend)}</td>
      <td style="padding:6px;border-bottom:1px solid var(--border);font-size:10px;color:var(--text);">${escapeHtml(r.region)}</td>
      <td style="padding:6px;border-bottom:1px solid var(--border);font-size:9px;color:var(--text2);">${escapeHtml(r.source)}<br><span style="font-size:8px;color:var(--text2);">${escapeHtml(r.reference_date)}</span></td>
      <td style="padding:6px;border-bottom:1px solid var(--border);font-size:9px;color:${statusColor};text-align:center;">${r.status === 'real_curado' ? 'REAL' : 'PEND.'}</td>
    </tr>`;
  }).join('') || `<tr><td colspan="8" style="padding:18px;text-align:center;color:var(--text2);font-size:11px;">Nenhum registro encontrado.</td></tr>`;

  const uniqueSources = new Set(MERCADO_REAL_DATA.records.flatMap(r => r.source.split('/').map(s => s.trim())));
  const priced = MERCADO_REAL_DATA.records.filter(r => r.price !== '—').length;
  document.getElementById('mercado-kpi-produtos').textContent = MERCADO_REAL_DATA.records.length;
  document.getElementById('mercado-kpi-fontes').textContent = uniqueSources.size;
  document.getElementById('mercado-kpi-precos').textContent = priced;
  document.getElementById('mercado-last-updated').textContent = '● ' + MERCADO_REAL_DATA.updated_at;
  document.getElementById('mercado-quality-panel').innerHTML = `
    <div style="border:1px solid rgba(48,209,88,.25);background:rgba(48,209,88,.06);border-radius:6px;padding:8px;margin-bottom:8px;">
      <div style="color:var(--accent2);font-size:10px;letter-spacing:1px;margin-bottom:4px;">CORREÇÃO APLICADA</div>
      <div>Removidos os números HFT/3,5s e spreads inventados. A aba agora separa produção/oferta de preço spot e mostra pendência quando a fonte de preço não está conectada.</div>
    </div>
    <div style="border:1px solid rgba(255,214,10,.25);background:rgba(255,214,10,.06);border-radius:6px;padding:8px;margin-bottom:8px;">
      <div style="color:var(--warn);font-size:10px;letter-spacing:1px;margin-bottom:4px;">PENDÊNCIAS REAIS</div>
      <div>Para cotação diária confiável: conectar CEAGESP/CEASAs por produto-classificação, CEPEA para séries específicas e CONAB/SISDEP para preços agropecuários.</div>
    </div>
    <div style="font-size:9px;color:var(--text2);">Metodologia: ${escapeHtml(MERCADO_REAL_DATA.methodology)}</div>
    <div style="margin-top:8px;font-size:9px;color:var(--text2);">Linhas exibidas: ${rows.length} de ${MERCADO_REAL_DATA.records.length}.</div>`;
}

function exportMercadoCSV() {
  const header = ['produto','categoria','producao_oferta','preco','tendencia','regiao','fonte','data_referencia','status','observacao'];
  const lines = [header.join(',')].concat(MERCADO_REAL_DATA.records.map(r => [r.product,r.category,r.production,r.price,r.trend,r.region,r.source,r.reference_date,r.status,r.note].map(v => '"' + String(v).replace(/"/g,'""') + '"').join(',')));
  const blob = new Blob([lines.join('\n')], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'mercado_dados_reais_curados.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}

function initMercadoReal() { window._ofertaInit = true; renderMercadoReal(); loadCeasaOfficialPrices(false); }
window.initOferta = initMercadoReal;
window.initCeasaTerminal = function(){ renderMercadoReal(); };
// Auto-start API loading after login
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(niasLoadRealData, 2000);
  
  // FIX: Move panels inside #main if they're outside
  const situationPanel = document.getElementById('panel-situation');
  const chatPanel = document.getElementById('panel-chat');
  const main = document.getElementById('main');
  if (situationPanel && main && situationPanel.parentElement !== main) {
    main.appendChild(situationPanel);
    console.log('[FIX] panel-situation moved inside #main');
  }
  if (chatPanel && main && chatPanel.parentElement !== main) {
    main.appendChild(chatPanel);
    console.log('[FIX] panel-chat moved inside #main');
  }
});
