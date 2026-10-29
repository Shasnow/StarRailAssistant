// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import zh from '../../locales/langs/zh-CN.json'
import en from '../../locales/langs/en-US.json'
import ru from '../../locales/langs/ru-RU.json'

beforeEach(() => {
  localStorage.clear()
  vi.unstubAllGlobals()
  vi.resetModules()
})

/** 消息资源按命名空间嵌套，这里拍平成 `namespace.key` 便于逐键比对 */
function flatten(obj: Record<string, unknown>, prefix = ''): Record<string, string> {
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k
    if (v !== null && typeof v === 'object') Object.assign(out, flatten(v as Record<string, unknown>, key))
    else out[key] = String(v)
  }
  return out
}

describe('Russian localization', () => {
  it('has the same keys and placeholders in all web resources', () => {
    const flatZh = flatten(zh)
    const flatEn = flatten(en)
    const flatRu = flatten(ru)
    expect(Object.keys(flatRu).sort()).toEqual(Object.keys(flatZh).sort())
    expect(Object.keys(flatEn).sort()).toEqual(Object.keys(flatZh).sort())
    const placeholders = (text: string) => [...text.matchAll(/\{\d+\}/g)].map(m => m[0]).sort()
    for (const key of Object.keys(flatZh)) {
      expect(placeholders(flatRu[key] ?? '')).toEqual(placeholders(flatZh[key] ?? ''))
      expect(placeholders(flatEn[key] ?? '')).toEqual(placeholders(flatZh[key] ?? ''))
    }
  })

  it('loads the saved Russian locale on a fresh module instance', async () => {
    localStorage.setItem('sra_locale', 'ru-RU')
    const { i18n, tr } = await import('../../locales/index')
    expect(i18n.global.locale.value).toBe('ru-RU')
    expect(document.documentElement.lang).toBe('ru-RU')
    expect(i18n.global.t('route.settings')).toBe('Настройки')
    expect(i18n.global.t('log.copiedCount', [12])).toBe('Скопировано записей: 12')
    expect(tr('开拓者名称')).toBe('Имя Первопроходца')
    expect(tr('CurrencyWarsPlus')).toBe('CurrencyWarsPlus')
    expect(localStorage.getItem('sra_locale')).toBe('ru-RU')
  })

  it('retains Chinese by default and provides English static text', async () => {
    const { i18n } = await import('../../locales/index')
    expect(i18n.global.t('route.settings')).toBe('设置')
    i18n.global.locale.value = 'en-US'
    expect(i18n.global.t('route.settings')).toBe('Settings')
  })

  it('persists the selected locale and reapplies it after reload', async () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { assign })
    const { setLocale } = await import('../../locales/index')
    setLocale('ru-RU')
    expect(localStorage.getItem('sra_locale')).toBe('ru-RU')
    expect(assign).toHaveBeenCalledWith(import.meta.env.BASE_URL)
    vi.resetModules()
    const restarted = await import('../../locales/index')
    expect(restarted.i18n.global.locale.value).toBe('ru-RU')
    expect(restarted.i18n.global.t('route.settings')).toBe('Настройки')
    setLocale('invalid')
    expect(localStorage.getItem('sra_locale')).toBe('ru-RU')
  })

  it('translates labels without replacing technical or user values', async () => {
    localStorage.setItem('sra_locale', 'ru-RU')
    const { tr } = await import('../../locales/index')
    expect(tr('开拓者名称')).toBe('Имя Первопроходца')
    expect(tr('himeko_level5_quality_level7_two_star_20261018')).toBe(
      'himeko_level5_quality_level7_two_star_20261018',
    )
    expect(tr('Тестовый профиль')).toBe('Тестовый профиль')
  })
})