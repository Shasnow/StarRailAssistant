import { http } from '../api/http'
import siteConfig from '../configs/siteConfig'
import { createDemoAdapter } from './adapter'
import { DemoLogSource } from './logSource'
import { setLogSourceFactory } from './mode'

/**
 * 演示模式装配入口（仅 --mode demo 构建/启动时由 main.ts 动态 import）：
 * - axios 适配层替换为内存路由，所有 /api 请求闭环，不发真实网络请求
 * - 日志流工厂注册为 DemoLogSource，替代原生 EventSource
 * - 背景图改指外链静态图（正式接口 /api/app/background 在静态站无资源）
 *
 * 正式构建下该模块不会被引用，可被完全 tree-shake。
 */
export function installDemoMode(): void {
  http.defaults.adapter = createDemoAdapter()
  setLogSourceFactory(() => new DemoLogSource())
  // 外链仅存在于本 demo 分包，正式产物中随该模块一并被消除
  siteConfig.bgUrl = 'https://shasnow.top/gallery/starrailassistant/default.jpg'
}
