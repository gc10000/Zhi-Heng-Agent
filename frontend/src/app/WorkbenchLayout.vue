<script setup lang="ts">
import { computed } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { SplitterPanel, SplitterResizeHandle } from 'reka-ui'
import { useRoute, useRouter } from 'vue-router'
import Sidebar from '@/components/ui/sidebar/Sidebar.vue'
import SidebarNav from '@/components/ui/SidebarNav.vue'
import ResizablePanelGroup from '@/components/ui/resizable/ResizablePanelGroup.vue'
import { useUiStore } from '@/stores/ui'
import ThemeToggle from '@/components/ui/ThemeToggle.vue'
import EvidenceDrawer from '@/features/evidence/components/EvidenceDrawer.vue'
const ui = useUiStore(), route = useRoute(), router = useRouter()
const mobile = useMediaQuery('(max-width: 767px)')
/* P4-2：证据栏仅聊天路由常驻；目录/资料/支持/评测页主区全宽（消"半屏空置"先天缺陷） */
const showEvidence = computed(() => route.meta.evidence === true && !mobile.value)
function scopeChanged() { ui.clear(); window.dispatchEvent(new Event('close-run-streams')); void router.push('/chat') }
</script>
<template><div class="workbench">
<a class="skip-link" href="#main-content" @click="($event.currentTarget as HTMLElement).ownerDocument.getElementById('main-content')?.focus()">跳到主要内容</a>
<Sidebar v-model:open="ui.menu"><SidebarNav @scope-changed="scopeChanged" /></Sidebar>
<div class="workspace"><header class="topbar"><div><button v-if="mobile" aria-label="打开会话导航" @click="ui.menu = true">目录</button><span class="eyebrow">知识支持 / 工作台</span></div><div class="topbar-right"><button v-if="mobile" aria-label="打开证据" @click="ui.evidence = true">证据</button><span v-else class="muted">依据可查 · 适用范围明确</span><ThemeToggle /></div></header>
<ResizablePanelGroup direction="horizontal" class="workspace-panels"><SplitterPanel :default-size="68" :min-size="mobile ? 100 : 38" data-testid="question-panel"><main id="main-content" tabindex="-1" class="page-content"><RouterView /></main></SplitterPanel>
<template v-if="showEvidence"><SplitterResizeHandle aria-label="调整问答与证据宽度" class="resize-handle" /><SplitterPanel :default-size="32" :min-size="23"><EvidenceDrawer /></SplitterPanel></template>
</ResizablePanelGroup></div>
<EvidenceDrawer v-if="mobile" />
</div></template>
