import { request } from './http'

/**
 * /api/Configs 服务模块（对应 OpenAPI ConfigsController）：
 * - GET    /api/Configs              → R<string[]>      所有配置名
 * - GET    /api/Configs/{name}       → R<TasksConfig>   读取配置（404 不存在）
 * - POST   /api/Configs/{name}       → R<string>        新建（400 非法字符 / 409 已存在）
 * - PUT    /api/Configs/{name}       → R<string>        更新（404 不存在）
 * - DELETE /api/Configs/{name}       → R<string>        删除（404 不存在）
 *
 * 所有方法在失败时抛出 ApiError，支持通过 AbortSignal 取消。
 */

/** TasksConfig 负载：由 OpenAPI schema 动态表单生成，字段结构以后端为准 */
export type TasksConfigPayload = Record<string, unknown>

/** 获取所有配置名称 */
export function listConfigs(signal?: AbortSignal): Promise<string[]> {
  return request<string[]>({ url: '/Configs', method: 'get', signal })
}

/** 读取指定配置；不存在时后端返回 404（抛 ApiError），空配置返回 null */
export function getConfig(name: string, signal?: AbortSignal): Promise<TasksConfigPayload | null> {
  return request<TasksConfigPayload | null>({
    url: `/Configs/${encodeURIComponent(name)}`,
    method: 'get',
    signal,
  })
}

/** 新建配置，返回后端提示信息 */
export function createConfig(name: string, signal?: AbortSignal): Promise<string> {
  return request<string>({
    url: `/Configs/${encodeURIComponent(name)}`,
    method: 'post',
    signal,
  })
}

/** 更新配置内容，返回后端提示信息 */
export function updateConfig(
  name: string,
  data: TasksConfigPayload,
  signal?: AbortSignal,
): Promise<string> {
  return request<string>({
    url: `/Configs/${encodeURIComponent(name)}`,
    method: 'put',
    data,
    signal,
  })
}

/** 删除配置，返回后端提示信息 */
export function removeConfig(name: string, signal?: AbortSignal): Promise<string> {
  return request<string>({
    url: `/Configs/${encodeURIComponent(name)}`,
    method: 'delete',
    signal,
  })
}
