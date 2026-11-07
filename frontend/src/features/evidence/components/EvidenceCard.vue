<script setup lang="ts">
import { ref, watch, defineAsyncComponent, computed } from 'vue'
import type { Citation } from '@/lib/api/types'
import SafeMarkdown from './SafeMarkdown.vue'
import { useDocumentNames } from '../queries/document-names'
const props=defineProps<{citation:Citation}>()
const PdfViewer=defineAsyncComponent(()=>import('./PdfViewer.vue')),showPdf=ref(false)
const { nameOf } = useDocumentNames()
const documentName=computed(()=>nameOf(props.citation.document_id)||'')
const pdfSource=computed(()=>props.citation.source_refs.find(s=>s.kind==='pdf'&&s.page))
const broken=ref<string[]>([])
const expanded=ref(false)
const answerImages=computed(()=>props.citation.image_selection_version===1?props.citation.asset_ids.filter(id=>props.citation.answer_asset_ids?.includes(id)):[])
const contextImages=computed(()=>props.citation.asset_ids.filter(id=>!answerImages.value.includes(id)))
const visibleImages=computed(()=>answerImages.value.concat(expanded.value?contextImages.value:[]))
watch(()=>props.citation.citation_id,()=>{broken.value=[];showPdf.value=false;expanded.value=false})
function url(id:string) { const expected='/api/v1/assets/'+encodeURIComponent(id);return props.citation.asset_urls?.[id]===expected ? expected : undefined }
</script>
<template><article class="evidence-card">
  <header class="evc-head"><span class="evc-no mono">证据</span><span class="evc-name" :title="documentName || citation.title || citation.document_id">{{ documentName || citation.title || citation.document_id }}</span><span v-if="pdfSource?.page" class="evc-page mono">p{{ pdfSource.page }}</span></header>
  <p class="eyebrow">{{ citation.source_refs.some(s=>s.kind==='image_description') ? '模型图像描述（需核对原图）' : '原文摘录' }}</p>
  <SafeMarkdown data-testid="citation-text" class="evc-quote" :text="citation.display_text || citation.text" />
  <ul class="source-refs"><li v-for="(source,i) in citation.source_refs" :key="i"><span>{{ source.kind === 'image_description' ? '模型图像描述（需核对原图）' : '原始资料' }}</span><p v-if="source.section_path?.length">章节：{{ source.section_path.join(' / ') }}</p><p v-if="source.page">物理页：{{ source.page }}</p><p v-else>未提供PDF页码，按章节或单元格溯源。</p><p v-if="source.sheet">工作表：{{ source.sheet }} {{ source.cell }}</p><p v-if="source.line_start">原文行：{{ source.line_start }}–{{ source.line_end || source.line_start }}</p></li></ul>
  <p v-if="!citation.source_refs.length" class="muted">此证据没有精确页码或坐标。</p>
  <section v-if="citation.description"><h3>模型图像描述</h3><p>{{ citation.description }}</p></section>
  <template v-if="citation.original"><p>原件：{{ citation.original.name }}</p><template v-if="citation.original.url==='/api/v1/assets/'+encodeURIComponent(citation.original.asset_id)"><button v-if="citation.original.media_type==='application/pdf'" @click="showPdf=!showPdf">{{ showPdf?'关闭PDF原件':'打开原件 ↗' }}</button><a v-else :href="citation.original.url" target="_blank" rel="noopener noreferrer">下载精确修订原件</a><PdfViewer v-if="showPdf" :url="citation.original.url" :page="pdfSource?.page" :bbox="pdfSource?.bbox" /></template></template>
  <p v-if="citation.image_selection_version!==1">历史图片的答案使用关系未记录，不据此推断为答案图；展开后可核对原件。</p>
  <details v-if="contextImages.length" @toggle="expanded=($event.target as HTMLDetailsElement).open"><summary>{{citation.image_selection_version===1?'检索关联图（未用于答案）':'历史图像来源（答案使用关系未记录）'}}</summary><p>这些资产保留用于核对原件，不能仅凭同型号或同页认定与回答相关。</p></details>
  <figure v-for="id in visibleImages" :key="id"><img v-if="url(id) && !broken.includes(id)" :src="url(id)" alt="本次证据的登记原图" loading="lazy" @error="broken.push(id)"><figcaption v-else>图片暂不可用或授权链接不匹配。</figcaption><a v-if="url(id)" :href="url(id)" target="_blank" rel="noopener noreferrer">查看登记原件</a></figure>
  <footer class="evc-foot"><span class="mono evc-rev">修订 {{ citation.revision_id }}</span><button v-if="citation.original" class="evc-open mono" :title="'打开 '+(documentName||'原件')" @click="showPdf=!showPdf">VERIFIED</button></footer>
</article></template>
<style scoped>
.evc-head { display: flex; align-items: center; gap: 8px; min-width: 0; }
.evc-no { font-size: 9px; color: var(--accent); background: var(--accent-soft); border: 1px solid var(--accent-line); border-radius: 4px; padding: 0.5px 6px; font-weight: 700; }
.evc-name { font-size: 12.5px; font-weight: 600; color: var(--ink); flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.evc-page { font-size: 9px; color: var(--ink3); }
.evc-quote { margin: 0; }
.evc-foot { display: flex; align-items: center; gap: 8px; }
.evc-rev { font-size: 9px; color: var(--ink3); overflow-wrap: anywhere; }
.mono { font-family: ui-monospace, Consolas, monospace; }
</style>
