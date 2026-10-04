import type { RouteContext, RouteResult } from '../adapter'
import {
  deleteConfig,
  hasConfig,
  listConfigNames,
  makeDefaultConfig,
  readConfig,
  writeConfig,
} from '../state'

/**
 * /api/Configs 演示处理器：
 * - GET    /Configs        → 所有配置名
 * - GET    /Configs/{name} → 配置内容（404 资源不存在）
 * - POST   /Configs/{name} → 新建（400 空名/非法名，409 重名）
 * - PUT    /Configs/{name} → 更新（404 不存在，400 请求体无效）
 * - DELETE /Configs/{name} → 删除（404 不存在）
 */

/** 后端拒绝的配置名字符集 */
const ILLEGAL_NAME = /[\\/:*?"<>|]/

/** 还原路径中的配置名（URL 编码解码 + 去首尾空白），解码失败时用原始串兜底 */
function decodeName(raw: string): string {
  let decoded = raw
  try {
    decoded = decodeURIComponent(raw)
  } catch {
    /* 非法编码序列：保留原始串 */
  }
  return decoded.trim()
}

/** 404 兜底：与后端 statusMessage(404) 文案保持一致 */
function notFound(): RouteResult {
  return { status: 404, envelope: { success: false, message: '资源不存在' } }
}

export function handleListConfigs(_ctx: RouteContext): RouteResult {
  return { envelope: { success: true, message: '', data: listConfigNames() } }
}

export function handleGetConfig(ctx: RouteContext): RouteResult {
  const data = readConfig(decodeName(ctx.params[0] ?? ''))
  if (!data) return notFound()
  return { envelope: { success: true, message: '', data } }
}

export function handleCreateConfig(ctx: RouteContext): RouteResult {
  const name = decodeName(ctx.params[0] ?? '')
  if (!name) {
    return { status: 400, envelope: { success: false, message: '配置名不能为空' } }
  }
  if (ILLEGAL_NAME.test(name)) {
    return {
      status: 400,
      envelope: { success: false, message: '配置名不能包含以下字符：\\ / : * ? " < > |' },
    }
  }
  if (hasConfig(name)) {
    return { status: 409, envelope: { success: false, message: `配置 "${name}" 已存在` } }
  }
  writeConfig(name, makeDefaultConfig(name))
  return { envelope: { success: true, message: '', data: `配置 "${name}" 已创建` } }
}

export function handleUpdateConfig(ctx: RouteContext): RouteResult {
  const name = decodeName(ctx.params[0] ?? '')
  if (!hasConfig(name)) return notFound()
  if (typeof ctx.body !== 'object' || ctx.body === null || Array.isArray(ctx.body)) {
    return { status: 400, envelope: { success: false, message: '请求体无效' } }
  }
  writeConfig(name, ctx.body as Record<string, unknown>)
  return { envelope: { success: true, message: '', data: `配置 "${name}" 已保存` } }
}

export function handleDeleteConfig(ctx: RouteContext): RouteResult {
  const name = decodeName(ctx.params[0] ?? '')
  if (!deleteConfig(name)) return notFound()
  return { envelope: { success: true, message: '', data: `配置 "${name}" 已删除` } }
}
