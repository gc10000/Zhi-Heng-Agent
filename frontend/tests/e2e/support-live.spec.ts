import {test,expect} from '@playwright/test'
import {readFileSync,writeFileSync,existsSync} from 'node:fs'
test.use({trace:'on',video:'on'})

test('真实新进程支持流程、用户确认与导出反馈',async({page,browser},testInfo)=>{
  if(!process.env.M5_LIVE_CONFIG)throw new Error('必须显式指定M5_LIVE_CONFIG')
  test.setTimeout(480000)
  const config=JSON.parse(readFileSync(process.env.M5_LIVE_CONFIG,'utf8'))
  const path=process.env.M5_LIVE_CONFIG.replace(/\.json$/,'.flow.json')
  const report:any=existsSync(path)?JSON.parse(readFileSync(path,'utf8')):{passed:false,checks:{},new_runs:[],query_requests:0,browser:browser.version(),mode:'real_api_browser_with_reused_supplier_evidence'}
  const save=()=>writeFileSync(path,JSON.stringify(report,null,2))
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message))
  await page.goto('/login')
  await page.getByLabel('用户名',{exact:true}).fill(config.username)
  await page.getByLabel('密码',{exact:true}).fill(config.password)
  await page.getByRole('button',{name:'登录',exact:true}).click()
  await expect(page.getByRole('button',{name:'新建会话',exact:true})).toBeVisible()
  const supportUrl=`/cases?conversation=${config.conversation_id}&run=${config.initial_run_id}`
  if(!report.checks.operation_report){
    await page.goto(supportUrl)
    await page.getByLabel('设备型号',{exact:true}).fill('隔离设备AX24')
    await page.getByLabel('实际现象',{exact:true}).fill('通信指示灯熄灭，尚未解决')
    await page.getByRole('button',{name:'保存确认信息与纠正',exact:true}).click()
    await expect(page.getByText('可依据资料生成待核对的操作清单',{exact:false})).toBeVisible()
    await page.getByRole('button',{name:'依据本轮引用生成清单',exact:true}).click()
    const list=page.getByRole('region',{name:'操作清单',exact:true}).first()
    await expect(list.getByRole('heading',{name:'资料建议',exact:true})).toBeVisible()
    await page.reload()
    await expect(page.getByLabel('设备型号',{exact:true})).toHaveValue('隔离设备AX24')
    await list.getByLabel('实际结果',{exact:true}).fill('用户自报：已断电核对接线，重新上电后仍无通信；请勿重复此步骤。')
    await list.getByRole('button',{name:'记录无效',exact:true}).click()
    await expect(page.getByText('已有可追溯步骤均被用户记录为无效',{exact:false})).toBeVisible()
    report.checks.operation_report=true;save()
    await page.screenshot({path:path.replace('.json','.operation.png'),fullPage:true})
  }
  await page.goto('/chat/'+config.conversation_id)
  if(!report.new_runs.length||report.retry_after_setup){
    await page.getByLabel('问题',{exact:true}).fill('根据已记录的实际结果，通信仍未解决。请不要重复无效步骤；若资料不足请明确建议转交人工，并保留引用依据。')
    await expect(page.getByRole('button',{name:'发送',exact:true})).toBeEnabled()
    const response=page.waitForResponse(r=>r.url().endsWith('/runs')&&r.request().method()==='POST')
    await page.getByRole('button',{name:'发送',exact:true}).click()
    const accepted=await response;expect(accepted.status()).toBe(202)
    report.new_runs.push((await accepted.json()).run_id);report.query_requests=report.new_runs.length;report.retry_after_setup=false;save()
  }
  const rid=report.new_runs.at(-1)
  let run:any
  await expect.poll(async()=>{const response=await page.request.get('/api/v1/runs/'+rid);expect(response.status()).toBe(200);run=await response.json();return run.state},{timeout:240000}).toMatch(/completed|failed|interrupted|cancelled/)
  expect(run.state,JSON.stringify(run.error)).toBe('completed')
  expect(run.citations.length).toBeGreaterThan(0)
  report.checks.real_followup_completed=true;report.answer=run.answer;report.citation_ids=run.citations.map((c:any)=>c.citation_id);save()
  await page.goto(`/cases?conversation=${config.conversation_id}&run=${rid}`)
  if(!report.case_id){
    const response=page.waitForResponse(r=>r.url().endsWith('/cases')&&r.request().method()==='POST')
    await page.getByRole('button',{name:'生成转交草稿',exact:true}).click()
    const created=await response;expect(created.status()).toBe(201);report.case_id=(await created.json()).case_id;save()
  }else{
    const savedCase=await page.request.get('/api/v1/cases/'+report.case_id)
    expect(savedCase.status()).toBe(200)
    const value=await savedCase.json()
    await page.getByRole('button',{name:value.fields.question+' · '+(value.status==='draft'?'草稿':'用户已确认'),exact:true}).click()
  }
  if(!report.checks.confirmed){
    await page.getByLabel('处理摘要',{exact:true}).fill('用户确认转交：设备通信仍未解决；已断电核对接线但无效。环境和错误码未知，需要人工支持。')
    await page.getByRole('button',{name:'保存用户编辑',exact:true}).click()
    await expect(page.getByRole('button',{name:'确认保存当前服务端草稿',exact:true})).toBeEnabled()
    await page.getByRole('button',{name:'确认保存当前服务端草稿',exact:true}).click()
    await expect(page.getByRole('button',{name:'导出已确认 Markdown',exact:true})).toBeVisible()
    report.checks.confirmed=true;save()
  }
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'导出已确认 Markdown',exact:true}).click();const artifact=await download;await artifact.saveAs(existsSync(path.replace('.json','.export.md'))?testInfo.outputPath('export.md'):path.replace('.json','.export.md'))
  report.checks.exported=true;save()
  if(!report.feedback_id){
    await page.getByLabel('反馈类别',{exact:true}).selectOption('operation')
    await page.getByLabel('反馈内容',{exact:true}).fill('真实验收用户自报仍未解决，需要补充排障资料。')
    const response=page.waitForResponse(r=>r.url().endsWith('/feedback')&&r.request().method()==='POST')
    await page.getByRole('button',{name:'提交待审反馈',exact:true}).click()
    const saved=await response;expect(saved.status()).toBe(201);const value=await saved.json();expect(value.state).toBe('pending_review');report.feedback_id=value.feedback_id;save()
  }
  expect(errors).toEqual([])
  report.checks.feedback_pending=true;report.checks.browser_no_errors=true;report.passed=true;save()
  await page.screenshot({path:testInfo.outputPath('confirmed.png'),fullPage:true})
})
