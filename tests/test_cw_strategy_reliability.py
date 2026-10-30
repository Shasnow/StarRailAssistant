"""公开攻略导入入口；只使用虚拟剪贴板，不包含真实分享码。"""
from pathlib import Path
from threading import Event
from types import SimpleNamespace

from PIL import Image, ImageDraw
import numpy as np
import pytest

from SRACore.operators.model import Box
from SRACore.util.errors import ThreadStoppedError
from extensions.cw_plus.unicode_templates import load_template
from tests.cw_reliability_replay import ReplayClock, engine

CODE = "TEST_ONLY_NOT_A_SHARE_CODE_0123456789"


class ImportOperator:
    def __init__(self):
        self.settings = SimpleNamespace()
        self.window_context = SimpleNamespace(width=1920, height=1080)
        self.stop_event = Event()
        self.tm_confidence = .9
        self.ocr_confidence = .7
        self.clock = ReplayClock()
        self.phase = "strategy"
        self.clipboard = self.text = ""
        self.confirms = self.native_pastes = self.shortcut_pastes = 0
        self.inputs = []
        self.native_works = False
        self.read_text = None
        self.application_confirmed = True
        self.ocr_score = .99
        self.modern_output = False
        self.stop_after_paste = False
        self.hide_control = None
        with Image.open(Path(__file__).parent / "fixtures/cw_strategy_code_dialog.png") as image:
            self.dialog = image.convert("RGB")

    def sleep(self, seconds):
        self.clock.advance(seconds)

    def screenshot(self):
        self.clock.advance(.05)
        frame = Image.new("RGB", (1920, 1080), (15, 25, 35))
        if self.phase == "dialog":
            frame.paste(self.dialog, (398, 288))
            if self.hide_control == "title":
                ImageDraw.Draw(frame).rectangle((870, 324, 1048, 360), fill=(196, 196, 196))
            elif self.hide_control == "paste":
                ImageDraw.Draw(frame).rectangle((1418, 509, 1470, 562), fill=(196, 196, 196))
            if self.text:
                draw = ImageDraw.Draw(frame)
                draw.rectangle((445, 430, 1395, 635), fill=(196, 196, 196))
                draw.text((458, 435), self.text, fill=(55, 55, 55))
        elif self.phase == "applied":
            frame.paste(load_template(engine.CurrencyWars.STRATEGY_APPLIED_IMAGE), (1200, 850))
        elif self.phase == "preparation":
            frame.paste(load_template(engine.CWIMG.PREPARATION_STAGE), (20, 20))
            frame.paste(load_template(engine.CWIMG.FOLD), (1000, 850))
        return frame

    def wait_img(self, template, **kwargs):
        return self.locate(template)

    def locate(self, template, **kwargs):
        if template == engine.CWIMG.STRATEGY and self.phase == "strategy":
            return Box(1570, 45, 80, 44, source=template)
        if template == engine.CWIMG.ENTER_STRATEGY_CODE and self.phase == "strategy":
            return Box(1400, 960, 166, 48, source=template)
        if template == engine.IMG.ENSURE2 and self.phase == "dialog":
            return Box(987, 713, 364, 62, source=template)
        if template == engine.CWIMG.APPLY_STRATEGY and self.phase == "apply":
            return Box(1400, 900, 160, 50, source=template)
        if (template == engine.CurrencyWars.STRATEGY_APPLIED_IMAGE and self.phase == "applied"
                and self.application_confirmed):
            return Box(1200, 850, 160, 50, source=template)
        return None

    def locate_any(self, templates, **kwargs):
        for index, template in enumerate(templates):
            box = self.locate(template)
            if box is not None:
                return index, box
        return -1, None

    def click_box(self, box, *, after_sleep=0, **kwargs):
        self.inputs.append(box.source)
        if box.source == engine.CWIMG.ENTER_STRATEGY_CODE:
            self.phase = "dialog"
        elif box.source == engine.IMG.ENSURE2:
            self.confirms += 1
            if self.text:
                self.phase = "apply"
        elif str(box.source).endswith("strategy_code_paste.png"):
            self.native_pastes += 1
            if self.native_works:
                self.text = self.clipboard
            if self.stop_after_paste:
                self.stop_event.set()
        elif box.source == engine.CWIMG.APPLY_STRATEGY:
            self.phase = "applied"
        self.sleep(after_sleep)
        return True

    def click_point(self, *args, after_sleep=0, **kwargs):
        self.sleep(after_sleep)
        return True

    def copy(self, text):
        self.clipboard = text

    def paste(self):
        self.shortcut_pastes += 1  # 复现无异常、但字段没有变化的快捷键路径。

    def ocr_engine(self, image, **kwargs):
        text = self.read_text if self.read_text is not None else self.text or "请输入攻略码..."
        box = [[0, 0], [700, 0], [700, 25], [0, 25]]
        if self.modern_output:
            return SimpleNamespace(boxes=[box], txts=[text], scores=[self.ocr_score])
        return [(box, text, self.ocr_score)]

    def press_key(self, key, **kwargs):
        self.inputs.append(key)
        if key == "esc" and self.phase == "applied":
            self.phase = "preparation"
        return True


@pytest.fixture
def strategy(tmp_path, monkeypatch):
    operator = ImportOperator()
    monkeypatch.setattr(engine, "time", SimpleNamespace(monotonic=operator.clock.monotonic))
    task = engine.CurrencyWars(operator, 1, data_dir=tmp_path)
    task._vision.max_samples = 0
    task.strategy_code = CODE
    return task, operator


def test_empty_paste_is_never_submitted(strategy):
    task, operator = strategy

    assert task.handle_game_entered() is False
    assert operator.confirms == 0
    assert engine.CWIMG.APPLY_STRATEGY not in operator.inputs
    assert operator.native_pastes == 1


def test_native_paste_works_without_keyboard_shortcut(strategy):
    task, operator = strategy
    operator.native_works = True

    assert task.handle_game_entered() is True
    assert operator.confirms == operator.native_pastes == 1
    assert operator.shortcut_pastes == 0
    assert operator.phase == "preparation"


@pytest.mark.parametrize("reading", ["", "请输入攻略码...", "UNRELATED_TEST_TEXT_9876543210"])
def test_empty_or_unrelated_ocr_never_authorizes_submission(strategy, reading):
    task, operator = strategy
    operator.native_works = True
    operator.read_text = reading

    assert task.handle_game_entered() is False
    assert operator.confirms == 0
    assert operator.native_pastes == 1


@pytest.mark.parametrize("score", [.69, float("nan"), float("inf"), True])
def test_invalid_or_weak_ocr_never_authorizes_submission(strategy, score):
    task, operator = strategy
    operator.native_works = True
    operator.ocr_score = score

    assert task.handle_game_entered() is False
    assert operator.confirms == 0


@pytest.mark.parametrize("control", ["title", "paste"])
def test_dialog_identity_is_required_before_copy_or_paste(strategy, control):
    task, operator = strategy
    operator.hide_control = control

    assert task.handle_game_entered() is False
    assert operator.clipboard == ""
    assert operator.confirms == operator.native_pastes == 0


def test_visible_placeholder_cannot_be_overridden_by_matching_ocr_text(strategy):
    task, operator = strategy
    operator.read_text = CODE

    assert task.handle_game_entered() is False
    assert operator.confirms == 0


def test_clicking_apply_is_not_proof_of_game_acceptance(strategy):
    task, operator = strategy
    operator.native_works = True
    operator.application_confirmed = False

    assert task.handle_game_entered() is False
    assert operator.phase == "applied"
    assert "esc" not in operator.inputs


def test_stop_after_single_paste_propagates_without_confirmation(strategy):
    task, operator = strategy
    operator.stop_after_paste = True

    with pytest.raises(ThreadStoppedError):
        task.handle_game_entered()
    assert operator.confirms == 0
    assert operator.native_pastes == 1


@pytest.mark.parametrize("modern_output", [False, True], ids=["rows", "modern"])
@pytest.mark.parametrize("score", [True, False, np.bool_(True), np.bool_(False)],
                         ids=["true", "false", "numpy-true", "numpy-false"])
def test_boolean_confidence_never_authorizes_submission(strategy, modern_output, score):
    task, operator = strategy
    operator.native_works = True
    operator.modern_output, operator.ocr_score = modern_output, score

    assert task.handle_game_entered() is False
    assert operator.confirms == 0
    assert engine.CWIMG.APPLY_STRATEGY not in operator.inputs


@pytest.mark.parametrize("modern_output,score", [
    pytest.param(False, .7, id="rows-threshold"),
    pytest.param(False, .99, id="rows-float"),
    pytest.param(False, 1, id="rows-integer"),
    pytest.param(True, .7, id="modern-threshold"),
    pytest.param(True, .99, id="modern-float"),
    pytest.param(True, 1, id="modern-integer"),
    pytest.param(True, np.float32(.99), id="modern-numpy-float32"),
    pytest.param(True, np.float64(.99), id="modern-numpy-float64"),
])
def test_supported_numeric_confidence_preserves_normal_import(strategy, modern_output, score):
    task, operator = strategy
    operator.native_works = True
    operator.modern_output, operator.ocr_score = modern_output, score

    assert task.handle_game_entered() is True
    assert operator.confirms == operator.native_pastes == 1
    assert operator.phase == "preparation"
