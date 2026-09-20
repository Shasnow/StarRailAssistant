import { afterEach, describe, expect, it, vi } from 'vitest'
import { SCREENSHOT_URL, fetchScreenshot } from '../live'

const fetchMock = vi.fn()

afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

function mockResponse(ok: boolean, status: number, blob: Blob) {
  fetchMock.mockResolvedValue({ ok, status, blob: async () => blob })
}

describe('fetchScreenshot', () => {
  it('接口地址为 /api/backend/screenshot', () => {
    expect(SCREENSHOT_URL).toBe('/api/backend/screenshot')
  })

  it('成功时返回图片 Blob，并携带缓存穿透参数', async () => {
    vi.stubGlobal('fetch', fetchMock)
    const blob = new Blob(['png'], { type: 'image/png' })
    mockResponse(true, 200, blob)

    const result = await fetchScreenshot(undefined, 123456)

    expect(result).toBe(blob)
    expect(fetchMock).toHaveBeenCalledWith(`${SCREENSHOT_URL}?t=123456`, { signal: undefined })
  })

  it('HTTP 非 2xx 时抛出错误', async () => {
    vi.stubGlobal('fetch', fetchMock)
    mockResponse(false, 500, new Blob([]))

    await expect(fetchScreenshot()).rejects.toThrow('截图请求失败（HTTP 500）')
  })

  it('返回非图片内容（如 JSON 错误体）时抛出错误', async () => {
    vi.stubGlobal('fetch', fetchMock)
    const jsonBlob = new Blob(['{"success":false}'], { type: 'application/json' })
    mockResponse(true, 200, jsonBlob)

    await expect(fetchScreenshot()).rejects.toThrow('截图接口返回了非图片内容')
  })
})
