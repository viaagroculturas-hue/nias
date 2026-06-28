// PredictX Live — interface futurista com dados oficiais/tempo real quando disponíveis
window.PredictXLive = {
  map:null, layers:[], data:null,
  esc(v){return String(v ?? '').replace(/[&<>'"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));},
  async load(force=false){
    const st=document.getElementById('pxx-live-status'); if(st) st.textContent='● consultando fontes';
    try{
      const res=await fetch('/api/predictix/live'+(force?'?force=1':''), {cache:'no-store'});
      const data=await res.json();
      this.data=data; this.render(data);
      if(st){st.textContent='● online'; st.style.color='#50C878';}
    }catch(e){
      if(st){st.textContent='● falha de rede'; st.style.color='#ff7b7b';}
      console.warn('PredictXLive', e);
    }
  },
  initMap(){
    const el=document.getElementById('pxx-map'); if(!el || this.map) return;
    if(!window.L){ el.innerHTML='<div style="padding:30px;color:#8eeaff;font-family:monospace">Leaflet não carregado.</div>'; return; }
    this.map=L.map(el,{zoomControl:true,attributionControl:false}).setView([29,-96],3);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:12}).addTo(this.map);
    addCountryContours(this.map, 'predictx-countries-real', ADMIN_BOUNDARY.northAmerica).catch(e => console.warn('predictx countries', e));
    addStateContours(this.map, 'predictx-states', ADMIN_BOUNDARY.northAmerica).catch(e => console.warn('predictx states', e));
  },
  markerIcon(score){
    const color = score>=82 ? '#ff4d6d' : score>=70 ? '#ffd166' : '#0a84ff';
    return L.divIcon({className:'',html:`<div style="width:18px;height:18px;border-radius:50%;background:${color};box-shadow:0 0 22px ${color};border:2px solid white"></div>`,iconSize:[18,18],iconAnchor:[9,9]});
  },
  renderMap(cities){
    this.initMap(); if(!this.map) return;
    this.layers.forEach(l=>this.map.removeLayer(l)); this.layers=[];
    cities.forEach(c=>{
      const m=L.marker([c.lat,c.lon],{icon:this.markerIcon(c.impact_score)}).addTo(this.map);
      m.bindPopup(`<b>${this.esc(c.city)}</b><br>${this.esc(c.country)}<br>Jogos: ${c.matches}<br>Score operacional: ${c.impact_score}/100<br>Risco: ${this.esc(c.risk_level)}`);
      this.layers.push(m);
    });
    const latlngs=cities.map(c=>[c.lat,c.lon]);
    if(latlngs.length){ try{this.map.fitBounds(latlngs,{padding:[28,28]});}catch(e){} }
  },
  render(data){
    const wc=data.worldcup_2026||{}; const event=wc.event||{}; const cities=wc.cities_ranked||[];
    const set=(id,v)=>{const e=document.getElementById(id); if(e)e.textContent=v;};
    set('pxx-kpi-event', event.name ? 'ATIVO' : '—');
    set('pxx-kpi-cities', cities.length || '—');
    set('pxx-kpi-risk', cities[0]?.risk_level?.toUpperCase() || '—');
    set('pxx-kpi-sources', (data.sources||[]).length || '—');
    set('pxx-updated', data.generated_at ? 'UTC '+new Date(data.generated_at).toISOString().slice(11,16) : 'UTC --');
    const why=document.getElementById('pxx-worldcup-why');
    if(why){
      const bullets=(wc.top_impacts||[]).map(x=>`<li>${this.esc(x)}</li>`).join('');
      why.innerHTML=`<b>${this.esc(event.name||'Evento')}</b><br>${this.esc(wc.summary||'')}<ul style="margin:8px 0 0 18px;padding:0;color:#bfefff;">${bullets}</ul>`;
    }
    const cityList=document.getElementById('pxx-city-list');
    if(cityList){
      cityList.innerHTML=cities.slice(0,10).map(c=>`<div style="border:1px solid rgba(10,132,255,.18);border-radius:12px;padding:9px;background:rgba(255,255,255,.025);">
        <div style="display:flex;justify-content:space-between;gap:8px;"><b style="color:#e8fbff">${this.esc(c.city)}</b><span style="color:#ffe681;font-family:monospace">${c.impact_score}/100</span></div>
        <div style="font-size:11px;color:#8fa4b8;margin-top:3px;">${this.esc(c.country)} · ${c.matches} jogos · risco ${this.esc(c.risk_level)}</div>
      </div>`).join('');
    }
    const signals=document.getElementById('pxx-signal-list');
    if(signals){
      const rows=[...(data.global_signals||[])];
      (data.regional_risks||[]).slice(0,3).forEach(r=>rows.push({signal:r.name,status:r.risk_level,source:r.weather?.source||'NASA POWER',why:(r.reasons||[]).join('; '),is_realtime:!!r.weather?.ok}));
      signals.innerHTML=rows.map(s=>`<div style="border-left:3px solid ${s.is_realtime?'#50C878':'#ffd166'};padding:8px 10px;background:rgba(255,255,255,.025);border-radius:10px;">
        <div style="display:flex;justify-content:space-between"><b style="color:#e8fbff">${this.esc(s.signal)}</b><span style="font-size:10px;color:${s.is_realtime?'#50C878':'#ffd166'}">${s.is_realtime?'tempo real':'monitorado'}</span></div>
        <div style="font-size:11px;color:#a8bbcf;margin:4px 0;">${this.esc(s.why)}</div>
        <div style="font-size:10px;color:#6f8295;">Fonte: ${this.esc(s.source)} · status: ${this.esc(s.status)}</div>
      </div>`).join('');
    }
    this.renderMap(cities);
  }
};

(function(){
  const oldShow=window.showPanel;
  window.showPanel=function(name){
    const r=oldShow ? oldShow.apply(this, arguments) : undefined;
    if(name==='predictix') setTimeout(()=>PredictXLive.load(false), 120);
    return r;
  };
  document.addEventListener('DOMContentLoaded',()=>setTimeout(()=>{ if(document.getElementById('panel-predictix')?.classList.contains('active')) PredictXLive.load(false); },500));
})();





// ═══════════════════════════════════════════════════════════════════
// DASHBOARD INICIAL — cards atualizados por API real/curada
// ═══════════════════════════════════════════════════════════════════
const DashboardLive = {
  lastWeather: [],
  lastTopbar: null,
  async load(){
    try{
      const r = await fetch('/api/dashboard/summary', {cache:'no-store'});
      if(!r.ok) throw new Error('HTTP ' + r.status);
      const data = await r.json();
      this.lastWeather = data.weather || [];
      this.lastTopbar = data.topbar || null;
      this.renderCards(data.cards || []);
      this.renderWeather(data.weather || []);
      this.renderAlerts(data.alerts || []);
      this.renderTopbar(data.topbar || {}, data.quality || {});
      this.renderMarket(data.market || []);
      this.renderMacro(data.macro || {});
      this.renderSituation(data.situation || {});
      this.renderSources(data.sources || []);
      this.renderStamp(data);
    }catch(e){
      console.warn('Dashboard summary indisponível:', e);
      this.renderStamp({status:'degraded', message:'API do dashboard indisponível'});
    }
  },
  renderCards(cards){
    const byId = Object.fromEntries(cards.map(c=>[c.id,c]));
    ['kpi-soja','kpi-milho','kpi-ndvi','kpi-hum','kpi-boi','kpi-horti'].forEach(id=>{
      const c=byId[id];
      if(!c) return;
      const val=document.getElementById(id);
      const delta=document.getElementById('kd-' + id.replace('kpi-',''));
      const label=val?.parentElement?.querySelector('.kpi-label');
      if(label && c.label) label.textContent = c.label;
      if(val) val.textContent = c.value || '—';
      if(delta){
        delta.textContent = c.delta || 'sem atualização';
        delta.classList.remove('up','down','neutral');
        delta.classList.add(c.delta_class || 'neutral');
        delta.title = `Fonte: ${c.source || 'não informada'} | Data: ${c.date || '—'} | Qualidade: ${c.quality || '—'}`;
      }
    });
  },
  renderWeather(rows){
    rows.slice(0,6).forEach((w,i)=>{
      const n=i+1;
      const card=document.querySelectorAll('.weather-row .wx-card')[i];
      if(!card) return;
      const region=card.querySelector('.wx-region');
      const t=document.getElementById('wx-t'+n);
      const h=document.getElementById('wx-h'+n);
      const wind=document.getElementById('wx-w'+n);
      const st=document.getElementById('wx-s'+n);
      if(region) region.textContent = w.region || 'Região monitorada';
      if(t) t.textContent = w.temp || '—';
      if(h) h.textContent = w.humidity || 'Umid: —';
      if(wind) wind.textContent = w.wind || 'Vento: —';
      if(st){
        st.textContent = w.status || 'monitorado';
        st.style.color = w.level === 'danger' ? 'var(--danger)' : w.level === 'warn' ? 'var(--warn)' : 'var(--accent2)';
        st.title = `Fonte: ${w.source || '—'} | Data: ${w.date || '—'} | Qualidade: ${w.quality || '—'}`;
      }
    });
  },
  renderAlerts(alerts){
    const strip=document.querySelector('#alerts-strip .alert-scroll');
    const list=document.getElementById('alerts-list');
    if(strip){
      strip.innerHTML = alerts.length
        ? alerts.map(a=>`<span class="alert-item">⚠ ${escapeHtml(a.title||'ALERTA')} — ${escapeHtml(a.region_key||'BR')} · ${escapeHtml(a.severity_label||a.severity||'') }<span class="sep">|</span></span>`).join('')
        : '<span class="alert-item">SEM ALERTAS OFICIAIS ATIVOS — aguardando fontes observadas<span class="sep">|</span></span>';
    }
    if(list){
      list.innerHTML = alerts.length ? alerts.slice(0,6).map(a=>`
        <div class="alert-card" onclick="showPanel('map')" title="Fonte: ${escapeHtml(a.source||'—')} | Qualidade: ${escapeHtml(a.quality||'—')}">
          <div class="alert-card-header"><span class="alert-card-title">${escapeHtml(a.title||'ALERTA')}</span><span class="severity ${(a.severity==='vermelho')?'alta':(a.severity==='laranja')?'media':'baixa'}">${escapeHtml(a.severity_label||a.severity||'ATENÇÃO')}</span></div>
          <div class="alert-card-body">${escapeHtml(a.region_key||'BR')} — ${escapeHtml(a.message||'Sem descrição detalhada.')}</div>
        </div>`).join('') : '<div class="alert-card"><div class="alert-card-header"><span class="alert-card-title">SEM ALERTAS ATIVOS</span><span class="severity baixa">OK</span></div><div class="alert-card-body">Nenhum alerta válido encontrado nas fontes carregadas.</div></div>';
    }
    const newsSummary=document.getElementById('news-summary');
    if(newsSummary) newsSummary.textContent = `${alerts.length} alertas ativos`;
  },
  renderTopbar(topbar, quality){
    if(topbar.temperature){ setLiveVal('ts-temp', topbar.temperature, 0, 0); setLiveVal('cs-temp', topbar.temperature, 0, 0); }
    if(topbar.ndvi){ setLiveVal('ts-ndvi', topbar.ndvi, 0, 0); setLiveVal('cs-ndvi', topbar.ndvi, 0, 0); }
    const badge=document.querySelector('.badge-live');
    if(badge){
      badge.textContent = topbar.status === 'LIVE' ? '● LIVE DATA' : '● DEGRADED';
      badge.title = `Cards observados: ${quality.observed_cards || 0}/${quality.total_cards || 0}`;
    }
  },
  renderMarket(rows){
    window.NIAS_DASHBOARD_MARKET = rows;
    const el=document.getElementById('flv-kpi-alerts');
    if(el) el.textContent = String(rows.length || 0);
  },
  renderMacro(macro){
    window.NIAS_DASHBOARD_MACRO = macro;
  },
  renderSituation(situation){
    window.NIAS_DASHBOARD_SITUATION = situation;
  },
  renderSources(sources){
    window.NIAS_DASHBOARD_SOURCES = sources;
  },
  renderStamp(data){
    let stamp=document.getElementById('dashboard-data-stamp');
    if(!stamp){
      const header=document.querySelector('.topbar-right') || document.querySelector('.badge-live')?.parentElement;
      if(header){
        stamp=document.createElement('span');
        stamp.id='dashboard-data-stamp';
        stamp.style.cssText='font-size:10px;color:var(--text2);margin-left:10px;';
        header.appendChild(stamp);
      }
    }
    if(stamp){
      const dt=data.updated_at ? new Date(data.updated_at).toLocaleString('pt-BR') : '—';
      stamp.textContent = `Dados: ${data.status || '—'} · ${dt}`;
      stamp.title = data.message || (data.quality ? data.quality.rule : 'Resumo atualizado por API');
    }
  }
};

document.addEventListener('DOMContentLoaded',()=>{
  setTimeout(()=>DashboardLive.load(),250);
  setInterval(()=>DashboardLive.load(),15*60*1000);
});

// ═══════════════════════════════════════════════════════════════════
// SYSTEM AUDIT — fontes reais, qualidade e abas consolidadas
// ═══════════════════════════════════════════════════════════════════
async function runSystemAudit(force=false){
  const summary = document.getElementById('system-audit-summary');
  const cards = document.getElementById('system-audit-cards');
  const warnings = document.getElementById('system-audit-warnings');
  if(!summary || !cards || !warnings) return;
  summary.textContent = 'Auditando fontes, tabelas e abas...';
  try{
    const res = await fetch('/api/system/audit' + (force ? '?force=1' : ''));
    const data = await res.json();
    const trusted = data.trusted_sources || [];
    const hidden = data.hidden_redundant_tabs || [];
    const tables = (data.data_quality && data.data_quality.tables) || [];
    const synth = tables.reduce((a,t)=>a+(Number(t.synthetic_rows||0)),0);
    summary.innerHTML = `Status: <strong style="color:var(--accent2)">${escapeHtml(data.status||'ok')}</strong> · Fontes auditáveis: <strong>${trusted.length}</strong> · Abas redundantes ocultas: <strong>${hidden.length}</strong> · Linhas sintéticas/proxy no banco: <strong style="color:${synth?'var(--warn)':'var(--accent2)'}">${synth}</strong>`;
    cards.innerHTML = '';
    const byCat = {};
    trusted.forEach(s=>{ byCat[s.category]=(byCat[s.category]||0)+1; });
    cards.innerHTML += `<div class="audit-card"><strong>Política de fonte</strong>${escapeHtml(data.source_policy||'Sem política carregada.')}</div>`;
    cards.innerHTML += `<div class="audit-card"><strong>Abas mantidas</strong>${(data.core_tabs||[]).map(t=>escapeHtml(t.label)).join(' · ')}</div>`;
    cards.innerHTML += `<div class="audit-card"><strong>Fontes por categoria</strong>${Object.entries(byCat).map(([k,v])=>`${escapeHtml(k)}: ${v}`).join('<br>')}</div>`;
    cards.innerHTML += `<div class="audit-card"><strong>Banco local</strong>${escapeHtml((data.data_quality&&data.data_quality.database)||'não localizado')}<br>Tabelas FLV: ${tables.length}</div>`;
    const topWarn = ((data.data_quality&&data.data_quality.warnings)||[]).slice(0,10);
    warnings.innerHTML = topWarn.length ? topWarn.map(w=>`<li>${escapeHtml(w)}</li>`).join('') : '<li>Nenhum alerta crítico de qualidade encontrado.</li>';
  }catch(e){
    summary.innerHTML = `<span style="color:var(--danger)">Falha na auditoria:</span> ${escapeHtml(String(e.message||e))}`;
    cards.innerHTML = '';
    warnings.innerHTML = '<li>Verifique se o servidor Python está em execução.</li>';
  }
}

function markDeprecatedPanels(){
  const deprecated=['map','logistica','warroom','flv_insights','flv_reports','predictix','macropolos','hyperlocal','sentiment','esg'];
  deprecated.forEach(id=>{
    const p=document.getElementById('panel-'+id);
    if(p){ p.setAttribute('data-deprecated','true'); }
  });
}

document.addEventListener('DOMContentLoaded',()=>{ markDeprecatedPanels(); setTimeout(()=>runSystemAudit(false),800); });


// ═══════════════════════════════════════════════════════════════════
// GUARDA DE CAMPOS — duplicata removida, usa definição principal acima
// ═══════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════
// NiasIntelFrontend — Conecta Motor de Inteligência ao Dashboard
// ═══════════════════════════════════════════════════════════════════════
const NiasIntelFrontend = {
  _cache: {},
  _interval: null,

  async _fetch(endpoint) {
    try {
      const r = await fetch('/api/intelligence/' + endpoint);
      if (!r.ok) return null;
      return await r.json();
    } catch(e) { return null; }
  },

  _priorityColor(p) {
    return p === 'critica' ? 'var(--danger)' : p === 'alta' ? '#ff9f0a' : p === 'media' ? 'var(--warn)' : 'var(--accent2)';
  },

  _priorityLabel(p) {
    return p === 'critica' ? 'CRÍTICO' : p === 'alta' ? 'ALTA' : p === 'media' ? 'MÉDIA' : 'BAIXA';
  },

  _confidenceIcon(c) {
    return c === 'alta' ? '●●●' : c === 'media' ? '●●○' : '●○○';
  },

  async renderAlerts() {
    const data = await this._fetch('alerts');
    const el = document.getElementById('intel-alerts-list');
    if (!el || !data || !data.alerts) return;

    const alerts = data.alerts.slice(0, 6);
    if (!alerts.length) {
      el.innerHTML = '<div style="padding:8px;color:var(--accent2);font-size:11px;">Nenhum alerta ativo no momento.</div>';
      return;
    }

    el.innerHTML = alerts.map(a => `
      <div class="alert-card" style="border-left:3px solid ${this._priorityColor(a.prioridade)}">
        <div class="alert-card-header">
          <span class="alert-card-title">${a.titulo}</span>
          <span class="severity" style="background:${this._priorityColor(a.prioridade)}22;color:${this._priorityColor(a.prioridade)}">${this._priorityLabel(a.prioridade)}</span>
        </div>
        <div class="alert-card-body" style="font-size:10px;">${a.explicacao || ''}</div>
        <div style="font-size:9px;color:var(--accent2);margin-top:3px;">
          <b>Ação:</b> ${a.acao_recomendada || '—'}<br>
          <span>Confiança: ${this._confidenceIcon(a.confianca)} ${a.confianca || '—'}</span>
          <span style="float:right">${(a.fontes||[]).join(', ')}</span>
        </div>
      </div>
    `).join('');
  },

  async renderOpportunities() {
    const data = await this._fetch('opportunities');
    const el = document.getElementById('intel-opps-list');
    if (!el || !data || !data.opportunities) return;

    const opps = data.opportunities.slice(0, 5);
    if (!opps.length) {
      el.innerHTML = '<div style="font-size:10px;color:var(--accent2);">Analisando mercado...</div>';
      return;
    }

    el.innerHTML = opps.map(o => {
      const scoreColor = o.score >= 75 ? 'var(--accent)' : o.score >= 50 ? 'var(--warn)' : 'var(--accent2)';
      const tipoIcon = o.tipo === 'venda' ? '📈' : o.tipo === 'compra' ? '📉' : '⚠️';
      return `
        <div style="padding:4px 6px;border-bottom:1px solid var(--border);font-size:10px;">
          <div style="display:flex;align-items:center;gap:6px;">
            <span>${tipoIcon}</span>
            <span style="font-weight:bold;color:var(--fg)">${o.nome || o.produto}</span>
            <span style="margin-left:auto;font-weight:bold;color:${scoreColor}">${o.score}/100</span>
            <span style="font-size:8px;color:var(--accent2)">${o.tipo.toUpperCase()}</span>
          </div>
          <div style="color:var(--accent2);font-size:9px;margin-top:2px;">${o.acao_recomendada || ''}</div>
          <div style="font-size:8px;color:var(--accent2);margin-top:1px;">
            Confiança: ${this._confidenceIcon(o.confianca)} | Urgência: ${o.urgencia} | Risco: ${o.risco}
          </div>
        </div>`;
    }).join('');
  },

  async renderFreshness() {
    const data = await this._fetch('freshness');
    const el = document.getElementById('intel-freshness-badge');
    if (!el || !data) return;

    const statusColors = { fresh: 'var(--accent)', stale: 'var(--warn)', critical: 'var(--danger)' };
    const statusLabels = { fresh: '● DADOS ATUALIZADOS', stale: '◐ DADOS PARCIAIS', critical: '○ DADOS ANTIGOS' };
    el.style.color = statusColors[data.data_freshness] || 'var(--accent2)';
    el.textContent = statusLabels[data.data_freshness] || data.data_freshness;
  },

  async renderReport() {
    const data = await this._fetch('report');
    if (!data || !data.resumo) return;
    this._cache.report = data;
  },

  async renderPredictions() {
    const data = await this._fetch('predictions');
    if (!data || !data.predictions) return;
    this._cache.predictions = data.predictions;
  },

  async init() {
    await Promise.all([
      this.renderAlerts(),
      this.renderOpportunities(),
      this.renderFreshness(),
      this.renderReport(),
      this.renderPredictions(),
    ]);

    // Refresh a cada 5 minutos
    this._interval = setInterval(() => {
      this.renderAlerts();
      this.renderOpportunities();
      this.renderFreshness();
    }, 300000);
  }
};

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => NiasIntelFrontend.init(), 3000);
  setTimeout(() => NiasClimateFrontend.init(), 4000);
});

// ═══════════════════════════════════════════════════════════════════════
// NiasClimateFrontend — Inteligência Climática no Dashboard
// ═══════════════════════════════════════════════════════════════════════
const NiasClimateFrontend = {
  _cache: {},

  async _fetch(endpoint) {
    try {
      const r = await fetch('/api/climate/' + endpoint);
      if (!r.ok) return null;
      return await r.json();
    } catch(e) { return null; }
  },

  async renderClimateAlerts() {
    const data = await this._fetch('alerts');
    const el = document.getElementById('climate-alerts-panel');
    if (!el) return;
    if (!data || !data.alerts || !data.alerts.length) {
      el.innerHTML = '<div style="padding:6px;font-size:10px;color:var(--accent2);">Sem eventos climáticos extremos no momento.</div>';
      return;
    }
    const alerts = data.alerts.slice(0, 4);
    el.innerHTML = alerts.map(a => {
      const pColor = a.priority === 'critica' ? 'var(--danger)' : a.priority === 'alta' ? '#ff9f0a' : 'var(--warn)';
      const pLabel = a.priority === 'critica' ? 'CRÍTICO' : a.priority === 'alta' ? 'ALTO' : 'MÉDIO';
      return `
        <div style="padding:5px 7px;border-left:3px solid ${pColor};margin-bottom:4px;background:${pColor}11;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:10px;font-weight:bold;color:var(--fg);">${a.titulo}</span>
            <span style="font-size:8px;padding:1px 4px;border-radius:2px;background:${pColor}22;color:${pColor};">${pLabel}</span>
          </div>
          <div style="font-size:9px;color:var(--accent2);margin-top:2px;">${a.explicacao || ''}</div>
          <div style="font-size:8px;color:var(--accent2);margin-top:2px;">
            <b>Ação:</b> ${a.acao_recomendada || '—'} | Confiança: ${a.confidence || '—'}
          </div>
        </div>`;
    }).join('');
  },

  async renderSourcesStatus() {
    try {
      const r = await fetch('/api/sources/status');
      if (!r.ok) return;
      const data = await r.json();
      const el = document.getElementById('sources-status-bar');
      if (!el || !data || !data.sources) return;
      const items = Object.entries(data.sources).map(([key, s]) => {
        const color = s.status === 'real' ? 'var(--accent)' : s.status === 'fallback' ? 'var(--warn)' : 'var(--danger)';
        const label = key.toUpperCase();
        const statusTxt = s.status === 'real' ? 'API REAL' : 'FALLBACK';
        return `<span style="font-size:8px;color:${color};margin-right:8px;">● ${label}: ${statusTxt}</span>`;
      }).join('');
      el.innerHTML = items;

      // Pipeline & Storage info
      const pipeEl = document.getElementById('pipeline-status-bar');
      if (pipeEl && data.storage) {
        const persistent = data.storage.persistent;
        const storageIcon = persistent ? '✅' : '⚠️';
        const storageText = persistent ? 'Dados protegidos entre deploys' : 'Storage efêmero — configure Persistent Disk';
        const storageColor = persistent ? 'var(--accent)' : 'var(--danger)';
        pipeEl.innerHTML = `<span style="font-size:8px;color:${storageColor};">${storageIcon} ${storageText}</span>`;
      }
    } catch(e) {}
  },

  async renderClimateSummary() {
    const data = await this._fetch('report');
    const el = document.getElementById('climate-summary-card');
    if (!el || !data) return;
    const evCount = data.total_events || 0;
    const alertCount = data.total_alerts || 0;
    const regions = (data.regions_at_risk || []).length;
    const products = (data.products_likely_up || []).length;

    if (evCount === 0) {
      el.innerHTML = `<div style="padding:6px;font-size:10px;color:var(--accent);">🌤 Sem eventos climáticos críticos. Operação normal.</div>`;
      return;
    }
    el.innerHTML = `
      <div style="padding:6px;">
        <div style="font-size:10px;font-weight:bold;color:var(--warn);">🌦 Inteligência Climática</div>
        <div style="font-size:9px;color:var(--fg);margin-top:3px;">
          ${regions} região(ões) em alerta<br>
          ${products} produto(s) com risco de alta<br>
          ${(data.logistic_bottlenecks||[]).length} gargalo(s) logístico(s)<br>
          <span style="color:var(--accent2);">Confiança: ${data.confidence || 'media'}</span>
        </div>
      </div>`;
  },

  async renderPriceImpact() {
    const data = await this._fetch('price-impact');
    const el = document.getElementById('climate-price-impact-panel');
    if (!el) return;
    if (!data || !data.items || !data.items.length) {
      const msg = data && data.message ? data.message : 'Sem correlação clima×preço disponível no momento.';
      el.innerHTML = `<div style="padding:6px;font-size:9px;color:var(--accent2);">${msg}</div>`;
      return;
    }
    const items = data.items.slice(0, 5);
    el.innerHTML = `
      <div style="padding:4px 6px;font-size:10px;font-weight:bold;color:var(--fg);border-bottom:1px solid var(--border);margin-bottom:3px;">🌦 Clima × Preço</div>
      ${items.map(item => {
        const impactColor = item.correlation > 0.7 ? 'var(--danger)' : item.correlation > 0.5 ? '#ff9f0a' : 'var(--warn)';
        const confLabel = item.confidence === 'alta' ? '🔴' : item.confidence === 'média' ? '🟠' : '🟡';
        return `
          <div style="padding:4px 6px;border-left:3px solid ${impactColor};margin-bottom:3px;background:${impactColor}08;">
            <div style="font-size:9px;font-weight:bold;color:var(--fg);">
              ${item.product_name || item.product} — ${item.region}
            </div>
            <div style="font-size:8px;color:var(--accent2);margin-top:1px;">
              Clima: ${item.weather_signal} | Preço: ${item.price_signal}
            </div>
            <div style="font-size:8px;color:${impactColor};margin-top:1px;">
              Impacto: ${item.expected_impact} (${item.price_impact_range}) | Corr: ${item.correlation}
            </div>
            <div style="font-size:8px;color:var(--accent2);margin-top:1px;">
              ${confLabel} ${item.recommended_action || '—'}
            </div>
          </div>`;
      }).join('')}
      <div style="font-size:7px;color:var(--accent2);padding:2px 6px;">Fonte: ${data.source || 'NiasClimate'} | Modo: ${data.mode || '—'}</div>`;
  },

  async init() {
    await Promise.all([
      this.renderClimateAlerts(),
      this.renderSourcesStatus(),
      this.renderClimateSummary(),
      this.renderPriceImpact(),
    ]);
    // Refresh a cada 10 min
    setInterval(() => {
      this.renderClimateAlerts();
      this.renderClimateSummary();
      this.renderPriceImpact();
    }, 600000);
  }
};


