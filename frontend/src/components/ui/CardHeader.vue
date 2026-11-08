<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = withDefaults(defineProps<{ class?: string; padded?: boolean }>(), { padded: true })
const classes = computed(() => cn('border-b border-[var(--line)] bg-[var(--bg)]', props.padded && 'px-4 py-3', props.class))
</script>
<template>
  <header :class="classes"><slot /></header>
</template>
