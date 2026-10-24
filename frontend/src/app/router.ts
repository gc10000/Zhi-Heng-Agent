import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/features/auth/LoginPage.vue') },
    { path: '/', redirect: '/chat' },
    { path: '/', component: () => import('./WorkbenchLayout.vue'), children: [
      { path: 'chat/:conversationId?', name: 'chat', component: () => import('@/features/chat/ChatPage.vue') },
      { path: 'products', component: () => import('./DeferredPage.vue'), props: { title: '设备目录', message: '设备目录接线将于M3-09完成。当前可在问答中确认适用型号。' } },
      { path: 'documents', component: () => import('./DeferredPage.vue'), props: { title: '资料管理', message: '资料上传和修订发布接线将于M3-09完成。' } },
      { path: 'cases', component: () => import('./DeferredPage.vue'), props: { title: '处理记录', message: '处理记录将在M5实现；模型建议不会被记为已执行操作。' } },
      { path: 'evaluations', component: () => import('./DeferredPage.vue'), props: { title: '评测工作台', message: '评测管理将在M6实现，当前没有可展示的评测结果。' } },
    ] },
    { path: '/:pathMatch(.*)*', redirect: '/chat' },
  ],
})
router.beforeEach(async to => {
  const auth = useAuthStore()
  if (!auth.restored) await auth.restore()
  if (!auth.user && to.name !== 'login') return { name: 'login' }
  if (auth.user && to.name === 'login') return { name: 'chat' }
})
