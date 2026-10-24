<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { api } from './lib/api/client'
import type { Login, User } from './lib/api/types'
import LoginPage from './features/auth/LoginPage.vue'
import CompatibilityPage from './features/chat/CompatibilityPage.vue'
const user = ref<User>(), restoring = ref(true)
function login(value: Login) { api.csrf = value.csrf_token; user.value = value.user }
function expired() { user.value = undefined }
onMounted(async () => { window.addEventListener('session-expired', expired); try { login(await api.request<Login>('/me')) } catch { /* 未登录显示登录页 */ } finally { restoring.value = false } })
onBeforeUnmount(() => window.removeEventListener('session-expired', expired))
</script>
<template><p v-if="restoring" role="status">正在恢复身份…</p><CompatibilityPage v-else-if="user" :user="user" /><LoginPage v-else @login="login" /></template>
