import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Run } from '@/lib/api/types'
import { reduceRun, type RunEvent } from '../composables/run-events'
export const useRunStore = defineStore('runs', () => {
  const runs = ref<Record<string, Run>>({})
  function snapshot(value: Run) {
    const old = runs.value[value.run_id]
    if (!old || value.seq >= old.seq) runs.value[value.run_id] = value
  }
  function event(value: RunEvent) { const old = runs.value[value.run_id]; if (old) runs.value[value.run_id] = reduceRun(old,value) }
  function forget(runId?: string) { if (runId) delete runs.value[runId]; else runs.value = {} }
  return { runs, snapshot, event, forget }
})
