### 主要更新内容:

2.27.1:
- 修复了货币战争中在特殊情况下会卡在遭遇节点界面的问题。

2.27.0:
- 新增热更新功能
- 修复了刷开局时投资策略连续触发导致任务失败的问题。
- 新增「机心巧匠」特殊事件处理逻辑

2.26.1:
- 修复新周本"贪欢的月亮"无法刷取的问题。

2.26.0:
- 新增命令面板，在 SRA 中按下 `ctrl`+`shift`+`p` 即可打开，命令面板把常用操作集中到一个可搜索的列表里，无需再逐页寻找按钮。
- cli新增serve命令，可以直接在当前会话中启动服务端，而无需重新启动程序。

### 问题修复：

- 延长结算页面等待时间并处理重开失败的情况。
- 修复货币战争中当选择了高傲巨人导致人口超限卡死的问题。
- 新增「从师」事件处理逻辑，确保在选择主角后能够正常出战。

### 更新说明：

#### 命令面板

新增命令面板，在 SRA 中按下 `ctrl`+`shift`+`p` 即可打开

例如当你想导出日志时，直接在命令面板中输入 `导出日志` 即可，而无需转到控制台页面再点击导出按钮。
这里也会提供一些没有显式入口的操作，例如启动服务端。

#### cli新增serve命令

新增serve命令，可以直接在当前会话中启动服务端，而无需重新启动。

例如当你想在当前会话中启动服务端时，直接在命令面板中输入 `serve` 即可。
这将在一个独立的线程中启动服务端，而不会阻塞当前会话，你可以继续执行其他操作。
服务端与当前会话共享上下文

要停止服务端时，使用 `serve stop` 即可。

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
