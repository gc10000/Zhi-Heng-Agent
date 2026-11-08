<script setup lang="ts">
import { computed } from 'vue'
import type { Run } from '@/lib/api/types'
import { resolveError } from '@/lib/error-codes'
const props = defineProps<{ run: Run }>()
const emit = defineEmits<{ retry: [] }>()
const stages: Record<string,string> = { authorization:'检查授权',product:'匹配设备',retrieve:'检索适用资料',rerank:'核对证据',generate:'生成有依据的回答',completed:'回答完成' }
const states: Record<string,string> = {pending:'等待执行',running:'正在处理',awaiting_input:'等待确认适用型号',cancel_requested:'已请求停止，等待执行端确认',completed:'回答完成',failed:'回答失败，部分内容仅供核对',cancelled:'已取消',interrupted:'运行已中断，部分内容仅供核对'}
const label = computed(() => props.run.state === 'running' ? stages[props.run.stage || ''] || states.running : states[props.run.state] || '状态待核对')
const failed = computed(() => props.run.state === 'failed' && !!props.run.error)
const resolved = computed(() => resolveError(props.run.error?.code, props.run.error?.message))
const stageLabel = computed(() => stages[props.run.error?.stage || ''] || props.run.error?.stage || '未知')
const copied = computed(() => `复制错误码 ${resolved.value.code}`)
/** T2.4：后端 run 无 behavior 字段时，按 INSUFFICIENT_ANSWER 固定文案匹配（app/answering/assertion_binding.py）。 */
const INSUFFICIENT_ANSWER = '当前授权知识库中没有找到可用证据，请补充资料或明确设备型号。'
const insufficient = computed(() => props.run.state === 'completed' && props.run.answer.trim() === INSUFFICIENT_ANSWER)
async function copyCode() {
  try { await navigator.clipboard.writeText(resolved.value.code) } catch { /* 剪贴板不可用时静默 */ }
}
</script>
<template>
  <div class="run-progress">
    <p role="status">{{ label }}</p>
    <section v-if="insufficient" class="warn-banner" role="status">
      <p class="warn-title">依据不足：当前知识库没有覆盖这个问题的资料。</p>
      <p class="warn-advice">可上传对应设备的资料后重试，或明确设备型号缩小检索范围。</p>
      <RouterLink class="warn-link" to="/documents">上传补充资料 →</RouterLink>
    </section>
    <section v-if="failed" class="error-card" role="alert">
      <h3 class="error-title">{{ resolved.advice?.title || '处理出错' }}</h3>
      <p class="error-advice">{{ resolved.advice?.advice || resolved.raw || '处理过程中发生错误。' }}</p>
      <p v-if="!resolved.advice && resolved.raw" class="error-advice">{{ resolved.raw }}</p>
      <div class="error-meta">
        <code class="error-code" :title="copied" @click="copyCode">{{ resolved.code }}</code>
        <span class="error-stage mono">阶段：{{ stageLabel }}</span>
      </div>
      <div class="error-actions">
        <button v-if="resolved.advice?.action?.to" type="button" class="btn-primary" @click="$router.push(resolved.advice!.action!.to!)">{{ resolved.advice.action.label }}</button>
        <button v-if="resolved.advice?.action?.retry || (resolved.advice?.action && !resolved.advice.action.to)" type="button" class="btn-primary" @click="emit('retry')">{{ resolved.advice?.action?.label || '重试' }}</button>
        <button type="button" class="btn-secondary" @click="emit('retry')">重新提问</button>
      </div>
    </section>
    <p v-else-if="run.error" role="alert">错误：{{ run.error.code }} · 阶段：{{ stageLabel }}</p>
  </div>
</template>
<style scoped>
.run-progress { color: var(--ink2); font-size: .85rem; }
.warn-banner { background: var(--warn-soft); border: 1px solid var(--line2); border-radius: 10px; padding: 12px 14px; display: grid; gap: 6px; }
.warn-title { margin: 0; font-weight: 700; color: var(--warn); font-size: .9rem; }
.warn-advice { margin: 0; color: var(--ink2); line-height: 1.7; }
.warn-link { color: var(--accent); text-decoration: none; font-weight: 600; font-size: .85rem; width: fit-content; }
.warn-link:hover { text-decoration: underline; }
.error-card { background: var(--danger-soft); border: 1px solid var(--danger-line); border-radius: 12px; padding: 14px 16px; display: grid; gap: 8px; }
.error-title { margin: 0; font-size: .95rem; font-weight: 700; color: var(--ink); }
.error-advice { margin: 0; color: var(--ink2); line-height: 1.7; overflow-wrap: anywhere; }
.error-meta { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.error-code { font-family: ui-monospace, Consolas, monospace; font-size: 10px; letter-spacing: .04em; color: var(--ink2); background: var(--bg); border: 1px solid var(--line2); border-radius: 5px; padding: 1px 7px; cursor: copy; }
.error-stage { font-size: 10px; color: var(--ink3); }
.mono { font-family: ui-monospace, Consolas, monospace; }
.error-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.btn-primary { background: var(--ink); color: var(--bg); border: none; border-radius: 8px; padding: 6px 14px; font-size: 12.5px; font-weight: 600; }
.btn-primary:hover { opacity: .88; }
.btn-secondary { background: transparent; color: var(--ink2); border: 1px solid var(--line2); border-radius: 8px; padding: 6px 14px; font-size: 12.5px; }
.btn-secondary:hover { color: var(--ink); border-color: var(--ink3); }
</style>
