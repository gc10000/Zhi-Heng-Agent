<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuery, useInfiniteQuery, useQueryClient } from '@tanstack/vue-query'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { api } from '@/lib/api/client'
import type { Page } from '@/lib/api/types'
import type { Support, CaseRecord } from './types'
import OperationChecklist from './components/OperationChecklist.vue'
const route=useRoute(),auth=useAuthStore(),ui=useUiStore(),cache=useQueryClient()
const cid=computed(()=>String(route.query.conversation||'')),rid=computed(()=>String(route.query.run||''))
const scope=computed(()=>[auth.user?.user_id||'',auth.kb])
const supportKey=computed(()=>[...scope.value,'support',cid.value])
const support=useQuery({queryKey:supportKey,enabled:computed(()=>!!auth.user&&!!cid.value),retry:false,
  queryFn:({signal})=>api.request<Support>(`/conversations/${encodeURIComponent(cid.value)}/support`,{signal})})
const records=useInfiniteQuery({queryKey:computed(()=>[...scope.value,'cases']),enabled:computed(()=>!!auth.user),retry:false,
  initialPageParam:'',queryFn:({pageParam,signal})=>api.request<Page<CaseRecord>>(`/cases?limit=50${pageParam?'&cursor='+encodeURIComponent(pageParam):''}`,{signal}),getNextPageParam:last=>last.next_cursor||undefined})
const items=computed(()=>records.data.value?.pages.flatMap(p=>p.items)||[])
const caseId=ref(''),error=ref(''),busy=ref(false),edits=reactive<Record<string,string>>({})
const record=useQuery({queryKey:computed(()=>[...scope.value,'case',caseId.value]),enabled:computed(()=>!!auth.user&&!!caseId.value),retry:false,
  queryFn:({signal})=>api.request<CaseRecord>('/cases/'+encodeURIComponent(caseId.value),{signal})})
let epoch=0
watch(()=>[...scope.value,cid.value,rid.value],()=>{epoch++;caseId.value='';error.value='';Object.keys(edits).forEach(k=>delete edits[k])})
watch(()=>record.data.value, value=>{Object.keys(edits).forEach(k=>delete edits[k]);if(value)Object.assign(edits,value.fields)})
async function perform(action:()=>Promise<void>){if(busy.value)return;busy.value=true;error.value='';const generation=epoch;try{await action()}catch(e){if(generation===epoch)error.value=(e as Error).message}finally{busy.value=false}}
async function change(path:string,fields:Record<string,unknown>){const current=support.data.value;if(!current)return;const key=[...supportKey.value],generation=epoch;
  const updated=await api.post<Support>(`/conversations/${encodeURIComponent(cid.value)}/support${path}`,{expected_version:current.version,...fields});
  if(generation===epoch)cache.setQueryData(key,updated)
}
function citation(runId:string,citationId:string){ui.selectedCitation={runId,citationId};ui.evidence=true}
async function draft(){const generation=epoch;const value=await api.post<CaseRecord>('/cases',{run_id:rid.value,expected_support_version:support.data.value?.version||0});if(generation!==epoch)return;caseId.value=value.case_id;cache.setQueryData([...scope.value,'case',value.case_id],value);await records.refetch()}
async function save(){if(!record.data.value)return;const old=record.data.value,generation=epoch;const value=await api.request<CaseRecord>('/cases/'+old.case_id,{method:'PATCH',body:JSON.stringify({expected_version:old.version,fields:{...edits}})});if(generation===epoch)cache.setQueryData([...scope.value,'case',old.case_id],value)}
async function confirm(){if(!record.data.value)return;const old=record.data.value,generation=epoch;const value=await api.post<CaseRecord>('/cases/'+old.case_id+'/confirm',{expected_version:old.version});if(generation===epoch){cache.setQueryData([...scope.value,'case',old.case_id],value);await records.refetch()}}
const values=reactive({device:'',symptom:''})
</script>
<template><section class="cases-page"><h1>处理记录</h1><p>建议、用户自报与已确认记录分别留痕。转交草稿不会自动发送给他人。</p>
<p v-if="error||support.error.value||records.error.value||record.error.value" role="alert">{{error||support.error.value?.message||records.error.value?.message||record.error.value?.message}}</p>
<section v-if="cid&&support.data.value" aria-label="当前支持流程"><h2>支持上下文</h2><p role="status">{{support.data.value.prompt}}</p><p>状态：{{support.data.value.state}} · 上下文版本 {{support.data.value.context_version}}</p>
<label>确认设备型号<input v-model="values.device" maxlength="4000" /></label><label>实际现象<input v-model="values.symptom" maxlength="4000" /></label>
<button :disabled="busy||!rid" @click="perform(()=>change('',{run_id:rid,values:Object.fromEntries(Object.entries(values).filter(([,v])=>v.trim())),confirmed:true}))">记录确认信息</button>
<button :disabled="busy||!rid" @click="perform(()=>change('/checklist',{run_id:rid}))">依据本轮引用生成清单</button>
<OperationChecklist :operations="support.data.value.operations" :busy="busy" @report="(id,status,note)=>perform(()=>change('/operations/'+id,{status,note}))" @citation="citation" />
<button :disabled="busy" @click="perform(()=>change('',{action:'handoff'}))">转交人工支持</button>
<button :disabled="busy" @click="perform(()=>change('',{action:'resolve'}))">用户确认已解决</button>
<button :disabled="busy" @click="perform(()=>change('',{action:'cancel'}))">结束支持流程</button>
<button :disabled="busy||!rid" @click="perform(draft)">生成转交草稿</button></section>
<p v-if="!records.isPending.value&&!items.length">尚无处理草稿。请从已完成的问答打开支持流程。</p>
<ul><li v-for="item in items" :key="item.case_id"><button @click="caseId=item.case_id">{{item.fields.question}} · {{item.status==='draft'?'草稿':'用户已确认'}}</button></li></ul>
<button v-if="records.hasNextPage.value" :disabled="records.isFetchingNextPage.value" @click="records.fetchNextPage()">加载更多记录</button>
<article v-if="record.data.value" aria-label="处理草稿"><h2>{{record.data.value.status==='draft'?'待用户确认的草稿':'用户已确认记录'}}</h2><p>未知字段需保留未知；摘要来自回答，实际操作以用户自报记录为准。</p>
<label v-for="(_,key) in record.data.value.fields" :key="key">{{{question:'问题',device:'设备',symptom:'现象',environment:'环境',error_code:'错误码',tried:'已尝试',summary:'处理摘要',handoff_reason:'转交原因'}[key]||key}}<textarea v-model="edits[key]" :disabled="busy||record.data.value.status==='confirmed'" maxlength="16000" /></label>
<template v-if="record.data.value.status==='draft'"><button :disabled="busy" @click="perform(save)">保存用户编辑</button><button :disabled="busy" @click="perform(confirm)">确认保存当前服务端草稿</button><p>请先保存编辑，再确认；确认冻结服务端版本。</p></template>
<p v-else>确认时间：{{record.data.value.confirmed_at}}</p>
<OperationChecklist :operations="record.data.value.operations" :busy="true" @citation="citation" />
</article></section></template>
