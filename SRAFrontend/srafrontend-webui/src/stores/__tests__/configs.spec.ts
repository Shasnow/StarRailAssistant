// @vitest-environment jsdom
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as configsApi from '@/api/configs'
import { useConfigsStore } from '../configs'

// mock 掉 /api/Configs 服务层：store 测试只关注状态管理逻辑
vi.mock('@/api/configs', () => ({
  listConfigs: vi.fn(),
  getConfig: vi.fn(),
  createConfig: vi.fn(),
  updateConfig: vi.fn(),
  removeConfig: vi.fn(),
}))
const mockedApi = vi.mocked(configsApi)

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

describe('configs store - 列表', () => {
  it('fetchNames 成功：填充 names 并清除 loading/error', async () => {
    mockedApi.listConfigs.mockResolvedValue(['a', 'b'])
    const s = useConfigsStore()
    await s.fetchNames()
    expect(s.names).toEqual(['a', 'b'])
    expect(s.namesLoading).toBe(false)
    expect(s.namesError).toBe('')
    expect(s.configCount).toBe(2)
    expect(s.isNamesLoaded).toBe(true)
  })

  it('fetchNames 失败：写入 namesError，loading 复位', async () => {
    mockedApi.listConfigs.mockRejectedValue(new Error('网络异常'))
    const s = useConfigsStore()
    await s.fetchNames()
    expect(s.namesError).toBe('网络异常')
    expect(s.namesLoading).toBe(false)
    expect(s.isNamesLoaded).toBe(false)
  })
})

describe('configs store - 当前配置', () => {
  it('loadConfig 记录 currentName/currentConfig 并返回负载', async () => {
    mockedApi.getConfig.mockResolvedValue({ startGame: { enabled: true } })
    const s = useConfigsStore()
    const data = await s.loadConfig('默认配置')
    expect(data).toEqual({ startGame: { enabled: true } })
    expect(s.currentName).toBe('默认配置')
    expect(s.currentConfig).toEqual({ startGame: { enabled: true } })
    expect(s.hasCurrent).toBe(true)
    expect(s.detailLoading).toBe(false)
  })

  it('loadConfig 失败：写入 detailError 并抛出原始错误', async () => {
    mockedApi.getConfig.mockRejectedValue(new Error('资源不存在'))
    const s = useConfigsStore()
    await expect(s.loadConfig('不存在')).rejects.toThrow('资源不存在')
    expect(s.detailError).toBe('资源不存在')
    expect(s.detailLoading).toBe(false)
  })

  it('selectName 仅切换选中名', () => {
    const s = useConfigsStore()
    s.selectName('x')
    expect(s.currentName).toBe('x')
    expect(mockedApi.getConfig).not.toHaveBeenCalled()
  })

  it('normalizeSelection：无效选中回退到第一个，列表为空则清空', async () => {
    mockedApi.listConfigs.mockResolvedValue(['a', 'b'])
    const s = useConfigsStore()
    s.selectName('不存在的')
    await s.fetchNames()
    s.normalizeSelection()
    expect(s.currentName).toBe('a')

    mockedApi.listConfigs.mockResolvedValue([])
    await s.fetchNames()
    s.normalizeSelection()
    expect(s.currentName).toBe('')
  })
})

describe('configs store - 写操作', () => {
  it('saveConfig 成功：返回 true 并同步 currentConfig', async () => {
    mockedApi.updateConfig.mockResolvedValue('更新成功')
    const s = useConfigsStore()
    s.selectName('a')
    s.currentConfig = { old: true }
    const payload = { startGame: { enabled: false } }
    await expect(s.saveConfig('a', payload)).resolves.toBe(true)
    expect(mockedApi.updateConfig).toHaveBeenCalledWith('a', payload)
    expect(s.currentConfig).toEqual(payload)
    expect(s.saving).toBe(false)
    expect(s.saveError).toBe('')
  })

  it('saveConfig 失败：返回 false 并写入 saveError', async () => {
    mockedApi.updateConfig.mockRejectedValue(new Error('校验失败'))
    const s = useConfigsStore()
    await expect(s.saveConfig('a', {})).resolves.toBe(false)
    expect(s.saveError).toBe('校验失败')
    expect(s.saving).toBe(false)
  })

  it('createConfig 成功后刷新配置名列表', async () => {
    mockedApi.createConfig.mockResolvedValue('新建成功')
    mockedApi.listConfigs.mockResolvedValue(['新配置'])
    const s = useConfigsStore()
    await expect(s.createConfig('新配置')).resolves.toBe(true)
    expect(mockedApi.createConfig).toHaveBeenCalledWith('新配置')
    expect(mockedApi.listConfigs).toHaveBeenCalledTimes(1)
    expect(s.names).toEqual(['新配置'])
  })

  it('removeConfig 删除当前配置时清空选中并刷新列表', async () => {
    mockedApi.removeConfig.mockResolvedValue('删除成功')
    mockedApi.listConfigs.mockResolvedValue(['b'])
    const s = useConfigsStore()
    s.selectName('a')
    s.currentConfig = { x: 1 }
    await expect(s.removeConfig('a')).resolves.toBe(true)
    expect(s.currentName).toBe('')
    expect(s.currentConfig).toBeNull()
    expect(s.names).toEqual(['b'])
  })
})

describe('configs store - 持久化', () => {
  it('选中名写入 localStorage（sra_last_config）', async () => {
    const s = useConfigsStore()
    s.selectName('持久化的配置')
    await nextTick()
    expect(localStorage.getItem('sra_last_config')).toContain('持久化的配置')
  })

  it('新建 store 时从 localStorage 恢复选中名', () => {
    localStorage.setItem('sra_last_config', '上次选的')
    const s = useConfigsStore()
    expect(s.currentName).toBe('上次选的')
  })
})
