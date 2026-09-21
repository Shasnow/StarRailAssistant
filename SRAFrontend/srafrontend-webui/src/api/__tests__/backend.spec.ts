import { beforeEach, describe, expect, it, vi } from 'vitest'
import { restartBackend, stopBackend } from '../backend'
import { requestEnvelope } from '../http'

// mock 掉 http 层：验证 URL / method 与结果解包
vi.mock('../http', () => ({ requestEnvelope: vi.fn() }))
const mockedRequestEnvelope = vi.mocked(requestEnvelope)

beforeEach(() => {
  mockedRequestEnvelope.mockReset()
})

describe('/api/Backend 服务模块', () => {
  it('restartBackend → POST /Backend/restart，返回 message', async () => {
    mockedRequestEnvelope.mockResolvedValueOnce({ success: true, message: '重启指令已发送' })
    const signal = new AbortController().signal
    await expect(restartBackend(signal)).resolves.toBe('重启指令已发送')
    expect(mockedRequestEnvelope).toHaveBeenCalledWith({
      url: '/Backend/restart',
      method: 'post',
      signal,
    })
  })

  it('stopBackend → POST /Backend/stop，返回 message', async () => {
    mockedRequestEnvelope.mockResolvedValueOnce({ success: true, message: '已停止' })
    await expect(stopBackend()).resolves.toBe('已停止')
    expect(mockedRequestEnvelope).toHaveBeenCalledWith({
      url: '/Backend/stop',
      method: 'post',
      signal: undefined,
    })
  })

  it('失败时透传 requestEnvelope 抛出的 ApiError', async () => {
    mockedRequestEnvelope.mockRejectedValueOnce(new Error('服务器内部错误'))
    await expect(restartBackend()).rejects.toThrow('服务器内部错误')
  })
})
