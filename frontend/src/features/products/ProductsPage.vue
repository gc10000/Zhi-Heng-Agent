<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Server } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { api } from '@/lib/api/client'
import type { Product } from '@/lib/api/types'
import { usePages } from '@/features/documents/queries'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Badge from '@/components/ui/Badge.vue'
const auth = useAuthStore(), ui = useUiStore(), router = useRouter()
const search = ref(''), filter = ref(''), name = ref(''), error = ref(''), busy = ref(false), showRegister = ref(false)
const query = usePages<Product>('products', filter, () => `/products?kb_id=${encodeURIComponent(auth.kb)}&search=${encodeURIComponent(filter.value)}`)
const items = computed(() => query.data.value?.pages.flatMap(p => p.items) || [])
async function add() { if (busy.value) return; busy.value = true; try { await api.post('/products', { kb_id: auth.kb, model: name.value }); name.value = ''; showRegister.value = false; await query.refetch() } catch (e) { error.value = (e as Error).message } finally { busy.value = false } }
function choose(product: Product) { ui.selectProduct(product, auth.user!.user_id, auth.kb); void router.push('/chat') }
</script>
<template><section class="catalog-page">
<header class="page-head"><div><p class="eyebrow mono">设备知识 / DEVICES</p><h1>设备目录</h1><p class="muted">选择型号后，下一轮问答使用该设备的资料范围。</p></div>
<Button v-if="auth.user?.role!=='viewer'" class="head-action" @click="showRegister=!showRegister"><Plus :size="14" :stroke-width="2" />登记设备</Button></header>
<form class="inline-form" @submit.prevent="filter=search"><label>搜索型号<Input v-model="search" maxlength="200" placeholder="输入设备型号关键词…" /></label><Button type="submit" variant="secondary">搜索</Button></form>
<p v-if="query.error.value||error" role="alert">{{ error || query.error.value?.message }}</p>
<p v-if="query.isPending.value" role="status">正在加载设备…</p>
<p v-else-if="!items.length" class="muted">当前知识范围没有匹配的设备。</p>
<div class="product-grid">
  <Card v-for="p in items" :key="p.product_id" class="product-card prod-card">
    <CardHeader><div class="pc-head"><span class="pc-ic"><Server :size="15" :stroke-width="1.8" /></span><h2 class="pc-model">{{ p.model }}</h2><Badge v-if="p.aliases?.length" variant="warning" size="sm">型号歧义</Badge></div></CardHeader>
    <CardContent><p class="pc-series">{{ p.series || '未标注系列' }}</p><p v-if="p.aliases?.length" class="muted pc-aliases">别名：{{ p.aliases.join('、') }}</p>
      <div class="pc-actions"><Button size="sm" @click="choose(p)">选择设备</Button><RouterLink class="pc-link" :to="{ path: '/documents', query: { product: p.product_id } }">查看适用资料 →</RouterLink></div>
    </CardContent>
  </Card>
</div>
<Button v-if="query.hasNextPage.value" variant="ghost" :disabled="query.isFetchingNextPage.value" @click="query.fetchNextPage()">更多设备</Button>
<form v-if="showRegister && auth.user?.role!=='viewer'" class="form-grid register-form" @submit.prevent="add"><h2>登记设备</h2><label>标准型号<Input v-model="name" required maxlength="200" /></label><Button type="submit" :disabled="busy || !name.trim()">登记设备</Button></form>
</section></template>
<style scoped>
.page-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.head-action { margin-top: 22px; }
.pc-head { display: flex; align-items: center; gap: 9px; min-width: 0; flex: 1; }
.pc-ic { display: inline-flex; color: var(--accent); flex-shrink: 0; }
.prod-card h2.pc-model { color: var(--ink); font-size: 13.5px; font-weight: 700; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.pc-series { color: var(--ink3); font-size: .8rem; margin: 0 0 2px; }
.pc-aliases { font-size: .75rem; margin: 0; }
.pc-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 4px; }
.pc-link { color: var(--accent); text-decoration: none; font-size: 12.5px; font-weight: 600; }
.pc-link:hover { text-decoration: underline; }
.register-form { max-width: 420px; margin-top: 16px; }
.mono { font-family: ui-monospace, Consolas, monospace; }
</style>
