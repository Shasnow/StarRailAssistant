"""离线 OCR 测量；只使用生成的图像，不截屏、不启动游戏、不发送输入。"""
from __future__ import annotations

import argparse
from collections import Counter
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def corpus():
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    cases = []
    font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/msyh.ttc"
    font_info = {"latin": "Pillow load_default", "cjk_sha256": None}
    if font_path.is_file():
        font_info["cjk_sha256"] = hashlib.sha256(font_path.read_bytes()).hexdigest()

    def add(name, size, lines, *, cjk=False, font_size=28, foreground="black", background="white", gray=False, det=True):
        image = Image.new("RGB", size, background)
        font = ImageFont.truetype(str(font_path), font_size) if cjk else ImageFont.load_default(size=font_size)
        draw = ImageDraw.Draw(image)
        for i, text in enumerate(lines):
            draw.text((8, 4 + i * (font_size + 12)), text, font=font, fill=foreground)
        if gray:
            image = image.convert("L")
        cases.append((name, image, {"use_det": det, "use_cls": False, "use_rec": True}, lines))

    add("digits-small", (96, 36), ["12"], font_size=22)
    add("digits", (256, 64), ["12345"], font_size=36)
    add("digits-gray", (256, 64), ["12345"], font_size=36, gray=True)
    add("digits-dark", (256, 64), ["100"], font_size=36, foreground="white", background="black")
    add("wide", (1024, 64), ["1234567890 1234567890 1234567890"], font_size=36)
    add("multiline", (640, 200), ["12345", "67890", "100"], font_size=36)
    add("low-contrast", (256, 64), ["12345"], font_size=36, foreground=(145, 145, 145), background=(160, 160, 160))
    add("recognition-only", (192, 48), ["12345"], font_size=30, det=False)
    add("blank", (192, 48), [])
    if font_path.is_file():
        add("cjk-name", (160, 64), ["姬子"], cjk=True, font_size=32)
        add("cjk-button", (192, 64), ["下一步"], cjk=True, font_size=32)
        add("cjk-gray", (192, 64), ["下一步"], cjk=True, font_size=32, gray=True)
        add("cjk-multiline", (640, 200), ["星穹铁道", "奖励 100", "下一步"], cjk=True, font_size=32)
    noise = Image.fromarray(np.random.default_rng(258).integers(0, 256, (64, 192, 3), dtype=np.uint8))
    cases.append(("noise", noise, {"use_det": True, "use_cls": False, "use_rec": True}, []))
    return cases, font_info


def output_record(output):
    return {
        "texts": list(output.txts) if output.txts is not None else [],
        "scores": [float(score) for score in output.scores] if output.scores is not None else [],
        "boxes": output.boxes.tolist() if getattr(output, "boxes", None) is not None else None,
    }


def template_corpus():
    from PIL import Image

    cases = []
    labels = {"next_step": "下一步", "next_page": "下一页", "withdraw_and_settle": "放弃并结算",
              "confirm_selection": "确认选择", "start_game": "开始对局", "preparation_stage": "备战阶段"}
    for stem, text in labels.items():
        path = ROOT / "resources/img/currency_wars" / (stem + ".png")
        with Image.open(path) as source:
            image = source.convert("RGB")
        for suffix, frame in (("rgb", image), ("gray", image.convert("L"))):
            cases.append((stem + "-" + suffix, frame, {"use_det": True, "use_cls": False, "use_rec": True}, [text]))
    return cases, {"source": "unchanged upstream text templates; no system font needed"}


def run(args):
    if args.output.exists():
        raise FileExistsError("--output must not exist")
    args.output.mkdir(parents=True)
    sys.path.insert(0, str(ROOT))
    if args.runtime:
        sys.path.insert(0, str(args.runtime.resolve()))
    os.environ["SRA_OCR_PROVIDER"] = args.provider
    started = time.perf_counter()
    import onnxruntime as ort
    import psutil
    from SRACore.operators.factory import OperatorFactory

    import_seconds = time.perf_counter() - started
    sessions = []
    if args.profile:
        original = ort.InferenceSession

        def profiled(path, sess_options=None, **kwargs):
            options = sess_options or ort.SessionOptions()
            options.enable_profiling = True
            options.profile_file_prefix = str(args.output.resolve() / (Path(path).stem + "-" + str(len(sessions))))
            session = original(path, sess_options=options, **kwargs)
            sessions.append((Path(path).name, session))
            return session

        ort.InferenceSession = profiled
        import rapidocr.inference_engine.onnxruntime.main as rapid_ort
        rapid_ort.InferenceSession = profiled

    class BenchFactory(OperatorFactory):
        pass

    process = psutil.Process()

    def memory():
        info = process.memory_info()
        return {key: getattr(info, key) for key in ("rss", "peak_wset", "private") if hasattr(info, key)} | {
            "handles": process.num_handles() if sys.platform == "win32" else None}

    report = {"provider_requested": args.provider, "python": sys.version, "platform": platform.platform(),
              "processor": platform.processor(), "hardware_label": args.hardware_label,
              "ram_bytes": psutil.virtual_memory().total, "onnxruntime_python": ort.__version__,
              "onnxruntime_native": ort.get_version_string(), "onnxruntime_module": str(ort.__file__),
              "rapidocr": importlib.metadata.version("rapidocr"), "numpy": importlib.metadata.version("numpy"),
              "pillow": importlib.metadata.version("pillow"), "available_providers": ort.get_available_providers(),
              "import_seconds": import_seconds, "profiled": args.profile, "memory_before": memory(),
              "dedicated_gpu_memory": "Not measured; process RSS is not VRAM"}
    started = time.perf_counter()
    engine = BenchFactory.get_ocr_instance()
    report["initialization_seconds"] = time.perf_counter() - started
    report["memory_after_initialization"] = memory()
    models = {name: model.session.session for name, model in
              (("det", engine.text_det), ("cls", engine.text_cls), ("rec", engine.text_rec))}
    report["selected_providers"] = {name: session.get_providers() for name, session in models.items()}
    report["models"] = {name: {"file": Path(session._model_path).name,
                               "sha256": hashlib.sha256(Path(session._model_path).read_bytes()).hexdigest(),
                               "inputs": [{"name": v.name, "shape": v.shape, "type": v.type} for v in session.get_inputs()]}
                        for name, session in models.items()}
    cases, report["fonts"] = template_corpus() if args.corpus == "templates" else corpus()
    report["corpus"] = args.corpus
    records = {}
    for name, image, kwargs, expected in cases:
        started = time.perf_counter()
        output = engine(image, **kwargs)
        records[name] = {"size": list(image.size), "mode": image.mode, "pixel_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
                         "expected_lines": expected, "first_seconds": time.perf_counter() - started,
                         "first_output": output_record(output), "warm_seconds": [], "warm_outputs": [], "stable_outputs": True}
    # 每种形状单独预热一次；first_seconds 保留该进程内第一次遇到该输入的成本。
    for _name, image, kwargs, _expected in cases:
        engine(image, **kwargs)
    for repeat in range(args.repeats):
        order = cases if repeat % 2 == 0 else list(reversed(cases))
        for name, image, kwargs, _expected in order:
            started = time.perf_counter()
            output = engine(image, **kwargs)
            record = records[name]
            record["warm_seconds"].append(time.perf_counter() - started)
            current = output_record(output)
            record["warm_outputs"].append(current)
            record["stable_outputs"] &= current == record["first_output"]
    report["memory_after_warmup"] = memory()
    report["stress_memory_samples"] = []
    for index in range(args.stress_calls):
        _name, image, kwargs, _expected = cases[index % len(cases)]
        engine(image, **kwargs)
        if index % 25 == 0:
            report["stress_memory_samples"].append({"call": index + 1, **memory()})
    report["memory_after_stress"] = memory()
    report["stress_calls"] = args.stress_calls
    report["selected_providers_after"] = {
        name: model.session.session.get_providers() for name, model in
        (("det", engine.text_det), ("cls", engine.text_cls), ("rec", engine.text_rec))}
    if args.profile:
        # Явно вызываем также CPU-классификатор; это отдельная, нештатная для SRA проверка модели.
        engine(cases[1][1], use_det=True, use_cls=True, use_rec=True)
        report["profiles"] = []
        for name, session in sessions:
            path = Path(session.end_profiling())
            events = json.loads(path.read_text(encoding="utf-8"))
            providers = Counter(event.get("args", {}).get("provider") for event in events
                                if event.get("cat") == "Node" and event.get("args", {}).get("provider"))
            report["profiles"].append({"model": name, "selected": session.get_providers(),
                                       "executed_node_events": dict(providers), "file": path.name})
    for record in records.values():
        record["warm_median_seconds"] = statistics.median(record["warm_seconds"])
    report["cases"] = records
    report["sum_warm_medians_seconds"] = sum(record["warm_median_seconds"] for record in records.values())
    del models, engine, BenchFactory
    sessions.clear()
    gc.collect()
    report["memory_after_release"] = memory()
    (args.output / "result.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "init_s": report["initialization_seconds"],
                      "sum_warm_medians_s": report["sum_warm_medians_seconds"], "selected": report["selected_providers_after"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("cpu", "directml"), required=True)
    parser.add_argument("--corpus", choices=("synthetic", "templates"), default="synthetic")
    parser.add_argument("--runtime", type=Path, help="Complete prepared runtime directory, for this process only")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--stress-calls", type=int, default=100)
    parser.add_argument("--profile", action="store_true", help="Instrumented provider audit, not a latency benchmark")
    parser.add_argument("--hardware-label", default="")
    arguments = parser.parse_args()
    if arguments.repeats < 1 or arguments.stress_calls < 0:
        parser.error("--repeats must be positive and --stress-calls non-negative")
    run(arguments)
