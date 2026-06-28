(function(){
  const fmtBRL = (v) => {
    const n = Number(v || 0);
    if (!Number.isFinite(n)) return 'n/d';
    return n.toLocaleString('pt-BR', {style:'currency', currency:'BRL', maximumFractionDigits:0});
  };
  const esc = (s) => String(s ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const colorRisk = (level) => ({'alto':'#ff453a','médio-alto':'#ff9f1c','médio':'#ffd166','baixo':'#50c878'}[String(level||'').toLowerCase()] || '#888');
  const join = (arr, sep=', ') => Array.isArray(arr) && arr.length ? arr.map(esc).join(sep) : 'n/d';

  window.SituationRoom = {
    data: null,
    activeUf: '',
    timer: null,
    async init(){
      this.renderShell();
      await this.load();
      if (this.timer) clearInterval(this.timer);
      this.timer = setInterval(() => this.load(false), 5 * 60 * 1000);
    },
    async load(showLoading=true){
      const status = document.getElementById('sit-real-status');
      if (status && showLoading) status.textContent = 'coletando/validando...';
      try {
        const qs = this.activeUf ? '?uf=' + encodeURIComponent(this.activeUf) : '';
        const r = await fetch('/api/situation/real' + qs, {cache:'no-store'});
        if (!r.ok) throw new Error('HTTP ' + r.status);
        this.data = await r.json();
        this.renderData();
      } catch (e) {
        if (status) status.textContent = 'API indisponível: exibindo aviso sem dados fabricados';
        const root = document.getElementById('sit-real-content');
        if (root) root.innerHTML = `<div style="padding:18px;border:1px solid #ff453a;background:rgba(255,69,58,.08);color:#fff;border-radius:12px;">Falha ao carregar /api/situation/real. Erro: ${esc(e.message)}. O painel não substitui por dados falsos.</div>`;
      }
    },
    renderShell(){
      const panel = document.getElementById('panel-situation');
      if (!panel) return;
      panel.style.cssText = 'background:radial-gradient(circle at 20% 0%,rgba(255,159,10,.16),transparent 28%),linear-gradient(135deg,#050505 0%,#090d12 60%,#050505 100%);overflow:hidden;display:flex;flex-direction:column;';
      panel.innerHTML = `
        <div style="height:54px;background:rgba(8,10,12,.92);border-bottom:1px solid rgba(255,159,10,.32);display:flex;align-items:center;padding:0 18px;gap:14px;box-shadow:0 0 28px rgba(255,159,10,.12);">
          <div style="width:10px;height:10px;border-radius:50%;background:#50c878;box-shadow:0 0 16px #50c878;"></div>
          <div>
            <div style="color:#ff9f0a;font-size:14px;font-weight:900;letter-spacing:3px;font-family:'Courier New',monospace;">SITUATION REAL</div>
            <div style="font-size:9px;color:#8a8f98;letter-spacing:1px;">RJ = RECUPERAÇÃO JUDICIAL • IMPACTO REGIONAL/NACIONAL • FONTES RASTREÁVEIS</div>
          </div>
          <div style="margin-left:auto;display:flex;gap:8px;align-items:center;">
            <button onclick="SituationRoom.setUf('')" id="sit-uf-all" style="background:#ff9f0a;color:#000;border:0;border-radius:999px;padding:6px 10px;font-size:10px;font-weight:800;cursor:pointer;">BRASIL</button>
            <button onclick="SituationRoom.setUf('RJ')" id="sit-uf-rj" style="background:#12161d;color:#ddd;border:1px solid #2a3442;border-radius:999px;padding:6px 10px;font-size:10px;cursor:pointer;">RJ</button>
            <button onclick="SituationRoom.setUf('SP')" id="sit-uf-sp" style="background:#12161d;color:#ddd;border:1px solid #2a3442;border-radius:999px;padding:6px 10px;font-size:10px;cursor:pointer;">SP</button>
            <button onclick="SituationRoom.load()" style="background:#111;color:#ff9f0a;border:1px solid #ff9f0a;border-radius:999px;padding:6px 10px;font-size:10px;cursor:pointer;">ATUALIZAR</button>
            <span id="sit-real-status" style="font-size:10px;color:#8a8f98;font-family:monospace;">--</span>
          </div>
        </div>
        <div id="sit-real-content" style="flex:1;overflow:auto;padding:16px;"></div>`;
    },
    setUf(uf){
      this.activeUf = uf || '';
      ['all','rj','sp'].forEach(x => {
        const b = document.getElementById('sit-uf-' + x);
        if (!b) return;
        const active = (x === 'all' && !this.activeUf) || x.toUpperCase() === this.activeUf;
        b.style.background = active ? '#ff9f0a' : '#12161d';
        b.style.color = active ? '#000' : '#ddd';
      });
      this.load();
    },
    renderData(){
      const root = document.getElementById('sit-real-content');
      const status = document.getElementById('sit-real-status');
      if (!root || !this.data) return;
      const d = this.data;
      const s = d.summary || {};
      if (status) status.textContent = 'UTC ' + new Date(d.generated_at).toLocaleString('pt-BR');
      const cards = [
        ['Casos RJ monitorados', s.rj_cases || 0, 'base interna + validação CNJ'],
        ['Dívida exposta', fmtBRL(s.total_debts_brl), 'risco financeiro na cadeia'],
        ['Receita exposta', fmtBRL(s.total_revenue_brl), 'capacidade econômica afetada'],
        ['Empregos expostos', Number(s.jobs_exposed||0).toLocaleString('pt-BR'), 'mão-de-obra e renda local']
      ].map(c => `<div style="background:linear-gradient(180deg,rgba(255,159,10,.10),rgba(15,18,24,.9));border:1px solid rgba(255,159,10,.28);border-radius:16px;padding:14px;box-shadow:0 0 24px rgba(255,159,10,.08);"><div style="font-size:10px;color:#98a2b3;text-transform:uppercase;letter-spacing:1px;">${esc(c[0])}</div><div style="font-size:24px;color:#fff;font-weight:900;margin-top:4px;font-family:monospace;">${esc(c[1])}</div><div style="font-size:10px;color:#ffb38a;margin-top:4px;">${esc(c[2])}</div></div>`).join('');
      const sectors = (s.top_sectors || []).map(x => `<div style="display:flex;justify-content:space-between;border-bottom:1px solid #1b2430;padding:6px 0;"><span>${esc(x.sector)}</span><b style="color:#ff9f0a;">${esc(x.cases)}</b></div>`).join('') || '<div style="color:#777;">Sem setores calculados.</div>';
      const ufRows = (s.by_uf || []).map(x => `<div style="display:flex;justify-content:space-between;border-bottom:1px solid #1b2430;padding:6px 0;"><span>${esc(x.region)} (${esc(x.uf)})</span><b style="color:#50c878;">${esc(x.cases)}</b></div>`).join('') || '<div style="color:#777;">Sem UF.</div>';
      const cases = (d.cases || []).map(c => this.caseCard(c)).join('') || '<div style="color:#777;padding:12px;">Nenhum caso encontrado para o filtro.</div>';
      const sources = (d.sources || []).map(src => `<div style="background:#0d1117;border:1px solid #202a36;border-radius:10px;padding:10px;margin-bottom:8px;"><div style="color:#fff;font-size:11px;font-weight:800;">${esc(src.name)}</div><div style="color:#9aa4b2;font-size:10px;margin-top:3px;">${esc(src.scope)}</div><div style="color:#ffb38a;font-size:10px;margin-top:3px;">Status: ${esc(src.live_status)}</div><a href="${esc(src.url)}" target="_blank" rel="noopener" style="color:#50c878;font-size:10px;">abrir fonte</a></div>`).join('');
      root.innerHTML = `
        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:14px;">${cards}</div>
        <div style="display:grid;grid-template-columns:1.25fr .75fr;gap:14px;align-items:start;">
          <div style="background:rgba(9,13,18,.72);border:1px solid #1c2633;border-radius:18px;padding:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
              <div><div style="color:#ff9f0a;font-size:12px;font-weight:900;letter-spacing:2px;">CASOS DE RJ E IMPACTO OPERACIONAL</div><div style="font-size:10px;color:#8a8f98;">Cada card mostra onde afeta, quais setores e por que importa para Brasil/região.</div></div>
              <div style="font-size:10px;color:#50c878;border:1px solid #315f45;border-radius:999px;padding:5px 9px;">sem dado inventado</div>
            </div>
            <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;">${cases}</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:12px;">
            <div style="background:rgba(9,13,18,.72);border:1px solid #1c2633;border-radius:18px;padding:14px;"><div style="color:#ff9f0a;font-size:12px;font-weight:900;margin-bottom:8px;">SETORES MAIS AFETADOS</div>${sectors}</div>
            <div style="background:rgba(9,13,18,.72);border:1px solid #1c2633;border-radius:18px;padding:14px;"><div style="color:#ff9f0a;font-size:12px;font-weight:900;margin-bottom:8px;">IMPACTO POR REGIÃO</div>${ufRows}</div>
            <div style="background:rgba(9,13,18,.72);border:1px solid #1c2633;border-radius:18px;padding:14px;"><div style="color:#ff9f0a;font-size:12px;font-weight:900;margin-bottom:8px;">FONTES SEGURAS</div>${sources}</div>
          </div>
        </div>
        <div style="margin-top:12px;color:#8a8f98;font-size:10px;line-height:1.5;">${esc(d.definition?.truth_policy || '')} Limitações: ${(d.limitations||[]).map(esc).join(' • ')}</div>`;
    },
    caseCard(c){
      const riskColor = colorRisk(c.impact_level);
      const reasons = (c.impact_reasons || []).map(r => `<li>${esc(r)}</li>`).join('');
      return `<div style="background:linear-gradient(135deg,#0d1117,#111820);border:1px solid #233044;border-left:4px solid ${riskColor};border-radius:14px;padding:12px;min-height:230px;">
        <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start;">
          <div style="color:#fff;font-size:12px;font-weight:900;line-height:1.25;">${esc(c.company_name)}</div>
          <div style="color:#000;background:${riskColor};border-radius:999px;padding:3px 7px;font-size:9px;font-weight:900;text-transform:uppercase;white-space:nowrap;">${esc(c.impact_level)}</div>
        </div>
        <div style="color:#98a2b3;font-size:10px;margin-top:5px;">${esc(c.city)}-${esc(c.state_uf)} • ${esc(c.judicial_status)} • ${esc(c.process_number)}</div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:10px 0;">
          <div style="background:#090d12;border:1px solid #1b2430;border-radius:8px;padding:7px;"><div style="font-size:8px;color:#777;">RISCO</div><div style="color:#fff;font-family:monospace;font-size:15px;">${esc(c.risk_score)}/100</div></div>
          <div style="background:#090d12;border:1px solid #1b2430;border-radius:8px;padding:7px;"><div style="font-size:8px;color:#777;">DÍVIDA</div><div style="color:#fff;font-family:monospace;font-size:12px;">${fmtBRL(c.debts_total)}</div></div>
          <div style="background:#090d12;border:1px solid #1b2430;border-radius:8px;padding:7px;"><div style="font-size:8px;color:#777;">EMPREGOS</div><div style="color:#fff;font-family:monospace;font-size:12px;">${Number(c.employees||0).toLocaleString('pt-BR')}</div></div>
        </div>
        <div style="font-size:10px;color:#ffb38a;margin-bottom:4px;">Produtos: ${join(c.products)}</div>
        <div style="font-size:10px;color:#b9c3d0;margin-bottom:4px;">Setores: ${join(c.affected_sectors)}</div>
        <div style="font-size:10px;color:#b9c3d0;margin-bottom:4px;">Canais regionais: ${join(c.regional_channels)}</div>
        <div style="font-size:10px;color:#98a2b3;margin:6px 0;"><b style="color:#fff;">Impacto no Brasil:</b> ${esc(c.brazil_impact)}</div>
        <ul style="margin:6px 0 0 16px;padding:0;color:#98a2b3;font-size:10px;line-height:1.45;">${reasons}</ul>
        <div style="margin-top:8px;font-size:9px;color:#6f7a88;border-top:1px solid #1b2430;padding-top:6px;">Fonte/validação: ${esc(c.validation_source)} • ${esc(c.data_confidence)}</div>
      </div>`;
    }
  };
})();
