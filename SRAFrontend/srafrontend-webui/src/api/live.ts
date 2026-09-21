/**
 * /api/Operator 实时画面服务模块（对应 OpenAPI OperatorController）：
 * - GET /api/Operator/screenshot → 200 image/png 原始字节（不走 R<T> 包装，直接二进制）
 *
 * 前端按固定间隔轮询该接口并渲染到 <img>，即构成实时画面。
 */

/** 截图接口地址（开发环境经 vite 代理 /api → 后端） */
export const SCREENSHOT_URL = '/api/backend/screenshot'

/**
 * 拉取一张当前截图，返回图片 Blob（调用方用 URL.createObjectURL 渲染）。
 * - 携带 cacheBust 时间戳查询参数绕过浏览器/代理缓存，保证拿到最新帧
 * - 非 2xx 或返回非图片内容（如 JSON 错误体）时抛出错误
 */
export async function fetchScreenshot(signal?: AbortSignal, cacheBust?: number): Promise<Blob> {
  const url = cacheBust ? `${SCREENSHOT_URL}?t=${cacheBust}` : SCREENSHOT_URL
  const res = await fetch(url, { signal })
  if (!res.ok) throw new Error(`截图请求失败（HTTP ${res.status}）`)
  const blob = await res.blob()
  if (!blob.type.startsWith('image/')) throw new Error('截图接口返回了非图片内容')
  return blob
}
