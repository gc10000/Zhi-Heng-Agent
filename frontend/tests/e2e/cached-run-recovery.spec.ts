import { test, expect } from '@playwright/test'
import { mockApi, conversation } from './helpers'

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))
for (const timing of [
  { name: '历史先到', history: 250, directory: 500, old: 0 },
  { name: '目录先到', history: 500, directory: 250, old: 0 },
  { name: '旧快照迟到', history: 150, directory: 300, old: 1200 },
]) {
  test(`缓存A→B→A恢复当前活动运行：${timing.name}`, async ({ page }) => {
    let active = false, confirmed = false, cancelled = false
    const reads: string[] = [], streams: string[] = [], commands: string[] = [], errors: string[] = []
    page.on('pageerror', e => errors.push(e.message))
    const snapshot = () => ({ run_id: 'new-active', conversation_id: 'conversation-a', kb_id: 'kb-test', question: '另一标签页的新问题',
      state: cancelled ? 'cancelled' : confirmed ? 'running' : 'awaiting_input', seq: cancelled ? 9 : confirmed ? 8 : 7,
      version: cancelled ? 4 : confirmed ? 3 : 2, answer: '', citations: [], stage: 'retrieve', candidates: [{ product_id: 'p', model: '当前轮AX24' }] })
    await mockApi(page, async route => {
      const path = new URL(route.request().url()).pathname
      if (path.endsWith('/conversations')) {
        const value = { items: [{ ...conversation, active_run_id: active && !cancelled ? 'new-active' : null }, { ...conversation, conversation_id: 'b', title: '会话B' }], next_cursor: null }
        if (active && new URL(route.request().url()).searchParams.get('limit') === '100') await delay(timing.directory)
        await route.fulfill({ json: value }); return true
      }
      if (path.endsWith('/conversation-a/messages')) {
        const value = { items: [{ message_id: 'old-q', run_id: 'old-done', role: 'user', ordinal: 1, text: '旧问题', citations: [] },
          { message_id: 'old-a', run_id: 'old-done', role: 'assistant', ordinal: 2, text: '旧答案', citations: [] },
          ...(active ? [{ message_id: 'new-q', run_id: 'new-active', role: 'user', ordinal: 3, text: '另一标签页的新问题', citations: [] }] : [])], next_cursor: null }
        if (active) await delay(timing.history)
        await route.fulfill({ json: value }); return true
      }
      if (path.endsWith('/runs/old-done')) {
        reads.push('old-done'); if (active) await delay(timing.old)
        await route.fulfill({ json: { ...snapshot(), run_id: 'old-done', state: 'completed', answer: '旧答案', candidates: [] } }); return true
      }
      if (path.endsWith('/runs/new-active')) { reads.push('new-active'); await route.fulfill({ json: snapshot() }); return true }
      if (path.endsWith('/runs/new-active/events')) { streams.push('new-active'); await route.fulfill({ contentType: 'text/event-stream', body: ': 心跳\n\n' }); return true }
      if (path.endsWith('/confirm-product')) {
        const body = route.request().postDataJSON(); expect(body).toEqual({ expected_version: 2, product_ids: ['p'] })
        commands.push('confirm'); confirmed = true; await route.fulfill({ json: snapshot() }); return true
      }
      if (path.endsWith('/cancel')) {
        expect(route.request().postDataJSON().expected_version).toBe(3)
        commands.push('cancel'); cancelled = true; await route.fulfill({ json: snapshot() }); return true
      }
      return false
    })
    await page.goto('/chat/conversation-a')
    await expect(page.getByText('回答完成', { exact: true })).toBeVisible()
    await page.getByRole('link', { name: '会话B', exact: true }).click()
    await page.getByLabel('问题', { exact: true }).fill('B的问题')
    await expect(page.getByRole('button', { name: '发送', exact: true })).toBeEnabled()
    active = true
    await page.getByRole('link', { name: '电源参数咨询', exact: true }).click()
    await expect(page.getByRole('button', { name: '当前轮AX24', exact: true })).toBeVisible({ timeout: 3500 })
    await page.getByLabel('问题', { exact: true }).fill('不能重复发送')
    await expect(page.getByRole('button', { name: '发送', exact: true })).toBeDisabled()
    expect(reads).toContain('new-active'); await expect.poll(() => streams.length).toBeGreaterThan(0)
    // 等待潜在旧快照到达，再验证它不能覆盖候选和停止目标。
    await delay(timing.old + 100)
    await expect(page.getByRole('button', { name: '当前轮AX24', exact: true })).toBeVisible()
    await page.getByRole('button', { name: '当前轮AX24', exact: true }).click()
    await page.getByRole('button', { name: '停止', exact: true }).click()
    await expect(page.getByText('已取消', { exact: true })).toBeVisible()
    expect(commands).toEqual(['confirm', 'cancel'])
    await page.getByRole('link', { name: '会话B', exact: true }).click()
    await expect(page.getByText('另一标签页的新问题', { exact: true })).toHaveCount(0)
    await expect(page.getByRole('button', { name: '停止', exact: true })).toHaveCount(0)
    expect(errors).toEqual([])
  })
}

test('恢复快照途中切会话，迟到的旧运行既不覆盖也不订阅', async ({ page }) => {
  let pending = false, release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve }), streams: string[] = []
  await mockApi(page, async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/conversations')) { await route.fulfill({ json: { items: [{ ...conversation, active_run_id: 'late' }, { ...conversation, conversation_id: 'b', title: '安全会话B' }], next_cursor: null } }); return true }
    if (path.endsWith('/runs/late')) {
      pending = true; await gate
      await route.fulfill({ json: { run_id: 'late', conversation_id: 'conversation-a', state: 'awaiting_input', seq: 1, version: 1, answer: '不应出现的旧内容', candidates: [{ product_id: 'late-product', model: '不应出现的旧候选' }], citations: [] } }); return true
    }
    if (path.endsWith('/events')) { streams.push(path); await route.fulfill({ contentType: 'text/event-stream', body: ': 心跳\n\n' }); return true }
    return false
  })
  await page.goto('/chat/conversation-a'); await expect.poll(() => pending).toBe(true)
  await page.getByRole('link', { name: '安全会话B', exact: true }).click(); release()
  await page.getByLabel('问题', { exact: true }).fill('只发B')
  await expect(page.getByRole('button', { name: '发送', exact: true })).toBeEnabled()
  await expect(page.getByText('不应出现的旧内容')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '不应出现的旧候选', exact: true })).toHaveCount(0)
  expect(streams).toEqual([])
})

test('历史尚有后续页时不把旧完成轮当作当前轮，加载末页才恢复新运行', async ({ page }) => {
  const reads: string[] = []
  // 此例只验证分页选轮；有限的route.fulfill流会立即断开，额外触发合法恢复读取。
  // 固定保持连接，继续严格断言只读一次末页运行；断流恢复另有stream用例。
  await page.addInitScript(() => {
    const streams: string[] = []
    Object.assign(window, { paginationStreams: streams })
    window.EventSource = class extends EventTarget {
      constructor(url: string | URL) { super(); streams.push(String(url)) }
      close() {}
    } as unknown as typeof EventSource
  })
  await mockApi(page, async route => {
    const url = new URL(route.request().url()), path = url.pathname
    if (path.endsWith('/messages')) {
      await route.fulfill({ json: url.searchParams.get('cursor')
        ? { items: [{ message_id: 'new', run_id: 'latest', role: 'user', text: '分页中的新问题', ordinal: 3, citations: [] }], next_cursor: null }
        : { items: [{ message_id: 'old', run_id: 'old', role: 'assistant', text: '分页中的旧答案', ordinal: 2, citations: [] }], next_cursor: 'next' } }); return true
    }
    if (path.endsWith('/runs/latest')) { reads.push('latest'); await route.fulfill({ json: { run_id: 'latest', conversation_id: 'conversation-a', state: 'awaiting_input', seq: 1, version: 1, answer: '', candidates: [{ product_id: 'p', model: '末页型号' }], citations: [] } }); return true }
    if (path.endsWith('/events')) { await route.fulfill({ contentType: 'text/event-stream', body: ': 心跳\n\n' }); return true }
    return false
  })
  await page.goto('/chat/conversation-a')
  await page.getByLabel('问题', { exact: true }).fill('等待末页')
  await expect(page.getByRole('button', { name: '发送', exact: true })).toBeDisabled(); expect(reads).toEqual([])
  await page.getByRole('button', { name: '加载更多历史', exact: true }).click()
  await expect(page.getByRole('button', { name: '末页型号', exact: true })).toBeVisible()
  expect(reads).toEqual(['latest'])
  expect(await page.evaluate(() => (window as unknown as { paginationStreams: string[] }).paginationStreams))
    .toEqual(['/api/v1/runs/latest/events?after_seq=1'])
})
