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
  <template v-if="!bare">
    <NavBar />

    <!-- 全局 Hero：所有页面共用，内容区紧随其后 -->
    <HeroSection />
  </template>

  <main id="page-content" class="page-content">
    <RouterView />
  </main>

  <FooterSection v-if="!bare" />
</template>