<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
import { useUiStore } from '@/stores/ui'
import { useCitation } from '../queries/citations'
import EvidenceCard from './EvidenceCard.vue'
import Modal from '@/components/ui/dialog/Modal.vue'
const ui=useUiStore(), query=useCitation(), mobile=useMediaQuery('(max-width: 767px)')
</script>
<template><component :is="mobile ? Modal : 'aside'" v-bind="mobile ? {open:ui.evidence,title:'证据与来源'} : {class:'evidence-panel'}" @update:open="ui.evidence=$event"><h2 v-if="!mobile">证据与来源</h2><template v-if="ui.selectedCitation"><p v-if="query.isPending.value" role="status">正在读取授权来源…</p><p v-else-if="query.error.value" role="alert">{{ query.error.value.message }}</p><EvidenceCard v-else-if="query.data.value" :key="query.data.value.citation_id" :citation="query.data.value" /><button @click="query.refetch()">重新读取来源</button></template><p v-else class="muted">点击回答中的引用，查看本次使用的原文、图像和资料修订。</p></component></template>
