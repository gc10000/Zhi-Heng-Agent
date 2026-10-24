import { afterEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { api } from '@/lib/api/client'
import { useProductSelection } from '@/features/chat/queries/product-selection'
const first = { product_id: 'first', model: '首屏型号' }, far = { product_id: 'far', model: '远端型号' }
function setup() {
  const pinia = createPinia(), cache = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const auth = useAuthStore(pinia), ui = useUiStore(pinia)
  auth.accept({ user: { user_id: 'u', username: '测试', role: 'viewer', kb_ids: ['k', 'other'] }, csrf_token: 'test' })
  let selection!: ReturnType<typeof useProductSelection>
  const wrapper = mount({ setup() { selection = useProductSelection(); return () => null } }, { global: { plugins: [pinia, [VueQueryPlugin, { queryClient: cache }]] } })
  return { auth, ui, selection, close: () => { wrapper.unmount(); cache.clear() } }
}
afterEach(() => vi.restoreAllMocks())

it('只有ID而无当前范围描述时明确拒绝核对，不遍历目录或静默接受', async () => {
  const call = vi.spyOn(api, 'request').mockResolvedValue({ items: [first], next_cursor: 'more' })
  const s = setup(); s.ui.productIds = ['unknown']
  await flushPromises(); await vi.waitFor(() => expect(s.selection.pending.value).toBe(false))
  expect(s.selection.ready.value).toBe(false); expect(s.selection.error.value).toContain('无法核对所选设备')
  expect(call).toHaveBeenCalledTimes(1); s.close()
})

it('旧用户或知识范围描述不能用于补充查询和范围提交', async () => {
  const call = vi.spyOn(api, 'request').mockResolvedValue({ items: [first], next_cursor: null })
  const s = setup(); s.ui.selectProduct(far, 'another-user', 'k')
  await flushPromises(); await vi.waitFor(() => expect(s.selection.pending.value).toBe(false))
  expect(s.selection.ready.value).toBe(false); expect(call).toHaveBeenCalledTimes(1)
  s.ui.selectProduct(far, 'u', 'other'); await flushPromises()
  expect(s.selection.ready.value).toBe(false); expect(call).toHaveBeenCalledTimes(1)
  s.close()
})

it('核对远端设备的迟到响应不能覆盖用户已选择的首屏设备', async () => {
  let release!: (value: unknown) => void
  vi.spyOn(api, 'request').mockImplementation(path => String(path).includes('search=')
    ? new Promise(resolve => { release = resolve }) : Promise.resolve({ items: [first], next_cursor: 'more' }))
  const s = setup(); s.ui.selectProduct(far, 'u', 'k')
  await vi.waitFor(() => expect(release).toBeTypeOf('function'))
  expect(s.selection.ready.value).toBe(false)
  s.selection.choose('first'); release({ items: [far], next_cursor: null }); await flushPromises()
  expect(s.selection.selectedId.value).toBe('first'); expect(s.selection.ready.value).toBe(true)
  expect(s.selection.options.value).toEqual([first]); s.close()
})
