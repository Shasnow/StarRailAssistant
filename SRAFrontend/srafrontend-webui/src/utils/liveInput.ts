import type { MouseButtonName } from '@/api/operator'

/** 浏览器事件 → pyautogui 键名映射（优先按 KeyboardEvent.code 匹配） */
const CODE_KEY_MAP: Record<string, string> = {
  Space: 'space',
  Enter: 'enter',
  NumpadEnter: 'enter',
  Escape: 'esc',
  Tab: 'tab',
  Backspace: 'backspace',
  Delete: 'delete',
  Insert: 'insert',
  Home: 'home',
  End: 'end',
  PageUp: 'pageup',
  PageDown: 'pagedown',
  ArrowUp: 'up',
  ArrowDown: 'down',
  ArrowLeft: 'left',
  ArrowRight: 'right',
  ShiftLeft: 'shift',
  ShiftRight: 'shift',
  ControlLeft: 'ctrl',
  ControlRight: 'ctrl',
  AltLeft: 'alt',
  AltRight: 'alt',
  MetaLeft: 'win',
  MetaRight: 'win',
  CapsLock: 'capslock',
  NumLock: 'numlock',
  ScrollLock: 'scrolllock',
}

/** 部分环境没有 code 时按 KeyboardEvent.key 兜底 */
const KEY_NAME_MAP: Record<string, string> = {
  ' ': 'space',
  Spacebar: 'space',
  Enter: 'enter',
  Escape: 'esc',
  Esc: 'esc',
  Tab: 'tab',
  Backspace: 'backspace',
  Delete: 'delete',
  Insert: 'insert',
  Home: 'home',
  End: 'end',
  PageUp: 'pageup',
  PageDown: 'pagedown',
  ArrowUp: 'up',
  ArrowDown: 'down',
  ArrowLeft: 'left',
  ArrowRight: 'right',
  Shift: 'shift',
  Control: 'ctrl',
  Alt: 'alt',
  Meta: 'win',
  CapsLock: 'capslock',
  NumLock: 'numlock',
  ScrollLock: 'scrolllock',
}

/**
 * 把键盘事件映射为 pyautogui 键名；不支持的键返回 null。
 * - 修饰键单独发送（ctrl 按下 → c 按下 → c 抬起 → ctrl 抬起），不组装组合键
 */
export function mapKeyEvent(event: KeyboardEvent): string | null {
  const code = event.code || ''
  if (CODE_KEY_MAP[code]) return CODE_KEY_MAP[code]

  const letter = /^Key([A-Z])$/.exec(code)
  if (letter?.[1]) return letter[1].toLowerCase()

  const digit = /^Digit([0-9])$/.exec(code)
  if (digit?.[1]) return digit[1]

  const numpad = /^Numpad([0-9])$/.exec(code)
  if (numpad?.[1]) return numpad[1]

  const fn = /^F([1-9]|1[0-9]|2[0-4])$/.exec(code)
  if (fn?.[1]) return `f${fn[1]}`

  const key = event.key || ''
  if (KEY_NAME_MAP[key]) return KEY_NAME_MAP[key]

  const lowerFn = /^F([1-9]|1[0-9]|2[0-4])$/.exec(key)
  if (lowerFn?.[1]) return `f${lowerFn[1]}`

  // 单字符键（字母、数字、符号）直接交给 pyautogui
  return key.length === 1 ? key.toLowerCase() : null
}

/** MouseEvent.button → Operator 鼠标按钮名 */
export function mapMouseButton(button: number): MouseButtonName | null {
  switch (button) {
    case 0:
      return 'left'
    case 1:
      return 'middle'
    case 2:
      return 'right'
    default:
      return null
  }
}

/** 单次滚轮的 pyautogui 滚轮格数上限，避免一次大滚动产生过量输入 */
const MAX_WHEEL_CLICKS = 10

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

/**
 * 滚轮增量 → pyautogui.scroll 的 clicks（正数向上）。
 * deltaMode：0 = 像素，1 = 行，2 = 页。
 */
export function wheelToClicks(deltaY: number, deltaMode: number): number {
  if (!Number.isFinite(deltaY) || deltaY === 0) return 0
  const unit = deltaMode === 1 ? 16 : deltaMode === 2 ? 400 : 1
  // 浏览器 deltaY 向下为正，pyautogui clicks 向上为正，因此取反
  const raw = Math.round(-deltaY / unit)
  if (raw === 0) return deltaY > 0 ? -1 : 1
  return clamp(raw, -MAX_WHEEL_CLICKS, MAX_WHEEL_CLICKS)
}

/** 画面容器与图片原始尺寸（用于反算 object-fit: contain 的实际渲染区） */
export interface ContainRect {
  left: number
  top: number
  width: number
  height: number
}

export interface NaturalSize {
  width: number
  height: number
}

/**
 * 把页面坐标换算成游戏窗口的相对比例坐标（0–1）。
 * 画面按 object-fit: contain 居中缩放，含留白时先去掉留白；落在画面外返回 null。
 */
export function toRelativePoint(
  rect: ContainRect,
  natural: NaturalSize,
  clientX: number,
  clientY: number,
): { x: number; y: number } | null {
  if (rect.width <= 0 || rect.height <= 0 || natural.width <= 0 || natural.height <= 0) return null

  const scale = Math.min(rect.width / natural.width, rect.height / natural.height)
  const renderedWidth = natural.width * scale
  const renderedHeight = natural.height * scale
  if (renderedWidth <= 0 || renderedHeight <= 0) return null

  const left = rect.left + (rect.width - renderedWidth) / 2
  const top = rect.top + (rect.height - renderedHeight) / 2
  if (
    clientX < left ||
    clientX > left + renderedWidth ||
    clientY < top ||
    clientY > top + renderedHeight
  ) {
    return null
  }

  return {
    x: clamp((clientX - left) / renderedWidth, 0, 1),
    y: clamp((clientY - top) / renderedHeight, 0, 1),
  }
}
