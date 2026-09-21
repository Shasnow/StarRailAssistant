// GitHub 仓库信息接口：公开 REST API（支持匿名跨域直连，未认证限流 60 次/小时/IP）
import siteConfig from '@/configs/siteConfig'

/** 关于页展示的仓库信息（已做形状兜底，字段保证为可用类型） */
export interface GitHubRepoInfo {
  /** 仓库全名（owner/name，如 StarRailAssistant/StarRailAssistant） */
  fullName: string
  /** 仓库主页 */
  htmlUrl: string
  /** 仓库描述 */
  description: string
  /** 作者用户名 */
  owner: string
  /** 作者头像地址 */
  ownerAvatar: string
  /** Star 数 */
  stars: number
  /** Fork 数 */
  forks: number
  /** 开放 issue 数 */
  openIssues: number
  /** License 标识（优先 SPDX id，如 AGPL-3.0） */
  license: string
}

/** 仓库标识 owner/name：从 siteConfig.repoUrl 解析（如 Shasnow/StarRailAssistant），解析失败时为空串 */
export const GITHUB_REPO_SLUG = (() => {
  const [owner, repo] = new URL(siteConfig.repoUrl).pathname.split('/').filter(Boolean)
  return owner && repo ? `${owner}/${repo}` : ''
})()

export const GITHUB_API_URL = `https://api.github.com/repos/${GITHUB_REPO_SLUG}`

// 模块级缓存：同一会话内避免重复消耗限流额度；并发调用共享同一个 in-flight 请求
let cache: GitHubRepoInfo | null = null
let inflight: Promise<GitHubRepoInfo> | null = null

/** 清空仓库信息缓存（测试用） */
export function clearGithubCache() {
  cache = null
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value ? value : fallback
}

function asCount(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : 0
}

/** 过滤非法字段，保证渲染时拿到的一定是可用形状 */
export function normalizeRepoInfo(raw: unknown): GitHubRepoInfo {
  const data = (raw ?? {}) as Record<string, unknown>
  const owner = (data.owner ?? {}) as Record<string, unknown>
  const license = (data.license ?? {}) as Record<string, unknown>
  // license 优先取 SPDX id；GitHub 对自定义协议返回 NOASSERTION，此时回退协议名
  const spdx = asString(license.spdx_id)
  return {
    fullName: asString(data.full_name),
    htmlUrl: asString(data.html_url),
    description: asString(data.description),
    owner: asString(owner.login),
    ownerAvatar: asString(owner.avatar_url),
    stars: asCount(data.stargazers_count),
    forks: asCount(data.forks_count),
    openIssues: asCount(data.open_issues_count),
    license: spdx && spdx !== 'NOASSERTION' ? spdx : asString(license.name),
  }
}

/**
 * 获取仓库实时信息（带缓存）
 * @param signal 可选中断信号（组件卸载时终止请求）
 */
export async function fetchRepoInfo(signal?: AbortSignal): Promise<GitHubRepoInfo> {
  if (cache) return cache
  if (inflight) return inflight

  inflight = (async () => {
    try {
      const res = await fetch(GITHUB_API_URL, {
        signal,
        headers: { Accept: 'application/vnd.github+json' },
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const info = normalizeRepoInfo(await res.json())
      cache = info
      return info
    } finally {
      inflight = null
    }
  })()
  return inflight
}
