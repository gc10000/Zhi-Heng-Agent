import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
test('真实浏览器登录调用保留原生fetch上下文', async ({ page }) => {
  test.skip(!process.env.M3_LIVE_CONFIG, '需独立真实API环境')
  const c = JSON.parse(readFileSync(process.env.M3_LIVE_CONFIG!, 'utf8'))
  await page.goto('/')
  await page.getByLabel('用户名', { exact: true }).fill(c.username)
  await page.getByLabel('密码', { exact: true }).fill(c.password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByRole('button', { name: '新建会话', exact: true })).toBeVisible()
})
