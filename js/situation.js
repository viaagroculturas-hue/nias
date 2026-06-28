(function() {
  'use strict';

  // ── Estado interno ────────────────────────────────────────────────
  let _allRecs = [];
  let _currentFilter = 'todos';

  const RISK_COLOR  = { baixo: '#22c55e', medio: '#f59e0b', alto: '#ef4444', critico: '#7f1d1d' };
  const CONF_COLOR  = { alta: '#22c55e', media: '#f59e0b', baixa: '#9ca3af' };
  const TIPO_LABEL  = {
    alerta:            '⚠ ALERTA',
    monitorar:         '👁 MONITORAR',
    comprar:           '🟢 COMPRAR',
    vender:            '🔴 VENDER',
    segurar:           '⏸ SEGURAR',
    evitar:            '🚫 EVITAR',
    antecipar_compra:  '⏩ ANTECIPAR COMPRA',
    antecipar_venda:   '⏩ ANTECIPAR VENDA',
  };
  const CC_FLAG = {
    BR:'🇧🇷', AR:'🇦🇷', CL:'🇨🇱', PE:'🇵🇪',
    BO:'🇧🇴', PY:'🇵🇾', UY:'🇺🇾', CO:'🇨🇴', EC:'🇪🇨',
  };

  // ── Carregar dados ────────────────────────────────────────────────
  window.loadAdvisor = function(force) {
    const badge = document.getElementById('advisor-status-badge');
    if (badge) { badge.textContent = 'ATUALIZANDO'; badge.className = 'panel-badge'; }

    Promise.all([
      fetch('/api/nias/advisor/summary').then(r => r.json()).catch(() => null),
      fetch('/api/nias/advisor/recommendations').then(r => r.json()).catch(() => null),
    ]).then(([summaryResp, recsResp]) => {
      _renderSummary(summaryResp);
      _renderCards(recsResp);
      if (badge) {
        const total = recsResp && recsResp.data ? recsResp.data.total || 0 : 0;
        badge.textContent = total > 0 ? `${total} SINAIS` : 'SEM DADOS';
        badge.className = total > 0 ? 'panel-badge ok' : 'panel-badge';
      }
    }).catch(err => {
      console.error('[Advisor] Erro ao carregar:', err);
      if (badge) { badge.textContent = 'ERRO'; badge.className = 'panel-badge'; }
    });
  };

  // ── Resumo executivo ──────────────────────────────────────────────
  function _renderSummary(resp) {
    const el = document.getElementById('advisor-summary-text');
    const stats = document.getElementById('advisor-summary-stats');
    if (!el || !stats) return;

    const data = resp && resp.data ? resp.data : null;
    if (!data || !data.resumo) {
      el.textContent = 'Dados insuficientes para gerar análise. Execute o pipeline para coletar clima e preços.';
      stats.innerHTML = '';
      return;
    }

    el.textContent = data.resumo;

    const items = [
      { label: 'CONSELHOS',      val: data.total_conselhos  || 0, color: '#22c55e' },
      { label: 'OPORTUNIDADES',  val: data.oportunidades    || 0, color: '#3b82f6' },
      { label: 'RISCOS CLIM.',   val: data.riscos_climaticos|| 0, color: '#f59e0b' },
      { label: 'ALERTAS',        val: data.alertas          || 0, color: '#ef4444' },
    ];
    stats.innerHTML = items.map(i =>
      `<div style="text-align:center;">
        <div style="font-size:22px;font-weight:700;color:${i.color};">${i.val}</div>
        <div style="font-size:9px;color:#555;letter-spacing:1px;">${i.label}</div>
      </div>`
    ).join('');

    // Freshness
    const fw = data.freshness;
    if (fw) {
      const fText = `Clima: ${fw.weather_days_old <= 1 ? 'hoje' : fw.weather_days_old + 'd atrás'} • Preços: ${fw.prices_days_old >= 999 ? 'sem dado' : fw.prices_days_old + 'd atrás'}`;
      const fEl = document.createElement('div');
      fEl.style.cssText = 'font-size:10px;color:#555;margin-top:10px;padding-top:10px;border-top:1px solid #1e3a2e;';
      fEl.textContent = '⏱ ' + fText;
      const parent = el.parentElement;
      const existing = parent.querySelector('.advisor-freshness');
      if (existing) existing.remove();
      fEl.className = 'advisor-freshness';
      parent.appendChild(fEl);
    }
  }

  // ── Cards de recomendações ────────────────────────────────────────
  function _renderCards(resp) {
    const container = document.getElementById('advisor-cards');
    const empty     = document.getElementById('advisor-empty');
    if (!container) return;

    const recs = resp && resp.data && resp.data.recommendations ? resp.data.recommendations : [];
    _allRecs = recs;
    _applyFilter(_currentFilter);
  }

  function _applyFilter(filter) {
    _currentFilter = filter;
    const container = document.getElementById('advisor-cards');
    const empty     = document.getElementById('advisor-empty');
    if (!container) return;

    // Atualizar botões de filtro
    document.querySelectorAll('.advisor-filter').forEach(btn => {
      const isActive = btn.dataset.filter === filter;
      btn.style.borderColor  = isActive ? '#22c55e' : '#333';
      btn.style.color        = isActive ? '#22c55e' : '#888';
    });

    const filtered = filter === 'todos'
      ? _allRecs
      : _allRecs.filter(r => r.tipo === filter || r.pais === filter);

    if (filtered.length === 0) {
      container.innerHTML = '';
      if (empty) empty.style.display = 'block';
      return;
    }
    if (empty) empty.style.display = 'none';
    container.innerHTML = filtered.map(_buildCard).join('');
  }

  function _buildCard(rec, idx) {
    const rColor  = RISK_COLOR[rec.risco]  || '#888';
    const cColor  = CONF_COLOR[rec.confianca] || '#888';
    const tipoLbl = TIPO_LABEL[rec.tipo]   || rec.tipo || 'MONITORAR';
    const flag    = CC_FLAG[rec.pais]      || '🌎';
    const score   = rec.score || 0;
    const scoreColor = score >= 75 ? '#22c55e' : score >= 55 ? '#f59e0b' : '#9ca3af';

    const justif = escapeHtml(rec.explicacao_completa || rec.justificativa || rec.tese || '');
    const titulo  = escapeHtml(rec.titulo || '');
    const regiao  = escapeHtml(rec.regiao || '');
    const produto = escapeHtml(rec.produto || '');
    const fontes  = (rec.fontes || []).map(f => escapeHtml(f)).join(', ');

    return `<div style="background:#111;border:1px solid #1e1e1e;border-radius:8px;padding:16px;
              display:flex;flex-direction:column;gap:10px;border-top:3px solid ${rColor};
              transition:border-color .2s;"
            onmouseover="this.style.borderColor='${rColor}';this.style.boxShadow='0 0 0 1px ${rColor}33'"
            onmouseout="this.style.borderColor='';this.style.boxShadow=''">

      <!-- Header do card -->
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
        <div style="font-size:10px;color:#22c55e;letter-spacing:1px;">${tipoLbl}</div>
        <div style="display:flex;gap:6px;align-items:center;flex-shrink:0;">
          <span style="font-size:9px;color:${scoreColor};background:${scoreColor}22;
                padding:2px 7px;border-radius:10px;font-weight:700;">${score}/100</span>
          <span style="font-size:13px;">${flag}</span>
        </div>
      </div>

      <!-- Título -->
      <div style="font-size:13px;color:#e5e7eb;font-weight:600;line-height:1.4;">${titulo}</div>

      <!-- Localização -->
      <div style="font-size:11px;color:#555;display:flex;gap:8px;flex-wrap:wrap;">
        <span>📍 ${regiao}</span>
        ${produto && produto !== 'produtos agrícolas da região' ? `<span>🌿 ${produto}</span>` : ''}
        <span>⏱ ${escapeHtml(rec.horizonte || '')}</span>
      </div>

      <!-- Sinais climáticos -->
      ${(rec.sinais_climaticos && rec.sinais_climaticos.length > 0) ? `
      <div style="display:flex;gap:6px;flex-wrap:wrap;">
        ${rec.sinais_climaticos.map(s => `
          <span style="font-size:9px;background:#1a1a1a;border:1px solid #333;
                color:#f59e0b;padding:2px 8px;border-radius:10px;">${escapeHtml(s)}</span>
        `).join('')}
      </div>` : ''}

      <!-- Justificativa curta -->
      <div style="font-size:12px;color:#9ca3af;line-height:1.5;display:-webkit-box;
            -webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">${justif}</div>

      <!-- Risco × Confiança -->
      <div style="display:flex;gap:12px;align-items:center;">
        <span style="font-size:9px;color:${rColor};letter-spacing:1px;">
          ⬟ RISCO ${(rec.risco||'').toUpperCase()}</span>
        <span style="font-size:9px;color:${cColor};letter-spacing:1px;">
          ● CONF. ${(rec.confianca||'').toUpperCase()}</span>
      </div>

      <!-- Fonte -->
      <div style="font-size:9px;color:#444;">Fonte: ${fontes}</div>

      <!-- Botão tese -->
      <button onclick='openAdvisorThesis(${JSON.stringify(rec).replace(/'/g,"&#39;")})'
        style="background:none;border:1px solid #22c55e22;color:#22c55e;padding:6px;
               border-radius:4px;cursor:pointer;font-size:10px;letter-spacing:1px;
               margin-top:auto;transition:background .2s;"
        onmouseover="this.style.background='#22c55e22'"
        onmouseout="this.style.background='none'">
        VER TESE COMPLETA →
      </button>
    </div>`;
  }

  // ── Modal: Tese Detalhada ─────────────────────────────────────────
  window.openAdvisorThesis = function(rec) {
    const modal = document.getElementById('advisor-thesis-modal');
    const title = document.getElementById('thesis-modal-title');
    const body  = document.getElementById('thesis-modal-body');
    if (!modal || !title || !body) return;

    const rColor  = RISK_COLOR[rec.risco]  || '#888';
    const cColor  = CONF_COLOR[rec.confianca] || '#888';
    const flag    = CC_FLAG[rec.pais] || '🌎';
    const fontes  = (rec.fontes || []).join(', ');

    title.textContent = rec.titulo || '';

    body.innerHTML = `
      <!-- Localização -->
      <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;">
        <span style="font-size:11px;color:#666;">${flag} ${escapeHtml(rec.pais_nome||rec.pais||'')} — ${escapeHtml(rec.regiao||'')}</span>
        <span style="font-size:11px;color:#666;">⏱ ${escapeHtml(rec.horizonte||'')}</span>
      </div>

      <!-- Tese principal -->
      <div style="margin-bottom:16px;">
        <div style="font-size:9px;color:#22c55e;letter-spacing:1.5px;margin-bottom:6px;">TESE</div>
        <div style="color:#e5e7eb;font-size:13px;line-height:1.7;">${escapeHtml(rec.explicacao_completa || rec.tese || rec.justificativa || '')}</div>
      </div>

      <!-- Sinais climáticos -->
      ${(rec.sinais_climaticos && rec.sinais_climaticos.length > 0) ? `
      <div style="margin-bottom:16px;">
        <div style="font-size:9px;color:#f59e0b;letter-spacing:1.5px;margin-bottom:6px;">SINAIS CLIMÁTICOS</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          ${rec.sinais_climaticos.map(s => `<span style="background:#1a1a1a;border:1px solid #f59e0b44;color:#f59e0b;padding:3px 10px;border-radius:12px;font-size:11px;">${escapeHtml(s)}</span>`).join('')}
        </div>
        ${rec.temp_max_c !== undefined ? `<div style="margin-top:8px;font-size:11px;color:#666;">Temp. máx: ${rec.temp_max_c}°C • Temp. mín: ${rec.temp_min_c}°C • Precip: ${rec.precip_mm}mm</div>` : ''}
      </div>` : ''}

      <!-- Ação recomendada -->
      <div style="background:#0d1f15;border:1px solid #1e3a2e;border-radius:6px;padding:14px;margin-bottom:16px;">
        <div style="font-size:9px;color:#22c55e;letter-spacing:1.5px;margin-bottom:6px;">AÇÃO RECOMENDADA</div>
        <div style="color:#d1fae5;font-size:13px;line-height:1.6;">${escapeHtml(rec.acao_recomendada||'')}</div>
      </div>

      <!-- Cenário contrário -->
      <div style="background:#1a1209;border:1px solid #3d2e0a;border-radius:6px;padding:14px;margin-bottom:16px;">
        <div style="font-size:9px;color:#f59e0b;letter-spacing:1.5px;margin-bottom:6px;">⚠ CENÁRIO CONTRÁRIO</div>
        <div style="color:#fef3c7;font-size:13px;line-height:1.6;">${escapeHtml(rec.cenario_contrario||'')}</div>
      </div>

      <!-- Score + Risco + Confiança -->
      <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px;">
        <div style="background:#1a1a1a;border-radius:6px;padding:10px 16px;text-align:center;">
          <div style="font-size:22px;font-weight:700;color:${rColor};">${rec.score||0}</div>
          <div style="font-size:9px;color:#555;letter-spacing:1px;">NIAS SCORE</div>
        </div>
        <div style="background:#1a1a1a;border-radius:6px;padding:10px 16px;text-align:center;">
          <div style="font-size:14px;font-weight:700;color:${rColor};">${(rec.risco||'').toUpperCase()}</div>
          <div style="font-size:9px;color:#555;letter-spacing:1px;">RISCO</div>
        </div>
        <div style="background:#1a1a1a;border-radius:6px;padding:10px 16px;text-align:center;">
          <div style="font-size:14px;font-weight:700;color:${cColor};">${(rec.confianca||'').toUpperCase()}</div>
          <div style="font-size:9px;color:#555;letter-spacing:1px;">CONFIANÇA</div>
        </div>
        <div style="background:#1a1a1a;border-radius:6px;padding:10px 16px;text-align:center;">
          <div style="font-size:12px;font-weight:700;color:#9ca3af;">${(rec.classificacao||'').replace(/_/g,' ')}</div>
          <div style="font-size:9px;color:#555;letter-spacing:1px;">CLASSIFICAÇÃO</div>
        </div>
      </div>

      <!-- Dados usados -->
      <div style="margin-bottom:12px;">
        <div style="font-size:9px;color:#555;letter-spacing:1.5px;margin-bottom:6px;">DADOS UTILIZADOS</div>
        <div style="font-size:11px;color:#666;">${(rec.dados_usados||[]).map(d => escapeHtml(d)).join(' • ')}</div>
      </div>

      <!-- Fontes -->
      <div style="border-top:1px solid #1e1e1e;padding-top:12px;">
        <div style="font-size:9px;color:#444;">Fontes: ${escapeHtml(fontes)} • Atualizado: ${escapeHtml(rec.atualizado_em||'')}</div>
      </div>
    `;

    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
  };

  window.closeAdvisorThesis = function() {
    const modal = document.getElementById('advisor-thesis-modal');
    if (modal) modal.style.display = 'none';
    document.body.style.overflow = '';
  };

  // ── Simulador ─────────────────────────────────────────────────────
  window.showAdvisorSimulator = function() {
    const modal = document.getElementById('advisor-simulator-modal');
    if (modal) { modal.style.display = 'block'; document.body.style.overflow = 'hidden'; }
  };

  window.closeAdvisorSimulator = function() {
    const modal = document.getElementById('advisor-simulator-modal');
    if (modal) { modal.style.display = 'none'; document.body.style.overflow = ''; }
    const res = document.getElementById('sim-result');
    if (res) { res.style.display = 'none'; res.innerHTML = ''; }
  };

  window.runAdvisorSimulation = function() {
    const product = (document.getElementById('sim-product') || {}).value || '';
    const region  = (document.getElementById('sim-region')  || {}).value || '';
    const res     = document.getElementById('sim-result');
    if (!res) return;

    if (!product && !region) {
      res.innerHTML = '<div style="color:#f59e0b;font-size:12px;">Informe produto e/ou região para simular.</div>';
      res.style.display = 'block';
      return;
    }

    res.innerHTML = '<div style="color:#555;font-size:12px;">Analisando…</div>';
    res.style.display = 'block';

    const url = `/api/nias/advisor/thesis?product=${encodeURIComponent(product)}&region=${encodeURIComponent(region)}`;
    fetch(url).then(r => r.json()).then(resp => {
      const data = resp.data || {};
      if (data.status === 'insuficiente') {
        res.innerHTML = `
          <div style="background:#1a1209;border:1px solid #3d2e0a;border-radius:6px;padding:14px;">
            <div style="font-size:9px;color:#f59e0b;letter-spacing:1px;margin-bottom:6px;">DADOS INSUFICIENTES</div>
            <div style="color:#fef3c7;font-size:12px;line-height:1.5;">${escapeHtml(data.mensagem||'')}</div>
          </div>`;
      } else {
        const score = data.score || {};
        const rColor = RISK_COLOR[score.risco] || '#888';
        res.innerHTML = `
          <div style="background:#0d1f15;border:1px solid #1e3a2e;border-radius:6px;padding:14px;">
            <div style="font-size:9px;color:#22c55e;letter-spacing:1px;margin-bottom:8px;">ANÁLISE — ${escapeHtml(product.toUpperCase())} / ${escapeHtml(region.toUpperCase())}</div>
            <div style="color:#d1fae5;font-size:12px;line-height:1.6;margin-bottom:10px;">${escapeHtml(data.tese||'')}</div>
            <div style="background:#1a1a1a;border-radius:4px;padding:10px;margin-bottom:10px;">
              <div style="font-size:9px;color:#f59e0b;letter-spacing:1px;margin-bottom:4px;">⚠ CENÁRIO CONTRÁRIO</div>
              <div style="color:#fef3c7;font-size:11px;line-height:1.5;">${escapeHtml(data.cenario_contrario||'')}</div>
            </div>
            <div style="display:flex;gap:10px;">
              <span style="font-size:9px;color:${rColor};">RISCO: ${(score.risco||'').toUpperCase()}</span>
              <span style="font-size:9px;color:${CONF_COLOR[score.confianca]||'#888'};">CONFIANÇA: ${(score.confianca||'').toUpperCase()}</span>
              <span style="font-size:9px;color:${rColor};">SCORE: ${score.score||0}/100</span>
            </div>
          </div>`;
      }
    }).catch(() => {
      res.innerHTML = '<div style="color:#ef4444;font-size:12px;">Erro ao conectar com o Conselheiro NIAS.</div>';
    });
  };

  // ── Filtro ────────────────────────────────────────────────────────
  window.advisorFilter = function(filter) {
    _applyFilter(filter);
  };

  // ── Fechar modais com ESC ─────────────────────────────────────────
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      closeAdvisorThesis();
      closeAdvisorSimulator();
    }
  });

  // ── Hook no showPanel ─────────────────────────────────────────────
  const _origShow = window.showPanel;
  window.showPanel = function(id) {
    _origShow && _origShow(id);
    if (id === 'advisor' && !window._advisorInit) {
      window._advisorInit = true;
      loadAdvisor(false);
    }
  };

})();
