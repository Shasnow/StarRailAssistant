<template>
  <!-- 关于页：卡片式布局（项目信息 / 构建环境 / 技术栈），风格与设置、日志页一致 -->
  <div class="about-page">
    <div class="about-grid">
      <PanelCard title="项目信息" class="card" >
        <GitHubRepoCard/>
      </PanelCard>
      <SystemInfoCard class="card" />
      <BuildEnvCard class="card" />
    </div>
  </div>
</template>

<script setup lang="ts">
import BuildEnvCard from '@/components/BuildEnvCard.vue'
import GitHubRepoCard from '@/components/GitHubRepoCard.vue'
import PanelCard from '@/components/PanelCard.vue';
import SystemInfoCard from '@/components/SystemInfoCard.vue'
</script>

<style scoped>
.about-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 32px 24px 48px;
}

/* 单列纵排 */
.about-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

/* 卡片入场过渡：依次上浮 */
.card {
  animation: about-fade-up 0.5s ease both;
}

.card-build {
  animation-delay: 0.06s;
}

.card-stack {
  animation-delay: 0.12s;
}

@keyframes about-fade-up {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}
</style>
