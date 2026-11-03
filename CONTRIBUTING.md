# 贡献指南

感谢你对 StarRailAssistant 的关注！以下是参与项目开发所需的全部信息。

## 📁 项目结构

```
├── .github/               # 🔧 GitHub相关配置文件
├── scripts/               # 🛠️ 各种脚本文件（如打包脚本）
├── SRACore/               # 🐍 Python后端核心代码 ⭐
│   ├── localization/      # 🌐 本地化支持
│   ├── task/              # 📋 任务相关代码
│   ├── thread/            # 🧵 线程管理
│   ├── triggers/          # ⚡ 触发器实现
│   ├── ui/                # 🎨 UI相关代码
│   └── util/              # 🛠️ 工具函数
├── SRAFrontend/           # 🎯 C#前端代码 (Avalonia框架) ⭐
│   ├── Assets/            # 📦 前端资源文件
│   ├── Controls/          # 🎛️ 自定义控件
│   ├── Data/              # 📊 数据模型
│   ├── Localization/      # 🌐 前端本地化
│   ├── Models/            # 📐 业务模型
│   ├── Services/          # 💼 服务层
│   ├── Styles/            # 🎨 样式定义
│   ├── Utilities/         # 🛠️ 前端工具类
│   ├── ViewModels/        # 🧠 ViewModel层
│   └── Views/             # 🖥️ 视图层
├── tests/                 # 🧪 自动化测试
│   └── backend/           # 🐍 后端单元测试
├── main.py                # 🚪 程序入口文件
├── rapidocr_onnxruntime/  # 👁️ OCR识别相关模型
├── pyproject.toml         # 📋 Python依赖与打包配置
├── resources/             # 📁 资源文件目录
│   ├── img/               # 🖼️ 图像资源
│   ├── test/              # 🧪 测试资源
├── setup/                 # 📦 安装包制作相关文件
├── tasks/                 # 📋 任务实现目录 ⭐
```

## 📋 环境要求

- **操作系统**：Windows 10 或 Windows 11 (推荐)
- **Python**：3.12 或更高版本（需添加到系统环境变量）
- **.NET SDK**：10.0（下载地址：[.NET 10.0 SDK](https://dotnet.microsoft.com/zh-cn/download/dotnet/10.0)）
- **Git**：用于克隆仓库（可选，但推荐）
- **Node.js**：用于执行 npm 脚本（可选）

## 📥 获取源码

```bash
# 克隆仓库
git clone https://github.com/Shasnow/StarRailAssistant.git
cd StarRailAssistant

# 或直接下载 ZIP 压缩包并解压
```

## 📦 安装依赖

```bash
# 安装运行依赖（含桌面端 standard 组，依赖声明单源于 pyproject.toml）
pip install -e ".[standard]"

# 安装开发/测试依赖
pip install -r requirements-dev.txt

# 如果遇到安装失败，尝试使用国内镜像源
pip install -e ".[standard]" -i https://pypi.tuna.tsinghua.edu.cn/simple
```

也可使用 npm 或 yarn:

```bash
npm install
```

## 🏗️ 运行前端

```bash
dotnet run --project SRAFrontend/SRAFrontend.csproj
```

或使用 npm:

```bash
npm run frontend
```

## 🚀 开发模式运行

SRA 采用前后端分离架构：前端（C# / Avalonia）通过 stdin/stdout 与后端（Python）子进程通信。

根据你要调试的目标，选择对应的方式：

### 调试前端 UI 或前后端交互

适用场景：修改前端界面、验证前后端 IPC 通信、测试任务页面的配置绑定等。

```bash
dotnet run --project SRAFrontend/SRAFrontend.csproj
```

或

```bash
npm run frontend
```

#### 启用开发者模式：

在前端 UI 中快速多次点击版本号，进入开发者模式后选择使用 Python 运行后端：

1. 选择 Python 解释器（建议使用虚拟环境），类似于 `C:\path\to\.venv\Scripts\python.exe`
2. 选择 主程序入口文件 `main.py`，通常位于项目根目录下

后端将自动重启，并切换到 Python 运行模式，方便你在UI中调试后端代码。

### 调试后端任务逻辑

适用场景：修改任务代码（`tasks/*.py`）、调试 TaskManager 流程、验证 OCR 识别等，不需要前端 UI。

```bash
python main.py
```

或

```bash
npm run dev
```

```
sra> help                             # 查看可用命令
sra> run Default                      # 运行 Default 配置中所有启用的任务
sra> single StartGameTask Default     # 只运行启动游戏任务
```

> 这里的 `Default` 是配置名称，对应 `%APPDATA%/SRA/configs/Default.json`。你可以在前端 UI 中创建自己的配置（如 `dev`），然后用
`run dev` 执行。

直接进入 CLI 交互模式，逐条执行命令观察输出。

接下来：参见[SRACLI](https://starrailassistant.top/getstarted/advance.html#sracli)文档，了解所有可用命令和参数。

### 用前端编辑配置，手动触发后端执行

适用场景：需要通过前端 UI 调整任务参数（选关卡、改次数等），然后手动控制后端执行时机。

1. 启动前端，在 UI 中修改配置并保存
2. 通过以下任一方式执行后端命令：

**方式 A**：切到控制台页面，在底部输入框中直接输入：

```
run Default                      # 运行 Default 配置中所有启用的任务
single StartGameTask Default     # 只运行启动游戏任务
help                             # 查看所有可用命令
```

> 输入框直接连接后端 stdin，等同于在后端 CLI 中输入。

**方式 B**：在独立终端中运行后端 CLI：

```bash
python main.py
```

或

```bash
npm run dev
```

```
sra> run Default
```

> 配置名称对应 `%APPDATA%/SRA/configs/<名称>.json`，前端和后端读取同一份文件，可在前端 UI 中创建和管理。

## 📦 构建完整发布包

使用以下命令构建前端和后端，并生成完整的发布包：

```bash
dotnet publish -c Release -r win-x64 SRAFrontend/SRAFrontend.csproj && python scripts/package.py
```

或

```bash
npm run build
```

完成后，发布包将位于项目根目录，命名格式为：StarRailAssistant_vX.X.X.zip、StarRailAssistant_Lite_vX.X.X.zip、StarRailAssistant_Core_vX.X.X.zip

## 辅助脚本
```bash
npm run pyl10nc # 运行 pyl10nc 本地化工具，编辑 SRACore/localization/resources.toml 文件以添加/修改翻译
npm run modelgen # 运行模型生成脚本，根据 C# 业务模型生成对应的 Python 数据类，保持前后端数据结构一致
npm run build # 构建项目，包括前端发布包和后端可执行文件，并生成完整的发布包
```

## 🧪 运行测试

```bash
# 运行全部后端测试
pytest 
```

## ⚠️ 常见问题

- **前端构建失败**：确保已安装 .NET 10.0 SDK，并尝试重新还原依赖：
  ```bash
  dotnet restore ./SRAFrontend/SRAFrontend.csproj -r win-x64 --force
  ```
- **运行时缺少 DLL 文件**：确保构建时使用了 `--self-contained true` 参数，或安装对应版本的 .NET 运行时。
- **图像识别不准确**：确保游戏分辨率设置为 1920x1080（全屏或窗口模式），并检查 `resources/img/` 目录下的模板图片是否完整。

## 🤝 参与开发

### 后端开发

* 🐍 熟悉 `Python`
* 🎮 正在游玩并将长期游玩`崩坏：星穹铁道`

### 前端开发

* 🎯 熟悉 `C#` 以及 `Avalonia` 框架

### 本地化支持

SRA 目前提供多语言支持。下面以新增西班牙语（资源后缀 `es-es`，BCP-47 标识 `es-ES`）
为例，列出需要改动的位置。

#### Python 后端与 CLI

1. 在 `SRACore/localization/resources.toml` 里为**每个**键补上新语言一列（`zh-cn` 是基准，占位符 `{name}`
   必须与其他语言一致）：

    ```toml
    [cli.intro] # 资源键
    zh-cn = "SRA-cli {version} ({core})\n输入 'help' 或 '?' 来查看命令列表。"
    en-us = "SRA-cli {version} ({core})\nType 'help' or '?' to list commands."
    ru-ru = "SRA-cli {version} ({core})\nВведите 'help' или '?' для списка команд."
    es-es = "SRA-cli {version} ({core})\nEscriba 'help' o '?' para listar los comandos."
    ```

2. 运行 `npm run pyl10nc`：生成 `resources_es-es.json`，`SRACore/localization/resources.py` 的
   `available_languages` 会自动包含新语言（生成物不要手改）。
3. **列顺序即枚举下标**：`Resources.set_language(int)` 按 `available_languages[值]` 取语言，因此 TOML 中
   语言列的顺序必须与 `AppSettings.cs` 里 `UiLanguage` 的枚举值一致；新增语言统一追加到末尾。
4. 术语表（OpenAPI `x-i18n` 的来源）：新增 `SRACore/localization/terms.es-es.json`，键结构照抄
   `terms.zh-cn.json`；在 `SRACore/localization/terms.py` 的 `_LANG_FILES` 里补 `"es-es": "es-ES"`；
   在 `scripts/i18n_check.py` 的 `LANGS` 里加上 `es-es`。
5. 扩展本地化：在 `SRACore/extension/locales.py` 的 `SUPPORTED_LANGS` 与 `_LANG_TAGS` 各加一项。

#### .NET 桌面端

1. `SRAFrontend/SRAFrontend/Models/AppSettings.cs` 的 `UiLanguage` 追加枚举值（顺序与 TOML 一致），
   `[Description]` 写该语言的母语名；改完执行 `npm run modelgen` 同步 `SRACore/models/app_settings.py`。
2. 新增卫星资源 `SRAFrontend/SRAFrontend/Localization/Resources.es-ES.resx`，键集与 `Resources.resx` 完全一致
   （从一个现成的 resx 复制翻译，并重新生成 `Resources.Designer.cs`）。
3. `SRAFrontend/SRAFrontend.Desktop/App.axaml.cs` 的 `CultureFor` 增加对应分支，
   如 `UiLanguage.Spanish => new CultureInfo("es-ES")`。
4. `SRAFrontend/SRAFrontend.Desktop/Views/SettingsPageView.axaml` 的语言下拉框追加一项 `ComboBoxItem`，
   顺序与枚举一致（`SelectedIndex` 直接绑定 `LanguageIndex`）；语言名取自 resx，不要硬编码。

#### Vue WebUI

1. 新增 `SRAFrontend/srafrontend-webui/src/locales/langs/es-ES.json`，键结构照抄 `zh-CN.json`。
2. `src/locales/index.ts` 的 `Locale` 联合类型与 `LOCALE_LABELS` 各加一项，`SUPPORTED_LOCALES` 会随之派生。
3. 后端字段说明会自动从 `x-i18n` 取新语言，未命中时回退 `description`（中文）。

#### 扩展

在每个扩展目录下补 `locales/es-ES.json`，键为 schema 字段键名（字段有 `alias` 时用 `alias`）：

- `name` / `description`：扩展展示名与说明；
- `<字段>.title` / `<字段>.description`：字段标题与说明；
- `<字段>.labels`：枚举标签数组，顺序与 `enum` 声明一致。

缺失的语言文件会回退中文，不影响扩展加载。

#### 校验

测试里的语言列表目前是写死的（`tests/test_russian_localization.py`、`tests/localization`、WebUI 的
`localization.spec.ts`），新增语言后需同步扩展用例，然后跑：

```bash
npm run pyl10nc && npm run i18n:check
python -m pytest tests/test_russian_localization.py tests/test_standard_io_utf8.py
dotnet test -c Release tests/localization/SRALocalizationChecks.csproj
cd SRAFrontend/srafrontend-webui && pnpm test
```

`tests/localization` 会无头渲染每种语言 × 明暗主题 × 800/1024 两档宽度的页面，具体见该目录的 `README.md`。

#### 本地化边界

日志是排查和定位问题的重要工具，本地化日志会导致日志内容变动，难以定位代码，因此不对日志进行本地化。

### 另辟蹊径

* 🎨 尝试为SRA绘制软件图标。

感谢您对SRA的支持！
