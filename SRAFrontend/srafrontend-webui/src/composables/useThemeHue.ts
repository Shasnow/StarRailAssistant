import { useStorage } from '@vueuse/core'

/** 默认主题色相：与原品牌绿 #42b883 对齐 */
export const DEFAULT_HUE = 250

// 模块级单例：全应用共享同一份持久化色相（localStorage key: theme-hue）
const hue = useStorage('theme-hue', DEFAULT_HUE)

function applyHue() {
  document.documentElement.style.setProperty('--hue', String(hue.value))
}

/**
 * 主题色相（OKLCH hue 通道，0-360 无单位数字）。
 * base.css 中所有中性色/主色均由 oklch(L C var(--hue)) 派生，
 * setHue 更新变量即全站即时生效（实时预览）。
 */
export function useThemeHue() {
  /** 应用启动时调用一次：把持久化的色相写入 html 内联样式，保证首帧生效 */
  function init() {
    applyHue()
  }

  function setHue(next: number) {
    hue.value = Math.min(360, Math.max(0, Math.round(next)))
    applyHue()
  }

  function resetHue() {
    setHue(DEFAULT_HUE)
  }

  return { hue, setHue, resetHue, init }
}
