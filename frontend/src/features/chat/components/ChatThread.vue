<script setup lang="ts">
import type { Message,Run } from '@/lib/api/types'
import SafeMarkdown from '@/features/evidence/components/SafeMarkdown.vue'
import ProductClarification from './ProductClarification.vue'
import RunProgress from './RunProgress.vue'
defineProps<{messages:Message[];run?:Run;showLive:boolean;busy:boolean}>()
const emit=defineEmits<{citation:[runId:string,citationId:string];confirm:[value:{product_ids:string[];expected_version:number}]}>()
</script>
<template><div class="chat-thread"><article v-for="m in messages" :key="m.message_id" :class="['message',m.role]"><p class="eyebrow">{{ m.role==='user'?'你':'知衡' }}</p><SafeMarkdown :text="m.text" :citations="m.citations" :assets="m.citations.flatMap(c=>c.asset_ids)" @citation="emit('citation',m.run_id,$event)" /><div class="citation-buttons"><button v-for="(c,i) in m.citations" :key="c.citation_id" @click="emit('citation',m.run_id,c.citation_id)">查看引用 {{ i+1 }}</button></div></article>
<article v-if="run && showLive" class="message assistant"><ProductClarification :run="run" :busy="busy" @confirm="emit('confirm',$event)" /><RunProgress :run="run" /><SafeMarkdown data-testid="live-answer" :text="run.answer" :citations="run.citations" :assets="run.citations.flatMap(c=>c.asset_ids)" @citation="emit('citation',run.run_id,$event)" /><div class="citation-buttons"><button v-for="(c,i) in run.citations" :key="c.citation_id" @click="emit('citation',run.run_id,c.citation_id)">查看引用 {{ i+1 }}</button></div></article></div></template>
