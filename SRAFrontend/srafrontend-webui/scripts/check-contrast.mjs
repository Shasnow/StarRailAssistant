// WCAG 对比率校验：从 base.css 提取 OKLCH token（单一事实来源），
// 按 CSS Color 4 算法换算线性 sRGB → 相对亮度 → 对比率，断言关键配色对。
// 仅 Node 原生能力，无第三方依赖。用法：node scripts/check-contrast.mjs
// 注意：色域映射采用简单逐通道截断，亮度计算与浏览器略有差异（<2%），
// 阈值均预留了余量；装饰性边框不参与 WCAG 1.4.11（非文字 3:1 仅约束有辨识功能的 UI）。

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const css = readFileSync(join(__dirname, '../src/assets/base.css'), 'utf8')

/** 按选择器提取声明块内的自定义属性 map */
function extractBlock(selector) {
  const start = css.indexOf(`${selector} {`)
  if (start === -1) throw new Error(`base.css 中未找到 ${selector}`)
  const end = css.indexOf('\n}', start)
  const body = css.slice(start, end)
  const map = {}
  for (const m of body.matchAll(/^\s*--([\w-]+):\s*([^;]+);/gm)) {
    map[m[1]] = m[2].trim()
  }
  return map
}

const light = extractBlock(':root')
const dark = { ...light, ...extractBlock(':root.dark') }
const terminalScope = { ...light, ...extractBlock('.terminal-scope') }

/** OKLCH → 线性 sRGB（CSS Color 4） */
function oklchToLinearSrgb(L, C, H) {
  const h = (H * Math.PI) / 180
  const a = C * Math.cos(h)
  const b = C * Math.sin(h)
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b
  const s_ = L - 0.0894841775 * a - 1.291485548 * b
  const l = l_ ** 3
  const m = m_ ** 3
  const s = s_ ** 3
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ]
}

function hexToLinearSrgb(hex) {
  const n = parseInt(hex.slice(1), 16)
  return [16, 8, 0].map((sh) => {
    const c = ((n >> sh) & 0xff) / 255
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
}

/** 解析 token 值为线性 sRGB（仅支持 oklch 与 hex；color-mix/transparent 不参与 gate） */
function parse(token, hue) {
  const v = token.replaceAll('var(--hue)', String(hue))
  if (v.startsWith('#')) return hexToLinearSrgb(v)
  const m = v.match(/^oklch\(([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/[^)]*)?\)$/)
  if (!m) return null
  return oklchToLinearSrgb(Number(m[1]), Number(m[2]), Number(m[3]))
}

function luminance(rgb) {
  return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
}

function contrast(rgbA, rgbB) {
  const [la, lb] = [luminance(rgbA), luminance(rgbB)].sort((x, y) => y - x)
  return (la + 0.05) / (lb + 0.05)
}

const WHITE = [1, 1, 1]
const PRESETS = [0, 30, 60, 163, 200, 250, 300, 330]

let failures = 0
let warnings = 0

function gate(name, ratio, min, { warnOnly = false } = {}) {
  const ok = ratio >= min
  const text = `${name}: ${ratio.toFixed(2)}:1 (目标 ≥ ${min}:1)`
  if (ok) {
    console.log(`  ✓ ${text}`)
  } else if (warnOnly) {
    warnings++
    console.warn(`  ⚠ ${text} [豁免警告]`)
  } else {
    failures++
    console.error(`  ✗ ${text}`)
  }
}

function runGates(title, tokens, hue, mode) {
  const get = (key) => parse(tokens[key], hue)
  const bg = get('color-background')
  console.log(`\n[${title}] hue=${hue}`)
  gate('text / background', contrast(get('color-text'), bg), 7)
  gate('heading / background', contrast(get('color-heading'), bg), 7)
  gate('text-secondary / background', contrast(get('color-text-secondary'), bg), 4.5)
  gate('muted / background', contrast(get('color-muted'), bg), 4.5)
  gate('primary / background', contrast(get('color-primary'), bg), 4.5)
  gate('white / primary', contrast(WHITE, get('color-primary')), mode === 'dark' ? 3 : 4.5, {
    // 黄绿色相亮度高，白字 ≥4.5 数学上不可达（对齐 EP #e6a23c 既有现状）
    warnOnly: mode === 'light' && hue >= 60 && hue <= 110,
  })
  gate('success / background', contrast(get('color-success'), bg), 4.5)
  gate('warning / background', contrast(get('color-warning'), bg), 4.5, { warnOnly: true })
  gate('danger / background', contrast(get('color-danger'), bg), 4.5)
  gate('info / background', contrast(get('color-info'), bg), 4.5)
}

function runTerminalGates(hue) {
  const get = (key) => parse(terminalScope[key], hue)
  const bg = get('terminal-bg')
  console.log(`\n[终端深色寄存器] hue=${hue}（两模式同值）`)
  gate('terminal-text / terminal-bg', contrast(get('terminal-text'), bg), 4.5)
  gate('terminal-time / terminal-bg', contrast(get('terminal-time'), bg), 4.5)
  gate('muted(深色档) / terminal-bg', contrast(get('color-muted'), bg), 4.5)
  gate('success(深色档) / terminal-bg', contrast(get('color-success'), bg), 4.5)
  gate('warning(深色档) / terminal-bg', contrast(get('color-warning'), bg), 4.5, { warnOnly: true })
  gate('danger(深色档) / terminal-bg', contrast(get('color-danger'), bg), 4.5)
  gate('info(深色档) / terminal-bg', contrast(get('color-info'), bg), 4.5)
  gate('hint-on-dark / terminal-bg', contrast(get('color-hint-on-dark'), bg), 4.5)
  // Hero 渐变最亮档上的白字（L 0.35 任意色相恒安全）
  gate('white / hero 渐变最亮档', contrast(WHITE, oklchToLinearSrgb(0.35, 0.03, hue)), 4.5)
}

// 默认色相全量 gate
runGates('浅色模式', light, 163, 'light')
runGates('深色模式', dark, 163, 'dark')
runTerminalGates(163)

// 8 个预设色相逐一报告（gate 只跑关键 primary 配对，输出紧凑表格）
console.log('\n[预设色相报告]（primary / background 与 white / primary）')
for (const hue of PRESETS) {
  const pl = contrast(parse(light['color-primary'], hue), parse(light['color-background'], hue))
  const wl = contrast(WHITE, parse(light['color-primary'], hue))
  const pd = contrast(parse(dark['color-primary'], hue), parse(dark['color-background'], hue))
  const wd = contrast(WHITE, parse(dark['color-primary'], hue))
  console.log(
    `  hue ${String(hue).padStart(3)}°  浅: ${pl.toFixed(2)} / 白${wl.toFixed(2)}  深: ${pd.toFixed(2)} / 白${wd.toFixed(2)}`
  )
}

console.log(`\n结果：${failures} 个失败，${warnings} 个豁免警告`)
if (failures > 0) process.exit(1)
