<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/lib/api/client'
import BrandMark from '@/components/ui/BrandMark.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
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
  <div class="login-brand"><span class="login-mark"><BrandMark :size="30" /></span><p class="eyebrow">知衡 / 技术支持与知识工作台</p></div><h1>登录工作台</h1><p class="muted">从设备资料出发，让每个答案都有依据。</p>
  <label>用户名<Input v-model="username" required autocomplete="username" maxlength="128" /></label>
  <label>密码<Input v-model="password" type="password" required autocomplete="current-password" /></label>
  <p v-if="error" role="alert">{{ error }}</p><Button type="submit" class="login-submit" :disabled="busy">{{ busy ? '正在登录…' : '登录' }}</Button>
</form></main></template>
<style scoped>
.login-submit { width: 100%; justify-content: center; padding: 10px; font-size: 14px; background: var(--accent); color: var(--bg); border-color: var(--accent); }
.login-submit:hover:not(:disabled) { opacity: .9; }
.login-card [role=alert] { color: var(--danger); }
</style>
