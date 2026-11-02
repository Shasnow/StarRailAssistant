import { createI18n } from 'vue-i18n'
import zh from './langs/zh-CN.json'
import en from './langs/en-US.json'
import ru from './langs/ru-RU.json'

export type Locale = 'zh-CN' | 'en-US' | 'ru-RU'

/** 语言展示名：用各自母语书写，不随界面语言变化 */
const LOCALE_LABELS: Record<Locale, string> = {
  'zh-CN': '简体中文',
  'en-US': 'English',
  'ru-RU': 'Русский',
}

/** 支持的语言清单（派生自 LOCALE_LABELS，作为唯一事实来源） */
const LOCALES = Object.keys(LOCALE_LABELS) as Locale[]

/** 语言选择器选项：由语言清单自动生成 */
export const SUPPORTED_LOCALES = LOCALES.map((value) => ({ value, label: LOCALE_LABELS[value] }))

function savedLocale(): string | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage.getItem('sra_locale')
  } catch {
    return null
  }
}

const saved = savedLocale()
const initialLocale: Locale =
  saved !== null && LOCALES.includes(saved as Locale) ? (saved as Locale) : 'zh-CN'

/**
 * vue-i18n 实例：消息资源按命名空间嵌套（如 `route.settings`），模板用 `$t` /
 * `<script setup>` 用 `useI18n()` 的 `t`。纯 TS 模块（api / utils / composables / router）
 * 通过 `i18n.global.t` 取值。
 */
export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: initialLocale,
  fallbackLocale: 'zh-CN',
  messages: { 'zh-CN': zh, 'en-US': en, 'ru-RU': ru },
})

export function setLocale(value: string) {
  if (!LOCALES.includes(value as Locale)) return
  localStorage.setItem('sra_locale', value)
  // Recreate setup-time option labels and third-party dialogs consistently.
  // Upstream does not provide an ASP.NET SPA deep-link fallback. Restart at
  // the supported base entry instead of requesting /settings or /logs as HTML.
  location.assign(import.meta.env.BASE_URL)
}

if (typeof document !== 'undefined') document.documentElement.lang = i18n.global.locale.value