import { ApiError, http, statusMessage } from './http'
import type { ApiEnvelope } from './http'

/**
 * /api/Auth 认证模块（对应后端 AuthController）：
 * - POST /api/Auth  请求体 { token }，校验 access token
 *
 * 仅以 HTTP 状态码判定结果：
 * - validateStatus 放行非 2xx（axios 默认会把 401 变成异常，这里需要直接读状态码）
 * - skipAuthHeader 让校验请求不携带本地遗留的旧 token（否则旧 token 会先于请求体被后端拒绝）
 */

/**
 * 校验用户输入的 access token：
 * - 200 → 校验通过，返回
 * - 401 → 抛出「Access Token 无效」的 ApiError
 * - 其他 → 抛出携带状态码的 ApiError
 */
export async function verifyToken(token: string): Promise<void> {
  const response = await http.request<ApiEnvelope>({
    url: '/auth',
    method: 'post',
    data: { token },
    validateStatus: () => true,
    rawEnvelope: true,
    skipAuthHeader: true,
  })

  if (response.status === 200) return
  if (response.status === 401) throw new ApiError('Access Token 无效，请检查后重试', 401)
  throw new ApiError(statusMessage(response.status), response.status)
}