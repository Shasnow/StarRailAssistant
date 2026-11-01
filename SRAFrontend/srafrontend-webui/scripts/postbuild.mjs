import { cp, rm, stat, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// 项目根目录（本脚本位于 scripts/ 下）
const rootDir = fileURLToPath(new URL('..', import.meta.url))
const distDir = path.join(rootDir, 'dist')
// 后端静态资源目录：SRAServer 通过 static/ 托管前端产物
const targetDir = path.resolve(rootDir, '..', '..', 'SRAServer', 'static')

// 产物不存在说明未先执行 vite build，直接失败避免把空目录拷过去
const distStat = await stat(distDir).catch(() => null)
if (!distStat?.isDirectory()) {
  console.error(`[postbuild] 未找到构建产物：${distDir}，请先执行 pnpm build-only`)
  process.exit(1)
}

// 先清空目标目录，否则上一轮构建的 hash 资源会残留在 static
await rm(targetDir, { recursive: true, force: true })
await cp(distDir, targetDir, { recursive: true })
// 保留占位文件，保证空仓库中 static 目录存在且被版本控制跟踪
await writeFile(path.join(targetDir, '.gitkeep'), '')

console.log(`[postbuild] 构建产物已复制：${distDir} -> ${targetDir}`)