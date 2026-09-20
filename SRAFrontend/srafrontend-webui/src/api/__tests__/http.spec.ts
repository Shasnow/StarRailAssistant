// @vitest-environment jsdom
import { AxiosError } from 'axios'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  ApiError,
  clearStoredToken,
  createHttpClient,
  getStoredToken,
  http,
  isCanceledError,
  request,
  setStoredToken,
  setUnauthorizedHandler,
} from '../http'

/** 构造成功 AxiosResponse（adapter 返回值） */
function okJson(data: unknown, status = 200): AxiosResponse {
  return { data, status, statusText: 'OK', headers: {}, config: {} as InternalAxiosRequestConfig }
}

/**
 * 构造 HTTP 错误：axios 的 validateStatus 由内置 adapter 执行，
 * 自定义 adapter 需显式 reject 携带 response 的 AxiosError 才能走错误分支。
 */
function failJson(data: unknown, status: number): Promise<never> {
  return Promise.reject(
    new AxiosError(
      `Request failed with status ${status}`,
      AxiosError.ERR_BAD_RESPONSE,
      {} as InternalAxiosRequestConfig,
      {},
      okJson(data, status),
    ),
  )
}

beforeEach(() => {
  localStorage.clear()
  // 替换全局实例的 adapter：不发真实网络请求，直接返回桩数据
  http.defaults.adapter = async (config) => {
    throw new AxiosError(`no mock for ${config.url}`, 'ERR_BAD_REQUEST', config)
  }
})

afterEach(() => {
  clearStoredToken()
})

describe('认证 token 拦截器', () => {
  it('token 存取', () => {
    expect(getStoredToken()).toBe('')
    setStoredToken('t-123')
    expect(getStoredToken()).toBe('t-123')
    clearStoredToken()
    expect(getStoredToken()).toBe('')
  })

  it('有 token 时请求头附加 X-Access-Token', async () => {
    setStoredToken('t-123')
    let seen: unknown
    http.defaults.adapter = async (config) => {
      seen = config.headers?.['X-Access-Token']
      return okJson({ success: true, message: '', data: null })
    }
    await http.get('/ping')
    expect(seen).toBe('t-123')
  })

  it('无 token 时不附加 X-Access-Token', async () => {
    let seen: unknown = 'sentinel'
    http.defaults.adapter = async (config) => {
      seen = config.headers?.['X-Access-Token']
      return okJson({ success: true, message: '', data: null })
    }
    await http.get('/ping')
    expect(seen).toBeUndefined()
  })

  it('skipAuthHeader 的请求不附加 token（认证探测/校验）', async () => {
    setStoredToken('stale')
    let seen: unknown = 'sentinel'
    http.defaults.adapter = async (config) => {
      seen = config.headers?.['X-Access-Token']
      return okJson({ success: true, message: '', data: null })
    }
    await request({ url: '/auth', method: 'post', skipAuthHeader: true })
    expect(seen).toBeUndefined()
  })
})

describe('全局 401 回调', () => {
  afterEach(() => setUnauthorizedHandler(null))

  it('业务请求返回 401 时触发回调', async () => {
    let called = 0
    setUnauthorizedHandler(() => {
      called += 1
    })
    http.defaults.adapter = async () => failJson({}, 401)
    await expect(request({ url: '/Configs' })).rejects.toMatchObject({ status: 401 })
    expect(called).toBe(1)
  })

  it('其他错误状态不触发回调', async () => {
    let called = 0
    setUnauthorizedHandler(() => {
      called += 1
    })
    http.defaults.adapter = async () => failJson({}, 500)
    await expect(request({ url: '/Configs' })).rejects.toMatchObject({ status: 500 })
    expect(called).toBe(0)
  })
})

describe('R<T> 解包与业务失败', () => {
  it('request 解包返回 data 字段', async () => {
    http.defaults.adapter = async () => okJson({ success: true, message: 'ok', data: ['a', 'b'] })
    await expect(request<string[]>({ url: '/Configs' })).resolves.toEqual(['a', 'b'])
  })

  it('success=false 抛出 ApiError（后端 message + HTTP 状态码）', async () => {
    http.defaults.adapter = async () => okJson({ success: false, message: '配置已存在' }, 200)
    const promise = request<string>({ url: '/Configs/x', method: 'post' })
    await expect(promise).rejects.toBeInstanceOf(ApiError)
    await promise.catch((e: ApiError) => {
      expect(e.message).toBe('配置已存在')
      expect(e.status).toBe(200)
      expect(e.canceled).toBe(false)
    })
  })
})

describe('HTTP 错误归一化', () => {
  it('404 ProblemDetails：取 title 作为错误信息', async () => {
    http.defaults.adapter = async () => failJson({ title: '配置不存在', status: 404 }, 404)
    await expect(request({ url: '/Configs/x' })).rejects.toMatchObject({
      name: 'ApiError',
      message: '配置不存在',
      status: 404,
    })
  })

  it('409 无错误体：按状态码给出默认提示', async () => {
    http.defaults.adapter = async () => failJson('冲突', 409)
    await expect(request({ url: '/Configs/x', method: 'post' })).rejects.toMatchObject({
      message: '资源已存在或状态冲突',
      status: 409,
    })
  })

  it('401 → 未授权提示', async () => {
    http.defaults.adapter = async () => failJson({}, 401)
    await expect(request({ url: '/x' })).rejects.toMatchObject({
      message: '未授权，请先完成认证',
      status: 401,
    })
  })

  it('请求超时（ECONNABORTED）', async () => {
    http.defaults.adapter = async (config) => {
      throw new AxiosError('timeout of 15000ms exceeded', 'ECONNABORTED', config)
    }
    await expect(request({ url: '/x' })).rejects.toMatchObject({
      message: '请求超时，请检查后端服务是否可用',
    })
  })

  it('网络异常（无 response）', async () => {
    http.defaults.adapter = async (config) => {
      throw new AxiosError('Network Error', 'ERR_NETWORK', config)
    }
    await expect(request({ url: '/x' })).rejects.toMatchObject({
      message: '网络异常，无法连接到后端服务',
    })
  })

  it('请求取消：canceled=true，isCanceledError 识别', async () => {
    http.defaults.adapter = async (config) => {
      throw new AxiosError('canceled', 'ERR_CANCELED', config)
    }
    const err: ApiError = await request({ url: '/x' }).then(
      () => Promise.reject(new Error('should reject')),
      (e: ApiError) => e,
    )
    expect(err.canceled).toBe(true)
    expect(isCanceledError(err)).toBe(true)
  })

  it('非 axios 错误兜底包装', async () => {
    http.defaults.adapter = async () => Promise.reject(new Error('boom'))
    await expect(request({ url: '/x' })).rejects.toMatchObject({ message: 'boom' })
  })
})

describe('取消与默认配置', () => {
  it('AbortSignal 透传到 adapter config', async () => {
    const controller = new AbortController()
    let seen: AbortSignal | undefined
    http.defaults.adapter = async (config) => {
      seen = config.signal
      return okJson({ success: true, message: '', data: null })
    }
    await request({ url: '/x', signal: controller.signal })
    expect(seen).toBe(controller.signal)
  })

  it('createHttpClient 默认 baseURL /api 与 15s 超时', () => {
    const client = createHttpClient()
    expect(client.defaults.baseURL).toBe('/api')
    expect(client.defaults.timeout).toBe(15_000)
  })
})
