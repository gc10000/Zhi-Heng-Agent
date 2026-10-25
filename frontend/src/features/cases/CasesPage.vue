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
import SupportContext from './components/SupportContext.vue'
import FeedbackForm from './components/FeedbackForm.vue'
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
async function refresh(){await records.refetch();if(cid.value)await support.refetch();if(caseId.value)await record.refetch()}
async function change(path:string,fields:Record<string,unknown>){const current=support.data.value;if(!current||support.isFetching.value||support.error.value)return;const key=[...supportKey.value],generation=epoch;
  const updated=await api.post<Support>(`/conversations/${encodeURIComponent(cid.value)}/support${path}`,{expected_version:current.version,...fields});
  if(generation===epoch)cache.setQueryData(key,updated)
}
function citation(runId:string,citationId:string){ui.selectedCitation={runId,citationId};ui.evidence=true}
async function draft(){const generation=epoch;const value=await api.post<CaseRecord>('/cases',{run_id:rid.value,expected_support_version:support.data.value?.version||0});if(generation!==epoch)return;caseId.value=value.case_id;cache.setQueryData([...scope.value,'case',value.case_id],value);await records.refetch()}
async function save(){if(!record.data.value)return;const old=record.data.value,generation=epoch;const value=await api.request<CaseRecord>('/cases/'+old.case_id,{method:'PATCH',body:JSON.stringify({expected_version:old.version,fields:{...edits}})});if(generation===epoch)cache.setQueryData([...scope.value,'case',old.case_id],value)}
async function confirm(){if(!record.data.value)return;const old=record.data.value,generation=epoch;const value=await api.post<CaseRecord>('/cases/'+old.case_id+'/confirm',{expected_version:old.version});if(generation===epoch){cache.setQueryData([...scope.value,'case',old.case_id],value);await records.refetch()}}
const dirty=computed(()=>!!record.data.value&&JSON.stringify(edits)!==JSON.stringify(record.data.value.fields))
const ended=computed(()=>!!support.data.value&&['handoff','resolved','cancelled'].includes(support.data.value.state))
const toolQuery=ref('')
const reasonLabels:Record<string,string>={all_steps_ineffective:'已有操作均由用户记录为无效',missing_evidence:'缺少可追溯证据',missing_slot:'待补充必要信息',no_progress:'没有获得新信息',round_budget:'补充信息达到上限',user_handoff:'用户要求转交',user_resolve:'用户确认解决',user_cancel:'用户结束支持',evidence_available:'已有资料可供核对',tool_repeat:'工具未获得新证据',tool_failed:'工具未获得可用结果',tool_timeout:'工具读取超时'}
const feedbackStatus=ref(''),exported=ref('')
const feedbackCitations=computed(()=>record.data.value?.run_snapshot?.citations||record.data.value?.citations||[])
watch(()=>[caseId.value,...scope.value],()=>{feedbackStatus.value='';exported.value=''})
async function feedback(value:unknown){await api.post('/feedback',value);feedbackStatus.value='反馈已保存为待审，尚未进入知识库。'}
async function download(){if(!record.data.value)return;const generation=epoch,id=record.data.value.case_id;const data=await api.request<{filename:string;markdown:string}>('/cases/'+id+'/export');if(generation!==epoch||record.data.value?.case_id!==id)return;exported.value=data.markdown;const url=URL.createObjectURL(new Blob([data.markdown],{type:'text/markdown;charset=utf-8'}));const anchor=document.createElement('a');anchor.href=url;anchor.download=data.filename;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
</script>
<template><section class="cases-page"><h1>处理记录</h1><p>建议、用户自报与已确认记录分别留痕。转交草稿不会自动发送给他人。</p>
<p v-if="error||support.error.value||records.error.value||record.error.value" role="alert">{{error||support.error.value?.message||records.error.value?.message||record.error.value?.message}}</p>
<button :disabled="busy" @click="perform(refresh)">刷新服务状态</button>
<section v-if="cid&&support.data.value" aria-label="当前支持流程">
<SupportContext :context="support.data.value" :busy="busy" :run-id="rid" @save="values=>perform(()=>change('',{...(!support.data.value?.run_id&&rid?{run_id:rid}:{}),values,confirmed:true}))" @action="action=>perform(()=>change('',{action}))" />
<button v-if="rid&&support.data.value.run_id&&rid!==support.data.value.run_id" :disabled="busy||ended" @click="perform(()=>change('',{run_id:rid}))">关联本轮新回答</button>
<RouterLink :to="'/chat/'+cid">回到会话继续问答</RouterLink>
<button :disabled="busy||!rid||ended" @click="perform(()=>change('/checklist',{run_id:rid}))">依据本轮引用生成清单</button>
<OperationChecklist :operations="support.data.value.operations" :busy="busy" @report="(id,status,note)=>perform(()=>change('/operations/'+id,{status,note}))" @citation="citation" />
<section aria-label="有限只读工具"><h2>有限只读工具</h2><p>工具仅读取授权资料，失败、重复或预算耗尽后转交。</p><label>扩展检索问题<input v-model="toolQuery" maxlength="1000" /></label><button :disabled="busy||ended||!toolQuery.trim()" @click="perform(()=>change('/tools',{tool:'search_manual',arguments:{query:toolQuery}}))">检索内部手册</button>
<button v-for="c in support.data.value.citations" :key="c.citation_id" :disabled="busy||ended" @click="perform(()=>change('/tools',{tool:'read_evidence',arguments:{citation_id:c.citation_id}}))">只读核对引用 {{c.citation_id}}</button>
<article v-for="call in support.data.value.tool_calls" :key="call.call_id"><p>{{({search_manual:'检索内部手册',lookup_product:'查产品目录',read_evidence:'读取引用'} as Record<string,string>)[call.tool]||'只读核对'}} · {{call.status==='completed'?'读取完成':call.status==='running'?'待核对结果':'未获得可用结果'}}</p><p v-if="call.reason">工具未获得新证据或达到预算，请转交人工支持。</p><p v-if="call.output">{{call.output.notice}}</p><blockquote v-for="(item,index) in call.output?.items||[]" :key="index">{{item.text||item.model||'请核对资料来源'}}</blockquote></article></section>
<button :disabled="busy||!rid" @click="perform(draft)">生成转交草稿</button></section>
<p v-if="!records.isPending.value&&!items.length">尚无处理草稿。请从已完成的问答打开支持流程。</p>
<ul><li v-for="item in items" :key="item.case_id"><button :disabled="busy" @click="caseId=item.case_id">{{item.fields.question}} · {{item.status==='draft'?'草稿':'用户已确认'}}</button></li></ul>
<button v-if="records.hasNextPage.value" :disabled="records.isFetchingNextPage.value" @click="records.fetchNextPage()">加载更多记录</button>
<article v-if="record.data.value" aria-label="处理草稿"><h2>{{record.data.value.status==='draft'?'待用户确认的草稿':'用户已确认记录'}}</h2><p>未知字段需保留未知；摘要来自回答，实际操作以用户自报记录为准。</p>
<label v-for="(_,key) in record.data.value.fields" :key="key">{{{question:'问题',device:'设备',symptom:'现象',environment:'环境',error_code:'错误码',tried:'已尝试',summary:'处理摘要',handoff_reason:'转交原因'}[key]||key}}<textarea :value="key==='handoff_reason'?(reasonLabels[edits[key]||'']||edits[key]):edits[key]" @input="edits[key]=($event.target as HTMLTextAreaElement).value" :disabled="busy||record.data.value.status==='confirmed'" maxlength="16000" /></label>
<template v-if="record.data.value.status==='draft'"><button :disabled="busy||!dirty" @click="perform(save)">保存用户编辑</button><button :disabled="busy||dirty" @click="perform(confirm)">确认保存当前服务端草稿</button><p>请先保存编辑，再确认；确认冻结服务端版本。</p></template>
<p v-else>确认时间：{{record.data.value.confirmed_at}}</p>
<button v-if="record.data.value.status==='confirmed'" :disabled="busy" @click="perform(download)">导出已确认 Markdown</button><pre v-if="exported" aria-label="导出内容">{{exported}}</pre>
<OperationChecklist :operations="record.data.value.operations" :busy="true" @citation="citation" />
<FeedbackForm :run-id="record.data.value.run_id" :citations="feedbackCitations" :busy="busy" @submit="value=>perform(()=>feedback(value))" /><p v-if="feedbackStatus" role="status">{{feedbackStatus}}</p>
</article></section></template>
<style scoped>.cases-page{padding:1.5rem;min-width:0;max-width:70rem}.cases-page section,.cases-page article,.cases-page form{margin:1.2rem 0}.cases-page h1{font-size:1.7rem;margin-bottom:.8rem}.cases-page h2{font-size:1.2rem;margin:1rem 0 .5rem}.cases-page p{line-height:1.7;margin:.5rem 0}.cases-page label{display:grid;gap:.4rem;margin:.7rem 0}.cases-page input,.cases-page textarea{min-width:0;max-width:100%}.cases-page button{margin:.3rem .5rem .3rem 0}.cases-page pre{max-height:22rem;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;padding:1rem;background:#fff;border:1px solid #cbd5e1}.cases-page blockquote{border-left:3px solid #0f766e;padding:.6rem 1rem;white-space:pre-wrap}.cases-page a{display:inline-block;margin:.5rem}</style>
