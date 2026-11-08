export interface ErrorAdvice {
  title: string
  advice: string
  action?: { label: string; to?: string; retry?: boolean }
}

/** 错误码 → 人话化文案映射。未命中 code 时回退显示后端 message 原文。 */
export const ERROR_CODES: Record<string, ErrorAdvice> = {
  product_selection_required: {
    title: '型号候选过多',
    advice: '该问题匹配到多个设备型号，无法确定唯一适用资料。请到设备目录选择或确认型号后重试。',
    action: { label: '去设备目录选择', to: '/products' },
  },
  generation_failed: {
    title: '回答生成失败',
    advice: '模型生成回答时出错，内容尚未写入。可直接重试；若多次失败请稍后再试。',
    action: { label: '重试', retry: true },
  },
  retrieval_empty: {
    title: '未检索到适用资料',
    advice: '当前知识范围内没有找到与问题和设备匹配的资料。请检查设备型号是否正确，或到资料管理上传对应手册。',
    action: { label: '检查设备或上传资料', to: '/documents' },
  },
  budget_exceeded: {
    title: '输入超出预算，请精简问题',
    advice: '问题过长超出单次处理预算。请拆分为更具体的小问题后重试。',
  },
  network: {
    title: '连接中断',
    advice: '与服务的连接中断，可能是网络波动。请检查网络后重试。',
    action: { label: '重试', retry: true },
  },
}

/** 网络类错误码（fetch 失败时 client 通常抛出的类型）。 */
export const NETWORK_HINTS = ['network', 'fetch', 'timeout', 'connection'] as const

export function isNetworkCode(code: string) {
  const lower = code.toLowerCase()
  return NETWORK_HINTS.some(h => lower.includes(h))
}

/** 由错误 code（及可选的后端 message）解析人话化信息。 */
export function resolveError(code: string | undefined, message?: string): { code: string; advice?: ErrorAdvice; raw?: string } {
  const rawCode = code || ''
  if (rawCode && ERROR_CODES[rawCode]) return { code: rawCode, advice: ERROR_CODES[rawCode], raw: message }
  if (rawCode && isNetworkCode(rawCode)) return { code: rawCode, advice: ERROR_CODES.network, raw: message }
  return { code: rawCode || 'unknown', raw: message }
}
