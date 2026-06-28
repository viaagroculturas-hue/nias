// NIAS v2 — Router de telas (sem reload)

const _screens = {}   // { id: { el, module } }
let _current = null

export function registerScreen(id, moduleObj) {
  _screens[id] = { el: document.getElementById(`screen-${id}`), module: moduleObj }
}

export function navigate(id) {
  if (_current === id) return

  // Desativa anterior
  if (_current && _screens[_current]) {
    _screens[_current].el?.classList.remove('active')
    _screens[_current].module?.onLeave?.()
  }

  _current = id
  const screen = _screens[id]
  if (!screen) { console.warn('[Router] Tela não encontrada:', id); return }

  screen.el?.classList.add('active')
  screen.module?.onEnter?.()

  // Atualiza sidebar
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.screen === id)
  })

  // Atualiza URL hash sem navegar
  history.replaceState(null, '', `#${id}`)
}

export function currentScreen() { return _current }

export function initRouter(defaultScreen) {
  // Wiring sidebar
  document.querySelectorAll('.nav-btn[data-screen]').forEach(btn => {
    btn.addEventListener('click', () => navigate(btn.dataset.screen))
  })

  // Garantir que nenhuma screen esteja ativa no HTML antes de navegar
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'))

  // Restaurar from hash
  const hash = location.hash.replace('#', '')
  navigate(hash && _screens[hash] ? hash : defaultScreen)
}
