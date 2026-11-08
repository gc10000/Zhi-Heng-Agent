<script setup lang="ts">
import { DialogPortal, DialogOverlay, DialogContent, DialogTitle, DialogDescription, DialogClose } from 'reka-ui'
import Dialog from './Dialog.vue'
defineProps<{ open: boolean; title: string; description?: string }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()
</script>
<template><Dialog :open="open" @update:open="emit('update:open', $event)"><DialogPortal><DialogOverlay class="modal-overlay" /><DialogContent class="modal-content">
<DialogTitle as="h2" class="modal-title">{{ title }}</DialogTitle><DialogDescription class="modal-desc">{{ description || '按 Escape 关闭，返回原操作位置。' }}</DialogDescription>
<slot /><DialogClose class="modal-close" aria-label="关闭">关闭</DialogClose>
</DialogContent></DialogPortal></Dialog></template>
<style scoped>
.modal-overlay { position: fixed; inset: 0; background: color-mix(in srgb, var(--ink) 45%, transparent); z-index: 50; }
.modal-content { position: fixed; inset: 50% auto auto 50%; transform: translate(-50%,-50%); width: min(92vw,640px); max-height: 90svh; overflow: auto; background: var(--bg); color: var(--ink); border: 1px solid var(--line2); border-radius: 14px; padding: 28px; z-index: 51; display: grid; gap: 18px; overflow-wrap: anywhere; box-shadow: 0 18px 60px color-mix(in srgb, var(--ink) 18%, transparent); }
.modal-title { color: var(--ink); }
.modal-desc { color: var(--ink3); font-size: .85rem; }
.modal-close { justify-self: end; border: 1px solid var(--line2); background: var(--bg); color: var(--ink2); }
.modal-close:hover { color: var(--ink); border-color: var(--ink3); }
</style>
