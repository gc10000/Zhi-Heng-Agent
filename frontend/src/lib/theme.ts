import { ref } from 'vue'

export type ThemeName = 'light' | 'dark'

const STORAGE_KEY = 'zhiheng-theme'
const state = ref<ThemeName>('light')
let initialized = false

function apply(theme: ThemeName) {
  const root = document.documentElement
  if (theme === 'dark') root.setAttribute('data-theme', 'dark')
  else root.removeAttribute('data-theme')
}

/** 初始化主题：localStorage 记忆优先，无则跟随系统 prefers-color-scheme。 */
function init() {
  if (initialized) return
  initialized = true
  let stored: string | null = null
  try { stored = localStorage.getItem(STORAGE_KEY) } catch { stored = null }
  if (stored === 'light' || stored === 'dark') state.value = stored
  else if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) state.value = 'dark'
  apply(state.value)
}

/** 切换主题并持久化。 */
function toggle() {
  set(state.value === 'dark' ? 'light' : 'dark')
}

/** 设置指定主题并持久化。 */
function set(theme: ThemeName) {
  state.value = theme
  apply(theme)
  try { localStorage.setItem(STORAGE_KEY, theme) } catch { /* 隐私模式等场景静默失败 */ }
}

export function useTheme() {
  return { theme: state, init, toggle, set }
}
