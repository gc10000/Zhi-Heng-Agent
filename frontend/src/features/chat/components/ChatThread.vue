<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Message,Run } from '@/lib/api/types'
import { terminal } from '@/lib/api/types'
import SafeMarkdown from '@/features/evidence/components/SafeMarkdown.vue'
import ProductClarification from './ProductClarification.vue'
import RunProgress from './RunProgress.vue'
import FeedbackForm from '@/features/cases/components/FeedbackForm.vue'
import { useProductSelection } from '../queries/product-selection'
const props=defineProps<{messages:Message[];run?:Run;showLive:boolean;busy:boolean}>()
const emit=defineEmits<{citation:[runId:string,citationId:string];confirm:[value:{product_ids:string[];expected_version:number}];askAgain:[]}>()
const selection = useProductSelection()
const scopeModel = computed(() => selection.options.value.find(p => p.product_id === selection.selectedId.value)?.model || '')
function modelsOf(snapshot?: { product_ids: string[] }) {
  if (!snapshot?.product_ids?.length) return [] as string[]
  return snapshot.product_ids.map(id => selection.options.value.find(p => p.product_id === id)?.model || id)
}
/* T1.5：消息级操作行（有帮助 / 反馈 / 处理草稿）+ 内联反馈表单 */
const feedbackFor = ref(''), helpfulFor = ref<string[]>([]), feedbackDone = ref('')
function toggleFeedback(key: string) { feedbackDone.value=''; feedbackFor.value = feedbackFor.value === key ? '' : key }
function markHelpful(key: string) { if (!helpfulFor.value.includes(key)) helpfulFor.value.push(key) }
function onFeedbackSubmit(value: { run_id: string; citation_ids: string[]; category: string; note: string; client_request_id: string }) {
  window.dispatchEvent(new CustomEvent('zhiheng-feedback', { detail: value }))
  feedbackDone.value = '已保存待审'
  feedbackFor.value = ''
}
const liveKey = computed(() => props.run?.run_id || '')
</script>
<template><div class="chat-thread">
<article v-for="m in messages" :key="m.message_id" :class="['message',m.role]">
  <p class="eyebrow">{{ m.role==='user'?'你':'知衡' }}</p>
  <p v-if="m.role==='assistant' && modelsOf(m.product_snapshot).length" class="scope-badge"><i aria-hidden="true"></i>适用型号：{{ modelsOf(m.product_snapshot).join(' / ') }}</p>
  <SafeMarkdown :text="m.text" :citations="m.citations" :assets="m.citations.flatMap(c=>c.asset_ids)" @citation="emit('citation',m.run_id,$event)" />
  <div class="citation-buttons"><button v-for="(c,i) in m.citations" :key="c.citation_id" @click="emit('citation',m.run_id,c.citation_id)">查看引用 {{ i+1 }}</button></div>
  <div v-if="m.role==='assistant' && m.citations.length" class="ai-foot">
    <button type="button" class="act" :class="{ done: helpfulFor.includes(m.message_id) }" @click="markHelpful(m.message_id)">{{ helpfulFor.includes(m.message_id) ? '✓ 已标记有帮助' : '✓ 有帮助' }}</button>
    <button type="button" class="act" @click="toggleFeedback(m.message_id)">✎ 反馈</button>
    <RouterLink class="act" :to="{path:'/cases',query:{conversation:m.run_id&&messages.length?undefined:undefined,run:m.run_id}}">生成处理草稿 →</RouterLink>
    <span class="stat mono">SOURCES <b>{{ m.citations.length }}</b></span>
    <div v-if="feedbackFor===m.message_id" class="feedback-inline">
      <FeedbackForm :run-id="m.run_id" :citations="m.citations" @submit="onFeedbackSubmit" />
      <p v-if="feedbackDone" role="status" class="feedback-done">{{ feedbackDone }}</p>
    </div>
  </div>
</article>
<article v-if="run && showLive" class="message assistant">
  <ProductClarification :run="run" :busy="busy" @confirm="emit('confirm',$event)" />
  <p v-if="modelsOf(run.product_snapshot).length" class="scope-badge"><i aria-hidden="true"></i>适用型号：{{ modelsOf(run.product_snapshot).join(' / ') }}</p>
  <RunProgress :run="run" @retry="emit('askAgain')" /><SafeMarkdown data-testid="live-answer" :text="run.answer" :citations="run.citations" :assets="run.citations.flatMap(c=>c.asset_ids)" @citation="emit('citation',run.run_id,$event)" /><div class="citation-buttons"><button v-for="(c,i) in run.citations" :key="c.citation_id" @click="emit('citation',run.run_id,c.citation_id)">查看引用 {{ i+1 }}</button></div>
  <div v-if="terminal(run.state) && run.citations.length" class="ai-foot">
    <button type="button" class="act" :class="{ done: helpfulFor.includes(liveKey) }" @click="markHelpful(liveKey)">{{ helpfulFor.includes(liveKey) ? '✓ 已标记有帮助' : '✓ 有帮助' }}</button>
    <button type="button" class="act" @click="toggleFeedback(liveKey)">✎ 反馈</button>
    <span class="stat mono">SOURCES <b>{{ run.citations.length }}</b></span>
    <div v-if="feedbackFor===liveKey" class="feedback-inline">
      <FeedbackForm :run-id="run.run_id" :citations="run.citations" @submit="onFeedbackSubmit" />
      <p v-if="feedbackDone" role="status" class="feedback-done">{{ feedbackDone }}</p>
    </div>
  </div>
</article></div></template>
<style scoped>
.ai-foot { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.act { background: none; border: 1px solid transparent; border-radius: 7px; font-size: 11.5px; color: var(--ink3); padding: 4px 10px; cursor: pointer; text-decoration: none; }
.act:hover { background: var(--panel); color: var(--ink); border-color: var(--line); }
.act.done { color: var(--ok); }
.stat { margin-left: auto; font-size: 9px; color: var(--ink3); }
.stat b { color: var(--accent); font-weight: 600; }
.mono { font-family: ui-monospace, Consolas, monospace; }
.feedback-inline { width: 100%; border: 1px solid var(--line2); border-radius: 10px; padding: 14px; background: var(--panel); margin-top: 8px; display: grid; gap: 8px; }
.feedback-done { color: var(--ok); font-size: .85rem; margin: 0; }
</style>
