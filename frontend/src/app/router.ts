import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/features/auth/LoginPage.vue') },
    { path: '/', redirect: '/chat' },
    { path: '/', component: () => import('./WorkbenchLayout.vue'), children: [
      { path: 'chat/:conversationId?', name: 'chat', component: () => import('@/features/chat/ChatPage.vue') },
      { path: 'products', component: () => import('@/features/products/ProductsPage.vue') },
      { path: 'documents', component: () => import('@/features/documents/DocumentsPage.vue') },
      { path: 'cases', component: () => import('@/features/cases/CasesPage.vue') },
      { path: 'evaluations', component: () => import('./DeferredPage.vue'), props: { title: '评测工作台', message: '评测管理尚未开放，当前没有可展示的评测结果。' } },
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
