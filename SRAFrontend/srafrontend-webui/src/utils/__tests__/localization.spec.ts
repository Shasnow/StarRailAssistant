// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import zh from '../../locales/zh-CN.json'
import en from '../../locales/en-US.json'
import ru from '../../locales/ru-RU.json'

beforeEach(() => {
  localStorage.clear()
  vi.unstubAllGlobals()
  vi.resetModules()
})

describe('Russian localization', () => {
  it('has the same keys and placeholders in all web resources', () => {
    expect(Object.keys(ru).sort()).toEqual(Object.keys(zh).sort())
    expect(Object.keys(en).sort()).toEqual(Object.keys(zh).sort())
    for (const key of Object.keys(zh) as (keyof typeof zh)[]) {
      const placeholders = (text: string) => [...text.matchAll(/\{\d+\}/g)].map(m => m[0]).sort()
      expect(placeholders(ru[key])).toEqual(placeholders(zh[key]))
      expect(placeholders(en[key])).toEqual(placeholders(zh[key]))
    }
  })

  it('loads the saved Russian locale on a fresh module instance', async () => {
    localStorage.setItem('sra_locale', 'ru-RU')
    const { locale, t, tf, tr } = await import('../../i18n')
    expect(locale.value).toBe('ru-RU')
    expect(document.documentElement.lang).toBe('ru-RU')
    expect(t('W0112')).toBe('Настройки')
    expect(tf('W0151', 12)).toBe('Скопировано записей: 12')
    expect(tr('开拓者名称')).toBe('Имя Первопроходца')
    expect(tr('CurrencyWarsPlus')).toBe('CurrencyWarsPlus')
    expect(localStorage.getItem('sra_locale')).toBe('ru-RU')
  })

  it('retains Chinese by default and provides English static text', async () => {
    const { locale, t } = await import('../../i18n')
    expect(t('W0112')).toBe('设置')
    locale.value = 'en-US'
    expect(t('W0112')).toBe('Settings')
  })

  it('persists the selected locale and reapplies it after reload', async () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { assign })
    const { setLocale } = await import('../../i18n')
    setLocale('ru-RU')
    expect(localStorage.getItem('sra_locale')).toBe('ru-RU')
    expect(assign).toHaveBeenCalledWith(import.meta.env.BASE_URL)
    vi.resetModules()
    const restarted = await import('../../i18n')
    expect(restarted.locale.value).toBe('ru-RU')
    expect(restarted.t('W0112')).toBe('Настройки')
    setLocale('invalid')
    expect(localStorage.getItem('sra_locale')).toBe('ru-RU')
  })

  it('translates labels without replacing technical or user values', async () => {
    localStorage.setItem('sra_locale', 'ru-RU')
    const { tr } = await import('../../i18n')
    expect(tr('开拓者名称')).toBe('Имя Первопроходца')
    expect(tr('himeko_level5_quality_level7_two_star_20261018')).toBe(
      'himeko_level5_quality_level7_two_star_20261018',
    )
    expect(tr('Тестовый профиль')).toBe('Тестовый профиль')
  })
})
