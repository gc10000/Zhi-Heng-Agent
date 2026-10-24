<script setup lang="ts">
import { computed,ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { api } from '@/lib/api/client'
import type { Product } from '@/lib/api/types'
import { usePages } from '@/features/documents/queries'
const auth=useAuthStore(),ui=useUiStore(),router=useRouter(),search=ref(''),filter=ref(''),name=ref(''),error=ref(''),busy=ref(false)
const query=usePages<Product>('products',filter,()=>`/products?kb_id=${encodeURIComponent(auth.kb)}&search=${encodeURIComponent(filter.value)}`)
const items=computed(()=>query.data.value?.pages.flatMap(p=>p.items)||[])
async function add(){if(busy.value)return;busy.value=true;try{await api.post('/products',{kb_id:auth.kb,model:name.value});name.value='';await query.refetch()}catch(e){error.value=(e as Error).message}finally{busy.value=false}}
function choose(id:string){ui.productIds=[id];void router.push('/chat')}
</script>
<template><section class="catalog-page"><header><p class="eyebrow">设备知识</p><h1>设备目录</h1><p class="muted">选择型号后，下一轮问答使用该设备的资料范围。</p></header><form class="inline-form" @submit.prevent="filter=search"><label>搜索型号<input v-model="search" maxlength="200"></label><button>搜索</button></form><p v-if="query.error.value||error" role="alert">{{error||query.error.value?.message}}</p><p v-if="query.isPending.value" role="status">正在加载设备…</p><p v-else-if="!items.length">当前知识范围没有匹配的设备。</p><div class="product-grid"><article v-for="p in items" :key="p.product_id" class="product-card"><p class="eyebrow">{{p.brand||'设备'}}</p><h2>{{p.model}}</h2><p>{{p.series||'未标注系列'}}</p><p v-if="p.aliases?.length" class="muted">别名：{{p.aliases.join('、')}}</p><div class="actions"><button class="primary" @click="choose(p.product_id)">选择设备</button><RouterLink :to="{path:'/documents',query:{product:p.product_id}}">查看适用资料</RouterLink></div></article></div><button v-if="query.hasNextPage.value" :disabled="query.isFetchingNextPage.value" @click="query.fetchNextPage()">更多设备</button><form v-if="auth.user?.role!=='viewer'" class="form-grid" @submit.prevent="add"><h2>登记设备</h2><label>标准型号<input v-model="name" required maxlength="200"></label><button :disabled="busy">登记设备</button></form></section></template>
