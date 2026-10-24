import MarkdownIt from 'markdown-it'
import type { Citation } from '@/lib/api/types'
export function renderEvidence(text: string, citations: Citation[] = [], allowedAssets: string[] = []): string {
  const md = new MarkdownIt({ html: false, linkify: false, breaks: true })
  const escape = md.utils.escapeHtml
  md.core.ruler.push('controlled-links', state => {
    for (const block of state.tokens) {
      const stack: boolean[] = []
      for (const token of block.children || []) {
        if (token.type === 'link_open') {
          const safe = /^https?:\/\//i.test(token.attrGet('href') || '')
          stack.push(safe)
          if (!safe) { token.tag = 'span'; token.attrs = [] }
          else { token.attrSet('rel','noopener noreferrer'); token.attrSet('target','_blank') }
        } else if (token.type === 'link_close') { if (!stack.pop()) token.tag = 'span' }
        if (token.type === 'text') token.meta = { citationAllowed: stack.length === 0 }
      }
    }
  })
  md.renderer.rules.text = (tokens, index) => {
    const token = tokens[index], safe = escape(token.content)
    if (!token.meta?.citationAllowed) return safe
    return safe.replace(/\[(\d+)\]/g, (label, number) => {
      const c = citations[Number(number) - 1]
      return c ? `<button type="button" class="inline-citation" data-citation-id="${escape(c.citation_id)}" aria-label="查看引用 ${Number(number)}">${label}</button>` : label
    })
  }
  md.renderer.rules.image = (tokens,index) => {
    const target = tokens[index].attrGet('src') || ''
    const id = target.startsWith('asset://') ? target.slice(8) : target.startsWith('/api/v1/assets/') ? target.slice(15) : ''
    if (!/^[A-Za-z0-9_-]+$/.test(id) || !allowedAssets.includes(id)) return '<span class="muted">（图片未在授权来源中登记）</span>'
    return `<img src="/api/v1/assets/${encodeURIComponent(id)}" alt="${escape(tokens[index].content)}" loading="lazy">`
  }
  return md.render(text)
}
