<script setup lang="ts">
import type { QuestionResult } from './types'
defineProps<{ result: QuestionResult['result']; status: string }>()
</script>
<template>
  <section aria-label="运行结果呈现">
    <p>运行状态：{{ result.state || status || '历史未记录' }}</p>
    <p v-if="['failed','cancelled','interrupted'].includes(result.state||status)" role="status">运行未形成完整答案；保留失败／取消／中断身份，不能当作正常空回答。</p>
    <template v-else-if="result.state==='awaiting_input'||result.behavior==='clarify'">
      <h3>请选择适用型号</h3>
      <p role="status">本轮请求确认设备型号，未生成答案。不同型号可能使用不同参数。确认后才会在对应资料中检索。</p>
      <ul v-if="result.candidates?.length"><li v-for="candidate in result.candidates" :key="candidate.product_id">{{ candidate.model }}</li></ul>
      <p v-else>本历史审核结果未保存型号候选；需核对关联Run的只读补充材料，不能据此认定无候选。</p>
    </template>
    <p v-else-if="result.behavior==='refuse'||result.behavior==='insufficient'" role="status">结果行为：{{ result.behavior==='refuse'?'拒绝':'依据不足' }}。此为辅助标记，请结合完整回答和展示来源审核。</p>
    <p v-else-if="!result.answer" role="status">当前结果没有答案正文，请核对运行状态与原始资料，无法确认的维度保留未知。</p>
    <details v-if="result.prompt_reference_map?.length">
      <summary>正文编号与来源映射</summary>
      <p>编号来自实际模型输入，页级引用列表可能一片多页或页码未知，不能按列表位置重编号。</p>
      <ul><li v-for="ref in result.prompt_reference_map" :key="ref.reference_number">
        <p>[{{ref.reference_number}}] · {{ref.products.join('、')||'归属未知'}} · 物理页 {{ref.physical_pages.join('、')||'unknown'}}</p>
        <p>document_id={{ref.document_id}} · revision_id={{ref.revision_id}} · chunk_id={{ref.chunk_uid}} · 原件SHA256 {{ref.original_sha256}} · 定位 {{ref.page_status}}</p>
      </li></ul>
    </details>
  </section>
</template>
