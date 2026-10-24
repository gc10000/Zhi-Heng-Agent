<script setup lang="ts">
import { DialogPortal, DialogOverlay, DialogContent, DialogTitle, DialogDescription, DialogClose } from 'reka-ui'
import Dialog from './Dialog.vue'
defineProps<{ open: boolean; title: string; description?: string }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()
</script>
<template><Dialog :open="open" @update:open="emit('update:open', $event)"><DialogPortal><DialogOverlay class="modal-overlay" /><DialogContent class="modal-content">
<DialogTitle as="h2">{{ title }}</DialogTitle><DialogDescription>{{ description || '按 Escape 关闭，返回原操作位置。' }}</DialogDescription>
<slot /><DialogClose class="modal-close" aria-label="关闭">关闭</DialogClose>
</DialogContent></DialogPortal></Dialog></template>
