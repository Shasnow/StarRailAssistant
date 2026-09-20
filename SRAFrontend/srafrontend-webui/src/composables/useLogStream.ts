import { useDebounceFn } from '@vueuse/core'
import { onScopeDispose, ref } from 'vue'
import { getStoredToken } from '@/api/http'
import { LOG_STREAM_URL, parseLogPayload } from '@/api/logs'
import type { LogEntry } from '@/api/logs'

/** 连接状态：连接中 / 已连接 / 重连中 / 已断开 */
export type StreamStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected'

/** 内存与本地缓存的上限：超出后丢弃最旧日志，防止长驻页面内存无限增长 */
export const MAX_LOGS = 1000

/** SSE 消息先入队，按固定间隔批量刷入响应式列表 —— 合并高频推送，降低 DOM 更新频率 */
const FLUSH_INTERVAL = 200

/** 断线重连策略：最多尝试次数，指数退避（1s → 2s → 4s → 8s 封顶） */
export const MAX_RECONNECT = 5
const BASE_RETRY_DELAY = 1000

/** 连接建立超时：EventSource 在响应头到达前不触发任何事件（如后端 SSE 未 Flush 头），
 * 超时后按失败处理进入重连，避免状态永远停留在「连接中」 */
const CONNECT_TIMEOUT = 10_000

/** 本地缓存键：页面刷新后恢复最近日志 */
const CACHE_KEY = 'sra_log_buffer_v1'

/** localStorage 中的精简条目结构（省略 id，减小体积） */
type CachedEntry = { t: string; l: LogEntry['level']; m: string }

/**
 * 日志实时流组合式函数：
 * - EventSource 建立与 /api/logs/stream 的 SSE 连接，断线指数退避自动重连（限次数）
 * - 高频消息先入 pending 队列，定时批量刷入 entries，避免逐条触发响应式更新
 * - 最近 MAX_LOGS 条日志防抖持久化到 localStorage，页面刷新后自动恢复
 */
export function useLogStream() {
  const entries = ref<LogEntry[]>([])
  const status = ref<StreamStatus>('disconnected')
  /** 当前重连尝试次数（0 表示不在重连流程中），用于状态栏展示进度 */
  const reconnectAttempt = ref(0)
  /** 最近一次致命错误（重连次数耗尽等），供界面提示 */
  const lastError = ref('')

  let source: EventSource | null = null
  let flushTimer: ReturnType<typeof setInterval> | undefined
  let retryTimer: ReturnType<typeof setTimeout> | undefined
  let openTimer: ReturnType<typeof setTimeout> | undefined
  let pending: Array<Omit<LogEntry, 'id'>> = []
  let reconnectAttempts = 0
  let nextId = 1
  /** 用户主动断开标记：与网络错误导致的断开区分，后者才触发重连 */
  let closedByUser = false

  restoreCache()

  /** 页面加载时从 localStorage 恢复最近日志（缓存损坏时静默忽略，从空白开始） */
  function restoreCache() {
    try {
      const raw = localStorage.getItem(CACHE_KEY)
      if (!raw) return
      const cached = JSON.parse(raw) as CachedEntry[]
      if (!Array.isArray(cached)) return
      entries.value = cached
        .filter((it) => it && typeof it.m === 'string')
        .slice(-MAX_LOGS)
        .map((it) => ({ id: nextId++, level: it.l, message: it.m, timestamp: it.t }))
    } catch {
      /* ignore */
    }
  }

  /** 缓存写盘去抖：连续批量刷入期间只落一次 localStorage */
  const persistCache = useDebounceFn(() => {
    try {
      const payload: CachedEntry[] = entries.value.map((e) => ({
        t: e.timestamp,
        l: e.level,
        m: e.message,
      }))
      localStorage.setItem(CACHE_KEY, JSON.stringify(payload))
    } catch {
      /* 存储不可用（隐私模式 / 配额满）时静默失败 */
    }
  }, 800)

  /** 批量刷入：整批追加并截断到上限，整体替换数组以保持响应式引用可追踪 */
  function flush() {
    if (!pending.length) return
    const batch = pending
    pending = []
    entries.value = [...entries.value, ...batch.map((it) => ({ ...it, id: nextId++ }))].slice(
      -MAX_LOGS,
    )
    persistCache()
  }

  function ensureFlushTimer() {
    if (flushTimer) return
    flushTimer = setInterval(flush, FLUSH_INTERVAL)
  }

  function stopFlushTimer() {
    if (flushTimer) {
      clearInterval(flushTimer)
      flushTimer = undefined
    }
    // 断开前把队列中残余日志刷入，避免丢尾
    flush()
  }

  /** 重连耗尽后的终态：停止重试，交由用户手动重连 */
  function scheduleReconnect() {
    if (reconnectAttempts >= MAX_RECONNECT) {
      status.value = 'disconnected'
      lastError.value = `连接已断开：连续 ${MAX_RECONNECT} 次重连失败，请检查后端服务后手动重连`
      return
    }
    reconnectAttempts += 1
    reconnectAttempt.value = reconnectAttempts
    status.value = 'reconnecting'
    const delay = Math.min(BASE_RETRY_DELAY * 2 ** (reconnectAttempts - 1), 8000)
    retryTimer = setTimeout(connect, delay)
  }

  /** 建立 SSE 连接（内部重连与手动刷新共用入口） */
  function connect() {
    clearTimeout(retryTimer)
    clearTimeout(openTimer)
    source?.close()
    closedByUser = false
    status.value = reconnectAttempts > 0 ? 'reconnecting' : 'connecting'
    ensureFlushTimer()

    // EventSource 无法自定义请求头，认证 token 以查询参数携带（后端未启用认证时忽略）
    const token = getStoredToken()
    const url = token
      ? `${LOG_STREAM_URL}?access_token=${encodeURIComponent(token)}`
      : LOG_STREAM_URL
    const es = new EventSource(url)
    source = es

    // 建立超时兜底：响应头迟迟未到时主动放弃并重连（close 后不会再触发 error 事件）
    openTimer = setTimeout(() => {
      if (source !== es) return
      es.close()
      source = null
      if (!closedByUser) scheduleReconnect()
    }, CONNECT_TIMEOUT)

    es.onopen = () => {
      // 连接成功：重置重连计数，进入正常接收状态
      clearTimeout(openTimer)
      reconnectAttempts = 0
      reconnectAttempt.value = 0
      lastError.value = ''
      status.value = 'connected'
    }

    es.onmessage = (event: MessageEvent) => {
      pending.push(parseLogPayload(String(event.data)))
      // 队列也做上限保护：极端洪峰下丢弃最旧的待渲染消息
      if (pending.length > MAX_LOGS) pending = pending.slice(-MAX_LOGS)
    }

    // EventSource 原生也会自动重连，这里主动 close 改为自管理，
    // 以实现次数限制、退避间隔与用户提示
    es.onerror = () => {
      clearTimeout(openTimer)
      es.close()
      source = null
      if (closedByUser) return
      scheduleReconnect()
    }
  }

  /** 手动刷新/重连：清空错误与重连计数后立即连接 */
  function refresh() {
    reconnectAttempts = 0
    reconnectAttempt.value = 0
    lastError.value = ''
    connect()
  }

  /** 主动断开（组件卸载时调用） */
  function disconnect() {
    closedByUser = true
    clearTimeout(retryTimer)
    clearTimeout(openTimer)
    stopFlushTimer()
    source?.close()
    source = null
    status.value = 'disconnected'
  }

  /** 清空日志：内存与本地缓存一并清除，SSE 连接保持不变 */
  function clear() {
    entries.value = []
    pending = []
    localStorage.removeItem(CACHE_KEY)
  }

  // 组件作用域销毁时自动断开连接并清理定时器，防止泄漏
  onScopeDispose(disconnect)

  return {
    entries,
    status,
    reconnectAttempt,
    lastError,
    refresh,
    disconnect,
    clear,
  }
}
