<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import { api } from '@/lib/api/client'
import type { Citation, Conversation, Run, User } from '@/lib/api/types'
import { terminal } from '@/lib/api/types'
import Modal from '@/components/ui/dialog/Modal.vue'
const evidenceOpen = ref(false)
const props = defineProps<{ user: User }>()
const cid = ref(''), question = ref(''), run = ref<Run>(), citation = ref<Citation>(), error = ref(''), busy = ref(false)
let stream: EventSource | undefined
async function create() {
  stream?.close(); run.value = undefined; citation.value = undefined
  try { cid.value = (await api.post<Conversation>('/conversations', { kb_id: props.user.kb_ids[0] })).conversation_id }
  catch (e) { error.value = (e as Error).message }
}
async function send() {
  if (!question.value.trim() || busy.value) return
  busy.value = true; error.value = ''; citation.value = undefined; stream?.close()
  try {
    run.value = await api.post<Run>(`/conversations/${cid.value}/runs`, { question: question.value, kb_id: props.user.kb_ids[0], client_request_id: crypto.randomUUID() })
    question.value = ''; subscribe()
  } catch (e) { error.value = (e as Error).message }
  finally { busy.value = false }
}
function subscribe() {
  stream?.close()
  const rid = run.value!.run_id
  const source = new EventSource(`/api/v1/runs/${rid}/events?after_seq=${run.value!.seq}`)
  stream = source
  for (const name of ['run.started', 'stage.changed', 'product.candidates', 'product.confirmed', 'answer.delta', 'citation.selected', 'run.completed', 'run.failed', 'run.cancelled', 'run.interrupted']) {
    source.addEventListener(name, async event => {
      const value = JSON.parse((event as MessageEvent).data)
      if (run.value?.run_id !== rid || value.run_id !== rid || value.seq <= run.value.seq) return
      run.value.seq = value.seq
      if (name === 'answer.delta') run.value.answer += value.payload.text
      else if (name === 'citation.selected') run.value.citations = value.payload.citations
      else {
        const snapshot = await api.request<Run>(`/runs/${rid}`)
        if (run.value?.run_id === rid && snapshot.seq >= run.value.seq) run.value = snapshot
      }
      if (run.value && terminal(run.value.state)) source.close()
    })
  }
  source.onerror = async () => {
    source.close()
    try {
      const snapshot = await api.request<Run>(`/runs/${rid}`)
      if (run.value?.run_id !== rid) return
      run.value = snapshot
      if (!terminal(snapshot.state)) subscribe()
    } catch (e) { error.value = (e as Error).message }
  }
}
async function command(name: string, fields = {}) {
  try {
    const fresh = await api.request<Run>(`/runs/${run.value!.run_id}`)
    run.value = await api.post<Run>(`/runs/${fresh.run_id}/${name}`, { expected_version: fresh.version, ...fields })
  } catch (e) { error.value = (e as Error).message }
}
async function show(c: Citation) { try { citation.value = await api.request<Citation>(`/runs/${run.value!.run_id}/citations/${c.citation_id}`); evidenceOpen.value = true } catch (e) { error.value = (e as Error).message } }
onBeforeUnmount(() => stream?.close())
</script>
<template><section class="compat-page"><header><h1>技术问答</h1><button @click="create">新建会话</button></header>
<p v-if="error" role="alert">{{ error }}</p><p v-if="!cid">新建会话后，选择适用设备并提问。</p>
<section v-if="run"><p v-if="run.state === 'awaiting_input'">请选择适用型号</p>
<button v-for="p in run.state === 'awaiting_input' ? run.candidates : []" :key="p.product_id" @click="command('confirm-product', { product_ids: [p.product_id] })">{{ p.model }}</button>
<p role="status">{{ run.state === 'completed' ? '回答完成' : run.state === 'cancelled' ? '已取消' : run.stage || run.state }}</p>
<p data-testid="live-answer" style="white-space:pre-wrap">{{ run.answer }}</p>
<button v-for="(c, i) in run.citations" :key="c.citation_id" @click="show(c)">查看引用 {{ i + 1 }}</button>
<button v-if="!terminal(run.state)" @click="command('cancel')">停止</button></section>
<form v-if="cid" @submit.prevent="send"><label>问题<textarea v-model="question" required maxlength="32000" /></label><button :disabled="busy || !!run && !terminal(run.state)">发送</button></form>
<Modal v-model:open="evidenceOpen" title="证据原文"><template v-if="citation"><p data-testid="citation-text">{{ citation.display_text || citation.text }}</p><p>修订：{{ citation.revision_id }}</p></template></Modal>
</section></template>
