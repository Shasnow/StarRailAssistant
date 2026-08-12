export type SraStatus = {
  running: boolean
  pid?: number | null
  executablePath?: string
  port?: number
  detail?: string
  mode?: string
  configs?: string[]
  session_id?: string
  unit?: string
  status?: string
  error?: string
  progress?: [number, number]
}

export type HealthInfo = {
  ok: boolean
  sra?: SraStatus
}

export type PageMeta = {
  title: string
  description: string
  label: string
}
