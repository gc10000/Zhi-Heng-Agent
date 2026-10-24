<script setup lang="ts">
import { computed } from 'vue'
import { normalizedBox } from '../composables/pdf-coordinates'
const props=defineProps<{bbox?:number[]|null;width:number;height:number;rotation:number}>()
const style=computed(()=>{if(!props.bbox)return;try{return Object.fromEntries(Object.entries(normalizedBox(props.bbox,props.width,props.height,props.rotation)).map(([k,v])=>[k,v+'px']))}catch{return undefined}})
</script>
<template><div v-if="style" class="citation-overlay" :style="style" aria-label="引用原文区域" /></template>
