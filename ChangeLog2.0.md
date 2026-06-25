### 主要更新内容:
- SRA-Server 新增 API Key 认证，保护服务器安全。
- SRA-cli 已发布到 PyPI，可直接安装使用。
- 新增抽卡资源预测扩展，可根据当前资源、奖励指南、版本周期、月卡、深渊类刷新、周常奖励和前瞻兑换码估算当前版本结束前可获得的抽卡资源。 #208

### 功能调整：
- 更新了任务结束后通知的截图页面，增加截图信息量。 #198
- 更新了问候语。
- 移除废弃的 `CurrencyWarsPolicy` 配置项。

### 问题修复：
- none

### 更新说明：

#### SRA-Server
- 新增基于密钥的认证机制：在 `appsettings.json` 中配置 `ApiKey` 后启用，未配置时允许匿名访问。
- 认证方式：请求头 `X-Api-Key: <your-key>`。
- 启动时若未配置 ApiKey，会打印警告日志 `ApiKey is not set; server is unsecured.`。

#### PyPI 上的 SRA
- SRA-cli 已发布到 PyPI，提供更方便的使用方式。
- 系统要求：
  - Python 3.12
  - pipx 或 uv （可选）
  - 以管理员权限运行终端
- 安装方法：
  - 在虚拟环境中安装：`pip install starrailassistant`
  - 安装为全局工具：`pipx install starrailassistant`
  - 安装为全局工具：`uv tool install starrailassistant`
- 首次使用：
  - 创建SRA专用文件夹：`mkdir -p starrailassistant` (如果你在虚拟环境中安装，不需要这一步)
  - 运行初始化命令：`cd starrailassistant && sra-cli init`
- 启动应用：
  - 运行应用：`cd starrailassistant && sra-cli`
- 更新应用：
  - pip 更新：`cd starrailassistant && pip install --upgrade starrailassistant`
  - pipx 更新：`pipx upgrade starrailassistant`
  - uv 更新：`uv tool upgrade starrailassistant`
  - 更新后可能需要重新运行`init`命令以应用新配置。
- 其他：请参阅 [SRA-cli 文档](https://starrailassistant.top/getstarted/advance.html#sracli)

[已有 Mirror酱 CDK ？前往 Mirror酱 高速下载](https://mirrorchyan.com/zh/projects?rid=StarRailAssistant&source=sra-release)

下载说明: 
- StarRailAssistant_Core*.zip - 标准版（需要手动配置）
- StarRailAssistant_Full*.zip - 尊享版（功能最全面）
- StarRailAssistant_Lite*.zip - 试玩版（需要手动安装和配置 Python 环境）
- StarRailAssistant_ServerDLC*.zip - 服务器DLC（需要标准版，提供http接口）
- StarRailAssistant_DesktopDLC*.zip - 桌面DLC（需要标准版，提供UI界面）
- StarRailAssistant_vX.X.X.zip - 豪华版（推荐）
- StarRailAssistant_vX.X.X_Setup.exe - 豪华版, 但是以exe形式安装（推荐）

需要安装 [.NET 桌面运行时 10.0](https://dotnet.microsoft.com/zh-cn/download/dotnet/10.0) 才能运行
首次使用建议下载豪华版
**看准文件名再下载！**
