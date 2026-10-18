<p align="center"><img src="/resources/SRAico.png" alt="icon"></p>
<p align="center">
    <img src="https://img.shields.io/badge/platform-Windows-blue" alt="platform">
    <img alt="Static Badge" src="https://img.shields.io/badge/python-3.12-skyblue">
    <img alt="Static Badge" src="https://img.shields.io/badge/.NET-10.0-purple">
    <img alt="GitHub Downloads (all assets, all releases)" src="https://img.shields.io/github/downloads/Shasnow/StarRailAssistant/total">
    <img alt="GitHub Release" src="https://img.shields.io/github/v/release/Shasnow/StarRailAssistant">
    <a href="https://mirrorchyan.com/zh/projects?rid=StarRailAssistant">
        <img alt="mirrorc" src="https://img.shields.io/badge/Mirror%E9%85%B1-%239af3f6?logo=countingworkspro&logoColor=4f46e5">
    </a>
    <a href="https://pypi.org/project/starrailassistant/">
      <img alt="PyPI Version" src="https://img.shields.io/pypi/v/starrailassistant">
    </a>
</p>
<p align="center"><a href="https://starrailassistant.top"><b>Homepage</b></a> | <a href="README.md"><b>中文</b></a></p>

#### [Troubleshooting](https://starrailassistant.top/getting-started/trouble-shooting/) | [FAQ](https://starrailassistant.top/getting-started/faq/) | [Download & Install](https://starrailassistant.top/getting-started/download/) | [Getting Started](https://starrailassistant.top/getting-started/getting-started/)

> The documentation site is currently available in Chinese only.

# 🌟 StarRailAssistant (SRA)

🎮 An automation assistant for Honkai: Star Rail
If you run into any issues while using SRA, please read the [Troubleshooting](https://starrailassistant.top/getting-started/trouble-shooting/) guide first.

If you find this project helpful, a Star ⭐ would be appreciated!

## ❓ What is SRA?

🤖 An image-recognition based automation program for Honkai: Star Rail that takes care of your dailies from launching the game to closing it.

![preview](https://starrailassistant.top/_astro/softwaremain2.C3xP9Cen_6MuUy.webp)

## ⚠️ Disclaimer

This software is an external tool designed to automate gameplay in Honkai: Star Rail.
It is designed to interact with the game only through the existing user interface, and complies with applicable laws and regulations.
This package is not intended to break game balance in any way or to provide any unfair advantage.
This package does not modify any game files or game code in any way.

This software is open source, free of charge and for learning and exchange purposes only. The developer team has the
final right to interpret this project. All problems arising from the use of this software are not related to this
project and the developer team. If you encounter a merchant using this software to practice on your behalf and charging
for it, it may be the cost of equipment and time, etc. The problems and consequences arising from this software have
nothing to do with it.

Please note that, according to miHoYo's [Fair Gaming Declaration for Honkai: Star Rail](https://sr.mihoyo.com/news/111246?nav=news&type=notice):

    "The use of cheats, accelerators, scripts, or other third-party tools that undermine the fairness of the game is strictly prohibited."
    "Once detected, miHoYo (hereinafter also referred to as 'we') will, depending on the severity and frequency of the violations, take measures such as deducting illegitimate gains, freezing game accounts, and permanently banning game accounts."

## ✨ Features

* 🎯 **Launch the game**
  * Select the game path, enter your account and password, then sit back and relax — SRA takes care of everything. The Bilibili server is supported.
* ⚡ **Farm Trailblaze Power**
  * Freely choose the stage, challenge count and challenge order; automatically pick stages and counts based on your training goals.
* 🎁 **Claim rewards**
  * Including: Daily Training, Nameless Honor, assist rewards, redeem code rewards, dispatch rewards, launch gifts for each version, mail rewards, and more.
* 🚀 **Divergent Universe leveling**
  * Automatically stops when the weekly points cap is reached, and claims the points rewards.
* 🎲 **Currency Wars**
  * Automate Standard and Overclock matches (the highest difficulty is not always winnable)
  * Opening reroll: supports any investment environment, investment strategy, Boss name, and Boss affixes, e.g. Jimi and Aventurine
* 🚪 **Exit the game**
  * Optionally exit SRA and shut down the computer.
* 📖 **Auto story mode**
  * Enjoy the story hands-free, with skip support.
* 🔄 **Multi-account switching**
* **Cloud Honkai: Star Rail (云星穹铁道)**
  * Supports the cloud version of the game for background operation.

## ⚠️ Notes

* 📺 **Resolution requirements**:
  * If your screen resolution is **higher than 1080p**, run the game in **1920x1080 windowed** mode, otherwise recognition errors may occur!
  * If your screen resolution is **exactly 1080p**, run the game in **1920x1080 fullscreen** mode, otherwise recognition errors may occur!
* 🖱️ **Important**: **Do not perform any other mouse or keyboard operations while a task is running!**

## 🚀 How do I use SRA?

⬇️ Download link: [SRA](https://github.com/Shasnow/StarRailAssistant/releases/latest)

Release notes: [ChangeLog2.0.md](ChangeLog2.0.md)

Runtime requirements:
Builds containing `StarRailAssistant_DesktopDLC` require the [.NET Desktop Runtime 10.0](https://dotnet.microsoft.com/en-us/download/dotnet/10.0).
Builds containing `StarRailAssistant_ServerDLC` require the [ASP.NET Core Runtime 10.0](https://dotnet.microsoft.com/en-us/download/dotnet/10.0).

* Download the `StarRailAssistant_vX.X.X.zip` file from the Releases page — *everything is ready to go*. Just extract it to a location of your choice and run `SRA.exe`!
* To use the WebUI, no separate download is needed: the WebUI is embedded in the full server package `StarRailAssistant_vX.X.X.zip` (or install the `ServerDLC`). After extraction it is hosted directly by the server — just start the server and access it from your browser.
* To run SRA from source, read the [Contributing Guide](CONTRIBUTING.md).

## 🐛 Any bugs?

We cannot guarantee that the code runs perfectly — that is what **`issues`** are for.

* 📝 Report via **`issues`**: <https://github.com/Shasnow/StarRailAssisant/issues>
* 📧 Report via **email**: <yukikage@qq.com>
* 💬 Or join the test group (QQ group: **994571792** — a Chinese-speaking community), where you can:
    * ~~⚡ Get faster download speeds~~
    * 🆕 Get early access to version updates
    * 💌 Get prompt replies to feedback and suggestions
    * 🤝 Chat with developers skilled in `Python`, `Java`, `C/C++`, `SQL`, `C#`, `Go`, `Vue3`, `HTML`, `JavaScript`, `CSS`, `TypeScript`
    * ✨ Trade friendship magic with **`Twilight Sparkle`**
    * 🎮 Slack off with **`Qingque`**
    * 🧠 Get counseling from **`Yumemizuki Mizuki`**
* Feedback and suggestions via any of the channels above are welcome!

## 🤝 Contributing

Please read the [Contributing Guide](CONTRIBUTING.md).

----------------------------------------------------------------------------------------------

## 🙏 Contributors

Thanks to the following contributors for their contributions to this project

<a href="https://github.com/Shasnow/StarRailAssistant/graphs/contributors">

  <img src="https://contrib.rocks/image?repo=Shasnow/StarRailAssistant"  alt="contrib"/>

</a>

## ⭐ Star History

<a href="https://www.star-history.com/?repos=Shasnow%2FStarRailAssistant&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=Shasnow/StarRailAssistant&type=date&theme=dark&legend=top-left&sealed_token=-d1hfRmVNv67qW-5NaLnQpmr58Vatft_y975chPsQxz3vrLBmXMjqH_G2XuU9t1rwl-NqjNBgKKmYL_3inwquYr1j0QEtL-uiclG-hR18uUPLcpm2mb92g" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=Shasnow/StarRailAssistant&type=date&theme=light&legend=top-left&sealed_token=-d1hfRmVNv67qW-5NaLnQpmr58Vatft_y975chPsQxz3vrLBmXMjqH_G2XuU9t1rwl-NqjNBgKKmYL_3inwquYr1j0QEtL-uiclG-hR18uUPLcpm2mb92g" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=Shasnow/StarRailAssistant&type=date&theme=light&legend=top-left&sealed_token=-d1hfRmVNv67qW-5NaLnQpmr58Vatft_y975chPsQxz3vrLBmXMjqH_G2XuU9t1rwl-NqjNBgKKmYL_3inwquYr1j0QEtL-uiclG-hR18uUPLcpm2mb92g" />
 </picture>
</a>

----------------------------------------------------------------------------------------------
