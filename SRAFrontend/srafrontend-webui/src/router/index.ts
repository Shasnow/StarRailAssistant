import { createRouter, createWebHashHistory } from 'vue-router'
import TasksPage from '@/views/TasksPage.vue'
import SettingsPage from '@/views/SettingsPage.vue'
import ExtensionsPage from '@/views/ExtensionsPage.vue'
import LogsPage from '@/views/LogsPage.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/tasks' },
    { path: '/tasks', component: TasksPage },
    { path: '/settings', component: SettingsPage },
    { path: '/extensions', component: ExtensionsPage },
    { path: '/logs', component: LogsPage }
  ]
})

export default router
