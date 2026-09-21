/// <reference types="vite/client" />

/** 构建环境信息（vite.config.ts 经 define 注入，关于页展示用） */
interface BuildInfo {
  /** 应用版本（package.json version） */
  appVersion: string
  /** 构建时真实 Node.js 版本（process.version） */
  node: string
  /** 声明的 Node 版本要求（package.json engines.node） */
  nodeRequired: string
  /** 构建时真实 pnpm 版本（npm_config_user_agent 解析） */
  pnpm: string
  /** 声明的 pnpm 版本（package.json packageManager，不含 hash） */
  pnpmRequired: string
  /** 关键依赖的声明版本（semver 区间） */
  deps: Record<string, string>
}

declare const __BUILD_INFO__: BuildInfo
