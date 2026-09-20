<script lang="ts">
/** 导航项：对应 AppSettings 的一个大类（section） */
export interface NavSection {
  key: string
  label: string
}
</script>

<template>
  <PanelCard title="设置导航">
    <nav class="nav" aria-label="设置项导航">
      <!-- 仅展示大类：点击滚动到对应 section -->
      <button v-for="section in sections" :key="section.key" type="button" class="nav-item"
        :class="{ active: activeKey === section.key }" :aria-current="activeKey === section.key ? 'true' : undefined"
        @click="$emit('select', section.key)">
        {{ section.label }}
      </button>
    </nav>
  </PanelCard>
</template>

<script setup lang="ts">
import PanelCard from './PanelCard.vue'

defineProps<{
  sections: NavSection[]
  /** 当前选中的大类（section key），由右侧内容区的滚动位置驱动 */
  activeKey: string
}>()

defineEmits<{ select: [anchor: string] }>()
</script>

<style scoped>
.nav {
  display: grid;
  gap: 4px;
}

.nav-item {
  display: block;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-heading);
  cursor: pointer;
  transition:
    background 0.2s,
    color 0.2s;
}

.nav-item:hover {
  background: var(--color-background-mute);
}

/* 选中态：主色文字 + 淡主色底 + 左侧指示条 */
.nav-item.active {
  color: var(--el-color-primary);
  background: color-mix(in srgb, var(--el-color-primary) 12%, transparent);
  box-shadow: inset 2px 0 0 var(--el-color-primary);
}
</style>
