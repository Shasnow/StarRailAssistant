### 主要更新内容:
- 更新 .NET 10.0
- 为集成Python环境和从源代码运行后端做准备
- 自动开启自动战斗。需要启用游戏启动参数
- 差分宇宙新增‘启用积分奖励’功能。启用后当每周积分达到上限时将跳过差分宇宙任务，并自动领取积分奖励。
- 清体力任务新增“启用多倍活动检测”功能。启用后将检测当前是否有花藏繁生、异器盈界等活动，并优先刷对应的副本。

### 功能调整：
- 设置-“使用Python从源代码运行后端”已移出开发者选项，改为高级设置并默认开启。

### 问题修复：
- 修复了货币战争刷开局阶段1没有刷到需要的投资策略时仍继续往下打的问题。
- 修复了云星穹铁道当cookies失效时无法登录的问题。
- 修复签证奖励无法领取的问题。
- 修复了自动计算饰品提取挑战次数时没有计入沉浸器的问题。

### 更新说明：

你必须安装.NET 10.0 Desktop Runtime才能运行更新后的SRA

任务配置文件格式已更新，旧版本的任务配置文件将无法直接使用，更新后请使用SRA重新打开任务配置，SRA会自动将其转换为新的格式。

#### 为集成Python环境和从源代码运行后端做准备：
- 现在SRA将默认使用本地Python解释器运行后端代码，而不是运行打包后的可执行文件。
- 首次运行时，SRA会自动安装Python环境和依赖。
- 如果更新后SRA无法正常运行，关闭“使用Python从源代码运行后端”设置后将回退到旧的运行模式，同时请及时向开发者反馈问题。
- SRA专用Python环境和依赖将存储在SRA的安装目录下/python目录下。

#### 更新 .NET 10.0：
- 本次更新将更新SRA的.NET运行环境为10.0，这将带来性能提升和新的功能。
- 请确保你的系统已安装.NET 10.0 Desktop Runtime，否则SRA将无法正常运行。
- [安装.NET 10.0 Desktop Runtime](https://builds.dotnet.microsoft.com/dotnet/WindowsDesktop/10.0.7/windowsdesktop-runtime-10.0.7-win-x64.exe)

#### 已过时的功能：
这些功能已过时，但仍在SRA中保留，以保持向后兼容性。它们将在未来版本中移除。
- SRA-cli.exe及其相关命令和参数
  - 请使用 SRA.exe 或 ./python/python.exe main.py 替代。

- 示例：
  - 旧命令：SRA-cli.exe -e run Default + exit
  - 新命令：SRA.exe -e run Default + exit
  - 旧命令：SRA-cli.exe
  - 新命令：./python/python.exe main.py
