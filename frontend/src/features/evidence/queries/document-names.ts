import { computed } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/lib/api/client'
import type { Document, Page } from '@/lib/api/types'
import { scopeKey } from '@/features/chat/queries/history'

/**
 * T1.4：citation 只带 document_id；用 /documents 列表缓存做 document_id → name 映射。
 * documents 无限分页仅能覆盖首屏，这里独立维护一个全量映射缓存（分页拉取、带 staleTime）。
 */
export function useDocumentNames() {
  const auth = useAuthStore(), cache = useQueryClient()
  const key = computed(() => scopeKey(auth.user?.user_id || '', auth.kb, 'document-name-map'))
  const query = useQuery({
    queryKey: key,
    enabled: computed(() => !!auth.user && !!auth.kb),
    retry: false,
    staleTime: 5 * 60_000,
    queryFn: async ({ signal }) => {
      const map: Record<string, string> = {}
      let cursor = ''
      for (let i = 0; i < 20; i++) {
        const page = await api.request<Page<Document>>(`/documents?kb_id=${encodeURIComponent(auth.kb)}&limit=100${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`, { signal })
        for (const d of page.items) map[d.document_id] = d.name
        if (!page.next_cursor) break
        cursor = page.next_cursor
      }
      return map
    },
  })
  function nameOf(documentId: string) {
    return query.data.value?.[documentId] || ''
  }
  return { names: query.data, pending: query.isPending, error: query.error, nameOf }
}
