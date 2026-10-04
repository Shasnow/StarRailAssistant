# 演示模式（静态部署）

演示模式让本项目在**没有任何后端服务**的情况下，作为独立静态网站部署运行：所有后端 API 由内置模拟层在浏览器内响应，界面、表单、任务流程、日志等交互完整可用。

## 1. 演示模式是什么

- 模式在**构建/启动期**唯一确定，由 `.env.demo` 中的 `VITE_DEMO_DEFAULT=1` 控制（仅 `--mode demo` 时加载）。
- **运行时没有任何切换开关**：无 localStorage 开关、无 URL 参数、无页面内切换按钮。切换方式就是换命令构建。
- 演示构建下，导航栏常驻一枚"演示模式"只读徽标；正式构建下该分支在编译期被消除，不渲染任何元素。

### 进入方式

```bash
pnpm dev:demo     # 本地开发（演示模式，端口 5173）
pnpm build:demo   # 产出可直接静态托管的演示站（dist/）
```

### 与正式模式的切换

| 场景     | 命令              | 结果                                        |
| -------- | ----------------- | ------------------------------------------- |
| 正式开发 | `pnpm dev`        | 代理 `/api` → `localhost:5073` 真实后端     |
| 正式构建 | `pnpm build`      | 正式产物，postbuild 照常拷贝到 wwwroot      |
| 演示开发 | `pnpm dev:demo`   | 内置模拟层，无后端也完整可用                |
| 演示构建 | `pnpm build:demo` | 静态演示产物（含 `404.html`、`_redirects`） |

两个构建共用同一份源码；`build:demo` 不触发 `postbuild` 的 wwwroot 拷贝。

## 2. 构建步骤与部署指南

### 通用静态托管

```bash
pnpm install
pnpm build:demo
# 产物在 dist/，直接上传即可
```

托管端（GitHub Pages / Netlify / Cloudflare Pages 等）开启 gzip 或 brotli 压缩即可，Vite 已完成 JS/CSS 压缩、hash 文件名与按需分包。

### GitHub Pages

1. 构建：`pnpm build:demo`
2. **子路径部署**：仓库为 `用户名.github.io/仓库名` 形式时需设置基路径：

   ```powershell
   # PowerShell
   $env:VITE_BASE='/仓库名/'; pnpm build:demo
   ```

   或在 `.env.demo.local` 中写入 `VITE_BASE=/仓库名/`（该文件不入库）。

3. SPA 路由回退：构建产物已包含 `404.html`（内容为 `index.html`），GitHub Pages 会用它响应任意未知路径，前端路由正常工作，无需额外配置。

### Netlify

1. 构建命令 `pnpm build:demo`，发布目录 `dist`
2. 产物已包含 `_redirects`（`/* /index.html 200`），SPA 路由自动回退，无需额外配置。

### 本地预览

```bash
pnpm build:demo
pnpm preview     # 预览 dist/ 产物
```

## 3. 模拟数据与错误场景

- **延迟**：所有 API 请求 120–500ms 随机延迟，UI loading 态自然生效。
- **确定性错误**（不随机注入故障，保证演示可重复）：

| 操作                   | 结果                                                           |
| ---------------------- | -------------------------------------------------------------- |
| 创建已存在的配置名     | 409：`配置 "x" 已存在`                                         |
| 配置名为空或含非法字符 | 400：`配置名不能为空` / `配置名不能包含以下字符：…`            |
| 读取/删除不存在的配置  | 404：`资源不存在`                                              |
| 运行时再次启动任务     | 409：`已有任务正在运行`                                        |
| 运行不存在的配置       | 400：`配置 "x" 不存在`                                         |
| 空闲时停止任务         | 409：`当前没有任务在运行`                                      |
| 未模拟的接口           | `success:false`，提示"演示模式：该接口暂未模拟" + console.warn |

- **任务生命周期**：启动 → running（日志持续产出）→ 停止或 45 秒自动完成 → 空闲；进度按耗时推算，共 12 步。
- **登录流程**：演示后端模拟「已启用访问认证」——除 `/auth` 外的业务请求不带 `X-Access-Token` 一律返回 401，触发既有 401 处理链跳转登录页；输入任意非空 token 经 `/auth` 校验通过后保存并回跳，复刻完整真实登录流程。
- **初始数据**：内置 `日常清体力`、`周本速刷`、`签到跑图` 三份配置，配置结构由 `src/demo/v1.json`（OpenAPI 规范快照）生成默认值。

## 4. 功能限制

- **演示数据存在浏览器 localStorage**（key：`sra_demo_state_v1`）：换浏览器、隐私模式或清除站点数据即恢复出厂演示数据。
- **背景图为外链静态图**：`installDemoMode()` 将 `siteConfig.bgUrl` 覆盖为 `https://shasnow.top/gallery/starrailassistant/default.jpg`（字符串仅存在于 demo 分包，正式产物不包含），加载失败时走既有渐变兜底。
- **后端管理卡片仅为模拟**：重启/停止后端只返回提示文案，不产生任何真实操作。
- **登录为模拟认证**：首次访问演示站（或本地无 `sra_token` 时）会先进登录页；任意非空 token 通过校验，不代表任何安全校验。登录页提示文案在演示构建下自动切换为演示说明（`__IS_DEMO__` 编译期分支，正式产物仍为原文案）。
- **外域功能照常依赖网络**：公告（starrailassistant.top）与 GitHub 仓库卡片走真实外域请求，离线环境下这两处不可用（其余功能不受影响）。
- **未覆盖的后端接口**会返回"该接口暂未模拟"提示，可在浏览器 console 中通过 `[demo]` 前缀发现遗漏。

## 5. 与正式环境的关系

- **物理隔离**：全部模拟代码位于 `src/demo/`，仅 `src/main.ts` 在演示模式下动态 `import('./demo/install')` 装载。
- **编译期判定**：`vite.config.ts` 按 `.env.demo` 的 `VITE_DEMO_DEFAULT` 经 `define` 注入编译期常量 `__IS_DEMO__`，各调用点内联为字面量——正式构建下所有演示分支与 demo 分包被整体消除，**正式产物不包含任何演示代码**。
- **生产模块的侵入最小**：`openapi.ts`、`live.ts` 各加一个 3-4 行的 `__IS_DEMO__` 动态 import 分支；`useLogStream.ts` 通过可注入的日志源工厂兼容两种模式；`http.ts` 及各 API 模块零改动（演示层直接替换 axios adapter）。
- **性能**：演示代码独立分包且仅演示构建加载；`manualChunks` 将 Element Plus 与 Vue 生态拆分为独立 chunk 提升缓存命中；路由保持懒加载。
- **测试**：演示层用例位于 `src/demo/__tests__/`，正式环境用例不受影响。
