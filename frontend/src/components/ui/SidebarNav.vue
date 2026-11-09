<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, MessageSquare, ClipboardCheck, Server, FolderOpen, FlaskConical, Search, LogOut } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import BrandMark from '@/components/ui/BrandMark.vue'
import ConversationList from '@/features/chat/components/ConversationList.vue'
import { useCreateConversation } from '@/features/chat/composables/useCreateConversation'
import { ref } from 'vue'

const auth = useAuthStore(), ui = useUiStore(), route = useRoute(), router = useRouter()
const { creating, createConversation } = useCreateConversation()

/* P4-1③ 分组导航（对照 ui-final-v6.html 侧栏） */
const groups = [
  { label: '工作台', tag: 'WORKSPACE', items: [
    { to: '/chat', label: '技术问答', icon: MessageSquare },
    { to: '/cases', label: '支持流程', icon: ClipboardCheck },
  ]},
  { label: '知识库', tag: 'KNOWLEDGE', items: [
    { to: '/products', label: '设备目录', icon: Server },
    { to: '/documents', label: '资料管理', icon: FolderOpen },
  ]},
  { label: '质量', tag: 'QUALITY', items: [
    { to: '/evaluations', label: '评测工作台', icon: FlaskConical },
  ]},
]
function isActive(to: string) { return to === '/chat' ? route.path === '/chat' || route.path.startsWith('/chat/') : route.path.startsWith(to) }

/* P4-1⑥ 用户卡片：首两字母大写头像 + 角色 mono 标 */
const initials = computed(() => (auth.user?.username || '?').slice(0, 2).toUpperCase())
const role = computed(() => (auth.user?.role || '').toUpperCase())
async function logout() { try { await auth.logout() } finally { ui.clear(); window.dispatchEvent(new Event('close-run-streams')); void router.replace('/login') } }

/* P4-1⑤ 会话搜索（前端按标题过滤） */
const keyword = ref('')
</script>
<template>
<div class="sb-root">
  <!-- ① 品牌区 -->
  <div class="brand"><span class="brand-mark"><BrandMark :size="26" /></span><div><strong>知衡</strong><p class="muted">设备技术支持</p></div></div>
  <!-- ② 新建会话主钮 -->
  <button class="sb-newbtn" :disabled="creating" @click="createConversation"><Plus :size="13" :stroke-width="2" />{{ creating ? '正在新建…' : '新建会话' }}</button>
  <!-- ③ 分组导航 -->
  <nav aria-label="工作台导航" class="sb-nav" @click="ui.menu = false">
    <template v-for="g in groups" :key="g.label">
      <div class="sb-grp mono">{{ g.label }} {{ g.tag }}</div>
      <RouterLink v-for="item in g.items" :key="item.to" :to="item.to" class="sb-item" :class="{ on: isActive(item.to) }">
        <component :is="item.icon" :size="15" :stroke-width="1.8" />{{ item.label }}
      </RouterLink>
    </template>
  </nav>
  <!-- ④ 知识范围卡 -->
  <label class="sb-kb"><span class="k mono">知识范围</span><select v-model="auth.kb" @change="$emit('scope-changed')"><option v-for="kb in auth.user?.kb_ids" :key="kb" :value="kb">{{ auth.labelOf(kb) }}</option></select></label>
  <!-- ⑤ 会话搜索 + 列表 -->
  <div class="sb-convs">
    <div class="sb-search"><Search :size="12" :stroke-width="2" /><input id="conversation-directory" v-model="keyword" placeholder="搜索会话…" aria-label="搜索会话"></div>
    <ConversationList :keyword="keyword" />
  </div>
  <!-- ⑥ 用户卡片 -->
  <footer class="sb-me">
    <span class="sb-av">{{ initials }}</span>
    <span class="sb-meta"><span class="n">{{ auth.user?.username }}</span><span class="r mono">{{ role }}</span></span>
    <button class="sb-logout" aria-label="退出登录" @click="logout"><LogOut :size="14" :stroke-width="1.8" /></button>
  </footer>
</div>
</template>
<script lang="ts">
export default { name: 'SidebarNav' }
</script>
<style scoped>
.sb-root { display: flex; flex-direction: column; gap: 0; min-height: 0; height: 100%; }
.brand { display: flex; align-items: center; gap: 12px; padding: 2px 4px 10px; }
.brand strong { font-size: 1.2rem; letter-spacing: .14em; color: var(--ink); }
.brand p { font-size: .72rem; margin: 1px 0 0; }
.brand-mark { display: inline-flex; }
/* ② 新建钮：v6 设计稿 newbtn 语义 */
.sb-newbtn { display: flex; align-items: center; justify-content: center; gap: 7px; margin: 2px 12px 8px; border: 1px solid var(--line2); background: var(--bg); color: var(--ink); border-radius: 9px; padding: 7px 0; font-size: 12.5px; font-weight: 600; cursor: pointer; }
.sb-newbtn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.sb-newbtn:disabled { opacity: .6; cursor: wait; }
/* ③ 分组导航 */
.sb-nav { padding: 0 10px; }
.sb-grp { font-size: 8.5px; letter-spacing: 0.15em; color: var(--ink3); padding: 11px 9px 5px; }
.sb-item { position: relative; display: flex; align-items: center; gap: 9px; padding: 6.5px 9px; border-radius: 7px; color: var(--ink2); font-size: 12.5px; font-weight: 500; text-decoration: none; }
.sb-item :deep(svg) { color: var(--ink3); flex-shrink: 0; }
.sb-item:hover { background: color-mix(in srgb, var(--line) 55%, transparent); color: var(--ink); }
.sb-item.on { background: color-mix(in srgb, var(--accent) 10%, transparent); color: var(--ink); font-weight: 600; }
.sb-item.on::before { content: ''; position: absolute; left: 0; top: 6px; bottom: 6px; width: 2.5px; border-radius: 2px; background: var(--accent); }
.sb-item.on :deep(svg) { color: var(--accent); }
/* ④ kb 卡 */
.sb-kb { margin: 10px 12px 2px; padding: 8px 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); display: grid; gap: 4px; }
.sb-kb .k { font-size: 8px; letter-spacing: 0.13em; color: var(--ink3); }
.sb-kb select { border: 1px solid var(--line2); border-radius: 6px; padding: 5px 8px; font-size: 12px; font-weight: 600; background: var(--bg); color: var(--ink); }
/* ⑤ 会话区 */
.sb-convs { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 8px 12px 0; }
.sb-search { display: flex; align-items: center; gap: 7px; border: 1px solid var(--line2); border-radius: 7px; padding: 5px 9px; margin-bottom: 8px; color: var(--ink3); }
.sb-search:focus-within { border-color: var(--accent); }
.sb-search input { border: none; outline: none; background: transparent; color: var(--ink); font-size: 12px; padding: 0; width: 100%; }
/* ⑥ 用户卡 */
.sb-me { display: flex; align-items: center; gap: 9px; padding: 10px 14px 4px; border-top: 1px solid var(--line); margin-top: 8px; }
.sb-av { width: 26px; height: 26px; border-radius: 50%; background: var(--accent-soft); color: var(--accent); display: grid; place-items: center; font-size: 10px; font-weight: 700; flex-shrink: 0; }
.sb-meta { flex: 1; min-width: 0; display: grid; }
.sb-meta .n { font-size: 12px; font-weight: 600; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sb-meta .r { font-size: 8px; letter-spacing: 0.12em; color: var(--ink3); }
.sb-logout { border: none; background: transparent; color: var(--ink3); padding: 5px; border-radius: 6px; cursor: pointer; display: inline-flex; }
.sb-logout:hover { color: var(--danger); background: var(--danger-soft); }
.mono { font-family: ui-monospace, Consolas, monospace; }
</style>
