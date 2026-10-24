<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
import { SplitterPanel, SplitterResizeHandle } from 'reka-ui'
import { useRouter } from 'vue-router'
import Sidebar from '@/components/ui/sidebar/Sidebar.vue'
import Modal from '@/components/ui/dialog/Modal.vue'
import ResizablePanelGroup from '@/components/ui/resizable/ResizablePanelGroup.vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import ConversationList from '@/features/chat/components/ConversationList.vue'
import EvidenceDrawer from '@/features/evidence/components/EvidenceDrawer.vue'
const auth = useAuthStore(), ui = useUiStore(), router = useRouter()
const mobile = useMediaQuery('(max-width: 767px)')
function scopeChanged() { ui.clear(); window.dispatchEvent(new Event('close-run-streams')); void router.push('/chat') }
async function logout() { try { await auth.logout() } finally { ui.clear(); void router.replace('/login') } }
</script>
<template><div class="workbench">
<Sidebar v-model:open="ui.menu"><div class="brand"><span class="brand-mark">衡</span><div><strong>知衡</strong><p class="muted">设备技术支持</p></div></div>
<label class="scope">知识范围<select v-model="auth.kb" @change="scopeChanged"><option v-for="kb in auth.user?.kb_ids" :key="kb" :value="kb">{{ kb }}</option></select></label>
<nav aria-label="工作台导航" @click="ui.menu = false"><RouterLink to="/chat">技术问答</RouterLink><RouterLink to="/products">设备目录</RouterLink><RouterLink to="/documents">资料管理</RouterLink><RouterLink to="/cases">处理记录</RouterLink><RouterLink to="/evaluations">评测工作台</RouterLink></nav>
<div id="conversation-directory"><ConversationList /></div>
<footer><span>{{ auth.user?.username }}</span><button @click="logout">退出登录</button></footer>
</Sidebar>
<div class="workspace"><header class="topbar"><div><button v-if="mobile" aria-label="打开会话导航" @click="ui.menu = true">目录</button><span class="eyebrow">知识支持 / 工作台</span></div><button v-if="mobile" aria-label="打开证据" @click="ui.evidence = true">证据</button><span v-else class="muted">依据可查 · 适用范围明确</span></header>
<ResizablePanelGroup direction="horizontal" class="workspace-panels"><SplitterPanel :default-size="68" :min-size="mobile ? 100 : 38" data-testid="question-panel"><main id="main-content" class="page-content"><RouterView /></main></SplitterPanel>
<template v-if="!mobile"><SplitterResizeHandle aria-label="调整问答与证据宽度" class="resize-handle" /><SplitterPanel :default-size="32" :min-size="23"><EvidenceDrawer /></SplitterPanel></template>
</ResizablePanelGroup></div>
<EvidenceDrawer v-if="mobile" />
</div></template>
