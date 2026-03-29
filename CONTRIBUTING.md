# 贡献指南

感谢你对 StarRailAssistant 的关注！以下是参与项目开发所需的全部信息。

## 📋 环境要求

- **操作系统**：Windows 10 或 Windows 11 (推荐)
- **Python**：3.12 或更高版本（需添加到系统环境变量）
- **.NET SDK**：8.0 或更高版本（下载地址：[.NET 8.0 SDK](https://dotnet.microsoft.com/zh-cn/download/dotnet/8.0)）
- **Git**：用于克隆仓库（可选，但推荐）

## 📥 获取源码

```bash
# 克隆仓库
git clone https://github.com/Shasnow/StarRailAssistant.git
cd StarRailAssistant

# 或直接下载 ZIP 压缩包并解压
```

## 📦 安装依赖

```bash
# 安装运行依赖
pip install -r requirements.txt

# 安装开发/测试依赖
pip install -r requirements-dev.txt

# 如果遇到安装失败，尝试使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 🧪 运行测试

```bash
# 运行全部后端测试
pytest tests/backend/ -v

# 运行测试并查看覆盖率
pytest tests/backend/ --cov=SRACore --cov=tasks --cov-report=term-missing

# 检查增量覆盖率（对比 main 分支）
pytest tests/backend/ --cov=SRACore --cov=tasks --cov-report=xml
diff-cover coverage.xml --compare-branch=origin/main --fail-under=60
```

> ⚠️ 提交 PR 时，CI 会自动检查变更代码的测试覆盖率，增量覆盖率低于 60% 将阻断合并。

## 🏗️ 构建前端

```bash
# 进入前端目录
cd SRAFrontend

# 还原 NuGet 依赖（首次构建时必须执行）
dotnet restore -r win-x64

# 构建前端项目（Release 模式）
dotnet publish -c Release -r win-x64

# 构建完成后，可执行文件将位于：
# ./SRAFrontend/bin/Release/net8.0/win-x64/publish/SRA.exe

# 返回项目根目录
cd ..
```

## 🚀 开发模式运行

SRA 采用前后端分离架构：前端（C# / Avalonia）通过 stdin/stdout 与后端（Python）子进程通信。

根据你要调试的目标，选择对应的方式：

### 调试前端 UI 或前后端交互

适用场景：修改前端界面、验证前后端 IPC 通信、测试任务页面的配置绑定等。

```bash
cd SRAFrontend
dotnet run
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
sra> help                             # 查看可用命令
sra> run Default                      # 运行 Default 配置中所有启用的任务
sra> single StartGameTask Default     # 只运行启动游戏任务
```

> 这里的 `Default` 是配置名称，对应 `%APPDATA%/SRA/configs/Default.json`。你可以在前端 UI 中创建自己的配置（如 `dev`），然后用 `run dev` 执行。

直接进入 CLI 交互模式，逐条执行命令观察输出。

### 用前端编辑配置，手动触发后端执行

适用场景：需要通过前端 UI 调整任务参数（选关卡、改次数等），然后手动控制后端执行时机。

1. 启动前端 `dotnet run`，在 UI 中修改配置并保存
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
sra> run Default
```

> 配置名称对应 `%APPDATA%/SRA/configs/<名称>.json`，前端和后端读取同一份文件，可在前端 UI 中创建和管理。

## 📦 构建完整发布包

```bash
# 运行打包脚本（确保前端已构建）
python ./package.py

# 完成后，发布包将位于项目根目录，命名格式为：StarRailAssistant_vX.X.X.zip
```

## ⚠️ 常见问题

- **前端构建失败**：确保已安装 .NET 8.0 SDK，并尝试重新还原依赖：
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

SRA 后端采用 [pyl10nc](https://github.com/Shasnow/pyl10nc) 进行本地化支持，欢迎贡献翻译！

1. 克隆仓库并创建新的分支
2. 在 `SRACore/localization/` 目录下编辑 `resource.toml` 文件，添加新的语言支持

    示例：
    ```toml
    [cli.intro] # 资源键
    en-us = "SRA-cli {version} ({core})\nType 'help' or '?' to list commands." # 现有的英文翻译
    zh-cn = "SRA-cli {version} ({core})\n输入 'help' 或 '?' 来查看命令列表。" # 现有的中文翻译
    ```
    
    新增语言键：
    ```toml
    [cli.intro]
    # ......
    es-es = "SRA-cli {version} ({core})\nEscriba 'help' o '?' para listar los comandos." # 新增的西班牙语翻译
    ```

3. 提交 Pull Request

SRA 前端采用 `ResX` 进行本地化支持，推荐使用 `Rider` 或 `Visual Studio` 进行编辑。

### 另辟蹊径

* 🎨 尝试为SRA绘制软件图标。

感谢您对SRA的支持！
