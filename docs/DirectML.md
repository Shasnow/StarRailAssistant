# 可选 DirectML OCR / Optional DirectML OCR

DirectML is opt-in. The normal install, settings schema, models, OCR preprocessing,
thresholds, coordinates, and game logic are unchanged. This is independent of the
OCR image-processing, CurrencyWarsPlus, and localization contributions.

## Selection and fallback

`SRA_OCR_PROVIDER` is read once, when `OperatorFactory.get_ocr_instance()` first
creates its process-wide OCR engine:

| Value | Behavior |
| --- | --- |
| unset | Original RapidOCR initialization and configuration, unchanged |
| `cpu` | Explicit CPU; disables the configured ONNX GPU providers |
| `directml` | Try DirectML on compatible Windows x64; otherwise log a CPU fallback |

For DirectML, the existing RapidOCR pipeline first creates its normal CPU
sessions. Detection and recognition then receive independent ONNX Runtime
sessions with `DmlExecutionProvider` first and `CPUExecutionProvider` second.
Both GPU sessions must initialize and actually select DirectML before either is
installed into the pipeline. Otherwise **all original CPU sessions are kept**.

GPU sessions disable memory patterns and use `ORT_SEQUENTIAL`. A lock serializes
the entire OCR call, including RapidOCR's mutable per-call options. The factory
also serializes singleton construction.

If ONNX Runtime raises `EPFail`, `Fail`, or `RuntimeException` during inference,
the complete GPU pipeline is disabled and the **same OCR input and arguments**
are retried once on the retained CPU sessions. Subsequent calls stay on CPU until
process restart. Errors from the CPU retry are not hidden. Invalid input and arbitrary Python
exceptions do not trigger a GPU retry. Native crashes, a stuck driver, and process
termination cannot be recovered by a Python exception handler.

The CPU sessions retained for fallback cost additional host memory. Initialization
is also more expensive than CPU-only initialization. There is no promise that
GPU will be faster for every image shape, small ROI, or under simultaneous game
load.

## Models and scope

RapidOCR 3.9.1 defaults are preserved:

| Stage | Model | Explicit DirectML mode |
| --- | --- | --- |
| Detection | `PP-OCRv6_det_small.onnx` | DML, with CPU nodes allowed for unsupported operations |
| Classification | `ch_ppocr_mobile_v2.0_cls_mobile.onnx` (legacy classifier selected by the PP-OCRv4 configuration) | CPU only |
| Recognition | `PP-OCRv6_rec_small.onnx` | DML, with CPU nodes allowed for unsupported operations |

SRA's normal OCR call has `use_cls=False`. Classification is not claimed as GPU
accelerated; explicit classification calls still work on CPU. Image loading,
Pillow/OpenCV processing, detector postprocessing, decoding, screen capture,
template matching, input, and the game itself remain CPU/original operations.
Custom non-ONNX backends are not converted to DirectML.

`get_available_providers()` only reports runtime capabilities.
`engine.text_det.session.session.get_providers()` (and the equivalent `text_cls`
and `text_rec` paths) report each session's actual selection, **not proof of GPU
execution**. An ONNX Runtime profile must contain executed node events with
`args.provider == "DmlExecutionProvider"` for detection and recognition. Mixed
CPU/DML graph execution is expected. The benchmark's separate `--profile` audit
records these events for all three models.

## Dependencies and ABI

| Variant | Python package | Native ONNX Runtime | DirectML DLL |
| --- | --- | --- | --- |
| Default upstream install | `onnxruntime==1.27.0` | 1.27.0 | none required |
| Optional build input | complete `onnxruntime-directml==1.24.4` official wheel | 1.24.4 | 1.15.4 |

Both use RapidOCR 3.9.1 and CPython **3.12 x64**. DirectML additionally needs Windows
10 1903/build 18362 or newer and a functioning DirectX 12-capable hardware adapter
and driver. The default adapter is device 0; multi-adapter selection is not added.
The pinned ORT provider's factory rejects software adapters; the software-device
check is not bypassed. A provider initialization failure is treated as CPU fallback.
Windows ARM64, 32-bit Python, CUDA, and non-Windows GPU support are outside scope.

The existing fork's compiled Python package 1.27.0 / native 1.24.4 combination is
**not** called a uniform 1.27.0 runtime and is **not** reproduced here. The optional
build uses the Python files, pybind extension, ONNX DLLs, and DirectML DLL from one
complete, checksum-pinned official wheel, before compilation. Runtime selection
also refuses GPU when `onnxruntime.__version__ != onnxruntime.get_version_string()`.

Do not install `onnxruntime` and `onnxruntime-directml` into the same site-packages:
they own the same import namespace and files. Do not replace only DLLs or copy
compiled 1.27 Python modules over the 1.24.4 package. CPU fallback in an optional
build uses the CPU provider **inside native 1.24.4**, not a second in-process 1.27
runtime.

## Reproducible local preparation

Keep the ordinary Python 3.12 development environment (`pip install ".[full]"`).
Prepare a separate build-input directory, without installing or changing any
existing packages:

```powershell
python scripts/prepare_directml.py --download --output ../ocr-directml
# Or reuse exactly the same official wheel, with no download:
python scripts/prepare_directml.py --wheel C:/cache/onnxruntime_directml-1.24.4-cp312-cp312-win_amd64.whl --output ../ocr-directml
```

The URL is fixed to PyPI's official wheel. SHA256 is
`f2ecb68b7b7b259d2ef3112ae760149f9b5a1e7c0fbb73d539da6250a648a614`.
The tool rejects a mismatch, checks ZIP CRC and paths, refuses existing output,
extracts the **whole** wheel, retains ONNX license/notices and adds the versioned
DirectML license. `directml-runtime.json` records origins, component versions and
per-file SHA256. No binaries or wheel are committed to this repository.

For a source run, set only the current PowerShell process environment (not system
PATH, registry, or Windows settings), **before** importing ONNX Runtime:

```powershell
$env:PYTHONPATH = (Resolve-Path ../ocr-directml).Path
$env:SRA_OCR_PROVIDER = 'directml'
python main.py --no-admin
```

An already-running GUI/backend must be completely restarted to inherit these
values. To force CPU, set `SRA_OCR_PROVIDER=cpu` and restart. To return to the
ordinary source environment, remove the process-local `PYTHONPATH` override and
restart Python. There are no automatic downloads or driver installations at app
startup for this GPU runtime. Models use the original RapidOCR loading/packaging path; prepare them
as for the existing CPU build.

## Windows packaging

Compile **from** the complete prepared runtime by giving the build process the
same process-local `PYTHONPATH` above. Do not retrofit the wheel onto an already
compiled CPU executable. The existing `scripts/package.py` resource-copy stage
detects the optional runtime, verifies matching Python/native 1.24.4 and the
four official native-file SHA256 values, refuses conflicting output DLLs, then
copies `onnxruntime/capi/{DirectML.dll,onnxruntime.dll,
onnxruntime_providers_shared.dll,onnxruntime_pybind11_state.pyd}` together with the
license material and component manifest. When Nuitka's native dependency scan has
already placed `directml.dll` in the application root, that verified copy is used
instead of making a duplicate in `capi`. The manifest records the actual location.
This also covers builds where Nuitka does not include the DirectML DLL automatically.

Default CPU packaging does not add DirectML files. The Lite/source package still
installs the original CPU dependency by default. The optional native libraries
stay application-local; neither DLL-search PATH nor global library locations are
changed. Move the complete application folder, not a single DLL.

The existing release workflows can publish releases and external uploads. **Do
not run them just to validate this feature.** No workflow/publication changes are
part of this contribution.

### Licenses and release decision

- SRA remains AGPL-3.0-or-later. RapidOCR and the unchanged Paddle OCR models are
  Apache-2.0 components; their original provenance is not replaced by this PR.
- ONNX Runtime is MIT, with its original `LICENSE` and `ThirdPartyNotices.txt`.
- **DirectML.dll is not MIT.** Version 1.15.4 is covered by Microsoft's
  [DirectML terms](https://www.nuget.org/packages/Microsoft.AI.DirectML/1.15.4/License),
  reproduced in [licenses/DirectML-1.15.4.txt](licenses/DirectML-1.15.4.txt).
  Those terms restrict use to Windows/Xbox, restrict reverse engineering, and
  permit redistribution in qualifying applications, not as a stand-alone offering.
- The prepared runtime is a **local build input**, not a stand-alone SRA release
  asset. No DirectML binary is newly distributed by this source-only contribution.
- The maintainer must explicitly review whether/how to redistribute a proprietary
  DirectML component with the AGPL application, including any applicable system-
  library exception. This document does **not** declare that legal question
  resolved. CPU releases remain available without that component.

DirectML is in sustained engineering according to Microsoft's current provider
documentation; new Windows AI feature development has moved to WinML. This is an
additional maintenance consideration, not a reason to silently change SRA's
runtime to WinML.

## Reproduce the checks

Tests never launch HSR or send game input. Optional model tests skip when the
unchanged model files are not already present; they do not download models.

```powershell
python -m pytest -q tests/test_ocr_directml.py tests/test_directml_payload.py
# To include the real payload/missing-DLL subprocess tests:
$env:SRA_DIRECTML_WHEEL = 'C:/cache/onnxruntime_directml-1.24.4-cp312-cp312-win_amd64.whl'
python -m pytest -q tests/test_ocr_directml.py tests/test_directml_payload.py
```

Use separate new output directories. Do not run latency measurements concurrently
with builds or other OCR benchmarks:

```powershell
# Use a fresh shell without the earlier PYTHONPATH override for the original CPU baseline:
python scripts/benchmark_ocr.py --provider cpu --output ../bench-cpu127
# Matched-runtime CPU and DML comparison; --runtime changes only this process:
python scripts/benchmark_ocr.py --provider cpu --runtime ../ocr-directml --output ../bench-cpu124
python scripts/benchmark_ocr.py --provider directml --runtime ../ocr-directml --output ../bench-dml124
# Separate instrumented provider audit, NOT a latency comparison:
python scripts/benchmark_ocr.py --provider directml --runtime ../ocr-directml --profile --repeats 1 --stress-calls 0 --output ../provider-audit
python scripts/compare_ocr_benchmarks.py --cpu ../bench-cpu127/result.json --directml ../bench-dml124/result.json --audit ../provider-audit/result.json --output ../comparison.json
```

Each result records component/model/font/pixel hashes, selected providers, import
and session initialization cost, first encounters with each input, five warmed
calls, and 100 additional calls with process memory/handle samples. The first
input measures the first OCR call in that process; later `first_seconds` values
mean the first encounter with that case, not fresh application startups. RSS is
**host** memory, not GPU memory. `--profile` additionally includes a CPU-classifier
call and executed-node counts for every created session.

The generated corpus contains digits, Chinese names/buttons, multiline/wide and
grayscale images, recognition-only input, low contrast, blank and deterministic
noise controls. CJK cases use the existing Windows Microsoft YaHei font when
available; its SHA256 is recorded. No fonts, images, or models are downloaded.
This corpus is a reproducible provider comparison, **not** a game-accuracy study.
If Microsoft YaHei is absent, the synthetic Chinese cases are explicitly omitted.
For a font-independent Chinese comparison, repeat the commands with
`--corpus templates`: this uses six unchanged upstream text-only templates and
their grayscale versions, with manually transcribed expected labels. It does
not transfer gameplay changes or private screenshots into this contribution.

Compare identical pixel hashes. Acceptance criteria are equal normalized Unicode
text/token counts, no additional or missing tokens, matched boxes with IoU >=0.95
and corner displacement <=2 pixels (or 0.5% of the longer image side), confidence
delta <=0.005 and unchanged decisions at 0.5/0.7/0.9. Numerical tensors need not
be bit-identical. Report ground-truth misses/false positives separately from CPU
vs DML equivalence; equal errors are not evidence of correctness.

Hardware, measured results, test status, and remaining limitations are recorded
in [DirectML-validation.md](DirectML-validation.md).

## Official references

- [ONNX Runtime DirectML requirements/options](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html)
- [Pinned provider factory, including software-device rejection](https://github.com/microsoft/onnxruntime/blob/v1.24.4/onnxruntime/core/providers/dml/dml_provider_factory.cc)
- [Official DirectML wheel metadata](https://pypi.org/pypi/onnxruntime-directml/1.24.4/json)
- [Original CPU wheel metadata](https://pypi.org/pypi/onnxruntime/1.27.0/json)
- [RapidOCR 3.9.1 metadata](https://pypi.org/pypi/rapidocr/3.9.1/json)
