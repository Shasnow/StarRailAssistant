<template>
  <PanelCard title="运行状态">
    <div class="status-grid">
      <div v-for="item in infoRows" :key="item.label" class="row">
        <span class="row-label">{{ item.label }}</span>
        <!-- 状态行用色彩编码 pill 展示，其余行展示文本值 -->
        <span v-if="item.pill" class="pill" :class="`pill-${stateMeta[status.status].pill}`">
          {{ stateMeta[status.status].label }}
        </span>
        <span v-else class="row-value" :class="{ mono: item.mono }" :title="item.value">
          {{ item.value }}
        </span>
      </div>

      <!-- 进度：百分比数值 + 进度条（progress 为后端 [current, total] 元组） -->
      <div class="progress">
        <div class="row">
          <span class="row-label">进度</span>
          <span class="progress-num">{{ Math.round(progressPercent) }}%</span>
        </div>
        <div class="progress-track" role="progressbar" :aria-valuenow="Math.round(progressPercent)" aria-valuemin="0"
          aria-valuemax="100">
          <div class="progress-fill" :class="`fill-${stateMeta[status.status].pill}`"
            :style="{ width: `${progressPercent}%` }"></div>
        </div>
      </div>
    </div>
  </PanelCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TaskStatus } from '@/api/task'
import PanelCard from './PanelCard.vue'

// 运行状态：字段与后端 RuntimeInfo 一致，由任务轮询驱动
const props = defineProps<{
  status: TaskStatus
}>()

// 状态展示：label 精确到后端 5 种 RunStatus；
// pill/进度条沿用三色编码（running-绿、failed-红、其余-灰）
const stateMeta: Record<TaskStatus['status'], { label: string; pill: 'running' | 'stopped' | 'error' }> = {
  idle: { label: '空闲', pill: 'stopped' },
  running: { label: '运行中', pill: 'running' },
  completed: { label: '已完成', pill: 'stopped' },
  failed: { label: '失败', pill: 'error' },
  stopped: { label: '已停止', pill: 'stopped' },
}

const infoRows = computed(() => [
  { label: '会话 ID', value: props.status.session_id || '—', mono: true },
  { label: '进程 PID', value: props.status.pid > 0 ? String(props.status.pid) : '—', mono: true },
  { label: '运行模式', value: props.status.mode || '—' },
  { label: '当前状态', pill: true },
  { label: '运行单元', value: props.status.unit || '—' },
  { label: '运行配置', value: props.status.configs.join('、') || '—' },
])

/** [current, total] 换算为 0-100 百分比；total 为 0 视为无进度 */
const progressPercent = computed(() => {
  const [current, total] = props.status.progress
  return total > 0 ? Math.min(100, Math.max(0, (current / total) * 100)) : 0
})
</script>

<style scoped>
.status-grid {
  display: grid;
  gap: 11px;
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.row-label {
  font-size: 13px;
  color: var(--color-text);
  opacity: 0.68;
  flex: none;
}

.row-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-heading);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-value.mono {
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 12px;
}

/* 状态 pill：--pill-c 驱动文字/圆点/底色，深色模式下用更亮的色阶 */
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: var(--pill-c);
  background: color-mix(in srgb, var(--pill-c) 13%, transparent);
  flex: none;
}

.pill::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--pill-c);
}

.pill-running {
  --pill-c: var(--color-success);
}

.pill-stopped {
  --pill-c: var(--color-muted);
}

.pill-error {
  --pill-c: var(--color-danger);
}

.progress {
  display: grid;
  gap: 6px;
}

.progress-num {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-heading);
  font-variant-numeric: tabular-nums;
}

.progress-track {
  height: 8px;
  border-radius: 999px;
  background: var(--color-background-mute);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--bar-c);
  transition: width 0.35s ease;
}

.fill-running {
  --bar-c: var(--color-success);
}

.fill-stopped {
  --bar-c: var(--color-muted);
}

.fill-error {
  --bar-c: var(--color-danger);
}
</style>
