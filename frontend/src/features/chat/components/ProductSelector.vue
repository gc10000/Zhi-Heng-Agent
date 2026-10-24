<script setup lang="ts">
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '@/lib/api/client'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import type { Product, Page } from '@/lib/api/types'
import { scopeKey } from '../queries/history'
const auth=useAuthStore(), ui=useUiStore()
const query=useQuery({queryKey:computed(()=>scopeKey(auth.user?.user_id||'',auth.kb,'products-selector')),queryFn:({signal})=>api.request<Page<Product>>(`/products?kb_id=${encodeURIComponent(auth.kb)}&limit=100`,{signal}),enabled:computed(()=>!!auth.kb),retry:false})
</script>
<template><label class="product-selector">本轮适用设备<select :value="ui.productIds[0] || ''" @change="ui.productIds = ($event.target as HTMLSelectElement).value ? [($event.target as HTMLSelectElement).value] : []"><option value="">未指定，必要时询问型号</option><option v-for="p in query.data.value?.items" :key="p.product_id" :value="p.product_id">{{ p.model }}</option></select></label><p v-if="query.error.value" role="alert">{{ query.error.value.message }}</p><p v-if="query.data.value?.next_cursor" class="muted">更多设备请从设备目录选择。</p></template>
