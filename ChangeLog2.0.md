### 主要更新内容:

- 新增 `CurrencyWarsPlus` 拓展，支持货币战争常规与超频博弈、阶段阵容与职责、阶段经济及 3-7 终局运营。 by YukkiSSYB
- 清体力培养目标新增“材料优先”选项，开启后若识别到材料仪器副本，未仪器副本，未识别到材料型副本时仍保留仪器副本。
- 新增自动拉取兑换码功能，兑换码任务将自动从官网拉取最新兑换码，与本地配置合并后兑换。
- 添加俄语本地化支持 by sososos662

### 问题修复：
- 修复了启动时错误地提示pynput库未安装的问题。
- 修复了extension stop命令无法停止非后台扩展的问题。
- 修复了货币战争中当应用攻略码失败时，程序卡死的问题。
- 修复了货币战争中当前台区域无角色时，程序卡死的问题。
- 修复了历战余响战斗结束时获得光锥时，程序卡死的问题。
- 修复了差分宇宙更新弹窗导致程序卡死的问题。

### 更新说明：

#### 新增货币战争 plus 独立优化扩展

此拓展是一个独立的任务，你需要拓展页面对它进行配置和运行

- 新增 `CurrencyWarsPlus`，支持常规与超频博弈、阶段阵容与职责、阶段经济及 3-7 终局运营。
- 提供动作结果核实、动态后台与锁定支援识别、会话恢复、两份正式攻略和中文配置说明。
- 配置表单支持枚举标签、真实数值、选项扫描与自定义路径。
- plusv1 补齐后台身份、事件观测、采购确认、出战门槛、事件交接、费用补读、结算血量与同线程任务重建。
- 完整的重大／一般／bug修复清单、测试结果和已知限制见[扩展 README](extensions/cw_plus/README.md)。
- 开发者：**YukkiSSYB**。

[已有 Mirror酱 CDK ？前往 Mirror酱 高速下载](https://mirrorchyan.com/zh/projects?rid=StarRailAssistant&source=sra-release)

下载说明: 
- [StarRailAssistant_v${VERSION}.zip](https://github.com/StarRailAssistant/StarRailAssistant/releases/download/v${VERSION}/StarRailAssistant_v${VERSION}.zip) - 主程序包（推荐）
- [StarRailAssistant_v${VERSION}_Setup.exe](https://github.com/StarRailAssistant/StarRailAssistant/releases/download/v${VERSION}/StarRailAssistant_v${VERSION}_Setup.exe) - 主程序安装包（推荐）
- [StarRailAssistant_Core_${VERSION}.zip](https://github.com/StarRailAssistant/StarRailAssistant/releases/download/v${VERSION}/StarRailAssistant_Core_${VERSION}.zip) - 核心包（需要手动配置）
- [StarRailAssistant_Lite_${VERSION}.zip](https://github.com/StarRailAssistant/StarRailAssistant/releases/download/v${VERSION}/StarRailAssistant_Lite_${VERSION}.zip) - 轻量版（需要手动安装和配置 Python 环境）

需要安装 [.NET 桌面运行时 10.0](https://dotnet.microsoft.com/zh-cn/download/dotnet/10.0) 才能运行
如果你需要使用SRA-server（提供HTTP接口、MCP服务器和WebUI），你必须安装`ASP.NET Core 运行时 10.0`。或`.NET SDK 10.0`。
首次使用建议下载主程序包。
**看准文件名再下载！**
