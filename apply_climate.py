import re

with open('nias.html', 'r', encoding='utf-8') as f:
    c = f.read()

orig = len(c)
changes = []

# ═══ STEP 9: CSS ═══
css_insert = """
/* CLIMATE INTELLIGENCE */
.climate-critical{border-left:3px solid var(--danger);animation:climatePulse 1.5s infinite;padding:6px 8px;margin:4px 0;font-size:10px;background:rgba(255,61,61,.06);border-radius:0 4px 4px 0;}
.climate-high{border-left:3px solid var(--warn);padding:6px 8px;margin:4px 0;font-size:10px;background:rgba(255,193,7,.06);border-radius:0 4px 4px 0;}
.climate-ok{border-left:3px solid var(--accent2);padding:6px 8px;margin:4px 0;font-size:10px;background:rgba(0,255,136,.04);border-radius:0 4px 4px 0;}
.odi-badge{font-size:11px;font-weight:bold;padding:2px 6px;border-radius:3px;display:inline-block;}
.odi-critical{background:rgba(255,61,61,.2);color:#ff3d3d;}
.odi-high{background:rgba(255,193,7,.2);color:#ffc107;}
.odi-medium{background:rgba(0,212,255,.15);color:var(--accent);}
.odi-low{background:rgba(0,255,136,.15);color:#00ff88;}
@keyframes climatePulse{0%,100%{opacity:1}50%{opacity:.5}}
"""
anchor_css = '@keyframes sonar-expand'
if anchor_css in c:
    c = c.replace(anchor_css, css_insert + anchor_css, 1)
    changes.append('CSS climate classes')

# ═══ STEP 1: Constants after argusCheckNdvi ═══
constants = """

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

"""
anchor_const = 'function argusCheckNdvi(mun) {'
if anchor_const in c:
    c = c.replace(anchor_const, constants + anchor_const, 1)
    changes.append('CLIMATE constants')

# ═══ STEP 3: HTML containers ═══

# WAR ROOM: add climate alerts div
war_anchor = '<div id="war-result" style="font-size:10px;line-height:1.6;">Selecione'
war_insert = '''<div id="war-climate-alerts" style="margin-bottom:10px;"></div>
          <div id="war-result" style="font-size:10px;line-height:1.6;">Selecione'''
if war_anchor in c:
    c = c.replace(war_anchor, war_insert, 1)
    changes.append('WAR ROOM climate div')

# SENTIMENTO: add climate impact div
sent_anchor = '<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:6px;" id="sent-gauges"></div>'
sent_insert = '''<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:6px;" id="sent-gauges"></div>
          <div id="sent-climate-impact" style="margin-top:8px;"></div>'''
if sent_anchor in c:
    c = c.replace(sent_anchor, sent_insert, 1)
    changes.append('SENTIMENTO climate div')

# LOGÍSTICA: add climate routes in right panel
log_anchor = 'SATURAÇÃO POR CORREDOR'
log_insert = '''ALERTAS CLIMÁTICOS — ROTAS</div>
          <div id="log-climate-routes" style="max-height:120px;overflow-y:auto;padding:4px 8px;font-size:9px;color:var(--text2);">Sem alertas climáticos ativos.</div>
          <div style="padding:6px 12px;color:var(--accent);font-size:10px;letter-spacing:2px;border-bottom:1px solid var(--border);border-top:1px solid var(--border);flex-shrink:0;margin-top:6px;">SATURAÇÃO POR CORREDOR'''
if log_anchor in c:
    c = c.replace(log_anchor, log_insert, 1)
    changes.append('LOGISTICA climate routes div')

# ═══ STEP 4: WAR ROOM presets ═══
war_presets_anchor = "{ name:'Pandemia 2.0 + colapso logístico', seca:15, bloq:70, cambio:7.0, icon:'🦠' },"
war_presets_insert = """{ name:'Pandemia 2.0 + colapso logístico', seca:15, bloq:70, cambio:7.0, icon:'🦠' },
    { name:'Massa polar + Geada Sul/Sudeste — polos tomate', seca:0, bloq:55, cambio:5.3, icon:'❄️', climateEvent:'geada' },
    { name:'Neve Serra Catarinense + BR-282 bloqueada', seca:0, bloq:90, cambio:5.1, icon:'🌨️', climateEvent:'neve' },
    { name:'Chuvas extremas Triângulo/PR — enchentes HF', seca:0, bloq:65, cambio:5.3, icon:'🌊', climateEvent:'enchente' },"""
if war_presets_anchor in c:
    c = c.replace(war_presets_anchor, war_presets_insert, 1)
    changes.append('WAR ROOM climate presets')

# ═══ STEP 7: NiasNews climate breaks ═══
news_anchor = "{ title:'Porto de Paranaguá: fila de navios reduz — 5 berços disponíveis', src:'NIA$ AIS', tag:'bullish' },"
news_insert = """{ title:'Porto de Paranaguá: fila de navios reduz — 5 berços disponíveis', src:'NIA$ AIS', tag:'bullish' },
        { title:'⚠️ CRÍTICO (SUL): Massa polar severa. Geada negra em polos de tomate. +22% preço em 72h.', src:'NIA$ Clima', tag:'bearish' },
        { title:'🚫 Serra Catarinense bloqueada por neve/gelo. Acesso ao trabalho -60%.', src:'NIA$ Logística', tag:'bearish' },
        { title:'💧 MATOPIBA: Excesso de chuva em colheita. Risco de podridão apical.', src:'NIA$ Clima', tag:'bearish' },
        { title:'🌡 ΔT >12°C em Ibiúna-SP. Estresse térmico em folhosas. Oferta reduzida.', src:'NIA$ ARGUS', tag:'bullish' },"""
if news_anchor in c:
    c = c.replace(news_anchor, news_insert, 1)
    changes.append('NiasNews climate breaks')

# ═══ STEP 2: NiasClimate module (after NiasNews bootstrap) ═══
nias_climate_module = """

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
    const el = document.getElementById('war-climate-alerts');
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
"""

bootstrap_anchor = "setTimeout(() => NiasNews.startAutoRefresh(), 3000);"
if bootstrap_anchor in c:
    c = c.replace(bootstrap_anchor, bootstrap_anchor + nias_climate_module, 1)
    changes.append('NiasClimate module')

# ═══ STEP 8: Bootstrap in niasLoadRealData ═══
boot_anchor = '// ── Schedule refresh every 15 minutes'
boot_insert = '''// ── Climate Intelligence ─────────────────────────────────────────
  if (typeof NiasClimate !== 'undefined' && !NiasClimate._running) {
    NiasClimate._running = true;
    await NiasClimate.run();
  }

  // ── Schedule refresh every 15 minutes'''
if boot_anchor in c:
    c = c.replace(boot_anchor, boot_insert, 1)
    changes.append('Bootstrap NiasClimate')

with open('nias.html', 'w', encoding='utf-8') as f:
    f.write(c)

print(f'Done — {len(c.splitlines())} lines (was {orig} chars)')
for ch in changes:
    print('  +', ch)
