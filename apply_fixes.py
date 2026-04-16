import re, shutil, os

src = 'nias.html'
shutil.copy(src, src + '.bak2')

with open(src, encoding='utf-8') as f:
    c = f.read()

orig_len = len(c)
changes = []

# ── FIX 1: CSS — map flex:1 ─────────────────────────────────────────
old = '#map{width:100%;height:100%;}'
new = '#map{width:100%;flex:1;min-height:300px;}\n#map-municipal{width:100%;flex:1;min-height:300px;}'
if old in c:
    c = c.replace(old, new, 1); changes.append('FIX1 #map css')
else:
    changes.append('SKIP1 #map css already patched or missing')

# ── FIX 2: invalidateSize at end of initMap ─────────────────────────
old2 = '  ]).addTo(leafletMap);\n}'
new2 = '  ]).addTo(leafletMap);\n  setTimeout(() => leafletMap && leafletMap.invalidateSize(), 120);\n}'
# Only replace the one inside initMap (before initSankey)
if old2 in c:
    c = c.replace(old2, new2, 1); changes.append('FIX2 initMap invalidateSize')
else:
    changes.append('SKIP2 anchor not found')

# ── FIX 3: invalidateSize at end of initMunicipal ───────────────────
old3 = '  setTimeout(addCrossBorderVectors, 800);\n  // IBGE drill-down system (state choropleth loads on top)\n  setTimeout(initStateChoropleth, 200);\n}'
new3 = '  setTimeout(addCrossBorderVectors, 800);\n  // IBGE drill-down system (state choropleth loads on top)\n  setTimeout(initStateChoropleth, 200);\n  setTimeout(() => munMap && munMap.invalidateSize(), 120);\n}'
if old3 in c:
    c = c.replace(old3, new3, 1); changes.append('FIX3 initMunicipal invalidateSize')
else:
    changes.append('SKIP3 anchor not found')

# ── FIX 4: showPanel — deferred sankey + invalidateSize + chat + biocommand ─
old4 = ('  if (id === \'map\' && !window._mapInit) initMap();\n'
        '  if (id === \'logistica\' && !window._sankeyInit) { initSankey(); updateArbitragem(); updateEcoScore(); updateAIS(); }\n'
        '  if (id === \'oferta\' && !window._ofertaInit) { initOferta(); initCeasaTerminal(); }\n'
        '  if (id === \'municipal\' && !window._munInit) initMunicipal();\n'
        '  if (id === \'macropolos\' && !window._macroInit) initMacroPolos();\n'
        '}')
new4 = ('  if (id === \'map\' && !window._mapInit) initMap();\n'
        '  if (id === \'map\') setTimeout(() => leafletMap && leafletMap.invalidateSize(), 120);\n'
        '  if (id === \'logistica\' && !window._sankeyInit) setTimeout(() => { initSankey(); updateArbitragem(); updateEcoScore(); updateAIS(); }, 50);\n'
        '  if (id === \'logistica\' && window._sankeyInit) setTimeout(updateArbitragem, 50);\n'
        '  if (id === \'oferta\' && !window._ofertaInit) { initOferta(); initCeasaTerminal(); }\n'
        '  if (id === \'municipal\' && !window._munInit) initMunicipal();\n'
        '  if (id === \'municipal\') setTimeout(() => munMap && munMap.invalidateSize(), 120);\n'
        '  if (id === \'biocommand\') initBioCommand();\n'
        '  if (id === \'macropolos\' && !window._macroInit) initMacroPolos();\n'
        '  if (id === \'chat\' && !window._chatInit) initChatIA();\n'
        '}')
if old4 in c:
    c = c.replace(old4, new4, 1); changes.append('FIX4 showPanel deferred+guards')
else:
    changes.append('SKIP4 showPanel anchor not found')

# ── FIX 5: showPanel idx — add biocommand:5, shift macropolos/chat ──
old5 = "const idx = {overview:0, map:1, logistica:2, oferta:3, municipal:4, macropolos:5, chat:6};"
new5 = "const idx = {overview:0, map:1, logistica:2, oferta:3, municipal:4, biocommand:5, macropolos:6, chat:7};"
if old5 in c:
    c = c.replace(old5, new5, 1); changes.append('FIX5 idx biocommand')
else:
    changes.append('SKIP5 idx already patched or missing')

# ── FIX 6: setTheme — guard updateArbitragem ────────────────────────
old6 = '  // Cyber mode: re-apply arb classes with blink intensity\n  updateArbitragem();\n}'
new6 = '  // Cyber mode: re-apply arb classes only if panel already rendered\n  if (window._sankeyInit) updateArbitragem();\n}'
if old6 in c:
    c = c.replace(old6, new6, 1); changes.append('FIX6 setTheme guard')
else:
    changes.append('SKIP6 setTheme anchor not found')

# ── FIX 7: initChatIA before sendMessage ────────────────────────────
old7 = '  msgs.scrollTop = msgs.scrollHeight;\n}\n\nfunction sendMessage() {'
new7 = ('  msgs.scrollTop = msgs.scrollHeight;\n}\n\n'
        'function initChatIA() {\n'
        '  if (window._chatInit) return;\n'
        '  window._chatInit = true;\n'
        '  const msgs = document.getElementById(\'chat-messages\');\n'
        '  if (msgs) msgs.scrollTop = msgs.scrollHeight;\n'
        '}\n\n'
        'function sendMessage() {')
if old7 in c:
    c = c.replace(old7, new7, 1); changes.append('FIX7 initChatIA')
else:
    changes.append('SKIP7 sendMessage anchor not found')

# ── FIX 8: BIO-COMMAND nav button ───────────────────────────────────
old8 = ("    <button class=\"nav-btn\" onclick=\"showPanel('municipal')\" title=\"Análise Municipal\">"
        "<span>⬢</span><span class=\"nav-label\">ANÁLISE MUNICIPAL</span></button>\n"
        "    <button class=\"nav-btn\" onclick=\"showPanel('macropolos')\" title=\"Macro-Polos Continental\">"
        "<span>✦</span><span class=\"nav-label\">MACRO-POLOS</span></button>")
new8 = ("    <button class=\"nav-btn\" onclick=\"showPanel('municipal')\" title=\"Análise Municipal\">"
        "<span>⬢</span><span class=\"nav-label\">ANÁLISE MUNICIPAL</span></button>\n"
        "    <button class=\"nav-btn\" onclick=\"showPanel('biocommand')\" title=\"BIO-COMMAND — Mapa Integrado\">"
        "<span>⬡</span><span class=\"nav-label\">BIO-COMMAND</span></button>\n"
        "    <button class=\"nav-btn\" onclick=\"showPanel('macropolos')\" title=\"Macro-Polos Continental\">"
        "<span>✦</span><span class=\"nav-label\">MACRO-POLOS</span></button>")
if old8 in c:
    c = c.replace(old8, new8, 1); changes.append('FIX8 BIO-COMMAND nav btn')
else:
    changes.append('SKIP8 nav anchor not found')

# ── FIX 9: BIO-COMMAND CSS (insert after blink-badge keyframe) ──────
old9 = '@keyframes blink-badge{0%,100%{opacity:1}50%{opacity:.5}}'
bc_css = '''
/* BIO-COMMAND PANEL */
#panel-biocommand{position:relative;overflow:hidden;}
#bc-topbar{position:absolute;top:0;left:0;right:0;height:36px;z-index:1200;background:rgba(11,14,20,.88);backdrop-filter:blur(8px);border-bottom:1px solid rgba(0,212,255,.22);display:flex;align-items:center;padding:0 12px;gap:10px;flex-shrink:0;}
#bc-topbar .bc-title{color:var(--accent);font-size:11px;font-weight:bold;letter-spacing:2px;}
.bc-sidebar{position:absolute;top:36px;bottom:0;z-index:1100;width:260px;background:rgba(11,14,20,.78);backdrop-filter:blur(14px);border:1px solid rgba(0,212,255,.18);display:flex;flex-direction:column;transition:transform .28s cubic-bezier(.4,0,.2,1);}
#bc-left{left:0;border-right:1px solid rgba(0,212,255,.18);}
#bc-right{right:0;border-left:1px solid rgba(0,212,255,.18);transform:translateX(260px);}
#bc-right.open{transform:translateX(0);}
#bc-left.collapsed{transform:translateX(-260px);}
#bc-map{position:absolute;inset:36px 0 0 0;z-index:1;}
.bc-sh{height:32px;background:rgba(0,212,255,.07);border-bottom:1px solid rgba(0,212,255,.14);display:flex;align-items:center;padding:0 10px;flex-shrink:0;font-size:9px;color:var(--accent);letter-spacing:1px;}
.bc-body{flex:1;overflow-y:auto;padding:8px;}
.bc-body::-webkit-scrollbar{width:3px;}
.bc-body::-webkit-scrollbar-thumb{background:rgba(0,212,255,.3);border-radius:2px;}
.bc-kv{display:flex;justify-content:space-between;align-items:center;padding:3px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:10px;}
.bc-kv .k{color:var(--text2);}
.bc-kv .v{color:var(--text);font-weight:bold;}
.bc-kv .v.good{color:var(--accent2);}
.bc-kv .v.warn{color:var(--warn);}
.bc-kv .v.bad{color:var(--danger);}
.bc-close{background:none;border:none;color:var(--text2);font-size:14px;cursor:pointer;padding:0 6px;flex-shrink:0;}
.bc-close:hover{color:var(--danger);}
.bc-toggle-btn{background:none;border:1px solid rgba(0,212,255,.3);color:var(--accent);font-family:var(--font);font-size:9px;padding:2px 8px;border-radius:3px;cursor:pointer;white-space:nowrap;flex-shrink:0;}
.bc-toggle-btn:hover{background:rgba(0,212,255,.12);}
.bc-arb-row{padding:5px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:10px;}
.bc-arb-best{color:var(--accent2);}
.bc-arb-label{font-size:9px;color:var(--text2);margin-top:2px;}'''
new9 = old9 + bc_css
if old9 in c:
    c = c.replace(old9, new9, 1); changes.append('FIX9 BIO-COMMAND CSS')
else:
    changes.append('SKIP9 blink-badge not found')

# ── FIX 10: BIO-COMMAND HTML panel (insert before LOGÍSTICA comment) ─
old10 = '    <!-- ═══ PANEL: LOGÍSTICA ═══ -->'
bc_html = '''    <!-- ═══ PANEL: BIO-COMMAND ═══ -->
    <div class="panel" id="panel-biocommand">
      <div id="bc-topbar">
        <span class="bc-title">N<span style="color:var(--accent2)">IA</span>$ · BIO-COMMAND</span>
        <span class="panel-badge ok" style="font-size:9px;">MAPA INTEGRADO</span>
        <span class="badge-live" style="font-size:9px;">● LIVE</span>
        <div style="margin-left:auto;display:flex;align-items:center;gap:6px;">
          <button class="bc-toggle-btn" onclick="bcToggleLeft()">⬡ FILTROS</button>
          <button id="bc-risk-btn" class="bc-toggle-btn" onclick="bcCycleRisk()">◎ SONAR</button>
          <button class="bc-toggle-btn" onclick="bcToggleRight()">⬢ DADOS</button>
          <span id="bc-clock" style="font-size:9px;color:var(--text2);margin-left:8px;font-family:monospace;"></span>
        </div>
      </div>
      <div class="bc-sidebar" id="bc-left">
        <div class="bc-sh">⬡ FILTRO MULTICULTURAL</div>
        <div class="bc-body">
          <div style="font-size:9px;color:var(--text2);margin-bottom:5px;letter-spacing:1px;">GRÃOS E FIBRAS</div>
          <button class="cult-btn" onclick="bcTrocarCultura('soja')">🟡 Soja</button>
          <button class="cult-btn" onclick="bcTrocarCultura('milho')">🟠 Milho</button>
          <button class="cult-btn" onclick="bcTrocarCultura('algodao')">⚪ Algodão</button>
          <div style="font-size:9px;color:var(--text2);margin:7px 0 4px;letter-spacing:1px;">HORTIFRUTI — iRed</div>
          <button class="cult-btn" onclick="bcTrocarCultura('tomate')">🔴 Tomate Mesa</button>
          <button class="cult-btn" onclick="bcTrocarCultura('tomate-ind')">🍅 Tomate Indústria</button>
          <button class="cult-btn" onclick="bcTrocarCultura('cebola')">🟤 Cebola</button>
          <button class="cult-btn" onclick="bcTrocarCultura('pimentao')">🟢 Pimentão</button>
          <div style="font-size:9px;color:var(--text2);margin:7px 0 4px;letter-spacing:1px;">FRUTICULTURA</div>
          <button class="cult-btn" onclick="bcTrocarCultura('manga')">🥭 Manga</button>
          <button class="cult-btn" onclick="bcTrocarCultura('uva')">🍇 Uva</button>
          <button class="cult-btn" onclick="bcTrocarCultura('laranja')">🍊 Laranja</button>
          <button class="cult-btn active" id="bc-cult-all" onclick="bcTrocarCultura('all')">◎ Todas</button>
          <div style="height:1px;background:var(--border);margin:8px 0;"></div>
          <div style="font-size:9px;color:var(--text2);margin-bottom:5px;letter-spacing:1px;">CAMADAS</div>
          <div class="layer-toggle"><input type="checkbox" id="bc-l1" checked onchange="bcToggleLayer('sonar-poi',this)"><label for="bc-l1">Sonar POI</label></div>
          <div class="layer-toggle"><input type="checkbox" id="bc-l2" checked onchange="bcToggleLayer('portos',this)"><label for="bc-l2">Portos</label></div>
          <div style="height:1px;background:var(--border);margin:8px 0;"></div>
          <button class="lyr-btn" style="width:100%;margin-bottom:3px;" onclick="bcSetRiskMode('radar')">📍 Sonar Radar</button>
          <button class="lyr-btn" style="width:100%;margin-bottom:3px;" onclick="bcSetRiskMode('impact')">🔴 Sonar Impacto</button>
          <button class="lyr-btn" style="width:100%;" onclick="bcSetRiskMode('off')">✕ Desligar Risco</button>
        </div>
      </div>
      <div id="bc-map"></div>
      <div class="bc-sidebar" id="bc-right">
        <div class="bc-sh" style="justify-content:space-between;">
          <span id="bc-right-title">⬢ BIÓPSIA GEOESPACIAL</span>
          <button class="bc-close" onclick="bcCloseRight()">✕</button>
        </div>
        <div class="bc-body" id="bc-right-body">
          <div style="color:var(--text2);font-size:10px;text-align:center;margin-top:28px;line-height:1.7;">Clique em um ponto<br>do sonar para ver<br>a análise detalhada.</div>
        </div>
      </div>
    </div>

    <!-- ═══ PANEL: LOGÍSTICA ═══ -->'''
if old10 in c:
    c = c.replace(old10, bc_html, 1); changes.append('FIX10 BIO-COMMAND HTML')
else:
    changes.append('SKIP10 logistica anchor not found')

# ── FIX 11: BIO-COMMAND JS (insert before _niasRequestUpgrade) ──────
old11 = 'function _niasRequestUpgrade() {'
bc_js = '''// ═══════════════════════════════════════════════════════════════════
// BIO-COMMAND — Mapa de Comando Integrado
// ═══════════════════════════════════════════════════════════════════
let bcMap, bcMapLayers = {}, _bcInit = false;
let _bcRiskCycle = -1;

function initBioCommand() {
  if (_bcInit) { setTimeout(() => bcMap && bcMap.invalidateSize(), 80); return; }
  _bcInit = true;
  bcMap = L.map('bc-map', { center:[-15,-52], zoom:4, zoomControl:true, attributionControl:false });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom:19, subdomains:'abcd' }).addTo(bcMap);
  const sonarPOI = L.layerGroup();
  (typeof MUNICIPAL_DB !== 'undefined' ? MUNICIPAL_DB : []).forEach(m => {
    if (!m.poly || m.poly.length < 3) return;
    const c = [(m.poly[0][0]+m.poly[2][0])/2, (m.poly[0][1]+m.poly[2][1])/2];
    const isAlert = m.ndvi < 0.52, isCrit = m.ndvi < 0.45;
    const state = isAlert ? 'alert' : (Math.random()<0.18 ? 'ai' : 'normal');
    const sev   = isCrit ? 'critical' : isAlert ? 'high' : 'ok';
    const sz    = isCrit ? 7 : isAlert ? 6 : 5;
    const tip   = `<div style="font-family:monospace;font-size:11px;"><b>${_esc(m.name)} — ${m.state||''}</b><br>${(m.culture||'').toUpperCase()} · NDVI ${(m.ndvi||0).toFixed(3)}<br>${isAlert?(isCrit?'🔴 CRÍTICO':'🟡 ATENÇÃO'):'🟢 SAFRA SAUDÁVEL'}</div>`;
    const mk = createSonarMarker(c, { state, severity:sev, size:sz, tooltip:tip });
    mk._bcMun = m;
    mk.on('click', () => bcOpenRight(m));
    sonarPOI.addLayer(mk);
  });
  bcMapLayers['sonar-poi'] = sonarPOI;
  sonarPOI.addTo(bcMap);
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
  setTimeout(() => bcMap.invalidateSize(), 80);
}

function bcToggleLeft() { document.getElementById('bc-left').classList.toggle('collapsed'); setTimeout(()=>bcMap&&bcMap.invalidateSize(),300); }
function bcToggleRight() { document.getElementById('bc-right').classList.toggle('open'); setTimeout(()=>bcMap&&bcMap.invalidateSize(),300); }
function bcCloseRight() { document.getElementById('bc-right').classList.remove('open'); setTimeout(()=>bcMap&&bcMap.invalidateSize(),300); }

function bcOpenRight(m) {
  const lat = m.poly?.length>=3 ? ((m.poly[0][0]+m.poly[2][0])/2).toFixed(2) : '—';
  const lon = m.poly?.length>=3 ? ((m.poly[0][1]+m.poly[2][1])/2).toFixed(2) : '—';
  const ndvi=m.ndvi??0;
  const cls = ndvi>=0.70?'good':ndvi>=0.50?'':ndvi>=0.30?'warn':'bad';
  const lbl = ndvi>=0.70?'🟢 Plena':ndvi>=0.50?'🟡 Normal':ndvi>=0.30?'🟠 Atenção':'🔴 Crítico';
  const rm  = m.area_ha?(m.area_ha*ndvi*0.82).toFixed(0)+' t':'—';
  const t=document.getElementById('bc-right-title'), b=document.getElementById('bc-right-body');
  if(t) t.textContent=`⬢ ${_esc(m.name)} — ${m.state||''}`;
  if(b) b.innerHTML=`
    <div class="bc-kv"><span class="k">Cultura</span><span class="v">${_esc(m.culture||'—')}</span></div>
    <div class="bc-kv"><span class="k">NDVI</span><span class="v ${cls}">${ndvi.toFixed(3)} · ${lbl}</span></div>
    <div class="bc-kv"><span class="k">Chuva 7d</span><span class="v">${m.chuva_7d??'—'} mm</span></div>
    <div class="bc-kv"><span class="k">Temp. máx.</span><span class="v">${m.temp_max??'—'}°C</span></div>
    <div class="bc-kv"><span class="k">Área aprox.</span><span class="v">${m.area_ha?m.area_ha.toLocaleString('pt-BR')+' ha':'—'}</span></div>
    <div class="bc-kv"><span class="k">R_m estimado</span><span class="v good">${rm}</span></div>
    <div class="bc-kv"><span class="k">Coords.</span><span class="v" style="font-size:9px;">${lat}°, ${lon}°</span></div>
    <div style="margin:8px 0 4px;font-size:9px;color:var(--accent);letter-spacing:1px;">◎ ARBITRAGEM CEASA</div>
    ${_bcArbSnippet(m)}
    <div style="margin-top:8px;font-size:9px;color:var(--text2);">Fenologia: ${_esc(m.phenology||'ciclo em andamento')}</div>`;
  document.getElementById('bc-right').classList.add('open');
  setTimeout(()=>bcMap&&bcMap.invalidateSize(),300);
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

function bcTrocarCultura(cult) {
  document.querySelectorAll('#bc-left .cult-btn').forEach(b=>{
    const match=cult==='all'?b.id==='bc-cult-all':b.textContent.toLowerCase().replace(/\\s+/g,'').includes(cult.replace('-',''));
    b.classList.toggle('active',match);
  });
  if(!bcMap||!bcMapLayers['sonar-poi'])return;
  bcMapLayers['sonar-poi'].eachLayer(mk=>{
    if(!mk._bcMun)return;
    const vis=cult==='all'||(mk._bcMun.culture||'').toLowerCase().includes(cult.replace('-',''));
    const el=mk.getElement?mk.getElement():null;
    if(el) el.style.opacity=vis?'1':'0.12';
  });
}

function bcCycleRisk() { const modes=['radar','impact','off']; _bcRiskCycle=(_bcRiskCycle+1)%modes.length; bcSetRiskMode(modes[_bcRiskCycle]); }

function bcSetRiskMode(mode) {
  const btn=document.getElementById('bc-risk-btn');
  if(btn) btn.textContent={'radar':'📍 SONAR RADAR','impact':'🔴 IMPACTO','off':'✕ RISCO OFF'}[mode]||'◎ SONAR';
  if(!bcMap||!bcMapLayers['sonar-poi'])return;
  mode==='off'?bcMap.removeLayer(bcMapLayers['sonar-poi']):bcMapLayers['sonar-poi'].addTo(bcMap);
}

function _niasRequestUpgrade() {'''
if old11 in c:
    c = c.replace(old11, bc_js, 1); changes.append('FIX11 BIO-COMMAND JS')
else:
    changes.append('SKIP11 _niasRequestUpgrade not found')

with open(src, 'w', encoding='utf-8') as f:
    f.write(c)

print(f'Done — {len(c.splitlines())} lines (was {orig_len} lines)')
for ch in changes:
    print(ch)
