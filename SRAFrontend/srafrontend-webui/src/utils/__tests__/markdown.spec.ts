// @vitest-environment jsdom
// renderMarkdown 依赖 DOMPurify，需要 DOM 环境
import { describe, expect, it } from 'vitest'
import { renderMarkdown } from '../markdown'

describe('renderMarkdown', () => {
  it('渲染标题、列表与加粗等常见 Markdown 元素', () => {
    const html = renderMarkdown('# 标题\n\n- 列表项\n\n**加粗**')
    expect(html).toContain('<h1>')
    expect(html).toContain('<li>列表项</li>')
    expect(html).toContain('<strong>加粗</strong>')
  })

  it('净化 script 脚本与事件属性，防 XSS', () => {
    const html = renderMarkdown(
      '正常文字\n\n<script>alert(1)</script>\n\n<img src=x onerror="alert(1)">',
    )
    expect(html).not.toContain('<script')
    expect(html).not.toContain('onerror')
    expect(html).toContain('正常文字')
  })

  it('净化 javascript: 链接', () => {
    const html = renderMarkdown('[点击](javascript:alert(1))')
    expect(html).not.toContain('javascript:')
  })

  it('空输入返回空字符串', () => {
    expect(renderMarkdown('')).toBe('')
  })
})
