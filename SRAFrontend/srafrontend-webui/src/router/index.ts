import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/tasks' },
    { path: '/login', component: () => import('@/views/LoginPage.vue') },
    { path: '/tasks', component: () => import('@/views/TasksPage.vue'), meta: { requiresAuth: true } },
    { path: '/settings', component: () => import('@/views/SettingsPage.vue'), meta: { requiresAuth: true } },
    { path: '/extensions', component: () => import('@/views/ExtensionsPage.vue'), meta: { requiresAuth: true } },
    { path: '/logs', component: () => import('@/views/LogsPage.vue'), meta: { requiresAuth: true } }
  ]
})

router.beforeEach((to) => {
  const token = localStorage.getItem('sra-webui-token')
  if (to.meta.requiresAuth && !token) return '/login'
  if (to.path === '/login' && token) return '/tasks'
})

export default router
