import { http, requestEnvelope, type ApiEnvelope } from './http'

/**
 * /api/Task 服务模块（对应 OpenAPI TaskController）：
 * - POST /api/Task/run     运行任务（400 参数无效 / 409 已有任务运行）
 * - POST /api/Task/stop    停止任务
 * - GET  /api/Task/status  获取任务状态（R.data 为 RuntimeInfo，字段名与后端一致）
 *
 * 失败时抛出 ApiError，支持通过 AbortSignal 取消。
 */

/** 运行任务请求体：configName 使用后端持久化的配置；config 直接下发配置内容 */
export interface RunRequest {
  configName?: string | null
  config?: Record<string, unknown> | null
  /** 携带 config 时是否将其持久化到后端 */
  persist?: boolean
}

/** Runner 运行状态（对齐后端 RunStatus StrEnum） */
export type RunStatus = 'idle' | 'running' | 'completed' | 'failed' | 'stopped'

/** 运行时状态（对齐后端 RuntimeInfo dataclass，字段名与 JSON 序列化一致） */
export interface TaskStatus {
  session_id: string
  pid: number
  mode: string
  status: RunStatus
  /** 当前任务配置名列表（一个或多个） */
  configs: string[]
  /** 当前任务单位，如 "任务1" */
  unit: string
  error: string
  /** [current, total] 任务进度 */
  progress: [number, number]
}

/** 空闲默认状态：后端无任务运行或暂时拿不到状态时使用 */
export const IDLE_TASK_STATUS: TaskStatus = {
  session_id: '',
  pid: 0,
  mode: 'unknown',
  status: 'idle',
  configs: [],
  unit: '',
  error: '',
  progress: [0, 0],
}

const RUN_STATUSES: readonly string[] = ['idle', 'running', 'completed', 'failed', 'stopped']

/**
 * 补全 R.data 为完整 TaskStatus（字段名与后端 RuntimeInfo 一致）：
 * 仅做 JSON 边界的形状兜底——异常 / 缺失字段回退默认值，不做字段改名。
 */
export function normalizeTaskStatus(data: unknown): TaskStatus {
  if (typeof data !== 'object' || data === null) return { ...IDLE_TASK_STATUS }
  const d = data as Record<string, unknown>

  const rawStatus = String(d.status ?? '').toLowerCase()
  const status: RunStatus = RUN_STATUSES.includes(rawStatus) ? (rawStatus as RunStatus) : 'idle'

  const pid = Number(d.pid ?? 0)
  const configs = Array.isArray(d.configs) ? d.configs.map((c) => String(c)).filter(Boolean) : []
  const progress: [number, number] =
    Array.isArray(d.progress) && d.progress.length >= 2
      ? [Number(d.progress[0]) || 0, Number(d.progress[1]) || 0]
      : [0, 0]

  return {
    session_id: typeof d.session_id === 'string' ? d.session_id : '',
    pid: Number.isFinite(pid) && pid > 0 ? pid : 0,
    mode: typeof d.mode === 'string' && d.mode ? d.mode : 'unknown',
    status,
    configs,
    unit: typeof d.unit === 'string' ? d.unit : '',
    error: typeof d.error === 'string' ? d.error : '',
    progress,
  }
}

/** 运行任务，返回后端提示 message */
export async function runTask(body: RunRequest, signal?: AbortSignal): Promise<string> {
  const envelope = await requestEnvelope({ url: '/Task/run', method: 'post', data: body, signal })
  return envelope.message
}

/** 停止任务，返回后端提示 message */
export async function stopTask(signal?: AbortSignal): Promise<string> {
  const envelope = await requestEnvelope({ url: '/Task/stop', method: 'post', signal })
  return envelope.message
}

/**
 * 获取任务状态。空闲时后端编排器返回 success=false（如内部后端无响应），
 * 因此以 rawEnvelope 方式请求并自行解读：无有效数据一律视为空闲。
 */
export async function fetchTaskStatus(signal?: AbortSignal): Promise<TaskStatus> {
  const response = await http.request<ApiEnvelope>({
    url: '/Task/status',
    method: 'get',
    signal,
    rawEnvelope: true,
  })
  const envelope = response.data
  if (!envelope || envelope.success === false || envelope.data == null) {
    return { ...IDLE_TASK_STATUS }
  }
  return normalizeTaskStatus(envelope.data)
}
