<p align="center"><img src="/res/SRAico.png"></p>
<p align="center">
    <img src="https://img.shields.io/badge/platform-Windows-blue" alt="platform">
    <img alt="Static Badge" src="https://img.shields.io/badge/python-3.11.5%2B-skyblue">
    <img alt="GitHub Downloads (all assets, all releases)" src="https://img.shields.io/github/downloads/Shasnow/StarRailAssistant/total">
    <img alt="GitHub Release" src="https://img.shields.io/github/v/release/Shasnow/StarRailAssistant">
    <a href="https://mirrorchyan.com/zh/projects">
        <img alt="mirrorc" src="https://img.shields.io/badge/Mirror%E9%85%B1-%239af3f6?logo=countingworkspro&logoColor=4f46e5">
    </a>
</p>
<p align="center"><a href="https://shasnow.github.io/SRA"><b>主页</b></a></p>

#### [帮助文档](https://docs.qq.com/doc/DWUFOUmJDc2xLRk1B) | [FAQ](https://github.com/Shasnow/StarRailAssistant/wiki/FAQ) | [下载和安装](https://shasnow.github.io/SRA/download.html) | [使用方法](https://shasnow.github.io/SRA/quickstart.html)
# StarRailAssistant(SRA)

崩坏星穹铁道自动化助手  
如果您在使用的过程中遇到问题，请先阅读帮助文档。

## 什么是SRA？

一个基于图像识别的崩铁自动化程序，帮您完成从启动到退出的崩铁日常。

## 免责声明

本软件是一个外部工具旨在自动化崩坏星轨的游戏玩法。它被设计成仅通过现有用户界面与游戏交互,并遵守相关法律法规。该软件包旨在提供简化和用户通过功能与游戏交互,并且它不打算以任何方式破坏游戏平衡或提供任何不公平的优势。该软件包不会以任何方式修改任何游戏文件或游戏代码。

This software is open source, free of charge and for learning and exchange purposes only. The developer team has the final right to interpret this project. All problems arising from the use of this software are not related to this project and the developer team. If you encounter a merchant using this software to practice on your behalf and charging for it, it may be the cost of equipment and time, etc. The problems and consequences arising from this software have nothing to do with it.

本软件开源、免费，仅供学习交流使用。开发者团队拥有本项目的最终解释权。使用本软件产生的所有问题与本项目与开发者团队无关。若您遇到商家使用本软件进行代练并收费，可能是设备与时间等费用，产生的问题及后果与本软件无关。

请注意，根据MiHoYo的 [崩坏:星穹铁道的公平游戏宣言](https://sr.mihoyo.com/news/111246?nav=news&type=notice):

    "严禁使用外挂、加速器、脚本或其他破坏游戏公平性的第三方工具。"
    "一经发现，米哈游（下亦称“我们”）将视违规严重程度及违规次数，采取扣除违规收益、冻结游戏账号、永久封禁游戏账号等措施。"

## 有什么功能？

* 启动游戏
  * 在这里选择好游戏路径，输入账号与密码，`坐和放宽`程序会帮你解决好一切。已经适配b服。
  * 或直接使用云·星穹铁道。（测试）
* 领取助战奖励
* 领取兑换码奖励
  * 可以一次性输入多个`兑换码`，确保每个`兑换码`分隔开。
* 领取派遣奖励
* 领取巡星之礼
  * *最爱的十连*
* 领取邮件
* 清体力
  * 您可以自由选择关卡，是否`补充体力`、`连战次数`、`执行次数`，一切都交由您来决定，也可以`混合搭配`。
* 领取每日实训
  * *最爱的`星琼`*
* 领取无名勋礼
* 退出游戏
  * *从不回头看`“爆炸”`*，可选退出SRA以及关闭计算机。
* 自动剧情
  * 只包含点击对话
* 多账号切换

## 我怎么才能使用SRA？急急急

下载链接：  
下载更新器，借助更新器下载：[SRA更新器](https://github.com/Shasnow/SRAUpdater/releases/download/SRAUpdater/SRAUpdater.zip)
或者直接下载本体，里面包含了更新器：[SRAv0.7.6](https://github.com/Shasnow/StarRailAssistant/releases/download/v0.7.6/StarRailAssistant_v0.7.6.zip)

* 如果你是小白，只需要下载项目中的`zip`文件，*一切都为您准备妥当*，只需解压到您喜欢的位置，然后运行`.exe`即可！
* **我想挑战一下自己！** 当然没问题。打包下载项目中所有文件，确保你的电脑中已经安装好了`Python`，并使用`pip`来安装依赖。请在项目根文件夹打开终端并运行以下指令：
  ```bash
  pip install -r requirements.txt
  ```

  > 万事俱备，只欠东风
  
  在您最喜爱的**Python编译器**中运行 **`SRA.py`** 文件，然后就可以享受`SRA`为您带来的服务。

### 注意事项

* **调整游戏分辨率为1920*1080（推荐）并保持游戏窗口无遮挡，不要让游戏窗口超出屏幕**
* **执行任务时不要进行其他键鼠操作！** 除非使用云·星穹铁道
* **还有一件事，菜单要用初始壁纸**

## 你这代码保熟吗？

我们无法保证代码能完美的运行，这便是 **`issues`** 存在的意义。

* 通过 **`issues`** 反馈：<https://github.com/Shasnow/StarRailAssisant/issues>
* 通过 **`Bilibili私信`** 反馈：<https://space.bilibili.com/349682013>
* 通过 **`电子邮件`** 反馈：<yukikage@qq.com>
* 或者加入测试群 **994571792** 在这里，你可以：
  * 获得更快的下载速度
  * 提前获取版本更新
  * 反馈和意见得到及时回复
  * 与精通 `Python` , `Java` , `C/C++` , `SQL`, `C#` , `Go` , `Vue3` , `HTML` , `JavaScript` , `CSS` , `TypeScript` 的大佬交流。
  * 与 **`太卜司·符玄`** 交流占卜术
  * 与 **`暮光闪闪`** 交流友谊的魔法
  * 和 **`青雀`** 一起摸鱼
* 欢迎通过上述渠道反馈问题和提交意见！

## 想要为项目做出贡献

当然，我们不会拒绝，不过我们会对你提出一些要求：

* 熟悉 `Python` ，这是必须的。
  * 了解 `PySide6` 或其他 `PyQt`、`PySide` 系列库。 *或者——*
  * 了解 `图像识别` 和 `模拟操作` 相关内容。
* 正在游玩并将长期游玩`崩坏：星穹铁道` 。
* 熟悉网页前端设计。

[点击了解SRA的开发计划](https://docs.qq.com/aio/DWUN3Qm54a2pkZ09x?nlc=1&p=FcrsSwXMOYoR5yq7bxjeLD)

或许，您可以`另辟蹊径`？

* 尝试为SRA绘制软件图标。`没有稿费`

感谢您对SRA的支持！

----------------------------------------------------------------------------------------------

## 贡献者

感谢以下贡献者对本项目做出的贡献

<a href="https://github.com/Shasnow/StarRailAssistant/graphs/contributors">

  <img src="https://contrib.rocks/image?repo=Shasnow/StarRailAssistant" />

</a>

## 赞助者
感谢以下用户对本项目的赞助
<div>
<div style="float:left">
<img src="https://avatars.githubusercontent.com/u/79625207?v=4" height="50" width="50">
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

# 项目优化方向 ~~（画大饼环节）~~

* [x] 多账号托管和切换
* [ ] 战利品查漏补缺
* [ ] 兼容云·星穹铁道
* [x] 与B服（世界树）的适配
* [x] 本地账号信息加密
* [x] 通过全家桶启动器进行启动
* [x] 定时自启动、自更新等计划事件的添加
* [x] 优化GUI界面与交互逻辑
* [x] 项目wiki的编写
* [x] 添加启动时游戏界面的检测
* [x] 替换新的小图标（x
* [x] 拓展功能的添加（如由咱们可爱的 **`太卜司·符玄`** 的提供的占卜awa）
* [x] 任务完成后退出程序/关机/睡眠
