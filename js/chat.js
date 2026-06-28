(function() {
  'use strict';

  const _esc = s => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const _fmt  = iso => { try { return new Date(iso).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}); } catch(e) { return iso || '—'; } };

  let _pulsoLoading = false;
  let _pulsoLastLoad = 0;

  window.loadPulso = function(force) {
    const now = Date.now();
    if (!force && _pulsoLoading) return;
    if (!force && (now - _pulsoLastLoad) < 45000) return; // debounce 45s
    _pulsoLoading = true;
    _pulsoLastLoad = now;

    // Carregar pulse + events + decisions em paralelo
    _loadAlertsStrip();
    Promise.all([
      fetch('/api/nias/brain/pulse', { cache: 'no-store' }).then(r => r.json()).catch(() => null),
      fetch('/api/nias/brain/events?limit=5', { cache: 'no-store' }).then(r => r.json()).catch(() => null),
      fetch('/api/nias/brain/decisions?limit=5', { cache: 'no-store' }).then(r => r.json()).catch(() => null),
    ]).then(([pulseResp, eventsResp, decisionsResp]) => {
      _renderPulsoHealth(pulseResp);
      _renderPulsoEvents(eventsResp);
      _renderPulsoDecisions(decisionsResp);
      // Timestamp no header
      const ts = _fmt(new Date().toISOString());
      const lup = document.getElementById('pulse-last-update'); if (lup) lup.textContent = ts;
      const nup = document.getElementById('pulse-next-update');
      if (nup) { const n = new Date(Date.now() + 30*60*1000); nup.textContent = _fmt(n.toISOString()); }
    }).catch(e => console.warn('[PULSO] load error:', e))
    .finally(() => { _pulsoLoading = false; });
  };

  function _renderPulsoHealth(resp) {
    if (!resp || resp.status === 'error') return;
    const d = resp.data || {};
    const health = d.health || '—';
    const hColors = { saudavel:'#30d158', ok:'#0a84ff', atencao:'#ffd60a', degradado:'#ef4444', desconhecido:'rgba(235,235,245,0.6)' };
    const hc = hColors[health] || 'rgba(235,235,245,0.6)';

    const hBadge = document.getElementById('pulse-health-badge');
    if (hBadge) { hBadge.textContent = health.toUpperCase(); hBadge.style.color = hc; hBadge.style.borderColor = hc; }

    const bh = document.getElementById('ph-brain-health');
    if (bh) { bh.textContent = health; bh.style.color = hc; }

    const cov = d.coverage || {};
    const cc = document.getElementById('ph-climate-coverage');
    if (cc) cc.textContent = (cov.weather_poles || 0) + ' polos';
    const pc = document.getElementById('ph-price-coverage');
    if (pc) pc.textContent = (cov.price_countries || 0) + ' países';
    const poles = document.getElementById('ph-poles-count');
    if (poles) poles.textContent = (cov.weather_poles || '—') + ' / 42';

    // Atualiza delta header com recomendações
    const recs = d.recommendations || [];
    const delta = document.getElementById('ph-delta');
    if (delta && recs.length) delta.textContent = 'REC: ' + recs[0].slice(0,40);
  }

  function _renderPulsoEvents(resp) {
    const list = document.getElementById('pulse-events-list');
    const cnt  = document.getElementById('pulse-events-count');
    if (!list) return;
    const events = (resp && resp.data && resp.data.events) ? resp.data.events : [];
    if (cnt) cnt.textContent = events.length + ' evento(s)';

    const alertBadge = document.getElementById('ph-alerts');
    if (alertBadge) alertBadge.textContent = events.length + ' ALERTAS VIVOS';

    // Topbar alert count
    const tsAlr = document.getElementById('ts-alr');
    if (tsAlr) {
      tsAlr.textContent = events.length || '0';
      tsAlr.style.color = events.length > 0 ? 'var(--danger)' : 'var(--accent2)';
    }

    // BR-163 from logState
    const tsBr = document.getElementById('ts-br163');
    if (tsBr && typeof logState !== 'undefined') {
      const sat = Math.round(logState.br163);
      tsBr.textContent = sat + '%';
      tsBr.style.color = sat >= 80 ? 'var(--danger)' : sat >= 68 ? 'var(--warn)' : 'var(--accent2)';
    }

    // Decision Banner
    _updateDecisionBanner(events);

    if (!events.length) {
      list.innerHTML = '<div style="padding:8px 10px;color:var(--text2);">Sem alertas ativos no momento.</div>';
      return;
    }
    const gravColors = { critica:'#ef4444', alta:'#f59e0b', warn:'#ffd60a', info:'rgba(235,235,245,0.6)' };
    list.innerHTML = events.slice(0,5).map(ev => {
      const c = gravColors[ev.gravidade] || 'rgba(235,235,245,0.6)';
      return `<div style="padding:4px 10px;border-left:2px solid ${c};margin:1px 0;cursor:pointer;" onclick="showPanel('brain')" title="${_esc(ev.descricao)}">
        <span style="color:${c};font-size:8px;font-weight:bold;">[${_esc(ev.gravidade||'').toUpperCase()}]</span>
        <span style="color:var(--text);margin-left:4px;font-size:9px;">${_esc(ev.titulo)}</span>
        <span style="float:right;color:var(--text2);font-size:8px;">${_esc(ev.pais||'SA')}</span>
      </div>`;
    }).join('');
  }

  function _updateDecisionBanner(events) {
    const banner  = document.getElementById('decision-banner');
    const dot     = document.getElementById('db-dot');
    const label   = document.getElementById('db-label');
    const msg     = document.getElementById('db-msg');
    const action  = document.getElementById('db-action');
    const wrDot   = document.getElementById('nav-wr-dot');
    if (!banner) return;

    const criticas = events.filter(e => e.gravidade === 'critica' || e.gravidade === 'alta');
    const warns    = events.filter(e => e.gravidade === 'warn');

    if (criticas.length > 0) {
      banner.className = 'estado-crit';
      dot.style.background = '#ef4444'; dot.style.boxShadow = '0 0 6px #ef4444';
      label.style.color = '#ef4444'; label.textContent = 'AÇÃO NECESSÁRIA';
      const top = criticas[0];
      msg.textContent = (top.titulo || top.descricao || 'Alerta crítico detectado') + (criticas.length > 1 ? ` (+${criticas.length - 1} outros)` : '');
      action.style.display = 'block'; action.style.color = '#ef4444'; action.style.borderColor = 'rgba(239,68,68,.4)';
      if (wrDot) wrDot.style.display = 'block';
    } else if (warns.length > 0 || events.length > 0) {
      banner.className = 'estado-warn';
      dot.style.background = 'var(--warn)'; dot.style.boxShadow = '0 0 6px var(--warn)';
      label.style.color = 'var(--warn)'; label.textContent = 'ATENÇÃO';
      msg.textContent = events.length + ' alerta(s) ativo(s) — revisar War Room';
      action.style.display = 'block'; action.style.color = 'var(--warn)'; action.style.borderColor = 'rgba(255,214,10,.4)';
      if (wrDot) wrDot.style.display = 'block';
    } else {
      banner.className = 'estado-ok';
      dot.style.background = 'var(--accent2)'; dot.style.boxShadow = '0 0 6px var(--accent2)';
      label.style.color = 'var(--accent2)'; label.textContent = 'SISTEMA ESTÁVEL';
      msg.textContent = 'Sem alertas críticos — nenhuma ação urgente necessária';
      action.style.display = 'none';
      if (wrDot) wrDot.style.display = 'none';
    }
  }

  function _renderPulsoDecisions(resp) {
    const list = document.getElementById('pulse-decisions-list');
    const cnt  = document.getElementById('pulse-cards-count');
    if (!list) return;
    const cards = (resp && resp.data && resp.data.decisions) ? resp.data.decisions : [];
    if (cnt) cnt.textContent = cards.length + ' card(s)';

    if (!cards.length) {
      list.innerHTML = '<div style="padding:8px 10px;color:var(--text2);">Sem oportunidades no momento. Aguardando dados de preço.</div>';
      return;
    }
    const typeColors = { comprar:'#30d158', antecipar_compra:'#22c55e', alerta:'#ef4444', monitorar:'#ffd60a', segurar:'rgba(235,235,245,0.6)' };
    list.innerHTML = cards.slice(0,5).map(c => {
      const tc = typeColors[c.tipo] || 'rgba(235,235,245,0.6)';
      const score = c.score || 0;
      const valid_until = c.valid_until || c.validade_ate || '';
      const generated_at = c.generated_at || c.gerado_em || '';
      const valLabel = valid_until ? `válido até ${valid_until}` : '';
      return `<div style="padding:4px 10px;border-left:2px solid ${tc};margin:1px 0;cursor:pointer;" onclick="showPanel('advisor')" title="${_esc(c.tese)}">
        <span style="color:${tc};font-size:8px;font-weight:bold;">[${_esc((c.tipo||'').toUpperCase())}]</span>
        <span style="color:var(--text);margin-left:4px;font-size:9px;">${_esc(c.titulo||c.produto||'—')}</span>
        <span style="float:right;color:var(--text2);font-size:8px;">${score}/100</span>
        ${valLabel ? `<div style="font-size:7px;color:var(--text2);margin-top:1px;">⏱ ${_esc(valLabel)}</div>` : ''}
      </div>`;
    }).join('');
  }

  // Auto-load quando o painel overview é o ativo inicial
  document.addEventListener('DOMContentLoaded', () => {
    const panel = document.getElementById('panel-overview');
    if (panel && panel.classList.contains('active')) {
      setTimeout(() => { try { loadPulso(true); } catch(e) {} }, 800);
    }
  });

})();
