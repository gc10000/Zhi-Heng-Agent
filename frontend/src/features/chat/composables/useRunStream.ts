import { ref, onBeforeUnmount } from 'vue'
import { api, ApiError } from '@/lib/api/client'
import { terminal, type Run } from '@/lib/api/types'
import { useRunStore } from '../stores/run'
import type { RunEvent } from './run-events'
const kinds = ['run.started','stage.changed','product.candidates','product.confirmed','input.required','citation.selected','answer.delta','run.completed','run.failed','run.cancelled','run.interrupted']

export function useRunStream(onTerminal: () => void) {
  const store = useRunStore(), connection = ref(''), error = ref('')
  let source: EventSource | undefined, timer: ReturnType<typeof setTimeout> | undefined, generation = 0, runId = '', backoff = 1000
  function close() { generation++; source?.close(); source = undefined; clearTimeout(timer); connection.value = '' }
  async function refresh(expected = generation) {
    const value = await api.request<Run>(`/runs/${encodeURIComponent(runId)}`)
    if (expected !== generation) return
    store.snapshot(value)
    return value
  }
  function schedule(version: number) {
    clearTimeout(timer)
    timer = setTimeout(() => { if (version === generation) connect(version) }, backoff)
    backoff = Math.min(backoff * 2, 15000)
  }
  async function recover(version: number) {
    source?.close(); connection.value = '连接中断，正在恢复快照…'
    try {
      const value = await refresh(version)
      if (!value || version !== generation) return
      if (terminal(value.state)) { connection.value = ''; onTerminal(); return }
      schedule(version)
    } catch (e) {
      if (version !== generation) return
      error.value = (e as Error).message
      if (!(e instanceof ApiError) || e.status >= 500) schedule(version)
    }
  }
  function connect(version: number) {
    if (version !== generation) return
    const current = store.runs[runId]
    if (!current || terminal(current.state)) return
    source?.close()
    const stream = new EventSource(`/api/v1/runs/${encodeURIComponent(runId)}/events?after_seq=${current.seq}`)
    source = stream
    stream.onopen = () => { if (version === generation) { backoff = 1000; connection.value = '已连接' } }
    for (const type of kinds) stream.addEventListener(type, event => {
      if (version !== generation || source !== stream) return
      try {
        const value: RunEvent = JSON.parse((event as MessageEvent).data)
        if (value.run_id !== runId || value.type !== type || terminal(store.runs[runId].state) || value.seq <= store.runs[runId].seq) return
        store.event(value)
        if (terminal(store.runs[runId].state)) {
          stream.close(); connection.value = ''; onTerminal()
          // 终态事件先到也不假定消息占用已释放；后端快照/历史仍是最终依据。
          void refresh(version).catch(e => { if (version === generation) error.value = e.message })
        }
      } catch { error.value = '收到无法读取的事件，正在恢复快照。'; void recover(version) }
    })
    // 原生EventSource不暴露HTTP状态；包括410在内的错误统一回读授权快照，按快照seq重开。
    stream.onerror = () => { if (version === generation && source === stream) void recover(version) }
  }
  function start(value: Run) { close(); runId = value.run_id; store.snapshot(value); error.value = ''; backoff = 1000; connect(generation) }
  async function command(name: 'cancel' | 'confirm-product', fields = {}) {
    const version = generation, rid = runId
    const fresh = name === 'confirm-product' ? store.runs[rid] : await refresh(version)
    if (!fresh || version !== generation) return
    let value: Run
    try { value = await api.post<Run>(`/runs/${encodeURIComponent(rid)}/${name}`, { expected_version: fresh.version, ...fields }) }
    catch (e) { if (e instanceof ApiError && e.status === 409) await refresh(version); throw e }
    if (version !== generation) return
    store.snapshot(value)
    if (terminal(value.state)) onTerminal()
  }
  window.addEventListener('close-run-streams', close)
  onBeforeUnmount(() => { close(); window.removeEventListener('close-run-streams', close) })
  return { start, close, refresh, command, connection, error }
}
