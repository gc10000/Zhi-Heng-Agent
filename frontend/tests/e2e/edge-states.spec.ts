import {test,expect}from'@playwright/test'
import {mockApi,conversation}from'./helpers'
test('窄屏长回答、输入法回车、过期登录与按需PDF',async({page})=>{
  let requests=0,expired=false
  const runtimeErrors:string[]=[],pdfRequests:string[]=[]
  page.on('pageerror',e=>runtimeErrors.push(e.message))
  page.on('request',r=>{if(/pdf\.worker|\/pdfjs\/|\/pdfjs-dist\//.test(r.url()))pdfRequests.push(r.url())})
  await page.setViewportSize({width:390,height:844});await page.emulateMedia({reducedMotion:'reduce'})
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/conversations')){await route.fulfill({json:{items:[{...conversation,title:'非常长的设备资料名称'.repeat(60)}],next_cursor:null}});return true}
    if(path.endsWith('/messages')){await route.fulfill({json:{items:[{message_id:'m',run_id:'r',role:'assistant',ordinal:1,text:'长参数'.repeat(4000),citations:[]}],next_cursor:null}});return true}
    if(path.endsWith('/runs/r')){await route.fulfill({json:{run_id:'r',state:'completed',seq:5,version:2,answer:'长参数'.repeat(4000),citations:[]}});return true}
    if(path.endsWith('/runs')&&route.request().method()==='POST'){requests++;expired=true;await route.fulfill({status:401,json:{error:{code:'session_expired',message:'登录已过期，请重新登录。'}}});return true}
    if(expired&&path.endsWith('/me')){await route.fulfill({status:401,json:{error:{code:'session_expired',message:'登录过期'}}});return true}
    return false
  })
  await page.goto('/chat/conversation-a')
  const input=page.getByLabel('问题',{exact:true});await expect(page.getByRole('button',{name:'发送',exact:true})).toBeDisabled()
  await input.fill('输入法选择中');await input.dispatchEvent('compositionstart');await input.press('Enter');expect(requests).toBe(0)
  await input.dispatchEvent('compositionend');await input.press('Shift+Enter');expect(requests).toBe(0)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  expect(pdfRequests).toHaveLength(0)
  await page.getByRole('button',{name:'发送',exact:true}).click()
  await expect(page.getByRole('heading',{name:'登录工作台',exact:true})).toBeVisible()
  expect(requests).toBe(1);expect(runtimeErrors).toEqual([])
})
test('键盘跳到主要内容，409保留问题并给出占用原因',async({page})=>{
  await mockApi(page,async route=>{if(route.request().method()==='POST'&&new URL(route.request().url()).pathname.endsWith('/runs')){await route.fulfill({status:409,json:{error:{code:'conversation_busy',message:'此会话已有运行，请等待或停止。'}}});return true}return false})
  await page.goto('/chat/conversation-a')
  await page.getByRole('link',{name:'跳到主要内容',exact:true}).focus();await page.keyboard.press('Enter')
  await expect(page.locator('#main-content')).toBeFocused()
  await page.getByLabel('问题',{exact:true}).fill('保留的问题')
  await page.getByRole('button',{name:'发送',exact:true}).click()
  await expect(page.getByRole('alert')).toContainText('此会话已有运行')
  await expect(page.getByLabel('问题',{exact:true})).toHaveValue('保留的问题')
})
test('慢来源有等待说明，撤权404不加载原图，403保留操作错误',async({page})=>{
  let release!:()=>void,assets=0
  const gate=new Promise<void>(resolve=>{release=resolve})
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/messages')){await route.fulfill({json:{items:[{message_id:'m',run_id:'r',role:'assistant',ordinal:1,text:'24V[1]',citations:[{citation_id:'c1',text:'24V',asset_ids:['private']}]}],next_cursor:null}});return true}
    if(path.endsWith('/runs/r')){await route.fulfill({json:{run_id:'r',state:'completed',seq:5,version:2,answer:'24V[1]',citations:[]}});return true}
    if(path.endsWith('/citations/c1')){await gate;await route.fulfill({status:404,json:{error:{code:'not_found',message:'来源不存在或无权访问。'}}});return true}
    if(path.includes('/assets/')){assets++;await route.abort();return true}
    if(path.endsWith('/runs')&&route.request().method()==='POST'){await route.fulfill({status:403,json:{error:{code:'forbidden',message:'当前身份无权执行此操作。'}}});return true}
    return false
  })
  await page.goto('/chat/conversation-a');await page.locator('button.inline-citation').click()
  await expect(page.getByText('正在读取授权来源…')).toBeVisible();release()
  await expect(page.getByRole('alert')).toContainText('来源不存在或无权访问');expect(assets).toBe(0)
  await page.getByLabel('问题',{exact:true}).fill('需要权限的问题');await page.getByRole('button',{name:'发送',exact:true}).click()
  await expect(page.locator('.chat-page [role=alert]')).toContainText('无权执行');await expect(page.getByLabel('问题',{exact:true})).toHaveValue('需要权限的问题')
})
test('390px大幅登记图片在抽屉内收缩，焦点可退出',async({page})=>{
  await page.setViewportSize({width:390,height:844})
  await mockApi(page,async route=>{
    const path=new URL(route.request().url()).pathname
    const citation={citation_id:'c1',text:'登记图像',asset_ids:['large'],asset_urls:{large:'/api/v1/assets/large'},source_refs:[]}
    if(path.endsWith('/messages')){await route.fulfill({json:{items:[{message_id:'m',run_id:'r',role:'assistant',ordinal:1,text:'图示[1]',citations:[citation]}],next_cursor:null}});return true}
    if(path.endsWith('/runs/r')){await route.fulfill({json:{run_id:'r',state:'completed',seq:5,version:2,answer:'图示[1]',citations:[citation]}});return true}
    if(path.endsWith('/citations/c1')){await route.fulfill({json:citation});return true}
    if(path.endsWith('/assets/large')){await route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="8000" height="4000"><rect width="8000" height="4000" fill="teal"/></svg>'});return true}
    return false
  })
  await page.goto('/chat/conversation-a');await page.locator('button.inline-citation').click()
  const dialog=page.getByRole('dialog');await expect(dialog).toBeVisible()
  const img=dialog.locator('img');await expect(img).toBeVisible()
  expect(await img.evaluate(el=>el.getBoundingClientRect().width<=innerWidth)).toBe(true)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.keyboard.press('Escape');await expect(dialog).not.toBeVisible()
})
