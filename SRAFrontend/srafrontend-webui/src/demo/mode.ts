/**
 * 演示模式判定 —— 轻量模块，允许被生产代码静态导入。
 *
 * 模式在构建/启动期唯一确定（`vite --mode demo` + `.env.demo` 的 VITE_DEMO_DEFAULT=1），
 * 运行时无任何切换开关；判定经 vite.config.ts 的 define 注入为编译期常量 __IS_DEMO__，
 * 各调用点直接内联字面量，正式构建下相关分支与 demo 代码被整体消除。
 * 重模块（adapter/handlers 等）一律通过动态 import 装载，见 install.ts。
 */

/** 与 EventSource 兼容的最小日志源接口（DemoLogSource 实现它） */
export type LogSource = Pick<
  EventSource,
  'onopen' | 'onmessage' | 'onerror' | 'close' | 'readyState'
>

/** 日志源工厂：演示模式下由 install.ts 注册，替代 new EventSource(url) */
export type LogSourceFactory = (url: string) => LogSource

let logSourceFactory: LogSourceFactory | null = null

/** 注册演示日志源工厂（仅演示模式装配时调用） */
export function setLogSourceFactory(factory: LogSourceFactory): void {
  logSourceFactory = factory
}

/** 取得已注册的日志源工厂；正式模式返回 null */
export function getLogSourceFactory(): LogSourceFactory | null {
  return logSourceFactory
}
