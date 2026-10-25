<script setup lang="ts">
import { reactive, watch, computed } from 'vue'
import type { Support } from '../types'
const props=defineProps<{context:Support;busy?:boolean;runId:string}>()
const emit=defineEmits<{save:[values:Record<string,string>];action:[name:string]}>()
const fields=reactive<Record<string,string>>({})
const labels:Record<string,string>={question:'问题',device:'设备型号',symptom:'实际现象',environment:'运行环境',error_code:'错误码',tried:'已尝试步骤'}
watch(()=>props.context, value=>{Object.keys(fields).forEach(k=>delete fields[k]);for(const [key,slot] of Object.entries(value.slots))fields[key]=slot.value||''},{immediate:true})
const ended=computed(()=>['cancelled','resolved','handoff'].includes(props.context.state))
function submit(){const values=Object.fromEntries(Object.entries(fields).filter(([key,value])=>value.trim()&&(value!==props.context.slots[key]?.value||!props.context.slots[key]?.confirmed)));emit('save',values)}
</script>
<template><section aria-label="支持上下文"><h2>支持上下文</h2><p role="status">{{context.prompt}}</p><p>状态：{{context.state}} · 上下文版本 {{context.context_version}}</p><p>仅确认你实际知道的信息；留空表示未知。更正只影响未来问答，原记录保留快照。</p>
<form @submit.prevent="submit"><label v-for="(label,key) in labels" :key="key">{{label}}<input v-model="fields[key]" maxlength="4000" :disabled="busy||ended" /></label><button :disabled="busy||ended||(!runId&&!context.run_id)">保存确认信息与纠正</button></form>
<button :disabled="busy||ended" @click="emit('action','handoff')">转交人工支持</button><button :disabled="busy||ended" @click="emit('action','resolve')">用户确认已解决</button><button :disabled="busy||ended" @click="emit('action','cancel')">结束支持流程</button>
</section></template>
