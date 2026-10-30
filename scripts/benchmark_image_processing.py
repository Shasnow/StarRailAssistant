"""离线精确对照与 CPU 基准；不截图、不运行游戏、不修改设置。"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
import types

import cv2
import numpy as np
import pyscreeze

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from extensions.cw_plus import equipment_choice, shop_overlay  # noqa: E402
from tests.image_processing_cases import (  # noqa: E402
    equipment_cases, equipment_frame, probability_cases, probability_frame,
)


def reference(ref, filename):
    source = subprocess.check_output(["git", "show", f"{ref}:extensions/cw_plus/{filename}.py"], cwd=ROOT)
    name = f"_image_baseline_{filename}"
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(compile(source, f"baseline/{filename}.py", "exec"), module.__dict__)
    return module, hashlib.sha256(source).hexdigest()


def original_match(needle, haystack, confidence):
    try:
        match = pyscreeze.locate(needle, haystack, grayscale=False, confidence=confidence)
        return tuple(match) if match is not None else None
    except pyscreeze.ImageNotFoundException:
        return None


def equipment_result(module, image, rows):
    geometry = module.equipment_choice_geometry(image)
    observation = module.detect_equipment_choice(image, rows)
    reused = (module.detect_equipment_choice(image, rows, cards=geometry[0])
              if geometry is not None else observation)
    return dict(geometry=geometry, cards=module.equipment_choice_cards(image),
                observation=asdict(observation), reused=asdict(reused),
                stable=module.same_equipment_choice(observation, reused))


def probability_result(module, image, rows):
    panel = module.observe_shop_probability_panel(image)
    frame = panel.frame
    pixels = None if frame is None else (frame.mode, frame.size, hashlib.sha256(frame.tobytes()).hexdigest())
    return dict(present=panel.present, same_image=panel.image is image, pixels=pixels,
                precheck=module.shop_probability_panel_present(image),
                observation=asdict(module.detect_shop_probability_overlay(image, rows)),
                reused=asdict(module.detect_shop_probability_overlay(image, rows, panel_observation=panel)))


def check(original_equipment, original_probability):
    checked = {}
    for label, cases, before, after, observe in (
        ("equipment", equipment_cases, original_equipment, equipment_choice, equipment_result),
        ("probability", probability_cases, original_probability, shop_overlay, probability_result),
    ):
        names = []
        for name, image, rows in cases():
            expected, actual = observe(before, image, rows), observe(after, image, rows)
            assert expected == actual, (label, name, expected, actual)
            names.append(name)
        checked[label] = names
    return checked


def workloads(before_equipment, before_probability, only_baseline):
    from tests.image_processing_cases import row

    if only_baseline:
        matcher = original_match
    else:
        from extensions.cw_plus.unicode_templates import locate_first

        def matcher(needle, haystack, confidence):
            return locate_first(needle, haystack, confidence=confidence)
    equipment = equipment_frame()
    blank = equipment_frame(fault="empty")
    probability = probability_frame()
    rows = [row("商店刷新概率", box=[[10, 10], [300, 10], [300, 40], [10, 40]])]
    yield "equipment_geometry_complete", (
        lambda: before_equipment.equipment_choice_geometry(equipment),
        lambda: equipment_choice.equipment_choice_geometry(equipment))
    yield "equipment_geometry_no_match", (
        lambda: before_equipment.equipment_choice_geometry(blank),
        lambda: equipment_choice.equipment_choice_geometry(blank))
    yield "probability_complete", (
        lambda: before_probability.detect_shop_probability_overlay(probability, rows),
        lambda: shop_overlay.detect_shop_probability_overlay(probability, rows))
    yield "probability_no_match", (
        lambda: before_probability.observe_shop_probability_panel(blank),
        lambda: shop_overlay.observe_shop_probability_panel(blank))
    rng = np.random.default_rng(521)
    needle = rng.integers(0, 256, (32, 48), dtype=np.uint8)
    sparse = rng.integers(0, 64, (1080, 1920), dtype=np.uint8)
    sparse[700:732, 1300:1348] = needle
    dense = np.zeros((1080, 1920), dtype=np.uint8)
    constant = np.zeros_like(needle)
    for name, template, image, confidence in (
        ("template_sparse", needle, sparse, .95),
        ("template_no_match", needle, sparse, 1.1),
        ("template_dense", constant, dense, .95),
    ):
        # 捕获循环值；输入分配和模型/文件加载不在计时区域。
        yield name, (lambda n=template, h=image, c=confidence: original_match(n, h, c),
                     lambda n=template, h=image, c=confidence: matcher(n, h, c))


def measure(functions, trials, repeats, only_baseline):
    active = ("baseline",) if only_baseline else ("baseline", "optimized")
    samples = {name: [] for name in active}
    for fn in functions[:len(active)]:
        for _ in range(3):
            fn()
    for trial in range(trials):
        order = range(len(active)) if trial % 2 == 0 else reversed(range(len(active)))
        for index in order:
            started = time.perf_counter_ns()
            for _ in range(repeats):
                functions[index]()
            samples[active[index]].append((time.perf_counter_ns() - started) / repeats / 1e6)
    result = {name: {"trial_ms_per_call": values, "median_ms": statistics.median(values)}
              for name, values in samples.items()}
    if not only_baseline:
        result["speedup"] = result["baseline"]["median_ms"] / result["optimized"]["median_ms"]
    for index, name in enumerate(active):
        # 计时结束后单独跟踪；包含 NumPy 缓冲区，不等于进程/原生峰值内存。
        tracemalloc.start()
        functions[index]()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        result[name]["traced_peak_bytes"] = peak
    return result


def ocr_control(trials, repeats, only_baseline):
    from PIL import Image
    from SRACore.operators.factory import OperatorFactory
    import onnxruntime

    engine = OperatorFactory.get_ocr_instance()
    providers = {name: getattr(engine, name).session.session.get_providers()
                 for name in ("text_det", "text_cls", "text_rec")}
    assert all(value == ["CPUExecutionProvider"] for value in providers.values()), providers
    images, hashes = [], {}
    for name in ("next_step", "next_page", "preparation_stage"):
        path = ROOT / "extensions/cw_plus/resources" / f"{name}.png"
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with Image.open(path) as image:
            images.extend((image.convert("RGB"), image.convert("L")))

    def call():
        return [engine(image, use_det=True, use_cls=False, use_rec=True) for image in images]

    # 不改 OCR/预处理，只作真实 CPU 路径负对照，不能归因于本 PR 的加速。
    first, second = call(), call()
    for left, right in zip(first, second):
        assert left.txts == right.txts
        np.testing.assert_array_equal(left.boxes, right.boxes)
        np.testing.assert_array_equal(left.scores, right.scores)
    models = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
              for path in (Path(importlib.util.find_spec("rapidocr").origin).parent / "models").glob("*.onnx")}
    return {"measurement": measure((call, call), trials, repeats, only_baseline),
            "images": hashes, "models": models, "providers": providers,
            "native_runtime": onnxruntime.get_version_string(), "inputs_per_call": len(images),
            "identical_outputs": True, "interpretation": "unchanged CPU OCR control, not an optimization claim"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True, help="本地原始 upstream 提交；不执行 fetch")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--only-baseline", action="store_true")
    parser.add_argument("--ocr-control", action="store_true")
    parser.add_argument("--trials", type=int, default=7)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.trials < 3 or args.repeats < 1:
        parser.error("at least 3 trials and 1 repetition are required")
    ref = subprocess.check_output(
        ["git", "rev-parse", "--verify", f"{args.baseline_ref}^{{commit}}"], cwd=ROOT).decode().strip()
    original_equipment, equipment_hash = reference(ref, "equipment_choice")
    original_probability, probability_hash = reference(ref, "shop_overlay")
    result = dict(baseline=ref, python=sys.version, platform=platform.platform(), processor=platform.processor(),
                  dependencies={name: importlib.metadata.version(name) for name in
                                ("numpy", "pillow", "opencv-python", "pyscreeze", "rapidocr", "onnxruntime")},
                  original_source_sha256={"equipment_choice": equipment_hash, "shop_overlay": probability_hash},
                  trials=args.trials, repeats=args.repeats, warmups=3, order="AB/BA alternating",
                  opencv_threads=cv2.getNumThreads(),
                  memory_note="tracemalloc peak per warm call; excludes untracked OpenCV/Pillow native allocations",
                  comparisons=check(original_equipment, original_probability))
    if not args.check_only:
        result["benchmarks"] = {name: measure(functions, args.trials, args.repeats, args.only_baseline)
                                for name, functions in workloads(original_equipment, original_probability, args.only_baseline)}
        if args.ocr_control:
            result["cpu_ocr_control"] = ocr_control(args.trials, max(1, args.repeats // 3), args.only_baseline)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"baseline": ref, "comparisons": {key: len(value) for key, value in result["comparisons"].items()},
                      "benchmarks": result.get("benchmarks"), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
