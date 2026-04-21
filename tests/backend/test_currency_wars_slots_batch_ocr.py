from PIL import Image

from tests.backend.test_execution_model_p1 import import_task_module


def test_get_character_in_area_batches_name_ocr_and_resolves_aliases():
    CurrencyWars = import_task_module("tasks.currency_wars.CurrencyWars").CurrencyWars

    capture_height = 56
    capture_gap = CurrencyWars.CHARACTER_NAME_BATCH_GAP

    class FakeOperator:
        def __init__(self):
            self.settings = {}
            self.stop_event = None
            self.clicks: list[tuple[float, float, float, str]] = []
            self.screenshot_calls: list[tuple[float, float, float, float]] = []
            self.ocr_engine_calls: list[tuple[int, int]] = []
            self.ocr_engine = self._ocr_engine

        def click_point(self, x, y, after_sleep=0, tag=""):
            self.clicks.append((x, y, after_sleep, tag))
            return True

        def screenshot(self, *, from_x=None, from_y=None, to_x=None, to_y=None):
            self.screenshot_calls.append((from_x, from_y, to_x, to_y))
            return Image.new("RGB", (192, capture_height), color="white")

        def _ocr_engine(self, image, *, use_det=True, use_cls=False, use_rec=True):
            self.ocr_engine_calls.append(image.size)
            return [
                ([[8, 8], [58, 8], [58, 34], [8, 34]], "椒丘", 0.99),
                (
                    [[8, capture_height + capture_gap + 8], [58, capture_height + capture_gap + 8],
                     [58, capture_height + capture_gap + 34], [8, capture_height + capture_gap + 34]],
                    "交光",
                    0.99,
                ),
            ], None

    operator = FakeOperator()
    task = CurrencyWars(operator, 1)
    target = [None, None]

    task._get_character_in_area([(0.1, 0.2), (0.3, 0.4)], target, force=False)

    assert [character.name if character is not None else None for character in target] == ["椒丘", "爻光"]
    assert operator.screenshot_calls == [CurrencyWars.CHARACTER_NAME_REGION] * 2
    assert operator.ocr_engine_calls == [(192, capture_height * 2 + capture_gap)]
    assert operator.clicks == [
        (0.5, 0.5, CurrencyWars.CHARACTER_NAME_DISMISS_SLEEP, "收起角色信息"),
        (0.1, 0.2, CurrencyWars.CHARACTER_NAME_CAPTURE_SLEEP, "读取角色名 0"),
        (0.5, 0.5, CurrencyWars.CHARACTER_NAME_DISMISS_SLEEP, "关闭角色信息"),
        (0.3, 0.4, CurrencyWars.CHARACTER_NAME_CAPTURE_SLEEP, "读取角色名 1"),
        (0.5, 0.5, CurrencyWars.CHARACTER_NAME_DISMISS_SLEEP, "关闭角色信息"),
    ]


def test_get_character_in_area_skips_existing_slots_when_force_false():
    CurrencyWars = import_task_module("tasks.currency_wars.CurrencyWars").CurrencyWars
    Characters = import_task_module("tasks.currency_wars.characters").Characters

    capture_height = 56

    class FakeOperator:
        def __init__(self):
            self.settings = {}
            self.stop_event = None
            self.clicks: list[tuple[float, float, float, str]] = []
            self.screenshot_calls: list[tuple[float, float, float, float]] = []
            self.ocr_engine_calls: list[tuple[int, int]] = []
            self.ocr_engine = self._ocr_engine

        def click_point(self, x, y, after_sleep=0, tag=""):
            self.clicks.append((x, y, after_sleep, tag))
            return True

        def screenshot(self, *, from_x=None, from_y=None, to_x=None, to_y=None):
            self.screenshot_calls.append((from_x, from_y, to_x, to_y))
            return Image.new("RGB", (192, capture_height), color="white")

        def _ocr_engine(self, image, *, use_det=True, use_cls=False, use_rec=True):
            self.ocr_engine_calls.append(image.size)
            return [
                ([[8, 8], [57, 8], [57, 34], [8, 34]], "佩拉", 0.99),
            ], None

    operator = FakeOperator()
    task = CurrencyWars(operator, 1)
    target = [Characters.get_character("花火"), None]

    task._get_character_in_area([(0.1, 0.2), (0.3, 0.4)], target, force=False)

    assert [character.name if character is not None else None for character in target] == ["花火", "佩拉"]
    assert operator.screenshot_calls == [CurrencyWars.CHARACTER_NAME_REGION]
    assert operator.ocr_engine_calls == [(192, capture_height)]
    assert operator.clicks == [
        (0.5, 0.5, CurrencyWars.CHARACTER_NAME_DISMISS_SLEEP, "收起角色信息"),
        (0.3, 0.4, CurrencyWars.CHARACTER_NAME_CAPTURE_SLEEP, "读取角色名 1"),
        (0.5, 0.5, CurrencyWars.CHARACTER_NAME_DISMISS_SLEEP, "关闭角色信息"),
    ]


def test_get_character_in_area_keeps_single_open_flow_when_detail_is_required():
    CurrencyWars = import_task_module("tasks.currency_wars.CurrencyWars").CurrencyWars

    class FakeOperator:
        def __init__(self):
            self.settings = {}
            self.stop_event = None
            self.clicks: list[tuple[float, float, float, str]] = []
            self.ocr_calls: list[tuple[float, float, float, float]] = []
            self.ocr_engine_calls: list[tuple[int, int]] = []
            self.ocr_engine = self._ocr_engine

        def click_point(self, x, y, after_sleep=0, tag=""):
            self.clicks.append((x, y, after_sleep, tag))
            return True

        def ocr(self, *, from_x=None, from_y=None, to_x=None, to_y=None, trace=True):
            del trace
            self.ocr_calls.append((from_x, from_y, to_x, to_y))
            return [
                ([[8, 8], [57, 8], [57, 34], [8, 34]], "佩拉", 0.99),
            ]

        def _ocr_engine(self, image, *, use_det=True, use_cls=False, use_rec=True):
            self.ocr_engine_calls.append(image.size)
            return [], None

        def locate_all(self, *args, **kwargs):
            del args, kwargs
            return []

    operator = FakeOperator()
    task = CurrencyWars(operator, 1)
    target = [None]

    task._get_character_in_area([(0.1, 0.2)], target, force=False, count_stars=True)

    assert [character.name if character is not None else None for character in target] == ["佩拉"]
    assert operator.ocr_calls == [CurrencyWars.CHARACTER_NAME_REGION]
    assert operator.ocr_engine_calls == []
