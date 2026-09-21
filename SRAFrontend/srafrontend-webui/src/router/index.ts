import { createRouter, createWebHistory } from 'vue-router'
import type { Component } from 'vue'
import { Document, HomeFilled, InfoFilled, Setting } from '@element-plus/icons-vue'
import HomeView from '../views/HomeView.vue'
import { clearStoredToken, setUnauthorizedHandler } from '@/api/http'

// 路由 meta 类型扩展：图标组件直接挂在 meta 上，导航栏读取渲染，新增页面无需改动 NavBar
declare module 'vue-router' {
  interface RouteMeta {
    /** 导航栏展示标题 */
    title?: string
    /** 导航栏图标（Element Plus 图标组件） */
    icon?: Component
    /** 全屏独立页：不渲染导航栏 / Hero / 页脚（如登录页） */
    bare?: boolean
    /** 不在导航栏中展示（如登录页） */
    hideInNav?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: '首页',
      component: HomeView,
      meta: {
        title: '首页',
        icon: HomeFilled,
      },
    },
    {
      path: '/settings',
      name: '设置',
      // 懒加载：设置页依赖 OpenAPI 规范解析，独立 chunk 按需加载
      component: () => import('../views/SettingsView.vue'),
      meta: {
        title: '设置',
        icon: Setting,
      },
    },
    {
      path: '/logs',
      name: '日志',
      // 懒加载：日志页包含 SSE 流与分页渲染逻辑，独立 chunk 按需加载
      component: () => import('../views/LogView.vue'),
      meta: {
        title: '日志',
        icon: Document,
      },
    },
    {
      path: '/about',
      name: '关于',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/AboutView.vue'),
      meta: {
        title: '关于',
        icon: InfoFilled,
      },
    },
    {
      path: '/login',
      name: '登录',
      // 懒加载：仅在后端启用了 access token 校验时才会进入
      component: () => import('../views/LoginView.vue'),
      meta: {
        title: '登录',
        // 全屏独立页：不渲染导航栏 / Hero / 页脚，且不出现在导航链接中
        bare: true,
        hideInNav: true,
      },
    },
  ],
})

/* ---------- 认证流程接入 ---------- */

// 进入时不做任何认证探测：后端启用认证时，首个业务请求返回 401 即触发这里——
// 清除本地失效 token 并跳转登录页（登录成功后按 redirect 参数回跳）
setUnauthorizedHandler(() => {
  clearStoredToken()
  const current = router.currentRoute.value
  if (current.name === '登录') return
  void router.replace({
    name: '登录',
    query: current.fullPath === '/' ? {} : { redirect: current.fullPath },
  })
})

export default router
