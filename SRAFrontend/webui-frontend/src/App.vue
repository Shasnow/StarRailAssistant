<template>
  <main class="app-shell" :class="`page-${activePage}`">
    <AppAtmosphere />

    <LoginPage
      v-if="!auth.isAuthed"
      v-model:token="loginToken"
      :avatar="consoleAvatar"
      :checking="auth.checking"
      :error="auth.error"
      @login="login"
    />

    <template v-else>
      <div class="page-background-stack" aria-hidden="true">
        <img
          v-for="item in backgroundItems"
          :key="item.page"
          :class="{ active: activePage === item.page }"
          :src="item.src"
          alt=""
        />
        <div class="page-background-wash"></div>
      </div>

      <header class="workspace-hero">
        <img class="workspace-hero-bg" :src="heroBanner" alt="" />
        <div class="workspace-hero-overlay"></div>

        <div class="workspace-hero-nav hero-glassbar">
          <div class="hero-brand">
            <img :src="consoleAvatar" alt="" />
            <div>
              <strong>SRA WebUI</strong>
              <span>远程控制台</span>
            </div>
          </div>

          <PageNav />

          <div class="hero-session">
            <span :class="['session-dot', app.health.ok ? 'online' : 'offline']"></span>
            <strong>{{ app.health.ok ? '在线' : '离线' }}</strong>
            <el-button text @click="logout">退出</el-button>
          </div>
        </div>

        <div class="workspace-hero-inner">
          <div class="hero-copy">
            <p class="eyebrow">StarRailAssistant WebUI</p>
            <h1>{{ pageTitle }}</h1>
            <p class="brand-desc">{{ pageDescription }}</p>
          </div>

          <section class="hero-metrics hero-status-strip">
            <article class="hero-metric">
              <span>服务状态</span>
              <strong>{{ app.health.ok ? '在线' : '离线' }}</strong>
            </article>
            <article class="hero-metric">
              <span>任务状态</span>
              <strong>{{ app.sraStatus.running ? '运行中' : '未运行' }}</strong>
            </article>
            <article class="hero-metric">
              <span>当前页面</span>
              <strong>{{ currentPageLabel }}</strong>
            </article>
            <article class="hero-metric">
              <span>日志流</span>
              <strong>{{ app.streaming ? '实时' : '静止' }}</strong>
            </article>
          </section>
        </div>

        <a class="hero-scroll-cue" href="#workspace-content" aria-label="进入控制台">
          <span>进入控制台</span>
          <i></i>
        </a>

        <div class="hero-cut" aria-hidden="true"></div>
        <svg class="hero-waves" viewBox="0 24 150 28" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <path id="gentle-wave" d="M-160 44c30 0 58-18 88-18s58 18 88 18 58-18 88-18 58 18 88 18v44h-352z" />
          </defs>
          <g class="wave-layer">
            <use href="#gentle-wave" x="48" y="0" class="wave-one" />
            <use href="#gentle-wave" x="48" y="3" class="wave-two" />
            <use href="#gentle-wave" x="48" y="6" class="wave-three" />
          </g>
        </svg>
      </header>

      <section id="workspace-content" class="workspace-shell">
        <router-view />
        <p class="workspace-quote">{{ webuiGreeting }}</p>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import consoleAvatar from './assets/console-avatar.jpg'
import heroBanner from './assets/hero-banner.jpg'
import bgExtensions from './assets/bg-extensions.jpg'
import bgLogs from './assets/bg-logs.jpg'
import bgSettings from './assets/bg-settings.jpg'
import bgTasks from './assets/bg-tasks.jpg'
import { useAuthStore } from './stores/auth'
import { useAppStore } from './stores/app'
import AppAtmosphere from './components/AppAtmosphere.vue'
import LoginPage from './views/LoginPage.vue'
import PageNav from './components/PageNav.vue'
import { randomGreeting } from './constants/greetings'
import type { PageKey } from './types'

const auth = useAuthStore()
const app = useAppStore()
const route = useRoute()

const loginToken = ref(auth.token)
const webuiGreeting = randomGreeting()

const backgroundItems: Array<{ page: PageKey; src: string }> = [
  { page: 'tasks', src: bgTasks },
  { page: 'settings', src: bgSettings },
  { page: 'extensions', src: bgExtensions },
  { page: 'logs', src: bgLogs }
]

const activePage = computed<PageKey>(() => {
  const page = String(route.path).replace('/', '') as PageKey
  return ['tasks', 'settings', 'extensions', 'logs'].includes(page) ? page : 'tasks'
})

const currentPageLabel = computed(() => {
  const labels: Record<PageKey, string> = {
    tasks: '任务',
    settings: '设置',
    extensions: '拓展',
    logs: '日志'
  }
  return labels[activePage.value]
})

const pageTitle = computed(() => {
  const titles: Record<PageKey, string> = {
    tasks: '远程控制台',
    settings: '设置中心',
    extensions: '拓展中心',
    logs: '运行日志'
  }
  return titles[activePage.value]
})

const pageDescription = computed(() => {
  const descriptions: Record<PageKey, string> = {
    tasks: '以更干净的控制台式布局承载任务、配置与运行状态，让桌面和手机都能直接操作。',
    settings: '将分散的系统项整理成分区明确的配置中心，常用项优先可见，复杂项保留深入入口。',
    extensions: '围绕常见扩展做成可直达的控制面板，减少跳转，也方便观察后端状态。',
    logs: '把日志查看做成更接近流式面板的体验，支持实时查看、刷新和长度控制。'
  }
  return descriptions[activePage.value]
})

async function login() {
  try {
    await auth.login(loginToken.value)
    await app.refreshAll()
  } catch {
    // Error is already set in auth store
  }
}

function logout() {
  auth.logout()
  loginToken.value = ''
}

onMounted(async () => {
  const ok = await auth.verifyStoredToken()
  if (ok) {
    loginToken.value = auth.token
    await app.refreshAll()
  }
})
</script>
