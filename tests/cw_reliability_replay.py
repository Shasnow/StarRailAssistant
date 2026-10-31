"""离线系统边界：虚拟截图、OCR、时间与输入；决策和视觉类仍为真实实现。"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace

from PIL import Image
import pytest

from SRACore.operators.model import Box
from extensions.cw_plus.characters import Characters
from extensions.cw_plus.logic import SlotObservation, SlotState
from extensions.cw_plus.paths import CALIBRATION_ROOT
from extensions.cw_plus.unicode_templates import load_template
from extensions.cw_plus.vision import POPULATION_ROI

engine = importlib.import_module("extensions.cw_plus.CurrencyWars")


class ReplayClock:
    def __init__(self):
        self.value = 1000.0

    def monotonic(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class ReplayOperator:
    def __init__(self, clock):
        self.clock = clock
        self.settings = SimpleNamespace()
        self.window_context = SimpleNamespace(width=1920, height=1080)
        self.stop_event = Event()
        self.tm_confidence = .9999
        self.ocr_confidence = .7
        self.selected = None
        self.points = {}
        self.scene = {}
        self.inputs = []
        self.slot_clicks = []
        self.unknown = set()
        self.missing_stars = set()
        self.ambiguous_empty = set()
        self.ocr_seconds = 0
        self.stop_on_ocr = False
        self.capture_error = False
        self.population = "3/3"
        self.frame = Image.new("RGB", (1920, 1080), (15, 25, 35))
        self.frame.paste(load_template(engine.CWIMG.PREPARATION_STAGE).convert("RGB"), (20, 20))

    def screenshot(self, **kwargs):
        if self.capture_error:
            raise OSError("replay capture unavailable")
        return self.frame.copy()

    def sleep(self, seconds):
        self.clock.advance(seconds)

    def click_point(self, x, y, *, after_sleep=0, **kwargs):
        self.selected = self.points.get((x, y))
        if self.selected is not None:
            self.slot_clicks.append(self.selected)
        self.sleep(after_sleep)
        return True

    def move_to(self, *args, **kwargs):
        return True

    def locate(self, *args, **kwargs):
        return None

    def locate_all(self, template, **kwargs):
        if self.selected in self.missing_stars:
            return []
        _, stars = self.scene.get(self.selected, (None, 0))
        return [Box(10 + 15 * i, 10, 5, 5) for i in range(stars)]

    def ocr(self, *, from_x=None, from_y=None, to_x=None, to_y=None, **kwargs):
        if (from_x, from_y, to_x, to_y) == POPULATION_ROI:
            return [([[1, 1], [40, 1], [40, 20], [1, 20]], self.population, .999)]
        if from_x != .775:
            return []
        self.sleep(self.ocr_seconds)
        if self.stop_on_ocr:
            self.stop_event.set()
        name, _ = self.scene.get(self.selected, (None, 0))
        if self.selected in self.unknown or name is None:
            return []
        return [([[0, 0], [180, 0], [180, 40], [0, 40]], name, .999)]

    def currency_wars_slot_is_empty(self, area, index):
        if (area, index) in self.ambiguous_empty:
            return None
        return self.scene.get((area, index), (None, 0))[0] is None

    def press_key(self, key, **kwargs):
        self.inputs.append(("key", key))
        raise AssertionError("离线整备不得购买、出售或开始战斗")

    def mouse_down(self, *args, **kwargs):
        self.inputs.append(("drag", args))
        raise AssertionError("该回放阵容不需要移动")


def paint_slots(operator):
    for filename in ("profile.json", "field_profile.json"):
        profile = json.loads((CALIBRATION_ROOT / filename).read_text(encoding="utf-8"))
        for slot in profile["slots"]:
            key = slot["area"], slot["index"]
            if key in operator.ambiguous_empty:
                continue
            group = "occupied" if key in operator.scene else "empty"
            template = slot[group][0]["path"]
            left, top = (round((slot["position"][i] + slot["relative_box"][i]) * (1920, 1080)[i])
                         for i in range(2))
            with Image.open(CALIBRATION_ROOT / template) as image:
                operator.frame.paste(image.convert("RGB"), (left, top))


@pytest.fixture
def replay(tmp_path, monkeypatch):
    saved = [(c, vars(c).copy()) for c in {id(c): c for c in Characters.characters.values()}.values()]
    clock = ReplayClock()
    monkeypatch.setattr(engine, "time", SimpleNamespace(monotonic=clock.monotonic))
    operator = ReplayOperator(clock)
    task = engine.CurrencyWars(operator, 1, data_dir=tmp_path / "runtime")
    task._vision.max_samples = 0
    strategy = {"on_field": {"丹恒·饮月": 1}, "off_field": {"三月七": 1, "千冶·刃": 1},
                "formation": {"stages": [{"name": "replay", "min_capacity": 0,
                    "on_field": ["丹恒·饮月"], "off_field": ["三月七", "千冶·刃"]}]}}
    path = tmp_path / "strategy.json"
    path.write_text(json.dumps(strategy, ensure_ascii=False), encoding="utf-8")
    task.load_strategy(str(path))
    operator.scene = {("on_field", 0): ("丹恒·饮月", 1), ("off_field", 0): ("三月七", 1),
                      ("off_field", 1): ("千冶·刃", 1), ("in_hand", 0): ("花火", 1)}
    paint_slots(operator)
    for area, slots in task._observations.items():
        for index in range(len(slots)):
            operator.points[getattr(task, area + "_area")[index]] = area, index
            name, stars = operator.scene.get((area, index), (None, 0))
            obs = SlotObservation(index, SlotState.KNOWN if name else SlotState.EMPTY,
                Characters.get_character(name) if name else None, bool(name),
                "name_match" if name else "empty_detector",
                stars=None if name == "花火" else stars if name else None)
            slots[index] = obs
            getattr(task, area + "_character")[index] = obs.character
            task._slot_evidence[area, index] = obs, clock.value
    task._layout_valid = task._backend_identity_confirmed = True
    task._backend_ordinary_slots = tuple(range(6))
    task._confirmed_layout_positions = tuple(task.off_field_area)
    task._bench_dirty = task._placement_pending = False
    task._bench_observed_at = task._field_observed_at = clock.value
    task._slot_evidence.pop(("in_hand", 0))
    task._dirty_slots.add(("in_hand", 0))
    task._purchase_pending_names = {"花火"}
    task._purchase_scan_baseline = (task._layout_revision,
        {area: list(slots) for area, slots in task._observations.items()})
    try:
        yield SimpleNamespace(task=task, operator=operator, clock=clock)
    finally:
        for character, attributes in saved:
            vars(character).clear()
            vars(character).update(attributes)
