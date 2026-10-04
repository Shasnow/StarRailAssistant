import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useThemeHue } from './composables/useThemeHue'

// 应用启动前应用持久化的主题色相，避免首帧闪色
useThemeHue().init()

// 演示模式：任何请求发出前完成装配（adapter 接管 / 日志源工厂注册）。
// 重模块走动态 import；__IS_DEMO__ 为 define 注入的编译期常量，
// 正式构建下该分支被整体消除、demo 代码不进产物。
if (__IS_DEMO__) {
  const mod = await import('./demo/install')
  mod.installDemoMode()
}

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
