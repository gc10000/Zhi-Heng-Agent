<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useRouter } from 'vue-router'
import { useConversations } from '../queries/conversations'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { api } from '@/lib/api/client'
import type { Conversation } from '@/lib/api/types'
import Modal from '@/components/ui/dialog/Modal.vue'
const auth = useAuthStore(), ui = useUiStore(), cache = useQueryClient(), router = useRouter()
const props = defineProps<{ keyword?: string }>()
const query = useConversations(), error = ref(''), editing = ref<Conversation>(), title = ref('')
const items = computed(() => {
  const all = query.data.value?.pages.flatMap(p => p.items).filter(c => c.kb_id === auth.kb && !c.archived) || []
  const kw = (props.keyword || '').trim().toLowerCase()
  return kw ? all.filter(c => c.title.toLowerCase().includes(kw)) : all
})
async function update(c: Conversation, fields: object) {
  try { await api.request(`/conversations/${c.conversation_id}`, { method: 'PATCH', body: JSON.stringify({ expected_version: c.version, ...fields }) }); await query.refetch(); editing.value = undefined; if ('archived' in fields) await router.push('/chat') }
  catch (e) { error.value = (e as Error).message; await query.refetch() }
}
</script>
<template><section class="conversation-list">
<p v-if="query.isPending.value" role="status">正在加载会话…</p><p v-if="query.error.value || error" role="alert">{{ error || query.error.value?.message }}</p>
<p v-if="!query.isPending.value && !items.length" class="muted">{{ (keyword || '').trim() ? '没有匹配的会话。' : '这个知识范围还没有会话。' }}</p>
<div v-for="c in items" :key="c.conversation_id" class="conversation-row"><RouterLink :to="'/chat/' + c.conversation_id" @click="ui.menu = false">{{ c.title }}</RouterLink><button :aria-label="'管理会话 ' + c.title" @click="editing = c; title = c.title">⋯</button></div>
<button v-if="query.hasNextPage.value" :disabled="query.isFetchingNextPage.value" @click="query.fetchNextPage()">更多会话</button>
<Modal :open="!!editing" title="管理会话" @update:open="!$event && (editing = undefined)"><form v-if="editing" class="form-grid" @submit.prevent="update(editing, { title })"><label>会话名称<input v-model="title" required maxlength="200"></label><button class="primary">保存名称</button><button type="button" @click="update(editing, { archived: true })">归档会话</button></form></Modal>
</section></template>
