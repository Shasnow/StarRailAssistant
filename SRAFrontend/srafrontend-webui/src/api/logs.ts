/**
 * /api/logs 日志流服务模块：
 * - GET /api/logs/stream → SSE（text/event-stream）实时推送日志
 *
 * SSE 消息负载约定（默认 message 事件）：
 * - 优先 JSON：{ level?: 'ERROR'|'WARN'|'INFO'|'DEBUG', message: string, timestamp?: string, source?: string }
 * - 后端纯文本行（自带前缀）：`21:51:02 | INFO  | 消息` → 拆出时间与级别，避免前端重复渲染
 * - 无前缀纯文本行：整行作为 INFO 级别日志，时间戳取前端接收时刻
 */

/** 日志级别（与后端日志级别对应，展示时区分颜色） */
export type LogLevel = 'ERROR' | 'WARN' | 'INFO' | 'DEBUG'

export const LOG_LEVELS: LogLevel[] = ['ERROR', 'WARN', 'INFO', 'DEBUG']

/** 单条日志：id 为前端自增序号，仅用于 v-for 的 key */
export interface LogEntry {
  id: number
  level: LogLevel
  message: string
  timestamp: string
}

/** SSE 推送端点（开发环境经 vite 代理转发到后端，生产由反代接管） */
export const LOG_STREAM_URL = '/api/backend/logs/stream'

/** 本地时间格式化 HH:mm:ss */
export function formatTime(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

/** 级别归一化：大小写不敏感，未知级别回退 INFO */
function normalizeLevel(value: unknown): LogLevel {
  const upper = typeof value === 'string' ? value.toUpperCase() : ''
  return (LOG_LEVELS as string[]).includes(upper) ? (upper as LogLevel) : 'INFO'
}

/** 后端纯文本行前缀：`21:51:02 | INFO  | 消息`（级别字段宽度可变，两侧空白不敏感） */
const PLAIN_PREFIX = /^(\d{1,2}:\d{2}:\d{2})\s*\|\s*([A-Za-z]+)\s*\|\s?(.*)$/

/**
 * 解析 SSE 推送的单条日志负载：
 * - JSON 负载：提取 level / message / timestamp，缺省字段按约定回退
 * - 带 `时间 | 级别 |` 前缀的纯文本行：拆出后端自带的时间与级别，仅保留消息体
 * - 无前缀非 JSON 文本：整行作为 INFO 日志，时间戳取当前接收时刻
 */
export function parseLogPayload(raw: string): Omit<LogEntry, 'id'> {
  const fallback = (): Omit<LogEntry, 'id'> => ({
    level: 'INFO',
    message: raw,
    timestamp: formatTime(new Date()),
  })
  if (!raw) return fallback()

  try {
    const data = JSON.parse(raw) as Record<string, unknown>
    return {
      level: normalizeLevel(data.level),
      // message 缺失或非字符串时回退为原始负载，保证内容不丢
      message: typeof data.message === 'string' ? data.message : raw,
      timestamp: typeof data.timestamp === 'string' ? data.timestamp : formatTime(new Date()),
    }
  } catch {
    // 非 JSON：识别后端自带的 `HH:mm:ss | LEVEL | msg` 前缀，避免前端重复渲染时间与等级
    const matched = PLAIN_PREFIX.exec(raw)
    if (matched) {
      return {
        level: normalizeLevel(matched[2]),
        message: matched[3] ?? '',
        timestamp: matched[1]!,
      }
    }
    return fallback()
  }
}
