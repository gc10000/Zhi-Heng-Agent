import { test, expect } from '@playwright/test'
import { mockApi } from './helpers'

test('历史引用不推断答案图，默认折叠且展开后才加载',async({page})=>{
  let reads=0
  const c={citation_id:'c1',document_id:'d',revision_id:'v',text:'原文',source_refs:[],asset_ids:['old'],asset_urls:{old:'/api/v1/assets/old'}}
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/messages')){await route.fulfill({json:{items:[{message_id:'m',run_id:'r',role:'assistant',ordinal:1,text:'原文 [1]',citations:[c]}],next_cursor:null}});return true}
    if(path.endsWith('/runs/r')){await route.fulfill({json:{run_id:'r',state:'completed',seq:9,version:4,answer:'原文 [1]',citations:[c]}});return true}
    if(path.endsWith('/citations/c1')){await route.fulfill({json:c});return true}
    if(path.endsWith('/assets/old')){reads++;await route.fulfill({contentType:'image/gif',body:Buffer.from('R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=','base64')});return true}
    return false
  })
  await page.goto('/chat/conversation-a');await page.locator('button.inline-citation').click()
  const card=page.locator('.evidence-card')
  await expect(card.locator('img')).toHaveCount(0)
  expect(reads).toBe(0)
  await expect(card).toContainText('答案使用关系未记录')
  await card.locator('summary').click()
  await expect(card.locator('img')).toBeVisible()
  await expect.poll(()=>reads).toBe(1)
})

for(const [name,body] of [['列表','1. 接线说明 [1]\n\n    ![图](/api/v1/assets/diagram)'],['转义反引号','\\`![图](/api/v1/assets/diagram)\\` [1]']]){
  test(`${name}图片在正式聊天渲染路径中可见`,async({page})=>{
    const c={citation_id:'c1',document_id:'d',revision_id:'v',text:'原文',source_refs:[],asset_ids:['diagram'],answer_asset_ids:['diagram'],image_selection_version:1}
    await mockApi(page,async route=>{
      const path=new URL(route.request().url()).pathname
      if(path.endsWith('/messages')){await route.fulfill({json:{items:[{message_id:'m',run_id:'r',role:'assistant',ordinal:1,text:body,citations:[c]}],next_cursor:null}});return true}
      if(path.endsWith('/runs/r')){await route.fulfill({json:{run_id:'r',state:'completed',seq:9,version:4,answer:body,citations:[c]}});return true}
      if(path.endsWith('/assets/diagram')){await route.fulfill({contentType:'image/gif',body:Buffer.from('R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=','base64')});return true}
      return false
    })
    await page.goto('/chat/conversation-a')
    await expect(page.locator('.safe-markdown img')).toHaveCount(1)
    await expect(page.locator('.safe-markdown img')).toBeVisible()
  })
}

test('引用工作台区分答案使用图与仅检索关联图',async({page})=>{
  let reads=0
  const c={citation_id:'c1',document_id:'d',revision_id:'v',text:'仅支持本厂控制器',source_refs:[],
    asset_ids:['context'],answer_asset_ids:[],image_selection_version:1,asset_urls:{context:'/api/v1/assets/context'}}
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/messages')){await route.fulfill({json:{items:[{message_id:'m',run_id:'r',role:'assistant',ordinal:1,text:'仅支持本厂控制器 [1]',citations:[c]}],next_cursor:null}});return true}
    if(path.endsWith('/runs/r')){await route.fulfill({json:{run_id:'r',state:'completed',seq:9,version:4,answer:'仅支持本厂控制器 [1]',citations:[c]}});return true}
    if(path.endsWith('/citations/c1')){await route.fulfill({json:c});return true}
    if(path.endsWith('/assets/context')){reads++;await route.fulfill({contentType:'image/gif',body:Buffer.from('R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=','base64')});return true}
    return false
  })
  await page.goto('/chat/conversation-a')
  await page.locator('button.inline-citation').click()
  await expect(page.locator('.evidence-card')).toContainText('未用于答案')
  await expect(page.locator('.evidence-card img')).toHaveCount(0)
  expect(reads).toBe(0)
  await page.locator('.evidence-card summary').click()
  await expect(page.locator('.evidence-card img')).toBeVisible()
})
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
  await page.locator('.evidence-card summary').click()
  await expect(page.getByText('图片暂不可用或授权链接不匹配。')).toBeVisible()
  expect(forbiddenRequests).toBe(0)
  expect(await page.evaluate(()=>('__xss' in window))).toBe(false)
})
