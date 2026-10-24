import { test, expect } from '@playwright/test'
import { mockApi, conversation } from './helpers'
test('刷新恢复候选、按展示版本确认，409后重新读取，不自动替用户确认', async ({ page }) => {
  let version = 4, confirmed = false, calls = 0
  const snapshot = () => ({ run_id:'r',conversation_id:'conversation-a',kb_id:'kb-test',question:'q',state: confirmed ? 'completed' : 'awaiting_input',seq:version,version,answer:confirmed ? '已完成答案' : '',citations:[],stage:'retrieve',candidates:[{product_id:'p',model:version === 4 ? 'AX24' : 'AX48'}] })
  await mockApi(page, async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/conversations')) { await route.fulfill({json:{items:[{...conversation,active_run_id:'r'}],next_cursor:null}}); return true }
    if (path.endsWith('/runs/r/events')) { await route.fulfill({contentType:'text/event-stream',body:': 心跳\n\n'}); return true }
    if (path.endsWith('/runs/r/confirm-product')) {
      calls++; const body=route.request().postDataJSON()
      if (calls === 1) { expect(body.expected_version).toBe(4); version = 8; await route.fulfill({status:409,json:{error:{code:'version_conflict',message:'型号候选已变化，请重新确认。'}}}) }
      else { expect(body.expected_version).toBe(8); confirmed = true; version=9; await route.fulfill({json:snapshot()}) }
      return true
    }
    if (path.endsWith('/runs/r')) { await route.fulfill({json:snapshot()}); return true }
    return false
  })
  await page.goto('/chat/conversation-a'); await page.reload()
  await expect(page.getByRole('button',{name:'AX24',exact:true})).toBeVisible()
  await expect(page.getByText('等待确认适用型号',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:'AX24',exact:true}).click()
  await expect(page.getByRole('button',{name:'AX48',exact:true})).toBeVisible()
  expect(calls).toBe(1)
  await page.getByRole('button',{name:'AX48',exact:true}).click()
  await expect(page.getByText('回答完成',{exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'AX48',exact:true})).toHaveCount(0)
})
