<script setup lang="ts">
import { computed,ref,watch } from 'vue'
import { useRoute,useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { api } from '@/lib/api/client'
import type { Document, Product } from '@/lib/api/types'
import { usePages } from './queries'
import ImportJobPanel from './ImportJobPanel.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Badge from '@/components/ui/Badge.vue'
import { Upload, FileText, FileSpreadsheet, FileCode, File } from 'lucide-vue-next'
import ImportJobsFold from './components/ImportJobsFold.vue'
import RevisionPanel from './RevisionPanel.vue'
const auth=useAuthStore(),route=useRoute(),router=useRouter(),search=ref(''),file=ref<File>(),purpose=ref('technical'),productIds=ref<string[]>([]),target=ref(''),busy=ref(false),error=ref(''),requestKey=ref(crypto.randomUUID()),selected=ref('')
const ui=useUiStore()
const product=computed(()=>String(route.query.product||'')),jobId=computed(()=>String(route.query.job||''))
const query=usePages<Document>('documents',product,()=>product.value?`/products/${encodeURIComponent(product.value)}/documents?kb_id=${encodeURIComponent(auth.kb)}`:`/documents?kb_id=${encodeURIComponent(auth.kb)}`)
const items=computed(()=>query.data.value?.pages.flatMap(p=>p.items)||[]),filtered=computed(()=>items.value.filter(d=>d.name.toLowerCase().includes(search.value.toLowerCase())))
const current=computed(()=>items.value.find(d=>d.document_id===selected.value))
const products=usePages<Product>('upload-products',computed(()=>auth.kb),()=>`/products?kb_id=${encodeURIComponent(auth.kb)}`)
const accepted=ref(false)
const fileInput=ref<HTMLInputElement>()
function docIcon(name: string) { const n=name.toLowerCase(); if(n.endsWith('.pdf'))return FileText; if(n.endsWith('.xlsx')||n.endsWith('.xls')||n.endsWith('.csv'))return FileSpreadsheet; if(n.endsWith('.md')||n.endsWith('.markdown'))return FileCode; return File }
function onDrop(e: DragEvent) { const f=e.dataTransfer?.files?.[0]; if(!f)return; file.value=f; newRequest(); error.value='' }
function newRequest(){requestKey.value=crypto.randomUUID();accepted.value=false}
function targetRevision(d?:Document){target.value=d?.document_id||'';productIds.value=d?.product_ids||[];newRequest()}
watch(()=>auth.kb,()=>{file.value=undefined;selected.value='';target.value='';productIds.value=[];requestKey.value=crypto.randomUUID()})
function choose(event:Event){file.value=(event.target as HTMLInputElement).files?.[0];newRequest();error.value=''}
async function upload(){if(busy.value||accepted.value||!file.value)return;busy.value=true;error.value='';const owner=auth.user?.user_id,kb=auth.kb;try{
  const form=new FormData();form.set('file',file.value);form.set('kb_id',auth.kb);form.set('product_ids',JSON.stringify(product.value?[product.value]:productIds.value));form.set('purpose',purpose.value);form.set('client_request_id',requestKey.value);if(target.value)form.set('document_id',target.value)
  const result=await api.request<{job_id:string;document_id:string}>('/documents',{method:'POST',body:form})
  if(owner!==auth.user?.user_id||kb!==auth.kb)return
  accepted.value=true
  ui.trackJob(result.job_id)
  await router.replace({path:'/documents',query:{...route.query,job:result.job_id}});selected.value=result.document_id;await query.refetch()
}catch(e){error.value=(e as Error).message}finally{busy.value=false}}
</script>
<template><section class="catalog-page"><header class="page-head"><div><p class="eyebrow mono">知识资料 / DOCUMENTS</p><h1>资料管理</h1><p class="muted">上传、解析、验证与发布分别记录；查询使用已激活修订。</p></div><button v-if="auth.user?.role!=='viewer'" class="head-action" @click="fileInput?.click()">上传资料</button></header><ImportJobsFold :job-id="jobId || undefined" /><p v-if="auth.user?.role==='viewer'">当前角色仅可查看授权资料。</p><p v-if="product" class="muted">按所选设备筛选 · <RouterLink to="/documents">清除设备筛选</RouterLink></p><label>筛选已加载资料<input v-model="search" placeholder="资料名称"></label><p v-if="query.error.value||error" role="alert">{{error||query.error.value?.message}}</p><p v-if="query.isPending.value" role="status">正在读取资料…</p><p v-else-if="!filtered.length" class="empty-state">当前范围没有匹配资料。</p><div class="document-list"><Card v-for="d in filtered" :key="d.document_id" class="document-row"><CardHeader><div class="doc-head"><span class="doc-ic"><component :is="docIcon(d.name)" :size="15" :stroke-width="1.8" /></span><span class="doc-name" :title="d.name">{{ d.name }}</span><Badge v-if="d.active_revision_id" variant="success" size="sm">已发布</Badge><Badge v-else size="sm">未发布</Badge></div></CardHeader><CardContent><p class="doc-purpose">{{d.purpose==='technical'?'技术资料':d.purpose==='project_plan'?'项目计划':'用途未确认'}}</p><div class="actions"><button @click="selected=d.document_id">管理修订</button><button v-if="auth.user?.role!=='viewer'" @click="targetRevision(d)">上传新修订</button></div></CardContent></Card></div><button v-if="query.hasNextPage.value" :disabled="query.isFetchingNextPage.value" @click="query.fetchNextPage()">更多资料</button><button @click="query.refetch()">刷新资料</button>
<form v-if="auth.user?.role!=='viewer'" class="upload-form" @submit.prevent="upload"><h2>上传资料{{ target ? '（新修订）' : '' }}</h2><p v-if="target" class="muted">为已有资料创建新修订：{{target}} <button type="button" @click="targetRevision()">改为新资料</button></p>
<div class="upload-drop" :class="{ filled: !!file }" @click="fileInput?.click()" @dragover.prevent @drop.prevent="onDrop"><template v-if="!file"><Upload :size="18" :stroke-width="1.8" /><p>拖放文件到此处，或点击选择</p><p class="muted">支持 PDF / Markdown / Excel</p></template><template v-else><FileText v-if="file.name.toLowerCase().endsWith('.pdf')" :size="16" :stroke-width="1.8" /><FileSpreadsheet v-else-if="/\.xlsx?$/.test(file.name.toLowerCase())" :size="16" :stroke-width="1.8" /><FileCode v-else :size="16" :stroke-width="1.8" /><p class="drop-file">{{ file.name }}（{{ Math.round(file.size/1024) }} KB）</p><p class="muted">点击重新选择</p></template></div>
<label>原件文件<input ref="fileInput" type="file" accept=".pdf,.md,.xlsx" required @change="choose"></label><label>资料用途<select v-model="purpose" @change="newRequest"><option value="technical">设备技术资料</option><option value="project_plan">项目计划（不冒充技术手册）</option><option value="unknown">用途待确认</option></select></label><fieldset v-if="!product"><legend>关联设备</legend><label v-for="p in products.data.value?.pages.flatMap(p=>p.items)" :key="p.product_id" class="checkbox-label"><input v-model="productIds" :value="p.product_id" type="checkbox" @change="newRequest">{{p.model}}</label><button v-if="products.hasNextPage.value" type="button" @click="products.fetchNextPage()">更多关联设备</button></fieldset><p class="muted">上传接收成功不等于发布；具体解析/发布结果见任务和活动修订。</p><button class="primary" :disabled="busy||accepted||!file">{{busy?'正在上传…':'上传并导入'}}</button></form>
<ImportJobPanel v-if="jobId" :key="jobId" :job-id="jobId"/><RevisionPanel v-if="current" :key="current.document_id" :document="current" @changed="query.refetch()"/>
</section></template>

<style scoped>
.page-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.head-action { margin-top: 22px; }
.doc-head { display: flex; align-items: center; gap: 9px; min-width: 0; flex: 1; }
.doc-ic { display: inline-flex; color: var(--accent); flex-shrink: 0; }
.doc-name { color: var(--ink); font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.doc-purpose { color: var(--ink3); font-size: .78rem; margin: 0; }
.upload-drop { border: 1.5px dashed var(--line2); border-radius: 10px; padding: 22px; display: grid; justify-items: center; gap: 6px; color: var(--ink2); cursor: pointer; background: var(--panel); }
.upload-drop:hover { border-color: var(--accent); color: var(--accent); }
.upload-drop p { margin: 0; font-size: 12.5px; }
.upload-drop .muted { font-size: 11px; }
.upload-drop.filled { border-style: solid; border-color: var(--accent-line); background: var(--accent-soft); color: var(--ink); }
.drop-file { font-weight: 600; }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.mono { font-family: ui-monospace, Consolas, monospace; }
</style>
