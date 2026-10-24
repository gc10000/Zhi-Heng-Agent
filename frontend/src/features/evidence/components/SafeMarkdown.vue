<script setup lang="ts">
import { computed } from 'vue'
import type { Citation } from '@/lib/api/types'
import { renderEvidence } from '../markdown'
const props=withDefaults(defineProps<{text:string;citations?:Citation[];assets?:string[]}>(),{citations:()=>[],assets:()=>[]})
const emit=defineEmits<{citation:[id:string]}>()
const html=computed(()=>renderEvidence(props.text,props.citations,props.assets))
function click(event: MouseEvent) { const button=(event.target as Element).closest<HTMLButtonElement>('button[data-citation-id]');if(button && props.citations.some(c=>c.citation_id===button.dataset.citationId))emit('citation',button.dataset.citationId!) }
function broken(event: Event) { const element=event.target;if(element instanceof HTMLImageElement){element.hidden=true;const note=document.createElement('p');note.textContent='图片暂不可用，请检查资料授权或稍后重试。';note.setAttribute('role','status');element.after(note)} }
</script>
<template><div class="safe-markdown" @click="click" @error.capture="broken" v-html="html" /></template>
