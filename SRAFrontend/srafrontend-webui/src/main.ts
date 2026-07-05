import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'element-plus/dist/index.css'
import './styles/app.css'
import App from './App.vue'
import router from './router'
import { applyTheme } from './configs/theme'

applyTheme()

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
