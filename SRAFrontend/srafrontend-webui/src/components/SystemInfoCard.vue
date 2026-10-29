<template>
  <PanelCard :title="t('system.title')" class="stack-card">
    <div v-if="loading" class="backend-loading">
      <el-skeleton animated :rows="3" />
    </div>
    <div v-else-if="info" class="info-grid">
      <DataCard v-for="row in backendRows" :key="row.label" :title="row.label" :value="row.value" :icon="row.icon" />
    </div>
  </PanelCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import { computed, onMounted, ref } from 'vue'
import { fetchSystemInfo, type AppSystemInfo } from '@/api/app'
import PanelCard from './PanelCard.vue'
import WindowIcon from './icons/WindowIcon.vue'
import ServerIcon from './icons/ServerIcon.vue'
import WindowsIcon from './icons/WindowsIcon.vue'
import DotnetIcon from './icons/DotnetIcon.vue'

const { t } = useI18n()


// __BUILD_INFO__ 由 vite.config.ts 在构建时经 define 注入（见 env.d.ts 类型声明）
const appVersion = __BUILD_INFO__.appVersion

/* ---------- 后端运行时信息 ---------- */
const loading = ref(true)
const info = ref<AppSystemInfo | null>(null)

onMounted(async () => {
  try {
    info.value = await fetchSystemInfo()
  } catch {
    info.value = null
  } finally {
    loading.value = false
  }
})

/** 后端字段 → 中文标签卡片，缺失值以 — 占位 */
const backendRows = computed(() => {
  const d = info.value
  if (!d) return []
  return [
    { icon: WindowIcon, label: t('system.frontendVersion'), value: appVersion || '—' },
    { icon: ServerIcon, label: t('system.backendVersion'), value: d.version || '—' },
    { icon: WindowsIcon, label: t('system.os'), value: `${d.osVersion} / ${d.architecture}` },
    { icon: DotnetIcon, label: t('system.dotnetRuntime'), value: d.dotnetVersion || '—' },
  ]
})
</script>

<style scoped>
/* 数据卡片网格：自适应列数，窄屏回落单列 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.backend-loading {
  padding: 6px 0;
}
</style>
