<script setup lang="ts">
import { reactive } from 'vue'
export interface Operation { operation_id: string; run_id: string; suggestion: string; prerequisites: string; risk: string; citation_ids: string[]; status: 'not_tried'|'tried'|'ineffective'; reports: {status:string;note:string;recorded_at:string;source:string}[] }
defineProps<{ operations: Operation[]; busy?: boolean }>()
const emit = defineEmits<{ report: [id:string, status:string, note:string]; citation: [runId:string, citationId:string] }>()
const notes = reactive<Record<string,string>>({})
</script>
<template><section aria-label="操作清单"><h2>操作清单</h2><p>以下为资料建议摘录，尚未执行。请人工核对完整前提；结果仅记录用户自报。</p>
<p v-if="!operations.length">暂无可追溯操作。可补充依据或转交人工支持。</p>
<article v-for="step in operations" :key="step.operation_id" class="card"><h3>资料建议</h3><p>{{ step.suggestion }}</p><p>前提：{{ step.prerequisites }}</p><p>风险提示：{{ step.risk }}</p>
<button v-for="citation in step.citation_ids" :key="citation" @click="emit('citation',step.run_id,citation)">核对依据</button>
<p role="status">用户记录：{{ {not_tried:'未试',tried:'已试',ineffective:'无效'}[step.status] }}</p>
<label>实际结果<textarea v-model="notes[step.operation_id]" :disabled="busy" maxlength="4000" /></label>
<button :disabled="busy || !notes[step.operation_id]?.trim()" @click="emit('report',step.operation_id,'tried',notes[step.operation_id]!)">记录已试</button>
<button :disabled="busy || !notes[step.operation_id]?.trim()" @click="emit('report',step.operation_id,'ineffective',notes[step.operation_id]!)">记录无效</button>
<button :disabled="busy || !notes[step.operation_id]?.trim()" @click="emit('report',step.operation_id,'not_tried',notes[step.operation_id]!)">更正为未试</button>
<ul><li v-for="(report,index) in step.reports" :key="index">{{ report.recorded_at }} · 用户自报 {{ report.status }}：{{ report.note }}</li></ul>
</article></section></template>
