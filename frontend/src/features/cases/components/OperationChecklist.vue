<script setup lang="ts">
import { reactive } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
export interface Operation { operation_id: string; run_id: string; suggestion: string; prerequisites: string; risk: string; citation_ids: string[]; status: 'not_tried'|'tried'|'ineffective'; reports: {status:string;note:string;recorded_at:string;source:string}[] }
defineProps<{ operations: Operation[]; busy?: boolean }>()
const emit = defineEmits<{ report: [id:string, status:string, note:string]; citation: [runId:string, citationId:string] }>()
const notes = reactive<Record<string,string>>({})
/** 三态语义：系统建议（info）/ 用户记录（warning）/ 无效尝试（danger）。 */
function statusBadge(status: string) {
  if (status === 'not_tried') return { variant: 'info' as const, label: '系统建议' }
  if (status === 'tried') return { variant: 'warning' as const, label: '用户记录 · 已试' }
  return { variant: 'danger' as const, label: '用户记录 · 无效' }
}
</script>
<template><section aria-label="操作清单"><h2>操作清单</h2><p>以下为资料建议摘录，尚未执行。请人工核对完整前提；结果仅记录用户自报。</p>
<p v-if="!operations.length">暂无可追溯操作。可补充依据或转交人工支持。</p>
<article v-for="step in operations" :key="step.operation_id" class="card"><header class="op-head"><h3 class="op-title">资料建议</h3><Badge :variant="statusBadge(step.status).variant" size="md">{{ statusBadge(step.status).label }}</Badge></header><p>{{ step.suggestion }}</p><p>前提：{{ step.prerequisites }}</p><p>风险提示：{{ step.risk }}</p>
<button v-for="citation in step.citation_ids" :key="citation" class="op-cite" @click="emit('citation',step.run_id,citation)">核对依据</button>
<p role="status">用户记录：{{ {not_tried:'未试',tried:'已试',ineffective:'无效'}[step.status] }}</p>
<label>实际结果<textarea v-model="notes[step.operation_id]" :disabled="busy" maxlength="4000" /></label>
<button :disabled="busy || !notes[step.operation_id]?.trim()" @click="emit('report',step.operation_id,'tried',notes[step.operation_id]!)">记录已试</button>
<button :disabled="busy || !notes[step.operation_id]?.trim()" @click="emit('report',step.operation_id,'ineffective',notes[step.operation_id]!)">记录无效</button>
<button :disabled="busy || !notes[step.operation_id]?.trim()" @click="emit('report',step.operation_id,'not_tried',notes[step.operation_id]!)">更正为未试</button>
<ul><li v-for="(report,index) in step.reports" :key="index">{{ report.recorded_at }} · 用户自报 {{ ({not_tried:'未试',tried:'已试',ineffective:'无效'} as Record<string,string>)[report.status]||'待核对' }}：{{ report.note }}</li></ul>
</article></section></template>
<style scoped>
.card { padding: 14px 16px; margin: .8rem 0; border: 1px solid var(--line); border-radius: 10px; background: var(--bg); display: grid; gap: 8px; }
p, li { line-height: 1.7; color: var(--ink2); }
label { display: grid; gap: .4rem; font-size: .85rem; color: var(--ink2); }
.op-head { display: flex; align-items: center; gap: 10px; }
.op-title { margin: 0; font-size: .95rem; color: var(--ink); }
.op-cite { margin: .2rem .5rem .2rem 0; font-size: 11.5px; border: 1px solid var(--accent-line); color: var(--accent); background: var(--accent-soft); border-radius: 6px; padding: 2px 10px; }
.op-cite:hover { background: var(--accent); color: var(--bg); }
.op-actions { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
