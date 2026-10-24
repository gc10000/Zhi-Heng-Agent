import { describe, it, expect } from 'vitest'
import { reduceRun, type RunEvent } from '@/features/chat/composables/run-events'
import type { Run } from '@/lib/api/types'
const run = (): Run => ({ run_id:'r', conversation_id:'c', kb_id:'k', question:'q', state:'running', seq:2, version:1, answer:'首段', citations:[] })
const event = (type: string, seq: number, payload = {}): RunEvent => ({ run_id:'r',seq,type,payload })
describe('持久事件折叠', () => {
  it('seq允许间隙，重复和跨run增量拒绝', () => {
    const one = reduceRun(run(),event('answer.delta',8,{text:'下一段'}))
    expect(one.answer).toBe('首段下一段'); expect(one.seq).toBe(8)
    expect(reduceRun(one,event('answer.delta',8,{text:'重复'}))).toBe(one)
    expect(reduceRun(one,{...event('answer.delta',9,{text:'串入'}),run_id:'other'})).toBe(one)
  })
  it('失败保留部分正文，不能显示completed', () => {
    const one = reduceRun(run(),event('run.failed',9,{error:{code:'query_execution_failed',stage:'generate'}}))
    expect(one.state).toBe('failed'); expect(one.answer).toBe('首段'); expect(one.error?.code).toBe('query_execution_failed')
    expect(reduceRun(one,event('run.completed',10,{answer:'伪造完成'}))).toBe(one)
  })
  it('终态使用最终答案/引用，不在已有delta上再次拼接', () => {
    expect(reduceRun(run(),event('run.completed',12,{answer:'最终完整正文',citations:[]}))).toMatchObject({answer:'最终完整正文',state:'completed',seq:12})
  })
  it('候选事件恢复版本与等待状态，确认不靠计时器', () => {
    expect(reduceRun(run(),event('product.candidates',5,{candidates:[{product_id:'p',model:'AX24'}],expected_version:4}))).toMatchObject({state:'awaiting_input',version:4,candidates:[{product_id:'p',model:'AX24'}]})
  })
  it('取消意图不是取消终态', () => {
    expect(reduceRun(run(),event('stage.changed',6,{state:'cancel_requested'})).state).toBe('cancel_requested')
  })
})
