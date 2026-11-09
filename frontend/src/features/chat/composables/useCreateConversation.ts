import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQueryClient } from '@tanstack/vue-query'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { api } from '@/lib/api/client'

/**
 * P4-1：新建会话动作（侧栏主钮与聊天空态共用，避免复制粘贴）。
 * 新建成功后跳 /chat/{id} 并失效会话目录缓存；离开 /chat 时由调用方触发同样安全。
 */
export function useCreateConversation() {
  const auth = useAuthStore(), ui = useUiStore(), cache = useQueryClient(), router = useRouter()
  const creating = ref(false), error = ref('')
  async function createConversation() {
    if (creating.value || !auth.user) return
    creating.value = true
    error.value = ''
    try {
      const c = await api.post<{ conversation_id: string }>('/conversations', { kb_id: auth.kb })
      await cache.invalidateQueries({ queryKey: ['scope', auth.user.user_id, auth.kb, 'conversations'] })
      ui.menu = false
      void router.push('/chat/' + c.conversation_id)
    } catch (e) {
      error.value = (e as Error).message
    } finally { creating.value = false }
  }
  return { creating, error, createConversation }
}
