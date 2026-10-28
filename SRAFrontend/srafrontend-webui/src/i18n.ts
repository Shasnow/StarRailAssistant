import { ref } from 'vue'
import zh from './locales/zh-CN.json'
import en from './locales/en-US.json'
import ru from './locales/ru-RU.json'
import russianDisplay from './locales/display.ru-RU.json'

export type Locale = 'zh-CN' | 'en-US' | 'ru-RU'
function savedLocale(): string | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage.getItem('sra_locale')
  } catch {
    return null
  }
}
const saved = savedLocale()
export const locale = ref<Locale>(saved === 'ru-RU' || saved === 'en-US' ? saved : 'zh-CN')
const resources: Record<Locale, Record<string, string>> = { 'zh-CN': zh, 'en-US': en, 'ru-RU': ru }
const display: Record<string, string> = russianDisplay

export function t(key: string): string {
  return resources[locale.value][key] ?? key
}

export function tf(key: string, ...values: unknown[]): string {
  return t(key).replace(/\{(\d+)\}/g, (_, index: string) => String(values[Number(index)] ?? ''))
}

/** Display text only: never use this result for keys, API parameters, or saved values. */
export function tr(source: string | undefined): string {
  if (!source) return ''
  return locale.value === 'ru-RU' ? display[source] ?? source : source
}

export function setLocale(value: string) {
  if (!['zh-CN', 'en-US', 'ru-RU'].includes(value)) return
  localStorage.setItem('sra_locale', value)
  // Recreate setup-time option labels and third-party dialogs consistently.
  // Upstream does not provide an ASP.NET SPA deep-link fallback. Restart at
  // the supported base entry instead of requesting /settings or /logs as HTML.
  location.assign(import.meta.env.BASE_URL)
}

if (typeof document !== 'undefined') document.documentElement.lang = locale.value
