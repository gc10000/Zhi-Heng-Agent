import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { api } from '@/lib/api/client'
import type { Citation } from '@/lib/api/types'
import { scopeKey } from '@/features/chat/queries/history'
export function useCitation() {
  const auth=useAuthStore(),ui=useUiStore()
  return useQuery({queryKey:computed(()=>scopeKey(auth.user?.user_id||'',auth.kb,'citation',`${ui.selectedCitation?.runId || ''}/${ui.selectedCitation?.citationId || ''}`)),
    enabled:computed(()=>!!auth.user && !!ui.selectedCitation),retry:false,
    queryFn:({signal})=>api.request<Citation>(`/runs/${encodeURIComponent(ui.selectedCitation!.runId)}/citations/${encodeURIComponent(ui.selectedCitation!.citationId)}`,{signal})})
}
