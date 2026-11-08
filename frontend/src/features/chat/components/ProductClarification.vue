<script setup lang="ts">
import { ref } from 'vue'
import type { Run } from '@/lib/api/types'
import { useProductSelection } from '../queries/product-selection'
const props = defineProps<{ run: Run; busy: boolean }>()
const emit = defineEmits<{ confirm: [value: { product_ids: string[]; expected_version: number }] }>()
const { manualOpen, manualQuery, manualSearch, openManual, closeManual } = useProductSelection()
const expanded = ref(false)
function choose(id: string) {
  if (props.busy || props.run.state !== 'awaiting_input') return
  emit('confirm', { product_ids: [id], expected_version: props.run.version })
}
function manualChoose(id: string) {
  closeManual(); expanded.value = false
  choose(id)
}
</script>
<template><section v-if="run.state === 'awaiting_input'" class="clarification">
  <h2>请选择适用型号</h2>
  <p class="muted">不同型号可能使用不同参数。确认后才会在对应资料中检索。</p>
  <div class="candidate-list">
    <button v-for="p in run.candidates" :key="p.product_id" :disabled="busy" class="candidate-card" @click="choose(p.product_id)">
      <span class="cand-model">{{ p.model }}</span>
      <small v-if="p.series" class="cand-series">{{ p.series }}</small>
    </button>
  </div>
  <button v-if="!expanded" type="button" class="none-of-these" @click="expanded = true; openManual()">以上都不是 — 手动指定型号</button>
  <div v-else class="manual-panel">
    <label>搜索型号<input v-model="manualQuery" placeholder="输入设备型号关键词…" autocomplete="off"></label>
    <p v-if="manualSearch.isPending.value" role="status">正在搜索设备目录…</p>
    <p v-else-if="manualSearch.error.value" role="alert">{{ manualSearch.error.value.message }}</p>
    <div v-else-if="manualSearch.data.value?.items.length" class="manual-results">
      <button v-for="p in manualSearch.data.value.items" :key="p.product_id" type="button" :disabled="busy" class="manual-row" @click="manualChoose(p.product_id)">
        <span class="cand-model">{{ p.model }}</span>
        <small v-if="p.series" class="cand-series">{{ p.series }}</small>
      </button>
    </div>
    <p v-else class="muted">没有匹配的设备。</p>
    <p class="manual-hint muted">找不到设备？可在<RouterLink to="/products">设备目录</RouterLink>登记后重试。</p>
  </div>
</section></template>
<style scoped>
.candidate-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 200px), 1fr)); gap: 10px; }
.candidate-card { text-align: left; padding: 12px 14px; background: var(--panel); border: 1px solid var(--line2); border-radius: 9px; display: grid; gap: 3px; }
.candidate-card:hover:not(:disabled) { border-color: var(--accent); }
.cand-model { font-weight: 700; color: var(--ink); }
.cand-series { color: var(--ink3); font-size: .75rem; }
.none-of-these { border: 1px dashed var(--line2); background: transparent; color: var(--ink2); border-radius: 9px; padding: 9px 14px; width: 100%; }
.none-of-these:hover { color: var(--warn); border-color: var(--warn); }
.manual-panel { display: grid; gap: 10px; border: 1px solid var(--line2); border-radius: 10px; padding: 14px; background: var(--bg); }
.manual-results { display: grid; gap: 6px; max-height: 220px; overflow: auto; }
.manual-row { text-align: left; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; display: grid; gap: 2px; }
.manual-row:hover:not(:disabled) { border-color: var(--accent); }
.manual-hint { font-size: .8rem; }
</style>
