import { test, expect } from '@playwright/test'
import { mockApi } from './helpers'
test('编号关联准确授权引用，原文/XSS/坏图/无页码状态清楚', async ({ page }) => {
  let forbiddenRequests=0
  const c={citation_id:'c1',document_id:'d',revision_id:'v',text:'准确原文24V',source_refs:[{kind:'markdown',section_path:['电源']}],asset_ids:['broken'],asset_urls:{broken:'/api/v1/assets/broken'}}
  await page.route('**/evil.test/**',async route=>{forbiddenRequests++;await route.abort()})
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/messages')){await route.fulfill({json:{items:[{message_id:'m',run_id:'r',role:'assistant',ordinal:1,text:'输入24V[1] <img src=x onerror="window.__xss=1"> ![跟踪](https://evil.test/x)',citations:[c]}],next_cursor:null}});return true}
    if(path.endsWith('/runs/r')){await route.fulfill({json:{run_id:'r',state:'completed',seq:9,version:4,answer:'输入24V[1]',citations:[c]}});return true}
    if(path.endsWith('/citations/c1')){await route.fulfill({json:c});return true}
    return false
  })
  await page.goto('/chat/conversation-a')
  await page.locator('button.inline-citation').click()
  await expect(page.getByTestId('citation-text')).toContainText('准确原文24V')
  await expect(page.getByText('未提供PDF页码，按章节或单元格溯源。')).toBeVisible()
  await expect(page.getByText('图片暂不可用或授权链接不匹配。')).toBeVisible()
  expect(forbiddenRequests).toBe(0)
  expect(await page.evaluate(()=>('__xss' in window))).toBe(false)
})
