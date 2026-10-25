import type { Citation } from '@/lib/api/types'
import type { Operation } from './components/OperationChecklist.vue'
export interface Slot { value:string|null; confirmed:boolean; source:string }
export interface Support { version:number; context_version:number; state:string; reason:string; requested_slot:string|null; prompt:string; run_id:string|null; slots:Record<string,Slot>; operations:Operation[]; citations:Citation[]; tool_calls:{call_id:string;tool:string;status:string;reason?:string;output?:{notice:string;items:{text?:string;model?:string}[]}}[] }
export interface CaseRecord { case_id:string; conversation_id:string; run_id:string; kb_id:string; version:number; status:'draft'|'confirmed'; fields:Record<string,string>; citations:Citation[]; operations:Operation[]; confirmed_at:string|null; run_snapshot?:{citations:Citation[]} }
