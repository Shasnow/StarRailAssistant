import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createConfig, getConfig, listConfigs, removeConfig, updateConfig } from '../configs'
import { request } from '../http'

// mock 掉 request：只验证服务层拼装的 URL / method / data / signal
vi.mock('../http', () => ({ request: vi.fn() }))
const mockedRequest = vi.mocked(request)

beforeEach(() => {
  mockedRequest.mockReset()
})

describe('/api/Configs 服务模块', () => {
  it('listConfigs → GET /Configs', async () => {
    mockedRequest.mockResolvedValueOnce(['默认配置', '每日'])
    const signal = new AbortController().signal
    await expect(listConfigs(signal)).resolves.toEqual(['默认配置', '每日'])
    expect(mockedRequest).toHaveBeenCalledWith({ url: '/Configs', method: 'get', signal })
  })

  it('getConfig → GET /Configs/{name}，名称 encodeURIComponent', async () => {
    mockedRequest.mockResolvedValueOnce(null)
    await expect(getConfig('a b/c')).resolves.toBeNull()
    expect(mockedRequest).toHaveBeenCalledWith({
      url: '/Configs/a%20b%2Fc',
      method: 'get',
      signal: undefined,
    })
  })

  it('createConfig → POST /Configs/{name}', async () => {
    mockedRequest.mockResolvedValueOnce('新建成功')
    await expect(createConfig('新配置')).resolves.toBe('新建成功')
    expect(mockedRequest).toHaveBeenCalledWith({
      url: '/Configs/%E6%96%B0%E9%85%8D%E7%BD%AE',
      method: 'post',
      signal: undefined,
    })
  })

  it('updateConfig → PUT /Configs/{name}，body 为配置负载', async () => {
    mockedRequest.mockResolvedValueOnce('更新成功')
    const payload = { startGame: { enabled: true } }
    await expect(updateConfig('默认配置', payload)).resolves.toBe('更新成功')
    expect(mockedRequest).toHaveBeenCalledWith({
      url: `/Configs/${encodeURIComponent('默认配置')}`,
      method: 'put',
      data: payload,
      signal: undefined,
    })
  })

  it('removeConfig → DELETE /Configs/{name}', async () => {
    mockedRequest.mockResolvedValueOnce('删除成功')
    await expect(removeConfig('默认配置')).resolves.toBe('删除成功')
    expect(mockedRequest).toHaveBeenCalledWith({
      url: `/Configs/${encodeURIComponent('默认配置')}`,
      method: 'delete',
      signal: undefined,
    })
  })

  it('失败时透传 request 抛出的 ApiError', async () => {
    mockedRequest.mockRejectedValueOnce(new Error('资源不存在'))
    await expect(getConfig('x')).rejects.toThrow('资源不存在')
  })
})
