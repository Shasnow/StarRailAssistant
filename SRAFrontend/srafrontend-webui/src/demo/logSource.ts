import { formatTime } from '../api/logs'
import type { LogLevel } from '../api/logs'
import type { LogSource } from './mode'
import { computeTaskProgress, getTaskSnapshot } from './state'

/**
 * 演示日志源：实现与 EventSource 兼容的最小接口（mode.ts 的 LogSource），
 * 定时产出 JSON 负载日志（{level,message,timestamp}），供 useLogStream 解析展示。
 * 任务运行中输出进度日志，空闲时轮换输出模板日志。
 */

/** EventSource 状态字面常量：jsdom/Node 无 EventSource 静态量，不引用全局枚举 */
const CONNECTING = 0
const OPEN = 1
const CLOSED = 2

/** 模拟「响应头到达」的建连耗时 */
const OPEN_DELAY = 500

/** 消息推送间隔区间（毫秒） */
const MESSAGE_MIN = 800
const MESSAGE_MAX = 1500

interface DemoLogPayload {
  level: LogLevel
  message: string
  timestamp: string
}

/** 空闲时循环轮换的模板日志 */
const IDLE_LOGS: Array<Pick<DemoLogPayload, 'level' | 'message'>> = [
  { level: 'INFO', message: '演示模式已就绪，当前无后端连接' },
  { level: 'INFO', message: '配置列表加载完成，共 3 份可用配置' },
  { level: 'DEBUG', message: '截图轮询切换为本地演示画面' },
  { level: 'WARN', message: '静态部署环境：所有数据均为模拟数据' },
  { level: 'INFO', message: '等待任务启动，可从配置页运行任一配置' },
  { level: 'DEBUG', message: '演示日志心跳正常' },
]

/** 演示日志源（EventSource 最小兼容实现） */
export class DemoLogSource implements LogSource {
  readyState = CONNECTING
  onopen: ((ev: Event) => unknown) | null = null
  onmessage: ((ev: MessageEvent) => unknown) | null = null
  onerror: ((ev: Event) => unknown) | null = null

  private idleIndex = 0
  private closed = false
  private openTimer: ReturnType<typeof setTimeout> | undefined
  private messageTimer: ReturnType<typeof setTimeout> | undefined

  constructor() {
    this.openTimer = setTimeout(() => this.handleOpen(), OPEN_DELAY)
  }

  close(): void {
    this.closed = true
    this.readyState = CLOSED
    clearTimeout(this.openTimer)
    clearTimeout(this.messageTimer)
  }

  /** 建连成功：置 OPEN 并通知 onopen，随后进入周期推送 */
  private handleOpen(): void {
    if (this.closed) return
    this.readyState = OPEN
    this.onopen?.(new Event('open'))
    this.scheduleNext()
  }

  private scheduleNext(): void {
    const delay = MESSAGE_MIN + Math.random() * (MESSAGE_MAX - MESSAGE_MIN)
    this.messageTimer = setTimeout(() => this.emit(), delay)
  }

  private emit(): void {
    if (this.closed) return
    const payload: DemoLogPayload = {
      ...this.nextLog(),
      timestamp: formatTime(new Date()),
    }
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent)
    this.scheduleNext()
  }

  /** 运行中→进度日志；否则轮换空闲模板日志 */
  private nextLog(): Pick<DemoLogPayload, 'level' | 'message'> {
    const task = getTaskSnapshot()
    if (task && task.status === 'running') {
      const [current, total] = computeTaskProgress(task)
      return {
        level: 'INFO',
        message: `任务执行中 ${current}/${total}（${task.unit}，配置：${task.configs.join('、')}）`,
      }
    }
    const idle = IDLE_LOGS[this.idleIndex % IDLE_LOGS.length] ?? IDLE_LOGS[0]
    this.idleIndex += 1
    return idle ?? { level: 'INFO', message: '演示模式已就绪' }
  }
}
