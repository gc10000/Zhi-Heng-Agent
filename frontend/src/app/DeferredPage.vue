<script setup lang="ts">
defineProps<{ title: string; message: string }>()
</script>
<template><section class="empty-state"><p class="eyebrow">工作台</p><h1>{{ title }}</h1><p>{{ message }}</p><RouterLink to="/chat">返回技术问答</RouterLink></section></template>
