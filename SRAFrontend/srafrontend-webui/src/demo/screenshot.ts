/**
 * 演示模式截图：用 canvas 绘制一张带时间戳的演示画面（PNG Blob），
 * 替代真实后端的 /api/backend/screenshot，保证实时画面轮询链路可用。
 */

/** 画面尺寸（16:9，接近常见游戏窗口比例） */
const WIDTH = 1280
const HEIGHT = 720

/** 无法创建 canvas 上下文时的兜底（几乎不会发生），保持 image/png 类型以通过调用方校验 */
function emptyPng(): Blob {
  return new Blob([], { type: 'image/png' })
}

export function renderDemoScreenshot(): Promise<Blob> {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas')
    canvas.width = WIDTH
    canvas.height = HEIGHT
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      resolve(emptyPng())
      return
    }

    // 渐变底 + 文案：canvas 绘制不走 CSS 主题变量，使用固定的演示配色
    const gradient = ctx.createLinearGradient(0, 0, WIDTH, HEIGHT)
    gradient.addColorStop(0, '#1b2a4e')
    gradient.addColorStop(1, '#3a2c66')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, WIDTH, HEIGHT)

    ctx.textAlign = 'center'
    ctx.fillStyle = '#f5f7ff'
    ctx.font = 'bold 52px system-ui, "Microsoft YaHei", sans-serif'
    ctx.fillText('演示画面', WIDTH / 2, HEIGHT / 2 - 16)
    ctx.font = '26px system-ui, "Microsoft YaHei", sans-serif'
    ctx.fillStyle = 'rgba(245, 247, 255, 0.75)'
    ctx.fillText('静态演示部署 · 无后端连接', WIDTH / 2, HEIGHT / 2 + 34)
    ctx.fillText(new Date().toLocaleString('zh-CN'), WIDTH / 2, HEIGHT / 2 + 78)

    canvas.toBlob((blob) => resolve(blob ?? emptyPng()), 'image/png')
  })
}
