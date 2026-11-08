import { test, expect } from '@playwright/test'
import { mockApi } from './helpers'

// Phase1/2 场景级前后对比截图（任务书：每项改动前后各截一张·亮色）
// SHOT_TAG=after 在 v6 分支跑；SHOT_TAG=before 在基线 worktree 跑。数据完全一致，只有代码不同。
const TAG = process.env.SHOT_TAG || 'after'
const OUT = `docs/design/screenshots/scenario`

const conversation = (active: string) => ({ conversation_id: 'conversation-a', kb_id: 'kb-test', title: 'NX308-S 光模块指示灯排查', product_ids: [], version: 0, archived: false, active_run_id: active })
const INSUFFICIENT = '当前授权知识库中没有找到可用证据，请补充资料或明确设备型号。'
const runFailed = { run_id: 'run-err', conversation_id: 'conversation-a', kb_id: 'kb-test', question: '光模块红灯常亮怎么排查？', state: 'failed', seq: 3, version: 2, answer: '', citations: [], error: { code: 'product_selection_required', message: 'matched 6 products for this question', stage: 'product' } }
const runClarify = { run_id: 'run-cla', conversation_id: 'conversation-a', kb_id: 'kb-test', question: '风扇告警阈值怎么查？', state: 'awaiting_input', seq: 2, version: 1, answer: '', citations: [], candidates: [{ product_id: 'p1', model: 'NX308-S', series: 'NX300 系列' }, { product_id: 'p2', model: 'NX308-L', series: 'NX300 系列' }, { product_id: 'p3', model: 'NX312-X', series: 'NX310 系列' }] }
const cite1 = { citation_id: 'cite-1', document_id: 'doc-1', revision_id: 'rev-3', text: '红色常亮：接收光功率低于告警下限，或模块未注册。此时应先检查对端连接。', display_text: '「红色常亮：接收光功率低于告警下限，或模块未注册」。此时应先检查对端连接…', source_refs: [{ kind: 'pdf', page: 42, bbox: [0.12, 0.26, 0.82, 0.44] }], asset_ids: [], answer_asset_ids: [], image_selection_version: 1, original: { asset_id: 'a1', media_type: 'application/pdf', name: 'NX300 安装手册.pdf', url: '/api/v1/assets/a1' } }
const cite2 = { citation_id: 'cite-2', document_id: 'doc-2', revision_id: 'rev-2', text: '光纤重新插拔，锁扣到位后观察指示灯状态变化。', display_text: '「光纤重新插拔，锁扣到位后观察指示灯状态变化」。', source_refs: [{ kind: 'pdf', page: 18 }], asset_ids: [], answer_asset_ids: [], image_selection_version: 1 }
const runOk = { run_id: 'run-ok', conversation_id: 'conversation-a', kb_id: 'kb-test', question: 'NX308-S 光模块红灯常亮怎么排查？', state: 'completed', seq: 5, version: 3, answer: '红色常亮指向光功率越界，按依赖顺序定位：\n1. 确认灯义：红色常亮表示接收光功率低于告警下限[1]。\n2. 物理层检查：两端光纤重新插拔[2]。', citations: [cite1, cite2], product_snapshot: { product_ids: ['p1'] } }
const messagesFull = [
  { message_id: 'm1', run_id: 'run-ok', role: 'user', text: 'NX308-S 光模块红灯常亮怎么排查？', citations: [], ordinal: 1 },
  { message_id: 'm2', run_id: 'run-ok', role: 'assistant', text: runOk.answer, citations: [cite1, cite2], ordinal: 2, product_snapshot: { product_ids: ['p1'] } },
]
const documents = { items: [
  { document_id: 'doc-1', name: 'NX300 安装手册.pdf', purpose: 'technical', kb_id: 'kb-test', product_ids: [], active_revision_id: 'rev-3', active_generation: 3 },
  { document_id: 'doc-2', name: '硬件维护手册.pdf', purpose: 'technical', kb_id: 'kb-test', product_ids: [], active_revision_id: 'rev-2', active_generation: 2 },
], next_cursor: null }

async function setup(page: import('@playwright/test').Page, active: string, messages: unknown[], extra?: import('@playwright/test').Route['request'] extends never ? never : (route: import('@playwright/test').Route) => Promise<boolean>) {
  await mockApi(page, async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/conversations') && route.request().method() === 'GET') { await route.fulfill({ json: { items: [conversation(active)], next_cursor: null } }); return true }
    if (path.endsWith('/messages')) { await route.fulfill({ json: { items: messages, next_cursor: null } }); return true }
    if (path.endsWith('/documents')) { await route.fulfill({ json: documents }); return true }
    if (path.endsWith('/runs/run-err')) { await route.fulfill({ json: runFailed }); return true }
    if (path.endsWith('/runs/run-cla')) { await route.fulfill({ json: runClarify }); return true }
    if (path.endsWith('/runs/run-ok')) { await route.fulfill({ json: runOk }); return true }
    if (path.endsWith('/runs/run-ok/citations/cite-1')) { await route.fulfill({ json: cite1 }); return true }
    if (path.endsWith('/runs/run-ok/citations/cite-2')) { await route.fulfill({ json: cite2 }); return true }
    if (extra && await extra(route)) return true
    return false
  })
}

test(`t1-1 error card [${TAG}]`, async ({ page }) => {
  await setup(page, 'run-err', [])
  await page.goto('/chat/conversation-a')
  await page.waitForTimeout(900)
  await page.screenshot({ path: `${OUT}/t1-1-error-${TAG}.png` })
  expect(true).toBe(true)
})

test(`t1-2 clarification [${TAG}]`, async ({ page }) => {
  await setup(page, 'run-cla', [])
  await page.goto('/chat/conversation-a')
  await page.waitForTimeout(900)
  await page.screenshot({ path: `${OUT}/t1-2-clarify-${TAG}.png` })
  expect(true).toBe(true)
})

test(`t1-4 evidence card [${TAG}]`, async ({ page }) => {
  await setup(page, 'run-ok', messagesFull)
  await page.goto('/chat/conversation-a')
  await page.waitForTimeout(900)
  await page.locator('button.inline-citation').first().click()
  await page.waitForTimeout(900)
  await page.screenshot({ path: `${OUT}/t1-4-evidence-${TAG}.png` })
  expect(true).toBe(true)
})

test(`t1-3-t1-5 thread actions [${TAG}]`, async ({ page }) => {
  await setup(page, 'run-ok', messagesFull)
  await page.goto('/chat/conversation-a')
  await page.waitForTimeout(900)
  await page.screenshot({ path: `${OUT}/t1-3-t1-5-thread-${TAG}.png` })
  expect(true).toBe(true)
})

test(`t2-4 insufficient [${TAG}]`, async ({ page }) => {
  await setup(page, 'run-ins', [], async route => {
    if (new URL(route.request().url()).pathname.endsWith('/runs/run-ins')) {
      await route.fulfill({ json: { ...runOk, run_id: 'run-ins', question: '怎么配置量子加密模块？', answer: INSUFFICIENT, citations: [], product_snapshot: undefined } })
      return true
    }
    return false
  })
  await page.goto('/chat/conversation-a')
  await page.waitForTimeout(900)
  await page.screenshot({ path: `${OUT}/t2-4-insufficient-${TAG}.png` })
  expect(true).toBe(true)
})
