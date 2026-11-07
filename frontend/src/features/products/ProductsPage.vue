<script setup lang="ts">
import { computed,ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { api } from '@/lib/api/client'
import type { Product } from '@/lib/api/types'
import { usePages } from '@/features/documents/queries'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
const auth=useAuthStore(),ui=useUiStore(),router=useRouter(),search=ref(''),filter=ref(''),name=ref(''),error=ref(''),busy=ref(false)
const query=usePages<Product>('products',filter,()=>`/products?kb_id=${encodeURIComponent(auth.kb)}&search=${encodeURIComponent(filter.value)}`)
const items=computed(()=>query.data.value?.pages.flatMap(p=>p.items)||[])
async function add(){if(busy.value)return;busy.value=true;try{await api.post('/products',{kb_id:auth.kb,model:name.value});name.value='';await query.refetch()}catch(e){error.value=(e as Error).message}finally{busy.value=false}}
function choose(product:Product){ui.selectProduct(product,auth.user!.user_id,auth.kb);void router.push('/chat')}
</script>
<template><section class="catalog-page"><header><p class="eyebrow">设备知识</p><h1>设备目录</h1><p class="muted">选择型号后，下一轮问答使用该设备的资料范围。</p></header><form class="inline-form" @submit.prevent="filter=search"><label>搜索型号<Input v-model="search" maxlength="200" placeholder="输入设备型号关键词…" /></label><Button type="submit">搜索</Button></form><p v-if="query.error.value||error" role="alert">{{error||query.error.value?.message}}</p><p v-if="query.isPending.value" role="status">正在加载设备…</p><p v-else-if="!items.length">当前知识范围没有匹配的设备。</p><div class="product-grid"><article v-for="p in items" :key="p.product_id" class="product-card v6"><header class="pc-head"><span class="pc-brand mono">{{p.brand||'DEVICE'}}</span><span v-if="p.aliases?.length" class="pc-ambiguous" title="存在别名/型号歧义">型号歧义</span></header><h2 class="pc-model">{{p.model}}</h2><p class="pc-series">{{p.series||'未标注系列'}}</p><p v-if="p.aliases?.length" class="muted pc-aliases">别名：{{p.aliases.join('、')}}</p><div class="pc-actions"><Button @click="choose(p)">选择设备</Button><RouterLink class="pc-link" :to="{path:'/documents',query:{product:p.product_id}}">查看适用资料 →</RouterLink></div></article></div><button v-if="query.hasNextPage.value" :disabled="query.isFetchingNextPage.value" @click="query.fetchNextPage()">更多设备</button><form v-if="auth.user?.role!=='viewer'" class="form-grid" @submit.prevent="add"><h2>登记设备</h2><label>标准型号<Input v-model="name" required maxlength="200" /></label><Button :disabled="busy||!name.trim()">登记设备</Button></form></section></template>
<style scoped>
.pc-head { display: flex; align-items: center; gap: 8px; justify-content: space-between; }
.pc-brand { font-size: 9px; letter-spacing: 0.1em; color: var(--ink3); }
.pc-ambiguous { font-size: 10px; font-weight: 700; color: var(--warn); background: var(--warn-soft); border: 1px solid var(--line2); border-radius: 5px; padding: 1px 8px; }
.pc-model { color: var(--ink); font-size: 1.05rem; margin: 0; }
.pc-series { color: var(--ink3); font-size: .8rem; margin: 0; }
.pc-aliases { font-size: .75rem; margin: 0; }
.pc-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.pc-link { color: var(--accent); text-decoration: none; font-size: 12.5px; font-weight: 600; }
.pc-link:hover { text-decoration: underline; }
.mono { font-family: ui-monospace, Consolas, monospace; }
</style>
