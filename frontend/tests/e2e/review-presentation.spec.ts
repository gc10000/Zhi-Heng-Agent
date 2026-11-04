import { test, expect } from '@playwright/test'
import { mockApi } from './helpers'

test('正式审阅呈现公开状态与型号候选，历史无字段仍可审阅', async ({page}) => {
  await mockApi(page, async route => {
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/reviews')){await route.fulfill({json:{subjects:[{question_id:'new',subject_sha256:'a'.repeat(64)},{question_id:'old',subject_sha256:'b'.repeat(64)}],items:[]}});return true}
    if(path.endsWith('/observations')){await route.fulfill({json:{items:[]}});return true}
    if(path.endsWith('/results')){await route.fulfill({json:{items:[
      {question_id:'new',question:'合成待澄清',status:'completed',result:{state:'awaiting_input',behavior:'clarify',answer:'',citations:[],candidates:[{product_id:'p',model:'合成网关 A'}]}},
      {question_id:'old',question:'合成历史回答',status:'completed',result:{answer:'历史正文',citations:[]}}
    ],next_cursor:null}});return true}
    return false
  })
  await page.goto('/evaluations/reviews/presentation')
  await expect(page.getByText('请选择适用型号',{exact:true})).toBeVisible()
  await expect(page.getByText('合成网关 A',{exact:true})).toBeVisible()
  await expect(page.getByText('awaiting_input',{exact:false})).toBeVisible()
  await page.getByLabel('待审问题',{exact:true}).selectOption('old')
  await expect(page.getByText('历史正文',{exact:true})).toBeVisible()
  await expect(page.getByText('合成网关 A',{exact:true})).toHaveCount(0)
})

test('审核页展示运行时冻结的澄清文案、候选与前端来源身份', async ({page}) => {
  const source={component:'frontend/src/features/chat/components/ProductClarification.vue',sha256:'a'.repeat(64)}
  const reviewSource={component:'frontend/src/features/evaluation/ResultPresentation.vue',sha256:'b'.repeat(64)}
  await mockApi(page, async route => {
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/reviews')){await route.fulfill({json:{subjects:[{question_id:'q',subject_sha256:'c'.repeat(64)}],items:[]}});return true}
    if(path.endsWith('/observations')){await route.fulfill({json:{items:[]}});return true}
    if(path.endsWith('/results')){await route.fulfill({json:{items:[{question_id:'q',question:'合成澄清',status:'completed',result:{
      state:'awaiting_input',behavior:'clarify',answer:'',citations:[],candidates:[{product_id:'p',model:'型号甲'}],
      presentation_snapshot:{schema_version:'clarification_presentation_v1',state:'awaiting_input',behavior:'clarify',sha256:'d'.repeat(64),
        chat:{heading:'产品提示甲',body:'冻结产品文案甲',candidates:[{product_id:'p',model:'型号甲',series:'系列甲'}],source},
        review:{state_line:'运行状态：awaiting_input',heading:'审核提示甲',body:'冻结审核文案甲',candidates:[{product_id:'p',model:'型号甲'}],
          empty_candidates_note:null,source:reviewSource}}
    }}],next_cursor:null}});return true}
    return false
  })
  await page.goto('/evaluations/reviews/presentation')
  await expect(page.getByText('审核提示甲',{exact:true})).toBeVisible()
  await expect(page.getByText('冻结审核文案甲',{exact:true})).toBeVisible()
  await expect(page.getByText('型号甲',{exact:true})).toBeVisible()
  await page.getByText('澄清呈现来源',{exact:true}).click()
  await expect(page.getByText(source.component,{exact:true})).toBeVisible()
  await expect(page.getByText(reviewSource.component,{exact:true})).toBeVisible()
  await expect(page.getByText('a'.repeat(64),{exact:true})).toBeVisible()
})

for(const state of ['failed','cancelled','interrupted'])test(`审阅区分${state}而非有效空答案`,async({page})=>{
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/reviews')){await route.fulfill({json:{subjects:[],items:[]}});return true}
    if(path.endsWith('/observations')){await route.fulfill({json:{items:[]}});return true}
    if(path.endsWith('/results')){await route.fulfill({json:{items:[{question_id:'q',question:'合成失败',status:state,result:{}}],next_cursor:null}});return true}
    return false
  })
  await page.goto('/evaluations/reviews/presentation')
  await expect(page.getByText('运行未形成完整答案',{exact:false})).toBeVisible()
})

test('正文编号按正式映射展示，未知页不挤占下一编号',async({page})=>{
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/reviews')){await route.fulfill({json:{subjects:[],items:[]}});return true}
    if(path.endsWith('/observations')){await route.fulfill({json:{items:[]}});return true}
    if(path.endsWith('/results')){await route.fulfill({json:{items:[{question_id:'q',question:'合成引用',status:'completed',result:{
      state:'completed',answer:'断言[2]',citations:[],prompt_reference_map:[{reference_number:2,document_id:'d',revision_id:'r',
        original_sha256:'b'.repeat(64),chunk_uid:'unknown-source',products:['合成设备'],product_status:'snapshot',physical_pages:[],page_status:'unknown'}]
    }}],next_cursor:null}});return true}
    return false
  })
  await page.goto('/evaluations/reviews/presentation')
  await page.getByText('正文编号与来源映射',{exact:true}).click()
  await expect(page.getByText('[2] · 合成设备',{exact:false})).toBeVisible()
  await expect(page.getByText('unknown-source',{exact:false})).toBeVisible()
  await expect(page.getByText('物理页 unknown',{exact:false})).toBeVisible()
})
