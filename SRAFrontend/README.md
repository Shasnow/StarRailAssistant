# StarRailAssistant 前端项目

## 概述

StarRailAssistant (SRA) 前端是一个模块化的 .NET 解决方案，负责 SRA 的 UI 和 API 层，分为三个项目：

- **SRAFrontend** - 共享核心库（模型、服务、工具类，无 UI 依赖）
- **SRAFrontend.Desktop** - Avalonia 桌面应用
- **SRAFrontend.Server** - ASP.NET Core HTTP API 服务

## 技术栈

- .NET 10 / C# 13
- Avalonia UI（桌面端）
- ASP.NET Core（服务端）
- CommunityToolkit.Mvvm
- SukiUI

## 项目结构

```
SRAFrontend/
├── SRAFrontend.sln

├── SRAFrontend/                     # 核心库（平台无关）
│   ├── Data/                        # PageName, DataPath
│   ├── Localization/                # 本地化资源（en, zh）
│   ├── Migrations/                  # 配置/设置版本迁移
│   ├── Models/                      # 数据实体
│   │   ├── AppSettings.cs
│   │   ├── Cache.cs
│   │   ├── TasksConfig.cs
│   │   └── ...
│   ├── Services/                    # 业务逻辑
│   │   ├── IBackendService.cs
│   │   ├── BackendServiceProxy.cs
│   │   ├── ConfigService.cs
│   │   ├── SettingsService.cs
│   │   ├── CacheService.cs
│   │   └── ...
│   └── Utils/                       # 工具类

├── SRAFrontend.Desktop/             # Avalonia 桌面应用
│   ├── Assets/                      # 图标、字体、背景
│   ├── Controls/                    # 自定义控件
│   ├── Models/                      # 桌面端专用模型
│   ├── Services/                    # 桌面端专用服务（OverlayService）
│   ├── Styles/                      # 样式
│   ├── ViewModels/                  # MVVM 视图模型
│   ├── Views/                       # 视图
│   ├── App.axaml                    # 应用入口
│   ├── Program.cs                   # 启动点
│   └── ViewLocator.cs

└── SRAFrontend.Server/              # ASP.NET Core API 服务
    ├── Controllers/
    │   ├── TaskController.cs        # 任务运行/停止/状态/日志（SSE）
    │   ├── ConfigsController.cs     # 配置 CRUD（RESTful）
    │   └── SettingsController.cs    # 设置
    ├── Services/
    │   ├── HostedService.cs         # 生命周期管理
    │   └── LogStreamService.cs      # SSE 日志推送
    └── Program.cs
```

## 构建与运行

### 环境要求

- .NET 10 SDK

### 构建全部项目

```bash
cd SRAFrontend
dotnet build
```

### 运行桌面端

```bash
dotnet run --project SRAFrontend.Desktop
# 开启调试控制台：
dotnet run --project SRAFrontend.Desktop
```

### 运行服务端

```bash
dotnet run --project SRAFrontend.Server
```

## API 接口

运行服务端后，您可以在`http://localhost:5000/swagger`查看API文档。

## 架构说明

- **服务初始化**：所有服务采用两阶段模式 — DI 容器构造后，显式调用 `Load()`/`Initialize()` 方法，避免依赖顺序问题。
- **事件订阅**：`ConfigService` 和 `SettingsService` 通过 `INotifyPropertyChanged`/`INotifyCollectionChanged` 实现属性变更自动保存，切换配置时正确取消/重新订阅事件。
- **后端抽象**：`IBackendService` 接口配合 `BackendServiceProxy`，支持根据设置运行时切换 CLI 和 Python 后端。
