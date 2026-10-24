<script setup lang="ts">
import type { Run } from '@/lib/api/types'
const props = defineProps<{ run: Run; busy: boolean }>()
const emit = defineEmits<{ confirm: [value: { product_ids: string[]; expected_version: number }] }>()
function choose(id: string) {
  if (props.busy || props.run.state !== 'awaiting_input') return
  emit('confirm', { product_ids: [id], expected_version: props.run.version })
}
</script>
<template><section v-if="run.state === 'awaiting_input'" class="clarification"><h2>请选择适用型号</h2><p class="muted">不同型号可能使用不同参数。确认后才会在对应资料中检索。</p><div class="candidate-list"><button v-for="p in run.candidates" :key="p.product_id" :disabled="busy" @click="choose(p.product_id)">{{ p.model }}<small v-if="p.series">{{ p.series }}</small></button></div></section></template>
