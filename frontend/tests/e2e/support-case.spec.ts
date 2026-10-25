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
