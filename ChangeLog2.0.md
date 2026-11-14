### 主要更新内容:

2.25.4:
- 修复了货币战争中启用积分奖励后未领取积分奖励的问题。
- 部分场景增加重试机制，以优化货币战争稳定性。

2.25.3:
- 将自动切号插件重写为一个拓展，受拓展系统管理，默认禁用，如果你需要免密码切号，请在拓展页面中启用。

2.25.2:
- 修复了特殊情况下SRA会关闭自动战斗的问题。

2.25.1:
- 修复了货币战争中未能正确处理“奇兽花园”事件的问题。
- 修复了货币战争中无法处理“梦境交织”事件的问题。
- 修复了货币战争中无法处理“独家代言”策略的装备选择事件的问题。
- 修复了货币战争中无法正确识别“我来当策划”事件的问题。
- 修复了货币战争中偶发点击出战未生效，导致流程卡死的问题。
- 移除了货币战争中已从游戏内删除的“命运卜者”事件处理及相关资源。

2.25.0:

**包含「破坏性变更」。请在更新后运行资源清理来删除旧资源。**

- SRA-Cli 与 SRA-Server 现在是一款统一的产品。
- 新增 `CurrencyWarsPlus` 拓展，支持货币战争常规与超频博弈、阶段阵容与职责、阶段经济及 3-7 终局运营。 by YukkiSSYB、sososos662
- 清体力培养目标新增“材料优先”选项，开启后若识别到材料型副本，则跳过饰品提取与侵蚀隧洞；未识别到材料型副本时仍保留原有副本。
- 新增自动拉取兑换码功能，兑换码任务将自动从官网拉取最新兑换码，与本地配置合并后兑换。
- 添加俄语本地化支持 by sososos662
- 添加 Docker 部署支持
- WebUI: 支持在实时预览画面时直接发送键鼠操作
- 新增免密码历史账号切号插件，密码留空时支持免密码从历史账号切号 by Camellune
- 适配4.7版本「此刻，将群星付之一笑」

### 问题修复：

- 修复了启动时错误地提示pynput库未安装的问题。
- 修复了extension stop命令无法停止非后台扩展的问题。
- 修复了货币战争中当应用攻略码失败时，程序卡死的问题。
- 修复了货币战争中当前台区域无角色时，程序卡死的问题。
- 修复了历战余响战斗结束时获得光锥时，程序卡死的问题。
- 修复了差分宇宙更新弹窗导致程序卡死的问题。
- 修复了在 WebUI 中保存任务配置后，账号密码在下次运行时失效的问题。
- 修复了货币战争中偶发商店未正常弹出，导致流程卡死的问题。

### 更新说明：

#### SRA-Cli 与 SRA-Server 现在是一款统一的产品。

我们已将 SRA-Cli 与 SRA-Server 合并为一款统一的产品，所有功能与之前相同。
你可以通过 `SRA-cli.exe serve` 命令启动服务端，而无需额外安装 ASP.NET Core。

服务端配置：
- 优先级：命令行参数 > 环境变量 > `SRAServer/server.toml` > 默认值。
- 可用键：`SRA_HOST`、`SRA_PORT`、`SRA_WEBUI`、`SRA_ACCESS_TOKEN`、`SRA_VISITOR_MODE`、`SRA_LOG_LEVEL`（`server.toml` 中为同名小写键）。
- 命令行参数：`--host`（绑定 `0.0.0.0` 对外暴露）、`--port`；`sra serve` 另支持 `--no-webui`
- Core / Full / Lite 发行包均已内置 WebUI，开箱即用；通过 `uv` / `pip` 安装（wheel 不含构建产物）时需执行一次 `sra init` 下载 WebUI，未下载时 REST 与 MCP 仍可用，只是没有 Web 界面。

#### 新增 Docker 部署支持

SRA 现在支持 Docker 部署，详见 [Docker 部署说明](https://starrailassistant.top/guides/docker/)。

#### 破坏性变更:

- 打包方式变更：不再使用Nuitka打包，而是直接嵌入 Python 运行时。
- Server: 移除了 `SRA-server.exe`, 请使用 `SRA-cli.exe serve` 启动服务端。
- Server: 服务器 REST 路径统一为小写。
- Server: 远程模式默认地址改为 `http://localhost:5073`（原 5000），请求路径同步改为 `/api/**`。
- Server: 不再需要 ASP.NET Core。
- Core: Python 依赖分组 `full` extra 更名为 `standard`：`pip install ".[full]"` 失效，改用 `pip install ".[standard]"`。
- Extensions: 扩展改为目录包（一级目录 + `__init__.py`）才加载，旧的单文件 `extensions/xxx.py` 只记录 warning 后忽略。
  第三方扩展需迁移为 `extensions/<名称>/__init__.py`，原文件内的相对导入与同目录资源一并移入该目录。

#### 新增货币战争 plus 独立优化扩展

此拓展是一个独立的任务，你需要拓展页面对它进行配置和运行

- 新增 `CurrencyWarsPlus`，支持常规与超频博弈、阶段阵容与职责、阶段经济及 3-7 终局运营。
- 提供动作结果核实、动态后台与锁定支援识别、会话恢复、两份正式攻略和中文配置说明。
- 配置表单支持枚举标签、真实数值、选项扫描与自定义路径。
- plusv1 补齐后台身份、事件观测、采购确认、出战门槛、事件交接、费用补读、结算血量与同线程任务重建。
- 完整的重大／一般／bug修复清单、测试结果和已知限制见[扩展 README](extensions/currency_wars_plus/cw_plus/README.md)。
- 开发者：**YukkiSSYB**。

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
