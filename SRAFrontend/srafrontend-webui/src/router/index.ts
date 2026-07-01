import { createRouter, createWebHashHistory } from 'vue-router'
import TasksPage from '@/views/TasksPage.vue'
import SettingsPage from '@/views/SettingsPage.vue'
import ExtensionsPage from '@/views/ExtensionsPage.vue'
import LogsPage from '@/views/LogsPage.vue'
import LoginPage from '@/views/LoginPage.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/tasks' },
    { path: '/login', component: LoginPage },
    { path: '/tasks', component: TasksPage, meta: { requiresAuth: true } },
    { path: '/settings', component: SettingsPage, meta: { requiresAuth: true } },
    { path: '/extensions', component: ExtensionsPage, meta: { requiresAuth: true } },
    { path: '/logs', component: LogsPage, meta: { requiresAuth: true } }
  ]
})

router.beforeEach((to) => {
  const token = localStorage.getItem('sra-webui-token')
  if (to.meta.requiresAuth && !token) return '/login'
  if (to.path === '/login' && token) return '/tasks'
})

export default router
