import { test, expect } from '@playwright/test'
test('登录入口键盘可用且窄屏无溢出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '登录工作台' })).toBeVisible()
  await page.getByLabel('用户名', { exact: true }).focus()
  await page.keyboard.press('Tab')
  await expect(page.getByLabel('密码', { exact: true })).toBeFocused()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
