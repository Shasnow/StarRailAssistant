![ico](/res/SRAico.jpg)
# StarRailAssistant(SRA)
崩坏星穹铁道自动化助手
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
  * 在这里选择好游戏路径，输入账号与密码，`坐和放宽`程序会帮你解决好一切。
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
  * *从不回头看`“爆炸”`*
## 我怎么才能使用SRA？急急急
下载链接：[SRAv0.6](https://github.com/Shasnow/StarRailAssisant/releases)
* 如果你是小白，只需要下载项目中的`zip`文件，*一切都为您准备妥当*，只需解压到您喜欢的位置，然后运行`.exe`即可！
* **我想挑战一下自己！** 当然没问题。打包下载项目中所有文件，确保你的电脑中已经安装好了`Python`，并使用`pip`来安装依赖。请在项目根文件夹打开终端并运行以下指令：
  ```bash
  pip install -r requirements.txt
  ```

什么？你用的是`Python_v3.12`！请额外安装一个库。
  ```bash
  pip install Pillow
  ```

  > 万事俱备，只欠东风
  
  在您最喜爱的**Python编译器**中运行带有 **`SRA`** 前缀的`.py`文件，然后就可以享受`SRA`为您带来的服务。

### 注意事项
* **调整游戏分辨率为1920*1080并保持游戏窗口无遮挡，不要让游戏窗口超出屏幕**
* **执行任务时不要进行其他键鼠操作！请使用游戏默认键位！**
* **还有一件事，菜单要用初始壁纸**
## 你这代码保熟吗？
我们无法保证代码能完美的运行，这便是 **`issues`** 存在的意义。
* 通过 **`issues`** 反馈：https://github.com/Shasnow/StarRailAssisant/issues
* 通过 **`Bilibili私信`** 反馈：https://space.bilibili.com/349682013
* 通过 **`电子邮件`** 反馈：<yukikage@qq.com>
* 或者加入测试群 **994571792** 在这里，你可以：
  * 提前获取版本更新
  * 反馈和意见得到及时回复
  * 与精通 `Python` , `Java` , `C/C++` , `SQL`, `C#` , `Go` , `Vue3` , `HTML` , `JavaScript` , `CSS` , `TypeScript` 的大佬交流。
  * 与 **`太卜司·符玄`** 交流
  * 与*音乐制作人*交流
* 欢迎通过上述渠道反馈问题和提交意见！

## 想要为项目做出贡献！
当然，我们不会拒绝，不过我们会对你提出一些要求：
* 熟悉 `Python` ，这是必须的。
  * 了解 `PySide6` 或其他 `PyQt`、`PySide` 系列库。 *或者——*
  * 了解 `图像识别` 和 `模拟操作` 相关内容。
* 正在游玩并将长期游玩`崩坏：星穹铁道` 。

或许，您可以`另辟蹊径`？
* 尝试为SRA绘制软件图标。`没有稿费`
# 更新公告
beta v0.6 更新公告  
新功能：  
1. 体验优化，新增日志文件 `log.txt` 便于在程序闪退时定位问题。  
2. 新增补充体力功能。  
3. 新增领取兑换码功能。  
4. 新增Windows消息提醒，在任务全部完成时会弹出消息。  
5. 体验优化，现在SRA可以主动获取管理员权限。
   
问题修复：  
1. 修复了在特定情况下未正确移动鼠标导致无法跳转到“侵蚀隧洞”和“历战余响”的问题。  
2. 修复了战斗遇到体力不足时无法处理的问题。  
3. 修正了“执行”与“停止”按钮的行为。  
4. 修复了游戏画面贴近或超出屏幕显示边缘时程序后台直接闪退的问题。
5. 移除了`him`。
   
已知问题：  
1. 在差分宇宙中因奇物“绝对失败处方(进入战斗时，我方全体有150%的基础概率陷入冻结状态，持续1回合)冻结队伍会导致无法开启自动战斗，建议开启游戏的沿用自动战斗设置。  
2. 游戏画面贴近或超出屏幕显示边缘时功能无法正常执行。  
3. 在执行“历战余响”时若未选择关卡，会导致程序闪退。

未来的更新内容（不代表先后顺序）：
1. 角色试用
2. 账号切换
3. 键位适应
   
感谢您对SRA的支持！

----------------------------------------------------------------------------------------------
## 贡献者

感谢以下贡献者对本项目做出的贡献

<a href="https://github.com/Shasnow/StarRailAssistant/graphs/contributors">

  <img src="https://contrib.rocks/image?repo=Shasnow/StarRailAssistant" />

</a>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Shasnow/StarRailAssistant&type=Date)](https://star-history.com/#Shasnow/StarRailAssistant&Date)

----------------------------------------------------------------------------------------------

# 项目优化方向

- [ ] 与B服（世界树）的适配
- [x] 本地账号信息加密
- [ ] 通过全家桶启动器进行启动
- [ ] 定时自启动、自更新等计划事件的添加
- [ ] 优化GUI界面与交互逻辑
- [ ] 项目wiki的编写
- [ ] 添加启动时游戏界面的检测
- [ ] 替换新的小图标（x
- [ ] 拓展功能的添加（如由咱们可爱的 **`太卜司·符玄`** 的提供的占卜awa）
- [ ] 功能解耦合
- [ ] 实现后台有遮挡截图（x
- [ ] 任务完成后退出程序/关机/睡眠

## 过往的更新公告
beta v0.5 更新公告  
新功能：  
1. 结束对饰品提取的维护，现在可以正常使用该功能。  
2. 新增停止按键，在执行任务后，你可以点击此按键来停止执行。  
3. 体验优化，在进入战斗时如果未启用自动战斗，程序会为你启用，除非你再一次取消。  
4. 外观更新，为程序添加了图标。  
5. 外观更新，调整字体大小，保护视力。  
6. 在常见问题中更新了内容。
   
问题修复：  
1. 修复了在勾选“启动游戏”时手动启动游戏后执行任务会导致程序闪退的问题。  
2. 修复了在未启动游戏且未勾选“启动游戏”时执行任务时会导致程序闪退的问题。  
3. 修复了存在回归任务时，领取巡星之礼异常失败的问题。  
4. 修复了巡星之礼第7天奖励无法领取的问题。
   
beta v0.4 更新公告  
重磅更新：自定义清体力！  
新功能：  
1. 体验优化，现在不需要保持窗口居中，但仍然需要窗口无遮挡。  
2. 体验优化，现在可以记录上一次运行时的选择。  
3. 在常见问题中更新了内容。  
4. 在问题反馈中更新了内容。
   
问题修复：  
1. 修复了某些情况下任务结束未正确返回大世界，导致下一个任务无法执行的问题。  
2. 修复了若干问题。
   
beta v0.3 更新公告  
重磅更新：新增图形化界面！  
新功能：  
1. 新增账号登录功能，输入你的账号和密码后（本地），如果启动游戏时未登录，可以自动登录。  
2. 新增领取巡星之礼功能，现在可以帮你领取巡星之礼。  
3. 现在你可以对功能进行一些更加自由的自定义。  
4. 新增退出游戏功能，在任务结束后，可以选择为你关闭游戏。
   
问题修复：  
1. 修复了某些情况下任务结束未正确返回大世界，导致下一个任务无法执行的问题。  
2. 修复了若干问题。
   
