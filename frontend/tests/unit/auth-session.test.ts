import { afterEach, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
import App from '@/App.vue'
import { api } from '@/lib/api/client'
import { useAuthStore } from '@/stores/auth'
import { setActivePinia } from 'pinia'
import { routerKey } from 'vue-router'

afterEach(() => vi.restoreAllMocks())
it('401清空上位用户的Query缓存及身份页', async () => {
  vi.spyOn(api, 'request').mockResolvedValue({ user: { user_id: 'owner-a', username: '甲', role: 'viewer', kb_ids: ['k'] }, csrf_token: 'csrf' })
  const cache = new QueryClient()
  cache.setQueryData(['owner-a', 'private'], { answer: '前用户的私有答案' })
  const wrapper = mount(App, { global: { provide: { [routerKey as symbol]: { replace: vi.fn() } }, plugins: [createPinia(), [VueQueryPlugin, { queryClient: cache }]] } })
  await flushPromises()
  window.dispatchEvent(new Event('session-expired'))
  await flushPromises()
  expect(cache.getQueryCache().getAll()).toHaveLength(0)
  expect(wrapper.text()).toContain('登录工作台')
  wrapper.unmount()
})
it('退出后迟到身份恢复不能复活旧用户，清理订阅只执行一次', async () => {
  setActivePinia(createPinia())
  let complete!: (value: unknown) => void
  vi.spyOn(api, 'request').mockImplementation(() => new Promise(resolve => { complete = resolve }))
  const auth = useAuthStore(), close = vi.fn()
  auth.onClear(close)
  const pending = auth.restore()
  auth.clear()
  complete({ user: { user_id: 'old', username: '旧用户', kb_ids: ['k'], role: 'viewer' }, csrf_token: 'old' })
  await pending
  expect(auth.user).toBeUndefined(); expect(api.csrf).toBe(''); expect(close).toHaveBeenCalledTimes(1)
})
