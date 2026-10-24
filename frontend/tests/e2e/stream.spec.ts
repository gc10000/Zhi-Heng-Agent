import { test, expect } from '@playwright/test'
import { mockApi } from './helpers'
test('SSE失败保留部分答案、去重且提供新运行重试', async ({ page }) => {
  const run = { run_id:'r',conversation_id:'conversation-a',kb_id:'kb-test',question:'参数是什么',state:'running',seq:0,version:1,answer:'',citations:[] }
  await mockApi(page, async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/runs') && route.request().method() === 'POST') { await route.fulfill({status:202,json:run}); return true }
    if (path.endsWith('/runs/r/events')) {
      const events = [{seq:3,type:'answer.delta',payload:{text:'部分答案'}},{seq:3,type:'answer.delta',payload:{text:'部分答案'}},{seq:7,type:'run.failed',payload:{error:{code:'query_execution_failed',stage:'generate'}}}]
      await route.fulfill({contentType:'text/event-stream',body:events.map(e=>`id: ${e.seq}\nevent: ${e.type}\ndata: ${JSON.stringify({...e,run_id:'r'})}\n\n`).join('')}); return true
    }
    if (path.endsWith('/runs/r')) { await route.fulfill({json:{...run,state:'failed',seq:7,answer:'部分答案'}}); return true }
    return false
  })
  await page.goto('/chat/conversation-a')
  await page.getByLabel('问题',{exact:true}).fill('参数是什么')
  await page.getByRole('button',{name:'发送',exact:true}).click()
  await expect(page.getByTestId('live-answer')).toHaveText('部分答案')
  await expect(page.getByText('回答失败，部分内容仅供核对',{exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'重新提问',exact:true})).toBeVisible()
  await expect(page.getByText('回答完成',{exact:true})).toHaveCount(0)
})
