<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/lib/api/client'
import type { Login } from '@/lib/api/types'
const emit = defineEmits<{ login: [value: Login] }>()
const username = ref(''), password = ref(''), error = ref(''), busy = ref(false)
async function login() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { emit('login', await api.post<Login>('/auth/login', { username: username.value, password: password.value })); password.value = '' }
  catch (e) { error.value = e instanceof Error ? e.message : '登录失败。' }
  finally { busy.value = false }
}
</script>
<template><main class="login-page"><form class="login-card" @submit.prevent="login">
  <p class="eyebrow">知衡 / 技术支持与知识工作台</p><h1>登录工作台</h1><p class="muted">从设备资料出发，让每个答案都有依据。</p>
  <label>用户名<input v-model="username" required autocomplete="username" maxlength="128"></label>
  <label>密码<input v-model="password" type="password" required autocomplete="current-password"></label>
  <p v-if="error" role="alert">{{ error }}</p><button class="primary" :disabled="busy">{{ busy ? '正在登录…' : '登录' }}</button>
</form></main></template>
