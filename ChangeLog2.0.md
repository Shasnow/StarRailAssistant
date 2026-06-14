### 主要更新内容:
- 记忆窗口大小和位置：在设置中启用后，SRA会记住您上次关闭窗口时的大小和位置。
- SRA-server：新增了一个新的服务端应用，您可以通过http协议与SRA进行通信。
- 远程后端支持：桌面端可以通过HTTP连接远程SRA服务端，实现跨设备任务管理。

### 功能调整：
- 更新了任务结束后通知的截图页面，增加截图信息量。 #198
- 更新了问候语。

### 问题修复：
- 修复了SRA无法将游戏窗口移动到前台的问题。
- 修复了云游戏模式启动游戏任务中途失败的问题。
- 执行体力清理时被切换视角的提示卡住
- 修复了无名勋礼更新时卡在奖励预览页面的问题。
- 修复了首次使用SRA时，报错提示未找到settings.json的问题。

### 更新说明：

#### SRA-server
- 新增了一个新的服务端应用，您可以通过http协议与SRA进行通信。
- 服务端应用的端口号为5000，通过`--port`选项可以自定义端口号。
- 访问`http://localhost:5000/swagger`可以查看API文档。

#### 远程后端
- 桌面端新增远程后端模式，可通过HTTP连接远程SRA服务端执行任务。
- 在高级设置中可启用远程后端并配置服务器地址（默认 `http://localhost:5000`）。
- 连接后自动订阅服务端SSE日志流，实时显示远程任务输出。
- 支持通过 `Task/run` 和 `Task/stop` API 启动和停止远程任务。
- SSE断线后自动重连（3秒间隔）。

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