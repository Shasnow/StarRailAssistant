---
name: sra-frontend-conventions
description: srafrontend-weiui（Vue 3 + Element Plus + Vite + TS strict）的开发约定与已知陷阱。涉及修改主题或颜色、编写样式、新增 API 模块、覆盖 EP 组件变量、日志终端样式或运行项目验证时使用。不适用于其他项目。
---

# srafrontend-weiui 开发约定

单页 Vue 3 应用 + .NET/Python 后端（dev 代理 /api、/openapi → localhost:5073）。UI 文案与代码注释一律中文。Prettier 无分号、单引号、100 列。

## 验证顺序（每次改动后依次执行）

```bash
pnpm lint        # oxlint --fix + eslint --fix --cache
pnpm type-check  # vue-tsc --build
pnpm test        # vitest run
pnpm build       # 生产构建
```

- Windows PowerShell 不支持 `&&`，多命令用 `;` 连接
- `eslint --cache` 会写临时文件，沙箱环境需禁用沙箱运行
- 改动任何颜色 token 后必须加跑 `node scripts/check-contrast.mjs`（WCAG gate：text/heading ≥7，其余 ≥4.5）

## R<T> 信封 API（新增 API 模块必读）

- 所有后端响应为 `{ success, message, data }`；`src/api/http.ts` 拦截器成功时自动解包 `data`，`success=false` 抛 `ApiError`
- 需要自行处理 `success=false` 时传 `rawEnvelope: true`（如 `Task/status` 空闲时返回 `success=false` 属正常态，前端映射为 stopped）
- `requestEnvelope()` 返回完整信封（保留 `message`），适合后端用 message 传提示的场景
- 测试 mock `request`（来自 `http.ts`），不要 mock axios 本体；HTTP 级测试改 `http.defaults.adapter`
- 详细模式（auth token、SSE、OpenAPI 动态表单、测试写法）见 [references/api-patterns.md](references/api-patterns.md)

## OKLCH 主题色彩系统（改颜色必读）

- 全站颜色由单一 `--hue` 派生 `oklch(L C var(--hue))`，**禁止新增硬编码颜色**——新颜色一律先在 base.css 加 token 再引用
- Element Plus 变量重映射必须放在 base.css 的 `:root:root`（特异性 0,2,0）块，且位于 `:root.dark` 之前；放普通 `:root` 会被 unplugin-vue-components 运行时注入的 `:root` EP 样式反超
- `:root.dark` 只放方向反转的 ramp 和深色专属字面值；基础映射是 `var(--color-*)` 间接引用，随 token 翻转自动适配，勿重复声明
- 日志/实时画面等终端区域固定深色：挂全局类 `.terminal-scope`（base.css），语义 token 自动重注册为深色档
- 深浅模式用 VueUse `useDark`（storageKey 'theme'）；View Transitions 400ms 圆形揭示动画的逻辑在 NavBar 的 `toggleTheme`，勿移入 `useDark` 的 onChanged
- token 清单、特异性陷阱细节、对比率脚本用法见 [references/theme-system.md](references/theme-system.md)

## UI 约定

- 新增页面只改 `router/index.ts`：`meta.icon` 直接携带图标组件（`RouteMeta` 类型已扩展 `icon?: Component`），NavBar 无映射表
- 未保存更改指示：6px 圆点 `.dirty-dot`，`background: currentColor`，`margin-left: 4px`
- 深底上的提示文字用固定亮灰 `--color-hint-on-dark`（#8b949e，对比约 5.5:1），不随主题翻转、不设 opacity
- 终端字体栈在 `monospace` 前包含中文字体（PingFang SC / Microsoft YaHei / Noto Sans CJK SC），保证中文与其他区域一致
- 阴影统一用 `var(--shadow-sm)` / `var(--shadow-lg)`，深浅模式各自定义，勿写死 rgba 值
