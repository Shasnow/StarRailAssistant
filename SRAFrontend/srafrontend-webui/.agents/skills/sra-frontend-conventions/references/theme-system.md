# OKLCH 主题色彩系统详解

源文件：`src/assets/base.css`（全部 token 与规则）、`src/composables/useThemeHue.ts`（色相管理）、`src/components/ThemeHuePicker.vue`（切换 UI）、`scripts/check-contrast.mjs`（对比率 gate）。

## 派生模型

全站颜色由单一色相 `--hue`（0-360 无单位数字）派生，写入 `<html>` 内联样式并持久化到 localStorage `theme-hue`（默认 163）：

- 中性/表面/主色：`oklch(L C var(--hue))`，低饱和着色（C 0.003~0.02）
- 语义四色：固定色相 + 与主色共享 L/C 坡道——success 150 / warning 80 / danger 27 / info 262
- 深浅两套 token：`:root`（浅色档）与 `:root.dark`（深色档），`useDark` 切换 `<html>` 的 `.dark` 类
- `--hue` 缺失时 `:root` 内默认值兜底（防 IACVT）

## EP 变量覆盖陷阱（核心教训）

unplugin-vue-components 按需引入 EP 组件时会在**运行时注入**独立的 `:root`(0,1,0) 样式表（`--el-color-primary: #409eff` 等），晚于 main.css 注入，同级特异性后来居上——普通 `:root` 块里的 EP 重映射会在浅色模式失效。

正确结构（base.css 内顺序固定）：

1. `:root` — 项目 token（浅色档），不含 `--el-*`
2. `:root:root`（0,2,0）— EP 浅色重映射。双写提升特异性后无论注入顺序均胜出，也高于 EP dark 的 `html.dark`(0,1,1)。light-N 向白混（悬停/plain 背景），dark-2 向黑混（按下）
3. `:root.dark`（0,2,0）— 仅深色专属内容：
   - 方向反转的 ramp（light-N 向 `--color-background` 混变暗、dark-2 向白混变亮）。等特异性下靠声明顺序压过 `:root:root`
   - 深色字面值：placeholder（oklch 0.55）、disabled（0.5）、border/fill 方向性变体
   - **勿重复声明基础映射**（`--el-color-primary: var(--color-primary)` 等间接引用）——已在 `:root:root` 提供，token 本身随 `:root.dark` 翻转自动适配

导入顺序（`src/assets/main.css`）：EP index.css → EP dark/css-vars.css → `./base.css`。`src/main.ts` 只留 `import './assets/main.css'`。

## .terminal-scope 恒深寄存器

全局类（base.css），挂载后内部恒为深底，两种模式下终端背景不变（`--terminal-*` 固定深色族，仅随色相微着色，对应原 #141414/#1f1f1f/#2d2d2d 等）。同时把语义 token 重注册为固定深色档：success/warning/danger/info、muted、text→terminal-text、text-secondary→terminal-time。

- `:root.dark` 只匹配 `<html>`，不与组件内元素竞争，后代自然继承覆盖值
- 已挂载：LogView 的 `.term-shell`、LiveViewCard 的 `.live-screen`
- 新增终端类区域：挂 `.terminal-scope` + 用 `--terminal-*` 族与语义 token，勿写死深色

## 对比率 gate 脚本

`node scripts/check-contrast.mjs`——从 base.css 提取 `:root` / `:root.dark` / `.terminal-scope` token，按 CSS Color 4 算法计算对比率：

- 门槛：text/heading ≥7，secondary/muted/primary/语义/终端深色档/hint ≥4.5，白字对深色 primary ≥3
- 豁免警告：warning 黄色（黄绿色相白字 ≥4.5 数学不可达）与 hue 60-110 的 primary
- 输出 8 个预设色相（0/30/60/163/200/250/300/330）的报告；失败 exit 1

调 L 值保持通过的参考基线：浅色 primary L 0.53、深色 primary L 0.64、terminal-time L 0.60。改动任何 token 的 L/C 后必须重跑。

## 主题切换动画（勿破坏的既有约束）

- VueUse `useDark({ storageKey: 'theme' })`
- View Transitions API，400ms 圆形揭示：浅→深裁剪旧（浅）视图向按钮收缩，深→浅裁剪新（浅）视图从按钮扩张
- 动画 CSS 驱动（`html[data-theme-transition='to-dark'|'to-light']` 选择 `@keyframes theme-change`，fill both）；圆心/半径由 NavBar `toggleTheme` 写入 `--theme-transition-x/y/radius`
- 过渡逻辑必须在按钮 click 处理器内——放 `useDark` 的 onChanged 会在初始化时同步触发（TDZ 错误）且主题已变更后才触发（切回闪烁）

## ThemeHuePicker

NavBar 弹层（el-popover 264px click 触发）：预览块 + 色相滑块（0-360，彩虹滑轨为显式 13 档 `oklch(0.6 0.14 N)` 渐变保证跨浏览器确定性）+ 8 预设色点 + 重置。`useThemeHue` 为模块级单例，`setHue` 钳制取整后写 `<html>` 内联样式，CSS 变量更新即全站即时生效。触发按钮 36px 圆钮、样式自含（不依赖父组件 scoped）。
