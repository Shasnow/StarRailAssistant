# AGENTS.md

StarRailAssistant (SRA) automates *Honkai: Star Rail* via screen recognition. Windows-only; the game window must be
1920x1080 (fullscreen at 1080p, windowed above it) or recognition fails. Python 3.12 backend + .NET 10 frontend
(Avalonia desktop) + Litestar server + Vue 3 WebUI.

## Repository layout

- `main.py` — 后端入口（委托 `SRACore/__main__.py`）。
- `SRACore/` — CLI（`cli2.py`，cmd2）、任务/扩展注册表、operators（视觉+输入）、通知、`services/`
  （框架无关宿主 `AppContext` 与设置/配置/缓存/应用信息/后端/日志流服务，CLI 与服务端复用）、utils、生成的模型。
- `tasks/`、`extensions/` — 任务与扩展实现。每个扩展是含 `__init__.py` 的目录包，可带
  `locales/<lang>.json` 与子包（`extensions/currency_wars_plus/cw_plus/` 为大型自包含子系统）。
- `resources/img/**` — 模板图片，只经 `tasks/img.py` 常量引用。
- `tests/` — 后端 pytest 套件。
- `SRAServer/` — Litestar 装配层（`/api/**`、`/openapi/v1.json`、MCP 于 `/mcp`、WebUI 静态托管）：
  `context.py::ServerContext` 组合 `SRACore.services.AppContext`，业务实现全部来自 `SRACore`。
- `SRAFrontend/` — .NET 方案：`SRAFrontend`（共享核心）、`SRAFrontend.Desktop`（Avalonia）。
- `SRAFrontend/srafrontend-webui/` — Vue 3 + Element Plus WebUI；**该子树有自己的 `AGENTS.md`，动手前先读**。
- `scripts/` — 打包、版本、模型/本地化生成、清理。

## Commands

**python命令需要使用venv环境**

```bash
pip install -e ".[standard]"                          # standard = 桌面依赖；跑测试用 ".[dev]"
python main.py                                        # 交互式 CLI；自提权（--no-admin 跳过）
python main.py -c "task run Default"                  # 单次执行；'+' 串联多条
python -m pytest tests/test_main.py -q                # 单文件测试；全量套件很慢，不要每次都跑
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics   # CI 阻塞项（无本地配置）
dotnet run --project SRAFrontend/SRAFrontend.Desktop/SRAFrontend.Desktop.csproj
python -m SRAServer                                   # http://localhost:5073（需 ".[server]"）
sra | sra-cli                                         # 统一入口，默认交互式 CLI
sra serve                                             # = sra-server = python -m SRAServer，启动前检查 [server]
docker compose up -d                                  # 服务端镜像，http://localhost:5073
npm run build | modelgen | pyl10nc | ver | clean
```

`sra serve` 与 `sra-server` 共用 `SRAServer.__main__.run_server`。服务端代码始终来自已安装的 `SRAServer` 包；
WebUI 是独立产物，由 `sra init` 下载的 WebUI 包解压到当前目录 `SRAServer/static`，`SRAServer/app.py::
_resolve_static_dir` 优先采用该目录（包内不含构建产物，wheel 场景必须 `sra init`）。

Docker 镜像由 `.github/workflows/docker.yml` 构建并推送 `ghcr.io/shasnow/starrailassistant`（`beta`/`latest`/
`v<版本>`/`sha-<哈希>`），内含 WebUI、tasks/extensions/resources 与 Chromium，启动不联网，也从不执行 `sra init`。

## Architecture

**Frontend ↔ backend is CLI-over-stdio.** 前端把 Python 后端作为子进程，用 stdin 写命令；`-c`/repl 输入追加到
`sys.argv` 后由 `SRACore/cli2.py` 执行。每条命令都支持 `--json`，输出 `{success,message,data}` 信封
（`SRACore/cli2.py::output`），HTTP API 以 `R` 返回同一结构；`R.message` 固定英文、不做本地化，
需要本地化的展示文本放在 `data` 中。`SRAFrontend/SRAFrontend/Services/LocalBackendService.cs`
保存了确切的命令串（`task run <config>`、`task status --json`、`operator call …`）；**改 `--json` payload 是跨语言
契约变更**，需同步 `LocalBackendService.cs` 与 WebUI。

**Server surface.** `SRAServer` 单进程内托管 `SRACore`，因此任务/扩展/配置/operator 状态直接共享，不再经 CLI。
WebUI 的任务与设置表单由 OpenAPI schema 生成，后端配置模型即 Web UI 的唯一来源；MCP 工具在
`SRAServer/mcp/server.py`（`sra_screenshot`、`sra_task_run`、`sra_operator_call`、`sra_config_update` …）。

**Core services (`SRACore/services/`).** 框架无关业务逻辑，两个宿主共用：`app_context.py::AppContext` 负责
任务/扩展/operator 编排（含快捷键、截图、设置/配置/缓存/应用信息/日志流）；`SRACore/__main__.py` 供 CLI，
`SRAServer/context.py::ServerContext` 组合它并叠加服务端配置。`SRAServer` 只保留装配（`controllers/`、
`middleware.py`、`openapi.py`、`app.py`、`config.py`、`context.py`、`mcp/`、`schemas/`）。

**Dynamic imports.** `tasks/` 不是包（无 `__init__.py`），由 `SRACore.util.dynamic_import` 扫描 `*.py` 导入；
`extensions/` 只加载含 `__init__.py` 的一级目录包（`load_extensions()`），遗留单文件会被忽略并告警。
两者都依赖 `main.py` 把 cwd 加入 `sys.path`，因此从仓库根运行，`tasks/config/*.toml`、`resources/img/...`
都按 cwd 相对解析。

**Registries.** 任务用 `@task(order=N)`、扩展用 `@extension(extension_id=..., background=...)`，导入即注册；
`task reload` / `extension reload` 原地重导入（扩展包会递归重载子模块）。扩展配置模型取自装饰器泛型参数，
转 JSON Schema 供表单生成；字段说明的多语言文案放在扩展目录的 `locales/<lang>.json`
（键为 schema 字段键名，有 `alias` 用 alias），注册表在 `get_schema()` 时按 `settings.json`
的界面语言合成单语 `description` / `x-enum-labels`（缺失回退中文）。

**Task contract.** 继承 `BaseTask` 实现 `run() -> bool`（`False` 为失败）。`TaskManager.run()` 遍历每个配置中
启用的任务，调用 `on_start`/`on_failed`/`on_completed`（分发通知），失败时经 `SRACore/util/task_recovery.py`
杀进程并重启游戏后重试同一配置。`TaskManager` 与 `ExtensionRunner` 都继承 `SRACore/thread/runner.py::Runner`
且**共用同一工作线程**：同一时刻只跑一个任务或扩展，`task stop` 必须在两个 runner 上都请求停止。

**Vision and input.** 一律通过 `IOperator`（`SRACore/operators/ioperator.py`）：模板匹配（`locate`/`locate_all`/
`locate_any`/`click_img`/`wait_img`）、RapidOCR（`ocr`/`ocr_match`/`ocr_boxes`）、HSV 颜色与矩形检测。
实现为 `Operator`（PyAutoGUI/PyWin32，本地）与 `BrowserOperator`（Selenium，云游戏），由 `OperatorFactory` 选择。
`WindowContext` 在实例间共享，`full_screen` 在窗口相对坐标与全屏坐标间切换。**坐标规则**：`int` 为绝对像素，
`float` 为窗口比例（0–1），偏移量同规则。

**Packaging.** `scripts/package.py` 决定各产物内容：Core（内嵌 Python 运行时 `python/` + `main.py` + 源码/资源）、
Full（Core + 桌面端 publish）、Lite（桌面端 + 源码 + `pyproject.toml`，用户自行 pip 安装）；WebUI 包
（`SRAServer/static/**`）与 Resources 包（tasks/extensions/resources）上传 R2 供 `sra init` 下载，二者**不带
`manifest.md5.json`**，以免覆盖整包的完整性清单。

**State on disk.** `%APPDATA%/SRA`（Linux `~/.config/SRA`）存 `settings.json`、`configs/<Name>.json`、`cache.json`
与 `cache/…`（`SRACore/util/const.py`，前端镜像于 `SRAFrontend/SRAFrontend/Data/DataPath.cs`）；前后端读写**同一批
文件**。Python 侧经 `SRACore/util/data_persister.py`（含旧配置迁移）。运行日志与失败截图在仓库本地 `log/`（gitignore）。

## Conventions

- **Language.** 提交消息中文约定式（`.trae/rules/git-commit-message.md`）；注释、文档、日志、任务名、UI 文案中文。
  `README.md` 为中文源文件，改动同步 `README.en.md`，两者顶部保留语言切换链接。
- **Generated files — never hand-edit.** `SRACore/models/app_settings.py`、`tasks_config.py` 由
  `SRAFrontend/SRAFrontend/Models/*.cs` 经 `npm run modelgen` 生成；`SRACore/localization/resources.py` 与
  `resources_*.json` 由 `resources.toml` 经 `npm run pyl10nc` 生成。改 C# 模型或 TOML 后重新生成。这两个模型文件是
  唯一的 Python 模型定义（`SRACore` 读写 `settings.json`/`configs/*.json`，`SRAServer` 经 `openapi.py` 展开成
  `/openapi/v1.json` 组件），**不要在服务端再声明镜像模型**。WebUI `ResX` 本地化为手工维护。
- **Version lives in three files**: `SRACore/util/const.py`（`VERSION`，驱动 `pyproject.toml`）、`package.json`、
  `SRAFrontend/SRAFrontend/Models/AppSettings.cs`，三者配合 `npm run ver` 一起改。
- **Localization** 为 `Resources` 单例的属性式访问（`Resources.cli_intro`），由 `__getattribute__` 从生成 JSON 解析，
  TOML 值中使用 `str.format` 占位符。
- **Logging** 用 `loguru`（`SRACore/util/logger.py`），不要用 `print` 做诊断。
- **Errors** 用 `SRACore/util/errors.py` 的编码枚举（`SRA-XXXX-YYYY`，级别前缀 1xxx 系统 … 9xxx 其他）；
  `ThreadStoppedError` 是 `Runner` 与 operators 识别的协作停止信号。
- **Types**: 使用 `from __future__ import annotations`、`StrEnum`、dataclass，以及 `@task`/`@extension` 装饰器处的
  `# pyright: ignore[...]`；保持风格而不是放松类型。
- **Adding a user-visible field** 必须改后端模型/schema：桌面端绑定任务配置、WebUI 由 OpenAPI 渲染，两者跟随后端。
- **Release notes live in `ChangeLog2.0.md`.** `scripts/package.py` 读取它、替换 `${VERSION}` 并写出 gitignore 的
  `version_info.txt`（首行为发布名/tag）供 CI 使用——改 changelog，不要改 `version_info.txt`。
  `.github/workflows/python-app.yml` 构建发布（内嵌 Python + 源码 + `SRA-cli.exe` 启动器 + Inno Setup + 多 zip）；
  构建步骤抽在可复用的 `build-artifacts.yml`（仅上传产物、不发布 release，不触发 Mirror酱 / auto-mas）。
  `pypi.yml` 发布 PyPI。

## Known issues

`main` 上曾有 3 个测试因漂移失败，若未修复请一并处理（不要当成自己改动的回归）：
`test_main.py::test_main_version_option_exits_cleanly`（patch 已不存在的 `main.load_app_settings`）、
`test_notification_system.py::test_channel_test_notification_catches_channel_exception`（patch 已不存在的
`service.load_notification_settings`）、`test_tasks_notifications.py::test_load_all_tasks_and_trigger_*`
（需自行导入五个核心任务才能注册）。
