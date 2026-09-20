import axios, { type AxiosRequestConfig, type AxiosInstance } from 'axios'

// axios 扩展：
// - rawEnvelope：跳过「success=false 抛错」的统一处理，
//   供需要自行解读 R 包装的接口使用（如 /api/Task/status 空闲时返回 success=false）
// - skipAuthHeader：不附加 X-Access-Token 请求头，
//   供认证探测/校验接口使用（登录页提交新 token 时，本地遗留的旧 token 会先于请求体被后端校验）
declare module 'axios' {
  export interface AxiosRequestConfig {
    rawEnvelope?: boolean
    skipAuthHeader?: boolean
  }
}

/** 后端统一响应包装 R<T>（.NET 侧 { success, message, data }） */
export interface ApiEnvelope<T = unknown> {
  success: boolean
  message: string
  data?: T
}

/** 统一 API 错误：携带 HTTP 状态码与后端返回的 message */
export class ApiError extends Error {
  readonly status?: number
  /** 请求被主动取消（AbortSignal / 取消令牌），调用方可静默处理 */
  readonly canceled: boolean

  constructor(message: string, status?: number, canceled = false) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.canceled = canceled
  }
}

/** 判断错误是否为「请求被取消」，此类错误不应展示给用户 */
export function isCanceledError(err: unknown): boolean {
  return err instanceof ApiError && err.canceled
}

/* ---------- 认证 token 存取 ---------- */

const TOKEN_STORAGE_KEY = 'sra_token'

/**
 * 读取本地保存的 access token。
 * 存储在 localStorage（同源脚本可读，属于前端能提供的最高持久性方案），
 * 后端未启用认证时为空串，此时所有请求都不附加认证头。
 */
export function getStoredToken(): string {
  return localStorage.getItem(TOKEN_STORAGE_KEY) ?? ''
}

/** 登录校验通过后写入本地 token */
export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

/** 清除本地 token（退出登录 / token 失效时调用） */
export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

/* ---------- 全局 401 回调 ---------- */

/** 会话中途认证失效时的回调（由 router 注册：清理 token 并跳回登录页） */
let unauthorizedHandler: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler
}

/* ---------- 错误归一化 ---------- */

/** 无后端错误信息时按状态码给出的默认提示 */
export function statusMessage(status: number): string {
  switch (status) {
    case 400:
      return '请求参数无效'
    case 401:
      return '未授权，请先完成认证'
    case 403:
      return '没有访问权限'
    case 404:
      return '资源不存在'
    case 409:
      return '资源已存在或状态冲突'
    case 422:
      return '请求校验失败'
    case 500:
      return '服务器内部错误'
    case 502:
    case 503:
    case 504:
      return '服务暂不可用，请稍后重试'
    default:
      return `请求失败（HTTP ${status}）`
  }
}

/**
 * 将任意抛出的错误归一化为 ApiError：
 * - R 包装失败（success=false，HTTP 200）→ 取后端 message
 * - HTTP 错误（ProblemDetails 或 R 包装）→ 取 message/title/detail，否则按状态码兜底
 * - 超时 / 网络异常 / 取消 → 对应固定提示
 */
function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err

  if (axios.isAxiosError(err)) {
    if (err.code === 'ERR_CANCELED') return new ApiError('请求已取消', undefined, true)
    if (err.code === 'ECONNABORTED')
      return new ApiError('请求超时，请检查后端服务是否可用', err.response?.status)
    if (!err.response) return new ApiError('网络异常，无法连接到后端服务')

    const status = err.response.status
    const body: unknown = err.response.data
    const remote =
      typeof body === 'object' && body !== null
        ? ((body as Partial<ApiEnvelope>).message ??
          (body as { detail?: string }).detail ??
          (body as { title?: string }).title)
        : undefined
    return new ApiError(remote || statusMessage(status), status)
  }

  return new ApiError(err instanceof Error ? err.message : String(err))
}

/* ---------- 客户端工厂 ---------- */

export function createHttpClient(): AxiosInstance {
  const client = axios.create({
    // 走 vite 代理（/api → http://localhost:5073），生产环境由反代接管
    baseURL: '/api',
    timeout: 15_000,
  })

  // 请求拦截：附加认证 token（后端启用认证时 /api/Auth 校验通过后保存），
  // 所有业务请求自动携带 X-Access-Token；探测/校验接口用 skipAuthHeader 排除
  client.interceptors.request.use((config) => {
    const token = getStoredToken()
    if (token && !config.skipAuthHeader) config.headers['X-Access-Token'] = token
    return config
  })

  // 响应拦截：R 包装 success=false 视为业务失败（rawEnvelope 标记的请求除外）；
  // 所有错误统一归一化为 ApiError
  client.interceptors.response.use(
    (response) => {
      const body = response.data as ApiEnvelope | undefined
      if (
        !response.config.rawEnvelope &&
        body &&
        typeof body === 'object' &&
        typeof body.success === 'boolean' &&
        !body.success
      ) {
        throw new ApiError(body.message || '请求失败', response.status)
      }
      return response
    },
    (error) => {
      const apiError = toApiError(error)
      // 会话中途返回 401（token 失效/被更换）：通知上层清理 token 并跳回登录页。
      // 探测与登录校验用 validateStatus 放行，不会进入错误分支
      if (apiError.status === 401) unauthorizedHandler?.()
      return Promise.reject(apiError)
    },
  )

  return client
}

/** 全局共享实例 */
export const http = createHttpClient()

/**
 * 发起请求并解包 R<T>，返回 data 字段。
 * - 取消：调用方通过 config.signal 传入 AbortSignal
 * - 失败（HTTP 非 2xx 或 success=false）：抛出 ApiError
 */
export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await http.request<ApiEnvelope<T>>(config)
  return response.data.data as T
}

/**
 * 发起请求并返回完整 R 包装（不解包 data），success=false 仍由拦截器抛错。
 * 需要读取后端 message 或自行处理 data 的接口使用；
 * 传入 rawEnvelope: true 可跳过 success=false 抛错，自行解读原始包装。
 */
export async function requestEnvelope(config: AxiosRequestConfig): Promise<ApiEnvelope> {
  const response = await http.request<ApiEnvelope>(config)
  return response.data
}
