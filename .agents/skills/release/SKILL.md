---
name: release
description: 为 StarRailAssistant 执行发版，含版本号是否已发布的检查、ver:patch/ver:pre/ver:release 递增、推送 main 并触发 python-app.yml 工作流。当用户要求发版、发正式版、发 beta/预发布或预发布转正式版时使用。不用于普通提交、代码打包或本地构建。
---

# StarRailAssistant 发版

发布目标是 `origin`（Shasnow/StarRailAssistant）。release 的 tag 与标题均为 `v<package.json 的 version>`。CI 的 `pre_check` 要求仓库是 `Shasnow/StarRailAssistant`，在 fork 上触发会直接失败。

## 0. 前提确认

- `gh auth status` 已登录，且具备 repo + workflow 权限。
- 当前在 `main`，工作区干净：`git status -sb`。若有未提交改动，先问用户如何处理，不要擅自提交无关改动。
- 本地不落后也不领先 origin：`git fetch origin` 后 `git log origin/main..HEAD --oneline` 与 `git log HEAD..origin/main --oneline` 均应为空。
- `ChangeLog2.0.md` 中已有本次版本的条目。工作流的 release notes 与 `version_info.txt` 都取自该文件；缺失时提醒用户补充后再继续。

## 1. 普通发版

读取当前版本并检查是否已发布：

```powershell
$v = (Get-Content package.json -Raw | ConvertFrom-Json).version
gh release view "v$v" --repo Shasnow/StarRailAssistant --json tagName,isPrerelease
```

- 输出 `release not found`（或命令非零退出）→ 该版本尚未发布，不改版本号，直接进入第 3 步。
- 已发布 → 按用户要求递增版本号：
  - 正式版：`npm.cmd run ver:patch`
  - beta/预发布：`npm.cmd run ver:pre`
    - 若当前是已发布的正式版（如 `2.25.1`），`ver:pre` 会得到 `2.25.1-beta.1`；要发下一个版本的 beta，应先 `npm.cmd run ver:patch` 再 `npm.cmd run ver:pre`，得到 `2.25.2-beta.1`。

版本脚本会同时更新三处：`package.json`、`SRACore/util/const.py`、`SRAFrontend/SRAFrontend/Models/AppSettings.cs`。

## 2. 预发布转正式版

用户要求把当前 beta 转为正式版时：

```powershell
npm.cmd run ver:release   # 2.25.2-beta.3 -> 2.25.2
```

## 3. 提交并推送

仅当版本号发生变更时提交：

```powershell
git add package.json SRACore/util/const.py SRAFrontend/SRAFrontend/Models/AppSettings.cs ChangeLog2.0.md
git commit -m "chore: 发布 v<新版本号>"
git push origin main
```

提交消息使用中文约定式提交。必须在推送成功后再触发工作流，因为 release 的 tag 指向 `main`，CI 构建的是远端 `main` 上的代码。

## 4. 触发发版工作流

```powershell
gh workflow run python-app.yml --repo Shasnow/StarRailAssistant --ref main
gh run list --workflow=python-app.yml --repo Shasnow/StarRailAssistant --limit 1
gh run watch <run-id> --repo Shasnow/StarRailAssistant
```

工作流链路：`build-artifacts` → `publish_release` → `mirrorchyan` → `auto_mas`。同名 release 已存在时会先删除再重建。

工作流运行时间较长，不必等它完成。

## 禁止

- 不要手写修改版本号，必须使用 `npm.cmd run ver*`（三处文件需同步）。
- 不要在推送前触发工作流，也不要在 `main` 上 force push。
- 不要跳过 `ChangeLog2.0.md` 的发版条目。
