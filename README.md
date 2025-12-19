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

#### [帮助文档](https://docs.qq.com/doc/DWUFOUmJDc2xLRk1B) | [FAQ](https://starrailassistant.top/faq.html) | [下载和安装](https://starrailassistant.top/download.html) | [使用方法](https://starrailassistant.top/getstarted/getstarted.html)

# StarRailAssistant(SRA)

崩坏星穹铁道自动化助手  
如果您在使用的过程中遇到问题，请先阅读[常见问题](https://starrailassistant.top/faq.html)。

## 什么是SRA？

一个基于图像识别的崩铁自动化程序，帮您完成从启动到退出的崩铁日常。

![preview](https://starrailassistant.top/img/use/softwaremain2.png)

## 免责声明

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

## 有什么功能？

* 启动游戏
  * 在这里选择好游戏路径，输入账号与密码，`坐和放宽`程序会帮你解决好一切。已经适配b服。
* 清体力
  * 您可以自由选择关卡，是否`补充体力`、`连战次数`、`执行次数`，一切都交由您来决定，也可以`混合搭配`。
* 领取奖励
  * 包括：每日实训、无名勋礼、助战奖励、兑换码奖励、派遣奖励、巡星之礼、邮件奖励等。
* 差分宇宙刷等级
* 货币战争
* 退出游戏
  * 可选退出SRA以及关闭计算机。
* 自动剧情
  * 解放双手，享受剧情，支持`跳过`
* 多账号切换

## 我怎么才能使用SRA？急急急

下载链接：[SRA](https://github.com/Shasnow/StarRailAssistant/releases/latest)

**自2.0.0版本后，SRA需要`.NET 8.0。`**

* 如果你是小白，只需要下载项目中的`zip`文件，*一切都为您准备妥当*，只需解压到您喜欢的位置，然后运行`SRA.exe`即可！
* **我想挑战一下自己！** 尽管不再推荐这种方式，但我们仍然会指导你如何从源码运行SRA。
  环境要求：
    * `Python` 3.12+
    * `.NET 8.0`

  安装依赖：
  ```bash
  pip install -r requirements.txt
  ```

  构建前端：使用下面的命令将前端项目构建为可执行文件。
  ```bash
  dotnet publish -c Release -r win-x64 ./SRAFrontend/SRAFrontend.csproj
  ```

  构建后端：使用下面的命令将后端项目构建为可执行文件。
  ```bash
  python ./package.py
  ```
  完成后，您可以在项目根目录找到创建好的压缩包，解压即可使用。

### 注意事项

* 如果你的屏幕分辨率**大于1080p**，请将游戏调整至**1920x1080窗口模式**下运行，否则可能出现识别错误！
* 如果你的屏幕分辨率**等于1080p**，请将游戏调整至**1920x1080全屏**模式下运行，否则可能出现识别错误！
* **执行任务时不要进行其他键鼠操作！**
* 如果在构建前端后发现前端缺少文件，请考虑使用以下指令，然后重新构建前端
  ```bash
  dotnet restore ./SRAFrontend/SRAFrontend.csproj -r win-x64
  ```

## 你这代码保熟吗？

我们无法保证代码能完美的运行，这便是 **`issues`** 存在的意义。

* 通过 **`issues`** 反馈：<https://github.com/Shasnow/StarRailAssisant/issues>
* 通过 **`电子邮件`** 反馈：<yukikage@qq.com>
* 或者加入测试群 **994571792** 在这里，你可以：
    * ~~获得更快的下载速度~~
    * 提前获取版本更新
    * 反馈和意见得到及时回复
    * 与精通 `Python` , `Java` , `C/C++` , `SQL`, `C#` , `Go` , `Vue3` , `HTML` , `JavaScript` , `CSS` , `TypeScript`
      的大佬交流。
    * 与 **`暮光闪闪`** 交流友谊的魔法
    * 和 **`青雀`** 一起摸鱼
    * 体验 **`柔情猫娘`** 的温柔
* 欢迎通过上述渠道反馈问题和提交意见！

## 想要为项目做出贡献

当然，我们不会拒绝，不过我们会对你提出一些要求：

如果你希望参与后端开发，你需要：

* 熟悉 `Python` 。
* 正在游玩并将长期游玩`崩坏：星穹铁道` 。

如果你希望参与前端开发，你需要：

* 熟悉 `C#` 以及 `Avalonia` 框架。

或许，您可以`另辟蹊径`？

* 尝试为SRA绘制软件图标。`没有稿费`

感谢您对SRA的支持！

----------------------------------------------------------------------------------------------

## 贡献者

感谢以下贡献者对本项目做出的贡献

<a href="https://github.com/Shasnow/StarRailAssistant/graphs/contributors">

  <img src="https://contrib.rocks/image?repo=Shasnow/StarRailAssistant"  alt="contrib"/>

</a>

## 赞助者

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

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Shasnow/StarRailAssistant&type=Date)](https://star-history.com/#Shasnow/StarRailAssistant&Date)

----------------------------------------------------------------------------------------------


