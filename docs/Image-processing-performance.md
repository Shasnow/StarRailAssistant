# CPU 图像处理优化 / CPU image-processing performance

本改动只减少同一张图上的 Python 像素循环和模板匹配临时索引。
不修改 OCR 引擎、模型、灰度转换、裁剪、缩放、置信度或游戏流程。
来源讨论：[upstream #258](https://github.com/Shasnow/StarRailAssistant/discussions/258)。

## 等价性约束

- 装备卡框：相同 ROI、原分辨率和金色判据。通道先转为 `int16`，
  避免 `uint8` 差值回绕。按原逐行顺序分组，一到两个空像素仍连接，
  三个空像素仍断开。宽高、侧边覆盖率、分组顺序和坐标计算不变。
- 概率面板：原图每个 ROI 像素都参加同一个颜色判据；只将计数向量化。
  标题、表格、列颜色、关闭符号和同帧约束全部保留。
- 页面模板：使用原 Pyscreeze 转换、完整搜索图、`TM_CCOEFF_NORMED`
  和严格 `score > confidence`，只取逐行首个命中，而不是最高分位置。
  不缩小搜索范围、不跳过模板，也不增加跨帧缓存。
  原无 OpenCV 分支、停止检查、文件版本失效和失败处理仍由原调用方执行。
- `unicode_templates.py` 中只新增匹配辅助；Unicode 路径处理和 OCR 缓存未改动。

## 可复现验证

Python 3.12，安装项目原有的 `full` 和 `dev` 依赖；无需 GPU 包或新模型。
以下命令从仓库根目录执行。完整测试与可选 OCR 控制应使用新的临时配置目录，
不要使用正在运行的应用配置：

```powershell
$profile = Join-Path (Resolve-Path ..).Path ("ocr-check-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory $profile | Out-Null
$env:APPDATA = $profile
$env:LOCALAPPDATA = $profile
$env:TEMP = $profile
$env:TMP = $profile
$env:PYTHONUTF8 = "1"
python -m pytest tests/test_image_processing.py tests/test_template_matching.py -q
python -m pytest -q
python scripts/benchmark_image_processing.py --baseline-ref 89ee0347fdda48f37ea96c38d409aeb12afbe8e4 --check-only --output ../image-comparison.json
python scripts/benchmark_image_processing.py --baseline-ref 89ee0347fdda48f37ea96c38d409aeb12afbe8e4 --trials 7 --repeats 9 --ocr-control --output ../image-benchmark.json
```

脚本只读取本地 Git 中指定提交的原模块，不会 fetch 或改工作树。
输出文件必须尚不存在。省略 `--ocr-control` 可只运行图像处理；
`--only-baseline` 可单独测原实现。不要并行运行其他基准或构建。

对照包含 56 组装备图像/输入、53 组概率面板图像/输入：完整/空白/低对比度、
部分可见、边界、颜色临界值、1/2/3 像素间隙、损坏标题、灰度/RGB/RGBA/调色板等模式。
完整观测字段、所有卡框坐标、顺序、选择点、外观向量、拒绝原因和同帧预检逐项精确相等，
没有数值容差。模板测试与 Pyscreeze 1.0.1 比较首个/多个/等分候选、严格阈值、
四角、无命中、常量图、步幅、浮点数组及错误类型。

## 本地实测：2026-10-29

基线：`89ee0347fdda48f37ea96c38d409aeb12afbe8e4`。
Windows 10 Pro x64 19045，Ryzen 5 2600（6C/12T），16 GiB RAM；
Python 3.12.10、NumPy 2.5.4、Pillow 12.2.0、OpenCV 4.13.0.92、
Pyscreeze 1.0.1、RapidOCR 3.9.1、ONNX Runtime Python/native 1.27.0。
OpenCV 使用 12 个线程。OCR 控制确认三模型都仅使用 `CPUExecutionProvider`。

每个实现预热 3 次；7 轮交替 AB/BA，每轮每实现 9 次，报告每轮平均耗时的中位数。
OCR 控制为每轮 3 次、每次 6 个 RGB/灰度模板输入；同样预热 3 次。
分配输入、磁盘读取、模型初始化和内存跟踪不进入热调用计时。
图像基准是固定种子的合成 1920×1080 输入，模板大小 48×32。

| Operation | Baseline ms | Optimized ms | Speedup |
| --- | ---: | ---: | ---: |
| Equipment geometry, complete | 57.951 | 4.295 | 13.49× |
| Equipment geometry, no match | 55.993 | 4.022 | 13.92× |
| Probability panel, complete | 219.768 | 8.323 | 26.40× |
| Probability precheck, no match | 8.568 | 2.358 | 3.63× |
| Template matching, sparse | 51.513 | 47.319 | 1.09× |
| Template matching, no match | 52.327 | 47.819 | 1.09× |
| Template matching, dense | 39.487 | 31.055 | 1.27× |
| **Unchanged CPU OCR control, six inputs** | **2339.834** | **2333.599** | **≈1×; noise** |

最后一行两侧调用的是同一个未修改的 OCR 函数；不代表本 PR 加速了模型推理。
`tracemalloc` 在计时结束后单独测得单次临时峰值：

| Operation | Baseline MiB | Optimized MiB |
| --- | ---: | ---: |
| Equipment geometry, complete | 0.005 | 1.992 |
| Probability panel, complete | 38.477 | 4.811 |
| Template matching, sparse | 26.234 | 9.370 |
| Template matching, dense | 39.350 | 9.370 |

**卡框向量化用约 2 MiB 临时数组换取更少 CPU 循环。**
这些是 Python/NumPy 可跟踪分配，不是完整进程 RSS 或 OpenCV/Pillow 原生峰值。

## 检查结果与限制

- 当前干净基线：1345 passed；优化后：1401 passed（新增 56），无跳过或新增失败。
- 修改文件的 blocking flake8 为零；新增 Python 文件的完整 flake8 为零。
  全项目 blocking flake8 仍有原来的
  `extensions/cw_plus/population_vision.py:240`：`F821 undefined name 'tokens'`。
  非阻断的全项目风格/复杂度告警也未在此 PR 中全面修复。
- 补充离线检查：真实页面匹配调用方的缓存、停止、换帧、缺失文件及 Pillow 后备行为保持一致；
  真实 `IOperator.ocr` 的 36 组 CPU 调用文本、框、分数和阈值过滤结果精确相等。
- 没有启动游戏、访问账号或验证完整 CurrencyWarsPlus 对局；没有声称整局加速或准确率提高。
  未做 GUI/安装器、其他操作系统/CPU、长期运行或真实动画流覆盖。
- 复杂投影预筛、合帧 OCR、前台空槽识别、采购/布局/状态机改动不在本补丁中。
  没有 GPU/DirectML、依赖/打包、模型、素材、策略或本地化变更。
