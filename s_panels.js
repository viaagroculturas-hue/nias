(() => {
  const TIMER_MS = 15000;
  const timers = {};

  function ensureInterpretationNode(card) {
    let node = card.querySelector('.horti-interpretation');
    if (!node) {
      node = document.createElement('div');
      node.className = 'horti-interpretation';
      node.setAttribute('aria-live', 'polite');
      card.appendChild(node);
    }
    return node;
  }

  function resolveCard(cardId) {
    return document.getElementById(cardId) || document.getElementById('hc-' + cardId);
  }

  window.toggleInterpretation = function toggleInterpretation(cardId) {
    const card = resolveCard(cardId);
    if (!card) return;

    const node = ensureInterpretationNode(card);
    const text = card.dataset.interpretationText || 'Interpretação NIA$: dados insuficientes para a unidade CEASA selecionada.';
    node.textContent = text;

    if (timers[card.id]) clearTimeout(timers[card.id]);
    card.classList.add('interpretation-mode');
    card.setAttribute('aria-pressed', 'true');

    timers[card.id] = setTimeout(() => {
      card.classList.remove('interpretation-mode');
      card.setAttribute('aria-pressed', 'false');
      delete timers[card.id];
    }, TIMER_MS);
  };

  window.isInterpretationActive = function isInterpretationActive(cardId) {
    const card = resolveCard(cardId);
    return !!card && card.classList.contains('interpretation-mode');
  };

  window.setDashboardCeasaUnit = function setDashboardCeasaUnit(unitKey) {
    window.NiasSelectedCeasaUnit = unitKey;
    window.dispatchEvent(new CustomEvent('nias:ceasa-unit-selected', { detail: { unitKey } }));
  };

  window.registerHortiInterpretationCards = function registerHortiInterpretationCards() {
    document.querySelectorAll('.horti-card').forEach(card => {
      if (card.dataset.interpretationBound === '1') return;
      card.dataset.interpretationBound = '1';
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');
      card.addEventListener('click', () => window.toggleInterpretation(card.id));
      card.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          window.toggleInterpretation(card.id);
        }
      });
    });
  };

  document.addEventListener('DOMContentLoaded', () => {
    window.registerHortiInterpretationCards();
  });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) return;
    Object.keys(timers).forEach(cardId => {
      const card = resolveCard(cardId);
      if (!card) delete timers[cardId];
    });
  });

  window.NiasInterpretation = {
    TIMER_MS,
    timers,
  };
})();
