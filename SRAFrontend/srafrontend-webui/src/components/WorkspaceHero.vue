<template>
  <header class="workspace-hero">
    <div class="workspace-hero-bg-stack" aria-hidden="true">
      <img :src="heroBg" alt="" class="workspace-hero-bg active" />
    </div>
    <div class="workspace-hero-overlay"></div>

    <div class="workspace-hero-nav hero-glassbar">
      <div class="hero-brand">
        <img :src="avatar" alt="" />
        <div>
          <strong>SRA WebUI</strong>
          <span>远程控制台</span>
        </div>
      </div>

      <PageNav />

      <div class="hero-session">
        <span :class="['session-dot', healthOk ? 'online' : 'offline']"></span>
        <strong>{{ healthOk ? '在线' : '离线' }}</strong>
        <el-button text @click="$emit('logout')">退出</el-button>
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
          <strong>{{ healthOk ? '在线' : '离线' }}</strong>
        </article>
        <article class="hero-metric">
          <span>任务状态</span>
          <strong>{{ taskRunning ? '运行中' : '未运行' }}</strong>
        </article>
        <article class="hero-metric">
          <span>当前页面</span>
          <strong>{{ currentPageLabel }}</strong>
        </article>
        <article class="hero-metric">
          <span>日志流</span>
          <strong>{{ streaming ? '实时' : '静止' }}</strong>
        </article>
      </section>
    </div>

    <a class="hero-scroll-cue" href="#" aria-label="进入控制台" @click.prevent="scrollToWorkspace">
      <span>进入控制台</span>
      <i></i>
    </a>

    <div class="hero-cut" aria-hidden="true"></div>
    <HeroWaves />
  </header>
</template>

<script setup lang="ts">
import HeroWaves from './HeroWaves.vue'
import PageNav from './PageNav.vue'

defineProps<{
  avatar: string
  heroBg: string
  healthOk: boolean
  taskRunning: boolean
  streaming: boolean
  pageTitle: string
  pageDescription: string
  currentPageLabel: string
}>()

defineEmits<{
  logout: []
}>()

function scrollToWorkspace() {
  document.getElementById('workspace-content')?.scrollIntoView({ behavior: 'smooth' })
}
</script>
