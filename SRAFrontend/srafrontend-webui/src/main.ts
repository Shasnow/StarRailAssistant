import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useThemeHue } from './composables/useThemeHue'

// 应用启动前应用持久化的主题色相，避免首帧闪色
useThemeHue().init()

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
