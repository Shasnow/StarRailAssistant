import { request, requestEnvelope } from './http'
import type { ApiEnvelope } from './http'

/**
 * /api/Settings 服务模块（对应 OpenAPI SettingsController）：
 * - GET /api/Settings  获取当前应用设置，R.data 为 AppSettings（按 section 分组的对象）
 * - PUT /api/Settings  按字段修改设置，支持只传需要修改的部分，返回被更新的字段名列表
 *
 * 失败时抛出 ApiError，支持通过 AbortSignal 取消。
 */

/** AppSettings 的部分 JSON：{ [section]: { [fieldKey]: value } }，如 { advanced: { 'backend.remote.enabled': true } } */
export type AppSettingsPayload = Record<string, Record<string, unknown>>

/** 获取当前应用设置（data 非对象时按空设置处理） */
export async function fetchSettings(signal?: AbortSignal): Promise<AppSettingsPayload> {
  const data = await request<AppSettingsPayload>({ url: '/Settings', method: 'get', signal })
  return data && typeof data === 'object' ? data : {}
}

/** 按字段修改设置，返回后端回传的已更新字段名列表 */
export async function updateSettings(
  partial: AppSettingsPayload,
  signal?: AbortSignal,
): Promise<string[]> {
  const envelope: ApiEnvelope<unknown> = await requestEnvelope({
    url: '/Settings',
    method: 'put',
    data: partial,
    signal,
  })
  return Array.isArray(envelope.data) ? envelope.data.map((it) => String(it)) : []
}
