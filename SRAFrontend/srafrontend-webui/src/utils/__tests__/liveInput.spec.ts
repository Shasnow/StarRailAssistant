// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mapKeyEvent, mapMouseButton, toRelativePoint, wheelToClicks } from '../liveInput'

function keyEvent(init: KeyboardEventInit): KeyboardEvent {
  return new KeyboardEvent('keydown', init)
}

describe('mapKeyEvent', () => {
  it('字母、数字与功能键', () => {
    expect(mapKeyEvent(keyEvent({ code: 'KeyW', key: 'w' }))).toBe('w')
    expect(mapKeyEvent(keyEvent({ code: 'Digit3', key: '3' }))).toBe('3')
    expect(mapKeyEvent(keyEvent({ code: 'F5', key: 'F5' }))).toBe('f5')
  })

  it('方向键、空格与修饰键', () => {
    expect(mapKeyEvent(keyEvent({ code: 'ArrowUp', key: 'ArrowUp' }))).toBe('up')
    expect(mapKeyEvent(keyEvent({ code: 'Space', key: ' ' }))).toBe('space')
    expect(mapKeyEvent(keyEvent({ code: 'Escape', key: 'Escape' }))).toBe('esc')
    expect(mapKeyEvent(keyEvent({ code: 'ShiftLeft', key: 'Shift' }))).toBe('shift')
    expect(mapKeyEvent(keyEvent({ code: 'ControlRight', key: 'Control' }))).toBe('ctrl')
  })

  it('缺少 code 时按 key 兜底', () => {
    expect(mapKeyEvent(keyEvent({ key: 'a' }))).toBe('a')
    expect(mapKeyEvent(keyEvent({ key: 'Enter' }))).toBe('enter')
    expect(mapKeyEvent(keyEvent({ key: 'ArrowLeft' }))).toBe('left')
  })

  it('不支持的键返回 null', () => {
    expect(mapKeyEvent(keyEvent({ code: 'Dead', key: 'Dead' }))).toBeNull()
  })
})

describe('mapMouseButton', () => {
  it('映射左中右键', () => {
    expect(mapMouseButton(0)).toBe('left')
    expect(mapMouseButton(1)).toBe('middle')
    expect(mapMouseButton(2)).toBe('right')
    expect(mapMouseButton(3)).toBeNull()
  })
})

describe('wheelToClicks', () => {
  it('方向与像素单位', () => {
    expect(wheelToClicks(-3, 0)).toBe(3)
    expect(wheelToClicks(3, 0)).toBe(-3)
    expect(wheelToClicks(0, 0)).toBe(0)
  })

  it('行/页单位换算', () => {
    expect(wheelToClicks(-48, 1)).toBe(3)
    expect(wheelToClicks(-800, 2)).toBe(2)
  })

  it('夹取到 ±10，极小增量至少 1 格', () => {
    expect(wheelToClicks(-9999, 0)).toBe(10)
    expect(wheelToClicks(9999, 0)).toBe(-10)
    expect(wheelToClicks(-0.1, 0)).toBe(1)
  })
})

describe('toRelativePoint', () => {
  const natural = { width: 1280, height: 720 }

  it('同比例容器直接换算', () => {
    const rect = { left: 0, top: 0, width: 320, height: 180 }
    expect(toRelativePoint(rect, natural, 160, 90)).toEqual({ x: 0.5, y: 0.5 })
    expect(toRelativePoint(rect, natural, 0, 0)).toEqual({ x: 0, y: 0 })
  })

  it('容器更高时去掉上下留白', () => {
    const rect = { left: 10, top: 20, width: 320, height: 320 }
    // 画面渲染为 320x180，垂直居中：top = 20 + (320-180)/2 = 90
    expect(toRelativePoint(rect, natural, 170, 180)).toEqual({ x: 0.5, y: 0.5 })
    expect(toRelativePoint(rect, natural, 170, 40)).toBeNull()
  })

  it('窗口/尺寸非法或落在画面外返回 null', () => {
    const rect = { left: 0, top: 0, width: 320, height: 180 }
    expect(toRelativePoint(rect, natural, -1, 10)).toBeNull()
    expect(toRelativePoint(rect, natural, 321, 10)).toBeNull()
    expect(toRelativePoint({ ...rect, width: 0 }, natural, 1, 1)).toBeNull()
    expect(toRelativePoint(rect, { width: 0, height: 0 }, 1, 1)).toBeNull()
  })
})
