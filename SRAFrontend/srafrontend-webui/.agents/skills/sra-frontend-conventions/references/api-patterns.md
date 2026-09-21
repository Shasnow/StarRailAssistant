# API 层模式详解

源文件：`src/api/http.ts`（Axios 客户端）、`src/api/*.ts`（每后端控制器一个文件）、`src/composables/useTaskRunner.ts` / `useLogStream.ts`。

## http.ts 核心机制

- 所有后端响应为 `R<T>` 信封 `{ success, message, data }`
- 响应拦截器：`success=true` 自动解包返回 `data`；`success=false` 抛 `ApiError`（携带 message）
- `rawEnvelope: true`（axios config 扩展，declare-module 声明在 http.ts 内）：跳过解包与抛错，返回完整信封。适用场景——`success=false` 是业务正常态（如 `Task/status` 空闲时返回 `success=false` + "No response from backend"，前端映射为 stopped）；或需要把 message 直接展示给用户（配合 `requestEnvelope()`）
- `requestEnvelope()`：返回完整 `R` 信封（保留 message），不抛业务错

## 认证与端点

- token 存 localStorage `sra_token`，Axios 附加 `Bearer` 头
- EventSource（SSE）无法设请求头，以 `?access_token=` 查询参数传递（日志流 `/api/backend/logs/stream`）
- dev 代理：`/api`、`/openapi` → `http://localhost:5073`；截图 `/api/backend/screenshot`
- 外部公告接口（starrailassistant.top）CORS 已放开，直连不走代理

## 关键端点约定

- 任务控制：POST `/api/Task/run`（RunRequest `{configName, config, persist}`）、POST `/api/Task/stop`、GET `/api/Task/status`
- 后端 RuntimeInfo（Python dataclass，snake_case JSON）：status ∈ idle|running|completed|failed|stopped，另有 session_id/pid/mode/configs/unit/error/progress
- 前端 `TaskStatus` 类型字段名与后端**完全一致**（用户明确要求，勿重命名）；`normalizeTaskStatus` 只做形状兜底（缺失/非法→默认值），不做字段映射
- 后端运行时控制：POST `/api/backend/restart`、`/api/backend/stop`
- 设置：GET `/api/Settings` → `R<AppSettings>`；PUT `/api/Settings`（按 section 部分提交 JSON）→ `R<string[]>` 更新的 key 列表

## OpenAPI 驱动表单

- 配置结构由后端定义：`TasksConfigPanel` 与设置页均拉取 `/openapi/v1.json`，按 schema 动态生成表单
- 设置页引用 `#/components/schemas/AppSettings`，5 个 section（general/display/update/advanced/notification）
- 工具函数在 `src/utils/schemaForm.ts`：`resolveNode`（解 $ref）、`buildDefaultModel`、`stableStringify`（脏检测用稳定序列化）
- 已知陷阱：`SchemaForm.vue` 只处理对象分支里的数组；**顶层数组**必须用 `SchemaArrayEditor.vue`，否则被渲染成合并的文本输入框

## 组合式函数模式

- `useTaskRunner`：仅在运行中每 1s 轮询 status（不常驻轮询）
- `useLogStream`：SSE 指数退避重连（MAX_RECONNECT 上限）；初始可见条目来自 `restoreCache()` 时**不会**触发非 immediate 的 watcher——需要滚动的页面在 `onMounted` 显式调一次 `scrollToBottom()`
- 日志页不用 keep-alive：切页断开 SSE、回页重连，滚动位置由上述调用恢复

## 测试写法

- 测试与源码同目录 `__tests__/`，环境按文件用 `// @vitest-environment jsdom` 注释启用
- API 层测试：vi.mock `request`（`http.ts` 导出），不 mock axios 本体
- HTTP 级测试（验证拦截器/解包行为）：替换 `http.defaults.adapter` 避免真实网络
- 改后请按 SKILL.md 的验证顺序跑 `pnpm test`（当前 72 用例基线）
