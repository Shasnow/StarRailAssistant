### 主要更新内容:
- 货币战争中当战斗超时时，强制放弃并结算。
- 新增SRA MCP (Model Control Protocol) 服务器，为Agent接入准备好。
- 新增operator命令，用于直接调用SRA的Operator API以实现游戏操控。
- 不再单独分发SRA ServerDLC，而是包含在主程序包中。
- 升级到Avalonia 12。
- 更新更新解压失败后的错误处理逻辑，增加手动解压选项。

### 问题修复：
- 修复了货币战争中无法处理命运卜者事件的问题。 #234
- 修复了货币战争中自动战斗情况下前后台角色均无法造成伤害时，卡死在奖励关卡的问题。 #233
- 修复了差分宇宙/货币战争中当点击前往参与后未直接进入主界面导致任务无法正常运行的问题。
- 修复了自动对话无法跳过对话的问题。
- 修复了云游戏模式下无法切换账号的问题。
- 修复了货币战争中特殊情况下无法输入攻略码的问题。
- 修复了差分宇宙选择面具时有刷新按钮导致无法选择面具的问题。
- 修复了货币战争中当选择了阿哈大悦策略后卡死的问题。

### 更新说明：

#### 新增operator命令
- 新增operator命令，用于直接调用SRA的Operator API以实现游戏操控。
- operator list - 显示所有可用的Operator API。
- operator call <method> <params> - 调用指定的Operator API，参数为JSON格式。
- operator help <method> - 显示指定Operator API的详细帮助信息。
- SRA Server同步更新。

#### 内置SRA ServerDLC
- 为了减少用户下载时的疑惑和提供统一的使用体验，不再单独分发SRA ServerDLC，而是包含在主程序包中。
- 但要使用SRA-server，你必须安装[ASP.NET Core 运行时 10.0](https://dotnet.microsoft.com/zh-cn/download/dotnet/10.0)。或[.NET SDK 10.0](https://dotnet.microsoft.com/download/dotnet/10.0)。

#### SRA MCP服务器

- 在此版本中新增了SRA MCP服务器，为agent接入提供了基础支持。
- 启动SRA Server后，在Agent中配置`http://host:port/mcp`，并以流式HTTP方式访问即可。
- 服务器提供了一组精选的MCP工具，用于与SRA或游戏本身进行交互。这些工具包括但不限于：
  - 获取游戏截图与OCR识别
  - 模拟输入
  - 任务列表
  - 其他自定义工具


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
