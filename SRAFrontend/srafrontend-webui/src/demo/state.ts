import type { TasksConfigPayload } from '../api/configs'
import type { AppSettingsPayload } from '../api/settings'
import type { RunStatus, TaskStatus } from '../api/task'
import { buildDefaultModel } from '../utils/schemaForm'
import { demoOpenApiSpec } from './openapi'

/** 演示状态持久化 key（刷新页面保留演示数据，清掉该 key 即恢复出厂演示数据） */
const STORAGE_KEY = 'sra_demo_state_v1'

/** 单次任务模拟运行总时长：超时后惰性结算为已完成 */
const RUN_DURATION_MS = 45_000

/** 单次任务模拟总进度步数 */
const RUN_TOTAL_TASKS = 12

/** 演示任务运行记录（时间戳驱动，读取时按耗时惰性推进状态与进度） */
export interface DemoTask {
  sessionId: string
  status: RunStatus
  configs: string[]
  unit: string
  error: string
  startedAt: number
  /** 运行结束时间（completed/stopped），运行中为 null */
  endedAt: number | null
}

/** 演示模式内存状态 */
export interface DemoState {
  configs: Record<string, TasksConfigPayload>
  settings: AppSettingsPayload
  task: DemoTask | null
}

/** 深拷贝：payload 一律复制后出入，避免调用方改动内部演示数据 */
function clone<T>(value: T): T {
  return structuredClone(value)
}

/** 是否为普通对象（拒绝 null/数组/原始值） */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/* ---------- 默认数据 ---------- */

/** 按 OpenAPI TasksConfig schema 递归生成带默认值的新配置 */
export function makeDefaultConfig(name: string): TasksConfigPayload {
  const schema = demoOpenApiSpec.components.schemas['TasksConfig']
  const model = schema ? buildDefaultModel(demoOpenApiSpec, schema) : null
  const payload = isRecord(model) ? model : {}
  payload['name'] = name
  payload['version'] = 1
  return payload as TasksConfigPayload
}

/** 首个示例配置打开「清体力」开关，让演示数据看起来处于启用状态 */
function withTrailblazeEnabled(payload: TasksConfigPayload): TasksConfigPayload {
  const power = payload['trailblazePower']
  if (isRecord(power)) power['enabled'] = true
  return payload
}

function createDefaultState(): DemoState {
  return {
    configs: {
      日常清体力: withTrailblazeEnabled(makeDefaultConfig('日常清体力')),
      周本速刷: makeDefaultConfig('周本速刷'),
      签到跑图: makeDefaultConfig('签到跑图'),
    },
    settings: {},
    task: null,
  }
}

/* ---------- 持久化 ---------- */

function loadState(): DemoState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed: unknown = JSON.parse(raw)
      if (isRecord(parsed) && isRecord(parsed['configs']) && isRecord(parsed['settings'])) {
        return {
          configs: parsed['configs'] as Record<string, TasksConfigPayload>,
          settings: parsed['settings'] as AppSettingsPayload,
          task: isRecord(parsed['task']) ? (parsed['task'] as unknown as DemoTask) : null,
        }
      }
    }
  } catch {
    // 本地数据损坏时静默回退到默认演示数据
  }
  return createDefaultState()
}

let state: DemoState = loadState()

function persistState(): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // 存储不可用（隐私模式/配额满）时仅保留内存态
  }
}

/** 重置为出厂演示数据（测试与手动恢复场景使用） */
export function resetDemoState(): DemoState {
  state = createDefaultState()
  persistState()
  return state
}

/* ---------- 配置（Configs） ---------- */

/** 所有配置名（字典序） */
export function listConfigNames(): string[] {
  return Object.keys(state.configs)
    .filter((name) => Object.hasOwn(state.configs, name))
    .sort()
}

/** 配置是否存在 */
export function hasConfig(name: string): boolean {
  return Object.hasOwn(state.configs, name)
}

/** 读取配置副本；不存在返回 null */
export function readConfig(name: string): TasksConfigPayload | null {
  if (!hasConfig(name)) return null
  const found = state.configs[name]
  return found ? clone(found) : null
}

/** 新建/覆盖配置并落盘 */
export function writeConfig(name: string, payload: TasksConfigPayload): void {
  state.configs[name] = clone(payload)
  persistState()
}

/** 删除配置；不存在返回 false */
export function deleteConfig(name: string): boolean {
  if (!hasConfig(name)) return false
  delete state.configs[name]
  persistState()
  return true
}

/* ---------- 设置（Settings） ---------- */

/** 读取设置副本 */
export function readSettings(): AppSettingsPayload {
  return clone(state.settings)
}

/** 按 section.field 合并部分设置，返回被更新的字段名列表 */
export function writeSettings(partial: AppSettingsPayload): string[] {
  const updated: string[] = []
  for (const [section, fields] of Object.entries(partial)) {
    if (!isRecord(fields)) continue
    const target = state.settings[section] ?? (state.settings[section] = {})
    for (const [key, value] of Object.entries(fields)) {
      target[key] = value
      updated.push(`${section}.${key}`)
    }
  }
  if (updated.length) persistState()
  return updated
}

/* ---------- 任务（Task） ---------- */

/** 结算任务状态：运行超时的任务惰性转为已完成并落盘，返回内部记录引用 */
function settleTask(): DemoTask | null {
  const task = state.task
  if (!task) return null
  if (task.status === 'running' && Date.now() - task.startedAt >= RUN_DURATION_MS) {
    task.status = 'completed'
    task.endedAt = task.startedAt + RUN_DURATION_MS
    task.unit = `任务${RUN_TOTAL_TASKS}`
    persistState()
  }
  return task
}

/** 按已耗时推算进度 [current, total]：完成→满格，运行中/已停止→按时间比例推进 */
export function computeTaskProgress(task: DemoTask): [number, number] {
  if (task.status === 'completed') return [RUN_TOTAL_TASKS, RUN_TOTAL_TASKS]
  const anchor = task.endedAt ?? Date.now()
  const elapsed = Math.max(0, anchor - task.startedAt)
  const ratio = Math.min(1, elapsed / RUN_DURATION_MS)
  return [Math.min(RUN_TOTAL_TASKS, Math.floor(ratio * RUN_TOTAL_TASKS)), RUN_TOTAL_TASKS]
}

/** 读取任务记录副本；无任务或状态已结算后仍为运行中以外的记录也照常返回 */
export function getTaskSnapshot(): DemoTask | null {
  const task = settleTask()
  return task ? { ...task } : null
}

/** 生成后端 RuntimeInfo 形状的任务状态；无任务记录返回 null */
export function getTaskStatus(): TaskStatus | null {
  const task = settleTask()
  if (!task) return null
  return {
    session_id: task.sessionId,
    pid: task.status === 'running' ? 4242 : 0,
    mode: 'demo',
    status: task.status,
    configs: [...task.configs],
    unit: task.unit,
    error: task.error,
    progress: computeTaskProgress(task),
  }
}

/** 启动演示任务（调用方负责参数与状态前置校验），返回新任务记录副本 */
export function startDemoTask(configNames: string[]): DemoTask {
  const task: DemoTask = {
    sessionId: `demo-${Date.now().toString(36)}`,
    status: 'running',
    configs: [...configNames],
    unit: '任务1',
    error: '',
    startedAt: Date.now(),
    endedAt: null,
  }
  state.task = task
  persistState()
  return { ...task }
}

/** 停止演示任务；仅运行中任务可停止，返回停止后的记录副本 */
export function stopDemoTask(): DemoTask | null {
  const task = settleTask()
  if (!task || task.status !== 'running') return null
  task.status = 'stopped'
  task.endedAt = Date.now()
  persistState()
  return { ...task }
}
