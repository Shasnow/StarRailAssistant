import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.setOptions({ gfm: true, breaks: true })

/** Markdown → HTML 字符串；内容来自远端接口，插入 DOM 前必须经 DOMPurify 净化 */
export function renderMarkdown(md: string): string {
  const html = marked.parse(md ?? '', { async: false })
  return DOMPurify.sanitize(html)
}
