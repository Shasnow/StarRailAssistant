<template>
  <main class="app-shell" :class="`page-${activePage}`">
    <AppAtmosphere />

    <template v-if="app.isAuthed">
      <div class="page-background-stack" aria-hidden="true">
        <img
          v-for="item in pageBackgrounds"
          :key="item.page"
          :class="{ active: activePage === item.page }"
          :src="item.src"
          alt=""
        />
        <div class="page-background-wash"></div>
      </div>

      <WorkspaceHero
        :avatar="theme.avatar"
        :hero-bg="theme.backgrounds.hero"
        :health-ok="app.health.ok"
        :task-running="app.sraStatus.running"
        :streaming="app.streaming"
        :page-title="pageTitle"
        :page-description="pageDescription"
        :current-page-label="currentPageLabel"
        @logout="logout"
      />

      <section id="workspace-content" class="workspace-shell">
        <router-view />
        <p class="workspace-quote">{{ webuiGreeting }}</p>
      </section>
    </template>

    <router-view v-else />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import theme from './configs/theme'
import { useAppStore } from './stores/app'
import AppAtmosphere from './components/AppAtmosphere.vue'
import WorkspaceHero from './components/WorkspaceHero.vue'
import { randomGreeting } from './constants/greetings'
import type { PageKey } from './types'

const app = useAppStore()
const route = useRoute()
const router = useRouter()

const webuiGreeting = randomGreeting()

const pageBackgrounds = Object.entries(theme.backgrounds)
  .filter(([key]) => key !== 'hero')
  .map(([page, src]) => ({ page: page as PageKey, src }))

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

function logout() {
  app.logout()
  router.push('/login')
}

onMounted(async () => {
  await app.verifyStoredToken()
  if (app.isAuthed) await app.refreshAll()
})
</script>
