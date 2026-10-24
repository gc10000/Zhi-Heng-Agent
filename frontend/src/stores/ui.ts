import { defineStore } from 'pinia'
import { ref } from 'vue'
export const useUiStore = defineStore('ui', () => {
  const menu = ref(false), evidence = ref(false)
  const selectedCitation = ref<{ runId: string; citationId: string }>()
  const productIds = ref<string[]>([])
  function clear() { menu.value = false; evidence.value = false; selectedCitation.value = undefined; productIds.value = [] }
  return { menu, evidence, selectedCitation, productIds, clear }
})
