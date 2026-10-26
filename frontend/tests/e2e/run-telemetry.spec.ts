import { test, expect } from '@playwright/test'
import { mockApi } from './helpers'

test('统计页面保留未知与零，分页说明范围，不显示私有内容',async({page})=>{
  await mockApi(page,async route=>{
    const url=new URL(route.request().url())
    if(url.pathname.endsWith('/run-telemetry')){
      await route.fulfill({json:{items:[{run_id:'run-safe-1',state:'completed',total_seconds:0,
        stage_seconds:{answer:0},model:null,token_usage:{input:0,output:null},failure_code:null,
        revision_count:1,logical_provider_calls:null,coverage:'single_run'}],next_cursor:null,coverage:'page_only'}})
      return true
    }
    return false
  })
  await page.goto('/evaluations/runs')
  await expect(page.getByRole('heading',{name:'运行质量统计',exact:true})).toBeVisible()
  await expect(page.getByRole('cell',{name:'0 秒',exact:true})).toBeVisible()
  await expect(page.getByRole('cell',{name:'未采集',exact:true})).toBeVisible()
  await expect(page.getByRole('cell',{name:'0 / 未采集',exact:true})).toBeVisible()
  await expect(page.getByText('仅当前已加载分页；不代表全部运行。',{exact:true})).toBeVisible()
})
