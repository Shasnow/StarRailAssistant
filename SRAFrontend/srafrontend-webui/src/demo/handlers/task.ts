import type { RouteContext, RouteResult } from '../adapter'
import type { RunRequest } from '../../api/task'
import { getTaskStatus, hasConfig, startDemoTask, stopDemoTask } from '../state'

/**
 * /api/Task 演示处理器：
 * - POST /Task/run   → 启动模拟任务（409 已有任务，400 参数无效/配置不存在）
 * - POST /Task/stop  → 停止模拟任务（409 无运行中任务）
 * - GET  /Task/status → 运行中返回 RuntimeInfo；空闲返回 success:false（配合 rawEnvelope 解读）
 */

export function handleRunTask(ctx: RouteContext): RouteResult {
  if (getTaskStatus()?.status === 'running') {
    return { status: 409, envelope: { success: false, message: '已有任务正在运行' } }
  }

  const body = ctx.body as Partial<RunRequest> | null
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return { status: 400, envelope: { success: false, message: '请求体无效' } }
  }

  const configName = typeof body.configName === 'string' ? body.configName.trim() : ''
  if (configName) {
    if (!hasConfig(configName)) {
      return { status: 400, envelope: { success: false, message: `配置 "${configName}" 不存在` } }
    }
    startDemoTask([configName])
  } else if (body.config && typeof body.config === 'object') {
    // 直接下发配置内容的临时运行：不落库，仅模拟执行
    const rawName = body.config['name']
    startDemoTask([typeof rawName === 'string' && rawName ? rawName : '未命名配置'])
  } else {
    return { status: 400, envelope: { success: false, message: '缺少 configName 或 config' } }
  }

  return { envelope: { success: true, message: '任务已启动', data: null } }
}

export function handleStopTask(_ctx: RouteContext): RouteResult {
  if (getTaskStatus()?.status !== 'running') {
    return { status: 409, envelope: { success: false, message: '当前没有任务在运行' } }
  }
  stopDemoTask()
  return { envelope: { success: true, message: '任务已停止', data: null } }
}

export function handleTaskStatus(_ctx: RouteContext): RouteResult {
  const status = getTaskStatus()
  // 空闲：success=false 让 rawEnvelope 请求方解读为 IDLE（与真实后端行为一致）
  if (!status) {
    return { envelope: { success: false, message: '当前没有任务在运行' } }
  }
  return { envelope: { success: true, message: '', data: status } }
}
