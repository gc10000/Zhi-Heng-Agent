<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { usePdfDocument } from '../composables/usePdfDocument'
import CitationOverlay from './CitationOverlay.vue'
import 'pdfjs-dist/web/pdf_viewer.css'
const props=defineProps<{url:string;page?:number|null;bbox?:number[]|null}>()
const pdf=usePdfDocument(),canvas=ref<HTMLCanvasElement>(),layer=ref<HTMLElement>(),page=ref(1),scale=ref(.8),rotation=ref(0)
const metrics=ref<{baseWidth:number;baseHeight:number;rotation:number}>()
let epoch=0
watch(()=>props.url,async value=>{const version=++epoch;metrics.value=undefined;page.value=props.page||1;rotation.value=0;await pdf.load(value);if(version===epoch)await draw()},{immediate:true})
watch(()=>props.page,value=>{page.value=value||1})
watch([page,scale,rotation],()=>{void draw()})
async function draw(){metrics.value=undefined;await nextTick();if(canvas.value&&layer.value){const value=await pdf.draw(page.value,scale.value,rotation.value,canvas.value,layer.value);if(value)metrics.value=value}}
</script>
<template><section class="pdf-viewer"><div class="pdf-toolbar"><button :disabled="page<=1" aria-label="上一页" @click="page--">上一页</button><label>PDF页码<input v-model.number="page" type="number" min="1" :max="pdf.document.value?.numPages||1" @change="page=Math.max(1,Math.min(page,pdf.document.value?.numPages||1))"></label><span>/ {{ pdf.document.value?.numPages || '—' }}</span><button :disabled="page >= (pdf.document.value?.numPages||1)" aria-label="下一页" @click="page++">下一页</button><button aria-label="缩小PDF" @click="scale=Math.max(.25,scale-.25)">−</button><span>{{ Math.round(scale*100) }}%</span><button aria-label="放大PDF" @click="scale=Math.min(3,scale+.25)">+</button><button aria-label="旋转PDF" @click="rotation=(rotation+90)%360">旋转</button></div><p v-if="pdf.loading.value" role="status">正在读取PDF原件…</p><p v-if="pdf.error.value" role="alert">{{ pdf.error.value }}<button @click="pdf.load(url).then(draw)">重试PDF</button></p><p v-if="!bbox" class="muted">没有区域坐标，仅定位物理页；不生成推测高亮。</p><div class="pdf-scroll"><div class="pdf-page" :style="metrics ? {width:canvas?.style.width,height:canvas?.style.height} : undefined"><canvas ref="canvas" aria-label="PDF原件页面" /><div ref="layer" class="textLayer" /><CitationOverlay v-if="metrics && page===(props.page||1)" :bbox="bbox" :width="metrics.baseWidth" :height="metrics.baseHeight" :rotation="metrics.rotation" /></div></div></section></template>
