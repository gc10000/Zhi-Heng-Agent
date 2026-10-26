import { test, expect } from '@playwright/test'
import { mockApi } from './helpers'

test('反馈确认只生成待复核草稿，保留运行和修订来源',async({page})=>{
  let reviewed=false
  const row={feedback_id:'f-1',run_id:'r-1',kb_id:'kb-test',state:'pending_review',version:0,category:'operation',note:'合成反馈：缺少检查前提',citations:[{document_id:'doc-1',revision_id:'rev-1'}]}
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/feedback/f-1/review')){const data=route.request().postDataJSON();expect(data.expected_version).toBe(0);expect(data.decision).toBe('confirm');expect(data.destination).toBe('regression');reviewed=true;await route.fulfill({json:{...row,state:'confirmed',version:1,draft:{draft_id:'draft-1',annotation_status:'draft',run_id:'r-1',source_revisions:[{document_id:'doc-1',revision_id:'rev-1'}],publication_state:'requires_affected_then_full_regression'}}});return true}
    if(path.endsWith('/feedback')){await route.fulfill({json:{items:[{...row,state:reviewed?'confirmed':'pending_review',version:reviewed?1:0,...(reviewed?{draft:{draft_id:'draft-1',annotation_status:'draft',run_id:'r-1',source_revisions:[{document_id:'doc-1',revision_id:'rev-1'}],publication_state:'requires_affected_then_full_regression'}}:{})}],next_cursor:null}});return true}
    return false
  })
  await page.goto('/evaluations/feedback')
  await expect(page.getByRole('heading',{name:'反馈审核',exact:true})).toBeVisible()
  await page.getByLabel('审核理由').fill('核对原件后确认')
  await page.getByLabel('草稿问题').fill('设备检查前提是什么？')
  await page.getByLabel('草稿预期').fill('应先核对断电前提')
  await page.getByRole('button',{name:'确认并保存草稿',exact:true}).click()
  await expect(page.getByText('待复核草稿',{exact:true})).toBeVisible()
  await expect(page.getByText('doc-1 · rev-1',{exact:true})).toBeVisible()
  expect(reviewed).toBe(true)
  await expect(page.getByRole('button',{name:'发布知识',exact:true})).toHaveCount(0)
})
