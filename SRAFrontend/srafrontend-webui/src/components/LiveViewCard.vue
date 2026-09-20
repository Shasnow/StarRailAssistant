<template>
  <PanelCard title="实时画面">
    <div class="live-card">
      <!-- 画面区：恒深终端底（terminal-scope 固定深色寄存器），PNG 帧按比例缩放居中展示 -->
      <div class="live-screen terminal-scope">
        <img v-if="frameUrl" :src="frameUrl" alt="实时画面" class="live-img" />
        <div v-else class="live-placeholder">
          <template v-if="viewing">
            <span class="live-spinner" aria-hidden="true" />
            <span>正在获取画面…</span>
          </template>
          <template v-else>实时查看未启动</template>
        </div>

        <!-- LIVE 角标：轮询进行中时显示 -->
        <span v-if="viewing" class="live-badge">
          <span class="badge-dot" aria-hidden="true" />
          LIVE
        </span>
      </div>

      <!-- 拉帧失败提示（保留最后一帧画面） -->
      <div v-if="error" class="live-error" role="alert">{{ error }}</div>

      <!-- 启动/停止实时查看 -->
      <div class="live-controls">
        <el-button type="success" :icon="VideoPlay" :disabled="viewing" @click="start">
          启动实时查看
        </el-button>
        <el-button type="danger" :icon="VideoPause" :disabled="!viewing" @click="stop">
          停止
        </el-button>
      </div>

      <!-- 轮询间隔调整：运行中修改立即按新间隔生效 -->
      <div class="live-settings">
        <span class="live-label">轮询间隔</span>
        <el-select v-model="intervalMs" size="small" class="interval-select">
          <el-option v-for="opt in INTERVAL_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </div>

      <div class="live-meta">
        <template v-if="frameUrl">上次更新 {{ lastUpdated }} · 已接收 {{ frameCount }} 帧</template>
        <template v-else>等待画面数据</template>
      </div>
    </div>
  </PanelCard>
</template>

<script setup lang="ts">
import { VideoPause, VideoPlay } from '@element-plus/icons-vue'
import { useIntervalFn, useLocalStorage } from '@vueuse/core'
import { onScopeDispose, ref, watch } from 'vue'
import { fetchScreenshot } from '@/api/live'
import { formatTime } from '@/api/logs'
import PanelCard from './PanelCard.vue'

/** 可选轮询间隔 */
const INTERVAL_OPTIONS = [
  { label: '0.5 秒', value: 500 },
  { label: '1 秒', value: 1000 },
  { label: '2 秒', value: 2000 },
  { label: '5 秒', value: 5000 },
  { label: '10 秒', value: 10000 },
]

const viewing = ref(false)
/** 当前帧的 Blob URL（空表示尚无画面） */
const frameUrl = ref('')
const error = ref('')
const lastUpdated = ref('')
const frameCount = ref(0)
/** 轮询间隔（毫秒），本地持久化 */
const intervalMs = useLocalStorage('sra_live_interval', 2000)

let controller: AbortController | null = null
/** 上一帧未返回时跳过本轮轮询，避免请求堆积 */
let inFlight = false

const { pause, resume } = useIntervalFn(tick, intervalMs, { immediate: false })

// 间隔变化时重启计时器，立即按新间隔生效
watch(intervalMs, () => {
  if (!viewing.value) return
  pause()
  resume()
})

async function tick() {
  if (inFlight) return
  inFlight = true
  controller = new AbortController()
  try {
    const blob = await fetchScreenshot(controller.signal, Date.now())
    const url = URL.createObjectURL(blob)
    // 释放上一帧的 Blob URL，防止长时间轮询内存泄漏
    URL.revokeObjectURL(frameUrl.value)
    frameUrl.value = url
    lastUpdated.value = formatTime(new Date())
    frameCount.value += 1
    error.value = ''
  } catch (err) {
    // 主动中止（停止 / 卸载）不视为错误
    if (err instanceof DOMException && err.name === 'AbortError') return
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    inFlight = false
  }
}

function start() {
  viewing.value = true
  error.value = ''
  void tick()
  resume()
}

function stop() {
  viewing.value = false
  pause()
  controller?.abort()
  controller = null
}

// 卸载时停止轮询并释放当前帧
onScopeDispose(() => {
  stop()
  URL.revokeObjectURL(frameUrl.value)
})
</script>

<style scoped>
.live-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 画面区：固定 16:9 宽高比，宽度随卡片自适应；terminal-scope 提供恒深底 */
.live-screen {
  position: relative;
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  overflow: hidden;
}

.live-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.live-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  /* 画面区固定深色底，提示文本用固定亮灰（不随主题翻转），保证对比度 */
  color: var(--color-hint-on-dark);
}

.live-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--terminal-border-strong);
  border-top-color: var(--color-success);
  border-radius: 50%;
  animation: live-spin 0.8s linear infinite;
}

@keyframes live-spin {
  to {
    transform: rotate(360deg);
  }
}

/* LIVE 角标 */
.live-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--terminal-bg) 72%, transparent);
  color: var(--color-danger);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-danger);
  animation: live-blink 1s infinite;
}

@keyframes live-blink {
  50% {
    opacity: 0.3;
  }
}

.live-error {
  font-size: 12px;
  color: var(--color-danger);
}

/* 启动/停止：与 ConfigCard 同款栅格，归零 el-button 相邻 margin */
.live-controls {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.live-controls .el-button {
  width: 100%;
  margin: 0;
}

.live-settings {
  display: flex;
  align-items: center;
  gap: 8px;
}

.live-label {
  flex: none;
  font-size: 12px;
  color: var(--color-text);
  opacity: 0.65;
}

.interval-select {
  flex: 1;
}

.live-meta {
  font-size: 11px;
  color: var(--color-text);
  opacity: 0.6;
}
</style>
