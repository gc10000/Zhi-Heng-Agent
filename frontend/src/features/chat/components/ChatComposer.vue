<script setup lang="ts">
import { ref } from 'vue'
defineProps<{ busy: boolean; active: boolean; disabled: boolean; modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; send: []; cancel: [] }>()
const composing = ref(false)
function key(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && !composing.value && event.keyCode !== 229) { event.preventDefault(); emit('send') }
}
</script>
<template><form class="composer" @submit.prevent="emit('send')"><label>问题<textarea :value="modelValue" @input="emit('update:modelValue',($event.target as HTMLTextAreaElement).value)" @compositionstart="composing = true" @compositionend="composing = false" @keydown="key" required maxlength="32000" rows="3" placeholder="描述设备、现象和已尝试的操作…" /></label><div><span class="muted">Enter发送 · Shift+Enter换行</span><button v-if="active" type="button" @click="emit('cancel')">停止</button><button class="primary" :disabled="busy || active || disabled || !modelValue.trim()">发送</button></div></form></template>
