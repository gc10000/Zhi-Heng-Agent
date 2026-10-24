import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/features/auth/LoginPage.vue') },
    { path: '/', redirect: '/chat' },
    { path: '/chat/:conversationId?', name: 'chat', component: () => import('@/features/chat/CompatibilityPage.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/chat' },
  ],
})
router.beforeEach(async to => {
  const auth = useAuthStore()
  if (!auth.restored) await auth.restore()
  if (!auth.user && to.name !== 'login') return { name: 'login' }
  if (auth.user && to.name === 'login') return { name: 'chat' }
})
