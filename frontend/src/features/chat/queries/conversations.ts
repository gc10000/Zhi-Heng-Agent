import { computed, type Ref } from 'vue'
import { useInfiniteQuery, useQuery } from '@tanstack/vue-query'
import { useAuthStore } from '@/stores/auth'
import { api, ApiError } from '@/lib/api/client'
import type { Conversation, Message, Page } from '@/lib/api/types'
import { scopeKey, mergeHistory } from './history'
export function useConversations() {
  const auth = useAuthStore()
  return useInfiniteQuery({ queryKey: computed(() => scopeKey(auth.user?.user_id || '', auth.kb, 'conversations')),
    initialPageParam: '', queryFn: ({ pageParam, signal }) => api.request<Page<Conversation>>(`/conversations?limit=50${pageParam ? '&cursor=' + encodeURIComponent(pageParam) : ''}`, { signal }),
    getNextPageParam: last => last.next_cursor || undefined, enabled: computed(() => !!auth.user && !!auth.kb), retry: false })
}
export function useHistory(cid: Ref<string>) {
  const auth = useAuthStore()
  const query = useInfiniteQuery({ queryKey: computed(() => scopeKey(auth.user?.user_id || '', auth.kb, 'history', cid.value)),
    initialPageParam: '', queryFn: ({ pageParam, signal }) => api.request<Page<Message>>(`/conversations/${encodeURIComponent(cid.value)}/messages?limit=50${pageParam ? '&cursor=' + encodeURIComponent(pageParam) : ''}`, { signal }),
    getNextPageParam: last => last.next_cursor || undefined, enabled: computed(() => !!auth.user && !!cid.value), retry: false })
  return { query, messages: computed(() => mergeHistory(query.data.value?.pages || [])) }
}
export function useConversation(cid: Ref<string>) {
  const auth = useAuthStore()
  return useQuery({ queryKey: computed(() => scopeKey(auth.user?.user_id || '', auth.kb, 'conversation', cid.value)),
    enabled: computed(() => !!cid.value && !!auth.user), retry: false,
    queryFn: async ({ signal }) => {
      // v1没有单会话GET；按真实目录分页查找，不假设首50条包含深链接。
      let cursor: string | null = ''
      const wanted = cid.value, kb = auth.kb
      do {
        const page: Page<Conversation> = await api.request(`/conversations?limit=100${cursor ? '&cursor=' + encodeURIComponent(cursor) : ''}`, { signal })
        const value = page.items.find(c => c.conversation_id === wanted)
        if (value) {
          if (value.kb_id !== kb) throw new ApiError(409, 'knowledge_scope_changed', '此会话不属于当前知识范围，请先切换知识范围。')
          return value
        }
        cursor = page.next_cursor
      } while (cursor)
      throw new ApiError(404, 'not_found', '会话不存在或不在授权范围。')
    } })
}
