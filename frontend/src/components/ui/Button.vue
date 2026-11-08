<script setup lang="ts">
import { computed } from 'vue'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-1.5 font-medium cursor-pointer select-none disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-[var(--ink)] text-[var(--bg)] border border-transparent hover:opacity-90',
        secondary: 'bg-transparent text-[var(--ink2)] border border-[var(--line2)] hover:text-[var(--ink)] hover:border-[var(--ink3)]',
        ghost: 'bg-transparent text-[var(--ink3)] border border-transparent hover:bg-[var(--panel)] hover:text-[var(--ink)]',
        soft: 'bg-[var(--panel)] text-[var(--ink2)] border border-[var(--line)] hover:text-[var(--ink)]',
      },
      size: {
        sm: 'text-[11.5px] rounded-md px-2.5 py-1',
        md: 'text-[12.5px] rounded-lg px-3.5 py-1.5',
      },
    },
    defaultVariants: { variant: 'default', size: 'md' },
  },
)
const props = defineProps<{ variant?: VariantProps<typeof buttonVariants>['variant']; size?: VariantProps<typeof buttonVariants>['size']; class?: string }>()
const classes = computed(() => cn(buttonVariants({ variant: props.variant, size: props.size }), props.class))
</script>
<template>
  <button type="button" :class="classes"><slot /></button>
</template>
