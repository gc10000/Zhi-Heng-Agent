<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useQueryClient } from '@tanstack/vue-query'
import { api } from '@/lib/api/client'
import { useAuthStore } from '@/stores/auth'
import type { Citation, Run } from '@/lib/api/types'
import { terminal } from '@/lib/api/types'
import { useHistory, useConversation } from './queries/conversations'
import { scopeKey } from './queries/history'
import Modal from '@/components/ui/dialog/Modal.vue'
import { useRunStore } from './stores/run'
import { useRunStream } from './composables/useRunStream'
import ChatComposer from './components/ChatComposer.vue'
const route = useRoute(), auth = useAuthStore(), cache = useQueryClient()
const cid = computed(() => String(route.params.conversationId || ''))
const conversation = useConversation(cid)
const historyId = computed(() => conversation.data.value?.conversation_id || '')
const { query: history, messages } = useHistory(historyId)
const selectedRun = ref(''), runs = useRunStore()
const run = computed({ get: () => runs.runs[selectedRun.value], set: (value: Run | undefined) => { selectedRun.value = value?.run_id || ''; if (value) runs.snapshot(value) } })
const question = ref(''), error = ref(''), busy = ref(false), citation = ref<Citation>(), evidence = ref(false), restored = ref(false)
const streaming = useRunStream(() => {
  if (auth.user) void cache.invalidateQueries({ queryKey: scopeKey(auth.user.user_id, auth.kb, 'history', cid.value) })
})
let epoch = 0
function close() { epoch++; streaming.close(); runs.forget(selectedRun.value); selectedRun.value = '' }
watch(cid, () => { close(); run.value = undefined; citation.value = undefined; evidence.value = false; error.value = ''; restored.value = false }, { immediate: true })
watch(() => [history.data.value, conversation.data.value], async ([data]) => {
  if (!data || restored.value || !cid.value) return
  const version = epoch, currentId = cid.value
  const rows = messages.value
  // 等待历史全部页到齐，再恢复末轮快照；先清空旧会话运行，拒绝迟到响应。
  const lastRun = conversation.data.value?.active_run_id || (!history.hasNextPage.value ? rows.at(-1)?.run_id : undefined)
  if (!lastRun) { restored.value = !history.hasNextPage.value; return }
  try { const value = await api.request<Run>(`/runs/${lastRun}`); if (version !== epoch || currentId !== cid.value) return; run.value = value; restored.value = true; if (!terminal(value.state)) subscribe() }
  catch (e) { if (version === epoch) error.value = (e as Error).message }
}, { immediate: true })
function subscribe() {
  if (run.value) streaming.start(run.value)
}
let pendingRequest: { question: string; key: string } | undefined
async function send() {
  if (!cid.value || !question.value.trim() || busy.value || !restored.value || run.value && !terminal(run.value.state)) return
  busy.value = true; error.value = ''; const version = epoch
  try {
    if (!pendingRequest || pendingRequest.question !== question.value) pendingRequest = { question: question.value, key: crypto.randomUUID() }
    const value = await api.post<Run>(`/conversations/${cid.value}/runs`, { question: question.value, kb_id: auth.kb, product_ids: [], client_request_id: pendingRequest.key })
    if (version !== epoch) return
    run.value = value; question.value = ''; pendingRequest = undefined; restored.value = true
    await cache.invalidateQueries({ queryKey: scopeKey(auth.user!.user_id, auth.kb, 'history', cid.value) }); subscribe()
  } catch (e) { if (version === epoch) error.value = (e as Error).message } finally { busy.value = false }
}
async function command(name: 'cancel' | 'confirm-product', fields = {}) {
  try { await streaming.command(name, fields) }
  catch (e) { error.value = (e as Error).message }
}
async function show(runId: string, c: Citation) { try { citation.value = await api.request<Citation>(`/runs/${runId}/citations/${c.citation_id}`); evidence.value = true } catch (e) { error.value = (e as Error).message } }
window.addEventListener('close-run-streams', close)
onBeforeUnmount(() => { close(); window.removeEventListener('close-run-streams', close) })
const showLive = computed(() => run.value && !messages.value.some(m => m.role === 'assistant' && m.run_id === run.value?.run_id))
</script>
<template><section class="chat-page"><header class="page-heading"><div><p class="eyebrow">技术支持</p><h1>让问题回到设备与依据</h1></div></header>
<div v-if="!cid" class="empty-state"><h2>开始一段设备咨询</h2><p class="muted">在会话目录中选择或新建会话。描述设备型号、现象与已尝试的操作。</p><p>回答会保留资料修订和来源，便于核对。</p></div>
<template v-else><p v-if="history.isPending.value && !conversation.error.value" role="status">正在恢复会话历史…</p><p v-if="conversation.error.value || history.error.value || error || streaming.error.value" role="alert">{{ error || streaming.error.value || conversation.error.value?.message || history.error.value?.message }}</p><p v-if="streaming.connection.value" class="muted" role="status">{{ streaming.connection.value }}</p>
<div class="chat-thread"><article v-for="m in messages" :key="m.message_id" :class="['message',m.role]"><p class="eyebrow">{{ m.role === 'user' ? '你' : '知衡' }}</p><div class="answer-text">{{ m.text }}</div><div class="citation-buttons"><button v-for="(c,i) in m.citations" :key="c.citation_id" @click="show(m.run_id,c)">查看引用 {{ i + 1 }}</button></div></article>
<article v-if="run && showLive" class="message assistant"><p v-if="run.state === 'awaiting_input'">请选择适用型号</p><div class="candidate-list"><button v-for="p in run.state === 'awaiting_input' ? run.candidates : []" :key="p.product_id" @click="command('confirm-product',{product_ids:[p.product_id]})">{{ p.model }}</button></div><p role="status">{{ run.state === 'completed' ? '回答完成' : run.state === 'cancelled' ? '已取消' : run.state === 'failed' ? '回答失败，部分内容仅供核对' : run.stage || run.state }}</p><div data-testid="live-answer" class="answer-text">{{ run.answer }}</div><button v-for="(c,i) in run.citations" :key="c.citation_id" @click="show(run.run_id,c)">查看引用 {{ i + 1 }}</button></article></div>
<button v-if="history.hasNextPage.value" :disabled="history.isFetchingNextPage.value" @click="history.fetchNextPage()">加载更多历史</button>
<p v-if="run && !showLive && terminal(run.state)" role="status">{{ run.state === 'completed' ? '回答完成' : run.state === 'cancelled' ? '已取消' : '回答未完成' }}</p>
<button v-if="run && ['failed','interrupted','cancelled'].includes(run.state)" @click="question = run.question">重新提问</button>
<ChatComposer v-model="question" :busy="busy" :active="!!run && !terminal(run.state)" :disabled="!restored || history.isPending.value" @send="send" @cancel="command('cancel')" /></template>
<Modal v-model:open="evidence" title="证据原文"><template v-if="citation"><p data-testid="citation-text">{{ citation.display_text || citation.text }}</p><p>修订：{{ citation.revision_id }}</p></template></Modal>
</section></template>
