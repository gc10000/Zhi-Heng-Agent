<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Source } from './types'
const props=defineProps<{eid:string;qid:string;sources:Source[];version?:number}>()
const expanded=ref(false),failed=ref(new Set<string>())
watch(()=>[props.eid,props.qid],()=>{expanded.value=false;failed.value=new Set()})
const context=computed(()=>props.sources.filter(c=>c.asset_sha256&&(props.version!==1||c.image_usage==='context')))
const visible=computed(()=>props.sources.filter(c=>!context.value.includes(c)).concat(expanded.value?context.value:[]))
const images=computed(()=>props.sources.some(c=>c.asset_sha256&&!context.value.includes(c)))
function key(c:Source){return [c.document_sha256,c.page,c.asset_sha256].join('/')}
function url(c:Source){
  if(!c.asset_sha256||!c.page||c.page<1||! /^[0-9a-f]{64}$/.test(c.document_sha256)||! /^[0-9a-f]{64}$/.test(c.asset_sha256))return ''
  return '/api/v1/experiments/'+encodeURIComponent(props.eid)+'/results/'+encodeURIComponent(props.qid)+'/images/'+c.document_sha256+'/'+c.page+'/'+c.asset_sha256
}
</script>
<template>
<h3>引用与配图</h3>
<p v-if="version===1&&!images">当前答案没有使用配图；检索关联图保留用于核对原件，不作为答案配图。</p>
<p v-if="version!==1">历史结果未区分答案配图与上下文关联图；以下图片不能仅凭同页或同型号认定相关。</p>
<details v-if="context.length" @toggle="expanded=($event.target as HTMLDetailsElement).open"><summary>{{version===1?'检索关联图（未用于答案）':'历史图像来源（答案使用关系未记录）'}}</summary><p>仅作溯源，未据此修改历史图片评分。展开后读取受控原图。</p></details>
<ul class="citations"><li v-for="(source,index) in visible" :key="index">
<p>原件 SHA256 {{source.document_sha256}} · 物理页 {{source.page??'未知'}}<template v-if="source.asset_sha256"> · 图片 SHA256 {{source.asset_sha256}} · {{source.image_usage==='context'?'检索关联图（未用于答案）':'引用配图'}}</template></p>
<figure v-if="url(source)&&!failed.has(key(source))"><img :src="url(source)" :alt="'资料第'+source.page+'页引用配图'" loading="lazy" decoding="async" @error="failed.add(key(source))"><figcaption>由当前实验结果、原件、物理页和图片指纹绑定的受控图片</figcaption></figure>
<p v-else-if="source.asset_sha256" class="muted" role="status">这条结果记录了图片来源，但当前图片未能安全读取或缺少物理页映射；请联系维护者核对，图片维度保留未知。</p>
</li></ul>
</template>
<style scoped>.citations{display:grid;gap:1rem;padding-left:1.25rem}figure{margin:.7rem 0}img{display:block;max-width:min(100%,48rem);max-height:34rem;object-fit:contain;border:1px solid #cad5dc}figcaption{font-size:.9rem;color:#587080}</style>
