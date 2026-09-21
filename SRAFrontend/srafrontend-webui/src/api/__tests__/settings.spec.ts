import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchSettings, updateSettings } from '../settings'
import { request, requestEnvelope } from '../http'

// mock 掉 http 层：验证 URL / method / data 与结果解包
vi.mock('../http', () => ({
  request: vi.fn(),
  requestEnvelope: vi.fn(),
}))
const mockedRequest = vi.mocked(request)
const mockedRequestEnvelope = vi.mocked(requestEnvelope)

beforeEach(() => {
  mockedRequest.mockReset()
  mockedRequestEnvelope.mockReset()
})

describe('/api/Settings 服务模块', () => {
  it('fetchSettings → GET /Settings，返回按 section 分组的设置', async () => {
    const payload = {
      general: { 'gamePath.index': 0 },
      advanced: { 'backend.remote.enabled': true },
    }
    mockedRequest.mockResolvedValueOnce(payload)
    const signal = new AbortController().signal
    await expect(fetchSettings(signal)).resolves.toEqual(payload)
    expect(mockedRequest).toHaveBeenCalledWith({ url: '/Settings', method: 'get', signal })
  })

  it('fetchSettings：data 非对象时按空设置处理', async () => {
    mockedRequest.mockResolvedValueOnce(null)
    await expect(fetchSettings()).resolves.toEqual({})
  })

  it('updateSettings → PUT /Settings，提交部分 JSON 并返回已更新字段列表', async () => {
    mockedRequestEnvelope.mockResolvedValueOnce({
      success: true,
      message: 'ok',
      data: ['advanced.backend.remote.enabled', 'general.gamePath.index'],
    })
    const partial = { advanced: { 'backend.remote.enabled': true } }
    await expect(updateSettings(partial)).resolves.toEqual([
      'advanced.backend.remote.enabled',
      'general.gamePath.index',
    ])
    expect(mockedRequestEnvelope).toHaveBeenCalledWith({
      url: '/Settings',
      method: 'put',
      data: partial,
      signal: undefined,
    })
  })

  it('updateSettings：data 非数组时返回空列表', async () => {
    mockedRequestEnvelope.mockResolvedValueOnce({ success: true, message: 'ok', data: null })
    await expect(updateSettings({})).resolves.toEqual([])
  })

  it('失败时透传 ApiError', async () => {
    mockedRequestEnvelope.mockRejectedValueOnce(new Error('请求参数无效'))
    await expect(updateSettings({ advanced: {} })).rejects.toThrow('请求参数无效')
  })
})
