<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Citation } from '@/lib/api/types'
import SafeMarkdown from './SafeMarkdown.vue'
const props=defineProps<{citation:Citation}>()
const broken=ref<string[]>([])
watch(()=>props.citation.citation_id,()=>{broken.value=[]})
function url(id:string) { const expected='/api/v1/assets/'+encodeURIComponent(id);return props.citation.asset_urls?.[id]===expected ? expected : undefined }
</script>
<template><article class="evidence-card"><p class="eyebrow">本次入选证据 · {{ citation.source_refs.some(s=>s.kind==='image_description') ? '模型图像描述（需核对原图）' : '原文' }}</p><h3>{{ citation.title || '来源片段' }}</h3><SafeMarkdown data-testid="citation-text" :text="citation.display_text || citation.text" /><dl><dt>资料</dt><dd>{{ citation.document_id }}</dd><dt>修订</dt><dd>{{ citation.revision_id }}</dd></dl><ul class="source-refs"><li v-for="(source,i) in citation.source_refs" :key="i"><span>{{ source.kind === 'image_description' ? '模型图像描述（需核对原图）' : '原始资料' }}</span><p v-if="source.section_path?.length">章节：{{ source.section_path.join(' / ') }}</p><p v-if="source.page">物理页：{{ source.page }}</p><p v-else>未提供PDF页码，按章节或单元格溯源。</p><p v-if="source.sheet">工作表：{{ source.sheet }} {{ source.cell }}</p><p v-if="source.line_start">原文行：{{ source.line_start }}–{{ source.line_end || source.line_start }}</p></li></ul><p v-if="!citation.source_refs.length" class="muted">此证据没有精确页码或坐标。</p>
<section v-if="citation.description"><h3>模型图像描述</h3><p>{{ citation.description }}</p></section>
<figure v-for="id in citation.asset_ids" :key="id"><img v-if="url(id) && !broken.includes(id)" :src="url(id)" alt="本次证据的登记原图" loading="lazy" @error="broken.push(id)"><figcaption v-else>图片暂不可用或授权链接不匹配。</figcaption><a v-if="url(id)" :href="url(id)" target="_blank" rel="noopener noreferrer">查看登记原件</a></figure>
</article></template>
