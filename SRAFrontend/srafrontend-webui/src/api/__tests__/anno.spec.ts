import { afterEach, describe, expect, it, vi } from 'vitest'
import { clearAnnoCache, fetchAnnouncements, normalizeAnnouncements } from '../anno'

afterEach(() => {
  clearAnnoCache()
  vi.unstubAllGlobals()
})

describe('normalizeAnnouncements', () => {
  it('过滤非法条目，仅保留 title/content 均为字符串的公告', () => {
    const out = normalizeAnnouncements({
      id: 27,
      announcements: [
        { title: '有效公告', content: '内容' },
        { title: 123, content: '标题非字符串' },
        { title: '缺内容' },
        null as never,
      ],
    })
    expect(out).toEqual({
      id: 27,
      announcements: [{ title: '有效公告', content: '内容' }],
    })
  })

  it('announcements 非数组时返回空列表', () => {
    const out = normalizeAnnouncements({ id: 1, announcements: 'bad' as never })
    expect(out.announcements).toEqual([])
  })

  it('id 非数字时回退为 0', () => {
    const out = normalizeAnnouncements({ id: 'x' as never, announcements: [] })
    expect(out.id).toBe(0)
  })
})

describe('fetchAnnouncements 缓存机制', () => {
  function mockFetchOnce(status = 200, body?: unknown) {
    return vi.fn(async () =>
      new Response(
        JSON.stringify(
          body ?? { id: 27, announcements: [{ title: '公告', content: '内容' }] },
        ),
        { status },
      ),
    )
  }

  it('缓存生效：多次调用只发起一次网络请求', async () => {
    const fetchMock = mockFetchOnce()
    vi.stubGlobal('fetch', fetchMock)

    const first = await fetchAnnouncements()
    const second = await fetchAnnouncements()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(second).toEqual(first)
    expect(first.announcements).toEqual([{ title: '公告', content: '内容' }])
  })

  it('并发调用共享同一个 in-flight 请求', async () => {
    const fetchMock = mockFetchOnce()
    vi.stubGlobal('fetch', fetchMock)

    await Promise.all([fetchAnnouncements(), fetchAnnouncements()])
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('请求失败时抛出错误且不写缓存（重试会再次请求）', async () => {
    const fetchMock = mockFetchOnce(500)
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchAnnouncements()).rejects.toThrow('HTTP 500')
    await expect(fetchAnnouncements()).rejects.toThrow('HTTP 500')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('force=true 时跳过缓存强制请求', async () => {
    const fetchMock = mockFetchOnce()
    vi.stubGlobal('fetch', fetchMock)

    await fetchAnnouncements()
    await fetchAnnouncements(true)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
