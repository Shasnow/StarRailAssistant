import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchTaskStatus, IDLE_TASK_STATUS, normalizeTaskStatus, runTask, stopTask } from '../task'
import { http, requestEnvelope } from '../http'

// mock 掉 http 层：验证 URL / method / data / rawEnvelope 与结果解包
vi.mock('../http', () => ({
  http: { request: vi.fn() },
  requestEnvelope: vi.fn(),
}))
const mockedRequestEnvelope = vi.mocked(requestEnvelope)
const mockedHttpRequest = vi.mocked(http.request)

beforeEach(() => {
  mockedRequestEnvelope.mockReset()
  mockedHttpRequest.mockReset()
})

/** 后端 RuntimeInfo 的 running 样例（字段名与 JSON 序列化一致） */
const RUNNING_INFO = {
  session_id: 'abc123',
  pid: 1234,
  mode: 'cli',
  status: 'running',
  configs: ['默认配置', '每日'],
  unit: '任务1',
  error: '',
  progress: [3, 10],
}

describe('/api/Task 服务模块', () => {
  it('runTask → POST /Task/run，携带 configName，返回 message', async () => {
    mockedRequestEnvelope.mockResolvedValueOnce({ success: true, message: '任务已启动' })
    const signal = new AbortController().signal
    await expect(runTask({ configName: '默认配置' }, signal)).resolves.toBe('任务已启动')
    expect(mockedRequestEnvelope).toHaveBeenCalledWith({
      url: '/Task/run',
      method: 'post',
      data: { configName: '默认配置' },
      signal,
    })
  })

  it('stopTask → POST /Task/stop，返回 message', async () => {
    mockedRequestEnvelope.mockResolvedValueOnce({ success: true, message: '已停止' })
    await expect(stopTask()).resolves.toBe('已停止')
    expect(mockedRequestEnvelope).toHaveBeenCalledWith({
      url: '/Task/stop',
      method: 'post',
      signal: undefined,
    })
  })

  it('fetchTaskStatus → GET /Task/status，rawEnvelope 跳过统一抛错', async () => {
    mockedHttpRequest.mockResolvedValueOnce({
      data: { success: true, message: 'ok', data: RUNNING_INFO },
    })
    await expect(fetchTaskStatus()).resolves.toEqual({
      session_id: 'abc123',
      pid: 1234,
      mode: 'cli',
      status: 'running',
      configs: ['默认配置', '每日'],
      unit: '任务1',
      error: '',
      progress: [3, 10],
    })
    expect(mockedHttpRequest).toHaveBeenCalledWith({
      url: '/Task/status',
      method: 'get',
      signal: undefined,
      rawEnvelope: true,
    })
  })

  it('fetchTaskStatus：success=false（后端空闲无响应）视为空闲', async () => {
    mockedHttpRequest.mockResolvedValueOnce({
      data: { success: false, message: 'No response from backend', data: null },
    })
    await expect(fetchTaskStatus()).resolves.toEqual(IDLE_TASK_STATUS)
  })

  it('fetchTaskStatus：data 为 null 视为空闲', async () => {
    mockedHttpRequest.mockResolvedValueOnce({ data: { success: true, message: 'ok', data: null } })
    await expect(fetchTaskStatus()).resolves.toEqual(IDLE_TASK_STATUS)
  })

  it('fetchTaskStatus：HTTP 错误照常抛出', async () => {
    mockedHttpRequest.mockRejectedValueOnce(new Error('服务器内部错误'))
    await expect(fetchTaskStatus()).rejects.toThrow('服务器内部错误')
  })
})

describe('normalizeTaskStatus 形状兜底（字段名与后端 RuntimeInfo 一致）', () => {
  it('非对象数据返回空闲默认值', () => {
    expect(normalizeTaskStatus(null)).toEqual(IDLE_TASK_STATUS)
    expect(normalizeTaskStatus('x')).toEqual(IDLE_TASK_STATUS)
  })

  it('合法 RuntimeInfo 原样保留字段值', () => {
    expect(normalizeTaskStatus(RUNNING_INFO)).toEqual({
      session_id: 'abc123',
      pid: 1234,
      mode: 'cli',
      status: 'running',
      configs: ['默认配置', '每日'],
      unit: '任务1',
      error: '',
      progress: [3, 10],
    })
  })

  it('非法 / 缺失字段回退默认值', () => {
    expect(
      normalizeTaskStatus({
        session_id: 42,
        pid: 'abc',
        mode: '',
        status: 'whatever',
        configs: 'not-array',
        unit: null,
        progress: [7],
      }),
    ).toEqual({
      session_id: '',
      pid: 0,
      mode: 'unknown',
      status: 'idle',
      configs: [],
      unit: '',
      error: '',
      progress: [0, 0],
    })
  })

  it('progress 元素非法时按 0 处理', () => {
    expect(normalizeTaskStatus({ status: 'running', progress: ['a', 10] }).progress).toEqual([
      0, 10,
    ])
    expect(normalizeTaskStatus({ status: 'running', progress: null }).progress).toEqual([0, 0])
  })
})
