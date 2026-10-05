import type { RouteContext, RouteResult } from '../adapter'
import type { AppSettingsPayload } from '../../api/settings'
import { readSettings, writeSettings } from '../state'

/**
 * /api 系统类演示处理器：auth、App 系统信息、Backend 控制、Settings 读写。
 * 确定性行为：登录仅要求非空 token；重启/停止仅返回提示，不产生任何副作用。
 */

/** 演示用问候/文案列表（/App/phrases） */
const PHRASES = [
  '开拓者，今天也要加油哦',
  '愿此行，终抵群星',
  '星穹列车即将启程，请坐稳扶好',
  '今日任务已全部完成，做得很好',
  '帕姆列车长为你加油打气',
  '前方到站：愿你一路顺风',
  '愿你途中有灯，心中有光',
  '敬每一份不曾放弃的努力',
]

/** 演示用运行时信息：版本取构建注入的真实版本，其余标注演示值 */
function buildSystemInfo(): Record<string, unknown> {
  return {
    version: __BUILD_INFO__.appVersion,
    osVersion: `${navigator.platform || 'Web'}`,
    architecture: 'X64',
    dotnetVersion: '10.0',
    processorCount: navigator.hardwareConcurrency || 4,
    cultureInfo: 'zh-CN',
  }
}

export function handleAuth(ctx: RouteContext): RouteResult {
  const body = ctx.body as { token?: unknown } | null
  const token = body && typeof body === 'object' ? body.token : null
  if (typeof token === 'string' && token.trim()) {
    return { envelope: { success: true, message: '校验通过', data: null } }
  }
  return { status: 401, envelope: { success: false, message: 'Access Token 无效' } }
}

export function handleSystemInfo(_ctx: RouteContext): RouteResult {
  return { envelope: { success: true, message: '', data: buildSystemInfo() } }
}

export function handlePhrases(_ctx: RouteContext): RouteResult {
  return { envelope: { success: true, message: '', data: [...PHRASES] } }
}

export function handleBackendRestart(_ctx: RouteContext): RouteResult {
  return { envelope: { success: true, message: '后端重启指令已下发' } }
}

export function handleBackendStop(_ctx: RouteContext): RouteResult {
  return { envelope: { success: true, message: '后端停止指令已下发' } }
}

export function handleGetSettings(_ctx: RouteContext): RouteResult {
  return { envelope: { success: true, message: '', data: readSettings() } }
}

export function handlePutSettings(ctx: RouteContext): RouteResult {
  if (typeof ctx.body !== 'object' || ctx.body === null || Array.isArray(ctx.body)) {
    return { status: 400, envelope: { success: false, message: '请求体无效' } }
  }
  const updated = writeSettings(ctx.body as AppSettingsPayload)
  return { envelope: { success: true, message: '', data: updated } }
}
