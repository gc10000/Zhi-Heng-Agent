import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/lib/api/client'
import type { Login, User } from '@/lib/api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User>(), kb = ref(''), restored = ref(false)
  let epoch = 0
  const cleanups = new Set<() => void>()
  function onClear(callback: () => void) { cleanups.add(callback); return () => cleanups.delete(callback) }
  function clear() {
    epoch++; api.csrf = ''; user.value = undefined; kb.value = ''
    for (const callback of cleanups) callback()
  }
  function accept(value: Login) { api.csrf = value.csrf_token; user.value = value.user; kb.value = value.user.kb_ids[0] || ''; restored.value = true }
  async function restore() {
    const version = epoch
    try { const value = await api.request<Login>('/me'); if (epoch === version) accept(value) }
    catch { if (epoch === version) clear() }
    finally { restored.value = true }
  }
  async function logout() {
    try { await api.post('/auth/logout', {}) } finally { clear() }
  }
  return { user, kb, restored, accept, restore, clear, logout, onClear }
})
