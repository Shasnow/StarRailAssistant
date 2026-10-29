"""公开终局导航：真实模板匹配、保存的像素/OCR、虚拟输入和时钟。"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace

from PIL import Image
from loguru import logger
import pyscreeze
import pytest

from SRACore.operators.model import Box
from SRACore.util.errors import ThreadStoppedError
from extensions.cw_plus.paths import RESOURCE_ROOT
from extensions.cw_plus.unicode_templates import load_template
from tests.cw_reliability_replay import ReplayClock, engine

FIXTURES = Path(__file__).parent / "fixtures/terminal_overclock"
OCR = json.loads((FIXTURES / "ocr.json").read_text(encoding="utf-8"))


class TerminalOperator:
    def __init__(self):
        self.clock = ReplayClock()
        self.stop_event = Event()
        self.settings = SimpleNamespace()
        self.window_context = SimpleNamespace(width=1920, height=1080)
        self.tm_confidence = .9999
        self.ocr_confidence = .7
        self.page = "summary"
        self.clicks = []
        self.fault = None
        self.readings = OCR
        frame = Image.new("RGB", (1920, 1080))
        with Image.open(FIXTURES / "summary.png") as crop:
            frame.paste(crop.convert("RGB"), (500, 160))
        self.pages = {"summary": frame}
        for page, template in (("details", "next_page.png"), ("return", "back_currency_wars.png")):
            image = Image.new("RGB", frame.size)
            image.paste(load_template(RESOURCE_ROOT / template), (800, 870))
            self.pages[page] = image
        menu = Image.new("RGB", frame.size)
        menu.paste(load_template(engine.CWIMG.START_CURRENCY_WARS), (1450, 900))
        self.pages["main"] = menu

    def sleep(self, seconds):
        self.clock.advance(seconds)

    def screenshot(self, *, from_x=None, from_y=None, to_x=None, to_y=None, **kwargs):
        self.clock.advance(.1)
        frame = self.pages[self.page].copy()
        if self.fault == "missing_next":
            frame.paste((0, 0, 0), (750, 860, 1170, 950))
        if from_x is not None:
            frame = frame.crop((from_x * 1920, from_y * 1080, to_x * 1920, to_y * 1080))
        return frame

    def ocr_engine(self, image, **kwargs):
        rows = deepcopy(self.readings.get(hashlib.sha256(image.tobytes()).hexdigest(), []))
        return rows

    def locate(self, template, **kwargs):
        try:
            match = pyscreeze.locate(load_template(template), self.screenshot(), confidence=self.tm_confidence)
        except pyscreeze.ImageNotFoundException:
            return None
        return Box(*match, source=template) if match else None

    def click_point(self, x, y, *, after_sleep=0, tag="", **kwargs):
        assert .35 <= x <= .65 and .77 <= y <= .9
        self.clicks.append(tag)
        self.page = {"summary": "details", "details": "return", "return": "main"}[self.page]
        self.sleep(after_sleep)
        return True

    def move_to(self, *args, **kwargs):
        return True


@pytest.fixture
def terminal(tmp_path, monkeypatch):
    operator = TerminalOperator()
    monkeypatch.setattr(engine, "time", SimpleNamespace(monotonic=operator.clock.monotonic))
    task = engine.CurrencyWars(operator, 1, data_dir=tmp_path)
    task.REWARD_TRANSITION_TIMEOUT = 8
    task._vision.max_samples = 0
    return task, operator


def test_overclock_win_without_current_rank_panel_returns_to_main(terminal):
    task, operator = terminal

    assert task.handle_game_over(None) is True

    assert operator.page == "main"
    assert operator.clicks == ["终局：final_summary", "终局：final_next_page", "终局：final_return"]


@pytest.fixture
def recorded_terminal(terminal):
    task, operator = terminal
    recorded = Path(__file__).parent / "fixtures/terminal_recorded_235133"
    with Image.open(recorded / "summary.png") as crop:
        frame = Image.new("RGB", (1920, 1080))
        frame.paste(crop.convert("RGB"), (500, 160))
    operator.pages["summary"] = frame
    operator.readings = {**OCR, **json.loads((recorded / "ocr.json").read_text(encoding="utf-8"))}
    return task, operator


def test_recorded_partial_action_requires_full_same_frame_recovery(recorded_terminal):
    task, operator = recorded_terminal

    assert task.handle_game_over(None) is True
    assert operator.page == "main"
    assert operator.clicks == ["终局：final_summary", "终局：final_next_page", "终局：final_return"]


def test_recorded_final_health_is_reported_only_after_two_fresh_frames(recorded_terminal):
    task, operator = recorded_terminal
    messages = []
    sink = logger.add(lambda message: messages.append(message.record["message"]))
    try:
        assert task.handle_game_over(None) is True
    finally:
        logger.remove(sink)
    assert operator.page == "main"
    assert any("小队生命值=100" in message for message in messages)


def test_enlarged_action_cannot_override_a_different_confident_native_action(recorded_terminal):
    task, operator = recorded_terminal
    read = operator.ocr_engine

    def conflicting(image, **kwargs):
        rows = read(image, **kwargs)
        if image.size == (576, 140):
            for row in rows:
                if "下一" in row[1]:
                    row[1], row[2] = "继续挑战", .999
        return rows

    operator.ocr_engine = conflicting
    with pytest.raises(RuntimeError, match="result_terminal_navigation_timeout"):
        task.handle_game_over(None)
    assert operator.clicks == []


@pytest.mark.parametrize("fault", ["weak_title", "weak_health", "weak_evaluation", "missing_health",
                                  "invalid_health", "conflicting_title", "missing_next"])
def test_incomplete_summary_never_authorizes_terminal_input(terminal, fault):
    task, operator = terminal
    operator.fault = fault
    read = operator.ocr_engine

    def ocr(image, **kwargs):
        rows = read(image, **kwargs)
        token = {"weak_title": "挑战成功", "weak_health": "小队生命值",
                 "weak_evaluation": "对局评价", "missing_health": "小队生命值"}.get(fault)
        if token:
            if fault == "missing_health":
                rows = [row for row in rows if token not in row[1]]
            else:
                for row in rows:
                    if token in row[1]:
                        row[2] = .89
        if fault == "invalid_health":
            for row in rows:
                if row[1] == "小队生命值❤100":
                    row[1] = "小队生命值❤150"
        if fault == "conflicting_title":
            for row in list(rows):
                if row[1] == "挑战成功":
                    rows.append([row[0], "挑战失败", .999])
        return rows

    operator.ocr_engine = ocr
    with pytest.raises(RuntimeError, match="result_terminal_navigation_timeout"):
        task.handle_game_over(None)
    assert operator.clicks == []


@pytest.mark.parametrize("fault", ["weak_action", "wrong_action", "stop_action"])
def test_expanded_action_still_requires_exact_confident_text(recorded_terminal, fault):
    task, operator = recorded_terminal
    read = operator.ocr_engine

    def ocr(image, **kwargs):
        rows = read(image, **kwargs)
        if image.size == (1152, 280):
            if fault == "stop_action":
                operator.stop_event.set()
            elif fault == "weak_action":
                rows[0][2] = .89
            else:
                rows[0][1] = "下一页"
        return rows

    operator.ocr_engine = ocr
    with pytest.raises(ThreadStoppedError if fault == "stop_action" else RuntimeError):
        task.handle_game_over(None)
    assert operator.clicks == []


@pytest.mark.parametrize("value,score", [("150", .999), ("100", .89), ("100 | 99", .999)])
def test_gray_fallback_cannot_override_invalid_weak_or_conflicting_rgb_health(recorded_terminal, value, score):
    task, operator = recorded_terminal
    read = operator.ocr_engine
    gray_calls = 0

    def ocr(image, **kwargs):
        nonlocal gray_calls
        if image.size == (268, 54):
            if image.mode == "L":
                gray_calls += 1
                return read(image, **kwargs)
            box = [[24, 6], [240, 6], [240, 50], [24, 50]]
            if value == "100 | 99":
                return [(box, "小队生命值100", score), (box, "小队生命值99", score)]
            return [(box, "小队生命值" + value, score)]
        return read(image, **kwargs)

    operator.ocr_engine = ocr
    messages = []
    sink = logger.add(lambda message: messages.append(message.record["message"]))
    try:
        assert task.handle_game_over(None) is True
    finally:
        logger.remove(sink)
    assert gray_calls == 0
    assert any("小队生命值=None" in message for message in messages)


def test_two_disagreeing_summary_frames_do_not_authorize_a_click(terminal):
    task, operator = terminal
    capture = operator.screenshot
    count = 0

    def alternating(**kwargs):
        nonlocal count
        frame = capture(**kwargs)
        count += 1
        if count % 2:
            frame.paste((0, 0, 0), (576, 335, 1325, 421))
        return frame

    operator.screenshot = alternating
    with pytest.raises(RuntimeError, match="result_terminal_navigation_timeout"):
        task.handle_game_over(None)
    assert operator.clicks == []


def test_stop_before_terminal_read_is_not_swallowed(terminal):
    task, operator = terminal
    operator.stop_event.set()
    with pytest.raises(ThreadStoppedError):
        task.handle_game_over(None)
    assert operator.clicks == []
