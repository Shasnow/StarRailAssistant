# SRA 日志分析指引

本文件随「导出日志」压缩包一起分发，用于帮助 AI 或人工快速定位问题。请先读完本文件，再按下面的结构阅读日志。

## 1. 压缩包结构

```text
console.log            桌面端控制台捕获的后端进程输出（仅包含本次运行期间的 stderr 输出，2000 行）
AGENTS.md              本说明
frontend/              前端（Avalonia 客户端）Serilog 日志，按天滚动，保留 7 天
backend/               后端（Python）日志，含 log/SRAYYYYMMDD.log 与截图子目录，按天滚动，保留 7 天
  ocr/                 带识别框与文本标注的 OCR 截图（只在开启保存OCR截图时生成）
  screenshot/          失败场景截图
manifest.json          导出时间、应用版本、系统信息、显示器参数与通用设置
```

## 2. 日志格式

后端（loguru）：

```text
14:33:23 | DEBUG | [Start]
14:33:23 | INFO  | TaskManager thread started
14:33:23 | DEBUG | run single task: config=Default, task=CosmicStrifeTask
14:36:21 | INFO  | 任务 'CosmicStrifeTask' 已完成。
14:36:21 | DEBUG | [Done]
```

- 字段依次为 `时间 | 级别 | 消息`，**不含日期**；
- 日期需结合文件名或 frontend 日志推断。
- 从 `[Start]` 开始，到 `[Done]` 结束，中间为一次任务执行。

前端（Serilog）：

```text
[12:34:56 INF] Backend process started successfully (PID: 1234)
```

控制台（console.log）：

- 内容与后端 stderr 基本一致，只包含本次运行期间的 CLI stderr 输出（2000 行），不包含历史运行记录。

## 3. 建议的分析步骤

1. 读 `manifest.json`：确认 `appVersion`、`exportedAt`、操作系统、显示器分辨率与缩放、语言。
2. 先找**最早的 ERROR / 异常堆栈**，不要从最后的报错倒推；后续错误往往是连锁反应。
3. 涉及画面识别时打开 `backend/ocr/` 的标注截图，核对 OCR 文本与模板匹配区域。
4. 涉及游戏窗口时核对分辨率（识别默认按 1920×1080；窗口化需要更大分辨率）与是否以管理员身份运行。

## 4. 输出结论时请包含

- 最早异常出现的时间点与所在文件（`backend/SRAxxx.log` 第 N 行 / `frontend/sraxxx.log`）。
- 判定类别：环境（权限、分辨率、运行库）、配置、资源版本、前后端契约、还是代码缺陷。
- 依据：引用关键日志原文，说明因果关系；不确定时明确写出假设与验证方法。
- 复现步骤建议，以及需要用户补充的信息（是否管理员、游戏分辨率、是否云游戏、使用的任务/配置）。

## 5. 注意事项

- 如果用户未描述问题，先要求用户描述问题，再分析日志。
- 日志可能包含本地路径、账号掩码、UID 映射等个人信息，不要原样公开到公开渠道。
- 不要臆造日志中不存在的信息；找不到证据时说明缺失项，而不是猜测具体行号。
- `console.log` 无日期字段，跨天排查优先使用 `frontend/` 与 `backend/` 的文件名。

## 参考

- [SRA GitHub 仓库](https://github.com/Shasnow/StarRailAssistant)
- [SRA FAQ](https://starrailassistant.top/getting-started/faq/)