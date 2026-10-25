<script setup lang="ts">
import { ref, watch } from 'vue'
const props=defineProps<{runId:string;citations:{citation_id:string}[];busy?:boolean}>()
const emit=defineEmits<{submit:[value:{run_id:string;citation_ids:string[];category:string;note:string;client_request_id:string}]}>()
const category=ref('evidence'),note=ref(''),selected=ref<string[]>([])
let pending:{identity:string;key:string}|undefined
watch(()=>props.runId,()=>{note.value='';selected.value=[];pending=undefined})
function send(){const identity=JSON.stringify([props.runId,selected.value,category.value,note.value]);if(pending?.identity!==identity)pending={identity,key:crypto.randomUUID()};emit('submit',{run_id:props.runId,citation_ids:selected.value,category:category.value,note:note.value,client_request_id:pending.key})}
</script>
<template><form aria-label="分类反馈" @submit.prevent="send"><h2>分类反馈</h2><p>反馈进入待审队列，不自动成为知识。</p><label>反馈类别<select v-model="category" :disabled="busy"><option value="model">型号识别</option><option value="evidence">证据不符</option><option value="missing_material">缺少资料</option><option value="operation">操作步骤</option><option value="image">配图问题</option></select></label>
<label v-for="citation in citations" :key="citation.citation_id"><input v-model="selected" type="checkbox" :value="citation.citation_id" :disabled="busy" />关联引用 {{citation.citation_id}}</label>
<label>反馈内容<textarea v-model="note" maxlength="4000" :disabled="busy" /></label><button :disabled="busy||!runId||!note.trim()">提交待审反馈</button></form></template>
