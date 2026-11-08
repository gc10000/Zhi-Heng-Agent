<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { api } from '@/lib/api/client'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { scopeKey } from '@/features/chat/queries/history'
import type { Job } from '@/lib/api/types'
/**
 * T2.5：导入任务折叠区。后端只有 /import-jobs/{jid} 单查端点（无列表），
 * 任务 ID 从两处收集：① 上传返回后写入 ui store 的最近任务；② URL ?job= 深链。
 * 离开页面再回来仍能看到进行中/最近失败任务及其进度。
 */
const props = defineProps<{ jobId?: string }>()
const auth = useAuthStore(), ui = useUiStore(), cache = useQueryClient()
const open = ref(false), busy = ref(false), error = ref('')
/** 最近任务（会话内存级）：上传成功即登记，刷新后靠 ?job= 深链兜底。 */
const recentJobs = computed(() => {
  const ids: string[] = []
  if (props.jobId) ids.push(props.jobId)
  for (const id of ui.recentJobs) if (!ids.includes(id)) ids.push(id)
  return ids.slice(0, 5)
})
const stage: Record<string, string> = { pending: '等待派发', download: '读取原件', parse: '解析原件', images: '登记图片与摘要', chunk: '结构化切片', embed: '生成索引', index: '写入隔离索引', validate: '验证产物', publish: '切换活动修订', completed: '已完成' }
const stateLabel: Record<string, string> = { pending: '等待派发', running: '进行中', completed: '已完成', failed: '失败' }
const queries = recentJobs.value.map(id => ({
  id,
  query: useQuery({
    queryKey: computed(() => scopeKey(auth.user?.user_id || '', auth.kb, 'job', id)),
    enabled: computed(() => !!id && open.value && !!auth.user),
    retry: false,
    queryFn: ({ signal }) => api.request<Job>(`/import-jobs/${encodeURIComponent(id)}`, { signal }),
    refetchInterval: q => q.state.data && ['pending', 'running'].includes(q.state.data.state) ? 1500 : false,
  }),
}))
const rows = computed(() => queries.map(({ id, query }) => ({ id, job: query.data.value, fetching: query.isFetching.value })).filter(r => r.job))
const active = computed(() => rows.value.filter(r => ['pending', 'running'].includes(r.job!.state)))
const failedRows = computed(() => rows.value.filter(r => r.job!.state === 'failed'))
const visible = computed(() => [...active.value, ...failedRows.value])
const summary = computed(() => visible.value.length ? `${active.value.length} 进行中 · ${failedRows.value.length} 失败` : '')
watch(() => props.jobId, id => { if (id) { open.value = true; ui.trackJob(id) } }, { immediate: true })
watch(open, value => { if (value) for (const { query } of queries) void query.refetch() })
async function retry(id: string, version: number) {
  if (busy.value) return; busy.value = true; error.value = ''
  try {
    await api.post(`/import-jobs/${encodeURIComponent(id)}/retry`, { expected_version: version })
    for (const { query } of queries) void query.refetch()
    await cache.invalidateQueries({ queryKey: ['scope', auth.user?.user_id, auth.kb, 'documents'] })
  } catch (e) { error.value = (e as Error).message } finally { busy.value = false }
}
</script>
<template>
  <section v-if="recentJobs.length" class="jobs-fold" :class="{ open }">
    <button type="button" class="jobs-head" :aria-expanded="open" @click="open = !open">
      <span class="jobs-title">任务</span>
      <span v-if="summary" class="jobs-summary mono">{{ summary }}</span>
      <span class="jobs-caret" aria-hidden="true">{{ open ? '▾' : '▸' }}</span>
    </button>
    <div v-if="open" class="jobs-body">
      <p v-if="!visible.length" class="muted">没有进行中或最近失败的任务。</p>
      <p v-if="error" role="alert">{{ error }}</p>
      <article v-for="r in visible" :key="r.id" class="job-row" :class="r.job!.state">
        <span class="job-state" :class="r.job!.state">{{ stateLabel[r.job!.state] || r.job!.state }}</span>
        <span class="job-stage">{{ r.job!.state === 'completed' ? '完成' : stage[r.job!.stage] || r.job!.stage }}</span>
        <span class="mono job-id">{{ r.id }}</span>
        <span v-if="r.job!.attempt > 1" class="mono job-attempt">尝试 {{ r.job!.attempt }}</span>
        <code v-if="r.job!.error" class="mono job-err">{{ r.job!.error.code }}</code>
        <button v-if="auth.user?.role !== 'viewer' && r.job!.state === 'failed' && r.job!.retryable" type="button" class="job-retry" :disabled="busy" @click="retry(r.id, r.job!.version)">重试</button>
      </article>
    </div>
  </section>
</template>
<style scoped>
.jobs-fold { border: 1px solid var(--line2); border-radius: 10px; background: var(--panel); overflow: hidden; }
.jobs-head { width: 100%; display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: transparent; border: none; cursor: pointer; text-align: left; }
.jobs-head:hover { background: var(--bg); }
.jobs-title { font-size: 12.5px; font-weight: 700; color: var(--ink); }
.jobs-summary { font-size: 9.5px; color: var(--ink3); }
.jobs-caret { margin-left: auto; color: var(--ink3); font-size: 10px; }
.jobs-body { padding: 4px 12px 10px; display: grid; gap: 6px; border-top: 1px solid var(--line); }
.job-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 6px 0; border-bottom: 1px dashed var(--line); font-size: 12px; }
.job-row:last-child { border-bottom: none; }
.job-state { font-size: 10px; font-weight: 700; border-radius: 5px; padding: 1px 8px; border: 1px solid var(--line2); color: var(--ink2); }
.job-state.running, .job-state.pending { color: var(--accent); background: var(--accent-soft); border-color: var(--accent-line); }
.job-state.failed { color: var(--danger); background: var(--danger-soft); border-color: var(--danger-line); }
.job-state.completed { color: var(--ok); background: var(--ok-soft); border-color: var(--ok-line); }
.job-stage { color: var(--ink2); }
.mono { font-family: ui-monospace, Consolas, monospace; }
.job-id { font-size: 9px; color: var(--ink3); }
.job-attempt { font-size: 9px; color: var(--ink3); }
.job-err { font-size: 9px; color: var(--danger); background: var(--danger-soft); border-radius: 4px; padding: 0 5px; }
.job-retry { margin-left: auto; font-size: 11px; border: 1px solid var(--line2); background: var(--bg); border-radius: 7px; padding: 3px 12px; }
.job-retry:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
</style>
