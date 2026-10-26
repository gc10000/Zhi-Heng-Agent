import { test, expect } from '@playwright/test'
import { mockApi, identity } from './helpers'

test('实验页展示真实状态、题级来源与基线差异，取消和重试带版本', async ({ page }) => {
  let run:any={experiment_id:'exp-1',state:'running',version:2,attempt:1,eval_set_id:'set',eval_set_version:'r1',config_id:'control',config_version:'v1',selected_questions:35,completed:1,retryable:false}
  let creates=0,cancels=0
  await mockApi(page,async route=>{
    const url=new URL(route.request().url()),path=url.pathname.replace('/api/v1',''),method=route.request().method()
    const item={eval_set_id:'set',version:'r1',configs:[{id:'control',version:'v1',strategy:'m3-baseline'}],dev_count:35,review_eligible_count:0}
    if(path==='/eval-sets'){await route.fulfill({json:{items:[item],next_cursor:null}});return true}
    if(path==='/eval-catalog'){await route.fulfill({json:{items:[],next_cursor:null}});return true}
    if(path==='/experiments'){
      if(method==='POST'){creates++;const data=route.request().postDataJSON();expect(data.eval_set_id).toBe('set');expect(data.config_id).toBe('control');expect(data.config_path).toBeUndefined();await route.fulfill({status:202,json:run})}
      else await route.fulfill({json:{items:[run],next_cursor:null}})
      return true
    }
    if(path==='/experiments/exp-1/cancel'){cancels++;expect(route.request().postDataJSON().expected_version).toBe(2);run={...run,state:'cancel_requested',version:3};await route.fulfill({json:run});return true}
    if(path==='/experiments/exp-1/results'){
      await route.fulfill({json:{items:[{question_id:'q1',question:'额定电压？',category:'parameter',status:'completed',result:{answer:'合成离线协议答案24V',citations:[{document_sha256:'a'.repeat(64),page:2}]},metrics:{human_answer_correctness:null},baseline:{answer:'旧答案',status:'completed'},difference:{answer_changed:true}}],next_cursor:null}});return true
    }
    if(path==='/experiments/exp-1'){await route.fulfill({json:run});return true}
    return false
  })
  await page.goto('/evaluations')
  await expect(page.getByRole('heading',{name:'评测实验',exact:true})).toBeVisible()
  await page.getByLabel('题集版本',{exact:true}).selectOption('set/r1')
  await page.getByRole('button',{name:'创建开发集实验',exact:true}).click()
  await expect(page.getByText('合成离线协议答案24V',{exact:true})).toBeVisible()
  await expect(page.getByText('物理页 2',{exact:false})).toBeVisible()
  await expect(page.getByText('旧答案',{exact:true})).toBeVisible()
  await expect(page.getByText('答案语义正确性：未审核',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:'取消实验',exact:true}).click()
  await expect(page.getByText('正在等待当前题边界取消',{exact:true})).toBeVisible()
  expect(creates).toBe(1);expect(cancels).toBe(1)
})

test('普通用户不能创建评测，空数据不显示假指标',async({page})=>{
  let experiments=0
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/me')){await route.fulfill({json:{...identity,user:{...identity.user,role:'viewer'}}});return true}
    if(path.includes('experiment')||path.includes('eval-')){experiments++;return false}
    return false
  })
  await page.goto('/evaluations')
  await expect(page.getByText('当前角色没有评测维护权限。',{exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'创建开发集实验',exact:true})).toHaveCount(0)
  expect(experiments).toBe(0)
})

test('失败实验可带版本重试，空结果与未知成本明确显示',async({page})=>{
  let version=4,retried=0
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    const row={experiment_id:'failed-1',state:retried?'pending':'failed',version,retryable:!retried,attempt:1,eval_set_id:'set',eval_set_version:'r1',config_id:'control'}
    if(path.endsWith('/retry')){expect(route.request().postDataJSON().expected_version).toBe(4);retried++;version++;await route.fulfill({status:202,json:{...row,state:'pending',version}});return true}
    if(path.endsWith('/experiments')){await route.fulfill({json:{items:[row],next_cursor:null}});return true}
    if(path.endsWith('/results')||path.endsWith('/eval-sets')||path.endsWith('/eval-catalog')){await route.fulfill({json:{items:[],next_cursor:null}});return true}
    if(path.endsWith('/failed-1')){await route.fulfill({json:row});return true}
    return false
  })
  await page.goto('/evaluations')
  await page.getByRole('button',{name:'查看 failed-1',exact:true}).click()
  await expect(page.getByText('尚无可见题级结果。',{exact:true})).toBeVisible()
  await expect(page.getByText('精确成本：未采集',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:'重试失败实验',exact:true}).click()
  expect(retried).toBe(1)
})
