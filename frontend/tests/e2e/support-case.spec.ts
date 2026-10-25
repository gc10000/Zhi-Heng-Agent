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
