<template>
    <el-card class="data-card" shadow="never">
        <el-icon v-if="icon" :size="24" class="data-card-icon">
            <component :is="icon" />
        </el-icon>
        <div class="data-card-title">{{ title }}</div>
        <div class="data-card-value" :title="hint ?? value">{{ value }}</div>
    </el-card>
</template>

<script lang="ts" setup>
import type { Component } from 'vue'

withDefaults(
    defineProps<{
        /** 图标组件（品牌图标以 currentColor 绘制，自动继承主题色）；缺省不渲染 */
        icon?: Component
        title: string
        value: string
        /** 悬停提示（如版本要求）；缺省时提示 value，用于查看截断的完整内容 */
        hint?: string
    }>(),
    {
        icon: undefined,
        hint: undefined,
    },
)
</script>

<style scoped>
/* EP 变量覆盖：与 PanelCard 一致的 surface 底 + token 阴影外观 */
.data-card {
    --el-card-border-radius: 12px;
    --el-card-border-color: var(--color-border);
    --el-card-bg-color: var(--color-surface);
    --el-card-padding: 14px 16px;

    display: flex;
    width: 100%;
    min-width: 0;
    box-shadow: var(--shadow-sm), var(--shadow-lg);
}

.data-card :deep(.el-card__body) {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    min-width: 0;
}

/* 图标：主题色填充 */
.data-card-icon {
    color: var(--color-primary);
}

/* 标题：小号浅色文字 */
.data-card-title {
    font-size: 12px;
    color: var(--color-text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
}

/* 值：大号深色文字 */
.data-card-value {
    font-size: 18px;
    font-weight: 600;
    color: var(--color-heading);
    font-variant-numeric: tabular-nums;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
}
</style>
