<!-- 改编shadcn-vue Sidebar.vue de1f76c（MIT）：保留移动端模态/桌面侧栏分支，业务布局和中文标题本地维护。 -->
<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
import Modal from '../dialog/Modal.vue'
defineProps<{ open: boolean; title?: string }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()
const mobile = useMediaQuery('(max-width: 767px)')
</script>
<template><Modal v-if="mobile" :open="open" :title="title || '会话导航'" @update:open="emit('update:open', $event)"><slot /></Modal><aside v-else class="sidebar" data-slot="sidebar"><slot /></aside></template>
