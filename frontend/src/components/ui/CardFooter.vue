<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = withDefaults(defineProps<{ class?: string; padded?: boolean }>(), { padded: true })
const classes = computed(() => cn('border-t border-[var(--line)] bg-[var(--panel)]', props.padded && 'px-4 py-2.5', props.class))
</script>
<template>
  <footer :class="classes"><slot /></footer>
</template>
