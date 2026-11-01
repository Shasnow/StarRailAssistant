import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  activateGameWindow,
  callOperator,
  isGameWindowActive,
  sendInputEvent,
  type InputEvent,
} from '../operator'
import { ApiError, request } from '../http'

// 只 mock 网络请求函数，保留 ApiError 等实现
vi.mock('../http', async () => {
  const actual = await vi.importActual<typeof import('../http')>('../http')
  return { ...actual, request: vi.fn() }
})
const mockedRequest = vi.mocked(request)

beforeEach(() => {
  mockedRequest.mockReset()
})

describe('callOperator', () => {
  it('POST /operator/call 并透传 method/params', async () => {
    mockedRequest.mockResolvedValueOnce(true)
    const signal = new AbortController().signal

    await expect(callOperator('key_down', { key: 'w', trace: false }, signal)).resolves.toBe(true)
    expect(mockedRequest).toHaveBeenCalledWith({
      url: '/operator/call',
      method: 'post',
      data: { method: 'key_down', params: { key: 'w', trace: false } },
      signal,
    })
  })

  it('方法返回 false 时抛出 ApiError', async () => {
    mockedRequest.mockResolvedValueOnce(false)
    await expect(callOperator('key_down', { key: 'w' })).rejects.toBeInstanceOf(ApiError)
  })
})

describe('sendInputEvent', () => {
  const cases: Array<[InputEvent, string, Record<string, unknown>]> = [
    [{ type: 'move', x: 0.25, y: 0.75 }, 'move_to', { x: 0.25, y: 0.75, trace: false }],
    [
      { type: 'down', x: 0.5, y: 0.5, button: 'right' },
      'mouse_down',
      { x: 0.5, y: 0.5, button: 'right', trace: false },
    ],
    [{ type: 'up', button: 'right' }, 'mouse_up', { button: 'right', trace: false }],
    [{ type: 'wheel', clicks: -2 }, 'scroll', { clicks: -2, trace: false }],
    [{ type: 'key_down', key: 'w' }, 'key_down', { key: 'w', trace: false }],
    [{ type: 'key_up', key: 'w' }, 'key_up', { key: 'w', trace: false }],
    [{ type: 'key_press', key: 'esc', presses: 2 }, 'press_key', { key: 'esc', presses: 2, trace: false }],
  ]

  it.each(cases)('输入事件映射为 Operator 方法', async (event, method, params) => {
    mockedRequest.mockResolvedValueOnce(true)
    await sendInputEvent(event)
    expect(mockedRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        url: '/operator/call',
        method: 'post',
        data: { method, params },
      }),
    )
  })
})

describe('窗口检测与激活', () => {
  it('isGameWindowActive 仅在 data === true 时为 true', async () => {
    mockedRequest.mockResolvedValueOnce(true)
    await expect(isGameWindowActive()).resolves.toBe(true)

    mockedRequest.mockResolvedValueOnce(false)
    await expect(isGameWindowActive()).resolves.toBe(false)

    mockedRequest.mockResolvedValueOnce(null)
    await expect(isGameWindowActive()).resolves.toBe(false)
  })

  it('activateGameWindow 调用 active_window', async () => {
    mockedRequest.mockResolvedValueOnce(true)
    await activateGameWindow()
    expect(mockedRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        data: { method: 'active_window', params: {} },
      }),
    )
  })
})
