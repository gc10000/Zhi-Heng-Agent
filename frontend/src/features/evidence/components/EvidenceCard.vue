<script setup lang="ts">
import { ref, watch, defineAsyncComponent, computed } from 'vue'
import type { Citation } from '@/lib/api/types'
import SafeMarkdown from './SafeMarkdown.vue'
const props=defineProps<{citation:Citation}>()
const PdfViewer=defineAsyncComponent(()=>import('./PdfViewer.vue')),showPdf=ref(false)
const pdfSource=computed(()=>props.citation.source_refs.find(s=>s.kind==='pdf'&&s.page))
const broken=ref<string[]>([])
const expanded=ref(false)
const answerImages=computed(()=>props.citation.image_selection_version===1?props.citation.asset_ids.filter(id=>props.citation.answer_asset_ids?.includes(id)):props.citation.asset_ids)
const contextImages=computed(()=>props.citation.asset_ids.filter(id=>!answerImages.value.includes(id)))
const visibleImages=computed(()=>answerImages.value.concat(expanded.value?contextImages.value:[]))
watch(()=>props.citation.citation_id,()=>{broken.value=[];showPdf.value=false;expanded.value=false})
function url(id:string) { const expected='/api/v1/assets/'+encodeURIComponent(id);return props.citation.asset_urls?.[id]===expected ? expected : undefined }
</script>
<template><article class="evidence-card"><p class="eyebrow">本次入选证据 · {{ citation.source_refs.some(s=>s.kind==='image_description') ? '模型图像描述（需核对原图）' : '原文' }}</p><h3>{{ citation.title || '来源片段' }}</h3><SafeMarkdown data-testid="citation-text" :text="citation.display_text || citation.text" /><dl><dt>资料</dt><dd>{{ citation.document_id }}</dd><dt>修订</dt><dd>{{ citation.revision_id }}</dd></dl><ul class="source-refs"><li v-for="(source,i) in citation.source_refs" :key="i"><span>{{ source.kind === 'image_description' ? '模型图像描述（需核对原图）' : '原始资料' }}</span><p v-if="source.section_path?.length">章节：{{ source.section_path.join(' / ') }}</p><p v-if="source.page">物理页：{{ source.page }}</p><p v-else>未提供PDF页码，按章节或单元格溯源。</p><p v-if="source.sheet">工作表：{{ source.sheet }} {{ source.cell }}</p><p v-if="source.line_start">原文行：{{ source.line_start }}–{{ source.line_end || source.line_start }}</p></li></ul><p v-if="!citation.source_refs.length" class="muted">此证据没有精确页码或坐标。</p>
<section v-if="citation.description"><h3>模型图像描述</h3><p>{{ citation.description }}</p></section>
<template v-if="citation.original"><p>原件：{{ citation.original.name }}</p><template v-if="citation.original.url==='/api/v1/assets/'+encodeURIComponent(citation.original.asset_id)"><button v-if="citation.original.media_type==='application/pdf'" @click="showPdf=!showPdf">{{ showPdf?'关闭PDF原件':'打开PDF原件' }}</button><a v-else :href="citation.original.url" target="_blank" rel="noopener noreferrer">下载精确修订原件</a><PdfViewer v-if="showPdf" :url="citation.original.url" :page="pdfSource?.page" :bbox="pdfSource?.bbox" /></template></template>
<details v-if="contextImages.length" @toggle="expanded=($event.target as HTMLDetailsElement).open"><summary>检索关联图（未用于答案）</summary><p>这些资产保留用于核对原件，不能仅凭同型号或同页认定与回答相关。</p></details>
<figure v-for="id in visibleImages" :key="id"><img v-if="url(id) && !broken.includes(id)" :src="url(id)" alt="本次证据的登记原图" loading="lazy" @error="broken.push(id)"><figcaption v-else>图片暂不可用或授权链接不匹配。</figcaption><a v-if="url(id)" :href="url(id)" target="_blank" rel="noopener noreferrer">查看登记原件</a></figure>
</article></template>
