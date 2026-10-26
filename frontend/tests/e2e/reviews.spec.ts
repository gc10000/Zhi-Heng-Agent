import { test, expect } from '@playwright/test'
import { mockApi } from './helpers'

test('审阅绑定题级结果、分离辅助身份，未知不会伪装通过',async({page})=>{
  let submitted:any, calibration=0
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/reviews')){
      if(route.request().method()==='POST'){submitted=route.request().postDataJSON();await route.fulfill({status:201,json:{...submitted,review_id:'review-1',reviewer_id:'test-maintainer'}})}
      else await route.fulfill({json:{subjects:[{question_id:'q1',subject_sha256:'a'.repeat(64)}],items:submitted?[{...submitted,review_id:'review-1',reviewer_id:'test-maintainer'}]:[],next_cursor:null}})
      return true
    }
    if(path.endsWith('/results')){await route.fulfill({json:{items:[{question_id:'q1',question:'合成问题',result:{answer:'合成待审答案',citations:[{document_sha256:'b'.repeat(64),page:2}]}}],next_cursor:null}});return true}
    if(path.endsWith('/calibrations')){calibration++;await route.fulfill({status:409,json:{error:{code:'human_review_required',message:'缺少人工两轮核对'}}});return true}
    return false
  })
  await page.goto('/evaluations/reviews/exp-1')
  await expect(page.getByRole('heading',{name:'答案审阅',exact:true})).toBeVisible()
  await expect(page.getByText('合成待审答案',{exact:true})).toBeVisible()
  await page.getByLabel('审阅身份',{exact:true}).selectOption('assistant')
  await page.getByLabel('核对依据或未知原因').fill('尚未核对原件，保留未知')
  await page.getByRole('button',{name:'保存本轮审阅',exact:true}).click()
  await expect.poll(()=>submitted?.question_id).toBe('q1')
  expect(submitted.subject_sha256).toBe('a'.repeat(64));expect(submitted.reviewer_id).toBeUndefined()
  expect(submitted.scores.factuality).toBe('unknown');expect(submitted.human_attested).toBe(false)
  await page.getByLabel('基线校准说明').fill('不能将辅助审核计作人工')
  await page.getByRole('button',{name:'冻结基线门槛',exact:true}).click()
  await expect(page.getByRole('alert')).toContainText('缺少人工两轮核对')
  expect(calibration).toBe(1)
})
