import { afterEach, describe, expect, it, vi } from 'vitest'
import { clearGithubCache, fetchRepoInfo, GITHUB_API_URL, normalizeRepoInfo } from '../github'
import siteConfig from '@/configs/siteConfig'

afterEach(() => {
  clearGithubCache()
  vi.unstubAllGlobals()
})

describe('GITHUB_API_URL', () => {
  it('API 地址由 siteConfig.repoUrl 解析而来，不硬编码仓库', () => {
    const expected = `https://api.github.com/repos/${new URL(siteConfig.repoUrl).pathname.replace(
      /^\/+|\/+$/g,
      '',
    )}`
    expect(GITHUB_API_URL).toBe(expected)
  })
})

describe('normalizeRepoInfo', () => {
  it('完整数据：解析出全部字段', () => {
    const out = normalizeRepoInfo({
      full_name: 'Shasnow/StarRailAssistant',
      html_url: 'https://github.com/Shasnow/StarRailAssistant',
      description: '自动化助手',
      owner: { login: 'Shasnow', avatar_url: 'https://avatars.example/u.png' },
      stargazers_count: 1200,
      forks_count: 130,
      open_issues_count: 12,
      license: { spdx_id: 'AGPL-3.0', name: 'GNU Affero General Public License v3.0' },
    })
    expect(out).toEqual({
      fullName: 'Shasnow/StarRailAssistant',
      htmlUrl: 'https://github.com/Shasnow/StarRailAssistant',
      description: '自动化助手',
      owner: 'Shasnow',
      ownerAvatar: 'https://avatars.example/u.png',
      stars: 1200,
      forks: 130,
      openIssues: 12,
      license: 'AGPL-3.0',
    })
  })

  it('license 为 NOASSERTION 时回退协议名', () => {
    const out = normalizeRepoInfo({ license: { spdx_id: 'NOASSERTION', name: 'Other' } })
    expect(out.license).toBe('Other')
  })

  it('缺失或非法字段回退为默认值', () => {
    const out = normalizeRepoInfo({ stargazers_count: 'bad', forks_count: -1, owner: null })
    expect(out.fullName).toBe('')
    expect(out.description).toBe('')
    expect(out.owner).toBe('')
    expect(out.ownerAvatar).toBe('')
    expect(out.stars).toBe(0)
    expect(out.forks).toBe(0)
    expect(out.openIssues).toBe(0)
    expect(out.license).toBe('')
  })

  it('入参为 null 时整体回退', () => {
    const out = normalizeRepoInfo(null)
    expect(out.stars).toBe(0)
    expect(out.fullName).toBe('')
  })
})

describe('fetchRepoInfo 缓存机制', () => {
  function mockFetchOnce(status = 200, body?: unknown) {
    return vi.fn(
      async () =>
        new Response(
          JSON.stringify(
            body ?? {
              full_name: 'Shasnow/StarRailAssistant',
              html_url: 'https://github.com/Shasnow/StarRailAssistant',
              description: '自动化助手',
              owner: { login: 'Shasnow', avatar_url: 'https://avatars.example/u.png' },
              stargazers_count: 1200,
              forks_count: 130,
              open_issues_count: 12,
              license: { spdx_id: 'AGPL-3.0' },
            },
          ),
          { status },
        ),
    )
  }

  it('缓存生效：多次调用只发起一次网络请求', async () => {
    const fetchMock = mockFetchOnce()
    vi.stubGlobal('fetch', fetchMock)

    const first = await fetchRepoInfo()
    const second = await fetchRepoInfo()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(second).toEqual(first)
    expect(first.stars).toBe(1200)
    expect(first.license).toBe('AGPL-3.0')
  })

  it('并发调用共享同一个 in-flight 请求', async () => {
    const fetchMock = mockFetchOnce()
    vi.stubGlobal('fetch', fetchMock)

    await Promise.all([fetchRepoInfo(), fetchRepoInfo()])
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('请求失败时抛出错误且不写缓存（重试会再次请求）', async () => {
    const fetchMock = mockFetchOnce(403)
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchRepoInfo()).rejects.toThrow('HTTP 403')
    await expect(fetchRepoInfo()).rejects.toThrow('HTTP 403')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
