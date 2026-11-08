<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useTheme } from '@/lib/theme'
import { useRouter } from 'vue-router'
import type { Login } from './lib/api/types'
import LoginPage from './features/auth/LoginPage.vue'
const auth = useAuthStore(), cache = useQueryClient()
const navigation = useRouter()
const ui = useUiStore()
const detach = auth.onClear(() => { ui.clear(); void cache.cancelQueries(); cache.clear(); window.dispatchEvent(new Event('close-run-streams')) })
function login(value: Login) { auth.accept(value); void navigation?.replace('/chat') }
function expired() { auth.clear() }
onMounted(async () => { useTheme().init(); window.addEventListener('session-expired', expired); if (!auth.restored) await auth.restore() })
onBeforeUnmount(() => { detach(); window.removeEventListener('session-expired', expired) })
</script>
<template><aside class="preview-notice" role="note">知衡 · 内部预览：回答与支持建议为辅助草稿，请核对引用原文并人工确认；已知质量问题仍在修复。</aside><p v-if="!auth.restored" role="status">正在恢复身份…</p><RouterView v-else-if="auth.user" /><LoginPage v-else @login="login" /></template>
<style scoped>.preview-notice{padding:.5rem 1rem;background:var(--warn-soft);color:var(--warn);border-bottom:1px solid var(--line2);font-size:.875rem}</style>
