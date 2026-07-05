export type SettingsModel = {
  general: Record<string, any>
  advanced: Record<string, any>
  notification: Record<string, any>
  warpForecast: Record<string, any>
  display?: Record<string, any>
  update?: Record<string, any>
  [key: string]: any
}
