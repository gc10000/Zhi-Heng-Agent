<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery, useInfiniteQuery } from '@tanstack/vue-query'
import { api } from '@/lib/api/client'
import type { Page } from '@/lib/api/types'
import { useAuthStore } from '@/stores/auth'
import type { EvalSet, CatalogSet, Experiment, QuestionResult } from './types'
const auth=useAuthStore(),allowed=computed(()=>['maintainer','admin'].includes(auth.user?.role||''))
const scope=computed(()=>[auth.user?.user_id,auth.kb]),enabled=computed(()=>allowed.value&&!!auth.kb)
const error=ref(''),busy=ref(false),selectedSet=ref(''),config=ref(''),baseline=ref(''),experimentId=ref(''),catalogChoice=ref('')
let epoch=0,pending:{identity:string;key:string}|undefined
const sets=useQuery({queryKey:computed(()=>['scope',...scope.value,'eval-sets']),enabled,retry:false,queryFn:({signal})=>api.request<Page<EvalSet>>('/eval-sets?kb_id='+encodeURIComponent(auth.kb),{signal})})
const catalog=useQuery({queryKey:computed(()=>['scope',...scope.value,'eval-catalog']),enabled,retry:false,queryFn:({signal})=>api.request<Page<CatalogSet>>('/eval-catalog?kb_id='+encodeURIComponent(auth.kb),{signal})})
const experiments=useQuery({queryKey:computed(()=>['scope',...scope.value,'experiments']),enabled,retry:false,queryFn:({signal})=>api.request<Page<Experiment>>('/experiments?kb_id='+encodeURIComponent(auth.kb),{signal})})
const set=computed(()=>sets.data.value?.items.find(x=>x.eval_set_id+'/'+x.version===selectedSet.value))
watch(set,()=>{config.value=set.value?.configs[0]?.id+'/'+set.value?.configs[0]?.version;baseline.value=''})
watch(scope,()=>{epoch++;error.value='';selectedSet.value='';config.value='';baseline.value='';experimentId.value='';catalogChoice.value='';pending=undefined})
const current=useQuery({queryKey:computed(()=>['scope',...scope.value,'experiment',experimentId.value]),enabled:computed(()=>enabled.value&&!!experimentId.value),retry:false,
  queryFn:({signal})=>api.request<Experiment>('/experiments/'+encodeURIComponent(experimentId.value),{signal}),
  refetchInterval:query=>['pending','running','cancel_requested'].includes(query.state.data?.state||'')?3000:false})
const results=useInfiniteQuery({queryKey:computed(()=>['scope',...scope.value,'experiment-results',experimentId.value,current.data.value?.version]),initialPageParam:'',enabled:computed(()=>enabled.value&&!!experimentId.value),retry:false,
  queryFn:({pageParam,signal})=>api.request<Page<QuestionResult>>('/experiments/'+encodeURIComponent(experimentId.value)+'/results?limit=20'+(pageParam?'&cursor='+encodeURIComponent(pageParam):''),{signal}),getNextPageParam:page=>page.next_cursor||undefined})
const rows=computed(()=>results.data.value?.pages.flatMap(p=>p.items)||[])
const baselines=computed(()=>experiments.data.value?.items.filter(x=>x.state==='completed'&&x.eval_set_id===set.value?.eval_set_id&&x.eval_set_version===set.value?.version)||[])
const states:Record<string,string>={pending:'等待独立评测队列',running:'正在评测',cancel_requested:'正在等待当前题边界取消',cancelled:'已取消',completed:'已完成',failed:'失败',incomplete:'部分完成'}
async function perform(action:()=>Promise<void>){if(busy.value)return;const generation=epoch;busy.value=true;error.value='';try{await action()}catch(e){if(generation===epoch)error.value=(e as Error).message}finally{busy.value=false}}
async function register(){const item=catalog.data.value?.items.find(x=>x.id+'/'+x.version===catalogChoice.value);if(!item)return;const generation=epoch;await api.post('/eval-sets',{kb_id:auth.kb,eval_set_id:item.id,version:item.version});if(generation===epoch)await sets.refetch()}
async function create(){if(!set.value)return;const cfg=set.value.configs.find(c=>c.id+'/'+c.version===config.value);if(!cfg)return;const generation=epoch;
  const data={kb_id:auth.kb,eval_set_id:set.value.eval_set_id,eval_set_version:set.value.version,config_id:cfg.id,config_version:cfg.version,baseline_experiment_id:baseline.value||null}
  const identity=JSON.stringify(data);if(pending?.identity!==identity)pending={identity,key:crypto.randomUUID()}
  const value=await api.post<Experiment>('/experiments',{...data,client_request_id:pending.key});if(generation===epoch){experimentId.value=value.experiment_id;pending=undefined;await experiments.refetch();await current.refetch()}}
async function change(action:string){const row=current.data.value;if(!row)return;const generation=epoch;await api.post('/experiments/'+encodeURIComponent(row.experiment_id)+'/'+action,{expected_version:row.version});if(generation===epoch){await current.refetch();await experiments.refetch()}}
const accounting=computed(()=>current.data.value?.summary?.accounting)
</script>
<template><section class="evaluation-page"><h1>评测实验</h1><p>固定版本开发集实验。来源命中不等于答案正确；未审核标签不计标准质量分。</p>
<p v-if="!allowed" role="status">当前角色没有评测维护权限。</p>
<template v-else>
<p v-if="error||sets.error.value||catalog.error.value||experiments.error.value||current.error.value||results.error.value" role="alert">{{error||sets.error.value?.message||catalog.error.value?.message||experiments.error.value?.message||current.error.value?.message||results.error.value?.message}}</p>
<section aria-label="题集登记"><h2>登记受控题集</h2><label>可登记版本<select v-model="catalogChoice"><option value="">请选择服务端版本</option><option v-for="item in catalog.data.value?.items" :key="item.id+'/'+item.version" :value="item.id+'/'+item.version">{{item.id}} / {{item.version}}</option></select></label><button :disabled="busy||!catalogChoice" @click="perform(register)">登记为我的私有题集</button></section>
<form @submit.prevent="perform(create)"><h2>新实验</h2><label>题集版本<select v-model="selectedSet" aria-label="题集版本"><option value="">请选择已登记题集</option><option v-for="item in sets.data.value?.items" :key="item.eval_set_id+'/'+item.version" :value="item.eval_set_id+'/'+item.version">{{item.eval_set_id}} / {{item.version}}</option></select></label>
<p v-if="set">开发题 {{set.dev_count}} · 标准标签合资格 {{set.review_eligible_count}}；heldout 不从工作台执行。</p>
<label>配置版本<select v-model="config"><option value="">请选择配置</option><option v-for="item in set?.configs" :key="item.id+'/'+item.version" :value="item.id+'/'+item.version">{{item.id}} / {{item.version}} · {{item.strategy}}</option></select></label>
<label>对比基线<select v-model="baseline"><option value="">不对比</option><option v-for="item in baselines" :key="item.experiment_id" :value="item.experiment_id">{{item.experiment_id}}</option></select></label>
<button :disabled="busy||!set||!config" type="submit">创建开发集实验</button></form>
<section aria-label="实验列表"><h2>我的实验</h2><p v-if="!experiments.isPending.value&&!experiments.data.value?.items.length">尚无实验。不会显示模拟指标。</p><ul><li v-for="item in experiments.data.value?.items" :key="item.experiment_id"><button :aria-label="'查看 '+item.experiment_id" @click="experimentId=item.experiment_id">{{item.experiment_id}}</button> · {{states[item.state]||item.state}}</li></ul><button @click="experiments.refetch()">刷新实验列表</button></section>
<article v-if="current.data.value" aria-label="实验详情"><h2>{{current.data.value.experiment_id}}</h2><RouterLink v-if="current.data.value.state==='completed'" :to="'/evaluations/reviews/'+encodeURIComponent(current.data.value.experiment_id)">审阅答案与质量门槛</RouterLink><p role="status">{{states[current.data.value.state]||current.data.value.state}}</p><p>尝试 {{current.data.value.attempt}} · 完成 {{current.data.value.completed??'未采集'}} / {{current.data.value.selected_questions??'未采集'}}</p><p v-if="current.data.value.error" role="alert">{{current.data.value.error.code}}</p>
<button v-if="['pending','running'].includes(current.data.value.state)" :disabled="busy" @click="perform(()=>change('cancel'))">取消实验</button><button v-if="current.data.value.state==='failed'&&current.data.value.retryable" :disabled="busy" @click="perform(()=>change('retry'))">重试失败实验</button><button @click="current.refetch();results.refetch()">刷新实验详情</button>
<p>精确成本：{{accounting?.exact_cost==null?'未采集':accounting.exact_cost+' '+accounting.currency}}</p><p>输入 token：{{accounting?.input_tokens??'未采集'}} · 输出 token：{{accounting?.output_tokens??'未采集'}}</p>
<p v-if="!results.isPending.value&&!rows.length">尚无可见题级结果。</p>
<section v-for="row in rows" :key="row.question_id" class="question-result"><h3>{{row.question_id}} · {{row.question}}</h3><p>{{states[row.status]||row.status}} · {{row.category}} <span v-if="row.failure_stage">失败阶段 {{row.failure_stage}}</span></p><p class="answer">{{row.result.answer}}</p><p>答案语义正确性：{{row.metrics?.human_answer_correctness==null?'未审核':row.metrics.human_answer_correctness}}</p>
<ul><li v-for="(source,index) in row.result.citations" :key="index">原件 SHA256 {{source.document_sha256}} · 物理页 {{source.page??'未知'}} <span v-if="source.asset_sha256">· 图片 SHA256 {{source.asset_sha256}}</span></li></ul>
<details v-if="row.result.retrieval_candidates"><summary>实际候选来源与指标</summary><pre>{{JSON.stringify({candidates:row.result.retrieval_candidates,metrics:row.metrics?.retrieval},null,2)}}</pre></details>
<aside v-if="row.baseline"><h4>基线回答</h4><p class="answer">{{row.baseline.answer??'无结果'}}</p><p>答案文本变化：{{row.difference?.answer_changed==null?'不可比较':row.difference.answer_changed?'有变化（须审核质量）':'无变化'}}</p></aside></section>
<button v-if="results.hasNextPage.value" :disabled="results.isFetchingNextPage.value" @click="results.fetchNextPage()">更多题级结果</button></article>
</template></section></template>
<style scoped>.evaluation-page{padding:1.5rem;max-width:74rem;min-width:0;overflow-wrap:anywhere}.evaluation-page h1{font-size:1.7rem}.evaluation-page h2{font-size:1.2rem;margin:1rem 0}.evaluation-page p{margin:.6rem 0;line-height:1.7}.evaluation-page label{display:grid;gap:.4rem;margin:.7rem 0}.evaluation-page select{min-width:0;max-width:100%}.evaluation-page section,.evaluation-page form{margin:1rem 0}.evaluation-page button{margin:.3rem .5rem .3rem 0}.question-result{border-top:1px solid #cbd5e1;padding:1rem 0}.answer,pre{white-space:pre-wrap;overflow-wrap:anywhere}pre{max-height:24rem;overflow:auto}aside{border-left:3px solid #0f766e;padding-left:1rem}</style>
