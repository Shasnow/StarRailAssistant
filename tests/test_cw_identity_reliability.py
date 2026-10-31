"""真实后台几何/角色复核通过公开整备入口，OCR分数来自历史普通面板读取。"""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
import pytest

from SRACore.util.errors import ThreadStoppedError
from extensions.cw_plus.logic import SlotState
from extensions.cw_plus.preparation import Readiness
from extensions.cw_plus.unicode_templates import load_template
from tests.cw_reliability_replay import ReplayOperator, engine, replay  # noqa: F401

FIXTURES = Path(__file__).parent / "fixtures/backend_identity"
META = json.loads((FIXTURES / "provenance.json").read_text(encoding="utf-8"))


class IdentityOperator(ReplayOperator):
    def __init__(self, clock):
        super().__init__(clock)
        self.scores = (.89194, .89328)
        self.names = ("千冶·刃",)
        self.panel_reads = self.panel_captures = 0

    @property
    def ocr_engine(self):
        # 此边界只为所选面板提供保存的模型输出；其他读数使用原operator.ocr入口。
        if self.selected != ("off_field", 3):
            raise AttributeError("No recorded engine output outside selected panel")
        return self.panel_ocr

    def panel_ocr(self, image, **kwargs):
        if image.size != (202, 61):
            return SimpleNamespace(txts=[], boxes=[], scores=[])
        index = self.panel_reads
        self.panel_reads += 1
        return SimpleNamespace(txts=[self.names[index % len(self.names)]],
            boxes=[[[1, 21], [99, 21], [99, 60], [1, 60]]], scores=[self.scores[index % len(self.scores)]])

    def screenshot(self, **kwargs):
        frame = super().screenshot(**kwargs)
        if self.selected == ("off_field", 3):
            self.panel_captures += 1
            # 两张面板真有不同像素；不以变化的假OCR结果绕过像素缓存契约。
            frame.putpixel((1490, 190), (self.panel_captures % 255, 100, 100))
        if getattr(self, "lose_layout_after_panel", False) and self.panel_reads >= 2 and self.selected is None:
            frame.paste((15, 25, 35), (192, 560, 1652, 760))
        return frame


@pytest.fixture
def identity(replay):
    task, old, clock = replay.task, replay.operator, replay.clock
    operator = IdentityOperator(clock)
    operator.frame = old.frame.copy()
    operator.points = dict(old.points)
    operator.scene = dict(old.scene)
    operator.scene[("off_field", 3)] = operator.scene.pop(("off_field", 1))
    with Image.open(FIXTURES / "row.png") as row:
        operator.frame.paste(row.convert("RGB"), tuple(META["paste_at"]))
    operator.frame.paste(load_template(engine.CWIMG.STAR), (1596, 163))
    task.operator = task._vision.operator = operator
    task.off_field_area = [tuple(point) for point in META["previous_positions"]]
    for i, point in enumerate(task.off_field_area):
        operator.points[point] = "off_field", i
    blade = task._observations["off_field"][1]
    task._observations["off_field"][3] = replace(blade, slot_index=3, state=SlotState.UNKNOWN,
                                              evidence="backend_identity_unknown")
    task.off_field_character[3] = blade.character
    empty = task._observations["off_field"][2]
    task._observations["off_field"][1] = replace(empty, slot_index=1)
    task.off_field_character[1] = None
    task._backend_unknown_slots = {3}
    task._backend_ordinary_slots = (0, 1, 2, 4, 5)
    task._backend_identity_confirmed = False
    task._purchase_pending_names.clear()
    task._purchase_scan_baseline = None
    task._dirty_slots = {("off_field", 3)}
    # 负例只需一次真实复核，不重复昂贵的几何扫描来证明同一拒绝。
    task.preparation_budget["recoveries"] = 0
    return task, operator


def test_recorded_normal_confidence_recovers_ordinary_blade_without_input(identity):
    task, operator = identity

    result = task.prepare_for_battle()

    assert result.state == Readiness.READY, result
    assert operator.inputs == []


@pytest.mark.parametrize("fault", ["below_floor", "higher_configured_threshold", "unknown_name",
                                  "conflicting_names", "missing_stars", "layout_lost"])
def test_role_review_never_relaxes_other_identity_requirements(identity, fault):
    task, operator = identity
    if fault == "below_floor":
        operator.ocr_confidence = .2
        operator.scores = (.69, .69)
    elif fault == "higher_configured_threshold":
        operator.ocr_confidence = .95
    elif fault == "unknown_name":
        operator.names = ("TEST_UNKNOWN_CHARACTER",)
    elif fault == "conflicting_names":
        operator.names = ("千冶·刃", "三月七")
    elif fault == "missing_stars":
        operator.frame.paste((15, 25, 35), (1593, 162, 1671, 185))
    else:
        operator.lose_layout_after_panel = True

    result = task.prepare_for_battle()

    assert result.state == Readiness.BLOCKED, result
    assert operator.inputs == []


def test_role_review_stop_propagates_without_input(identity):
    task, operator = identity
    operator.stop_event.set()
    with pytest.raises(ThreadStoppedError):
        task.prepare_for_battle()
    assert operator.inputs == []
