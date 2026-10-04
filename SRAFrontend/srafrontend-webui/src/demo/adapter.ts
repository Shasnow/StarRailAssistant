import { AxiosError, CanceledError } from 'axios'
import type { AxiosHeaders, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { ApiEnvelope } from '../api/http'
import {
  handleCreateConfig,
  handleDeleteConfig,
  handleGetConfig,
  handleListConfigs,
  handleUpdateConfig,
} from './handlers/configs'
import { handleRunTask, handleStopTask, handleTaskStatus } from './handlers/task'
import {
  handleAuth,
  handleBackendRestart,
  handleBackendStop,
  handleGetSettings,
  handlePhrases,
  handlePutSettings,
  handleSystemInfo,
} from './handlers/system'

/**
 * 演示模式 axios 适配层：
 * 直接替换 http.defaults.adapter，所有 /api 请求在浏览器内闭环，
 * 不发出任何真实网络请求；按 method + 路径路由到 handlers 并返回 R<T> 包装。
 * 同时模拟「后端已启用访问认证」：除 /auth 校验接口外，业务请求必须携带
 * X-Access-Token，缺失时返回 401 —— 由既有 401 处理链跳转登录页，复刻完整登录流程。
 */

/** 模拟网络延迟区间（毫秒），让交互节奏接近真实后端 */
const LATENCY_MIN = 120
const LATENCY_MAX = 500

/** 路由命中上下文：path 已剥离 query，body 已完成 JSON 反序列化 */
export interface RouteContext {
  /** 小写 HTTP 方法 */
  method: string
  /** 请求路径（不含 query，如 /Configs/日常清体力 编码后原样） */
  path: string
  /** 正则捕获组（如配置名） */
  params: string[]
  /** 请求体：对象或字符串（axios transformRequest 已序列化，这里已还原） */
  body: unknown
  config: InternalAxiosRequestConfig
}

/** 路由处理结果：status 缺省 200；envelope 为返回给拦截器的 R 包装 */
export interface RouteResult {
  status?: number
  envelope: ApiEnvelope
}

export type DemoRouteHandler = (ctx: RouteContext) => RouteResult

export interface DemoRoute {
  method: string
  pattern: RegExp
  handler: DemoRouteHandler
}

/** 路由表：与 src/api 下各模块的 url 一一对应，未命中走兜底响应 */
const routes: DemoRoute[] = [
  // Configs
  { method: 'get', pattern: /^\/Configs$/, handler: handleListConfigs },
  { method: 'get', pattern: /^\/Configs\/(.+)$/, handler: handleGetConfig },
  { method: 'post', pattern: /^\/Configs\/(.+)$/, handler: handleCreateConfig },
  { method: 'put', pattern: /^\/Configs\/(.+)$/, handler: handleUpdateConfig },
  { method: 'delete', pattern: /^\/Configs\/(.+)$/, handler: handleDeleteConfig },
  // Task
  { method: 'post', pattern: /^\/Task\/run$/, handler: handleRunTask },
  { method: 'post', pattern: /^\/Task\/stop$/, handler: handleStopTask },
  { method: 'get', pattern: /^\/Task\/status$/, handler: handleTaskStatus },
  // App
  { method: 'get', pattern: /^\/App\/system-info$/, handler: handleSystemInfo },
  { method: 'get', pattern: /^\/App\/phrases$/, handler: handlePhrases },
  // Auth / Backend / Settings
  { method: 'post', pattern: /^\/auth$/, handler: handleAuth },
  { method: 'post', pattern: /^\/Backend\/restart$/, handler: handleBackendRestart },
  { method: 'post', pattern: /^\/Backend\/stop$/, handler: handleBackendStop },
  { method: 'get', pattern: /^\/Settings$/, handler: handleGetSettings },
  { method: 'put', pattern: /^\/Settings$/, handler: handlePutSettings },
]

/** 解析请求体：axios transformRequest 已把对象序列化为 JSON 字符串，这里还原 */
function parseBody(data: unknown): unknown {
  if (typeof data === 'string') {
    try {
      return JSON.parse(data)
    } catch {
      return data
    }
  }
  return data
}

/** 读取请求头中的访问 token（兼容 AxiosHeaders 的大小写不敏感读取与普通对象） */
function readAccessToken(config: InternalAxiosRequestConfig): string {
  const headers = config.headers as (Partial<AxiosHeaders> & Record<string, unknown>) | undefined
  const value =
    typeof headers?.get === 'function' ? headers.get('X-Access-Token') : headers?.['X-Access-Token']
  return typeof value === 'string' ? value : ''
}

/** 模拟网络延迟；期间信号被取消则以 CanceledError 拒绝（映射为「请求已取消」） */
function simulateLatency(config: InternalAxiosRequestConfig): Promise<void> {
  const signal = config.signal
  const ms = LATENCY_MIN + Math.random() * (LATENCY_MAX - LATENCY_MIN)
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new CanceledError('canceled', config))
      return
    }
    // 函数声明提升：onAbort 在 timer 初始化前定义，但仅在 abort 触发时执行，无 TDZ 风险
    function onAbort(): void {
      clearTimeout(timer)
      reject(new CanceledError('canceled', config))
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener?.('abort', onAbort)
      resolve()
    }, ms)
    signal?.addEventListener?.('abort', onAbort, { once: true })
  })
}

/**
 * 构造响应并按 validateStatus 判定成败：
 * 自定义 adapter 需自行实现 axios 内置 settle 逻辑，非 2xx 一律 reject 携带 response 的
 * AxiosError，才能进入拦截器错误分支归一化为 ApiError（auth 的 validateStatus(()=>true) 由此放行）。
 */
function buildResponse(
  config: InternalAxiosRequestConfig,
  status: number,
  data: unknown,
): AxiosResponse {
  const response: AxiosResponse = { data, status, statusText: '', headers: {}, config }
  const validate = config.validateStatus || ((s: number) => s >= 200 && s < 300)
  if (validate(status)) return response
  throw new AxiosError(
    `Request failed with status code ${status}`,
    AxiosError.ERR_BAD_RESPONSE,
    config,
    undefined,
    response,
  )
}

/** 创建演示适配器（赋给 http.defaults.adapter） */
export function createDemoAdapter(): (
  config: InternalAxiosRequestConfig,
) => Promise<AxiosResponse> {
  return async (config: InternalAxiosRequestConfig): Promise<AxiosResponse> => {
    const method = (config.method ?? 'get').toLowerCase()
    const path = (config.url ?? '').split('?')[0] ?? ''

    // 模拟启用认证的后端：/auth 为登录校验接口（skipAuthHeader 不带头），其余业务请求
    // 无 X-Access-Token 一律 401 —— 拦截器归一化后触发 unauthorizedHandler 跳转登录页
    if (path !== '/auth' && !readAccessToken(config)) {
      await simulateLatency(config)
      return buildResponse(config, 401, {
        success: false,
        message: '未授权，请先完成认证',
      } satisfies ApiEnvelope)
    }

    let hit: { route: DemoRoute; params: string[] } | null = null
    for (const route of routes) {
      if (route.method !== method) continue
      const matched = path.match(route.pattern)
      if (matched) {
        hit = { route, params: matched.slice(1) }
        break
      }
    }

    // 未匹配：不发真实请求，显式返回未模拟提示，便于发现遗漏的接口
    if (!hit) {
      console.warn(`[demo] 未模拟接口：${method.toUpperCase()} ${path}`)
      await simulateLatency(config)
      return buildResponse(config, 200, {
        success: false,
        message: `演示模式：该接口暂未模拟（${method.toUpperCase()} ${path}）`,
      } satisfies ApiEnvelope)
    }

    await simulateLatency(config)
    const ctx: RouteContext = {
      method,
      path,
      params: hit.params,
      body: parseBody(config.data),
      config,
    }
    const result = hit.route.handler(ctx)
    return buildResponse(config, result.status ?? 200, result.envelope)
  }
}
