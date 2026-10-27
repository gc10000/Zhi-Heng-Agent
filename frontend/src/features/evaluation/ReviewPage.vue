<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuery, useInfiniteQuery } from '@tanstack/vue-query'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/lib/api/client'
import type { Page } from '@/lib/api/types'
import type { QuestionResult } from './types'
import ReviewFollowup from './ReviewFollowup.vue'
import type { Followup } from './ReviewFollowup.vue'
const auth=useAuthStore(),route=useRoute(),eid=computed(()=>String(route.params.eid))
const allowed=computed(()=>['maintainer','admin'].includes(auth.user?.role||''))
const scope=computed(()=>[auth.user?.user_id,auth.kb,eid.value]),error=ref(''),busy=ref(false),qid=ref('')
type Score=0|1|2|'unknown'|'not_applicable'
const dimensions={factuality:'事实正确性',citation_support:'引用支持',actionability:'步骤可执行性',image_relevance:'配图相关性'}
const scores=reactive<Record<keyof typeof dimensions,Score>>({factuality:'unknown',citation_support:'unknown',actionability:'unknown',image_relevance:'unknown'})
const kind=ref('assistant'),round=ref(1),attested=ref(false),checked=ref(false),rationale=ref(''),unauthorized=ref(false),wrongModel=ref(false)
const calibrationNote=ref(''),calibrationId=ref(''),gate=ref<{status:string;reasons:string[]}>()
type Review={review_id:string;question_id:string;subject_sha256:string;reviewer_id:string;reviewer_kind:string;round:number;scores:typeof scores;rationale:string}
const reviews=useQuery({queryKey:computed(()=>['scope',...scope.value,'reviews']),enabled:allowed,retry:false,
  queryFn:({signal})=>api.request<{subjects:{question_id:string;subject_sha256:string}[];items:Review[];followups?:Followup[]}>('/experiments/'+encodeURIComponent(eid.value)+'/reviews',{signal})})
const results=useInfiniteQuery({queryKey:computed(()=>['scope',...scope.value,'review-results']),enabled:allowed,retry:false,initialPageParam:'',
  queryFn:({pageParam,signal})=>api.request<Page<QuestionResult>>('/experiments/'+encodeURIComponent(eid.value)+'/results?limit=50'+(pageParam?'&cursor='+encodeURIComponent(pageParam):''),{signal}),getNextPageParam:page=>page.next_cursor||undefined})
const rows=computed(()=>results.data.value?.pages.flatMap(p=>p.items)||[]),current=computed(()=>rows.value.find(q=>q.question_id===qid.value))
const savedIdentity=ref('')
const reviewIdentity=computed(()=>JSON.stringify([eid.value,qid.value,kind.value,round.value,auth.user?.user_id,reviews.data.value?.subjects.find(s=>s.question_id===qid.value)?.subject_sha256]))
const alreadySaved=computed(()=>savedIdentity.value===reviewIdentity.value||!!reviews.data.value?.items.some(r=>
  r.question_id===qid.value&&r.round===round.value&&r.reviewer_kind===kind.value&&r.reviewer_id===auth.user?.user_id&&
  r.subject_sha256===reviews.data.value?.subjects.find(s=>s.question_id===qid.value)?.subject_sha256))
const originalHuman=computed(()=>kind.value==='human'?reviews.data.value?.items.find(r=>r.question_id===qid.value&&r.round===round.value&&r.reviewer_kind==='human'&&r.reviewer_id===auth.user?.user_id&&r.subject_sha256===reviews.data.value?.subjects.find(s=>s.question_id===qid.value)?.subject_sha256):undefined)
const priorFollowup=computed(()=>reviews.data.value?.followups?.find(f=>f.review_id===originalHuman.value?.review_id))
const hasImages=computed(()=>!!current.value?.result.citations?.some(s=>s.asset_sha256))
watch(rows,()=>{if(!qid.value)qid.value=rows.value[0]?.question_id||''})
let epoch=0,pending:{identity:string;key:string}|undefined
watch(scope,()=>{epoch++;savedIdentity.value='';qid.value='';error.value='';gate.value=undefined;calibrationId.value='';pending=undefined;reset()})
function reset(){rationale.value='';attested.value=false;checked.value=false;unauthorized.value=false;wrongModel.value=false;for(const key of Object.keys(dimensions) as (keyof typeof dimensions)[])scores[key]='unknown'}
watch(qid,reset)
async function perform(action:()=>Promise<void>){if(busy.value)return;const generation=epoch;busy.value=true;error.value='';try{await action()}catch(e){if(generation===epoch)error.value=(e as Error).message}finally{busy.value=false}}
async function submit(){const subject=reviews.data.value?.subjects.find(s=>s.question_id===qid.value);if(!subject||alreadySaved.value)return;const generation=epoch,savingIdentity=reviewIdentity.value
  const data={question_id:qid.value,subject_sha256:subject.subject_sha256,round:round.value,reviewer_kind:kind.value,human_attested:kind.value==='human'&&attested.value,source_checked:checked.value,scores:{...scores},critical_errors:[...(unauthorized.value?['unauthorized']:[]),...(wrongModel.value?['wrong_model']:[])],rationale:rationale.value}
  const identity=JSON.stringify(data);if(pending?.identity!==identity)pending={identity,key:crypto.randomUUID()}
  await api.post('/experiments/'+encodeURIComponent(eid.value)+'/reviews',{...data,client_request_id:pending.key})
  if(generation===epoch){savedIdentity.value=savingIdentity;pending=undefined;await reviews.refetch()}}
async function calibrate(){const generation=epoch;const row=await api.post<{calibration_id:string}>('/experiments/'+encodeURIComponent(eid.value)+'/calibrations',{client_request_id:crypto.randomUUID(),rationale:calibrationNote.value});if(generation===epoch)calibrationId.value=row.calibration_id}
async function checkGate(){const generation=epoch;const result=await api.request<{status:string;reasons:string[]}>('/experiments/'+encodeURIComponent(eid.value)+'/release-gate?calibration_id='+encodeURIComponent(calibrationId.value));if(generation===epoch)gate.value=result}
</script>
<template><section class="review-page"><h1>答案审阅</h1><RouterLink to="/evaluations">返回实验</RouterLink><p>实验 {{eid}}。0 错误、1 部分支持、2 完整支持。无法核对标未知；人工须本人对照原件。保存后不可覆盖，复核请选第二轮。</p>
<p v-if="!allowed" role="status">当前角色没有评测维护权限。</p><template v-else>
<p v-if="error||reviews.error.value||results.error.value" role="alert">{{error||reviews.error.value?.message||results.error.value?.message}}</p>
<label>待审问题<select v-model="qid" aria-label="待审问题"><option v-for="row in rows" :key="row.question_id" :value="row.question_id">{{row.question_id}} · {{row.question}}</option></select></label>
<button v-if="results.hasNextPage.value" :disabled="results.isFetchingNextPage.value" @click="results.fetchNextPage()">更多问题</button>
<article v-if="current"><h2>{{current.question}}</h2><p v-if="current.result.behavior==='clarify'" role="status">本轮请求确认设备型号，未生成答案。请核对澄清行为是否符合问题；无法确认的维度保留未知。</p><p v-else-if="!current.result.answer" role="status">当前结果没有答案正文，请核对运行状态与原始资料，无法确认的维度保留未知。</p><p class="answer">{{current.result.answer}}</p><ul><li v-for="(source,index) in current.result.citations" :key="index">原件 SHA256 {{source.document_sha256}} · 物理页 {{source.page??'未知'}} · 图片 {{source.asset_sha256??'无图像标识'}}</li></ul></article>
<aside v-if="current" aria-label="审阅判定依据"><h2>审阅判定依据</h2>
<h3>步骤是否适用</h3><p>先按题意判断是否要求执行配置、排查或操作。兼容性、参数事实判断题若不需要操作步骤，可以说明理由后选择不适用；不能因为未找到步骤就自动跳过。要求操作时，核对前提、顺序、命令与风险，再评0/1/2；尚未核实保留未知。</p>
<h3>配图用途与相关性</h3><p>逐张核对原件页和图像：图片是否属于当前型号、说明什么、与问题或答案哪句话相关。图片直接展示且便于理解题目涉及内容评2，只有次要/间接关系评1，无关或误导评0；不要把图像存在或哈希一致当作正确性证明。有配图来源不能标不适用，尚未看图保留未知。下列标识用于对应原件/图像，请结合来源工作台或本机对照页核对。</p></aside>
<form v-if="current" @submit.prevent="perform(submit)">
<label>审阅身份<select v-model="kind" aria-label="审阅身份"><option value="assistant">独立助手辅助审阅</option><option value="model">模型辅助评分</option><option value="human">人工本人核对</option></select></label>
<label>复核轮次<select v-model.number="round" aria-label="复核轮次"><option :value="1">第一轮</option><option :value="2">第二轮</option></select></label>
<p v-if="alreadySaved" role="status">{{qid}} 第{{round}}轮审阅已保存，无需再次提交。历史记录见下方；另一轮须重新核对后单独保存。</p>
<label v-for="(name,key) in dimensions" :key="key">{{name}}<select v-model="scores[key]" :aria-label="name"><option value="unknown">未知</option><option :value="0">0 · 错误</option><option :value="1">1 · 部分支持</option><option :value="2">2 · 完整支持</option><option v-if="key!=='factuality'" value="not_applicable">不适用（需说明）</option></select></label>
<label><input v-model="checked" type="checkbox">已核对原始资料与来源</label><label v-if="kind==='human'"><input v-model="attested" type="checkbox">确认我是执行本次原件核对的人工本人</label>
<label><input v-model="unauthorized" type="checkbox">存在越权关键错误</label><label><input v-model="wrongModel" type="checkbox">存在型号关键错误</label>
<label>核对依据或未知原因<textarea v-model="rationale" required maxlength="4000"/></label>
<button :disabled="busy||alreadySaved||!rationale.trim()||(kind==='human'&&(!attested||!checked))">保存本轮审阅</button></form>
<ReviewFollowup v-if="originalHuman&&Object.values(originalHuman.scores).includes('unknown')" :key="originalHuman.review_id+originalHuman.subject_sha256" :eid="eid" :review="originalHuman" :prior="priorFollowup" :has-images="hasImages" @saved="reviews.refetch()"/>
<h2>不可变审阅记录</h2><ul><li v-for="row in reviews.data.value?.items.filter(r=>r.question_id===qid)" :key="row.review_id">{{row.reviewer_kind}} · {{row.reviewer_id}} · 第{{row.round}}轮 · {{JSON.stringify(row.scores)}}<p>{{row.rationale}}</p></li></ul>
<h2>基线校准与质量门槛</h2><p>先在基线完成两轮人工核对并冻结零退化门槛，再创建候选实验。关键越权和型号错误零容忍；该检查不自动发布知识或授权下一阶段。</p>
<label>基线校准说明<textarea v-model="calibrationNote" maxlength="4000"/></label><button :disabled="busy||!calibrationNote.trim()" @click="perform(calibrate)">冻结基线门槛</button>
<label>校准 ID<input v-model="calibrationId"></label><button :disabled="busy||!calibrationId" @click="perform(checkGate)">检查当前候选</button><p v-if="gate" role="status">{{{passed:'通过门槛',pending:'待审或不可比较',blocked:'阻止发布'}[gate.status]||gate.status}} · {{gate.reasons.join('、')}}</p>
</template></section></template>
<style scoped>.review-page{padding:1.5rem;max-width:70rem;overflow-wrap:anywhere}h1{font-size:1.7rem}h2{font-size:1.2rem;margin:1rem 0}p{line-height:1.7;margin:.6rem 0}label{display:grid;gap:.4rem;margin:.7rem 0}input[type=checkbox]{justify-self:start}select,textarea,input{max-width:100%;min-width:0}button{margin:.4rem}.answer{white-space:pre-wrap}</style>
