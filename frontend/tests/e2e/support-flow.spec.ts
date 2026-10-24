import { test, expect } from '@playwright/test'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
test.use({ video: 'on', trace: 'on' })

// 显式独立真实环境；保存运行ID，脚本故障后的续验不重复付费。
test('正式工作台真实设备、澄清、引用、追问、恢复与导入', async ({ page, browser }) => {
  if (!process.env.M3_LIVE_CONFIG) throw new Error('必须指定独立M3_LIVE_CONFIG')
  test.setTimeout(480000)
  const c = JSON.parse(readFileSync(process.env.M3_LIVE_CONFIG, 'utf8'))
  const path = process.env.M3_LIVE_CONFIG.replace(/\.json$/, '.flow.json')
  const report: any = existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : { checks: {}, runs: [], browser: browser.version(), paid_attempts: 0 }
  const save = () => writeFileSync(path, JSON.stringify(report, null, 2))
  const errors: string[] = [], external: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  page.on('request', r => { if (!/^(127\.0\.0\.1|localhost)$/.test(new URL(r.url()).hostname)) external.push(new URL(r.url()).origin) })
  await page.goto('/')
  await page.getByLabel('用户名', { exact: true }).fill(c.username)
  await page.getByLabel('密码', { exact: true }).fill(c.password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByRole('button', { name: '新建会话', exact: true })).toBeVisible()
  report.checks.login = true; save()
  if (!report.url) {
    await page.getByRole('link', { name: '设备目录', exact: true }).click()
    await page.locator('.product-card').filter({ hasText: '隔离设备AX24' }).getByRole('button', { name: '选择设备' }).click()
    await page.getByRole('button', { name: '新建会话', exact: true }).click()
    await expect(page).toHaveURL(/\/chat\/.+/)
    await expect(page.getByLabel('本轮适用设备')).toHaveValue(c.product_ids[0])
    report.checks.choose_device = true; report.url = page.url(); save()
  } else await page.goto(report.url)
  for (let i = 0; i < 2; i++) {
    if (report.checks['answer' + i]) continue
    const send = page.getByRole('button', { name: '发送', exact: true })
    if (!report.runs[i]) {
      await page.getByLabel('本轮适用设备').selectOption(i === 0 ? '' : c.product_ids[0])
      await page.getByLabel('问题', { exact: true }).fill(i === 0 ? '请查询设备输入电压、额定电流及接线注意事项。' : '根据上一轮参数，再说明接线前的安全注意事项，并给出依据。')
      await expect(send).toBeEnabled()
      const pending = page.waitForResponse(r => r.url().endsWith('/runs') && r.request().method() === 'POST')
      await send.click(); const response = await pending; expect(response.status()).toBe(202)
      report.runs[i] = (await response.json()).run_id
      if (i === 1) report.paid_attempts++
      save()
    }
    if (i === 0 && !report.checks.clarification) {
      await expect(page.getByText('请选择适用型号', { exact: true })).toBeVisible({ timeout: 30000 })
      await page.reload()
      await page.getByRole('button', { name: '隔离设备AX24', exact: true }).click()
      report.checks.clarification = true; report.paid_attempts++; save()
    }
    await expect.poll(async () => (await (await page.request.get('/api/v1/runs/' + report.runs[i])).json()).state, { timeout: 240000, intervals: [2000] }).toBe('completed')
    const snapshot = await (await page.request.get('/api/v1/runs/' + report.runs[i])).json()
    report['answer' + i] = snapshot.answer
    expect(snapshot.answer.length).toBeGreaterThan(0); expect(snapshot.citations.length).toBeGreaterThan(0)
    report.checks['answer' + i] = true; save(); await page.reload()
  }
  await expect(page.locator('.message.assistant')).toHaveCount(2)
  await page.getByRole('button', { name: '查看引用 1', exact: true }).first().click()
  await expect(page.getByTestId('citation-text')).toContainText('24V')
  await expect(page.getByRole('link', { name: '下载精确修订原件' })).toBeVisible()
  report.checks.citation_original = true; report.checks.refresh_history = true; save()
  await page.screenshot({ path: '../docs/development/evidence/M3-11-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  // 桌面已选证据在切换窄屏时直接进入模态，不能再点击被遮罩的顶栏。
  if (!await page.getByRole('dialog').isVisible()) await page.getByRole('button', { name: '打开证据', exact: true }).click({ timeout: 10000 })
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByTestId('citation-text')).toContainText('24V')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: '../docs/development/evidence/M3-11-mobile.png', fullPage: true })
  await page.keyboard.press('Escape'); await page.setViewportSize({ width: 1500, height: 960 })
  report.checks.mobile = true; save()
  await page.getByRole('link', { name: '资料管理', exact: true }).click()
  if (!report.upload) {
    await page.getByLabel('原件文件', { exact: true }).setInputFiles({ name: 'm3-ui-isolated.md', mimeType: 'text/markdown', buffer: Buffer.from('# AX24页面导入核验\n\n## 安全要求\n\nAX24接线前必须断电，由合格人员操作。额定电压24V。\n') })
    await page.getByRole('checkbox', { name: '隔离设备AX24', exact: true }).check()
    const pending = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/documents' && r.request().method() === 'POST')
    await page.getByRole('button', { name: '上传并导入', exact: true }).click()
    const response = await pending; expect(response.status()).toBe(202)
    report.upload = await response.json(); save()
  } else await page.goto('/documents?job=' + report.upload.job_id)
  await expect(page.getByText('导入任务完成，发布状态以活动修订为准。', { exact: true })).toBeVisible({ timeout: 180000 })
  await page.getByRole('button', { name: '刷新资料', exact: true }).click()
  const row = page.locator('.document-row').filter({ hasText: 'm3-ui-isolated.md' })
  await expect(row).toContainText('已发布')
  await row.getByRole('button', { name: '管理修订', exact: true }).click()
  await page.getByRole('button', { name: '预览切片', exact: true }).click()
  await expect(page.locator('.chunk-preview').filter({ hasText: '断电' })).toHaveCount(1)
  report.checks.real_upload_published = true
  await page.screenshot({ path: '../docs/development/evidence/M3-11-import.png', fullPage: true })
  report.runtime_errors = errors; report.external_origins = external; save()
  expect(errors).toEqual([]); expect(external).toEqual([])
  report.checks.no_browser_errors_or_external_provider = true; report.passed = Object.values(report.checks).every(Boolean); save()
})
