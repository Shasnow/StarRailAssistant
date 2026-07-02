export type SraStatus = {
  running: boolean
  pid?: number | null
  executablePath?: string
  port?: number
  detail?: string
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
