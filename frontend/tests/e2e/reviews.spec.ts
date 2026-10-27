import { test, expect } from '@playwright/test'
import { mockApi } from './helpers'

test('新版按题意保存适用性，聊天来源可引用但不预填分数和本人声明',async({page})=>{
  let submitted:any
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/observations')){await route.fulfill({json:{items:[{observation_id:'o1',question_id:'q1',source_message_id:'chat-one',statement:'无需步骤，两图无关',scores:{factuality:2,citation_support:2,actionability:'not_applicable',image_relevance:0},transcriber_kind:'assistant'}]}});return true}
    if(path.endsWith('/reviews')){
      if(route.request().method()==='POST'){submitted=route.request().postDataJSON();await route.fulfill({status:201,json:{...submitted,review_id:'r1'}})}
      else await route.fulfill({json:{subjects:[{question_id:'q1',subject_sha256:'a'.repeat(64)}],items:[]}})
      return true
    }
    if(path.endsWith('/results')){await route.fulfill({json:{items:[{question_id:'q1',question:'兼容性判断',result:{answer:'不可以 [1]',citations:[]}}],next_cursor:null}});return true}
    return false
  })
  await page.goto('/evaluations/reviews/exp-purpose')
  await expect(page.getByLabel('审阅规则',{exact:true})).toHaveValue('question-purpose-v1')
  await expect(page.getByText('无需步骤，两图无关',{exact:true})).toBeVisible()
  await page.getByLabel('引用聊天反馈（不代填评分或本人声明）').selectOption('o1')
  await expect(page.getByLabel('事实正确性',{exact:true})).toHaveValue('unknown')
  await expect(page.getByLabel('已核对原始资料与来源')).not.toBeChecked()
  await page.getByLabel('本题步骤是否适用',{exact:true}).selectOption('no')
  await page.getByLabel('步骤适用性依据',{exact:true}).fill('合成兼容性判断，无配置操作目标。')
  await page.getByLabel('步骤可执行性',{exact:true}).selectOption('not_applicable')
  await page.getByLabel('核对依据或未知原因').fill('合成助手复核，非人工双轮')
  await page.getByRole('button',{name:'保存本轮审阅',exact:true}).click()
  await expect.poll(()=>submitted?.observation_id).toBe('o1')
  expect(submitted.rubric_version).toBe('question-purpose-v1')
  expect(submitted.actionability_applicable).toBe(false)
  expect(submitted.human_attested).toBe(false)
  expect(submitted.reviewer_kind).toBe('assistant')
})

test('新版只默认展示答案图片，关联图展开后才读取，不当作答案配图',async({page})=>{
  const requests:string[]=[]
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.includes('/images/')){requests.push(path);await route.fulfill({contentType:'image/gif',body:Buffer.from('R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=','base64')});return true}
    if(path.endsWith('/reviews')){await route.fulfill({json:{subjects:[{question_id:'q1',subject_sha256:'a'.repeat(64)}],items:[]}});return true}
    if(path.endsWith('/results')){await route.fulfill({json:{items:[{question_id:'q1',question:'兼容性判断',result:{answer:'仅支持本厂控制器 [1]',image_selection_version:1,citations:[{document_sha256:'b'.repeat(64),page:4,asset_sha256:'c'.repeat(64),image_usage:'context'}]}}],next_cursor:null}});return true}
    return false
  })
  await page.goto('/evaluations/reviews/exp-selection')
  await page.getByLabel('审阅规则',{exact:true}).selectOption('legacy-v1')
  await expect(page.locator('article')).toContainText('当前答案没有使用配图')
  await expect(page.locator('article img')).toHaveCount(0)
  expect(requests).toEqual([])
  await expect(page.getByLabel('配图相关性',{exact:true}).locator('option[value="not_applicable"]')).toHaveCount(1)
  await page.getByText('检索关联图（未用于答案）',{exact:true}).click()
  await expect(page.locator('article img')).toBeVisible()
  await expect.poll(()=>requests.length).toBe(1)
})

test('原审核者逐轮追加未知结论，旧记录和确定分数保留，刷新可见',async({page})=>{
  const originals=[1,2].map(round=>({review_id:'original-'+round,question_id:'q1',subject_sha256:'a'.repeat(64),round,
    reviewer_kind:'human',reviewer_id:'offline-user',human_attested:true,source_checked:true,
    scores:{factuality:2,citation_support:1,actionability:'unknown',image_relevance:'unknown'},rationale:'原始未知判断'}))
  const followups:any[]=[];let submitted:any
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/followups')){
      submitted=route.request().postDataJSON()
      const review_id=path.split('/').at(-2)
      const row={...submitted,review_id,followup_id:'followup-'+review_id}
      followups.push(row);await route.fulfill({status:201,json:row});return true
    }
    if(path.endsWith('/reviews')){await route.fulfill({json:{subjects:[{question_id:'q1',subject_sha256:'a'.repeat(64)}],items:originals,followups,next_cursor:null}});return true}
    if(path.endsWith('/results')){await route.fulfill({json:{items:[{question_id:'q1',question:'设备能与任意品牌互通吗？',result:{answer:'合成待审答案',citations:[{document_sha256:'b'.repeat(64),page:4,asset_sha256:'c'.repeat(64)}]}}],next_cursor:null}});return true}
    return false
  })
  await page.goto('/evaluations/reviews/exp-followups')
  await page.getByLabel('审阅规则',{exact:true}).selectOption('legacy-v1')
  await page.getByLabel('审阅身份',{exact:true}).selectOption('human')
  await expect(page.getByText('步骤是否适用',{exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'保存本轮审阅',exact:true})).toBeDisabled()
  await expect(page.locator('#review-submit-help')).toContainText('不可覆盖')
  await expect(page.getByRole('region',{name:'未知项追加复核',exact:true})).toBeVisible()
  for(const round of [1,2]){
    await page.getByLabel('复核轮次',{exact:true}).selectOption(String(round))
    const section=page.getByRole('region',{name:'未知项追加复核',exact:true})
    await expect(section.getByRole('button',{name:'保存追加复核'})).toBeDisabled()
    await expect(section.locator('[aria-live="polite"]')).toContainText('选择')
    await expect(section.locator('[aria-live="polite"]')).toContainText('填写')
    await expect(section.locator('[aria-live="polite"]')).toContainText('本人已重新核对原件')
    await section.getByLabel('复核结论：步骤可执行性',{exact:true}).selectOption('not_applicable')
    await section.getByLabel('复核依据：步骤可执行性',{exact:true}).fill('合成兼容性判断题，不涉及操作步骤；未据此认定真实001得分')
    await section.getByLabel('复核结论：配图相关性',{exact:true}).selectOption('1')
    await section.getByLabel('复核依据：配图相关性',{exact:true}).fill('合成示意图，间接相关；不是实际人工评分')
    await section.getByLabel('本人已重新核对原件与上述依据',{exact:true}).check()
    await section.getByLabel('确认由原审核者本人追加复核',{exact:true}).check()
    await section.getByRole('button',{name:'保存追加复核'}).click()
    await expect(section.getByRole('status')).toContainText('追加复核已保存')
    expect(submitted.resolutions.factuality).toBeUndefined()
    expect(submitted.reviewer_id).toBeUndefined()
  }
  await page.reload()
  await page.getByLabel('审阅规则',{exact:true}).selectOption('legacy-v1')
  await page.getByLabel('审阅身份',{exact:true}).selectOption('human')
  await expect(page.getByRole('region',{name:'未知项追加复核'}).getByRole('status')).toContainText('追加复核已保存')
  expect(followups.length).toBe(2)
  expect(originals[0].scores.actionability).toBe('unknown')
  expect(originals[1].scores.citation_support).toBe(1)
})

test('审阅页显示绑定结果的配图，并解释本轮提交禁用原因',async({page})=>{
  const document='b'.repeat(64),image='c'.repeat(64),subject='a'.repeat(64)
  const imageRequests:string[]=[]
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.includes('/images/')){
      imageRequests.push(path)
      if(path.includes('/5/')){await route.fulfill({status:404,json:{error:{message:'不可用'}}});return true}
      await route.fulfill({status:200,contentType:'image/gif',body:Buffer.from('R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=','base64')})
      return true
    }
    if(path.endsWith('/reviews')){await route.fulfill({json:{subjects:[{question_id:'q-image',subject_sha256:subject}],items:[],next_cursor:null}});return true}
    if(path.endsWith('/results')){await route.fulfill({json:{items:[{question_id:'q-image',question:'核对图示含义',status:'completed',result:{answer:'合成答案',citations:[{document_sha256:document,page:4,asset_sha256:image},{document_sha256:document,page:5,asset_sha256:'d'.repeat(64)}]}}],next_cursor:null}});return true}
    return false
  })
  await page.goto('/evaluations/reviews/exp-image')
  await page.getByLabel('审阅规则',{exact:true}).selectOption('legacy-v1')
  await expect(page.locator('article img')).toHaveCount(0)
  expect(imageRequests).toEqual([])
  await page.getByText('历史图像来源（答案使用关系未记录）',{exact:true}).click()
  const visual=page.getByRole('img',{name:'资料第4页引用配图'})
  await expect(visual).toBeVisible()
  await expect.poll(()=>visual.evaluate(node=>(node as HTMLImageElement).naturalWidth)).toBe(1)
  expect(imageRequests).toContain(`/api/v1/experiments/exp-image/results/q-image/images/${document}/4/${image}`)
  await expect(page.locator('article')).toContainText('这条结果记录了图片来源，但当前图片未能安全读取')

  const button=page.getByRole('button',{name:'保存本轮审阅',exact:true})
  await expect(button).toBeDisabled()
  await expect(page.locator('#review-submit-help')).toContainText('核对依据或未知原因')
  await expect(page.getByLabel('配图相关性',{exact:true}).locator('option[value="not_applicable"]')).toHaveCount(0)
  await page.getByLabel('审阅身份',{exact:true}).selectOption('human')
  await expect(page.locator('#review-submit-help')).toContainText('核对原始资料与来源')
  await expect(page.locator('#review-submit-help')).toContainText('人工本人')
  await page.getByLabel('核对依据或未知原因').fill('离线界面测试文本，不是真实评分')
  await page.getByLabel('已核对原始资料与来源').check()
  await page.getByLabel('确认我是执行本次原件核对的人工本人').check()
  await expect(button).toBeEnabled()
})

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
  await page.getByLabel('审阅规则',{exact:true}).selectOption('legacy-v1')
  await page.getByLabel('核对依据或未知原因').fill('辅助界面测试，不是本人评分')
  await page.getByRole('button',{name:'保存本轮审阅',exact:true}).click()
  await expect(page.locator('#review-saved-notice')).toContainText('第1轮审阅已保存')
  await expect(page.getByRole('button',{name:'保存本轮审阅',exact:true})).toBeDisabled()
  await expect(page.locator('#review-submit-help')).toContainText('不可覆盖')
  await page.reload()
  await expect(page.locator('#review-saved-notice')).toContainText('第1轮审阅已保存')
  await page.getByLabel('审阅规则',{exact:true}).selectOption('legacy-v1')
  await page.getByLabel('复核轮次',{exact:true}).selectOption('2')
  await page.getByLabel('核对依据或未知原因').fill('第二轮辅助界面测试')
  await page.getByRole('button',{name:'保存本轮审阅',exact:true}).click()
  await expect(page.locator('#review-saved-notice')).toContainText('第2轮审阅已保存')
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
  await page.getByLabel('审阅规则',{exact:true}).selectOption('legacy-v1')
  await expect(page.locator('article').getByRole('status')).toContainText('本轮请求确认设备型号，未生成答案')
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
  await page.getByLabel('审阅规则',{exact:true}).selectOption('legacy-v1')
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
