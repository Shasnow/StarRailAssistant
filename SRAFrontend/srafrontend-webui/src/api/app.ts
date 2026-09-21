import { request } from './http'

/**
 * /api/App 服务模块：
 * - GET /api/App/system-info  后端运行时信息（.NET Environment 元数据）
 *
 * 失败时抛出 ApiError，支持通过 AbortSignal 取消。
 */

/** 后端运行时信息（字段名与后端 data 结构保持一致，不做重命名） */
export interface AppSystemInfo {
  /** 应用版本（AppSettings.Version） */
  version: string
  /** 操作系统版本 */
  osVersion: string
  /** 进程架构（x64 / x86） */
  architecture: string
  /** .NET 运行时版本（Environment.Version.ToString()） */
  dotnetVersion: string
  /** 处理器逻辑核心数（Environment.ProcessorCount） */
  processorCount: number
  /** 当前区域文化（CultureInfo.CurrentCulture.Name） */
  cultureInfo: string
}

/** 获取后端运行时信息 */
export async function fetchSystemInfo(signal?: AbortSignal): Promise<AppSystemInfo> {
  return request<AppSystemInfo>({ url: '/App/system-info', method: 'get', signal })
}

export async function fetchPhrases(signal?: AbortSignal): Promise<string[]> {
  return request<string[]>({ url: '/App/phrases', method: 'get', signal })
}
