<script setup lang="ts">
import { computed } from 'vue'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
const badgeVariants = cva(
  'inline-flex items-center font-semibold whitespace-nowrap',
  {
    variants: {
      variant: {
        default: 'text-[var(--ink2)] bg-[var(--panel)] border border-[var(--line2)]',
        success: 'text-[var(--ok)] bg-[var(--ok-soft)] border border-[var(--ok-line)]',
        warning: 'text-[var(--warn)] bg-[var(--warn-soft)] border border-[var(--line2)]',
        danger: 'text-[var(--danger)] bg-[var(--danger-soft)] border border-[var(--danger-line)]',
        info: 'text-[var(--accent)] bg-[var(--accent-soft)] border border-[var(--accent-line)]',
      },
      size: {
        sm: 'text-[10px] rounded px-1.5 py-px',
        md: 'text-[11px] rounded-md px-2 py-0.5',
      },
    },
    defaultVariants: { variant: 'default', size: 'md' },
  },
)
const props = defineProps<{ variant?: VariantProps<typeof badgeVariants>['variant']; size?: VariantProps<typeof badgeVariants>['size']; class?: string }>()
const classes = computed(() => cn(badgeVariants({ variant: props.variant, size: props.size }), props.class))
</script>
<template>
  <span :class="classes"><slot /></span>
</template>
