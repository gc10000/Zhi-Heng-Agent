<script setup lang="ts">
import { computed,ref } from 'vue'
import { useQuery,useQueryClient } from '@tanstack/vue-query'
import { api } from '@/lib/api/client'
import { useAuthStore } from '@/stores/auth'
import { scopeKey } from '@/features/chat/queries/history'
import type { Job } from '@/lib/api/types'
const props=defineProps<{jobId:string}>(),auth=useAuthStore(),cache=useQueryClient(),busy=ref(false),error=ref('')
const stage:Record<string,string>={pending:'等待派发',download:'读取原件',parse:'解析原件',images:'登记图片与摘要',chunk:'结构化切片',embed:'生成索引',index:'写入隔离索引',validate:'验证产物',publish:'切换活动修订',completed:'已完成'}
const query=useQuery({queryKey:computed(()=>scopeKey(auth.user?.user_id||'',auth.kb,'job',props.jobId)),enabled:computed(()=>!!props.jobId),retry:false,
  queryFn:({signal})=>api.request<Job>(`/import-jobs/${encodeURIComponent(props.jobId)}`,{signal}),
  refetchInterval:q=>q.state.data&&['pending','running'].includes(q.state.data.state)?1500:false})
async function retry(){if(busy.value||!query.data.value)return;busy.value=true;error.value='';try{await api.post(`/import-jobs/${encodeURIComponent(props.jobId)}/retry`,{expected_version:query.data.value.version});await query.refetch();await cache.invalidateQueries({queryKey:['scope',auth.user?.user_id,auth.kb,'documents']})}catch(e){error.value=(e as Error).message;await query.refetch()}finally{busy.value=false}}
</script>
<template><section class="job-panel"><h2>导入任务</h2><p class="muted">{{jobId}}</p><p v-if="query.isPending.value" role="status">正在读取任务…</p><p v-if="query.error.value||error" role="alert">{{error||query.error.value?.message}}</p><template v-if="query.data.value"><p role="status">{{query.data.value.state==='completed'?'导入任务完成，发布状态以活动修订为准。':query.data.value.state==='failed'?'导入失败':query.data.value.state==='pending'?'等待派发':'正在导入'}}</p><p>阶段：{{stage[query.data.value.stage]||query.data.value.stage}} · 尝试 {{query.data.value.attempt}}</p><p v-if="query.data.value.error" role="alert">{{query.data.value.error.code}} · {{query.data.value.error.stage||query.data.value.stage}}</p><button v-if="auth.user?.role!=='viewer'&&query.data.value.state==='failed'&&query.data.value.retryable" :disabled="busy" @click="retry">重试导入</button><p v-else-if="query.data.value.state==='failed'&&!query.data.value.retryable">此错误不能自动重试，请修正配置或原件后重新提交。</p></template><button @click="query.refetch()">刷新任务状态</button></section></template>
