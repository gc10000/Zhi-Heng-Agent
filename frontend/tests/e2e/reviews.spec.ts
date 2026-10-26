import { test, expect } from '@playwright/test'
import { mockApi } from './helpers'

test('已保存轮次明确提示并拦住重复提交，切轮次保留独立身份',async({page})=>{
  let submitted:any,posts=0
  const saved:any[]=[]
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/reviews')){
      if(route.request().method()==='POST'){
        posts++;submitted=route.request().postDataJSON()
        const row={...submitted,review_id:'saved-'+posts,reviewer_id:'offline-user'}
        saved.push(row);await route.fulfill({status:201,json:row})
      }else await route.fulfill({json:{subjects:[{question_id:'q1',subject_sha256:'a'.repeat(64)}],items:saved,next_cursor:null}})
      return true
    }
    if(path.endsWith('/results')){await route.fulfill({json:{items:[{question_id:'q1',question:'合成待审问题',result:{answer:'合成答案',citations:[]}}],next_cursor:null}});return true}
    return false
  })
  await page.goto('/evaluations/reviews/exp-rounds')
  await page.getByLabel('核对依据或未知原因').fill('辅助界面测试，不是本人评分')
  await page.getByRole('button',{name:'保存本轮审阅',exact:true}).click()
  await expect(page.getByRole('status')).toContainText('第1轮审阅已保存')
  await expect(page.getByRole('button',{name:'保存本轮审阅',exact:true})).toBeDisabled()
  await page.reload()
  await expect(page.getByRole('status')).toContainText('第1轮审阅已保存')
  await page.getByLabel('复核轮次',{exact:true}).selectOption('2')
  await page.getByLabel('核对依据或未知原因').fill('第二轮辅助界面测试')
  await page.getByRole('button',{name:'保存本轮审阅',exact:true}).click()
  await expect(page.getByRole('status')).toContainText('第2轮审阅已保存')
  expect(submitted.round).toBe(2);expect(posts).toBe(2)
})

test('真实协议澄清结果不显示为空白答案且保留未知评分',async({page})=>{
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/reviews')){await route.fulfill({json:{subjects:[{question_id:'q-clarify',subject_sha256:'a'.repeat(64)}],items:[],next_cursor:null}});return true}
    if(path.endsWith('/results')){await route.fulfill({json:{items:[{question_id:'q-clarify',question:'未明确设备的查询',status:'completed',result:{behavior:'clarify',answer:'',citations:[]}}],next_cursor:null}});return true}
    return false
  })
  await page.goto('/evaluations/reviews/exp-clarify')
  await expect(page.getByRole('status')).toContainText('本轮请求确认设备型号，未生成答案')
  await expect(page.getByLabel('事实正确性',{exact:true})).toHaveValue('unknown')
  await expect(page.getByRole('button',{name:'保存本轮审阅',exact:true})).toBeDisabled()
})

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
