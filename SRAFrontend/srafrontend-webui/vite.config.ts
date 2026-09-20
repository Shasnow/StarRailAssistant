import { readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
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

// https://vite.dev/config/
export default defineConfig({
  define: {
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
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
