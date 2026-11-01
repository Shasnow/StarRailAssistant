import { ApiError, request } from './http'

/**
 * /api/operator 服务模块（对应后端 OperatorController）：
 * - POST /api/operator/call  { method, params } 调用 IOperator 的任意方法
 *
 * 实时画面的手动输入不新增后端接口：鼠标/键盘事件逐一映射为
 * move_to / mouse_down / mouse_up / scroll / key_down / key_up / press_key 调用。
 */

export type MouseButtonName = 'left' | 'middle' | 'right'

/** 手动输入事件（与 Operator 方法一一对应） */
export type InputEvent =
  | { type: 'move'; x: number; y: number }
  | { type: 'down'; x: number; y: number; button: MouseButtonName }
  | { type: 'up'; button: MouseButtonName }
  | { type: 'wheel'; clicks: number }
  | { type: 'key_down'; key: string }
  | { type: 'key_up'; key: string }
  | { type: 'key_press'; key: string; presses?: number }

/**
 * 调用 POST /api/operator/call。
 * - success=false（HTTP 200）由 http 拦截器抛 ApiError
 * - 方法自身返回 false（执行失败）时 data === false，这里同样抛错，调用方可统一按失败处理
 */
export async function callOperator(
  method: string,
  params: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<unknown> {
  const data = await request<unknown>({
    url: '/operator/call',
    method: 'post',
    data: { method, params },
    signal,
  })
  if (data === false) throw new ApiError(`Operator 方法 ${method} 执行失败`)
  return data
}

/** 输入事件 → Operator 方法映射（trace: false，避免高频输入刷日志） */
export async function sendInputEvent(event: InputEvent, signal?: AbortSignal): Promise<void> {
  switch (event.type) {
    case 'move':
      await callOperator('move_to', { x: event.x, y: event.y, trace: false }, signal)
      return
    case 'down':
      await callOperator(
        'mouse_down',
        { x: event.x, y: event.y, button: event.button, trace: false },
        signal,
      )
      return
    case 'up':
      await callOperator('mouse_up', { button: event.button, trace: false }, signal)
      return
    case 'wheel':
      // scroll 作用于当前光标位置，调用方需先发送 move
      await callOperator('scroll', { clicks: event.clicks, trace: false }, signal)
      return
    case 'key_down':
      await callOperator('key_down', { key: event.key, trace: false }, signal)
      return
    case 'key_up':
      await callOperator('key_up', { key: event.key, trace: false }, signal)
      return
    case 'key_press':
      await callOperator(
        'press_key',
        { key: event.key, presses: event.presses ?? 1, trace: false },
        signal,
      )
  }
}

/** 游戏窗口是否处于前台（后端 Operator.is_window_active） */
export async function isGameWindowActive(signal?: AbortSignal): Promise<boolean> {
  const data = await request<unknown>({
    url: '/operator/call',
    method: 'post',
    data: { method: 'is_window_active', params: {} },
    signal,
  })
  return data === true
}

/** 用户主动请求激活游戏窗口（后端 Operator.active_window） */
export async function activateGameWindow(signal?: AbortSignal): Promise<void> {
  await callOperator('active_window', {}, signal)
}
