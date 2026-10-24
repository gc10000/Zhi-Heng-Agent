<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import type { Login } from './lib/api/types'
import LoginPage from './features/auth/LoginPage.vue'
const auth = useAuthStore(), cache = useQueryClient()
const navigation = useRouter()
const detach = auth.onClear(() => { void cache.cancelQueries(); cache.clear(); window.dispatchEvent(new Event('close-run-streams')) })
function login(value: Login) { auth.accept(value); void navigation?.replace('/chat') }
function expired() { auth.clear() }
onMounted(async () => { window.addEventListener('session-expired', expired); if (!auth.restored) await auth.restore() })
onBeforeUnmount(() => { detach(); window.removeEventListener('session-expired', expired) })
</script>
<template><p v-if="!auth.restored" role="status">正在恢复身份…</p><RouterView v-else-if="auth.user" /><LoginPage v-else @login="login" /></template>
