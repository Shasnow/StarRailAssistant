<template>
  <PanelCard :title="t('live.title')">
    <div class="live-card">
      <!-- 画面区：恒深终端底（terminal-scope 固定深色寄存器），PNG 帧按比例缩放居中展示 -->
      <div
        v-if="viewing"
        ref="screenEl"
        class="live-screen terminal-scope"
        :class="{ 'input-active': inputMode, 'input-ready': canInput }"
        tabindex="0"
        @pointerdown.prevent="onPointerDown"
        @pointermove="onPointerMove"
        @wheel.prevent="onWheel"
        @contextmenu.prevent
      >
        <img v-if="frameUrl" ref="imageEl" :src="frameUrl" :alt="t('live.title')" class="live-img" />
        <div v-else class="live-placeholder">
          <span class="live-spinner" aria-hidden="true" />
          <span>{{ t('live.fetching') }}</span>
        </div>

        <!-- LIVE 角标：轮询进行中时显示 -->
        <span v-if="viewing" class="live-badge">
          <span class="badge-dot" aria-hidden="true" />
          LIVE
        </span>

        <!-- 输入模式角标与退出入口 -->
        <span v-if="inputMode" class="live-input-badge">
          <span class="input-dot" aria-hidden="true" />
          {{ t('live.inputActive') }}
        </span>
        <button
          v-if="inputMode"
          type="button"
          class="live-input-exit"
          @pointerdown.stop
          @click="exitInputMode"
        >
          {{ t('live.inputExit') }}
        </button>
      </div>

      <!-- 输入模式提示：放在画面外，始终显示 -->
      <p class="live-input-hint">{{ t('live.inputHint') }}</p>

      <!-- 游戏窗口不在前台：暂停发送并允许用户主动激活 -->
      <div v-if="inputMode && !windowActive" class="live-input-warn" role="alert">
        <span class="warn-text">{{ t('live.inputWindowInactive') }}</span>
        <el-button size="small" type="warning" plain :loading="activating" @click="onActivateWindow">
          {{ t('live.inputActivateWindow') }}
        </el-button>
      </div>

      <!-- 输入发送失败提示 -->
      <div v-if="inputError" class="live-error" role="alert">{{ inputError }}</div>

      <!-- 拉帧失败提示（保留最后一帧画面） -->
      <div v-if="error" class="live-error" role="alert">{{ error }}</div>

      <!-- 启动/停止实时查看 -->
      <div class="live-controls">
        <el-button type="success" :icon="VideoPlay" :disabled="viewing" @click="start">
          {{ t('live.start') }}
        </el-button>
        <el-button type="danger" :icon="VideoPause" :disabled="!viewing" @click="stop">
          {{ t('backend.stop') }}
        </el-button>
      </div>

      <!-- 轮询间隔调整：运行中修改立即按新间隔生效 -->
      <div class="live-settings">
        <span class="live-label">{{ t('live.interval') }}</span>
        <el-select v-model="intervalMs" size="small" class="interval-select">
          <el-option v-for="opt in INTERVAL_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </div>

      <div class="live-meta">
        <template v-if="frameUrl">{{ t('live.lastUpdated') }} {{ lastUpdated }} {{ t('live.receivedSuffix') }} {{ frameCount }} {{ t('live.framesUnit') }}</template>
        <template v-else>{{ t('live.waiting') }}</template>
      </div>

      <!-- 手动输入的前提说明 -->
      <div v-if="inputMode" class="live-meta live-input-tip">{{ t('live.inputFocusHint') }}</div>
    </div>
  </PanelCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import { VideoPause, VideoPlay } from '@element-plus/icons-vue'
import { useIntervalFn, useLocalStorage } from '@vueuse/core'
import { ElMessage } from 'element-plus'
import { computed, onScopeDispose, ref, watch } from 'vue'
import { fetchScreenshot } from '@/api/live'
import { formatTime } from '@/api/logs'
import {
  activateGameWindow,
  isGameWindowActive,
  sendInputEvent,
  type InputEvent,
  type MouseButtonName,
} from '@/api/operator'
import { mapKeyEvent, mapMouseButton, toRelativePoint, wheelToClicks } from '@/utils/liveInput'
import PanelCard from './PanelCard.vue'

const { t } = useI18n()

/** 演示模式没有真实后端，禁用手动输入 */
const isDemo = __IS_DEMO__

/** 可选轮询间隔 */
const INTERVAL_OPTIONS = [
  { label: t('live.intervalHalfSecond'), value: 500 },
  { label: t('live.interval1s'), value: 1000 },
  { label: t('live.interval2s'), value: 2000 },
  { label: t('live.interval5s'), value: 5000 },
  { label: t('live.interval10s'), value: 10000 },
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
  exitInputMode()
  viewing.value = false
  pause()
  controller?.abort()
  controller = null
}

/* ---------- 手动输入模式 ----------
   点击画面进入输入模式：鼠标/键盘事件转换成 /api/operator/call 调用。
   输入必须串行发送（down → move* → up），移动事件 50ms 合并以降低请求量。 */

const MOVE_FLUSH_MS = 50
/** 前台检测间隔：仅当游戏窗口在前台时才发送键盘/鼠标按下 */
const ACTIVE_POLL_MS = 1000

const screenEl = ref<HTMLElement>()
const imageEl = ref<HTMLImageElement>()
const inputMode = ref(false)
const windowActive = ref(true)
const inputError = ref('')
const activating = ref(false)

/** 有画面且非演示模式时才允许进入输入模式 */
const canInput = computed(() => !isDemo && viewing.value && !!frameUrl.value)

const heldKeys = new Set<string>()
const heldButtons = new Set<MouseButtonName>()
let queue: InputEvent[] = []
let pendingMove: { x: number; y: number } | null = null
let sending = false
let moveTimer: number | undefined
let activeTimer: number | undefined

/** 按 object-fit: contain 反算画面内相对坐标（0–1） */
function pointerToRelative(event: PointerEvent | WheelEvent): { x: number; y: number } | null {
  const el = screenEl.value
  if (!el) return null
  const img = imageEl.value
  const natural =
    img && img.naturalWidth > 0 && img.naturalHeight > 0
      ? { width: img.naturalWidth, height: img.naturalHeight }
      : { width: 1280, height: 720 }
  return toRelativePoint(el.getBoundingClientRect(), natural, event.clientX, event.clientY)
}

/** 串行发送队列：一次只发一个事件，保证 down → move → up 的顺序 */
async function pump() {
  if (sending) return
  sending = true
  try {
    for (;;) {
      let event = queue.shift()
      if (!event && pendingMove) {
        event = { type: 'move', x: pendingMove.x, y: pendingMove.y }
        pendingMove = null
      }
      if (!event) break
      try {
        await sendInputEvent(event)
        inputError.value = ''
      } catch (err) {
        inputError.value = t('live.inputSendFailed', [
          err instanceof Error ? err.message : String(err),
        ])
        // 失败时清空后续操作并释放已按下的键/鼠标，避免游戏内卡住输入
        queue = []
        pendingMove = null
        releaseHeld()
        break
      }
    }
  } finally {
    sending = false
    if (queue.length) void pump()
  }
}

/** 离散事件立即入队；窗口不在前台时只放行「释放」类事件 */
function enqueueDiscrete(event: InputEvent) {
  const isRelease = event.type === 'up' || event.type === 'key_up'
  if (!windowActive.value && !isRelease) return
  queue.push(event)
  void pump()
}

function scheduleMove() {
  if (moveTimer !== undefined) return
  moveTimer = window.setTimeout(() => {
    moveTimer = undefined
    if (!pendingMove) return
    if (sending) {
      scheduleMove()
      return
    }
    queue.push({ type: 'move', x: pendingMove.x, y: pendingMove.y })
    pendingMove = null
    void pump()
  }, MOVE_FLUSH_MS)
}

/** 把尚未发出的移动位置并入队列（滚轮前需要先定位） */
function flushPendingMove() {
  if (!pendingMove) return
  if (moveTimer !== undefined) {
    clearTimeout(moveTimer)
    moveTimer = undefined
  }
  queue.push({ type: 'move', x: pendingMove.x, y: pendingMove.y })
  pendingMove = null
}

function releaseHeld() {
  for (const button of heldButtons) queue.push({ type: 'up', button })
  for (const key of heldKeys) queue.push({ type: 'key_up', key })
  heldButtons.clear()
  heldKeys.clear()
  if (queue.length) void pump()
}

async function refreshWindowActive() {
  try {
    windowActive.value = await isGameWindowActive()
  } catch {
    // 检测失败不阻断输入，真正的失败会在发送事件时提示
  }
}

function onPointerDown(event: PointerEvent) {
  if (!inputMode.value) {
    enterInputMode()
    return
  }
  if (!windowActive.value) return
  const point = pointerToRelative(event)
  if (!point) return
  const button = mapMouseButton(event.button)
  if (!button) return
  heldButtons.add(button)
  enqueueDiscrete({ type: 'down', x: point.x, y: point.y, button })
}

function onPointerMove(event: PointerEvent) {
  if (!inputMode.value || !windowActive.value) return
  const point = pointerToRelative(event)
  if (!point) return
  pendingMove = point
  scheduleMove()
}

function onWheel(event: WheelEvent) {
  if (!inputMode.value || !windowActive.value) return
  const point = pointerToRelative(event)
  if (point) pendingMove = point
  const clicks = wheelToClicks(event.deltaY, event.deltaMode)
  if (!clicks) return
  flushPendingMove()
  enqueueDiscrete({ type: 'wheel', clicks })
}

function onPointerUp(event: PointerEvent) {
  if (!inputMode.value) return
  const button = mapMouseButton(event.button)
  if (!button || !heldButtons.delete(button)) return
  queue.push({ type: 'up', button })
  void pump()
}

function onKeyDown(event: KeyboardEvent) {
  if (!inputMode.value) return
  if (event.repeat) {
    event.preventDefault()
    return
  }
  const key = mapKeyEvent(event)
  if (!key) return
  event.preventDefault()
  if (!windowActive.value || heldKeys.has(key)) return
  heldKeys.add(key)
  enqueueDiscrete({ type: 'key_down', key })
}

function onKeyUp(event: KeyboardEvent) {
  if (!inputMode.value) return
  const key = mapKeyEvent(event)
  if (!key) return
  event.preventDefault()
  if (!heldKeys.delete(key)) return
  queue.push({ type: 'key_up', key })
  void pump()
}

function onWindowBlur() {
  if (inputMode.value) exitInputMode()
}

function onVisibilityChange() {
  if (document.hidden && inputMode.value) exitInputMode()
}

function attachInputListeners() {
  window.addEventListener('pointerup', onPointerUp, true)
  window.addEventListener('pointercancel', onPointerUp, true)
  window.addEventListener('keydown', onKeyDown, true)
  window.addEventListener('keyup', onKeyUp, true)
  window.addEventListener('blur', onWindowBlur)
  document.addEventListener('visibilitychange', onVisibilityChange)
}

function detachInputListeners() {
  window.removeEventListener('pointerup', onPointerUp, true)
  window.removeEventListener('pointercancel', onPointerUp, true)
  window.removeEventListener('keydown', onKeyDown, true)
  window.removeEventListener('keyup', onKeyUp, true)
  window.removeEventListener('blur', onWindowBlur)
  document.removeEventListener('visibilitychange', onVisibilityChange)
}

function enterInputMode() {
  if (inputMode.value) return
  if (isDemo) {
    ElMessage.warning(t('live.inputDemoUnsupported'))
    return
  }
  if (!canInput.value) {
    ElMessage.warning(t('live.inputNeedLive'))
    return
  }
  inputMode.value = true
  inputError.value = ''
  windowActive.value = true
  attachInputListeners()
  screenEl.value?.focus()
  void refreshWindowActive()
  activeTimer = window.setInterval(() => void refreshWindowActive(), ACTIVE_POLL_MS)
}

function exitInputMode() {
  if (!inputMode.value) return
  inputMode.value = false
  detachInputListeners()
  if (activeTimer !== undefined) {
    clearInterval(activeTimer)
    activeTimer = undefined
  }
  if (moveTimer !== undefined) {
    clearTimeout(moveTimer)
    moveTimer = undefined
  }
  pendingMove = null
  queue = []
  releaseHeld()
}

async function onActivateWindow() {
  activating.value = true
  try {
    await activateGameWindow()
    await refreshWindowActive()
  } catch (err) {
    inputError.value = t('live.inputSendFailed', [
      err instanceof Error ? err.message : String(err),
    ])
  } finally {
    activating.value = false
  }
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
  user-select: none;
}

/* 有画面时提示可点击进入输入模式 */
.live-screen.input-ready {
  cursor: pointer;
}

.live-screen.input-active {
  border-color: var(--color-success);
  cursor: crosshair;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-success) 45%, transparent);
}

.live-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  /* 拖动画面时避免浏览器原生图片拖拽 */
  pointer-events: none;
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

/* 输入模式角标：放在 LIVE 右侧 */
.live-input-badge {
  position: absolute;
  top: 8px;
  left: 60px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--terminal-bg) 72%, transparent);
  color: var(--color-success);
  font-size: 10px;
  font-weight: 700;
}

.input-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-success);
  animation: live-blink 1s infinite;
}

/* 退出输入：右上角悬浮按钮 */
.live-input-exit {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 3px 10px;
  border: 1px solid color-mix(in srgb, var(--color-success) 55%, transparent);
  border-radius: 10px;
  background: color-mix(in srgb, var(--terminal-bg) 78%, transparent);
  color: var(--color-success);
  font-size: 11px;
  cursor: pointer;
}

.live-input-exit:hover {
  background: var(--color-success);
  color: var(--terminal-bg);
}

/* 输入模式提示：位于画面外，始终显示 */
.live-input-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-text);
  opacity: 0.68;
}

.live-input-warn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid color-mix(in srgb, var(--color-warning) 45%, transparent);
  border-radius: 6px;
  background: color-mix(in srgb, var(--color-warning) 12%, transparent);
  font-size: 11px;
}

.warn-text {
  min-width: 0;
  color: var(--color-warning);
}

.live-error {
  font-size: 12px;
  color: var(--color-danger);
}

.live-input-tip {
  line-height: 1.5;
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
