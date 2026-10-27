<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { api } from '@/lib/api/client'
type Score=0|1|2|'unknown'|'not_applicable'
type Dimension='factuality'|'citation_support'|'actionability'|'image_relevance'
export interface Followup { followup_id:string;review_id:string;resolutions:Partial<Record<Dimension,{score:Score;evidence:string}>> }
const props=defineProps<{review:{review_id:string;subject_sha256:string;scores:Record<Dimension,Score>};eid:string;prior?:Followup;hasImages:boolean}>()
const emit=defineEmits<{saved:[]}>()
const names:Record<Dimension,string>={factuality:'事实正确性',citation_support:'引用支持',actionability:'步骤可执行性',image_relevance:'配图相关性'}
const unknown=computed(()=>(Object.keys(names) as Dimension[]).filter(key=>props.review.scores[key]==='unknown'))
const choices=reactive<Partial<Record<Dimension,Exclude<Score,'unknown'>|''>>>({})
const evidence=reactive<Partial<Record<Dimension,string>>>({})
const checked=ref(false),attested=ref(false),busy=ref(false),error=ref(''),saved=ref(false)
const unauthorized=ref(false),wrongModel=ref(false)
const ready=computed(()=>unknown.value.length>0&&checked.value&&attested.value&&unknown.value.every(key=>choices[key]!==undefined&&choices[key]!==''&&!!evidence[key]?.trim()))
let pending:{identity:string;key:string}|undefined,active=true
onBeforeUnmount(()=>{active=false})
async function save(){
  if(!ready.value||busy.value||saved.value||props.prior)return
  busy.value=true;error.value=''
  const resolutions=Object.fromEntries(unknown.value.map(key=>[key,{score:choices[key],evidence:evidence[key]}]))
  const data={subject_sha256:props.review.subject_sha256,human_attested:attested.value,source_checked:checked.value,resolutions,
    critical_errors:[...(unauthorized.value?['unauthorized']:[]),...(wrongModel.value?['wrong_model']:[])]}
  const identity=JSON.stringify(data)
  if(pending?.identity!==identity)pending={identity,key:crypto.randomUUID()}
  try{
    await api.post('/experiments/'+encodeURIComponent(props.eid)+'/reviews/'+encodeURIComponent(props.review.review_id)+'/followups',{...data,client_request_id:pending.key})
    if(active){saved.value=true;emit('saved')}
  }catch(e){if(active)error.value=(e as Error).message}finally{if(active)busy.value=false}
}
</script>
<template><section aria-label="未知项追加复核" class="followup">
<h2>未知项追加复核</h2>
<p>保留原审阅，只追加该轮全部未知项的结论。必须由原审核者本人重新核对并逐项说明依据；确定分数及原关键错误保留。尚无法确定时请暂不提交，原未知保持有效。</p>
<p v-if="prior||saved" role="status">本轮追加复核已保存，原始审阅仍保留。该轮不能再次覆盖；另一轮须独立核对。</p>
<ul v-if="prior"><li v-for="(value,key) in prior.resolutions" :key="key">{{names[key]}}：{{value?.score}}<p>{{value?.evidence}}</p></li></ul>
<form v-else-if="!saved" @submit.prevent="save">
<template v-for="key in unknown" :key="key">
<label>{{names[key]}}复核结论<select v-model="choices[key]" :aria-label="'复核结论：'+names[key]" required>
<option value="" disabled>请独立选择结论</option><option :value="0">0 · 错误</option><option :value="1">1 · 部分支持</option><option :value="2">2 · 完整支持</option>
<option v-if="key!=='factuality'&&!(key==='image_relevance'&&hasImages)" value="not_applicable">不适用（需说明）</option></select></label>
<label>{{names[key]}}复核依据<textarea v-model="evidence[key]" :aria-label="'复核依据：'+names[key]" required maxlength="4000"/></label>
</template>
<label><input v-model="checked" type="checkbox">本人已重新核对原件与上述依据</label>
<label><input v-model="attested" type="checkbox">确认由原审核者本人追加复核</label>
<label><input v-model="unauthorized" type="checkbox">本次发现越权关键错误</label><label><input v-model="wrongModel" type="checkbox">本次发现型号关键错误</label>
<p v-if="error" role="alert">{{error}}</p><button :disabled="busy||!ready">保存追加复核</button>
</form></section></template>
<style scoped>.followup{margin:1rem 0;padding:1rem;border:1px solid var(--border,#aaa)}label{display:grid;gap:.4rem;margin:.7rem 0}input[type=checkbox]{justify-self:start}p{margin:.6rem 0;line-height:1.7}textarea,select{max-width:100%}</style>
