import type { Page, Route } from '@playwright/test'
export const identity = { user: { user_id: 'offline-user', username: '离线测试', role: 'maintainer', kb_ids: ['kb-test'] }, csrf_token: 'csrf-test' }
export const conversation = { conversation_id: 'conversation-a', kb_id: 'kb-test', title: '电源参数咨询', product_ids: [], version: 0, archived: false, active_run_id: null }
export const product = { product_id: 'product-a', model: 'AX24' }
export type Handler = (route: Route) => Promise<boolean | void>
// 明确的离线协议模拟，不作为真实供应商或阶段全链路证据。
export async function mockApi(page: Page, handler?: Handler) {
  await page.route('**/api/v1/**', async route => {
    if (handler && await handler(route)) return
    const path = new URL(route.request().url()).pathname.replace('/api/v1', '')
    let value: unknown
    if (path === '/me' || path === '/auth/login') value = identity
    else if (path === '/auth/logout') value = { logged_out: true }
    else if (path === '/conversations' && route.request().method() === 'POST') value = conversation
    else if (path === '/conversations') value = { items: [conversation], next_cursor: null }
    else if (path.endsWith('/messages')) value = { items: [], next_cursor: null }
    else if (path === '/products') value = { items: [product], next_cursor: null }
    else if (path === '/documents' || path.endsWith('/documents')) value = { items: [], next_cursor: null }
    else { await route.fulfill({ status: 404, json: { error: { code: 'not_found', message: '离线测试没有此资源。' } } }); return }
    await route.fulfill({ json: value })
  })
}
