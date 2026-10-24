<script setup lang="ts">
import type { Product } from '@/lib/api/types'
defineProps<{ modelValue: string; products: Product[]; pending: boolean; error: string; hasMore: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>
<template><label class="product-selector">本轮适用设备<select :value="modelValue" @change="emit('update:modelValue',($event.target as HTMLSelectElement).value)"><option value="">未指定，必要时询问型号</option><option v-if="modelValue && !products.some(p=>p.product_id===modelValue)" :value="modelValue" disabled>设备待核对（{{modelValue}}）</option><option v-for="p in products" :key="p.product_id" :value="p.product_id">{{p.model}}</option></select></label><p v-if="pending" role="status">正在核对所选设备，核对完成前不能发送。</p><p v-if="error" role="alert">{{error}}</p><p v-if="hasMore" class="muted">更多设备请从设备目录选择。</p></template>
