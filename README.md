<p align="center"><img src="/resources/SRAico.png" alt="icon"></p>
<p align="center">
    <img src="https://img.shields.io/badge/platform-Windows-blue" alt="platform">
    <img alt="Static Badge" src="https://img.shields.io/badge/python-3.12-skyblue">
    <img alt="Static Badge" src="https://img.shields.io/badge/.NET-8.0-purple">
    <img alt="GitHub Downloads (all assets, all releases)" src="https://img.shields.io/github/downloads/Shasnow/StarRailAssistant/total">
    <img alt="GitHub Release" src="https://img.shields.io/github/v/release/Shasnow/StarRailAssistant">
    <a href="https://mirrorchyan.com/zh/projects?rid=StarRailAssistant">
        <img alt="mirrorc" src="https://img.shields.io/badge/Mirror%E9%85%B1-%239af3f6?logo=countingworkspro&logoColor=4f46e5">
    </a>
</p>
<p align="center"><a href="https://starrailassistant.top"><b>主页</b></a></p>

#### [问题排查](https://starrailassistant.top/trouble/having_trouble.html) | [FAQ](https://starrailassistant.top/faq.html) | [下载和安装](https://starrailassistant.top/download.html) | [使用方法](https://starrailassistant.top/getstarted/getstarted.html)

# 🌟 StarRailAssistant(SRA)

🎮 崩坏星穹铁道自动化助手  
如果您在使用的过程中遇到问题，请先阅读[问题排查](https://starrailassistant.top/trouble/having_trouble.html)。

## ❓ 什么是SRA？

🤖 一个基于图像识别的崩铁自动化程序，帮您完成从启动到退出的崩铁日常。

![预览](https://starrailassistant.top/img/use/softwaremain2.png)

## ⚠️ 免责声明

本软件是一个外部工具旨在自动化《崩坏：星穹铁道》的游戏玩法。
它被设计成仅通过现有用户界面与游戏交互,并遵守相关法律法规。
该软件包不打算以任何方式破坏游戏平衡或提供任何不公平的优势。
该软件包不会以任何方式修改任何游戏文件或游戏代码。

This software is open source, free of charge and for learning and exchange purposes only. The developer team has the
final right to interpret this project. All problems arising from the use of this software are not related to this
project and the developer team. If you encounter a merchant using this software to practice on your behalf and charging
for it, it may be the cost of equipment and time, etc. The problems and consequences arising from this software have
nothing to do with it.

本软件开源、免费，仅供学习交流使用。
开发者团队拥有本项目的最终解释权。
使用本软件产生的所有问题与本项目与开发者团队无关。
若您遇到商家使用本软件进行代练并收费，可能是设备与时间等费用，产生的问题及后果与本软件无关。

请注意，根据MiHoYo的 [崩坏:星穹铁道的公平游戏宣言](https://sr.mihoyo.com/news/111246?nav=news&type=notice):

    "严禁使用外挂、加速器、脚本或其他破坏游戏公平性的第三方工具。"
    "一经发现，米哈游（下亦称“我们”）将视违规严重程度及违规次数，采取扣除违规收益、冻结游戏账号、永久封禁游戏账号等措施。"

## ✨ 有什么功能？

* 🎯 **启动游戏**
  * 在这里选择好游戏路径，输入账号与密码，`坐和放宽`程序会帮你解决好一切。已经适配b服。
* ⚡ **清体力**
  * 您可以自由选择关卡，是否`补充体力`、`连战次数`、`执行次数`，一切都交由您来决定，也可以`混合搭配`。
* 🎁 **领取奖励**
  * 包括：每日实训、无名勋礼、助战奖励、兑换码奖励、派遣奖励、巡星之礼、邮件奖励等。
* 🚀 **差分宇宙刷等级**
* 🎲 **货币战争**
  * 标准博弈、超频博弈自动化（最高难度不一定能赢）
  * 刷开局：支持任意投资环境、投资策略，如叽米、砂金
* 🚪 **退出游戏**
  * 可选退出SRA以及关闭计算机。
* 📖 **自动剧情**
  * 解放双手，享受剧情，支持`跳过`
* 🔄 **多账号切换**

## 🚀 我怎么才能使用SRA？急急急

⬇️ 下载链接：[SRA](https://github.com/Shasnow/StarRailAssistant/releases/latest)

**自2.0.0版本后，SRA需要`.NET 8.0。`**

* 🎯 **小白友好版**：在Release页面下载`StarRailAssistant_vX.X.X.zip`文件，*一切都为您准备妥当*，只需解压到您喜欢的位置，然后运行`SRA.exe`即可！
* 🔧 **开发者版**：从源码运行SRA，适合想要自定义或贡献代码的开发者。

  ### 📋 **环境要求**
  - **操作系统**：Windows 10 或 Windows 11 (推荐)
  - **Python**：3.12 或更高版本（需添加到系统环境变量）
  - **.NET SDK**：8.0 或更高版本（下载地址：[.NET 8.0 SDK](https://dotnet.microsoft.com/zh-cn/download/dotnet/8.0)）
  - **Git**：用于克隆仓库（可选，但推荐）

  ### 📥 **获取源码**
  ```bash
  # 克隆仓库（推荐）
  git clone https://github.com/Shasnow/StarRailAssistant.git
  cd StarRailAssistant
  
  # 或直接下载 ZIP 压缩包并解压
  ```

  ### 📦 **安装 Python 依赖**
  ```bash
  # 使用 pip 安装所有依赖
  pip install -r requirements.txt
  
  # 如果遇到安装失败的情况，尝试使用以下命令
  pip install -r requirements.txt --upgrade --no-cache-dir
  
  ```

  ### 🏗️ **构建前端项目**
  ```bash
  # 进入前端目录
  cd SRAFrontend
  
  # 还原 NuGet 依赖（首次构建时必须执行）
  dotnet restore -r win-x64
  
  # 构建前端项目（Release 模式）
  dotnet publish -c Release -r win-x64
  
  # 构建完成后，可执行文件将位于：
  # ./SRAFrontend/bin/Release/net8.0/win-x64/publish/SRA.exe
  
  # 返回项目根目录
  cd ..
  ```

  ### 🚀 **直接运行（开发模式）**
  如果您不想构建可执行文件，可以直接运行：
  ```bash
  # 启动前端（开发模式）
  cd SRAFrontend
  dotnet run
  
  # 在另一个终端中启动后端
  cd ..
  python main.py
  ```

  ### 📦 **构建完整发布包**
  ```bash
  # 运行打包脚本
  python ./package.py
  
  # 打包脚本会自动执行以下操作：
  # 收集所有必要的文件（含前端构建输出，所以确保前端已构建）
  # 创建 ZIP 压缩包
  
  # 完成后，发布包将位于项目根目录，命名格式为：StarRailAssistant_vX.X.X.zip
  ```

  ### 🎯 **运行构建后的应用**
  1. 解压生成的 ZIP 压缩包
  2. 运行 `SRA.exe` 启动应用程序

  ### ⚠️ **常见问题与解决方案**
  - **Python 依赖安装失败**：尝试使用国内镜像源，如：
    ```bash
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    ```
    
  - **前端构建失败**：确保已安装 .NET 8.0 SDK，并尝试重新还原依赖：
    ```bash
    dotnet restore ./SRAFrontend/SRAFrontend.csproj -r win-x64 --force
    ```
    
  - **运行时缺少 DLL 文件**：确保构建时使用了 `--self-contained true` 参数，或安装对应版本的 .NET 运行时。
    
  - **图像识别不准确**：确保游戏分辨率设置为 1920x1080（全屏或窗口模式），并检查 `resources/img/` 目录下的模板图片是否完整。

### 😡 我不想安装 .NET 8.0 

没关系!🤗 SRA 甚至有**社区版**🤓，您可以在 [这里](https://github.com/EveGlowLuna/StarRailAssistant-CommunityEdition) 查看。

社区版使用 Tauri + Vue 3 重构了前端界面，使您可以在不安装 .NET 8.0 的情况下运行 SRA 🥵

除此之外并无其他区别。

### ⚠️ 注意事项

* 📺 **分辨率要求**：
  * 如果你的屏幕分辨率**大于1080p**，请将游戏调整至**1920x1080窗口模式**下运行，否则可能出现识别错误！
  * 如果你的屏幕分辨率**等于1080p**，请将游戏调整至**1920x1080全屏**模式下运行，否则可能出现识别错误！
* 🖱️ **操作提示**：**执行任务时不要进行其他键鼠操作！**

## 📁 项目结构

```
├── .github/               # 🔧 GitHub相关配置文件
├── SRACore/               # 🐍 Python后端核心代码
│   ├── localization/      # 🌐 本地化支持
│   ├── task/              # 📋 任务相关代码
│   ├── thread/            # 🧵 线程管理
│   ├── triggers/          # ⚡ 触发器实现
│   ├── ui/                # 🎨 UI相关代码
│   └── util/              # 🛠️ 工具函数
├── SRAFrontend/           # 🎯 C#前端代码 (Avalonia框架)
│   ├── Assets/            # 📦 前端资源文件
│   ├── Controls/          # 🎛️ 自定义控件
│   ├── Data/              # 📊 数据模型
│   ├── Localization/      # 🌐 前端本地化
│   ├── Models/            # 📐 业务模型
│   ├── Services/          # 💼 服务层
│   ├── Styles/            # 🎨 样式定义
│   ├── Utilities/         # 🛠️ 前端工具类
│   ├── ViewModels/        # 🧠 ViewModel层
│   └── Views/             # 🖥️ 视图层
├── main.py                # 🚪 程序入口文件
├── package.py             # 📦 打包脚本
├── rapidocr_onnxruntime/  # 👁️ OCR识别相关模型
├── requirements.txt       # 📋 Python依赖列表
├── resources/             # 📁 资源文件目录
│   ├── img/               # 🖼️ 图像资源
│   ├── test/              # 🧪 测试资源
├── setup/                 # 📦 安装包制作相关文件
├── tasks/                 # 📋 任务实现目录
└── version.json           # 🔢 版本信息
```

### 📁 主要目录说明

- **SRACore/**: 🐍 包含程序的核心逻辑，包括任务管理、线程控制、触发器系统和工具函数等。
- **SRAFrontend/**: 🎯 使用Avalonia框架开发的C#前端界面，实现用户交互和配置管理。
- **tasks/**: 📋 各种自动化任务的具体实现，如启动游戏、领取奖励、清体力等。
- **resources/**: 📁 存放程序所需的各种资源文件，包括图像识别所需的模板图片。

### 📄 关键文件说明

- **main.py**: 🚪 程序的入口点，负责解析命令行参数并启动后端服务。
- **requirements.txt**: 📋 列出了项目所需的所有Python依赖包。
- **package.py**: 📦 用于将项目打包为可执行文件的脚本。
- **version.json**: 🔢 存储项目的版本信息。

## 🐛 你这代码保熟吗？

我们无法保证代码能完美的运行，这便是 **`issues`** 存在的意义。

* 📝 通过 **`issues`** 反馈：<https://github.com/Shasnow/StarRailAssisant/issues>
* 📧 通过 **`电子邮件`** 反馈：<yukikage@qq.com>
* 💬 或者加入测试群 **994571792** 在这里，你可以：
    * ~~⚡ 获得更快的下载速度~~
    * 🆕 提前获取版本更新
    * 💌 反馈和意见得到及时回复
    * 🤝 与精通 `Python` , `Java` , `C/C++` , `SQL`, `C#` , `Go` , `Vue3` , `HTML` , `JavaScript` , `CSS` , `TypeScript`
      的大佬交流。
    * ✨ 与 **`暮光闪闪`** 交流友谊的魔法
    * 🎮 和 **`青雀`** 一起摸鱼
    * 😺 体验 **`柔情猫娘`** 的温柔
* 欢迎通过上述渠道反馈问题和提交意见！

## 🤝 想要为项目做出贡献

### 参与后端开发：

* 🐍 熟悉 `Python` 。
* 🎮 正在游玩并将长期游玩`崩坏：星穹铁道` 。

### 参与前端开发：

* 🎯 熟悉 `C#` 以及 `Avalonia` 框架。

### 本地化支持：

为了减少工作量，SRA仅对日志级别高于或等于`INFO`的日志进行本地化支持。其他日志内容将保持英文。

SRA 后端采用 `pyl10nc` 进行本地化支持，欢迎为SRA贡献更多语言的翻译！
1. 克隆仓库并创建新的分支
2. 在 `SRACore/localization/` 目录下编辑 `resource.toml` 文件，添加新的语言支持
示例：
```toml
[cli.intro] # 资源键
en-us = "SRA-cli {version} ({core})\nType 'help' or '?' to list commands." # 现有的英文翻译
zh-cn = "SRA-cli {version} ({core})\n输入 'help' 或 '?' 来查看命令列表。" # 现有的中文翻译
```
新增语言键：
```toml
[cli.intro]
# ......
es-es = "SRA-cli {version} ({core})\nEscriba 'help' o '?' para listar los comandos." # 新增的西班牙语翻译
```
3. 提交 Pull Request

SRA 前端采用 `ResX` 进行本地化支持，推荐使用 `Rider` 或 `Visual Studio` 进行编辑。

### 另辟蹊径

* 🎨 尝试为SRA绘制软件图标。`没有稿费`

感谢您对SRA的支持！

----------------------------------------------------------------------------------------------

## 🙏 贡献者

感谢以下贡献者对本项目做出的贡献

<a href="https://github.com/Shasnow/StarRailAssistant/graphs/contributors">

  <img src="https://contrib.rocks/image?repo=Shasnow/StarRailAssistant"  alt="contrib"/>

</a>

## 💖 赞助者

感谢以下用户对本项目的赞助
<div>
<div style="float:left">
<img src="https://avatars.githubusercontent.com/u/79625207?v=4" height="50" width="50" alt="avatars">
&nbsp;
</div>

<div>
<a href="https://github.com/sanhaQAQ">Sanha</a><br>
<a href="https://www.miyoushe.com/sr/article/62787970">推荐链接</a>
</div>
</div>

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Shasnow/StarRailAssistant&type=Date)](https://star-history.com/#Shasnow/StarRailAssistant&Date)

----------------------------------------------------------------------------------------------


