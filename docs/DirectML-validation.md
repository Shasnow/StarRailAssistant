# DirectML OCR validation — 2026-10-29

**Status: validated local draft, not an approved upstream release.** No push, PR,
release, CI publication workflow, game launch, or game/account interaction was
performed. Redistribution policy still needs the maintainer's explicit review.

Base: upstream `main` at `863509072bf2011b4d5a3e3d71072b6cd269637e`.
The implementation is independent of the localization, CurrencyWarsPlus, and
OCR image-processing contributions. No model, threshold, strategy, or game file
is changed.

## Hardware and components

- Windows 10 Pro x64, build 19045; Ryzen 5 2600, 6 cores / 12 threads; 16 GB RAM.
- AMD Radeon RX 590, driver `31.0.23013.14001`.
- Read-only DXGI enumeration identifies adapter **0** as the RX 590, vendor
  `0x1002`, flags `0` (not software), LUID `0x00000000:0x0000B45E`, approximately
  8 GB dedicated memory. Adapter 1 is the software Microsoft Basic Render Driver;
  it is **not** the selected device.
- CPython 3.12.10 x64; RapidOCR 3.9.1; NumPy 2.5.4; Pillow 12.2.0.
- Default CPU: Python ONNX Runtime **1.27.0**, native **1.27.0**.
- Optional runtime: complete official `onnxruntime-directml` **1.24.4** wheel,
  Python **1.24.4**, native **1.24.4**, DirectML DLL **1.15.4**.
- Standalone backend built with Nuitka 4.3.1 / cached GCC 15.2.0. No compiler,
  driver, global Python package, service, or system PATH change was needed.

Wheel SHA256 and preparation instructions are in [DirectML.md](DirectML.md).
The older fork's compiled Python 1.27.0 / native 1.24.4 combination is **not**
reproduced, relabeled as one version, or assumed ABI-compatible here.

Unchanged model SHA256 values:

| Stage | SHA256 |
| --- | --- |
| `PP-OCRv6_det_small.onnx` | `090f04abcd9d9a7498bc4ebf677e4cb9bdce1fe4197ddb7e529f1ef44e1ff94f` |
| `ch_ppocr_mobile_v2.0_cls_mobile.onnx` | `e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c` |
| `PP-OCRv6_rec_small.onnx` | `6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884` |

## Available, selected, and executed providers

The original 1.27.0 CPU package advertises `AzureExecutionProvider` and
`CPUExecutionProvider`. RapidOCR selects **CPU only** for all three models.
The optional 1.24.4 package advertises DML and CPU. Explicit DirectML mode selects:

| Model | Session provider priority | Actually executed in the separate Chinese-template profile |
| --- | --- | --- |
| Detection | DML, CPU | 5,809 DML node events |
| Classification | CPU | 229 CPU node events in an explicit classification call |
| Recognition | DML, CPU | 6,290 DML and 74 CPU node events |

These are **event counts over repeated calls**, not a percentage of GPU work or
FLOPs. The retained standby CPU detector/recognizer sessions had no execution
events in normal DirectML mode. CPU nodes in the active recognition graph are
expected. SRA normally passes `use_cls=False`.

A separate fixed-ROI worker also increased the **same PID's** RX 590 3D-engine
running-time counter from 1,360,579 to 45,404,021 ticks across 100 OCR calls. Its
counter instance's adapter LUID matches hardware adapter 0 above. Together with
ORT's executed-node profiles, this is evidence of physical GPU execution, not
merely an installed DLL, a provider capability list, or a Task Manager label.

The official 1.24.4 `dml_provider_factory.cc` explicitly rejects software devices
when `device_id` is supplied; the Python path does not bypass this check. An
additional native check redirected only the external ORT constructor to the
enumerated software adapter 1: initialization failed, all three model sessions
remained CPU, and three actual CPU OCR calls succeeded. On this localized Windows
installation ORT's low-level error text included a UTF-8 decoding error; SRA still
clearly reported CPU fallback. Native diagnostic wording is a maintenance limit,
not a Unicode/localization change included in this feature.

## Benchmarks

Source-Python OCR pipeline measurements, not a whole-game or compiled-executable
speed claim. Separate fresh processes, no concurrent build or other test OCR
workload. Background desktop activity was not controlled as in a laboratory.
First encounters are not disk-cache-cold Windows boots. Instrumented profiles
are excluded from latency comparisons.

### Generated corpus: 10 images, three rotated-order trials

Digits, grayscale/dark/wide/multiline variants, recognition-only input, low
contrast, blank and seeded noise. Microsoft YaHei was absent on this machine,
so optional generated Chinese cases were **not** included in these ten images.
Chinese testing was performed separately on the unchanged templates below.

For each process: first encounters, one warmup per image, five timed calls per
image, then 100 additional calls. Variant order was rotated between three trials.

| Metric | CPU 1.27.0 | CPU 1.24.4 | DML 1.24.4 |
| --- | ---: | ---: | ---: |
| Median session initialization | 0.471 s | 0.392 s | 0.795 s |
| Median first OCR call, after initialization | 0.685 s | 0.676 s | 0.435 s |
| Median initialization + first OCR call, excludes imports | 1.168 s | 1.089 s | 1.228 s |
| Median sum of first encounters with all ten images | 6.928 s | 7.046 s | 3.347 s |
| Median sum of per-image warm medians | **6.014 s** | **6.313 s** | **3.069 s** |
| Median warmed host RSS | 145.3 MiB | 145.8 MiB | 316.3 MiB |
| Median host RSS after 100 extra calls | 145.3 MiB | 146.2 MiB | 316.5 MiB |

Raw warm sums across the three trials:

- CPU 1.27.0: `5.9908475`, `6.0139048`, `6.0206531` seconds.
- CPU 1.24.4: `6.3288325`, `6.3132345`, `5.9294882` seconds.
- DML 1.24.4: `3.0694912`, `3.0612619`, `3.1067716` seconds.

This is **1.96x** versus the original CPU package, **2.06x** versus CPU in the
matched runtime. It is **not** acceleration of the complete application/game.
Initialization is slower and the first initialization-plus-OCR transaction is
slower than CPU here. Recognition-only warm calls improve only approximately
`21.7 -> 14.8 ms`; such a small absolute saving may not justify GPU setup/memory
for an occasional OCR call. No warm synthetic case was slower in this cycle;
that is not a guarantee for other inputs or simultaneous game load.

### Chinese source templates: 12 images, one trial per variant

Six existing upstream text-only images and their grayscale versions, including
`next_step`, `next_page`, `withdraw_and_settle`, `confirm_selection`, `start_game`,
and `preparation_stage`. No image, model, strategy, or CurrencyWarsPlus change is
made. Five warmed calls per image; this smaller single-trial comparison is less
robust than the rotated three-trial measurement.

| Variant | Sum of per-image warm medians |
| --- | ---: |
| Original CPU 1.27.0 | 6.651 s |
| Matched CPU 1.24.4 | 6.786 s |
| DirectML 1.24.4 | 3.698 s |

Approximately **1.80x** versus original CPU / **1.84x** versus matched CPU.

### OCR equivalence and existing errors

Compared identical input pixel/model hashes. Criteria: same normalized Unicode
tokens and counts; no extra/missing tokens versus CPU; box IoU >=0.95 and corner
movement <=2 pixels or 0.5% of the long side; confidence delta <=0.005; unchanged
decisions at 0.5/0.7/0.9. No bitwise tensor identity is required.

- All 22 input cases passed CPU-versus-DML equivalence. Coordinates were identical
  in the captured comparisons; maximum Chinese confidence difference was 0.00001.
- All captured Chinese warm repeats passed the same criteria. A separate
  50-call captured-repeat check of the generated corpus also passed. The earlier
  throughput trials recorded first results plus a bitwise-repeat flag, not every
  warm output; bitwise-repeat identity was not universal and is not an acceptance
  requirement.
- The low-contrast numeric image was missed by **both** CPU and DML. Blank/noise
  controls produced no extra text. This is not a claim of perfect accuracy.
- Four Chinese cases (RGB/gray `next_step` and `next_page`) retain an existing
  CPU error: `下一步` becomes tokens `下一`, `一步`, and `下一页` becomes `下一`,
  `一页`. Thus even joined text duplicates `一`. Exact joined rendered text is
  correct for **8/12** Chinese inputs, equally for CPU and DML. A one-label-per-box
  oracle reports four missing labels/eight extra tokens for both providers; these
  are not new GPU regressions. No CPU recognition fix is mixed into this PR.

## Memory, resource release, and bounded stability

- Three synthetic trials per variant each included 100 extra calls: **300 stress
  calls per variant**, in addition to first/warm calls. No hangs or native crashes
  occurred in the final implementation. Host RSS and handles plateaued over the
  sampled calls; this is a bounded observation, not proof of unlimited leak-free
  operation.
- A separate 256x64 fixed-image DML worker, after warmup and after 100 more calls,
  had unchanged per-PID dedicated GPU usage **723.1 MiB** and shared GPU usage
  **48.4 MiB**. These are Windows GPU counters, **not RSS**, and not peak memory
  for the multi-shape corpus.
- After deleting the disposable factory/engine and collecting garbage, these
  counters dropped to **7.3 MiB dedicated / 2.6 MiB shared**. After clean process
  exit (code 0), its GPU memory/engine counter instances disappeared.
- Native/driver caches mean host RSS does not immediately return to the CPU-only
  baseline when an engine object is released. GPU initialization, retained CPU
  fallback sessions, dynamic shapes and native heaps have a real memory cost.
- A rejected experimental **per-model** fallback reproduced a native access
  violation when another GPU model was used after one session was discarded.
  It is not shipped. The final implementation abandons the **entire** GPU
  pipeline, retries the input on retained CPU sessions, and remains on CPU.
  The vendor/driver root cause is not declared fixed.

## Test results and Windows standalone checks

Public test boundaries: `OperatorFactory.get_ocr_instance()` and ordinary OCR
calls, isolated CLI startup, and local runtime preparation/packaging. No private
project helper is tested directly and no fake OCR results substitute for native
inference. Provider/adapter/run faults are injected at the external ORT boundary.

| Check | Result |
| --- | --- |
| New integration tests, default CPU environment + local wheel | 8 passed, 5 GPU-only skipped |
| New integration tests, optional DML runtime + local wheel | **13 passed** |
| Full upstream suite before implementation | 7 passed, 3 failed |
| Full final CPU suite | 15 passed, 5 skipped, **same 3 existing failures** |
| Full final DML suite | 20 passed, **same 3 existing failures** |
| Blocking flake8 on changed Python files | 0 errors |
| Full blocking flake8 | Existing `F821` at `extensions/cw_plus/population_vision.py:240` |

The three existing failures are:

- `test_main_version_option_exits_cleanly` (obsolete patch target).
- `test_channel_test_notification_catches_channel_exception` (obsolete patch target).
- `test_load_all_tasks_and_trigger_start_complete_notifications` (task-registration assumption).

They are documented by upstream `AGENTS.md` and were reproduced before changes.
The lint-error file and all three old tests are unchanged. **Full tests/CI are not
reported green.** Release workflows were not run because they can publish/upload.

The actual standalone `SRA-cli.exe` was built from the full coherent 1.24.4
runtime, using the existing packaging resource-copy integration. A disposable
offline task imported by the real CLI exercised the public OCR factory; it was
removed afterwards. Six separate process checks passed:

1. Forced CPU, five real OCR calls.
2. DML, five real OCR calls, executed DML nodes for both accelerated models.
3. Application DirectML DLL absent, startup and five CPU OCR calls still work.
4. Injected adapter initialization failure, CPU OCR still works.
5. Injected native execution failure, full-pipeline CPU fallback and later calls.
6. Entire folder relocated; DML still works with **Windows-only PATH**, without
   `PYTHONPATH`, `PYTHONHOME`, or a virtual environment.

The compiled Python package and native runtime both report **1.24.4**; the Python
module is compiled, not loaded from the source environment. DLL loader paths were
checked with `GetModuleFileNameW` and point into the application in normal and
relocated cases. With its DLL missing, Windows can load its older system DirectML
DLL; the actual OCR sessions still fall back to CPU. No system DLL was installed.
Nuitka's root `directml.dll` is verified and retained without an unnecessary
second copy in `onnxruntime/capi`.

Compiled startup uses the ordinary inline REPL with `exit` on stdin. The unchanged
upstream Nuitka command's self-execution guard rejects compiled `-c exit`; that
separate packaging/CLI issue is recorded, not silently fixed in this OCR PR.

## Limits and release blockers

1. **Maintainer decision required:** DirectML.dll has proprietary Microsoft terms,
   not ONNX Runtime's MIT license. Those terms and ONNX notices are retained;
   whether/how to distribute it with AGPL SRA needs explicit licensing/release
   policy review. No legal compatibility conclusion is invented.
2. Existing full-test and lint failures remain outside this feature's scope.
3. Only this Windows x64 / AMD adapter/driver combination is GPU-tested. Physical
   GPU absence was not tested by removing hardware; CPU-only runtime, missing DLL,
   real software-device rejection and fault injection were tested. Software-device
   acceleration is not supported. Multi-GPU selection,
   other vendors, Windows ARM, and arbitrary driver failures are not qualified.
4. No live HSR/account test, game concurrency benchmark, hours-long soak, desktop
   GUI startup/restart, .NET rebuild, installer, or release workflow validation.
   Source and standalone **backend CLI** startup were exercised.
5. RapidOCR integration uses the pinned 3.9.1 model/session attributes. Upgrading
   RapidOCR, ORT, native DLLs, model opsets or packaging requires repeating these
   tests/profiles, refreshing checksums and checking licenses.
6. DirectML is in sustained engineering; future Windows GPU support may require
   a separate WinML proposal. No such migration is bundled here.

Reproduction commands and acceptance criteria: [DirectML.md](DirectML.md).
The local preparation retains raw JSON, profiles, logs and the English PR draft
outside the Git diff; no private screenshots or existing releases are included.
