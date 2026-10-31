"""真实空标像素通过公开整备入口；OCR/输入/时钟为离线边界。"""
from dataclasses import replace
import json
from pathlib import Path
import random

from PIL import Image, ImageDraw
import pytest

from SRACore.util.errors import ThreadStoppedError
from extensions.cw_plus.logic import SlotState
from extensions.cw_plus.paths import CALIBRATION_ROOT
from extensions.cw_plus.preparation import Readiness
from tests.cw_reliability_replay import replay  # noqa: F401

FIXTURES = Path(__file__).parent / "fixtures/frontend_empty"
META = json.loads((FIXTURES / "provenance.json").read_text(encoding="utf-8"))["round_1_2"]
BOUNDS = tuple(round((META["position"][i % 2] + value) * (1920, 1080)[i % 2])
               for i, value in enumerate(META["relative_box"]))


def prepare_crop(replay, crop):
    task, operator = replay.task, replay.operator
    operator.frame.paste(crop, BOUNDS[:2])
    operator.ambiguous_empty.add(("on_field", 2))
    task._purchase_pending_names.clear()
    task._purchase_scan_baseline = None
    task._dirty_slots.discard(("in_hand", 0))
    task._observations["on_field"][2] = replace(task._observations["on_field"][2],
        state=SlotState.UNKNOWN, evidence="investment_reward_unknown")
    task._slot_evidence.pop(("on_field", 2), None)
    task._dirty_slots.add(("on_field", 2))


@pytest.mark.parametrize("case", ["round_1_1", "round_1_2", "earlier_run"])
def test_recorded_thin_empty_emblem_does_not_block_preparation(replay, case):
    with Image.open(FIXTURES / (case + ".png")) as crop:
        prepare_crop(replay, crop.convert("RGB"))

    result = replay.task.prepare_for_battle()

    assert result.state == Readiness.READY, result
    assert replay.operator.inputs == []


@pytest.mark.parametrize("control", ["blank", "gradient", "star", "noise", "occupied",
                                     "top_hidden", "middle_hidden", "bottom_hidden"])
def test_similar_colors_or_incomplete_glyph_never_prove_empty(replay, control):
    with Image.open(FIXTURES / "round_1_2.png") as image:
        crop = image.convert("RGB")
    color = crop.getpixel((1, crop.height // 2))
    if control == "occupied":
        with Image.open(CALIBRATION_ROOT / "field-occupied-0-on_field-0.png") as image:
            crop = image.convert("RGB").resize(crop.size)
    elif control in {"blank", "gradient", "star", "noise"}:
        crop = Image.new("RGB", crop.size, color)
        draw = ImageDraw.Draw(crop)
        if control == "gradient":
            for y in range(crop.height):
                draw.line((0, y, crop.width, y), fill=tuple(min(255, c + y // 8) for c in color))
        elif control == "star":
            draw.regular_polygon((crop.width // 2, crop.height // 2, 8), 5, fill=(160, 160, 190))
        elif control == "noise":
            rng = random.Random(527)
            crop.putdata([tuple(min(255, c + 15) for c in color) if rng.random() < .25 else color
                          for _ in range(crop.width * crop.height)])
    else:
        third = crop.height // 3
        y = {"top_hidden": 0, "middle_hidden": third, "bottom_hidden": 2 * third}[control]
        ImageDraw.Draw(crop).rectangle((0, y, crop.width, y + third + 2), fill=color)
    prepare_crop(replay, crop)

    result = replay.task.prepare_for_battle()

    assert result.state == Readiness.BLOCKED, result
    assert replay.operator.inputs == []


def test_two_live_frames_must_agree_on_empty_slot(replay):
    with Image.open(FIXTURES / "round_1_2.png") as image:
        empty = image.convert("RGB")
    with Image.open(CALIBRATION_ROOT / "field-occupied-0-on_field-0.png") as image:
        occupied = image.convert("RGB").resize(empty.size)
    prepare_crop(replay, empty)
    captures = 0

    def screenshot():
        nonlocal captures
        captures += 1
        frame = replay.operator.frame.copy()
        frame.paste(empty if captures % 2 else occupied, BOUNDS[:2])
        return frame

    replay.operator.screenshot = screenshot
    result = replay.task.prepare_for_battle()

    assert result.state == Readiness.BLOCKED, result
    assert replay.operator.inputs == []


def test_stop_before_empty_read_propagates_without_input(replay):
    replay.operator.stop_event.set()
    with pytest.raises(ThreadStoppedError):
        replay.task.prepare_for_battle()
    assert replay.operator.inputs == []


@pytest.mark.parametrize("control", ["empty", "blank", "occupied"])
def test_backend_slot_keeps_original_exact_structure_contract(replay, control):
    task, operator = replay.task, replay.operator
    profile = json.loads((CALIBRATION_ROOT / "field_profile.json").read_text(encoding="utf-8"))
    slot = next(item for item in profile["slots"] if (item["area"], item["index"]) == ("off_field", 2))
    # 静态审核配置来自另一行位置；不能把默认坐标误当成该模板的已校准坐标。
    task.off_field_area[2] = tuple(slot["position"])
    operator.points[task.off_field_area[2]] = "off_field", 2
    group = "occupied" if control == "occupied" else "empty"
    with Image.open(CALIBRATION_ROOT / slot[group][0]["path"]) as image:
        crop = image.convert("RGB")
    if control == "blank":
        crop = Image.new("RGB", crop.size, crop.getpixel((0, 0)))
    bounds = tuple(round((slot["position"][i % 2] + value) * (1920, 1080)[i % 2])
                   for i, value in enumerate(slot["relative_box"]))
    operator.frame.paste(crop, bounds[:2])
    operator.ambiguous_empty.add(("off_field", 2))
    task._purchase_pending_names.clear()
    task._purchase_scan_baseline = None
    task._dirty_slots = {("off_field", 2)}
    task._observations["off_field"][2] = replace(task._observations["off_field"][2],
        state=SlotState.UNKNOWN, evidence="reward_unknown")

    result = task.prepare_for_battle()

    assert result.state == (Readiness.READY if control == "empty" else Readiness.BLOCKED), result
    assert operator.inputs == []
