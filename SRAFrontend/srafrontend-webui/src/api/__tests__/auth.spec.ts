// @vitest-environment jsdom
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { afterEach, describe, expect, it } from 'vitest'
import { verifyToken } from '../auth'
import { ApiError, clearStoredToken, http, setStoredToken } from '../http'

/**
 * 构造桩 adapter：校验请求用 validateStatus 放行，任意状态码都 resolve。
 * 必须把真实 config 回填到 response.config —— 响应拦截器靠它的 rawEnvelope 标记跳过 success=false 抛错。
 */
function respond(
  status = 200,
  body: unknown = { success: true, message: '', data: null },
  /** 读取实际发出的请求配置（url / data / headers） */
  inspect?: (config: InternalAxiosRequestConfig) => void,
) {
  return async (config: InternalAxiosRequestConfig): Promise<AxiosResponse> => {
    inspect?.(config)
    return { data: body, status, statusText: 'OK', headers: {}, config }
  }
}

afterEach(() => {
  clearStoredToken()
  http.defaults.adapter = async (config) => {
    throw new Error(`no mock for ${config.url}`)
  }
})

describe('verifyToken 校验 Access Token', () => {
  it('200 → 校验通过', async () => {
    http.defaults.adapter = respond(200)
    await expect(verifyToken('t-abc')).resolves.toBeUndefined()
  })

  it('401 → 抛出 ApiError（token 无效）', async () => {
    http.defaults.adapter = respond(401, { success: false, message: '未授权' })
    const promise = verifyToken('bad')
    await expect(promise).rejects.toBeInstanceOf(ApiError)
    await promise.catch((e: ApiError) => {
      expect(e.message).toBe('Access Token 无效，请检查后重试')
      expect(e.status).toBe(401)
    })
  })

  it('请求 /api/Auth，请求体为 { token } 且不携带本地遗留的 X-Access-Token', async () => {
    setStoredToken('stale-token')
    const seen: { url?: unknown; body?: unknown; header?: unknown } = { header: 'sentinel' }
    http.defaults.adapter = respond(200, undefined, (config) => {
      seen.url = config.url
      seen.body = config.data
      seen.header = config.headers?.['X-Access-Token']
    })

    await verifyToken('t-abc')
    expect(seen.url).toBe('/auth')
    expect(JSON.parse(String(seen.body))).toEqual({ token: 't-abc' })
    expect(seen.header).toBeUndefined()
  })

  it('其他失败状态按状态码提示', async () => {
    http.defaults.adapter = respond(503, { success: false, message: '' })
    await expect(verifyToken('t-abc')).rejects.toMatchObject({
      message: '服务暂不可用，请稍后重试',
      status: 503,
    })
  })
})
