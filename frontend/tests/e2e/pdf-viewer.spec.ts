import { test,expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { mockApi } from './helpers'
test('PDF本地worker、文本层、旋转高亮与无坐标降级',async({page})=>{
  const raw=Buffer.from(readFileSync('tests/fixtures/one-page.base64.txt','utf8'),'base64')
  const cite={citation_id:'pdf-cite',document_id:'d',revision_id:'v',text:'M3 PDF',source_refs:[{kind:'pdf',page:1,bbox:[.1,.1,.5,.4]}],asset_ids:[],original:{asset_id:'pdf-one',media_type:'application/pdf',name:'manual.pdf',url:'/api/v1/assets/pdf-one'}}
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/messages')){await route.fulfill({json:{items:[{message_id:'m',run_id:'r',role:'assistant',ordinal:1,text:'参数[1]',citations:[cite]}],next_cursor:null}});return true}
    if(path.endsWith('/runs/r')){await route.fulfill({json:{run_id:'r',state:'completed',seq:4,version:1,answer:'参数[1]',citations:[cite]}});return true}
    if(path.endsWith('/citations/pdf-cite')){await route.fulfill({json:cite});return true}
    if(path.endsWith('/assets/pdf-one')){await route.fulfill({contentType:'application/pdf',headers:{'Accept-Ranges':'bytes'},body:raw});return true}
    return false
  })
  await page.goto('/chat/conversation-a');await page.locator('button.inline-citation').click()
  await page.getByRole('button',{name:'打开PDF原件',exact:true}).click()
  await expect(page.locator('.textLayer')).toContainText('M3 local PDF')
  const canvas=page.getByLabel('PDF原件页面'),overlay=page.getByLabel('引用原文区域')
  await expect(overlay).toBeVisible()
  const before=(await canvas.boundingBox())!,box=(await overlay.boundingBox())!
  expect(box.x-before.x).toBeCloseTo(before.width*.1,0)
  await page.getByRole('button',{name:'旋转PDF',exact:true}).click()
  await expect.poll(async()=>Number(await canvas.getAttribute('width'))).toBeGreaterThan(before.width)
  await expect(overlay).toBeVisible()
  await page.getByRole('button',{name:'放大PDF',exact:true}).click()
  await expect(page.getByText('105%',{exact:true})).toBeVisible()
  await expect(overlay).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
})
