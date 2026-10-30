"""按 OCR 等价标准比较离线结果；不要求浮点结果逐位一致。"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFC", text).strip()


def compare(cpu, directml):
    import cv2
    import numpy as np

    results = {}
    for name, baseline in cpu["cases"].items():
        candidate = directml["cases"][name]
        reasons = []
        if baseline["pixel_sha256"] != candidate["pixel_sha256"] or baseline["size"] != candidate["size"]:
            reasons.append("different input pixels")
        left, right = baseline["first_output"], candidate["first_output"]
        left_texts, right_texts = list(map(normalize, left["texts"])), list(map(normalize, right["texts"]))
        missing = Counter(left_texts) - Counter(right_texts)
        extra = Counter(right_texts) - Counter(left_texts)
        if missing or extra:
            reasons.append("different recognized text/token counts")
        max_score_delta = 0.0
        max_corner_delta = 0.0
        minimum_iou = 1.0
        unused = set(range(len(right_texts)))
        for index, text in enumerate(left_texts):
            choices = [j for j in unused if right_texts[j] == text]
            if not choices:
                continue
            if left["boxes"] is not None and right["boxes"] is not None:
                a = np.asarray(left["boxes"][index], dtype=np.float32)

                def geometry(j):
                    b = np.asarray(right["boxes"][j], dtype=np.float32)
                    intersection = cv2.intersectConvexConvex(a, b)[0]
                    union = cv2.contourArea(a) + cv2.contourArea(b) - intersection
                    return (intersection / union if union > 0 else 0.0,
                            float(np.max(np.linalg.norm(a - b, axis=1))))

                matched = max(choices, key=lambda j: geometry(j)[0])
                iou, corners = geometry(matched)
                minimum_iou = min(minimum_iou, iou)
                max_corner_delta = max(max_corner_delta, corners)
                if iou < 0.95 or corners > max(2.0, max(baseline["size"]) * 0.005):
                    reasons.append("box geometry outside tolerance")
            else:
                matched = choices[0]
                if (left["boxes"] is None) != (right["boxes"] is None):
                    reasons.append("different coordinate availability")
            unused.remove(matched)
            score_a, score_b = left["scores"][index], right["scores"][matched]
            delta = abs(score_a - score_b)
            max_score_delta = max(max_score_delta, delta)
            if delta > 0.005:
                reasons.append("confidence delta exceeds 0.005")
            if any((score_a > threshold) != (score_b > threshold) for threshold in (0.5, 0.7, 0.9)):
                reasons.append("confidence threshold decision changed")
        expected = Counter(map(normalize, baseline["expected_lines"]))
        joined = lambda texts: "".join("".join(map(normalize, texts)).split())
        results[name] = {"equivalent": not reasons, "reasons": sorted(set(reasons)), "missing_vs_cpu": dict(missing),
                         "extra_vs_cpu": dict(extra), "max_confidence_delta": max_score_delta,
                         "min_box_iou": minimum_iou, "max_corner_displacement_px": max_corner_delta,
                         "cpu_strict_line_misses_vs_rendered": dict(expected - Counter(left_texts)),
                         "cpu_strict_line_extras_vs_rendered": dict(Counter(left_texts) - expected),
                         "dml_strict_line_misses_vs_rendered": dict(expected - Counter(right_texts)),
                         "dml_strict_line_extras_vs_rendered": dict(Counter(right_texts) - expected),
                         "cpu_joined_text_matches_rendered": joined(left_texts) == joined(baseline["expected_lines"]),
                         "dml_joined_text_matches_rendered": joined(right_texts) == joined(baseline["expected_lines"]),
                         "cpu_warm_median_seconds": baseline["warm_median_seconds"],
                         "dml_warm_median_seconds": candidate["warm_median_seconds"],
                         "warm_speedup": baseline["warm_median_seconds"] / candidate["warm_median_seconds"]}
        repeat_failures = []
        repeat_max_delta = 0.0
        repeat_max_corners = 0.0
        for variant, case in (("cpu", baseline), ("directml", candidate)):
            for repeat, observed in enumerate(case.get("warm_outputs", [])):
                repeated = dict(case, first_output=observed)
                repeated.pop("warm_outputs", None)
                fixed = dict(baseline)
                fixed.pop("warm_outputs", None)
                check = compare({"models": cpu["models"], "cases": {name: fixed}},
                                {"models": cpu["models"], "cases": {name: repeated}})["cases"][name]
                repeat_max_delta = max(repeat_max_delta, check["max_confidence_delta"])
                repeat_max_corners = max(repeat_max_corners, check["max_corner_displacement_px"])
                if not check["equivalent"]:
                    repeat_failures.append({"variant": variant, "repeat": repeat, "reasons": check["reasons"]})
        results[name]["repeat_failures"] = repeat_failures
        results[name]["max_repeat_confidence_delta_vs_cpu_first"] = repeat_max_delta
        results[name]["max_repeat_corner_displacement_px"] = repeat_max_corners
        results[name]["repeated_outputs_checked"] = sum(len(case.get("warm_outputs", [])) for case in (baseline, candidate))
        if repeat_failures:
            results[name]["equivalent"] = False
    same_models = {key: value["sha256"] for key, value in cpu["models"].items()} == {
        key: value["sha256"] for key, value in directml["models"].items()}
    return {"equivalent": same_models and set(cpu["cases"]) == set(directml["cases"]) and
            all(item["equivalent"] for item in results.values()), "same_models": same_models, "cases": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpu", type=Path, required=True)
    parser.add_argument("--directml", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True, help="Separate --profile result.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("--output must not exist")
    report = compare(json.loads(args.cpu.read_text(encoding="utf-8")),
                     json.loads(args.directml.read_text(encoding="utf-8")))
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    executed = [item["model"] for item in audit["profiles"] if
                item["executed_node_events"].get("DmlExecutionProvider", 0) > 0]
    report["dml_execution_proven_for_det_and_rec"] = all(
        any(f"{stage}_" in model.lower() for model in executed) for stage in ("det", "rec"))
    report["accepted"] = report["equivalent"] and report["dml_execution_proven_for_det_and_rec"]
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"accepted": report["accepted"], "equivalent": report["equivalent"], "dml_models": executed}))
    raise SystemExit(0 if report["accepted"] else 1)
