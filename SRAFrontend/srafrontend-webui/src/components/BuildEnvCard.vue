<template>
  <PanelCard title="构建环境" class="build-card">
    <div class="build-grid">
      <DataCard
        v-for="row in rows"
        :key="row.label"
        :icon="row.icon"
        :title="row.label"
        :value="row.value"
        :hint="row.hint"
      />
    </div>
  </PanelCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Component } from 'vue'
import NodeLogoIcon from './icons/NodeLogoIcon.vue'
import PanelCard from './PanelCard.vue'
import PnpmLogoIcon from './icons/PnpmLogoIcon.vue'
import TypescriptLogoIcon from './icons/TypescriptLogoIcon.vue'
import ViteLogoIcon from './icons/ViteLogoIcon.vue'

interface BuildRow {
  icon: Component
  label: string
  value: string
  hint?: string
}

// __BUILD_INFO__ 由 vite.config.ts 在构建时经 define 注入（见 env.d.ts 类型声明）
const build = __BUILD_INFO__

const rows = computed<BuildRow[]>(() => [
  {
    icon: NodeLogoIcon,
    label: 'Node.js',
    value: build.node,
    hint: `要求 ${build.nodeRequired}`,
  },
  {
    icon: PnpmLogoIcon,
    label: 'pnpm',
    value: build.pnpm || build.pnpmRequired,
    hint: build.pnpm ? `要求 ${build.pnpmRequired}` : '取自 packageManager 声明',
  },
  {
    icon: ViteLogoIcon,
    label: 'Vite',
    value: build.deps.vite ?? '—',
  },
  {
    icon: TypescriptLogoIcon,
    label: 'TypeScript',
    value: build.deps.typescript ?? '—',
  },
])
</script>

<style scoped>
/* 数据卡片网格：自适应列数，窄屏回落单列 */
.build-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

</style>
