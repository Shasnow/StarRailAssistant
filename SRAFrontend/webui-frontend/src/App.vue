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
        <div class="workspace-hero-bg-stack" aria-hidden="true">
          <img
            v-for="(src, index) in heroSlides"
            :key="src"
            class="workspace-hero-bg"
            :class="{ active: heroSlideIndex === index }"
            :src="src"
            alt=""
          />
        </div>
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
        <div class="hero-waves" aria-hidden="true">
          <svg class="wave-svg wave-back" viewBox="0 0 2400 140" preserveAspectRatio="none">
            <path d="M0 74c120-42 220-42 340 0s220 42 340 0 220-42 340 0 220 42 340 0 220-42 340 0 220 42 340 0 360 0 360 0v66H0z" />
          </svg>
          <svg class="wave-svg wave-mid" viewBox="0 0 2400 140" preserveAspectRatio="none">
            <path d="M0 68c132-30 230-26 360 8s228 34 360-8 230-42 360 0 228 42 360 0 230-38 360-4 600 4 600 4v72H0z" />
          </svg>
          <svg class="wave-svg wave-front" viewBox="0 0 2400 140" preserveAspectRatio="none">
            <path d="M0 54c116 0 178 46 300 46s184-46 300-46 178 46 300 46 184-46 300-46 178 46 300 46 184-42 300-42 194 34 300 34 300-24 300-24v72H0z" />
          </svg>
        </div>
      </header>

      <section id="workspace-content" class="workspace-shell">
        <router-view />
        <p class="workspace-quote">{{ webuiGreeting }}</p>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import consoleAvatar from './assets/console-avatar.jpg'
import heroBanner from './assets/hero-banner.jpg'
import bgExtensions from './assets/bg-extensions.jpg'
import bgLogin from './assets/bg-login.jpg'
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
const heroSlideIndex = ref(0)

const backgroundItems: Array<{ page: PageKey; src: string }> = [
  { page: 'tasks', src: bgTasks },
  { page: 'settings', src: bgSettings },
  { page: 'extensions', src: bgExtensions },
  { page: 'logs', src: bgLogs }
]
const heroSlides = [heroBanner, bgTasks, bgSettings, bgExtensions, bgLogs, bgLogin]
let heroSlideTimer: number | undefined

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
  heroSlideTimer = window.setInterval(() => {
    heroSlideIndex.value = (heroSlideIndex.value + 1) % heroSlides.length
  }, 10000)

  const ok = await auth.verifyStoredToken()
  if (ok) {
    loginToken.value = auth.token
    await app.refreshAll()
  }
})

onUnmounted(() => {
  if (heroSlideTimer !== undefined) window.clearInterval(heroSlideTimer)
})
</script>
