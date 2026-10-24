// OpenAPI目前未声明动态响应schema；此处逐项对齐实际v1公开字段，输入类型从生成文件导出。
import type { components } from './schema'
export type RunInput = components['schemas']['RunInput']
export interface User { user_id: string; username: string; role: 'viewer' | 'maintainer' | 'admin'; kb_ids: string[] }
export interface Login { user: User; csrf_token: string }
export interface Page<T> { items: T[]; next_cursor: string | null }
export interface Product { product_id: string; model: string; brand?: string; series?: string; aliases?: string[] }
export interface Conversation { conversation_id: string; title: string; kb_id: string; product_ids: string[]; version: number; archived: boolean; active_run_id: string | null }
export interface SourceRef { kind: string; page?: number | null; section_path?: string[]; sheet?: string | null; cell?: string | null; line_start?: number | null; line_end?: number | null; bbox?: number[] | null }
export interface Citation { citation_id: string; document_id: string; revision_id: string; text: string; display_text?: string; source_refs: SourceRef[]; asset_ids: string[]; asset_urls?: Record<string, string>; title?: string; description?: string; original?: {asset_id:string;media_type:string;name:string;url:string}|null }
export interface Run { run_id: string; conversation_id: string; kb_id: string; question: string; state: string; seq: number; version: number; answer: string; citations: Citation[]; stage?: string; error?: { code: string; message?: string; stage?: string }; candidates?: Product[]; product_snapshot?: { product_ids: string[] } }
export interface Message { message_id: string; run_id: string; role: 'user' | 'assistant'; text: string; citations: Citation[]; ordinal: number; product_snapshot?: { product_ids: string[] } }
export interface Document { document_id: string; name: string; purpose: string; kb_id: string; product_ids: string[]; active_revision_id: string | null; active_generation: number }
export interface Revision { revision_id: string; status: string; quality_flags?: string[]; parser_version?: string; attempt: number }
export interface Job { job_id: string; state: string; stage: string; attempt: number; version: number; retryable: boolean; error?: { code: string; stage?: string }; revision_id: string; document_id: string }
export const terminal = (state: string) => ['completed', 'failed', 'cancelled', 'interrupted'].includes(state)
