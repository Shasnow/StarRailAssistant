"""公开购物入口，真实视觉/经济逻辑与虚拟Win32边界；不发送系统输入。"""
import ctypes
import sys
from types import SimpleNamespace

import pytest

from SRACore.util.errors import ThreadStoppedError
from extensions.cw_plus.logic import SlotObservation, SlotState
from extensions.cw_plus.unicode_templates import load_template
from tests.cw_reliability_replay import ReplayClock, ReplayOperator, engine, paint_slots

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Win32 input boundary")


class ShopOperator(ReplayOperator):
    type = "Local"

    def __init__(self, clock):
        super().__init__(clock)
        self.shop_open = False
        self.level, self.progress, self.gold = 6, 34, 20
        self.native_events = []
        self.store_name = None
        self.store_price = None
        self.card_clicks = 0
        self.game_accepts = self.active = True
        self.minimum_hold = 0
        paint_slots(self)

    def is_window_active(self):
        return self.active

    def screenshot(self, **kwargs):
        frame = super().screenshot(**kwargs)
        if self.shop_open:
            frame.paste(load_template(engine.CWIMG.FOLD), (1550, 960))
        return frame

    def click_point(self, x, y, **kwargs):
        if (x, y) == (.25, .18):
            self.card_clicks += 1
        if (x, y) in ((.8438, .8481), (1620, 915)):
            self.shop_open = True
        return super().click_point(x, y, **kwargs)

    def click_box(self, box, after_sleep=0, **kwargs):
        if box.source == engine.CWIMG.FOLD:
            self.shop_open = False
        self.sleep(after_sleep)
        return True

    def press_key(self, key, **kwargs):
        self.inputs.append(("logical_key", key))
        if self.type == "Browser" and key == "f":
            self.gold -= 4
            self.level, self.progress = 7, 2
        return True  # 复现逻辑键映射失效而不报错。

    def ocr(self, *, from_x=None, **kwargs):
        if from_x == .19 and self.store_name:
            rows = [([[70, 5], [150, 5], [150, 30], [70, 30]], self.store_name, .999)]
            if self.store_price is not None:
                rows.append(([[220, 5], [238, 5], [238, 30], [220, 30]], str(self.store_price), .999))
            return rows
        if from_x in (.115, .05, .015):
            return [([[5, 5 + 25 * i], [110, 5 + 25 * i], [110, 25 + 25 * i], [5, 25 + 25 * i]], text, .999)
                    for i, text in enumerate(("购买经验", f"Lv.{self.level}", f"{self.progress}/36"))]
        text = (str(self.gold) if from_x == .815 else "4" if from_x == .158 else
                "2" if from_x == .846 else "备战阶段 2-5" if from_x in (.105, .205) else "")
        return [([[5, 10], [28, 10], [28, 31], [5, 31]], text, .999)] if text else []

    def send_input(self, count, inputs, size):
        assert count == len(inputs) == 1
        assert size == 40  # Win64 INPUT须包含鼠标大小的union。
        events = [(item.type, item.ki.wVk, item.ki.wScan, item.ki.dwFlags) for item in inputs]
        assert all(item[:2] == (1, 0) and item[3] in (8, 10) for item in events)
        self.native_events.extend(events)
        for event in events:
            if event[3] == 8:
                self.held_since = self.clock.value
            elif self.game_accepts and self.clock.value - self.held_since >= self.minimum_hold:
                if event[2] == 0x21:
                    self.gold -= 4
                    self.progress += 4
                    if self.progress >= 36:
                        self.level += 1
                        self.progress -= 36
                elif event[2] == 0x20:
                    self.gold -= 2
        return count


@pytest.fixture
def shop(tmp_path, monkeypatch, request):
    clock = ReplayClock()
    operator = ShopOperator(clock)
    operator.type = getattr(request, "param", "Local")
    monkeypatch.setattr(engine, "time", SimpleNamespace(monotonic=clock.monotonic))
    monkeypatch.setattr(ctypes.windll.user32, "SendInput", operator.send_input)
    task = engine.CurrencyWars(operator, 1, data_dir=tmp_path)
    task._vision.max_samples = 0
    task.is_overclock = True
    task.min_level = task.mid_level = 7
    task.min_coins = 0
    task.shopping_budget.update(actions=3, experiences=1, refreshes=0)
    task._layout_valid = task._backend_identity_confirmed = True
    task._backend_ordinary_slots = tuple(range(6))
    task._bench_dirty = task._placement_pending = False
    for area, slots in task._observations.items():
        for i in range(len(slots)):
            obs = SlotObservation(i, SlotState.EMPTY, occupied=False, evidence="two_empty_frames")
            slots[i] = obs
            task._slot_evidence[area, i] = obs, clock.value
    task._field_observed_at = task._bench_observed_at = clock.value
    return task, operator


def test_experience_purchase_uses_layout_independent_input_and_confirms_game_progress(shop):
    task, operator = shop

    result = task.shopping()

    assert operator.gold == 16, result
    assert operator.level == 7
    assert result.reason != "experience_no_progress"
    assert operator.inputs == []


def test_physical_key_is_held_for_game_polling(shop):
    task, operator = shop
    operator.minimum_hold = .03

    task.shopping()

    assert operator.gold == 16 and operator.level == 7
    assert [event[3] for event in operator.native_events] == [8, 10]


def test_refresh_uses_physical_d_and_observes_payment(shop):
    task, operator = shop
    operator.level = 7
    task.shopping_budget.update(refreshes=1)

    result = task.shopping()

    assert operator.gold == 18, result
    assert result.refreshes == 1
    assert [event[2:] for event in operator.native_events] == [(0x20, 8), (0x20, 10)]


def test_os_acceptance_without_game_progress_never_replays_paid_input(shop):
    task, operator = shop
    operator.game_accepts = False

    result = task.shopping()

    assert result.reason == "experience_no_progress"
    assert operator.gold == 20 and operator.level == 6
    assert len(operator.native_events) == 2


@pytest.mark.parametrize("fault", ["os_rejects", "inactive_window"])
def test_rejected_or_unfocused_input_never_spends(shop, monkeypatch, fault):
    task, operator = shop
    if fault == "os_rejects":
        monkeypatch.setattr(ctypes.windll.user32, "SendInput", lambda *args: 0)
    else:
        operator.active = False

    result = task.shopping()

    assert result.reason == "experience_click_failed"
    assert operator.gold == 20
    assert operator.native_events == []


def test_failed_key_up_retries_only_release_not_purchase(shop, monkeypatch):
    task, operator = shop
    sent = []

    def partial_send(count, events, size):
        sent.extend(event.ki.dwFlags for event in events)
        return 0 if len(sent) == 2 else 1

    monkeypatch.setattr(ctypes.windll.user32, "SendInput", partial_send)
    result = task.shopping()

    assert result.reason == "experience_click_failed"
    assert sent == [8, 10, 10]
    assert operator.gold == 20


def test_stop_immediately_after_down_still_releases_key(shop, monkeypatch):
    task, operator = shop
    sent = []

    def stop_send(count, events, size):
        sent.extend(event.ki.dwFlags for event in events)
        operator.stop_event.set()
        return count

    monkeypatch.setattr(ctypes.windll.user32, "SendInput", stop_send)
    with pytest.raises(ThreadStoppedError):
        task.shopping()
    assert sent == [8, 10]


def test_stop_during_hold_still_releases_key(shop):
    task, operator = shop
    sleep = operator.sleep

    def stop_during_hold(seconds):
        sleep(seconds)
        if seconds == .05:
            operator.stop_event.set()
            raise ThreadStoppedError("回放停止", "测试")

    operator.sleep = stop_during_hold
    with pytest.raises(ThreadStoppedError):
        task.shopping()
    assert [event[3] for event in operator.native_events] == [8, 10]


def test_insufficient_gold_never_sends_paid_input(shop):
    task, operator = shop
    operator.gold = 3

    task.shopping()

    assert operator.gold == 3 and operator.level == 6
    assert operator.native_events == operator.inputs == []


@pytest.mark.parametrize("shop", ["Browser"], indirect=True)
def test_browser_operator_retains_logical_keyboard_path(shop):
    task, operator = shop

    task.shopping()

    assert operator.gold == 16 and operator.level == 7
    assert operator.inputs == [("logical_key", "f")]
    assert operator.native_events == []


def seed_store_target(shop):
    task, operator = shop
    task.strategy_characters = {"花火": 1}
    task.shopping_budget.update(actions=1, purchases=1, refreshes=0, experiences=0)
    operator.level = 7
    operator.store_name = "花火"


def test_unchanged_purchase_is_not_confirmed_or_clicked_twice(shop):
    seed_store_target(shop)
    task, operator = shop

    result = task.shopping()

    assert result.attempted_purchases == 1
    assert result.confirmed_purchases == 0
    assert operator.card_clicks == 1
    assert operator.gold == 20
    assert operator.native_events == []


def test_known_card_price_above_balance_never_authorizes_purchase(shop):
    seed_store_target(shop)
    task, operator = shop
    operator.store_price, operator.gold = 4, 3

    result = task.shopping()

    assert result.attempted_purchases == result.confirmed_purchases == 0
    assert operator.card_clicks == 0 and operator.gold == 3
    assert operator.native_events == []


def test_occupied_store_slot_with_unknown_name_never_authorizes_purchase(shop):
    seed_store_target(shop)
    task, operator = shop
    operator.store_name = "TEST_UNKNOWN_CHARACTER"
    operator.scene["store", 0] = "花火", 1
    paint_slots(operator)

    result = task.shopping()

    assert result.attempted_purchases == result.confirmed_purchases == 0
    assert operator.card_clicks == 0
    assert operator.native_events == []
