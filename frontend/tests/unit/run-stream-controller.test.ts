import { it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { useRunStream } from '@/features/chat/composables/useRunStream'
import { useRunStore } from '@/features/chat/stores/run'
import { api, ApiError } from '@/lib/api/client'
import type { Run } from '@/lib/api/types'
class Port {
  static all: Port[] = []
  closed = false; onerror?: () => void; onopen?: () => void
  listeners = new Map<string, (e: MessageEvent) => void>()
  constructor(public url: string) { Port.all.push(this) }
  addEventListener(name: string, action: (e: MessageEvent) => void) { this.listeners.set(name,action) }
  close() { this.closed = true }
  emit(type: string, seq: number, payload = {}) { this.listeners.get(type)?.(new MessageEvent(type,{ data: JSON.stringify({run_id:'r',type,seq,payload}) })) }
}
function setup() {
  Port.all = []; vi.stubGlobal('EventSource', Port)
  let stream!: ReturnType<typeof useRunStream>, store!: ReturnType<typeof useRunStore>
  const done = vi.fn()
  const wrapper = mount({ setup() { stream = useRunStream(done); store = useRunStore(); return () => null } },{global:{plugins:[createPinia()]}})
  const row: Run = {run_id:'r',conversation_id:'c',kb_id:'k',question:'q',state:'running',seq:2,version:1,answer:'部分',citations:[]}
  return { stream,store,done,wrapper,row }
}
afterEach(() => {vi.restoreAllMocks();vi.unstubAllGlobals();vi.useRealTimers()})
it('重复终态/已关闭流排队事件只触发一次终态同步', async () => {
  const s = setup(); vi.spyOn(api,'request').mockResolvedValue({...s.row,state:'failed',seq:8})
  s.stream.start(s.row); const port = Port.all[0]
  port.emit('run.failed',8); port.emit('run.failed',8); await flushPromises()
  expect(s.done).toHaveBeenCalledTimes(1); expect(port.closed).toBe(true); s.wrapper.unmount()
})
it('EventSource的410/断线错误先回读快照，按新seq重连且不重复正文', async () => {
  vi.useFakeTimers(); const s=setup()
  vi.spyOn(api,'request').mockResolvedValue({...s.row,seq:9,answer:'已恢复正文'})
  s.stream.start(s.row); Port.all[0].onerror?.(); await flushPromises()
  expect(s.store.runs.r.answer).toBe('已恢复正文')
  await vi.advanceTimersByTimeAsync(1000)
  expect(Port.all[1].url).toContain('after_seq=9')
  Port.all[1].emit('answer.delta',9,{text:'重复'})
  expect(s.store.runs.r.answer).toBe('已恢复正文'); s.wrapper.unmount()
})
it('401后停止重连，卸载不接受迟到快照', async () => {
  vi.useFakeTimers(); const s=setup()
  vi.spyOn(api,'request').mockRejectedValue(new ApiError(401,'unauthorized','登录过期'))
  s.stream.start(s.row); Port.all[0].onerror?.(); await flushPromises(); await vi.advanceTimersByTimeAsync(20000)
  expect(Port.all).toHaveLength(1); expect(s.stream.error.value).toBe('登录过期'); s.wrapper.unmount()
})
it('卸载或切换后迟到恢复不能覆盖新运行，也不重新开流', async () => {
  vi.useFakeTimers(); const s=setup(); let resolve!: (value: unknown) => void
  vi.spyOn(api,'request').mockImplementation(() => new Promise(r=>{resolve=r}))
  s.stream.start(s.row); Port.all[0].onerror?.(); s.stream.close()
  resolve({...s.row,seq:9,answer:'迟到旧答案'}); await flushPromises(); await vi.advanceTimersByTimeAsync(20000)
  expect(s.store.runs.r.answer).toBe('部分'); expect(Port.all).toHaveLength(1); s.wrapper.unmount()
})
it('取消读取最新版本并发后端命令，等待取消终态而非仅断流', async () => {
  const s=setup(); vi.spyOn(api,'request').mockResolvedValue({...s.row,version:12})
  const post=vi.spyOn(api,'post').mockResolvedValue({...s.row,version:13,state:'cancel_requested'})
  s.stream.start(s.row); await s.stream.command('cancel')
  expect(post).toHaveBeenCalledWith('/runs/r/cancel',{expected_version:12})
  expect(s.store.runs.r.state).toBe('cancel_requested'); expect(Port.all[0].closed).toBe(false); s.wrapper.unmount()
})
