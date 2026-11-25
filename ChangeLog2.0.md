### 主要更新内容:

2.28.0:
- 优化差分宇宙任务逻辑，增强稳定性，减少“撞墙”问题。
- 新增基于多模态大语言模型视觉的界面识别功能，能够更准确地识别游戏界面元素，但可能产生资金消耗。
- 货币战争刷开局改为独立开关，可与标准博弈、超频博弈自由组合。
- 货币战争新增高级设置，可跳过商店刷新、应用攻略、收集晶矿与装备穿戴。

### 问题修复：

- 修复了差分宇宙任务在探索成功后，未正确结束对局的问题。
- 修复了差分宇宙任务在站点卡识别失败时无法判断站点类型的问题，改为按左上角 HUD 的站点名兜底。
- 修复了差分宇宙任务选择下一站点时把界面噪声（步数、贴图误识别）当成站点选项的问题。
- 修复了beta频道无法使用热更新的问题。

### 更新说明：

#### MLLM 视觉识别功能

新增基于多模态大语言模型（MLLM）视觉的界面识别功能，能够更准确地识别游戏界面元素，但可能产生资金消耗。

- 在高级设置-多模态视觉中开启并填写 API 端点（OpenAI Chat Completion 格式）和 API 密钥后，在部分场景下SRA将优先使用 MLLM 识别界面元素。
- 使用此功能将产生费用，在使用 DeepSeek-V4.1-Flash 模型时，单次调用的花费约为 0.002 元。

目前已在以下场景加入 MLLM 视觉识别功能：
- 差分宇宙中事件类站点识别事件画框。

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
