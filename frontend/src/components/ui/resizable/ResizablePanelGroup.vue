<!-- 来源：shadcn-vue de1f76c，MIT；将注册表别名调整为项目工具。 -->
<script setup lang="ts">
import type { SplitterGroupEmits, SplitterGroupProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { reactiveOmit } from '@vueuse/core'
import { cn } from '@/lib/utils'
import { SplitterGroup, useForwardPropsEmits } from 'reka-ui'
const props = defineProps<SplitterGroupProps & { class?: HTMLAttributes['class'] }>()
const emits = defineEmits<SplitterGroupEmits>()
const delegatedProps = reactiveOmit(props, 'class')
const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>
<template><SplitterGroup v-slot="slotProps" data-slot="resizable-panel-group" v-bind="forwarded" :class="cn('flex h-full w-full data-[orientation=vertical]:flex-col', props.class)"><slot v-bind="slotProps" /></SplitterGroup></template>
