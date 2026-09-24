<template>
  <!-- 页面容器：参考主页的卡片布局，左侧日志终端 + 右侧实时画面 -->
  <div class="log-page">
    <div class="log-layout">
      <PanelCard title="系统日志" class="log-panel">
        <!-- 终端外壳：深色区域（工具栏 + 滚动日志区 + 状态栏） -->
        <!-- terminal-scope：恒深终端底 + 语义色深色档寄存器（见 base.css） -->
        <div class="term-shell terminal-scope">
          <!-- 顶部工具栏：连接状态、操作按钮、级别筛选/搜索/字号 -->
          <header class="term-toolbar">
            <div class="bar-row">
              <span class="conn" :class="`conn-${status}`" role="status">
                <span class="conn-dot" />
                {{ statusText }}<span v-if="status === 'reconnecting'">（{{ reconnectAttempt }}/{{ MAX_RECONNECT
                }}）</span>
              </span>

              <div class="bar-actions">
                <el-button size="small" :icon="Refresh" title="重新连接" aria-label="重新连接" @click="refresh" />
                <el-button size="small" :icon="CopyDocument" title="复制当前筛选结果" aria-label="批量复制" @click="copyAll" />
                <el-button size="small" :icon="Download" title="导出为文本文件" aria-label="导出日志" @click="exportLogs" />
                <el-button size="small" :icon="Delete" title="清除日志" aria-label="清除日志" class="clear-btn"
                  @click="clearLogs" />
              </div>
            </div>

            <div class="bar-row">
              <!-- 日志级别筛选：点击切换该级别的显示/隐藏 -->
              <div class="level-chips" role="group" aria-label="日志级别筛选">
                <button v-for="lv in LOG_LEVELS" :key="lv" class="chip"
                  :class="[`chip-${lv.toLowerCase()}`, { active: selectedLevels.has(lv) }]"
                  :aria-pressed="selectedLevels.has(lv)" @click="toggleLevel(lv)">
                  {{ lv }}
                </button>
              </div>

              <el-input v-model="keyword" class="search" size="small" clearable placeholder="搜索日志…"
                :prefix-icon="Search" />

              <div class="font-size" role="group" aria-label="字体大小调整">
                <el-button size="small" title="减小字号" @click="changeFont(-1)">A-</el-button>
                <el-button size="small" title="增大字号" @click="changeFont(1)">A+</el-button>
              </div>
            </div>

            <!-- 断连错误提示（重连次数耗尽等） -->
            <div v-if="status === 'disconnected' && lastError" class="term-alert" role="alert">
              <span class="alert-text">{{ lastError }}</span>
              <el-button size="small" type="warning" plain :icon="Refresh" @click="refresh">重连</el-button>
            </div>
          </header>

          <!-- 日志主体：外层定位容器 + 内层滚动区域；字号由 A-/A+ 控制 -->
          <div class="term-body-wrap">
            <main ref="listEl" class="term-body" :style="{ fontSize: `${fontSize}px` }" @scroll="onScroll">
              <!-- 窗口分页渲染：仅渲染最新 visibleCount 条，向上「加载更早」扩充 -->
              <div class="term-inner">
                <button v-if="hiddenCount > 0" class="load-earlier" @click="loadEarlier">
                  ↑ 加载更早日志（剩余 {{ hiddenCount }} 条）
                </button>

                <div v-for="entry in visibleEntries" :key="entry.id" class="log-line"
                  :class="entry.level.toLowerCase()">
                  <span class="log-time">{{ entry.timestamp }}</span>
                  <span class="log-level">[{{ entry.level }}]</span>
                  <span class="log-msg">
                    <template v-for="(seg, i) in highlightSegments(entry.message)" :key="i">
                      <mark v-if="seg.hit" class="hit">{{ seg.text }}</mark>
                      <template v-else>{{ seg.text }}</template>
                    </template>
                  </span>
                  <!-- 单条复制：悬停行时浮现 -->
                  <button class="log-copy" title="复制该条日志" aria-label="复制该条日志" @click="copyEntry(entry)">
                    <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </svg>
                  </button>
                </div>

                <!-- 空态：区分连接中 / 断开 / 筛选无结果 / 等待推送 -->
                <div v-if="!visibleEntries.length" class="term-empty">
                  <p v-if="status === 'connecting'">正在连接日志服务…</p>
                  <p v-else-if="status === 'reconnecting'">正在重连日志服务…</p>
                  <p v-else-if="status === 'disconnected'">连接已断开，请点击工具栏刷新按钮重连</p>
                  <p v-else-if="entries.length">没有匹配当前筛选条件的日志</p>
                  <p v-else>暂无日志，等待服务推送…</p>
                </div>
              </div>
            </main>

            <!-- 回到底部悬浮按钮：绝对定位悬浮于滚动区右下角，不参与滚动内容布局，
                 避免其出现/消失改变 scrollHeight 导致底部位置跳动 -->
            <transition name="fade">
              <button v-if="!autoScroll && visibleEntries.length" class="jump-bottom" @click="jumpToBottom">
                ↓ 回到底部（自动滚动已暂停）
              </button>
            </transition>
          </div>

          <!-- 底部状态栏 -->
          <footer class="term-status">
            <span>共 {{ entries.length }} 条 · 显示 {{ visibleEntries.length }} 条</span>
            <span class="status-tip">内存 / 本地缓存上限 {{ MAX_LOGS }} 条 · 向上滚动可暂停自动滚动</span>
          </footer>
        </div>
      </PanelCard>

      <!-- 右栏：实时画面（轮询后端截图接口）+ 后端控制 -->
      <aside class="col-right">
        <LiveViewCard class="live-panel" />
        <BackendControlCard />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Delete, Download, Refresh, Search } from '@element-plus/icons-vue'
import { useLocalStorage, refDebounced } from '@vueuse/core'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import type { LogEntry, LogLevel } from '@/api/logs'
import { LOG_LEVELS } from '@/api/logs'
import { MAX_LOGS, MAX_RECONNECT, useLogStream } from '@/composables/useLogStream'
import PanelCard from '@/components/PanelCard.vue'
import LiveViewCard from '@/components/LiveViewCard.vue'
import BackendControlCard from '@/components/BackendControlCard.vue'

/* ---------- 日志流：连接 / 缓存 / 批量刷入 ---------- */
const { entries, status, reconnectAttempt, lastError, refresh, ensureConnected, clear } =
  useLogStream()

const STATUS_TEXT: Record<string, string> = {
  connecting: '连接中',
  connected: '已连接',
  reconnecting: '重连中',
  disconnected: '已断开',
}
const statusText = computed(() => STATUS_TEXT[status.value])

/* ---------- 级别筛选 ---------- */
const selectedLevels = ref<Set<LogLevel>>(new Set(LOG_LEVELS))

function toggleLevel(lv: LogLevel) {
  const next = new Set(selectedLevels.value)
  if (next.has(lv)) next.delete(lv)
  else next.add(lv)
  selectedLevels.value = next
}

/* ---------- 搜索（输入防抖 300ms 后生效）与关键词高亮 ---------- */
const keyword = ref('')
const debouncedKeyword = refDebounced(keyword, 300)

/** 把消息按关键词切分为 {text, hit} 片段，模板中对 hit 片段渲染 <mark> */
function highlightSegments(message: string): Array<{ text: string; hit: boolean }> {
  const kw = debouncedKeyword.value.trim().toLowerCase()
  if (!kw) return [{ text: message, hit: false }]

  const segments: Array<{ text: string; hit: boolean }> = []
  const lower = message.toLowerCase()
  let cursor = 0
  while (cursor <= message.length) {
    const idx = lower.indexOf(kw, cursor)
    if (idx === -1) {
      segments.push({ text: message.slice(cursor), hit: false })
      break
    }
    if (idx > cursor) segments.push({ text: message.slice(cursor, idx), hit: false })
    segments.push({ text: message.slice(idx, idx + kw.length), hit: true })
    cursor = idx + kw.length
  }
  return segments
}

/* ---------- 筛选结果与窗口分页渲染 ----------
   行高随内容换行而变化，基于下标的虚拟列表会导致错位，
   因此采用分页方案：只渲染最新 N 条，向上按需「加载更早」。 */
const PAGE_SIZE = 200
const visibleCount = ref(PAGE_SIZE)

const filtered = computed(() => {
  const kw = debouncedKeyword.value.trim().toLowerCase()
  return entries.value.filter(
    (e) => selectedLevels.value.has(e.level) && (!kw || e.message.toLowerCase().includes(kw)),
  )
})

const visibleEntries = computed(() => filtered.value.slice(Math.max(0, filtered.value.length - visibleCount.value)))
const hiddenCount = computed(() => Math.max(0, filtered.value.length - visibleCount.value))

// 筛选条件变化后重置窗口，避免停留在过大的渲染窗口
watch([selectedLevels, debouncedKeyword], () => {
  visibleCount.value = PAGE_SIZE
})

/** 向上加载更早日志：渲染后补偿滚动高度，保持视口停留在原内容处 */
async function loadEarlier() {
  const el = listEl.value
  const prevHeight = el?.scrollHeight ?? 0
  visibleCount.value += PAGE_SIZE
  await nextTick()
  if (el) el.scrollTop += el.scrollHeight - prevHeight
}

/* ---------- 自动滚动：向上滚动暂停，回到底部恢复 ---------- */
const listEl = ref<HTMLElement>()
const autoScroll = ref(true)

watch(visibleEntries, () => {
  if (autoScroll.value) void scrollToBottom()
})

/** 瞬时定位到底部：不用平滑滚动，避免滚动途中 scroll 事件的中间位置翻转 autoScroll 状态 */
async function scrollToBottom() {
  await nextTick()
  const el = listEl.value
  if (el) el.scrollTop = el.scrollHeight
}

function onScroll() {
  const el = listEl.value
  if (!el) return
  const gap = el.scrollHeight - el.scrollTop - el.clientHeight
  // 阈值收紧：离开底部（>8px）立即暂停自动滚动，回到底部（≤8px）恢复，
  // 消除「拖动上移一行后仍被视为在底部、又被强制拉回」的拉锯现象
  if (gap > 8) autoScroll.value = false
  else autoScroll.value = true
}

function jumpToBottom() {
  autoScroll.value = true
  void scrollToBottom()
}

/* ---------- 复制：单条 / 批量（当前筛选结果） ---------- */
function formatLine(entry: LogEntry): string {
  return `[${entry.timestamp}] [${entry.level}] ${entry.message}`
}

/** 剪贴板写入：clipboard API 优先，失败时降级 execCommand（旧浏览器 / 非安全上下文） */
async function writeClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      ta.remove()
      return ok
    } catch {
      return false
    }
  }
}

async function copyEntry(entry: LogEntry) {
  const ok = await writeClipboard(formatLine(entry))
  if (ok) ElMessage.success('已复制到剪贴板')
  else ElMessage.error('复制失败')
}

async function copyAll() {
  if (!filtered.value.length) {
    ElMessage.warning('当前筛选条件下没有可复制的日志')
    return
  }
  const ok = await writeClipboard(filtered.value.map(formatLine).join('\n'))
  if (ok) ElMessage.success(`已复制 ${filtered.value.length} 条日志`)
  else ElMessage.error('复制失败')
}

/* ---------- 导出：当前筛选结果下载为 .log 文本文件 ---------- */
function exportLogs() {
  if (!filtered.value.length) {
    ElMessage.warning('当前筛选条件下没有可导出的日志')
    return
  }
  const text = filtered.value.map(formatLine).join('\n')
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `sra-logs-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.log`
  a.click()
  // 释放 Blob URL，避免内存泄漏
  URL.revokeObjectURL(url)
  ElMessage.success(`已导出 ${filtered.value.length} 条日志`)
}

/* ---------- 清除：确认后清空内存与本地缓存（连接保持） ---------- */
async function clearLogs() {
  try {
    await ElMessageBox.confirm('将清空当前日志与本地缓存，确定继续？', '清除日志', {
      confirmButtonText: '清除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  clear()
  ElMessage.success('日志已清除')
}

/* ---------- 字号调整（12-18px，localStorage 持久化） ---------- */
const fontSize = useLocalStorage('sra_log_font_size', 13)

function changeFont(delta: number) {
  fontSize.value = Math.min(18, Math.max(12, fontSize.value + delta))
}

onMounted(() => {
  // 连接为全局单例：已开着就不动（切回页面不强制重连），仅在真正未连接时建连
  ensureConnected()
  // 初始定位到最新日志：缓存恢复发生在首次渲染前，visibleEntries 的 watch（非 immediate）
  // 不会触发，切页返回 / 刷新后滚动条会停留在顶部，这里主动定位一次
  void scrollToBottom()
})
</script>

<style scoped>
/* ---------- 页面容器：与主页一致的卡片布局 ---------- */
.log-page {
  /* 终端/画面区统一高度变量：随视口缩放并保证最小可用高度 */
  --term-h: clamp(420px, calc(100vh - 300px), 900px);
  max-width: 1400px;
  margin: 0 auto;
  /* 顶部留白避开全局导航 */
  padding: 32px 24px 48px;
}

/* 左日志 + 右实时画面双栏；窄屏折叠为单列 */
.log-layout {
  display: flex;
  align-items: stretch;
  gap: 20px;
}

.log-panel {
  flex: 1;
  min-width: 0;
}

/* 右栏：实时画面 + 后端控制，纵向排布（对齐主页 .col 栅格） */
.col-right {
  flex: none;
  width: 320px;
  display: grid;
  gap: 20px;
  align-content: start;
  min-width: 0;
}

@media (max-width: 1199px) {
  .log-layout {
    flex-direction: column;
  }

  .col-right {
    width: auto;
  }
}

@media (max-width: 767px) {
  .log-page {
    --term-h: clamp(380px, calc(100vh - 260px), 900px);
    padding: 72px 16px 32px;
  }
}

/* ---------- 终端外壳：深色区域嵌在卡片内，工具栏/日志区/状态栏纵向排布 ---------- */
/* terminal-scope 提供恒深底与语义色深色档（base.css） */
.term-shell {
  display: flex;
  flex-direction: column;
  /* 卡片内固定高度，日志区内部滚动 */
  height: var(--term-h);
  border: 1px solid var(--terminal-border);
  border-radius: 10px;
  overflow: hidden;
  /* 等宽栈不含中文字形，末尾补上页面同款中文字体（须在 monospace 之前），
     避免中文回退到浏览器默认等宽字体（Windows 上为宋体） */
  font-family:
    ui-monospace,
    'Cascadia Code',
    'Source Code Pro',
    Menlo,
    Consolas,
    'Courier New',
    'PingFang SC',
    'Microsoft YaHei',
    'Noto Sans CJK SC',
    monospace;
}

/* ---------- 终端内工具栏 ---------- */
.term-toolbar {
  flex: none;
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  background: var(--terminal-surface);
  border-bottom: 1px solid var(--terminal-border);
}

.bar-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

/* 连接状态靠左，操作按钮靠右 */
.conn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-right: auto;
  font-size: 12px;
}

.conn-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-muted);
}

.conn-connected {
  color: var(--color-success);
}

.conn-connected .conn-dot {
  background: var(--color-success);
  box-shadow: 0 0 6px color-mix(in srgb, var(--color-success) 70%, transparent);
}

.conn-connecting,
.conn-reconnecting {
  color: var(--color-warning);
}

.conn-connecting .conn-dot,
.conn-reconnecting .conn-dot {
  background: var(--color-warning);
  animation: blink 1s infinite;
}

.conn-disconnected {
  color: var(--color-danger);
}

.conn-disconnected .conn-dot {
  background: var(--color-danger);
}

@keyframes blink {
  50% {
    opacity: 0.3;
  }
}

.bar-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 深色工具栏上的 Element Plus 按钮定制：深灰底 + 浅色文字，悬停半透明蓝底蓝描边 */
.bar-actions :deep(.el-button),
.font-size :deep(.el-button) {
  --el-button-bg-color: var(--terminal-btn-bg);
  --el-button-border-color: var(--terminal-btn-border);
  --el-button-text-color: var(--terminal-btn-text);
  --el-button-hover-bg-color: color-mix(in oklab, var(--color-info) 14%, transparent);
  --el-button-hover-border-color: color-mix(in oklab, var(--color-info) 60%, transparent);
  --el-button-hover-text-color: var(--color-info);
  --el-button-active-bg-color: color-mix(in oklab, var(--color-info) 22%, transparent);
  --el-button-active-border-color: color-mix(in oklab, var(--color-info) 70%, transparent);
  --el-button-active-text-color: var(--color-info);
  --el-button-disabled-bg-color: var(--terminal-btn-disabled-bg);
  --el-button-disabled-border-color: var(--terminal-btn-disabled-border);
  --el-button-disabled-text-color: var(--terminal-btn-disabled-text);
}

/* 清除按钮悬停转为红色警示 */
.bar-actions :deep(.el-button.clear-btn:hover) {
  --el-button-hover-text-color: var(--color-danger);
  --el-button-hover-border-color: color-mix(in oklab, var(--color-danger) 50%, transparent);
  --el-button-hover-bg-color: color-mix(in oklab, var(--color-danger) 12%, transparent);
}

/* ---------- 级别筛选 chips ---------- */
.level-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  font-family: inherit;
  font-size: 11px;
  padding: 2px 10px;
  border: 1px solid var(--terminal-border-strong);
  border-radius: 4px;
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  transition:
    color 0.15s,
    border-color 0.15s,
    background-color 0.15s;
}

/* 每个级别提供自己的主题色变量 */
.chip-error {
  --lv: var(--color-danger);
}

.chip-warn {
  --lv: var(--color-warning);
}

.chip-info {
  --lv: var(--color-success);
}

.chip-debug {
  --lv: var(--color-info);
}

.chip:hover {
  color: var(--lv);
}

.chip.active {
  color: var(--lv);
  border-color: var(--lv);
  background: color-mix(in srgb, var(--lv) 12%, transparent);
}

/* ---------- 搜索框（深色定制） ---------- */
.search {
  width: 220px;
}

.search :deep(.el-input__wrapper) {
  background: var(--terminal-deep);
  box-shadow: 0 0 0 1px var(--terminal-border-strong) inset;
}

.search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--color-success) inset;
}

.search :deep(.el-input__inner) {
  color: var(--terminal-text);
  font-family: inherit;
}

.search :deep(.el-input__inner::placeholder) {
  color: var(--color-muted);
}

/* ---------- 日志主体 ---------- */
/* 外层定位容器：为悬浮按钮提供定位上下文，自身不滚动 */
.term-body-wrap {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
}

.term-body {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  background: var(--terminal-bg);
  /* 底部预留约两行空间（随字号缩放），末行不贴底 */
  padding: 8px 0 3em;
  scrollbar-width: thin;
  scrollbar-color: var(--terminal-scrollbar) transparent;
}

.term-body::-webkit-scrollbar {
  width: 10px;
}

.term-body::-webkit-scrollbar-thumb {
  background: var(--terminal-scrollbar);
  border-radius: 5px;
}

.term-body::-webkit-scrollbar-thumb:hover {
  background: var(--terminal-scrollbar-hover);
}

.term-inner {
  padding: 0 16px;
}

.log-line {
  position: relative;
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 2px 28px 2px 0;
  line-height: 1.5;
}

.log-line:hover {
  background: var(--terminal-hover);
}

.log-time {
  flex: none;
  color: var(--terminal-time);
}

.log-level {
  flex: none;
  font-weight: 600;
}

/* 消息体自动换行，长词断行，保证完整显示 */
.log-msg {
  min-width: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 级别差异化配色：整行文字按级别着色（terminal-scope 内为深色档） */
.log-line.error .log-level {
  color: var(--color-danger);
}

.log-line.error .log-msg {
  color: color-mix(in oklab, var(--color-danger) 85%, white);
}

.log-line.warn .log-level {
  color: var(--color-warning);
}

.log-line.warn .log-msg {
  color: color-mix(in oklab, var(--color-warning) 85%, white);
}

.log-line.info .log-level {
  color: var(--color-success);
}

.log-line.info .log-msg {
  color: var(--terminal-text-2);
}

.log-line.debug .log-level {
  color: var(--color-info);
}

.log-line.debug .log-msg {
  color: color-mix(in oklab, var(--terminal-text) 70%, var(--terminal-bg));
}

/* 搜索命中高亮 */
.hit {
  background: var(--terminal-hl-bg);
  color: var(--terminal-hl-text);
  padding: 0 1px;
  border-radius: 2px;
}

/* 单条复制按钮：悬停行时浮现 */
.log-copy {
  position: absolute;
  right: 4px;
  top: 4px;
  display: flex;
  align-items: center;
  padding: 3px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  opacity: 0;
  transition:
    opacity 0.15s,
    color 0.15s;
}

.log-line:hover .log-copy {
  opacity: 1;
}

.log-copy:hover {
  color: var(--terminal-text);
  background: var(--terminal-hover-strong);
}

/* 加载更早按钮 */
.load-earlier {
  display: block;
  width: 100%;
  margin: 4px 0 8px;
  padding: 6px;
  border: 1px dashed var(--terminal-border-strong);
  border-radius: 6px;
  background: transparent;
  color: var(--color-muted);
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  transition:
    color 0.15s,
    border-color 0.15s;
}

.load-earlier:hover {
  color: var(--color-success);
  border-color: var(--color-success);
}

/* 回到底部悬浮按钮：绝对定位悬浮于滚动区右下角，脱离滚动内容流，
   其出现/消失不影响 scrollHeight，避免底部位置跳动 */
.jump-bottom {
  position: absolute;
  bottom: 12px;
  right: 16px;
  z-index: 1;
  padding: 6px 14px;
  border: 1px solid var(--color-success);
  border-radius: 16px;
  background: var(--terminal-surface);
  color: var(--color-success);
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgb(0 0 0 / 40%);
  transition:
    background-color 0.15s,
    color 0.15s;
}

.jump-bottom:hover {
  background: var(--color-success);
  color: var(--terminal-bg);
}

/* 空态提示 */
.term-empty {
  padding: 48px 16px;
  text-align: center;
  color: var(--color-muted);
  font-size: 13px;
}

/* 断连错误横幅 */
.term-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 10px;
  border: 1px solid color-mix(in oklab, var(--color-danger) 40%, transparent);
  border-radius: 6px;
  background: color-mix(in oklab, var(--color-danger) 10%, transparent);
  color: color-mix(in oklab, var(--color-danger) 85%, white);
  font-size: 12px;
}

.alert-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---------- 底部状态栏 ---------- */
.term-status {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 4px 16px;
  padding: 6px 16px;
  background: var(--terminal-surface);
  border-top: 1px solid var(--terminal-border);
  color: var(--color-muted);
  font-size: 11px;
}

.status-tip {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 过渡：回到底部按钮 */
.fade-enter-active,
.fade-leave-active {
  transition:
    opacity 0.2s,
    transform 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

/* ---------- 响应式：窄屏收紧间距与搜索宽度 ---------- */
@media (max-width: 767px) {
  .term-toolbar {
    padding: 8px 10px;
  }

  .search {
    width: 100%;
    flex: 1;
  }

  .term-inner {
    padding: 0 10px;
  }
}
</style>
