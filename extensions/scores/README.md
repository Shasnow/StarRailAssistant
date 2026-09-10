# SRA 乐谱格式规范（sra-score v1）

SRA 自动演奏扩展（`extensions/auto_player.py`）使用的 JSON 乐谱格式。
乐谱文件可放在 `extensions/scores/` 目录下（推荐），或使用任意路径引用。

## 1. 完整结构示例

```json
{
  "format": "sra-score",
  "version": 1,
  "meta": {
    "title": "节奏练习曲",
    "bpm": 108,
    "beat": "4/4",
    "transpose": 0
  },
  "notes": [
    { "pitch": "C4", "duration": 1.0 },
    { "pitch": "C4", "duration": 0.5 },
    { "pitch": "rest", "duration": 0.5 },
    { "pitch": ["C4", "E4", "G4"], "duration": 2.0 }
  ]
}
```

## 2. 字段说明

### 顶层字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `format` | string | 是 | 固定为 `"sra-score"` |
| `version` | int | 是 | 当前规范版本，固定为 `1` |
| `meta` | object | 否 | 乐谱元信息，见下表 |
| `notes` | array | 是 | 音符序列，至少 1 个元素 |

### meta 字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `title` | string | 否 | `"未命名"` | 乐谱标题，用于日志展示 |
| `bpm` | number | 否 | `100` | 速度（每分钟拍数），允许 20–300 |
| `beat` | string | 否 | `"4/4"` | 拍号（如 `"3/4"`），仅作展示，不影响演奏 |
| `transpose` | int | 否 | `0` | 整体移调八度数（-2 ~ 2），如 `1` 表示全曲升八度 |

### 音符字段（notes[]）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pitch` | string / array / null | 否 | `null` | 音名或音名数组（和弦）；`null` 或 `"rest"` 表示休止符 |
| `duration` | number | 否 | `1.0` | 时值，单位为拍（四分音符 = 1 拍）；必须为正数，支持小数（`0.5` 八分音符、`1.5` 附点四分） |

游戏按键为瞬时敲击触发，无长按延音设定，因此乐谱不含演奏效果标记。

## 3. 音名与按键映射

音名采用科学音高记号（音名字母 + 八度数字），仅支持 C3~B5 范围内的
自然音（游戏键盘无黑键，不支持升/降号）。音名字母不区分大小写。

| 八度 | 音名 | 游戏按键 |
| --- | --- | --- |
| 高八度 | C5 D5 E5 F5 G5 A5 B5 | `Q` `W` `E` `R` `T` `Y` `U` |
| 基本音 | C4 D4 E4 F4 G4 A4 B4 | `A` `S` `D` `F` `G` `H` `J` |
| 低八度 | C3 D3 E3 F3 G3 A3 B3 | `Z` `X` `C` `V` `B` `N` `M` |

和弦（音名数组）通过组合键方式近似同时触发（如 `a+s+d`）。

## 4. 播放控制与速度

- **开始**：`sra> extension run AutoPlayer`（首次开始前有 `start_delay` 秒延迟，用于切换到游戏窗口）。
- **暂停/继续**：默认热键 `F8`（配置项 `hotkey_pause`）。
- **重置**：默认热键 `F10`（配置项 `hotkey_reset`），回到乐谱开头重新演奏。
- **停止**：SRA 全局停止热键（默认 `F9`）。
- **速度调节**：配置项 `speed`（0.25 ~ 4.0）为全局倍率，实际 BPM = 乐谱 `bpm` × `speed`。
- **循环**：配置项 `loop`（1 ~ 99）控制演奏遍数。

配置示例（`AppData` 下 `extensions.json`）：

```json
{
  "AutoPlayer": {
    "score": "twinkle_star",
    "speed": 1.0,
    "loop": 1,
    "start_delay": 2.0,
    "dry_run": false,
    "enable_hotkeys": true,
    "hotkey_pause": "f8",
    "hotkey_reset": "f10"
  }
}
```

热键不要设置为演奏按键（QWERTYU / ASDFGHJ / ZXCVBNM），否则演奏音符会同时触发播放控制。

## 5. 时序精度设计

引擎采用**绝对时间锚点调度**：每个音符的目标时刻 = 锚点 + 音符偏移，
独立等待、互不累积，单个音符的执行耗时不会造成节奏漂移。配合：

1. Windows 下 `timeBeginPeriod(1)` 将定时器精度提升到 1ms；
2. 粗等待阶段使用可中断休眠（可被停止热键立即打断）；
3. 最后约 4ms 自旋等待；

音符触发误差通常在 5ms 以内，满足 ≤50ms 的设计目标。演奏结束时日志会
输出本次平均/最大时序误差，可用于验证（`dry_run: true` 演练模式不实际按键，
仅输出时序，适合测试乐谱与速度）。

## 6. 校验规则摘要

解析失败会抛出明确错误（含音符序号定位）：

- `format`/`version` 不正确；`notes` 非数组或为空；
- `bpm` 不是 20–300 的数值；`transpose` 不是 -2~2 的整数；
- 音名不在 C3~B5 范围或含升降号；`duration` ≤ 0；
- 音符移调后超出 C3~B5 范围。

音符对象中的未知字段（如已废弃的 `effect`）会被忽略。

## 7. 示例乐谱

| 文件 | 曲目 | 节奏特点 |
| --- | --- | --- |
| `twinkle_star.json` | 小星星 | 4/4，四分音符为主，简单节奏 |
| `ode_to_joy.json` | 欢乐颂 | 4/4，附点节奏（附点四分 + 八分），含低八度音 |
| `happy_birthday.json` | 生日快乐 | 3/4 拍，弱起小节，八分音符节奏 |
| `etude_effects.json` | 节奏练习曲 | 上下行音阶、休止符、和弦、八分/十六分混合节奏 |
