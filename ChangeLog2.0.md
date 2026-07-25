### 主要更新内容:
- 货币战争现在支持在攻略中指定特殊事件处理策略。
- SRA-cli现在支持动态新增cli命令。

### 问题修复：
- 修复了货币战争中当选择了免战牌投资策略后，无法识别到出战按钮导致卡死的问题。
- 修复了货币战争中无法识别领航员特殊事件的问题。

### 更新说明：

#### 在攻略中指定特殊事件处理策略
- 货币战争攻略新增 `special_events` 字段，用于指定特殊事件的选择。
- 支持的特殊事件有：`领航员`、`盛会之星`、`头号玩家`、`命运卜者`。
- 格式：`特殊事件名称`: `选择`，选择为选项中的视觉文本。
```json
{
    "special_events": {
        "领航员": "护盾",  // 触发领航员事件时，选择“护盾”选项，即三月七
        "盛会之星": "星期日",  // 触发盛会之星事件时，选择含有“星期日”文本的选项，”盛会之星——星期日先生！“
        "头号玩家": "银狼"  // 触发头号玩家事件时，选择含有“银狼”文本的选项，让银狼升费
    }
}
```

#### 动态新增cli命令
- 基于SRA-cli的任务扫描功能，现在SRA-cli可以动态新增cli命令
- 本次更新新增了货币战争相关的cli命令，包括：
  - `strategy list` - 获取已安装的货币战争策略列表
- 通过修改 `taskcli.py` 可以新增更多命令。

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
