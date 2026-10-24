import {test,expect}from'@playwright/test'
import {mockApi,identity}from'./helpers'
test('查看者不提供上传/发布入口',async({page})=>{
  await mockApi(page,async route=>{if(new URL(route.request().url()).pathname.endsWith('/me')){await route.fulfill({json:{...identity,user:{...identity.user,role:'viewer'}}});return true}return false})
  await page.goto('/documents')
  await expect(page.getByRole('heading',{name:'资料管理',exact:true})).toBeVisible()
  await expect(page.getByText('当前角色仅可查看授权资料。',{exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'上传并导入',exact:true})).toHaveCount(0)
})
test('上传幂等、真实任务错误阶段/重试，完成不冒充已发布',async({page})=>{
  let uploads=0,retries=0,published=false
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname,method=route.request().method()
    if(path.endsWith('/documents')&&method==='POST'){uploads++;await route.fulfill({status:202,json:{document_id:'d',revision_id:'v',job_id:'j',original_asset_id:'a'}});return true}
    if(path.endsWith('/documents')){await route.fulfill({json:{items:[{document_id:'d',name:'隔离资料.md',purpose:'technical',product_ids:[],active_revision_id:published?'v':null}],next_cursor:null}});return true}
    if(path.endsWith('/revisions')){await route.fulfill({json:{items:[{revision_id:'v',status:published?'published':'validated',attempt:1,quality_flags:['missing_page_refs']}],next_cursor:null}});return true}
    if(path.endsWith('/chunks')){await route.fulfill({json:{items:[{chunk_uid:'chunk',ordinal:0,text:'原文参数24V',metadata:{source_refs:[],asset_ids:[]}}],next_cursor:null}});return true}
    if(path.endsWith('/publish')){expect(route.request().postDataJSON().expected_active_revision_id).toBeNull();published=true;await route.fulfill({json:{active_revision_id:'v'}});return true}
    if(path.endsWith('/import-jobs/j/retry')){expect(route.request().postDataJSON().expected_version).toBe(4);retries++;await route.fulfill({json:{state:'pending'}});return true}
    if(path.endsWith('/import-jobs/j')){await route.fulfill({json:{job_id:'j',state:retries?'completed':'failed',stage:retries?'completed':'parse',version:4,attempt:1,retryable:true,error:retries?undefined:{code:'upstream_timeout',stage:'parse'}}});return true}
    return false
  })
  await page.goto('/documents')
  await page.getByLabel('原件文件',{exact:true}).setInputFiles({name:'sample.md',mimeType:'text/markdown',buffer:Buffer.from('# 参数\n24V')})
  await page.getByRole('button',{name:'上传并导入',exact:true}).dblclick()
  await expect(page.getByText('upstream_timeout',{exact:false})).toBeVisible()
  expect(uploads).toBe(1)
  await page.getByRole('button',{name:'重试导入',exact:true}).click()
  await expect(page.getByText('导入任务完成，发布状态以活动修订为准。',{exact:true})).toBeVisible()
  await expect(page.getByText('未发布',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:'管理修订',exact:true}).click()
  await page.getByRole('button',{name:'预览切片',exact:true}).click()
  await expect(page.getByText('原文参数24V',{exact:true})).toBeVisible()
  await expect(page.getByText('missing_page_refs',{exact:false})).toBeVisible()
  await page.getByRole('button',{name:'发布此修订',exact:true}).click()
  await expect(page.getByText('当前活动版本',{exact:true})).toBeVisible()
})
