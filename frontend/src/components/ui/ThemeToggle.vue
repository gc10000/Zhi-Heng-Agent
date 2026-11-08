<script setup lang="ts">
import { Sun, Moon } from 'lucide-vue-next'
import { useTheme } from '@/lib/theme'
const { theme, set } = useTheme()
</script>
<template>
  <div class="theme-toggle" role="radiogroup" aria-label="主题切换">
    <button
      type="button" role="radio" aria-checked="true" :aria-pressed="theme === 'light'"
      class="seg" :class="{ on: theme === 'light' }" title="亮色主题"
      @click="set('light')"
    ><Sun :size="13" aria-hidden="true" /><span>亮</span></button>
    <button
      type="button" role="radio" :aria-checked="theme === 'dark'" :aria-pressed="theme === 'dark'"
      class="seg" :class="{ on: theme === 'dark' }" title="暗色主题"
      @click="set('dark')"
    ><Moon :size="13" aria-hidden="true" /><span>暗</span></button>
  </div>
</template>
<style scoped>
.theme-toggle { display: inline-flex; align-items: center; border: 1px solid var(--line2); border-radius: 8px; overflow: hidden; }
.seg { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; padding: 3px 10px; cursor: pointer; color: var(--ink3); background: var(--bg); border: none; }
.seg.on { background: var(--ink); color: var(--bg); font-weight: 600; }
.seg:hover:not(.on) { color: var(--ink); }
</style>
