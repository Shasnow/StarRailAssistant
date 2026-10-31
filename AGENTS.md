# AGENTS.md

StarRailAssistant (SRA) automates *Honkai: Star Rail* via screen recognition. Windows-only; the game window must be
1920x1080 (fullscreen at 1080p, windowed above it) or recognition fails. Python 3.12 backend + .NET 10 frontend
(Avalonia desktop / ASP.NET Core server) + Vue 3 WebUI.

## Repository layout

- `main.py` — backend entry point (delegates to `SRACore/__main__.py`).
- `SRACore/` — CLI (`cli2.py`, cmd2-based), task/extension registries, operators (vision + input), notifications,
  `services/`（进程内宿主 `AppContext` 与设置/配置/缓存/应用信息/后端/日志流等框架无关服务，CLI 与服务端复用）,
  utils, generated models.
- `tasks/` — task implementations.
- `extensions/` — extension implementations; `extensions/cw_plus/` is a large self-contained subsystem.
- `resources/img/**` — image templates, referenced only through `tasks/img.py` constants.
- `tests/` — pytest suite for the backend.
- `SRAFrontend/` — .NET solution: `SRAFrontend` (shared core), `SRAFrontend.Desktop` (Avalonia).
- `SRAServer/` — Litestar 装配层（`/api/**` REST、`/openapi/v1.json`、MCP 于 `/mcp`、WebUI 静态托管）：
  `context.py::ServerContext` 组合 `SRACore.services.AppContext` 并叠加服务端配置（AccessToken / 访问模式），
  业务实现全部来自 `SRACore`（不再以 stdio 子进程调用 CLI）。
- `SRAFrontend/srafrontend-webui/` — Vue 3 + Element Plus WebUI. **It has its own `AGENTS.md`; read it before working
  in that subtree.**
- `scripts/` — packaging, version bumping, model/localization generation, cleanup.

## Commands

Setup (Python 3.12 only, `requires-python >=3.12,<3.13`):

```bash
pip install -e ".[full]"   # full = desktop deps (pyautogui/pywin32/...); ".[dev]" for pytest
```

Run the backend:

```bash
python main.py                        # interactive CLI; self-elevates unless --no-admin
python main.py -c "task run Default"  # one-shot command(s); '+' chains several
```

Test:

```bash
pytest                                                                 # full suite (10 tests)
python -m pytest tests/test_main.py -q                                 # one file
python -m pytest tests/test_runner_blocking.py::test_start_and_wait_blocks_until_worker_finishes -q
```

Lint — flake8 is configured **only in CI** (`.github/workflows/python-app.yml`), there is no local config file:

```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics   # blocking
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

Frontend / server (from repo root):

```bash
dotnet run --project SRAFrontend/SRAFrontend.Desktop/SRAFrontend.Desktop.csproj
python -m SRAServer                                                            # http://localhost:5073（需 pip install -e ".[server]"）
```

Console scripts (available after `pip install -e .`, `uv tool install starrailassistant`, `pipx install …`):

```bash
sra            # 统一入口，默认启动交互式 CLI（sra-cli 为等价别名）
sra serve      # 启动 Litestar 服务端（sra-server / python -m SRAServer 等价）
```

`sra serve` 与 `sra-server` 共用 `SRAServer.__main__.run_server`：启动前会检查 `[server]` extra 依赖
（缺失时提示 `--extra server` 安装命令）。服务端代码始终来自已安装的 `SRAServer` 包；WebUI 是独立产物，
由 `sra init` 下载的 WebUI 包解压到当前目录 `SRAServer/static`，`SRAServer/app.py::_resolve_static_dir`
优先采用该目录（包内不含构建产物）。

Repo scripts:

```bash
npm run build      # dotnet publish -c Release -r win-x64 SRAFrontend/SRAFrontend.sln && python scripts/package.py
npm run modelgen   # regenerate SRACore/models/*.py from the C# models
npm run pyl10nc    # regenerate localization from SRACore/localization/resource.toml
npm run ver | ver:release | ver:patch | ver:pre
npm run clean      # recursively drop __pycache__
```

## Architecture

**Frontend ↔ backend is CLI-over-stdio.** The frontend spawns the Python backend as a child process and writes commands
to its stdin; there is no private IPC protocol. `-c`/repl input is appended to `sys.argv` and executed by
`SRACore/cli2.py`. Every command accepts `--json` and then prints the `{success, message, data}` envelope
(`SRACore/cli2.py::output`) that the HTTP API returns as `R`. `SRAFrontend/SRAFrontend/Services/LocalBackendService.cs`
holds the exact commands issued (`task run <config>`, `task status --json`, `operator call <method> '<json>' --json`,
`extension schema <id> --json`, …). **Changing a `--json` payload shape is a cross-language API change** — update
`LocalBackendService.cs` and the WebUI together.

**Server surface.** `SRAServer` (Litestar, Python) exposes `/api/**` REST, `/openapi/v1.json`, the static WebUI,
and MCP tools at `/mcp` (`SRAServer/mcp/server.py`: `sra_screenshot`, `sra_task_run`, `sra_operator_call`,
`sra_config_update`, …). It runs as a single process hosting `SRACore` in-process, so task/extension/config/operator
state is shared directly instead of being driven through the CLI. The WebUI generates its task and settings forms
from the OpenAPI schema, so backend config models are the source of truth for the web UI.

**Core services (`SRACore/services/`).** Framework-independent business logic lives here and is shared by both hosts:
`app_context.py::AppContext` owns the task/extension/operator orchestration (plus hotkeys, screenshot, settings/config/
cache/app-info/log-stream services). `SRACore/__main__.py` builds one for the CLI; `SRAServer/context.py::ServerContext`
wraps one with the server config. `SRAServer` keeps only assembly (`controllers/`, `middleware.py`, `openapi.py`,
`app.py`, `config.py`, `context.py`, `mcp/`, `schemas/`), so path/JSON envelopes and CLI `--json` output stay as they are.

**Dynamic imports.** `tasks/` and `extensions/` are not packages (no `__init__.py`). `SRACore.util.dynamic_import`
and `load_extensions()` scan `*.py` and import them, relying on `main.py` putting cwd on `sys.path`. Both are
therefore run from the repo root and read paths like `tasks/config/trailblaze_power.toml` and `resources/img/...`
**relative to cwd**.

**Registries.** Tasks use `@task(order=N)`, extensions use
`@extension(extension_id=..., background=...)` (`SRACore/task/__init__.py`, `SRACore/extension/__init__.py`).
Registration happens at import time, so dropping a file into `tasks/` or `extensions/` is usually all that is needed;
`task reload` / `extension reload` re-import in place for hot reload. Extension config models are Pydantic models
taken from the decorator's generic parameter and served as JSON Schema for form generation.

**Task contract.** Subclass `BaseTask` and implement `run() -> bool` (`False` = failure). `TaskManager.run()` walks
the enabled tasks of each config, calls `on_start`/`on_failed`/`on_completed` (which fan out to notifications) and, on
failure, delegates to `SRACore/util/task_recovery.py` to kill and relaunch the game before retrying the same config.
`TaskManager` and `ExtensionRunner` both subclass `SRACore/thread/runner.py::Runner` and **share one global work
thread**: at most one task or extension runs at a time, and `task stop` must request the stop on *both* runners.

**Vision and input.** Everything goes through `IOperator` (`SRACore/operators/ioperator.py`): template matching
(`locate`, `locate_all`, `locate_any`, `click_img`, `wait_img`), RapidOCR (`ocr`, `ocr_match`, `ocr_boxes`), HSV
color and rectangle detection. Implementations are `Operator` (PyAutoGUI/PyWin32, local game) and `BrowserOperator`
(Selenium, cloud game), chosen by `OperatorFactory`. `WindowContext` is shared between instances and `full_screen`
switches coordinates from window-relative to whole-screen. **Coordinate rule:** `int` args are absolute pixels,
`float` args are ratios (0–1) of the window; offsets follow the same convention.

**State on disk.** `%APPDATA%/SRA` (Linux: `~/.config/SRA`) holds `settings.json`, `configs/<Name>.json`, `cache.json`
and `cache/…` (`SRACore/util/const.py`, mirrored by `SRAFrontend/SRAFrontend/Data/DataPath.cs`); frontend and backend
read and write the **same** files. Python-side access goes through `SRACore/util/data_persister.py`, which also
migrates legacy config shapes. Runtime logs and failure screenshots go to the repo-local `log/` directory (gitignored).

## Conventions

- **Language.** Commit messages are Chinese conventional commits (`.trae/rules/git-commit-message.md`); comments,
  docstrings, log messages, task names and UI strings are Chinese. `README.md` is the Chinese source document — keep
  it Chinese, mirror edits into `README.en.md`, and keep the language-switch links at the top of both.
- **Generated files — never hand-edit.** `SRACore/models/app_settings.py` and `SRACore/models/tasks_config.py` come
  from `SRAFrontend/SRAFrontend/Models/*.cs` via `npm run modelgen`; `SRACore/localization/resource.py`,
  `resource_zh-cn.json` and `resource_en-us.json` come from `resource.toml` via `npm run pyl10nc`. Edit the C# model
  or the TOML, then regenerate. WebUI `ResX` localization is updated by hand. The two model files are Pydantic models
  and are the **only** Python model definitions: `SRACore` uses them for `settings.json` / `configs/*.json` and
  `SRAServer` expands them into the `/openapi/v1.json` components (`SRAServer/openapi.py`), so never re-declare a
  mirror model on the server side.
- **Version lives in three files**: `SRACore/util/const.py` (`VERSION`, which drives `pyproject.toml`),
  `package.json` and `SRAFrontend/SRAFrontend/Models/AppSettings.cs`. Change them together with `npm run ver`.
- **Localization** is attribute-style on the `Resource` singleton (`Resource.cli_intro`), resolved by
  `__getattribute__` from the generated JSON, with `str.format` placeholders in the TOML values.
- **Logging** uses `loguru` (`SRACore/util/logger.py`); do not add `print` for diagnostics.
- **Errors** use the coded enum in `SRACore/util/errors.py` (`SRA-XXXX-YYYY`, level prefixes 1xxx system … 9xxx
  other). `ThreadStoppedError` is the cooperative-stop signal recognized by `Runner` and the operators.
- **Types**: `from __future__ import annotations`, `StrEnum`, dataclasses and `# pyright: ignore[...]` markers around
  the `@task`/`@extension` decorators are the house style; follow it rather than loosening types.
- **Adding a user-visible field** means changing the backend model/schema: desktop Views bind to task configs and the
  WebUI renders from OpenAPI, so both follow the backend.
- **Release notes live in `ChangeLog2.0.md`.** `scripts/package.py` reads it, substitutes `${VERSION}` and writes the
  gitignored `version_info.txt` (first line = release name/tag) consumed by CI — edit the changelog, not
  `version_info.txt`. `.github/workflows/python-app.yml` builds releases (Nuitka + Inno Setup + multi-zip artifacts),
  `pypi.yml` publishes to PyPI, and `scripts/package.py` decides which files land in the Lite/Core/Resources/Server
  zips.

## Known issues

Three backend tests currently fail on `main` from drift — do not treat them as regressions from your change, but do
fix them if you touch the relevant modules:

- `tests/test_main.py::test_main_version_option_exits_cleanly` patches `main.load_app_settings`, which no longer exists.
- `tests/test_notification_system.py::test_channel_test_notification_catches_channel_exception` patches
  `service.load_notification_settings`, which no longer exists.
- `tests/test_tasks_notifications.py::test_load_all_tasks_and_trigger_start_complete_notifications` expects the five
  core tasks to be registered merely by importing the test module; the test must import them itself.