import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Product } from '@/lib/api/types'
export const useUiStore = defineStore('ui', () => {
  const menu = ref(false), evidence = ref(false)
  const selectedCitation = ref<{ runId: string; citationId: string }>()
  const productIds = ref<string[]>([])
  const selectedProduct = ref<{ product: Product; userId: string; kb: string }>()
  /** T2.5：最近的导入任务 ID（内存级，供 DocumentsPage 任务折叠区轮询）。 */
  const recentJobs = ref<string[]>([])
  function trackJob(jobId: string) {
    if (!jobId || recentJobs.value.includes(jobId)) return
    recentJobs.value = [jobId, ...recentJobs.value].slice(0, 5)
  }
  function selectProduct(product: Product | undefined, userId: string, kb: string) {
    productIds.value = product ? [product.product_id] : []
    selectedProduct.value = product ? { product, userId, kb } : undefined
  }
  function clear() { menu.value = false; evidence.value = false; selectedCitation.value = undefined; productIds.value = []; selectedProduct.value = undefined }
  return { menu, evidence, selectedCitation, productIds, selectedProduct, recentJobs, trackJob, selectProduct, clear }
})
