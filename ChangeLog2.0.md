### 主要更新内容:
- 添加了新的特殊背景“yumemizukimizuki”
- 新增游戏活动日历功能，支持日历视图展示版本活动信息，按日期筛选活动并显示剩余时间倒计时。
- 更新解压流程优化：手动更新时新增确认解压对话框，避免误操作；自动更新沿用原流程。
- 新增拓展系统，支持自定义插件和脚本。
- 移除了旧版触发器系统，现在由拓展系统替代。
- 默认禁用任务失败后重试功能。

### 问题修复：
- 修复了修改设置后需要重启SRA才能生效的问题。
- 修复了侵蚀隧洞中迅拳之径与霜风之径丢失的问题。
- 修复了当货币战争未选择攻略时导致任务失败的问题。
- 修复了货币战争金币数量识别错误导致无限进行升级操作的问题。
- 修复了差分宇宙结算时检测超时的问题。
- 修复了领取签证奖励时偶现卡加载导致任务失败的问题。
- 修复了任务结束后通知截图丢失的问题。

### 更新说明：

#### 拓展系统：
- 新增拓展系统，支持自定义插件和脚本。
- 拓展系统旨在以最小的侵入或对主程序的修改，实现动态加载自定义插件和脚本的功能。
- 只需按固定模式编写python脚本，即可在SRA中动态加载和运行，自动生成可视化配置界面。

#### 破坏性变更：
- 移除了旧版触发器系统，现在由拓展系统替代。
- trigger及它的子命令已被移除，现在由拓展系统替代。
- 示例：
  - 旧 trigger enable <extension_id>
  - 新 extension run <extension_id>
  - 旧 trigger disable <extension_id>
  - 新 extension stop <extension_id>


[已有 Mirror酱 CDK ？前往 Mirror酱 高速下载](https://mirrorchyan.com/zh/projects?rid=StarRailAssistant&source=sra-release)

下载说明: 
- StarRailAssistant_Core*.zip - 标准版（需要手动配置）
- StarRailAssistant_Full*.zip - 尊享版（功能最全面）
- StarRailAssistant_Lite*.zip - 试玩版（需要手动安装和配置 Python 环境）
- StarRailAssistant_ServerDLC*.zip - 服务器DLC（需要标准版，提供http接口）
- StarRailAssistant_DesktopDLC*.zip - 桌面DLC（需要标准版，提供UI界面）
- StarRailAssistant_vX.X.X.zip - 主程序包（推荐）
- StarRailAssistant_vX.X.X_Setup.exe - 主程序安装包（推荐）

需要安装 [.NET 桌面运行时 10.0](https://dotnet.microsoft.com/zh-cn/download/dotnet/10.0) 才能运行
首次使用建议下载豪华版
**看准文件名再下载！**
