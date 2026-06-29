import request from './request'
import type { SettingsModel } from '@/types'

export function getSettings() {
  return request.get<SettingsModel>('/Settings')
}

export function saveSettings(body: SettingsModel) {
  return request.put('/Settings', body)
}
