<script setup lang="ts">
withDefaults(defineProps<{ size?: number }>(), { size: 30 })
</script>
<template>
  <svg
    :width="size" :height="size" viewBox="0 0 36 36" fill="none"
    stroke="currentColor" stroke-width="2.4" stroke-linecap="round"
    aria-hidden="true" focusable="false"
  >
    <rect x="3.5" y="12" width="29" height="12" rx="6" />
    <circle cx="18" cy="18" r="2.4" fill="var(--accent)" stroke="none" />
    <path d="M9.5 18h2.5M24 18h2.5" />
  </svg>
</template>
