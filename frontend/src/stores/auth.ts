import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/lib/api/client'
import type { Login, User } from '@/lib/api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User>(), kb = ref(''), restored = ref(false)
  /** T2.2：kb 显示名映射；无后端名称时取 ID 首段大写作展示名。 */
  const kbLabels = ref<Record<string, string>>({})
  function labelOf(id: string) {
    if (kbLabels.value[id]) return kbLabels.value[id]
    const head = id.split('-')[0].split('_')[0] || id
    return head.toUpperCase()
  }
  let epoch = 0
  const cleanups = new Set<() => void>()
  function onClear(callback: () => void) { cleanups.add(callback); return () => cleanups.delete(callback) }
  function clear() {
    epoch++; api.csrf = ''; user.value = undefined; kb.value = ''
    for (const callback of cleanups) callback()
  }
  function accept(value: Login) { api.csrf = value.csrf_token; user.value = value.user; kb.value = value.user.kb_ids[0] || ''; restored.value = true }  async function restore() {
    const version = epoch
    try { const value = await api.request<Login>('/me'); if (epoch === version) accept(value) }
    catch { if (epoch === version) clear() }
    finally { restored.value = true }
  }
  async function logout() {
    try { await api.post('/auth/logout', {}) } finally { clear() }
  }
  return { user, kb, restored, kbLabels, labelOf, accept, restore, clear, logout, onClear }
})
