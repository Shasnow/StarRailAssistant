# 🌟 StarRailAssistant 前端项目

## 📋 项目概述

StarRailAssistant (SRA) 前端是一个基于 Avalonia 框架开发的跨平台桌面应用程序，为崩坏星穹铁道玩家提供自动化任务管理界面。前端负责用户交互、配置管理和与后端 Python 服务的通信。

## 🛠️ 技术栈

- **框架**: Avalonia UI (跨平台 .NET UI 框架)
- **语言**: C# 10+
- **架构**: MVVM (Model-View-ViewModel)
- **构建工具**: .NET 8.0 SDK
- **依赖管理**: NuGet

## 📁 项目结构

```
├── Assets/                # 资源文件
│   ├── Phosphor.ttf       # 图标字体
│   ├── SRAicon.ico        # 应用图标
│   └── background-lt.jpg  # 背景图片
├── Controls/              # 自定义控件
├── Data/                  # 数据模型定义
├── Localization/          # 本地化资源
├── Models/                # 业务模型
├── Services/              # 服务层
├── Styles/                # 样式定义
├── Utilities/             # 工具类
├── ViewModels/            # MVVM ViewModel 层
├── Views/                 # MVVM View 层
│   └── TaskViews/         # 任务相关视图
├── App.axaml              # 应用入口 XAML
├── App.axaml.cs           # 应用入口代码
├── MainWindow.axaml       # 主窗口 XAML
├── MainWindow.axaml.cs    # 主窗口代码
├── Program.cs             # 程序启动点
├── SRAFrontend.csproj     # 项目文件
└── SRAFrontend.sln        # 解决方案文件
```

## 🚀 开发环境要求

- .NET 8.0 SDK 或更高版本
- Rider (推荐) 或 Visual Studio 2022 或 Visual Studio Code
- Avalonia 扩展 (推荐)

## 🔧 构建和运行

### 1. 克隆仓库

```bash
git clone https://github.com/Shasnow/StarRailAssistant.git
cd StarRailAssistant/SRAFrontend
```

### 2. 还原依赖

```bash
dotnet restore
```

### 3. 构建项目

```bash
dotnet build -c Debug
# 或发布版本
dotnet build -c Release
```

### 4. 运行项目

```bash
dotnet run
```

### 5. 发布项目

```bash
dotnet publish -c Release -r win-x64 --self-contained
```

## 📐 架构说明

### MVVM 架构

项目采用标准 MVVM 架构，将关注点分离：

- **Models**: 数据实体和业务逻辑
- **Views**: UI 界面 (XAML)
- **ViewModels**: 连接 View 和 Model 的中间层，处理 UI 逻辑

### 服务层

服务层提供各种功能支持：

- **ConfigService**: 配置管理
- **SettingsService**: 设置管理
- **SraService**: 与后端 Python 服务通信
- **UpdateService**: 更新检查和安装
- **AnnouncementService**: 公告服务

### 本地化支持

项目支持多语言，本地化资源文件位于 `Localization/` 目录：

- `Resources.resx`: 默认语言 (英语)
- `Resources.zh-hans.resx`: 简体中文

## 🌍 本地化

要添加新语言支持：

1. 在 `Localization/` 目录下创建新的资源文件 (如 `Resources.ja.resx`)
2. 翻译所有字符串资源
3. 在 `App.axaml.cs` 中配置新语言

## 🎨 自定义样式

项目样式定义位于 `Styles/` 目录，可以通过修改这些文件来自定义应用外观。

## 🤝 贡献指南

### 开发规范

1. 遵循 C# 编码规范
2. 使用 PascalCase 命名类和方法
3. 使用 camelCase 命名变量和字段
4. 为所有公共方法和类添加 XML 注释
5. 保持 MVVM 模式的一致性

### 提交代码

1. 创建新分支
2. 实现功能或修复 bug
3. 提交 PR 到主分支
