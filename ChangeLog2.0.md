### 主要更新内容:

2.26.0:
- 新增命令面板，在 SRA 中按下 `ctrl`+`shift`+`p` 即可打开，命令面板把常用操作集中到一个可搜索的列表里，无需再逐页寻找按钮。
- cli新增serve命令，可以直接在当前会话中启动服务端，而无需重新启动。

### 问题修复：

...

### 更新说明：

...

### 发布包结构

- 主程序包（Full）：内嵌 Python 运行时 + 源码 + .NET 桌面端，开箱即用。
- 核心包（Core）：内嵌 Python 运行时 + 源码，不含桌面端。
- 轻量版（Lite）：仅源码与桌面端，需自行安装 Python 3.12 并执行 `pip install ".[standard]"`。

[已有 Mirror酱 CDK ？前往 Mirror酱 高速下载](https://mirrorchyan.com/zh/projects?rid=StarRailAssistant&source=sra-release)

下载说明: 
- [StarRailAssistant_v${VERSION}.zip](https://github.com/Shasnow/StarRailAssistant/releases/download/v${VERSION}/StarRailAssistant_v${VERSION}.zip) - 主程序包（推荐）
- [StarRailAssistant_v${VERSION}_Setup.exe](https://github.com/Shasnow/StarRailAssistant/releases/download/v${VERSION}/StarRailAssistant_v${VERSION}_Setup.exe) - 主程序安装包（推荐）
- [StarRailAssistant_Core_v${VERSION}.zip](https://github.com/Shasnow/StarRailAssistant/releases/download/v${VERSION}/StarRailAssistant_Core_v${VERSION}.zip) - 核心包（内嵌 Python 3.12 运行时与源码）
- [StarRailAssistant_Lite_v${VERSION}.zip](https://github.com/Shasnow/StarRailAssistant/releases/download/v${VERSION}/StarRailAssistant_Lite_v${VERSION}.zip) - 轻量版（需要手动安装和配置 Python 环境）

需要安装 [.NET 桌面运行时 10.0](https://dotnet.microsoft.com/zh-cn/download/dotnet/10.0) 才能运行GUI界面。
主程序包与核心包已内置 Python 3.12 运行时，无需额外安装；轻量版需自行安装 Python 3.12
首次使用建议下载主程序包。
**看准文件名再下载！**
