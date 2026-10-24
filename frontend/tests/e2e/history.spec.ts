import { test, expect } from '@playwright/test'
import { mockApi, conversation } from './helpers'
test('URL恢复答案/引用，切换会话清除旧答案', async ({ page }) => {
  await mockApi(page, async route => {
    const path = new URL(route.request().url()).pathname
    let value
    if (path.endsWith('/conversations')) value = { items: [conversation, { ...conversation, conversation_id: 'conversation-b', title: '另一会话' }], next_cursor: null }
    else if (path.endsWith('/conversation-a/messages')) value = { items: [{ message_id: 'message-a', run_id: 'run-a', ordinal: 2, role: 'assistant', text: '持久答案24V', citations: [{ citation_id: 'cite-a', text: '24V', source_refs: [], asset_ids: [] }] }], next_cursor: null }
    else if (path.endsWith('/runs/run-a')) value = { run_id: 'run-a', conversation_id: 'conversation-a', state: 'completed', seq: 12, version: 8, answer: '持久答案24V', citations: [] }
    else return false
    await route.fulfill({ json: value }); return true
  })
  await page.goto('/chat/conversation-a')
  await expect(page.getByText('持久答案24V', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '查看引用 1' })).toBeVisible()
  await page.reload()
  await expect(page.getByText('持久答案24V', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: '另一会话', exact: true }).click()
  await expect(page.getByText('持久答案24V', { exact: true })).toHaveCount(0)
})
