<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NavBar from './components/NavBar.vue'
import HeroSection from './components/HeroSection.vue'
import FooterSection from './components/FooterSection.vue'

// 全屏独立页（登录页）：不渲染导航栏 / Hero / 页脚
const route = useRoute()
const bare = computed(() => route.meta.bare === true)
</script>

<template>
  <!-- 全局消息配置：顶部固定导航栏占 60px，ElMessage 默认贴顶弹出会被遮挡，统一下移到导航栏下方 -->
  <ElConfigProvider :message="{ offset: 76 }">
    <template v-if="!bare">
      <NavBar />

      <!-- 全局 Hero：所有页面共用，内容区紧随其后 -->
      <HeroSection />
    </template>

    <main id="page-content" class="page-content">
      <RouterView />
    </main>

    <FooterSection v-if="!bare" />
  </ElConfigProvider>
</template>