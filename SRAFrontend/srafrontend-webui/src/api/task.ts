import request from './request'
import type { SraStatus, TpTaskDefinition } from '@/types'

export function getHealth() {
  return request.get<SraStatus>('/Task/status')
}

export function getTaskDefinitions() {
  return request.get<TpTaskDefinition[]>('/Metadata/trailblaze-power/tasks')
}

export function getLogs(count: number) {
  return request.get<string[]>(`/Task/logs?count=${count}`)
}

export function runTask(configName: string | null) {
  return request.post('/Task/run', { configName })
}

export function stopTask() {
  return request.post('/Task/stop')
}
