### 主要更新内容:
- 支持差分宇宙完整对局，在旷宇纷争页签中将差分宇宙模式切换为完整对局即可。
- 设置-高级：新增资源完整性检查功能，可检查当前应用目录是否有文件缺失或损坏。
- 设置-高级：新增资源清理功能，可清理版本迭代后残留的无用的文件。扫描的结果可能包含重要的个人数据，请谨慎操作。
- SRA-server: 为SRA提供了WebUI界面，使你可以通过浏览器访问 SRA 的功能。在线预览：[https://webui.starrailassistant.top/](https://webui.starrailassistant.top/)

### 问题修复：
- 修复了差分宇宙中偶现因敌人未进入攻击范围而无法进入战斗的问题。
- 修复了历战余响卡在获得光锥页面的问题。
- 修复了在云游戏模式下，当浏览器进程异常退出时，无法再次启动浏览器的问题。
- 修复了在云游戏模式下，无头浏览器截图尺寸不满足要求的问题。
- 修复了无法自动检测新版米哈游启动器的游戏安装路径的问题。
- 修复了SRA-server并发时偶现命令超时的问题。
- 修复了SRA-server中当后端无日志输出时，SSE日志流无法正确建立连接的问题。


### 更新说明：

#### 差分宇宙完整对局说明
- 在旷宇纷争页签中将差分宇宙模式切换为完整对局即可。
- 如果需要SRA中途接管对局，需要当前处于刚进入战斗类节点的状态，然后在SRA中启动旷宇纷争任务。
- 当前版本仅支持周期演算。

#### SRA-WebUI 说明
- SRA-WebUI 是一个基于 Vue 3 的 Web 应用，用于提供 SRA 的 Web 用户界面，使你可以通过浏览器访问 SRA 的功能。
- 它需要 SRA-server 才能正常工作。
- 启动SRA-server后，SRA-WebUI会自动启动，你可以在浏览器中访问 `http://localhost:5000` 来查看 SRA-WebUI。
- 如果不需要使用SRA-WebUI，你可以在启动SRA-server时添加 `--no-webui` 参数来禁用它。
- 如果要更改监听端口，你可以在启动SRA-server时添加 `--urls http://localhost:{port}`  参数来指定监听端口。
- 如果要让SRA-server在所有网络接口上监听，你可以在启动SRA-server时添加 `--urls http://0.0.0.0:{port}`  参数。


[已有 Mirror酱 CDK ？前往 Mirror酱 高速下载](https://mirrorchyan.com/zh/projects?rid=StarRailAssistant&source=sra-release)

下载说明: 
- StarRailAssistant_vX.X.X.zip - 主程序包（推荐）
- StarRailAssistant_vX.X.X_Setup.exe - 主程序安装包（推荐）
- StarRailAssistant_Core*.zip - 核心包（需要手动配置）
- StarRailAssistant_Lite*.zip - 轻量版（需要手动安装和配置 Python 环境）

需要安装 [.NET 桌面运行时 10.0](https://dotnet.microsoft.com/zh-cn/download/dotnet/10.0) 才能运行
如果你需要使用SRA-server（提供HTTP接口和MCP服务器），你必须安装`ASP.NET Core 运行时 10.0`。或`.NET SDK 10.0`。
首次使用建议下载主程序包。
**看准文件名再下载！**
