import { describe, it, expect, vi } from 'vitest'
import { ApiClient, ApiError } from '@/lib/api/client'

describe('Cookie身份与公开错误', () => {
  it('写请求携带同源Cookie和CSRF，不替换FormData的Content-Type', async () => {
    let received: RequestInit = {}
    const client = new ApiClient(() => {}, async (_url, init) => { received = init!; return new Response('{}') })
    client.csrf = 'public-csrf'
    const form = new FormData(); form.set('kb_id', 'k')
    await client.request('/documents', { method: 'POST', body: form })
    expect(received.credentials).toBe('same-origin')
    expect(new Headers(received.headers).get('X-CSRF-Token')).toBe('public-csrf')
    expect(new Headers(received.headers).has('Content-Type')).toBe(false)
  })
  it.each([401, 403, 409, 410])('HTTP %i传播状态和脱敏错误码，只有401清理身份', async (status) => {
    const expired = vi.fn()
    const client = new ApiClient(expired, async () => new Response(JSON.stringify({ error: { code: 'test_code', message: '中文错误' }, request_id: 'request' }), { status }))
    await expect(client.request('/me')).rejects.toMatchObject({ status, code: 'test_code', message: '中文错误' })
    expect(expired).toHaveBeenCalledTimes(status === 401 ? 1 : 0)
  })
  it('非JSON失败也转换成可读错误，不泄露HTML响应', async () => {
    const client = new ApiClient(() => {}, async () => new Response('<secret>proxy</secret>', { status: 502 }))
    await expect(client.request('/me')).rejects.toBeInstanceOf(ApiError)
  })
})
