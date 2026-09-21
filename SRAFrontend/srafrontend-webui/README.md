# SRA WebUI

基于 Vue 3 + Element Plus 的崩坏：星穹铁道自动化助手控制台前端。

作为 .NET 后端（`localhost:5073`）的 Web 控制面板，提供任务配置管理、运行控制、实时日志、画面监控和后端管理等功能。

> 本项目为 [StarRailAssistant](https://github.com/Shasnow/StarRailAssistant) 的前端子项目，采用 [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) 协议。

## 功能一览

| 页面 | 路径        | 功能                                                                   |
| ---- | ----------- | ---------------------------------------------------------------------- |
| 首页 | `/`         | 任务状态仪表盘、运行配置管理、OpenAPI 驱动的任务配置表单、公告         |
| 设置 | `/settings` | 基于 OpenAPI Schema 动态生成的后端应用设置表单                         |
| 日志 | `/logs`     | SSE 实时日志流（筛选/搜索/复制/导出）、截图轮询实时画面、后端重启/停止 |
| 关于 | `/about`    | GitHub 仓库信息、系统运行时信息、构建环境信息                          |
| 登录 | `/login`    | Access Token 认证（全局 401 自动跳转）                                 |

## 技术栈

- **框架**: Vue 3.5 + Composition API (`<script setup>`)
- **类型**: TypeScript 6.0（strict, `noUncheckedIndexedAccess`）
- **UI**: Element Plus 2.14（组件自动导入）
- **状态管理**: Pinia 4.x
- **路由**: Vue Router 5.x（HTML5 History）
- **构建**: Vite 8.2 + pnpm 12.4.2
- **测试**: Vitest 5.x + jsdom
- **Lint**: oxlint + ESLint（双重检查）
- **格式化**: Prettier（无分号、单引号、100 字符行宽）

### 核心设计

- **OKLCH 主题系统** — 全站颜色由单一 `--hue` 色相变量派生，支持运行时实时切换，深色/浅色双模式 + 终端恒深色作用域
- **OpenAPI 动态表单** — 任务配置和应用设置表单均由后端 OpenAPI 规范驱动渲染，配置结构完全由后端定义
- **R\<T\> 信封模式** — 所有 API 响应经 `{ success, message, data }` 包装，Axios 拦截器自动解包

## 开发

### 环境要求

- Node.js `^22.18.0 || >=24.12.0`
- pnpm 12.4.2（corepack 管理）

### 常用命令

```bash
pnpm install          # 安装依赖
pnpm dev              # 开发服务器（端口 5173，代理 /api → localhost:5073）
pnpm build            # 类型检查 + 生产构建（并行）
pnpm build-only       # 仅 Vite 构建（跳过类型检查）
pnpm type-check       # vue-tsc 类型检查
pnpm test             # Vitest 单次运行
pnpm test:watch       # Vitest 监听模式
pnpm lint             # oxlint + eslint（顺序运行，均带 --fix）
pnpm format           # Prettier 格式化
```

### 验证流程

每次改动后按顺序执行：

```bash
pnpm lint        # 代码检查
pnpm type-check  # 类型检查
pnpm test        # 单元测试
pnpm build       # 生产构建
```

### 构建产物

`pnpm build` 完成后，`scripts/postbuild.mjs` 会自动将 `dist/` 复制到后端项目的 `SRAFrontend.Server/wwwroot/` 目录，供 .NET 后端托管前端静态文件。

### 项目结构

```
src/
  api/              # API 服务模块（一个文件对应一个后端 Controller）
    http.ts         # Axios 客户端（R<T> 解包、认证 token、错误归一化）
  components/       # Vue 组件（Element Plus 组件自动导入，无需手动 import）
  composables/      # 组合式函数（任务运行、日志流、主题色相）
  configs/          # 站点元数据（标题、作者、仓库地址）
  router/           # 路由配置（5 个路由 + 401 全局处理）
  stores/           # Pinia Store（configs）
  utils/            # 工具函数（OpenAPI Schema 解析、Markdown 渲染）
  views/            # 页面视图
```

## 测试

```bash
pnpm test        # 单次运行
pnpm test:watch  # 监听模式
```

测试文件位于各模块的 `__tests__/` 目录。API 测试 mock `request` 函数（来自 `http.ts`），不直接 mock Axios。

## 相关项目

- [StarRailAssistant](https://github.com/Shasnow/StarRailAssistant) — 后端服务与自动化核心
