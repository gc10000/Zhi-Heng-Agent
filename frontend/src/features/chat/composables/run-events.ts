import { terminal, type Run, type Citation, type Product } from '@/lib/api/types'
export interface RunEvent { run_id: string; seq: number; type: string; payload: Record<string, unknown> }
export function reduceRun(current: Run, event: RunEvent): Run {
  if (event.run_id !== current.run_id || !Number.isSafeInteger(event.seq) || event.seq <= current.seq || terminal(current.state)) return current
  const next = { ...current, seq: event.seq }, p = event.payload
  if (event.type === 'answer.delta' && typeof p.text === 'string') next.answer += p.text
  if (event.type === 'run.started') next.state = 'running'
  if (event.type === 'stage.changed') { if (typeof p.stage === 'string') next.stage = p.stage; if (typeof p.state === 'string') next.state = p.state }
  if (event.type === 'citation.selected' && Array.isArray(p.citations)) next.citations = p.citations as Citation[]
  if (event.type === 'product.candidates') { next.state = 'awaiting_input'; next.candidates = p.candidates as Product[]; next.version = p.expected_version as number }
  if (event.type === 'product.confirmed') { next.state = 'pending'; next.candidates = [] }
  const state = event.type.replace(/^run\./, '')
  if (terminal(state)) {
    next.state = state
    if (typeof p.answer === 'string') next.answer = p.answer
    if (Array.isArray(p.citations)) next.citations = p.citations as Citation[]
    if (p.error) next.error = p.error as Run['error']
  }
  return next
}
