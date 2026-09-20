<template>
  <section class="panel">
    <header class="panel-header">
      <span class="panel-bar" aria-hidden="true"></span>
      <h2 class="panel-title">{{ title }}</h2>
    </header>
    <div class="panel-body">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
// 统一卡片外壳：一致的边框、阴影、内边距与标题栏，具体内容由默认插槽提供
defineProps<{ title: string }>()
</script>

<style scoped>
.panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: var(--shadow-sm), var(--shadow-lg);
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 13px 18px;
  border-bottom: 1px solid var(--color-border);
}

.panel-bar {
  width: 4px;
  height: 14px;
  border-radius: 2px;
  background: var(--el-color-primary);
  flex: none;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-heading);
  line-height: 1.4;
}

.panel-body {
  padding: 16px 18px;
}
</style>
