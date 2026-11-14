# 自动切号扩展

在 SRA 启动游戏时，把 `StartGameTask` 的登录流程替换为「历史账号选号」：插件只负责在登录页选中目标账号并确认登录，密码始终由游戏客户端从本地登录记录中回填，插件不读取也不保存密码。

这是一个**无执行逻辑**扩展（`executable=False`）：不需要点“运行”，只在扩展页面启用/禁用。

## 启用方式

- 桌面端 / WebUI：进入「扩展」页面，打开「自动切号」的启用开关。
- CLI：

```text
sra> extension list
sra> extension enable AccountSwitch
sra> extension disable AccountSwitch
```

`extension list --json` 中可以看到该扩展的 `executable: false` 与当前 `enabled` 状态。

## 配置项

配置保存在 `%APPDATA%\SRA\extensions.json`（Linux 为 `~/.config/SRA/extensions.json`）中 `AccountSwitch` 节点下，也可以在前端配置表单或 CLI 中修改：

```json
{
  "enabled": true,
  "account_hint": "138****5678"
}
```

| 字段 | 说明 |
|---|---|
| `enabled` | 是否启用自动切号。关闭时会还原对 `StartGameTask` 的修改。 |
| `account_hint` | 目标账号提示，**单个账号**。支持完整手机号/账号、登录页脱敏片段（`138****5678`）、邮箱（`qin***@qq.com`）。留空则不使用提示词兜底。 |

CLI 修改示例：

```text
sra> extension config set AccountSwitch '{"enabled": true, "account_hint": "138****5678"}'
```

> `account_hint` 会以明文保存在 `extensions.json`，建议只填脱敏片段或邮箱，不要填密码。

## 目标账号来源（优先级从高到低）

1. **AUTO-MAS 花名册**：由 AUTO-MAS 拉起 SRA 时，从命令行里的 `sra-config` 路径反查 `config/scripts.yaml`（旧版 `config/ScriptConfig.json`），读取该用户 `Info.Id` 并用 DPAPI 解密出账号。
2. **扩展配置 `account_hint`**：手动运行 SRA、或挂机守护脚本设置 `ZZ_SRA_OVERNIGHT=1` 时使用。
3. 两者都没有时回退原版登录流程。

安全策略：本进程确由 AUTO-MAS 拉起、但花名册解析失败时，插件会**拒绝**用 `account_hint` 顶替，避免多账号场景下切成别的号。

## 使用场景

### 手动运行 SRA

1. 启用扩展，填写 `account_hint`。
2. 任务配置中开启「自动登录」，但**账号/密码留空**。插件会在需要填账密时改用历史账号选号。
3. 若账号/密码已填全，则沿用原版账密登录，插件不介入。

### 挂机守护

守护脚本设置环境变量 `ZZ_SRA_OVERNIGHT=1` 后启动 SRA，插件直接用 `account_hint` 选号，忽略 `isAutoLogin` 与 MAS 配置。

### AUTO-MAS 托管

无需填写 `account_hint`，插件自动按花名册选号。若任务配置开启了「自动登录」且非挂机模式，则沿用原版账密登录。

## 登录与登出行为

- 登录页：OCR 识别当前显示的账号，与目标一致则直接点「进入游戏」；不一致则点击账号框唤出历史账号下拉，匹配目标号后点选，再点「登录」。
- 已在游戏内：若 15 分钟内已核对过，或主界面 UID 与映射一致，则沿用当前会话；否则先登出再切号。
- 登出走「电源图标 → 返回登录页面」，遇到「保留/清除登录记录」弹窗时固定选择**保留**，不会清除登录记录。

## UID 终验

进入游戏后 OCR 左下角 `UID:xxxxxxxxx`，并核对程序根目录的 `zz_uid_map.txt`：

```text
# 每行：用户名或账号=游戏内UID
138****5678=123456789
```

- 首次由插件登录成功会自动写入该文件；条目冲突只报错、不覆盖。
- UID 与目标不一致、或 UID 属于映射表中的其他账号时，会登出重切，最多 2 次。
- 重切仍失败会放弃本次登录，交由 AUTO-MAS 重试。

## 前置条件

- SRA 运行在 Windows（DPAPI 解密、窗口 OCR）。
- 客户端登录页需要已有**历史账号记录**（勾选过「保留登录记录」）。没有记录时，先手动登录一次目标账号。
- 面向本地客户端的登录页设计；云游戏（Browser Operator）场景未做专门适配。

## 排障

| 现象 | 处理 |
|---|---|
| 日志提示「下拉中未找到账号」 | 客户端没有该账号的登录记录，先手动登录一次并保留登录记录；或检查 `account_hint` 是否与登录页显示的脱敏格式一致。 |
| 日志提示「MAS 花名册中未找到当前用户」 | 检查 `scripts.yaml` / `ScriptConfig.json` 中该 uid 是否存在、`Info.Id` 是否可解密。 |
| 日志提示「UID 校验失败」 | 核对 `zz_uid_map.txt` 中目标账号对应的 UID；确认后修正或删除该行重新登录记录。 |
| 想看详细日志 | 在 SRA 根目录创建 `zz_debug.txt`，插件会输出 DEBUG 级别日志。 |
| 失败现场 | 截图保存在 `log/zz_error/`，文件名带失败阶段（如 `dropdown_missing`、`uid_mismatch`）。 |

## 相关文件

| 路径 | 作用 |
|---|---|
| `extensions/account_switch/__init__.py` | 配置模型、扩展声明与任务注册后钩子。 |
| `extensions/account_switch/plugin.py` | 切号实现：解析目标账号、登出、选号、UID 终验。 |
| `extensions/account_switch/locales/` | 扩展名称、字段说明的三语本地化。 |
| `zz_uid_map.txt` | 程序根目录，账号与游戏内 UID 的映射表，插件自动维护。 |
| `log/zz_error/` | 失败现场截图。 |
