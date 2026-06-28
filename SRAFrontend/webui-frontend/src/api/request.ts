import axios, { type AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'

type TokenGetter = () => string
type UnauthorizedHandler = () => void

let getToken: TokenGetter = () => ''
let onUnauthorized: UnauthorizedHandler = () => {}

export function configureRequest(opts: {
  getToken: TokenGetter
  onUnauthorized: UnauthorizedHandler
  baseURL?: string
}) {
  getToken = opts.getToken
  onUnauthorized = opts.onUnauthorized
  if (opts.baseURL !== undefined) request.defaults.baseURL = opts.baseURL
}

const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

request.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getToken()
  if (token) config.headers.set('X-Api-Key', token)
  return config
})

request.interceptors.response.use(
  (res: AxiosResponse) => res.data,
  (error: AxiosError<{ message?: string; Message?: string; errors?: Record<string, string[]>; title?: string }>) => {
    if (error.response?.status === 401) {
      onUnauthorized()
      return Promise.reject(new Error('访问令牌不正确或已失效'))
    }
    const data = error.response?.data
    const fieldErrors = data?.errors ? Object.values(data.errors).flat().join('；') : ''
    const message = data?.message ?? data?.Message ?? fieldErrors ?? data?.title ?? error.message
    return Promise.reject(new Error(message))
  }
)

export default request as unknown as {
  get<T = unknown>(url: string, config?: object): Promise<T>
  post<T = unknown>(url: string, data?: unknown, config?: object): Promise<T>
  put<T = unknown>(url: string, data?: unknown, config?: object): Promise<T>
  delete<T = unknown>(url: string, config?: object): Promise<T>
  defaults: typeof axios.defaults
}
