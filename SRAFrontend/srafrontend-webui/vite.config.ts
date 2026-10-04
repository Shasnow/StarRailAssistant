import { readFileSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// 构建时读取 package.json：版本与环境信息经 define 注入前端（关于页展示用）
const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf-8')) as {
  version: string
  engines: { node: string }
  packageManager: string
  devDependencies: Record<string, string>
}

// npm_config_user_agent 由 pnpm 注入（如 "pnpm/12.4.2 npm/..."），解析出构建时真实 pnpm 版本
const pnpmVersion = /pnpm\/([\w.]+)/.exec(process.env.npm_config_user_agent ?? '')?.[1] ?? ''

// 演示模式静态托管适配：构建结束时向产物目录写入 SPA 路由回退文件
// - 404.html：GitHub Pages 无重写规则，用 404.html 承载入口实现前端路由回退
// - _redirects：Netlify 的 SPA 重写规则
function demoStaticHostingPlugin(mode: string): Plugin {
  let outDir = 'dist'
  return {
    name: 'demo-static-hosting',
    apply: 'build',
    configResolved(config) {
      outDir = resolve(config.root, config.build.outDir)
    },
    closeBundle() {
      if (mode !== 'demo') return
      const indexHtml = readFileSync(join(outDir, 'index.html'), 'utf-8')
      writeFileSync(join(outDir, '404.html'), indexHtml)
      writeFileSync(join(outDir, '_redirects'), '/* /index.html 200\n')
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 第三参传空串：读取全部前缀的 env（需要 VITE_BASE 等自定义键，不限于 VITE_）
  const env = loadEnv(mode, process.cwd(), '')

  return {
    // 部署基路径：默认根路径，子路径部署（如 GitHub Pages 项目页）通过 VITE_BASE 覆盖
    base: env.VITE_BASE || '/',
    define: {
      // 演示模式编译期常量：仅 --mode demo（.env.demo 的 VITE_DEMO_DEFAULT=1）为 true，
      // 各调用点内联为字面量后可被直接消除，保证正式构建不含 demo 分支与代码
      __IS_DEMO__: JSON.stringify(env.VITE_DEMO_DEFAULT === '1'),
      __BUILD_INFO__: JSON.stringify({
        appVersion: pkg.version,
        node: process.version,
        nodeRequired: pkg.engines.node,
        pnpm: pnpmVersion,
        pnpmRequired: pkg.packageManager.split('+')[0] ?? pkg.packageManager,
        deps: {
          vite: pkg.devDependencies.vite,
          typescript: pkg.devDependencies.typescript,
        },
      }),
    },
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:5073',
          changeOrigin: true,
          secure: false,
        },
        // 后端 OpenAPI 规范文档
        '/openapi': {
          target: 'http://localhost:5073',
          changeOrigin: true,
          secure: false,
        },
      },
    },
    plugins: [
      vue(),
      vueDevTools(),
      AutoImport({
        resolvers: [ElementPlusResolver()],
      }),
      Components({
        resolvers: [ElementPlusResolver()],
      }),
      demoStaticHostingPlugin(mode),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    build: {
      // 分包：Element Plus 与 Vue 生态各自独立，配合预加载策略提升缓存命中率
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            if (!id.includes('node_modules')) return undefined
            if (id.includes('element-plus') || id.includes('@element-plus')) return 'element-plus'
            if (/[\\/]node_modules[\\/](@vue|vue|vue-router|pinia)[\\/]/.test(id)) {
              return 'vue-eco'
            }
            return undefined
          },
        },
      },
    },
  }
})
