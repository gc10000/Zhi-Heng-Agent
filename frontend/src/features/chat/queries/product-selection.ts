import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '@/lib/api/client'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import type { Product, Page } from '@/lib/api/types'
import { scopeKey } from './history'

export function useProductSelection() {
  const auth = useAuthStore(), ui = useUiStore()
  const selectedId = computed(() => ui.productIds[0] || '')
  const directory = useQuery({
    queryKey: computed(() => scopeKey(auth.user?.user_id || '', auth.kb, 'products-selector')),
    queryFn: ({ signal }) => api.request<Page<Product>>(`/products?kb_id=${encodeURIComponent(auth.kb)}&limit=100`, { signal }),
    enabled: computed(() => !!auth.user && !!auth.kb), retry: false,
  })
  const first = computed(() => directory.data.value?.items || [])
  const description = computed(() => {
    const value = ui.selectedProduct
    return value?.userId === auth.user?.user_id && value?.kb === auth.kb && value?.product.product_id === selectedId.value ? value.product : undefined
  })
  const needsLookup = computed(() => !!selectedId.value && !first.value.some(p => p.product_id === selectedId.value))
  const canLookup = computed(() => !!auth.user && needsLookup.value && !!description.value && !directory.isFetching.value && !directory.error.value)
  // 只核对目录带回的型号，精确匹配返回ID；不遍历无限目录，也不把旧描述当作仍有授权。
  const lookup = useQuery({
    queryKey: computed(() => [...scopeKey(auth.user?.user_id || '', auth.kb, 'selected-product', selectedId.value), description.value?.model || '']),
    queryFn: ({ signal }) => api.request<Page<Product>>(`/products?kb_id=${encodeURIComponent(auth.kb)}&limit=100&search=${encodeURIComponent(description.value!.model)}`, { signal }),
    enabled: canLookup, retry: false,
  })
  const verified = computed(() => first.value.find(p => p.product_id === selectedId.value)
    || (needsLookup.value && description.value ? lookup.data.value?.items.find(p => p.product_id === selectedId.value) : undefined))
  const pending = computed(() => !!selectedId.value && (directory.isPending.value || directory.isFetching.value
    || canLookup.value && (lookup.isPending.value || lookup.isFetching.value)))
  const ready = computed(() => !selectedId.value || ui.productIds.length === 1 && !pending.value && !directory.error.value
    && (!needsLookup.value || !lookup.error.value) && !!verified.value)
  const error = computed(() => directory.error.value?.message || (needsLookup.value ? lookup.error.value?.message : '')
    || (selectedId.value && !pending.value && !ready.value ? '无法核对所选设备，请重新从设备目录选择或清空选择。' : ''))
  const options = computed(() => verified.value && !first.value.some(p => p.product_id === verified.value!.product_id) ? [...first.value, verified.value] : first.value)
  function choose(id: string) {
    const product = options.value.find(p => p.product_id === id)
    if (!id || product) ui.selectProduct(product, auth.user!.user_id, auth.kb)
  }
  return { selectedId, options, pending, ready, error, choose, hasMore: computed(() => !!directory.data.value?.next_cursor) }
}
