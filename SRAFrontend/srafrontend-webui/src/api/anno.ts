// 公告数据接口：SRA 官方公告（接口已开放 CORS，可直连）

export interface Announcement {
  title: string
  content: string
}

export interface AnnoResponse {
  id: number
  announcements: Announcement[]
}

export const ANNO_URL = 'https://starrailassistant.top/api/v1/anno.json'

// 模块级缓存：同一会话内避免重复请求；并发调用共享同一个 in-flight 请求
let cache: AnnoResponse | null = null
let inflight: Promise<AnnoResponse> | null = null

/** 清空公告缓存（测试用） */
export function clearAnnoCache() {
  cache = null
}

/** 过滤非法条目，保证渲染时 title/content 一定是字符串 */
export function normalizeAnnouncements(data: AnnoResponse): AnnoResponse {
  return {
    id: typeof data?.id === 'number' ? data.id : 0,
    announcements: Array.isArray(data?.announcements)
      ? data.announcements.filter(
          (a): a is Announcement =>
            !!a && typeof a.title === 'string' && typeof a.content === 'string',
        )
      : [],
  }
}

/**
 * 获取公告列表（带缓存）
 * @param force 为 true 时跳过缓存强制请求
 */
export async function fetchAnnouncements(
  force = false,
  signal?: AbortSignal,
): Promise<AnnoResponse> {
  if (!force && cache) return cache
  if (!force && inflight) return inflight

  inflight = (async () => {
    try {
      const res = await fetch(ANNO_URL, { signal })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const data = normalizeAnnouncements((await res.json()) as AnnoResponse)
      cache = data
      return data
    } finally {
      inflight = null
    }
  })()
  return inflight
}
