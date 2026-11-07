<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = withDefaults(defineProps<{ class?: string; padded?: boolean }>(), { padded: true })
const classes = computed(() => cn('bg-[var(--bg)] min-w-0', props.padded && 'px-4 py-3', props.class))
</script>
<template>
  <div :class="classes"><slot /></div>
</template>
