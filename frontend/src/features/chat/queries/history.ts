import type { Message } from '@/lib/api/types'
export function scopeKey(userId: string, kb: string, kind: string, id = '') { return ['scope', userId, kb, kind, id] }
export function mergeHistory(pages: { items: Message[] }[]) { return [...new Map(pages.flatMap(page => page.items).map(m => [m.message_id, m])).values()].sort((a,b) => a.ordinal - b.ordinal) }
