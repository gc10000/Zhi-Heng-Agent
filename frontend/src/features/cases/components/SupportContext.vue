<script setup lang="ts">
import { reactive, watch, computed, ref } from 'vue'
import type { Support } from '../types'
const props=defineProps<{context:Support;busy?:boolean;runId:string}>()
const emit=defineEmits<{save:[values:Record<string,string>,clearSlots:string[]];action:[name:string]}>()
const fields=reactive<Record<string,string>>({})
const notice=ref('')
const labels:Record<string,string>={question:'问题',device:'设备型号',symptom:'实际现象',environment:'运行环境',error_code:'错误码',tried:'已尝试步骤'}
watch(()=>props.context, value=>{Object.keys(fields).forEach(k=>delete fields[k]);for(const [key,slot] of Object.entries(value.slots))fields[key]=slot.value||''},{immediate:true})
const ended=computed(()=>['cancelled','resolved','handoff'].includes(props.context.state))
function changedValues(except:string[]=[]){return Object.fromEntries(Object.entries(fields).filter(([key,value])=>!except.includes(key)&&value.trim()&&(value!==props.context.slots[key]?.value||!props.context.slots[key]?.confirmed)))}
function submit(){notice.value='';const blankConfirmed=Object.keys(fields).filter(key=>props.context.slots[key]?.confirmed&&props.context.slots[key]?.value&&!fields[key].trim());if(blankConfirmed.length){notice.value='留空不会自动撤回已确认信息，请点击对应字段的“设为未知”。';return}emit('save',changedValues(),[])}
function clearSlot(key:string){notice.value='';fields[key]='';emit('save',changedValues([key]),[key])}
</script>
<template><section aria-label="支持上下文"><h2>支持上下文</h2><p role="status">{{context.prompt}}</p><p>状态：{{({awaiting_input:'等待补充',ready:'待核对操作',handoff:'待人工支持',resolved:'用户确认解决',cancelled:'已结束'} as Record<string,string>)[context.state]||'待核对'}} · 上下文版本 {{context.context_version}}</p><p>仅确认你实际知道的信息；留空表示未知。更正只影响未来问答，原记录保留快照。</p>
<p v-if="notice" role="alert">{{notice}}</p><form @submit.prevent="submit"><div v-for="(label,key) in labels" :key="key" class="slot-field"><label :for="'support-'+key">{{label}}</label><input :id="'support-'+key" v-model="fields[key]" maxlength="4000" :disabled="busy||ended" /><button v-if="context.slots[key]?.confirmed&&context.slots[key]?.value" type="button" :disabled="busy||ended||(!runId&&!context.run_id)" :aria-label="`将${label}设为未知`" @click="clearSlot(key)">设为未知</button></div><p>尚未确认的信息留空为未知；撤回已确认信息请使用对应字段的“设为未知”按钮。</p><button :disabled="busy||ended||(!runId&&!context.run_id)">保存确认信息与纠正</button></form>
<button :disabled="busy||ended" @click="emit('action','handoff')">转交人工支持</button><button :disabled="busy||ended" @click="emit('action','resolve')">用户确认已解决</button><button :disabled="busy||ended" @click="emit('action','cancel')">结束支持流程</button>
</section></template>
<style scoped>.slot-field{display:grid;grid-template-columns:minmax(8rem,1fr) minmax(10rem,2fr) auto;align-items:center;gap:.6rem;margin:.7rem 0}.slot-field label{font-weight:600}.slot-field input{min-width:0}section{max-width:64rem}p{line-height:1.7}button{margin:.25rem}</style>
