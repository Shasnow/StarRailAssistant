### 主要更新内容:
- 更新 .NET 10.0
- 为集成Python环境和从源代码运行后端做准备

### 功能调整：
- 设置-“使用Python从源代码运行后端”已移出开发者选项，改为高级设置并默认开启。

### 问题修复：
- 修复了阶段1没有刷到需要的投资策略时仍继续往下打的问题。

### 更新说明：
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
