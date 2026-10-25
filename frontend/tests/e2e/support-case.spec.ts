import {test,expect} from '@playwright/test'
import {mockApi} from './helpers'

test('处理记录开放，空数据不伪造已完成事实',async({page})=>{
  await mockApi(page,async route=>{
    if(new URL(route.request().url()).pathname.endsWith('/cases')){await route.fulfill({json:{items:[],next_cursor:null}});return true}
    return false
  })
  await page.goto('/cases')
  await expect(page.getByRole('heading',{name:'处理记录',exact:true})).toBeVisible()
  await expect(page.getByText('尚无处理草稿。请从已完成的问答打开支持流程。',{exact:true})).toBeVisible()
})


test('支持澄清持久恢复、纠正与取消不会复活',async({page})=>{
  let context:any={version:0,context_version:0,state:'awaiting_input',reason:'missing_slot',requested_slot:'question',prompt:'请描述需要解决的问题。',run_id:null,
    slots:Object.fromEntries(['question','device','symptom','environment','error_code','tried'].map(k=>[k,{value:null,confirmed:false,source:'unknown'}])),operations:[],citations:[],tool_calls:[]}
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/cases')){await route.fulfill({json:{items:[],next_cursor:null}});return true}
    if(path.endsWith('/support')){
      if(route.request().method()==='POST'){
        const data=route.request().postDataJSON();expect(data.expected_version).toBe(context.version)
        context={...context,version:context.version+1,context_version:context.context_version+1}
        if(data.action==='cancel'){context.state='cancelled';context.prompt='已结束；可保存转交草稿。'}
        else {for(const[k,value]of Object.entries(data.values))context.slots[k]={value,confirmed:true,source:'user_report'};context.run_id='r';context.prompt='请描述实际观察到的现象。';context.requested_slot='symptom'}
      }
      await route.fulfill({json:context});return true
    }
    return false
  })
  await page.goto('/cases?conversation=conversation-a&run=r')
  await page.getByLabel('设备型号',{exact:true}).fill('AX-24')
  await page.getByRole('button',{name:'保存确认信息与纠正',exact:true}).click()
  await expect(page.getByText('上下文版本 1',{exact:false})).toBeVisible()
  await page.reload()
  await expect(page.getByLabel('设备型号',{exact:true})).toHaveValue('AX-24')
  await page.getByRole('button',{name:'结束支持流程',exact:true}).click()
  await page.reload()
  await expect(page.getByRole('button',{name:'保存确认信息与纠正',exact:true})).toBeDisabled()
})


test('草稿编辑须先保存、确认冻结、导出和反馈分别留痕',async({page})=>{
  let record:any={case_id:'case-1',conversation_id:'conversation-a',run_id:'r',kb_id:'kb-test',version:0,status:'draft',fields:{question:'通信失败',summary:'未知'},citations:[{citation_id:'cite-1'}],operations:[],confirmed_at:null}
  let feedbacks=0,exports=0
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname,method=route.request().method()
    if(path.endsWith('/cases')){await route.fulfill({json:{items:[record],next_cursor:null}});return true}
    if(path.endsWith('/cases/case-1')&&method==='PATCH'){const body=route.request().postDataJSON();expect(body.expected_version).toBe(record.version);record={...record,version:record.version+1,fields:{...record.fields,...body.fields}};await route.fulfill({json:record});return true}
    if(path.endsWith('/cases/case-1/confirm')){expect(route.request().postDataJSON().expected_version).toBe(record.version);record={...record,version:record.version+1,status:'confirmed',confirmed_at:'2026-10-25T00:00:00Z'};await route.fulfill({json:record});return true}
    if(path.endsWith('/cases/case-1/export')){exports++;await route.fulfill({json:{filename:'case-1.md',markdown:'# 用户确认记录\n用户自报未解决'}});return true}
    if(path.endsWith('/cases/case-1')){await route.fulfill({json:record});return true}
    if(path.endsWith('/feedback')){feedbacks++;expect(route.request().postDataJSON().run_id).toBe('r');await route.fulfill({status:201,json:{state:'pending_review'}});return true}
    return false
  })
  await page.goto('/cases')
  await page.getByRole('button',{name:'通信失败 · 草稿',exact:true}).click()
  await page.getByLabel('处理摘要',{exact:true}).fill('用户编辑：已试仍无效')
  await expect(page.getByRole('button',{name:'确认保存当前服务端草稿',exact:true})).toBeDisabled()
  await page.getByRole('button',{name:'保存用户编辑',exact:true}).click()
  await expect(page.getByRole('button',{name:'确认保存当前服务端草稿',exact:true})).toBeEnabled()
  await page.getByRole('button',{name:'确认保存当前服务端草稿',exact:true}).click()
  await expect(page.getByLabel('处理摘要',{exact:true})).toBeDisabled()
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'导出已确认 Markdown',exact:true}).click();await download
  await page.getByLabel('反馈类别',{exact:true}).selectOption('operation')
  await page.getByLabel('反馈内容',{exact:true}).fill('步骤仍无效，请补充资料')
  await page.getByRole('button',{name:'提交待审反馈',exact:true}).click()
  await expect(page.getByText('反馈已保存为待审，尚未进入知识库。',{exact:true})).toBeVisible()
  expect(feedbacks).toBe(1);expect(exports).toBe(1)
})
