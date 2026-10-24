export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public requestId?: string) { super(message) }
}
export class ApiClient {
  csrf = ''
  constructor(private expired: () => void = () => {}, private send: typeof fetch = fetch) {}
  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers)
    if (!['GET', 'HEAD'].includes(options.method || 'GET') && this.csrf) headers.set('X-CSRF-Token', this.csrf)
    if (typeof options.body === 'string') headers.set('Content-Type', 'application/json')
    const response = await this.send.call(globalThis, '/api/v1' + path, { ...options, headers, credentials: 'same-origin', cache: 'no-store' })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      if (response.status === 401) { this.csrf = ''; this.expired() }
      throw new ApiError(response.status, data?.error?.code || 'http_error', data?.error?.message || errorMessage(response.status), data?.request_id)
    }
    return data as T
  }
  post<T>(path: string, data: unknown) { return this.request<T>(path, { method: 'POST', body: JSON.stringify(data) }) }
}
export function errorMessage(status: number) {
  return ({ 401: '登录已过期，请重新登录。', 403: '当前角色或请求来源无权执行此操作。', 404: '资源不存在或不在授权范围。', 409: '状态已改变或会话正忙，请刷新后重试。', 410: '事件已过期，正在恢复快照。' } as Record<number, string>)[status] || '服务暂不可用，请稍后重试。'
}
export const api = new ApiClient(() => window.dispatchEvent(new Event('session-expired')))
