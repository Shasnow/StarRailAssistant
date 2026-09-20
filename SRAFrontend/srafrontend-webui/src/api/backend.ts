import { requestEnvelope } from './http'

/**
 * /api/Backend 服务模块（对应 OpenAPI BackendController）：
 * - POST /api/Backend/restart  重启后端（请求体可选，不传使用默认参数）
 * - POST /api/Backend/stop     停止后端
 *
 * 失败时抛出 ApiError，支持通过 AbortSignal 取消。
 */

/** 重启后端，返回后端提示 message */
export async function restartBackend(signal?: AbortSignal): Promise<string> {
  const envelope = await requestEnvelope({ url: '/Backend/restart', method: 'post', signal })
  return envelope.message
}

/** 停止后端，返回后端提示 message */
export async function stopBackend(signal?: AbortSignal): Promise<string> {
  const envelope = await requestEnvelope({ url: '/Backend/stop', method: 'post', signal })
  return envelope.message
}
