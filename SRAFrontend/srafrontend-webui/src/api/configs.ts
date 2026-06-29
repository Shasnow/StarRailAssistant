import request from './request'

export function getConfigNames() {
  return request.get<string[]>('/Configs')
}

export function getConfigDetail(name: string) {
  return request.get<unknown>(`/Configs/${encodeURIComponent(name)}`)
}

export function createConfig(name: string) {
  return request.post(`/Configs/${encodeURIComponent(name)}`)
}

export function saveConfig(name: string, body: unknown) {
  return request.put(`/Configs/${encodeURIComponent(name)}`, body)
}
