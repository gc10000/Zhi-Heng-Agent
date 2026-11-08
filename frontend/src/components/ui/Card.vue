<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps<{ class?: string }>()
const classes = computed(() => cn('rounded-[10px] border border-[var(--line)] bg-[var(--bg)] min-w-0 overflow-hidden', props.class))
</script>
<template>
  <section :class="classes"><slot /></section>
</template>
