(function() {
  'use strict';

  var _brainData = { pulse: null, events: [], cards: [], radar: null };
  var _brainActiveFilter = 'all';
  var _brainActiveHorizon = 'agora';
  var _brainLoading = false;

  var GRAVITY_COLOR = {
    critica: '#ef4444',
    alta:    '#f97316',
    warn:    '#eab308',
    info:    '#22c55e',
  };
  var TIPO_COLOR = {
    alerta:           '#ef4444',
    comprar:          '#22c55e',
    antecipar_compra: '#22c55e',
    vender:           '#3b82f6',
    monitorar:        '#6b7280',
  };

  window.initBrainPanel = function() {
    window._brainInit = true;
  };

  window.loadBrain = function(force) {
    if (_brainLoading && !force) return;
    _brainLoading = true;

    Promise.all([
      fetch('/api/nias/brain/pulse').then(r => r.json()).catch(() => null),
      fetch('/api/nias/brain/events').then(r => r.json()).catch(() => null),
      fetch('/api/nias/brain/decisions').then(r => r.json()).catch(() => null),
      fetch('/api/nias/brain/radar').then(r => r.json()).catch(() => null),
    ]).then(function(results) {
      _brainLoading = false;
      var pulse   = results[0] && results[0].data;
      var evData  = results[1] && results[1].data;
      var decData = results[2] && results[2].data;
      var radData = results[3] && results[3].data;

      _brainData.pulse  = pulse;
      _brainData.events = (evData  && evData.events)    || [];
      _brainData.cards  = (decData && decData.decisions) || [];
      _brainData.radar  = radData || null;

      _renderPulse(pulse);
      _renderEvents(_brainData.events);
      _renderCards(_brainData.cards, _brainActiveFilter);
      if (_brainData.radar) showRadarHorizon(_brainActiveHorizon);

      var ts = document.getElementById('brain-ts');
      if (ts) ts.textContent = new Date().toLocaleTimeString('pt-BR');
    }).catch(function(e) {
      _brainLoading = false;
      console.error('[Brain] load error:', e);
    });
  };

  function _renderPulse(pulse) {
    if (!pulse) return;

    // Health badge
    var badge = document.getElementById('brain-health-badge');
    if (badge) {
      var h = pulse.health || 'desconhecido';
      var hColors = { saudavel:'#22c55e', ok:'#22c55e', atencao:'#eab308', degradado:'#ef4444', desconhecido:'#6b7280' };
      badge.textContent = h.toUpperCase();
      badge.style.color = hColors[h] || '#a78bfa';
      badge.style.borderColor = hColors[h] || '#a78bfa';
    }

    // Sources
    var srcsEl = document.getElementById('brain-pulse-sources');
    if (!srcsEl || !pulse.sources) return;
    var srcs = pulse.sources;
    var statusIcon = { ok:'●', warn:'◐', stale:'○', missing:'✕' };
    var statusColor = { ok:'#22c55e', warn:'#eab308', stale:'#f97316', missing:'#ef4444' };

    srcsEl.innerHTML = Object.values(srcs).map(function(s) {
      var ic = statusIcon[s.status] || '○';
      var cl = statusColor[s.status] || '#6b7280';
      return '<div style="display:flex;justify-content:space-between;align-items:center;font-size:10px;">' +
        '<span style="color:var(--text2);">' + escapeHtml(s.label || '') + '</span>' +
        '<span style="color:' + cl + ';white-space:nowrap;margin-left:6px;">' + ic + ' ' + escapeHtml(s.freshness || s.status || '') + '</span>' +
      '</div>';
    }).join('');

    // Coverage
    var covEl = document.getElementById('brain-coverage');
    if (!covEl || !pulse.coverage) return;
    var cov  = pulse.coverage;
    var recs = pulse.recommendations || {};
    covEl.innerHTML =
      '<div style="display:flex;justify-content:space-between;font-size:10px;"><span style="color:var(--text2);">Polos climáticos</span><span style="color:#a78bfa;">' + (cov.weather_poles || 0) + '</span></div>' +
      '<div style="display:flex;justify-content:space-between;font-size:10px;"><span style="color:var(--text2);">Países com clima</span><span style="color:#a78bfa;">' + (cov.weather_countries || 0) + '/9</span></div>' +
      '<div style="display:flex;justify-content:space-between;font-size:10px;"><span style="color:var(--text2);">Países com preço</span><span style="color:#a78bfa;">' + (cov.price_countries || 0) + '/9</span></div>' +
      '<div style="display:flex;justify-content:space-between;font-size:10px;margin-top:4px;border-top:1px solid #2d1f6e;padding-top:4px;">' +
        '<span style="color:#ef4444;">Alertas</span><span style="color:#ef4444;">' + (recs.alertas || 0) + '</span></div>' +
      '<div style="display:flex;justify-content:space-between;font-size:10px;">' +
        '<span style="color:#22c55e;">Comprar</span><span style="color:#22c55e;">' + (recs.comprar || 0) + '</span></div>' +
      '<div style="display:flex;justify-content:space-between;font-size:10px;">' +
        '<span style="color:var(--text2);">Monitorar</span><span style="color:var(--text2);">' + (recs.monitorar || 0) + '</span></div>';
  }

  function _renderEvents(events) {
    var el = document.getElementById('brain-events-list');
    if (!el) return;
    if (!events || !events.length) {
      el.innerHTML = '<div style="color:var(--text2);font-size:10px;">Sem eventos detectados no momento.</div>';
      return;
    }
    el.innerHTML = events.map(function(ev) {
      var gc  = GRAVITY_COLOR[ev.gravidade] || '#6b7280';
      var ts  = (ev.timestamp || '').substring(0,16).replace('T',' ');
      var reg = ev.regiao ? ' · ' + escapeHtml(ev.regiao) : '';
      return '<div style="background:#0d0d1a;border:1px solid #1e1a3a;border-left:3px solid ' + gc + ';border-radius:5px;padding:7px 10px;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;">' +
          '<span style="font-size:10px;font-weight:600;color:' + gc + ';">' + escapeHtml(ev.titulo || '') + '</span>' +
          '<span style="font-size:9px;color:var(--text2);">' + escapeHtml(ev.pais_nome || ev.pais || '') + escapeHtml(reg) + '</span>' +
        '</div>' +
        '<div style="font-size:9px;color:var(--text2);margin-top:3px;line-height:1.4;">' + escapeHtml(ev.descricao || '') + '</div>' +
        (ev.acao ? '<div style="font-size:9px;color:#a78bfa;margin-top:3px;">→ ' + escapeHtml(ev.acao) + '</div>' : '') +
        '<div style="font-size:8px;color:#3d3460;margin-top:3px;">' + escapeHtml(ts) + ' · ' + escapeHtml(ev.fonte || '') + '</div>' +
      '</div>';
    }).join('');
  }

  function _renderCards(cards, filter) {
    var el    = document.getElementById('brain-cards-grid');
    var count = document.getElementById('brain-cards-count');
    if (!el) return;

    var filtered = cards.filter(function(c) {
      if (filter === 'all' || !filter) return true;
      if (filter === 'comprar') return c.tipo === 'comprar' || c.tipo === 'antecipar_compra';
      return c.tipo === filter;
    });

    if (count) count.textContent = filtered.length + ' cartão(ões)';

    if (!filtered.length) {
      el.innerHTML = '<div style="color:var(--text2);font-size:10px;padding:10px;">Nenhum cartão para o filtro selecionado.</div>';
      return;
    }

    el.innerHTML = filtered.map(function(c) {
      var tc  = TIPO_COLOR[c.tipo] || '#6b7280';
      var inv = (c.invalida_se || []).slice(0,2);
      var ds  = (c.dados_usados || []).slice(0,2);
      var hasPrice = c.has_price;

      return '<div style="background:#0d0d1a;border:1px solid #1e1a3a;border-top:2px solid ' + tc + ';border-radius:6px;padding:10px;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">' +
          '<span style="font-size:9px;font-weight:700;color:' + tc + ';letter-spacing:1px;">' + (c.tipo || '').toUpperCase() + '</span>' +
          '<span style="font-size:9px;color:#a78bfa;background:#1a0a3a;padding:1px 5px;border-radius:3px;">' + escapeHtml(c.pais || '') + ' · ' + (c.score || 0) + 'pts</span>' +
        '</div>' +
        '<div style="font-size:10px;font-weight:600;color:var(--text);margin-bottom:4px;">' + escapeHtml(c.titulo || '') + '</div>' +
        '<div style="font-size:9px;color:var(--text2);line-height:1.4;margin-bottom:5px;">' + escapeHtml((c.justificativa || c.tese || '').substring(0,120)) + (((c.justificativa || '').length > 120) ? '…' : '') + '</div>' +
        (c.acao_recomendada ? '<div style="font-size:9px;color:#a78bfa;margin-bottom:4px;">→ ' + escapeHtml(c.acao_recomendada) + '</div>' : '') +
        '<div style="border-top:1px solid #1e1a3a;margin-top:5px;padding-top:5px;font-size:8px;color:var(--text2);">' +
          '<div style="color:#3d3460;margin-bottom:2px;">Válido até: ' + escapeHtml(c.validade_ate || '') + ' (' + escapeHtml(c.validade_label || '') + ')</div>' +
          (inv.length ? '<div>Invalida se: ' + escapeHtml(inv.join('; ')) + '</div>' : '') +
          (!hasPrice ? '<div style="color:#eab308;margin-top:2px;">⚠ Sem preço local — tipo máx: monitorar</div>' : '') +
          (c.cenario_contrario ? '<div style="color:#6b7280;margin-top:2px;font-style:italic;">Contrário: ' + escapeHtml(c.cenario_contrario.substring(0,80)) + '…</div>' : '') +
        '</div>' +
      '</div>';
    }).join('');
  }

  window.brainFilterCards = function(filter) {
    _brainActiveFilter = filter;
    document.querySelectorAll('[id^="bcard-"]').forEach(function(b) {
      b.style.background = '';
      b.style.borderColor = '';
      b.style.color = '';
    });
    var active = document.getElementById('bcard-' + filter);
    if (active) {
      active.style.background = '#1a0a3a';
      active.style.borderColor = '#7c3aed';
      active.style.color = '#a78bfa';
    }
    _renderCards(_brainData.cards, filter);
  };

  window.showRadarHorizon = function(horizon) {
    _brainActiveHorizon = horizon;

    document.querySelectorAll('[id^="radar-"]').forEach(function(b) {
      b.style.background = '';
      b.style.borderColor = '';
      b.style.color = '';
    });
    var active = document.getElementById('radar-' + horizon);
    if (active) {
      active.style.background = '#1a0a3a';
      active.style.borderColor = '#7c3aed';
      active.style.color = '#a78bfa';
    }

    var el = document.getElementById('brain-radar-view');
    if (!el) return;

    if (!_brainData.radar || !_brainData.radar.radar) {
      el.innerHTML = '<div style="color:var(--text2);font-size:10px;">Dados de radar não disponíveis.</div>';
      return;
    }

    var h = _brainData.radar.radar[horizon];
    if (!h) {
      el.innerHTML = '<div style="color:var(--text2);font-size:10px;">Horizonte não disponível.</div>';
      return;
    }

    var riskColors = { critico:'#ef4444', alto:'#f97316', elevado:'#eab308', moderado:'#3b82f6', baixo:'#22c55e' };
    var rc = riskColors[h.risk_level] || '#6b7280';
    var countries = (h.countries_at_risk || []).join(', ') || 'nenhum';
    var confPct   = Math.round((h.confidence_mult || 0) * 100);

    el.innerHTML = '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">' +
      '<div style="font-size:24px;font-weight:700;color:' + rc + ';">' + (h.risk_level || '?').toUpperCase() + '</div>' +
      '<div>' +
        '<div style="font-size:9px;color:var(--text2);">Horizonte: <span style="color:#a78bfa;">' + escapeHtml(horizon) + '</span></div>' +
        '<div style="font-size:9px;color:var(--text2);">Países em risco: <span style="color:' + rc + ';">' + escapeHtml(countries) + '</span></div>' +
        '<div style="font-size:9px;color:var(--text2);">Confiança: <span style="color:#a78bfa;">' + confPct + '%</span></div>' +
      '</div>' +
    '</div>' +
    (h.events && h.events.length ? '<div style="margin-bottom:6px;">' + h.events.slice(0,3).map(function(ev) {
      var gc = GRAVITY_COLOR[ev.gravidade] || '#6b7280';
      return '<div style="font-size:9px;color:var(--text2);border-left:2px solid ' + gc + ';padding-left:6px;margin-bottom:3px;">' +
        escapeHtml(ev.titulo || '') + ' — ' + escapeHtml(ev.pais_nome || ev.pais || '') +
      '</div>';
    }).join('') + '</div>' : '') +
    '<div style="font-size:8px;color:#3d3460;font-style:italic;">' + escapeHtml(h.note || '') + '</div>' +
    (h.events && !h.events.length && horizon !== 'agora' ?
      '<div style="font-size:9px;color:var(--text2);">Sem eventos específicos projetados para este horizonte.<br>Use dados climáticos atuais como referência.</div>' : '');
  };

  window.sendBrainCommand = function() {
    var input = document.getElementById('brain-cmd-input');
    var result = document.getElementById('brain-cmd-result');
    if (!input || !result) return;

    var cmd = input.value.trim();
    if (!cmd) return;

    result.innerHTML = '<div style="color:#a78bfa;font-size:10px;">Processando comando...</div>';

    fetch('/api/nias/brain/command', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({command: cmd})
    }).then(function(r) { return r.json(); }).then(function(res) {
      if (!res || res.status === 'error') {
        result.innerHTML = '<div style="color:#ef4444;font-size:10px;">Erro: ' + escapeHtml((res && res.message) || 'Falha na requisição') + '</div>';
        return;
      }
      var data = res.data || {};
      var intent = data.intent || 'unknown';
      var tipo   = data.tipo  || '';

      result.innerHTML = _renderCommandResult(data, intent, tipo);
    }).catch(function(e) {
      result.innerHTML = '<div style="color:#ef4444;font-size:10px;">Erro de conexão: ' + escapeHtml(e.message || '') + '</div>';
    });
  };

  function _renderCommandResult(data, intent, tipo) {
    var html = '<div style="background:#0d0d1a;border:1px solid #2d1f6e;border-left:3px solid #7c3aed;border-radius:5px;padding:10px;margin-top:4px;">';
    html += '<div style="font-size:9px;color:#a78bfa;letter-spacing:1px;margin-bottom:6px;">' + escapeHtml(tipo.toUpperCase().replace(/_/g,' ')) + '</div>';

    if (intent === 'pulse') {
      var pulse = data.resultado || {};
      html += '<div style="font-size:10px;color:var(--text);">Saúde: <strong>' + escapeHtml(pulse.health || '?') + '</strong></div>';
      var recs = pulse.recommendations || {};
      html += '<div style="font-size:9px;color:var(--text2);margin-top:4px;">Alertas: ' + (recs.alertas||0) + ' · Comprar: ' + (recs.comprar||0) + ' · Monitorar: ' + (recs.monitorar||0) + '</div>';

    } else if (intent === 'risks') {
      var events = data.eventos || [];
      html += '<div style="font-size:10px;color:#ef4444;margin-bottom:4px;">' + (data.total||0) + ' evento(s) de risco detectado(s)</div>';
      events.slice(0,4).forEach(function(ev) {
        var gc = GRAVITY_COLOR[ev.gravidade] || '#6b7280';
        html += '<div style="font-size:9px;color:var(--text2);border-left:2px solid ' + gc + ';padding-left:6px;margin-bottom:3px;">' +
          '<strong style="color:' + gc + ';">' + escapeHtml(ev.titulo||'') + '</strong> — ' + escapeHtml(ev.pais_nome||ev.pais||'') +
          (ev.acao ? '<br><span style="color:#a78bfa;">→ ' + escapeHtml(ev.acao) + '</span>' : '') +
        '</div>';
      });

    } else if (intent === 'opportunities') {
      var cards = data.cards || [];
      html += '<div style="font-size:10px;color:#22c55e;margin-bottom:4px;">' + (data.total||0) + ' oportunidade(s) com preço real</div>';
      cards.slice(0,3).forEach(function(c) {
        html += '<div style="font-size:9px;color:var(--text2);border-left:2px solid #22c55e;padding-left:6px;margin-bottom:3px;">' +
          '<strong>' + escapeHtml(c.titulo||'') + '</strong> (' + escapeHtml(c.pais||'') + ' · ' + (c.score||0) + 'pts)<br>' +
          escapeHtml((c.acao_recomendada||'').substring(0,80)) +
        '</div>';
      });
      if (!cards.length) html += '<div style="font-size:9px;color:#eab308;">Sem oportunidades com preço local disponível. Execute o pipeline de preços.</div>';

    } else if (intent === 'climate') {
      var events2 = data.eventos || [];
      html += '<div style="font-size:10px;color:#3b82f6;margin-bottom:4px;">' + (data.polos||0) + ' polo(s) monitorado(s) · ' + events2.length + ' evento(s) climático(s)</div>';
      events2.slice(0,4).forEach(function(ev) {
        var gc = GRAVITY_COLOR[ev.gravidade] || '#6b7280';
        html += '<div style="font-size:9px;color:var(--text2);border-left:2px solid ' + gc + ';padding-left:6px;margin-bottom:2px;">' +
          escapeHtml(ev.titulo||'') + ' · ' + escapeHtml(ev.regiao||'') +
        '</div>';
      });
      if (!events2.length) html += '<div style="font-size:9px;color:#22c55e;">Nenhum evento climático extremo detectado.</div>';

    } else if (intent === 'prices') {
      var prices = data.precos || [];
      html += '<div style="font-size:10px;color:var(--text);margin-bottom:4px;">' + (data.total||0) + ' registro(s) de preço</div>';
      prices.slice(0,5).forEach(function(p) {
        html += '<div style="font-size:9px;color:var(--text2);display:flex;justify-content:space-between;">' +
          '<span>' + escapeHtml(p.product_normalized||p.product||'') + ' (' + escapeHtml(p.country_code||'') + ')</span>' +
          '<span style="color:#a78bfa;">' + (p.price_per_kg||p.price||'?') + ' ' + escapeHtml(p.currency||'') + '/kg</span>' +
        '</div>';
      });
      if (!prices.length) html += '<div style="font-size:9px;color:#eab308;">Sem preços disponíveis para o filtro. Execute o pipeline.</div>';

    } else if (intent === 'thesis' || intent === 'summary') {
      var thesis = data.tese || {};
      if (thesis.status === 'sem_dado') {
        html += '<div style="font-size:9px;color:#eab308;">' + escapeHtml(thesis.message||'Sem dados.') + '</div>';
      } else {
        html += '<div style="font-size:10px;color:var(--text);line-height:1.5;margin-bottom:4px;">' + escapeHtml(thesis.thesis||'') + '</div>';
        if (thesis.climate_signals && thesis.climate_signals.length) {
          html += '<div style="font-size:9px;color:#f97316;margin-top:4px;">Sinais: ' + escapeHtml(thesis.climate_signals.join(' · ')) + '</div>';
        }
        html += '<div style="font-size:8px;color:#3d3460;margin-top:4px;">Fontes: ' + escapeHtml((thesis.fontes||[]).join(', ')) + '</div>';
      }

    } else {
      // resumo geral
      var pulso = data.pulso || {};
      var evSummary = data.eventos || {};
      html += '<div style="font-size:10px;color:var(--text);">Saúde: <strong>' + escapeHtml(pulso.health||'?') + '</strong></div>';
      html += '<div style="font-size:9px;color:var(--text2);margin-top:4px;">Eventos: ' + (evSummary.total||0) + ' (' + (evSummary.criticos||0) + ' críticos)</div>';
      if (data.nota) html += '<div style="font-size:9px;color:#a78bfa;margin-top:4px;">' + escapeHtml(data.nota||'') + '</div>';
    }

    if (data.nota && intent !== 'unknown') {
      html += '<div style="font-size:8px;color:#3d3460;margin-top:6px;font-style:italic;">' + escapeHtml(data.nota) + '</div>';
    }
    html += '</div>';
    return html;
  }

  // Expor para o hook de showPanel já existente
  window._brainReady = true;

})();
