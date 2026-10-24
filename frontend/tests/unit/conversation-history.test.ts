import { it, expect } from 'vitest'
import { scopeKey, mergeHistory } from '@/features/chat/queries/history'
import type { Message } from '@/lib/api/types'
const message = (id: string, ordinal: number, text: string): Message => ({ message_id: id, run_id: 'r', ordinal, text, role: 'assistant', citations: [] })
it('同会话ID在不同用户/知识范围不能共用缓存', () => {
  expect(scopeKey('a', 'k1', 'history', 'same')).not.toEqual(scopeKey('b', 'k1', 'history', 'same'))
  expect(scopeKey('a', 'k1', 'history', 'same')).not.toEqual(scopeKey('a', 'k2', 'history', 'same'))
})
it('分页重叠时保留唯一消息的持久ordinal顺序，不能按到达时间重排', () => {
  expect(mergeHistory([{ items: [message('b', 8, '答案')] }, { items: [message('a', 2, '问题'), message('b', 8, '答案')] }]).map(m => m.text)).toEqual(['问题', '答案'])
})
