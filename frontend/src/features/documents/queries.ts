import { computed, type Ref } from 'vue'
import { useInfiniteQuery } from '@tanstack/vue-query'
import { useAuthStore } from '@/stores/auth'
import { scopeKey } from '@/features/chat/queries/history'
import { api } from '@/lib/api/client'
import type { Page } from '@/lib/api/types'
export function usePages<T>(kind:string,id:Ref<string>,path:()=>string,enabled:()=>boolean=()=>true) {
  const auth=useAuthStore()
  return useInfiniteQuery({queryKey:computed(()=>scopeKey(auth.user?.user_id||'',auth.kb,kind,id.value)),initialPageParam:'',
    enabled:computed(()=>!!auth.user&&!!auth.kb&&enabled()),retry:false,
    queryFn:({pageParam,signal})=>api.request<Page<T>>(path()+(path().includes('?')?'&':'?')+'limit=50'+(pageParam?'&cursor='+encodeURIComponent(pageParam):''),{signal}),
    getNextPageParam:page=>page.next_cursor||undefined})
}
