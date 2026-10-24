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
import { useProductSelection } from './queries/product-selection'
import { useRunStore } from './stores/run'
import { useRunStream } from './composables/useRunStream'
import ChatComposer from './components/ChatComposer.vue'
import ProductSelector from './components/ProductSelector.vue'
import ChatThread from './components/ChatThread.vue'
import { useUiStore } from '@/stores/ui'
const ui = useUiStore()
const commandBusy = ref(false)
const route = useRoute(), auth = useAuthStore(), cache = useQueryClient()
const productSelection = useProductSelection()
const cid = computed(() => String(route.params.conversationId || ''))
const conversation = useConversation(cid)
const historyId = computed(() => conversation.data.value?.conversation_id || '')
const { query: history, messages } = useHistory(historyId)
const selectedRun = ref(''), runs = useRunStore()
const run = computed({ get: () => runs.runs[selectedRun.value], set: (value: Run | undefined) => { selectedRun.value = value?.run_id || ''; if (value) runs.snapshot(value) } })
const question = ref(''), error = ref(''), busy = ref(false), restored = ref(false)
const streaming = useRunStream(() => {
  if (auth.user) void cache.invalidateQueries({ queryKey: scopeKey(auth.user.user_id, auth.kb, 'history', cid.value) })
})
let epoch = 0, restoreGeneration = 0, resolvedTarget = ''
function close() { epoch++; restoreGeneration++; resolvedTarget = ''; streaming.close(); runs.forget(selectedRun.value); selectedRun.value = '' }
watch(cid, () => { close(); run.value = undefined; ui.selectedCitation = undefined; ui.evidence = false; error.value = ''; restored.value = false }, { immediate: true })
watch(() => [history.data.value, conversation.data.value, history.isFetching.value, conversation.isFetching.value,
  history.hasNextPage.value, history.error.value, conversation.error.value], async () => {
  const request = ++restoreGeneration, version = epoch, currentId = cid.value
  // 缓存可先显示历史，当前运行须等本次目录和历史刷新完成再选择，不能以旧终态锁住恢复。
  if (!auth.user || !cid.value || !history.data.value || conversation.data.value?.conversation_id !== cid.value
    || history.isFetching.value || conversation.isFetching.value || history.error.value || conversation.error.value) {
    restored.value = false; return
  }
  const rows = messages.value
  const lastRun = conversation.data.value?.active_run_id || (!history.hasNextPage.value ? rows.at(-1)?.run_id : undefined)
  // 同一目标的历史刷新不重置正在流式接收的状态；改变目标才读取新的快照。
  if (lastRun && lastRun === resolvedTarget) { restored.value = true; return }
  restored.value = false
  if (!lastRun) { restored.value = !history.hasNextPage.value; return }
  streaming.close()
  try {
    const value = await api.request<Run>(`/runs/${encodeURIComponent(lastRun)}`)
    if (request !== restoreGeneration || version !== epoch || currentId !== cid.value) return
    if (selectedRun.value !== value.run_id) runs.forget(selectedRun.value)
    run.value = value; resolvedTarget = lastRun; restored.value = true
    if (!terminal(value.state)) subscribe()
  } catch (e) { if (request === restoreGeneration && version === epoch) error.value = (e as Error).message }
}, { immediate: true })
function subscribe() {
  if (run.value) streaming.start(run.value)
}
let pendingRequest: { question: string; products: string; key: string } | undefined
async function send() {
  if (!cid.value || !question.value.trim() || busy.value || !restored.value || !productSelection.ready.value || run.value && !terminal(run.value.state)) return
  busy.value = true; error.value = ''; const version = epoch
  try {
    const products = JSON.stringify(ui.productIds)
    if (!pendingRequest || pendingRequest.question !== question.value || pendingRequest.products !== products) pendingRequest = { question: question.value, products, key: crypto.randomUUID() }
    const value = await api.post<Run>(`/conversations/${cid.value}/runs`, { question: question.value, kb_id: auth.kb, product_ids: ui.productIds, client_request_id: pendingRequest.key })
    if (version !== epoch) return
    restoreGeneration++; run.value = value; question.value = ''; pendingRequest = undefined; restored.value = true; resolvedTarget = value.run_id
    subscribe()
    await Promise.all([
      cache.invalidateQueries({ queryKey: scopeKey(auth.user!.user_id, auth.kb, 'history', cid.value) }),
      cache.invalidateQueries({ queryKey: scopeKey(auth.user!.user_id, auth.kb, 'conversation', cid.value) }),
    ])
  } catch (e) { if (version === epoch) error.value = (e as Error).message } finally { busy.value = false }
}
async function command(name: 'cancel' | 'confirm-product', fields = {}) {
  if (commandBusy.value || !restored.value) return
  commandBusy.value = true
  try { await streaming.command(name, fields) }
  catch (e) { error.value = (e as Error).message }
  finally { commandBusy.value = false }
}
function show(runId: string, citationId: string) { ui.selectedCitation = { runId, citationId }; ui.evidence = true }
window.addEventListener('close-run-streams', close)
onBeforeUnmount(() => { close(); window.removeEventListener('close-run-streams', close) })
const showLive = computed(() => run.value && !messages.value.some(m => m.role === 'assistant' && m.run_id === run.value?.run_id))
</script>
<template><section class="chat-page"><header class="page-heading"><div><p class="eyebrow">技术支持</p><h1>让问题回到设备与依据</h1></div></header>
<div v-if="!cid" class="empty-state"><h2>开始一段设备咨询</h2><p class="muted">在会话目录中选择或新建会话。描述设备型号、现象与已尝试的操作。</p><p>回答会保留资料修订和来源，便于核对。</p></div>
<template v-else><p v-if="history.isPending.value && !conversation.error.value" role="status">正在恢复会话历史…</p><p v-if="conversation.error.value || history.error.value || error || streaming.error.value" role="alert">{{ error || streaming.error.value || conversation.error.value?.message || history.error.value?.message }}</p><p v-if="streaming.connection.value" class="muted" role="status">{{ streaming.connection.value }}</p>
<ChatThread :messages="messages" :run="run" :show-live="!!showLive" :busy="commandBusy" @citation="show" @confirm="command('confirm-product',$event)" />
<button v-if="history.hasNextPage.value" :disabled="history.isFetchingNextPage.value" @click="history.fetchNextPage()">加载更多历史</button>
<p v-if="run && !showLive && terminal(run.state)" role="status">{{ run.state === 'completed' ? '回答完成' : run.state === 'cancelled' ? '已取消' : '回答未完成' }}</p>
<button v-if="run && ['failed','interrupted','cancelled'].includes(run.state)" @click="question = run.question">重新提问</button>
<ProductSelector :model-value="productSelection.selectedId.value" :products="productSelection.options.value" :pending="productSelection.pending.value" :error="productSelection.error.value" :has-more="productSelection.hasMore.value" @update:model-value="productSelection.choose" />
<ChatComposer v-model="question" :busy="busy" :active="!!run && !terminal(run.state)" :disabled="!restored || history.isPending.value || !productSelection.ready.value" @send="send" @cancel="command('cancel')" /></template>
</section></template>
