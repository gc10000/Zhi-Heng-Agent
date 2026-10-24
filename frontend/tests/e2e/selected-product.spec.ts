import { test, expect } from '@playwright/test'
import { mockApi, conversation, identity } from './helpers'

test('目录搜索首100项外设备后，新建/切换会话范围可见且发送一致', async ({ page }) => {
  const products = Array.from({ length: 101 }, (_, i) => ({ product_id: `p-${i + 1}`, model: i === 100 ? 'BEYOND-100' : `MODEL-${i + 1}` }))
  const posts: string[][] = []
  await mockApi(page, async route => {
    const url = new URL(route.request().url()), path = url.pathname
    if (path.endsWith('/products')) {
      const selected = url.searchParams.get('search') === 'BEYOND-100'
      await route.fulfill({ json: { items: selected ? products.slice(100) : products.slice(0, 100), next_cursor: selected ? null : 'page-2' } }); return true
    }
    if (path.endsWith('/conversations') && route.request().method() === 'POST') { await route.fulfill({ status: 201, json: { ...conversation, conversation_id: 'new', title: '新会话' } }); return true }
    if (path.endsWith('/conversations')) { await route.fulfill({ json: { items: [conversation, { ...conversation, conversation_id: 'new', title: '新会话' }], next_cursor: null } }); return true }
    if (path.endsWith('/runs') && route.request().method() === 'POST') { posts.push(route.request().postDataJSON().product_ids); await route.fulfill({ status: 409, json: { error: { code: 'busy', message: '测试保留问题。' } } }); return true }
    return false
  })
  await page.goto('/products')
  await page.getByLabel('搜索型号', { exact: true }).fill('BEYOND-100')
  await page.getByRole('button', { name: '搜索', exact: true }).click()
  await page.getByRole('heading', { name: 'BEYOND-100', exact: true }).waitFor()
  await page.getByRole('button', { name: '选择设备', exact: true }).click()
  await page.getByRole('button', { name: '新建会话', exact: true }).click()
  const select = page.getByLabel('本轮适用设备')
  await expect(select).toHaveValue('p-101', { timeout: 2500 })
  await expect(select.locator('option:checked')).toHaveText('BEYOND-100')
  await page.getByRole('link', { name: '电源参数咨询', exact: true }).click()
  await expect(select).toHaveValue('p-101')
  await expect(select.locator('option:checked')).toHaveText('BEYOND-100')
  await page.getByLabel('问题', { exact: true }).fill('核对设备范围')
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await expect.poll(() => posts.length).toBe(1); expect(posts[0]).toEqual(['p-101'])
  await select.selectOption('')
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await expect.poll(() => posts.length).toBe(2); expect(posts[1]).toEqual([])
})

for (const failure of ['失效', '断线', '缓慢']) {
  test(`跨页设备授权核对${failure}时不能从按钮或Enter静默发送`, async ({ page }) => {
    let catalogSelected = false, posts = 0, lookups = 0, release!: () => void
    const gate = new Promise<void>(resolve => { release = resolve })
    const p = { product_id: 'far', model: '远端型号' }
    await mockApi(page, async route => {
      const url = new URL(route.request().url()), path = url.pathname
      if (path.endsWith('/products')) {
        if (url.searchParams.has('search')) {
          if (!catalogSelected) { await route.fulfill({ json: { items: [p], next_cursor: null } }); return true }
          lookups++
          if (failure === '缓慢') await gate
          if (failure === '断线') await route.fulfill({ status: 503, json: { error: { code: 'unavailable', message: '目录暂不可用，请稍后重选。' } } })
          else await route.fulfill({ json: { items: failure === '失效' ? [] : [p], next_cursor: null } })
          return true
        }
        await route.fulfill({ json: { items: [{ product_id: 'first', model: '首屏型号' }], next_cursor: 'more' } }); return true
      }
      if (path.endsWith('/runs') && route.request().method() === 'POST') { posts++; await route.fulfill({ status: 409, json: { error: { code: 'busy', message: '已提交' } } }); return true }
      return false
    })
    await page.goto('/products'); await page.getByLabel('搜索型号', { exact: true }).fill('远端型号')
    await page.getByRole('button', { name: '搜索', exact: true }).click()
    await page.getByRole('heading', { name: '远端型号', exact: true }).waitFor()
    catalogSelected = true; await page.getByRole('button', { name: '选择设备', exact: true }).click()
    await page.getByRole('link', { name: '电源参数咨询', exact: true }).click()
    await expect.poll(() => lookups).toBeGreaterThan(0)
    await page.getByLabel('问题', { exact: true }).fill('未知范围禁止发送')
    if (failure === '缓慢') await expect(page.getByText('正在核对所选设备，核对完成前不能发送。')).toBeVisible()
    else await expect(page.getByRole('alert')).toContainText(failure === '失效' ? '无法核对所选设备' : '目录暂不可用')
    await expect(page.getByRole('button', { name: '发送', exact: true })).toBeDisabled()
    await page.getByLabel('问题', { exact: true }).press('Enter'); expect(posts).toBe(0)
    if (failure === '缓慢') {
      release(); await expect(page.getByLabel('本轮适用设备').locator('option:checked')).toHaveText('远端型号')
      await expect(page.getByRole('button', { name: '发送', exact: true })).toBeEnabled()
    } else {
      await page.getByLabel('本轮适用设备').selectOption('')
      await expect(page.getByRole('button', { name: '发送', exact: true })).toBeEnabled()
    }
  })
}

test('目录分页选中后切知识范围/退出再登录均清除设备ID和描述', async ({ page }) => {
  const posts: string[][] = []
  await mockApi(page, async route => {
    const url = new URL(route.request().url()), path = url.pathname
    if (path.endsWith('/me') || path.endsWith('/auth/login')) { await route.fulfill({ json: { ...identity, user: { ...identity.user, kb_ids: ['kb-test', 'other-kb'] } } }); return true }
    if (path.endsWith('/products')) {
      const more = !!url.searchParams.get('cursor') || url.searchParams.get('search') === '分页型号'
      await route.fulfill({ json: { items: more ? [{ product_id: 'p-101', model: '分页型号' }] : Array.from({ length: 100 }, (_, i) => ({ product_id: `p-${i}`, model: `型号${i}` })), next_cursor: more ? null : 'more' } }); return true
    }
    if (path.endsWith('/runs') && route.request().method() === 'POST') { posts.push(route.request().postDataJSON().product_ids); await route.fulfill({ status: 409, json: { error: { code: 'busy', message: '未改变运行' } } }); return true }
    return false
  })
  async function choose(paginate: boolean) {
    await page.getByRole('link', { name: '设备目录', exact: true }).click()
    if (paginate) await page.getByRole('button', { name: '更多设备', exact: true }).click()
    else { await page.getByLabel('搜索型号', { exact: true }).fill('分页型号'); await page.getByRole('button', { name: '搜索', exact: true }).click() }
    await page.locator('.product-card').filter({ hasText: '分页型号' }).getByRole('button', { name: '选择设备', exact: true }).click()
    await page.getByRole('link', { name: '电源参数咨询', exact: true }).click()
    await expect(page.getByLabel('本轮适用设备').locator('option:checked')).toHaveText('分页型号')
  }
  await page.goto('/chat'); await choose(true)
  await page.getByRole('combobox', { name: /^知识范围/ }).selectOption('other-kb')
  await expect(page).toHaveURL(/\/chat$/)
  await page.getByRole('combobox', { name: /^知识范围/ }).selectOption('kb-test')
  await page.getByRole('link', { name: '电源参数咨询', exact: true }).click()
  await expect(page.getByLabel('本轮适用设备')).toHaveValue('')
  await page.getByLabel('问题', { exact: true }).fill('切范围后')
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await expect.poll(() => posts.length).toBe(1); expect(posts[0]).toEqual([])
  await choose(false)
  await page.getByRole('button', { name: '退出登录', exact: true }).click()
  await page.getByLabel('用户名', { exact: true }).fill('下一用户')
  await page.getByLabel('密码', { exact: true }).fill('测试口令')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await page.getByRole('link', { name: '电源参数咨询', exact: true }).click()
  await expect(page.getByLabel('本轮适用设备')).toHaveValue('')
  await page.getByLabel('问题', { exact: true }).fill('重新登录后')
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await expect.poll(() => posts.length).toBe(2); expect(posts[1]).toEqual([])
})
