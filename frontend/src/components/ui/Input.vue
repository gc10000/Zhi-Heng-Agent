<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
const props = defineProps<{ modelValue: string; type?: string; placeholder?: string; disabled?: boolean; required?: boolean; maxlength?: number | string; autocomplete?: string; class?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const classes = computed(() => cn(
  'w-full bg-[var(--bg)] text-[var(--ink)] border border-[var(--line2)] rounded-lg px-3 py-2 text-[13px] outline-none',
  'placeholder:text-[var(--ink3)] focus:border-[var(--accent)] focus:shadow-[0_0_0_3px_color-mix(in_srgb,var(--accent)_12%,transparent)]',
  'disabled:opacity-50 disabled:cursor-not-allowed',
  props.class,
))
function onInput(event: Event) { emit('update:modelValue', (event.target as HTMLInputElement).value) }
</script>
<template>
  <input :type="type || 'text'" :value="modelValue" :class="classes" :placeholder="placeholder" :disabled="disabled" :required="required" :maxlength="maxlength" :autocomplete="autocomplete" @input="onInput">
</template>
