<script setup lang="ts">
import { computed } from 'vue'
import type { Run } from '@/lib/api/types'
const props = defineProps<{ run: Run }>()
const stages: Record<string,string> = { authorization:'检查授权',product:'匹配设备',retrieve:'检索适用资料',rerank:'核对证据',generate:'生成有依据的回答',completed:'回答完成' }
const states: Record<string,string> = {pending:'等待执行',running:'正在处理',awaiting_input:'等待确认适用型号',cancel_requested:'已请求停止，等待执行端确认',completed:'回答完成',failed:'回答失败，部分内容仅供核对',cancelled:'已取消',interrupted:'运行已中断，部分内容仅供核对'}
const label = computed(() => props.run.state === 'running' ? stages[props.run.stage || ''] || states.running : states[props.run.state] || '状态待核对')
</script>
<template><div class="run-progress"><p role="status">{{ label }}</p><p v-if="run.error" role="alert">错误：{{ run.error.code }} · 阶段：{{ stages[run.error.stage || ''] || run.error.stage || '未知' }}</p></div></template>
