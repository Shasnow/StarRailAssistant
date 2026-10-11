"""CurrencyWars flow regression tests without importing GUI/runtime dependencies.

The loader removes application imports only and executes the production class.
Character definitions and pure logic are loaded afresh for each test, so their
shared state cannot leak between cases. All input, OCR and waits are fake.
"""
from __future__ import annotations

import ast
import atexit
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, mock_open, patch
import uuid


ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "tasks/currency_wars"

# One explicit-lifetime temporary root; each isolated task gets a private child.
_FLOW_SESSION_TEMP_ROOT = tempfile.TemporaryDirectory()
atexit.register(_FLOW_SESSION_TEMP_ROOT.cleanup)


class OperationBudgetExceeded(BaseException):
    """Escape even broad production exception handlers if a test spins."""


class NullLogger:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class ImageNames:
    def __getattr__(self, name):
        return name


class FakeBox:
    def __init__(self, left=0, top=0, width=1, height=1, source=""):
        self.left, self.top = left, top
        self.width, self.height, self.source = width, height, source

    @property
    def center(self):
        return self.left + self.width // 2, self.top + self.height // 2

    def distance(self, other):
        return sum((a - b) ** 2 for a, b in zip(self.center, other.center)) ** 0.5


class FakeExecutable:
    def __init__(self, operator):
        self.operator = operator
        self.settings = operator.settings


class FakeOperator:
    def __init__(self):
        self.settings = types.SimpleNamespace(
            General=types.SimpleNamespace(hotkeyF4="f4")
        )
        self.window_context = types.SimpleNamespace(width=1920, height=1080)
        self.stop_event = threading.Event()
        self.type = "Local"
        self.calls = []
        self.ocr_results = []
        self.on_press = None

    def record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        if len(self.calls) > 400:
            raise OperationBudgetExceeded("Flow exceeded 400 fake operations")

    def sleep(self, seconds):
        self.record("sleep", seconds)

    def ocr(self, *args, **kwargs):
        self.record("ocr", *args, **kwargs)
        return self.ocr_results

    def click_point(self, *args, **kwargs):
        self.record("click", *args, **kwargs)
        return True

    def click_box(self, *args, **kwargs):
        self.record("click_box", *args, **kwargs)
        return args[0] is not None if args else False

    def click_img(self, *args, **kwargs):
        self.record("click_img", *args, **kwargs)
        return False

    def press_key(self, key, *args, **kwargs):
        self.record("key", key, *args, **kwargs)
        if self.on_press:
            self.on_press(key)
        return True

    def drag_to(self, *args, **kwargs):
        self.record("drag", *args, **kwargs)
        return True

    def move_to(self, *args, **kwargs):
        self.record("move", *args, **kwargs)
        return True

    def locate(self, *args, **kwargs):
        self.record("locate", *args, **kwargs)
        return None

    def locate_all(self, *args, **kwargs):
        self.record("locate_all", *args, **kwargs)
        return None

    def locate_any(self, *args, **kwargs):
        self.record("locate_any", *args, **kwargs)
        return -1, None

    def wait_img(self, *args, **kwargs):
        self.record("wait_img", *args, **kwargs)
        return None

    def wait_any_img(self, *args, **kwargs):
        self.record("wait_any_img", *args, **kwargs)
        return -1, None

    def rectangle_detect(self, *args, **kwargs):
        self.record("rectangle", *args, **kwargs)
        return [FakeBox(left=x * 1920 - 70, top=599.6, width=140, height=140)
                for x in (0.3056, 0.3806, 0.4525, 0.5264, 0.6004, 0.6738)]

    def keys(self):
        return [args[0] for name, args, _ in self.calls if name == "key"]

    def drags(self):
        return [args for name, args, _ in self.calls if name == "drag"]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_isolated_task():
    prefix = "_currency_wars_flow_" + uuid.uuid4().hex
    names = [prefix + "_" + suffix
             for suffix in ("characters", "logic", "formation", "vision", "preparation", "layout", "session", "economy", "task", "shop_overlay", "policy", "equipment_policy", "shopping_batch")]
    try:
        characters = load_module(TASKS / "characters.py", names[0])
        logic = load_module(TASKS / "logic.py", names[1])
        formation = load_module(TASKS / "formation.py", names[2])
        vision = load_module(TASKS / "vision.py", names[3])
        preparation = load_module(TASKS / "preparation.py", names[4])
        layout = load_module(TASKS / "layout.py", names[5])
        session = load_module(TASKS / "session.py", names[6])
        economy = load_module(TASKS / "economy.py", names[7])
        shop_overlay = load_module(TASKS / "shop_overlay.py", names[9])
        policy = load_module(TASKS / "policy.py", names[10])
        equipment_policy = load_module(TASKS / "equipment_policy.py", names[11])
        shopping_batch = load_module(TASKS / "shopping_batch.py", names[12])
        module = types.ModuleType(names[8])
        module.__file__ = str(TASKS / "CurrencyWars.py")
        sys.modules[names[8]] = module
        namespace = module.__dict__
        namespace.update({
            "logger": NullLogger(),
            "Box": FakeBox,
            "Executable": FakeExecutable,
            "ErrorCode": ImageNames(),
            "SRAError": RuntimeError,
            "ThreadStoppedError": type("ThreadStoppedError", (RuntimeError,), {}),
            "CWIMG": ImageNames(), "IMG": ImageNames(), "DUIMG": ImageNames(),
        })
        namespace.update({
            key: value for key, value in vars(characters).items()
            if not key.startswith("_")
        })
        for helper in (logic, formation, vision, preparation, layout, session, economy, shop_overlay, policy, equipment_policy, shopping_batch):
            namespace.update({
                key: value for key, value in vars(helper).items()
                if not key.startswith("_")
            })
        namespace["_placement_areas"] = formation._placement_areas
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8-sig"))
        application_roots = ("SRACore", "tasks", "loguru")
        tree.body = [
            node for node in tree.body
            if not (
                isinstance(node, ast.ImportFrom)
                and (
                    node.level
                    or (node.module or "").split(".")[0] in application_roots
                )
            )
            and not (
                isinstance(node, ast.Import)
                and any(alias.name.split(".")[0] in application_roots
                        for alias in node.names)
            )
        ]
        exec(compile(tree, module.__file__, "exec"), namespace)
        # Every flow test owns a temporary checkpoint; never write task runtime.
        module._session_tempdir = _FLOW_SESSION_TEMP_ROOT
        checkpoint_path = Path(_FLOW_SESSION_TEMP_ROOT.name) / prefix / "current_run.json"
        namespace["SessionStore"] = lambda _path, **kwargs: session.SessionStore(
            checkpoint_path, **kwargs)
        return module, characters, logic, names
    except BaseException:
        for name in names:
            sys.modules.pop(name, None)
        raise


class CurrencyWarsFlowTests(unittest.TestCase):
    def setUp(self):
        self.module, self.characters, self.logic, self.module_names = (
            load_isolated_task()
        )
        self.addCleanup(
            lambda: [sys.modules.pop(name, None) for name in self.module_names]
        )
        self.operator = FakeOperator()
        self.task = self.module.CurrencyWars(self.operator, runtimes=1)
        self.task.is_running = True
        self.task.get_coins = Mock(return_value=50)
        self.task.get_level = Mock(return_value=5)
        self.task.handle_special_event = Mock()
        self.task.detect_silver_wolf_lv999 = Mock()
        # These decision tests supply card snapshots; panel I/O is covered by
        # test_currency_wars_shop_state with a stateful operator.
        self.task._set_shop_open = Mock(return_value=True)
        # Decision-only shop tests start on an authenticated ordinary preparation.
        # OCR/round tests replace this reader or explicitly clear the cached label.
        self.task._preparation_round = (2, 1)

    def character(self, name="灵砂"):
        return self.characters.Characters.get_character(name)

    def observe(self, area, index, character=None, *, state=None, stars=None):
        state = state or (
            self.logic.SlotState.KNOWN if character
            else self.logic.SlotState.EMPTY
        )
        observation = self.logic.SlotObservation(
            index, state, character=character,
            occupied=(True if state == self.logic.SlotState.KNOWN else
                      False if state == self.logic.SlotState.EMPTY else None),
            evidence="test observation", revision=1, stars=stars,
        )
        self.task._observations[area][index] = observation
        getattr(self.task, area + "_character")[index] = character
        return observation

    def empty_board(self):
        for area in ("on_field", "off_field", "in_hand"):
            for index in range(len(getattr(self.task, area + "_character"))):
                self.observe(area, index)
        self.task._layout_valid = True

    def configure_main_c(self):
        character = self.character()
        self.task.main_c = character.name
        self.task.main_c_search_level = 5
        self.task.main_c_first_fielded_confirmed = False
        self.task.strategy_characters = {character.name: 2}
        return character

    def shop(self, state, *cards):
        return self.logic.ShopObservation(state, cards=tuple(cards))

    def card(self, name="灵砂", slot=2):
        character = self.character(name)
        return self.logic.ShopCard(
            slot, character, self.task.store_area[slot], raw_text=name
        )

    def scan_sequence(self, *observations):
        values = iter(observations)
        self.task._scan_store = Mock(
            side_effect=lambda: next(
                values, self.shop(self.logic.ShopState.UNKNOWN)
            )
        )

    def prepare_sale(self, character=None):
        self.empty_board()
        character = character or self.character("佩拉")
        for index in range(8):
            self.observe("in_hand", index, character, stars=1)
        self.task._observe_slot = Mock(
            side_effect=lambda area, index, *args, **kwargs:
                self.task._observations[area][index]
        )
        return character

    def install_local_sale_board(self):
        """Model a sold source emptying while other bench coordinates stay put."""
        sold = set()

        def drag(from_x, from_y, to_x, to_y, **kwargs):
            self.operator.record("drag", from_x, from_y, to_x, to_y, **kwargs)
            self.assertEqual((to_x, to_y), (0.05, 0.86))
            sold.add(self.task.in_hand_area.index((from_x, from_y)))
            return True

        def observe(area, index, **kwargs):
            if area == "in_hand" and index in sold:
                return self.logic.SlotObservation(index, self.logic.SlotState.EMPTY,
                    occupied=False, evidence="confirmed local empty", revision=2)
            return self.task._observations[area][index]

        self.operator.drag_to = Mock(side_effect=drag)
        self.task._observe_slot = Mock(side_effect=observe)
        self.task.get_in_hand_area = Mock(side_effect=AssertionError("unexpected full bench scan"))
        return sold

    def configure_future_sale_requirements(self, *, gate=None):
        self.task.strategy_characters = {"灵砂": 2, "佩拉": 2}
        self.task.formation_config = self.module.FormationConfig({}, {}, {}, (
            self.module.FormationStage("early", 0, ("灵砂",), ()),
            self.module.FormationStage("future", 6, ("灵砂",), ("佩拉",)),
        ), gate)

    def test_main_c_gate_blocks_both_experience_branches(self):
        for minimum in (3, 7):
            with self.subTest(min_level=minimum):
                self.operator.calls.clear()
                self.empty_board()
                self.configure_main_c()
                self.task.min_level = minimum
                self.task.mid_level = 8
                self.task.min_coins = 40
                self.task.get_coins = Mock(return_value=50)
                self.scan_sequence(
                    self.shop(self.logic.ShopState.EMPTY),
                    self.shop(self.logic.ShopState.EMPTY),
                    self.shop(self.logic.ShopState.UNKNOWN),
                )
                self.task.shopping()
                self.assertNotIn("f", self.operator.keys())

    def test_below_search_level_still_allows_upgrade(self):
        self.configure_main_c()
        self.assertTrue(self.task._can_upgrade(4))

    def test_unknown_level_does_not_unlock_main_c_gate(self):
        self.configure_main_c()
        self.assertFalse(self.task._can_upgrade(None))
        self.assertFalse(self.task.main_c_first_fielded_confirmed)

    def test_bench_ownership_and_shared_flag_do_not_unlock(self):
        self.empty_board()
        character = self.configure_main_c()
        character.is_placed = True
        self.observe("in_hand", 0, character, stars=1)
        self.assertFalse(self.task._confirm_main_c_fielded())
        self.assertFalse(self.task._can_upgrade(5))

    def test_confirmed_front_field_unlocks_once_per_game(self):
        self.empty_board()
        character = self.configure_main_c()
        self.observe("on_field", 0, character, stars=1)
        self.assertTrue(self.task._confirm_main_c_fielded())
        self.assertTrue(self.task._can_upgrade(5))
        self.observe("on_field", 0, state=self.logic.SlotState.UNKNOWN)
        self.assertTrue(self.task._can_upgrade(5))
        self.assertTrue(self.task.main_c_first_fielded_confirmed)

    def test_confirmed_legal_back_field_also_unlocks(self):
        self.empty_board()
        character = self.configure_main_c()
        character.position = self.characters.Positioning.OffField
        self.observe("off_field", 0, character, stars=1)
        self.assertTrue(self.task._confirm_main_c_fielded())
        self.assertTrue(self.task._can_upgrade(5))

    def test_illegal_main_c_position_does_not_unlock(self):
        self.empty_board()
        character = self.configure_main_c()
        character.position = self.characters.Positioning.OffField
        self.observe("on_field", 0, character, stars=1)
        self.assertFalse(self.task._confirm_main_c_fielded())

    def test_legacy_strategy_without_main_c_remains_unrestricted(self):
        strategy = {
            "title": "legacy", "on_field": {"灵砂": 2},
            "off_field": {}, "min_level": 7, "mid_level": 8,
        }
        with patch("builtins.open", mock_open(read_data=json.dumps(strategy))):
            self.task.load_strategy("legacy.json")
        self.assertIsNone(self.task.main_c)
        self.assertTrue(self.task._can_upgrade(5))

    def test_loading_main_c_strategy_sets_gate_and_default_level(self):
        strategy = {
            "title": "main c", "on_field": {"灵砂": 2},
            "off_field": {}, "main_c": "灵砂",
        }
        with patch("builtins.open", mock_open(read_data=json.dumps(strategy))):
            self.task.load_strategy("main_c.json")
        self.assertEqual(self.task.main_c, "灵砂")
        self.assertEqual(self.task.main_c_search_level, 5)
        self.assertFalse(self.task._can_upgrade(5))

    def test_reset_clears_run_state_but_preserves_strategy(self):
        self.empty_board()
        character = self.configure_main_c()
        character.stars = 3
        character.is_placed = True
        self.observe("on_field", 0, character, stars=3)
        self.task.is_continue = True
        self.task.main_c_first_fielded_confirmed = True
        self.task.max_team_size = 9
        self.task.off_field_area.append((0.7, 0.62))
        self.task.off_field_character.append(None)
        self.task.reset_character()
        self.assertEqual(character.stars, 0)
        self.assertFalse(character.is_placed)
        self.assertFalse(self.task.is_continue)
        self.assertFalse(self.task.main_c_first_fielded_confirmed)
        self.assertEqual(self.task.max_team_size, 3)
        self.assertEqual(len(self.task.off_field_area), 6)
        self.assertEqual(self.task.strategy_characters, {"灵砂": 2})
        self.assertEqual(self.task.main_c, "灵砂")

    def test_locked_bench_is_not_sold(self):
        character = self.prepare_sale()
        character.is_locked = True
        self.task.sell_character()
        self.assertEqual(self.operator.drags(), [])

    def test_numeric_pollution_is_never_sold(self):
        character = self.characters.Characters.new_character("1")
        character.is_locked = False
        self.prepare_sale(character)
        self.task.sell_character()
        self.assertEqual(self.operator.drags(), [])

    def test_protected_targets_are_not_force_sold(self):
        character = self.prepare_sale()
        self.task.strategy_characters = {character.name: 3}
        character.stars = 1
        self.task.sell_character()
        self.assertEqual(self.operator.drags(), [])

    def test_unknown_bench_is_not_treated_as_sellable_occupancy(self):
        self.task.sell_character()
        self.assertEqual(self.operator.drags(), [])

    def test_sale_reserves_future_root_front_even_with_backend_default(self):
        self.empty_board()
        self.task.max_team_size = 1
        stage = self.module.FormationStage("early", 0, ("姬子·启行",), ())
        self.task.formation_config = self.module.FormationConfig({}, {}, {}, (stage,),
            purchase_targets={"花火": 2}, root_positions={"花火": ("on_field",)})
        sparkle = self.character("花火")
        self.assertEqual(sparkle.positioning, self.characters.Positioning.OffField)
        self.observe("in_hand", 0, sparkle, stars=1)
        self.assertEqual(self.task._sale_interim_reserve({"花火": 2}), {0})

    def test_sale_reserve_stage_area_overrides_root_front(self):
        self.empty_board()
        self.task.max_team_size = 1
        stage = self.module.FormationStage("early", 0, ("姬子·启行",), ("花火",))
        self.task.formation_config = self.module.FormationConfig({}, {}, {}, (stage,),
            purchase_targets={"花火": 2}, root_positions={"花火": ("on_field",)})
        self.observe("in_hand", 0, self.character("花火"), stars=1)
        # A configured back-line unit cannot supply the missing front line.
        self.assertEqual(self.task._sale_interim_reserve({"花火": 2}), set())

    def test_sale_reserve_fallback_uses_character_configured_position(self):
        self.empty_board()
        self.task.max_team_size = 1
        stage = self.module.FormationStage("early", 0, ("姬子·启行",), ())
        self.task.formation_config = self.module.FormationConfig({}, {}, {}, (stage,))
        sparkle = self.character("花火")
        sparkle.position = self.characters.Positioning.OnField
        self.observe("in_hand", 0, sparkle, stars=1)
        self.assertEqual(self.task._sale_interim_reserve({}), {0})

    def test_indeterminate_sale_stops_without_repeating_drag(self):
        self.prepare_sale()
        self.task._population_current = 0
        self.task._confirm_sale = Mock(
            return_value=self.logic.ActionResult.INDETERMINATE
        )
        self.task.sell_character()
        self.assertEqual(len(self.operator.drags()), 1)

    def test_failed_sale_is_bounded_without_forcing_other_targets(self):
        character = self.prepare_sale()
        self.task._population_current = 0
        self.task._confirm_sale = Mock(
            return_value=self.logic.ActionResult.FAILED
        )
        self.task.sell_character()
        self.assertGreater(len(self.operator.drags()), 0)
        self.assertLessEqual(len(self.operator.drags()), 3)
        self.assertEqual(
            {tuple(drag[:2]) for drag in self.operator.drags()},
            {self.task.in_hand_area[0]},
        )
        self.assertIs(self.task.in_hand_character[0], character)

    def test_sale_of_duplicate_keeps_field_character_placed(self):
        character = self.prepare_sale(self.character())
        self.task.strategy_characters = {character.name: 2}
        character.stars = 2
        character.is_placed = True
        self.observe("on_field", 0, character, stars=2)

        def confirmed(index, sold_character, before_coins):
            self.assertIs(sold_character, character)
            self.observe("in_hand", index)
            return self.logic.ActionResult.CONFIRMED

        self.task._confirm_sale = Mock(side_effect=confirmed)
        result = self.task.sell_character()
        self.assertEqual(result.confirmed, 8)
        self.assertTrue(character.is_placed)
        self.assertEqual(character.stars, 2)

    def test_sparse_non_strategy_bench_is_cleaned_without_full_scans(self):
        self.empty_board()
        self.task.max_team_size = 1
        self.observe("on_field", 0, self.character(), stars=1)
        self.task._population_current = 1
        self.observe("in_hand", 0, self.character("佩拉"), stars=1)
        self.observe("in_hand", 4, self.character("椒丘"), stars=1)
        sold = self.install_local_sale_board()
        result = self.task.sell_character()
        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.attempted, result.confirmed), (2, 2))
        self.assertEqual(sold, {0, 4})
        self.assertEqual([call.args[1] for call in self.task._observe_slot.call_args_list], [0, 0, 4, 4])
        self.task.get_in_hand_area.assert_not_called()

    def test_known_non_strategy_source_can_be_sold_among_unknown_bench_slots(self):
        # The bench remains unknown except for the source; the deployed roster
        # must be positively known before its filler can be declared surplus.
        for area in ("on_field", "off_field"):
            for index in range(len(self.task._observations[area])):
                self.observe(area, index)
        self.task.max_team_size = 1
        self.task._bench_full = True
        self.observe("on_field", 0, self.character(), stars=1)
        self.task._population_current = 1
        self.observe("in_hand", 2, self.character("佩拉"), stars=1)
        sold = self.install_local_sale_board()
        result = self.task.sell_character()
        self.assertEqual(result.confirmed, 1)
        self.assertEqual(sold, {2})
        self.assertEqual(self.task.in_hand_unknown_count, 8)
        self.assertFalse(self.task._bench_full)
        self.task.get_in_hand_area.assert_not_called()

    def test_future_stage_upgrade_copies_are_retained_during_sparse_cleanup(self):
        self.empty_board()
        self.configure_future_sale_requirements()
        self.task.max_team_size = 1
        self.observe("on_field", 0, self.character(), stars=2)
        self.task._population_current = 1
        material = self.character("佩拉")
        self.observe("in_hand", 0, material, stars=1)
        self.observe("in_hand", 1, material, stars=1)
        self.observe("in_hand", 3, self.character("椒丘"), stars=1)
        sold = self.install_local_sale_board()
        self.assertEqual(self.task.sell_character().confirmed, 1)
        self.assertEqual(sold, {3})
        self.assertIs(self.task.in_hand_character[0], material)
        self.assertIs(self.task.in_hand_character[1], material)

    def test_future_gate_star_requirement_protects_otherwise_completed_duplicates(self):
        self.empty_board()
        self.configure_future_sale_requirements(gate=self.module.UpgradeGate(6, fielded={"佩拉": 3}))
        self.task.max_team_size = 2
        self.observe("on_field", 0, self.character(), stars=2)
        material = self.character("佩拉")
        self.observe("off_field", 0, material, stars=2)
        self.observe("in_hand", 0, material, stars=1)
        self.task.sell_character()
        self.assertEqual(self.operator.drags(), [])
        self.assertIs(self.task.in_hand_character[0], material)

    def test_future_gate_price_requirement_retains_copies_until_price_is_confirmed(self):
        self.empty_board()
        self.configure_future_sale_requirements(gate=self.module.UpgradeGate(6, prices={"佩拉": 4}))
        self.task.max_team_size = 2
        self.task._observed_prices["佩拉"] = 2
        self.observe("on_field", 0, self.character(), stars=2)
        material = self.character("佩拉")
        self.observe("off_field", 0, material, stars=2)
        self.observe("in_hand", 0, material, stars=1)
        self.task.sell_character()
        self.assertEqual(self.operator.drags(), [])
        self.task._observed_prices["佩拉"] = 4
        sold = self.install_local_sale_board()
        self.assertEqual(self.task.sell_character().confirmed, 1)
        self.assertEqual(sold, {0})

    def test_main_c_copy_is_not_sold_before_first_fielding_is_confirmed(self):
        self.empty_board()
        self.task.max_team_size = 1
        self.observe("on_field", 0, self.character(), stars=1)
        main_c = self.character("佩拉")
        self.task.main_c = main_c.name
        self.task.main_c_first_fielded_confirmed = False
        self.observe("in_hand", 0, main_c, stars=1)
        self.task.sell_character()
        self.assertEqual(self.operator.drags(), [])

    def test_unknown_field_keeps_all_temporary_bench_units(self):
        starter = self.character()
        self.observe("in_hand", 0, starter, stars=1)
        self.observe("in_hand", 1, self.character("飞霄"), stars=1)
        self.observe("in_hand", 2, self.character("佩拉"), stars=1)
        sold = self.install_local_sale_board()
        result = self.task.sell_character()
        self.assertEqual((result.attempted, result.confirmed), (0, 0))
        self.assertEqual(sold, set())
        self.assertEqual(self.operator.drags(), [])
        self.assertIs(self.task.in_hand_character[0], starter)
        self.assertEqual([char.name for char in self.task.in_hand_character[:3]],
                         [starter.name, "飞霄", "佩拉"])
        self.task._observe_slot.assert_not_called()

    def test_needed_interim_unit_for_reliable_open_population_is_not_sold(self):
        self.empty_board()
        self.task.max_team_size = 2
        self.observe("on_field", 0, self.character(), stars=1)
        self.task._population_current = 1
        interim = self.character("佩拉")
        self.observe("in_hand", 0, interim, stars=1)
        self.task.sell_character()
        self.assertEqual(self.operator.drags(), [])
        self.assertIs(self.task.in_hand_character[0], interim)

    def test_active_bench_cleanup_keeps_the_non_strategy_field_starter(self):
        self.empty_board()
        self.task.max_team_size = 2
        self.observe("on_field", 0, self.character(), stars=1)
        starter = self.character("佩拉")
        starter.is_placed, starter.stars = True, 1
        self.observe("off_field", 0, starter, stars=1)
        self.task._population_current = 2
        self.observe("in_hand", 3, starter, stars=1)
        sold = self.install_local_sale_board()
        self.assertEqual(self.task.sell_character().confirmed, 1)
        self.assertEqual(sold, {3})
        self.assertIs(self.task.off_field_character[0], starter)
        self.assertTrue(starter.is_placed)
        self.assertEqual(starter.stars, 1)

    def test_unreliable_known_source_is_not_used_for_active_sale(self):
        self.empty_board()
        self.task.max_team_size = 1
        self.observe("on_field", 0, self.character(), stars=1)
        self.task._population_current = 1
        material = self.character("佩拉")
        self.observe("in_hand", 0, material, stars=1)
        self.task._observations["in_hand"][0] = self.logic.SlotObservation(
            0, self.logic.SlotState.KNOWN, character=material, occupied=True,
            evidence="pending_drag", stars=1)
        self.task.sell_character()
        self.assertEqual(self.operator.drags(), [])

    def test_sparse_sale_rechecks_source_identity_before_dragging(self):
        self.empty_board()
        self.task.max_team_size = 1
        self.observe("on_field", 0, self.character(), stars=1)
        self.task._population_current = 1
        self.observe("in_hand", 0, self.character("佩拉"), stars=1)
        replacement = self.character("椒丘")
        self.task._observe_slot = Mock(return_value=self.logic.SlotObservation(
            0, self.logic.SlotState.KNOWN, character=replacement, occupied=True,
            evidence="name_match", stars=1))
        result = self.task.sell_character()
        self.assertEqual(result.reason, "source_changed")
        self.assertEqual(self.operator.drags(), [])
        self.assertIs(self.task.in_hand_character[0], replacement)

    def test_changed_source_after_sale_triggers_one_recalibration_before_next_action(self):
        self.empty_board()
        self.task.max_team_size = 1
        self.observe("on_field", 0, self.character(), stars=1)
        self.task._population_current = 1
        junk = self.character("佩拉")
        self.observe("in_hand", 0, junk, stars=1)
        self.observe("in_hand", 4, self.character("椒丘"), stars=1)
        before = self.task._observations["in_hand"][0]
        shifted = self.logic.SlotObservation(0, self.logic.SlotState.KNOWN,
            character=self.character("飞霄"), occupied=True, evidence="name_match", stars=1)
        self.task._observe_slot = Mock(side_effect=[before, shifted])
        self.task.get_coins = Mock(side_effect=[50, 52])

        def recalibrate_bench(*args):
            for index in range(len(self.task.in_hand_area)):
                self.observe("in_hand", index)

        self.task.get_in_hand_area = Mock(side_effect=recalibrate_bench)
        result = self.task.sell_character()
        self.assertEqual(result.confirmed, 1)
        self.assertEqual(len(self.operator.drags()), 1)
        self.task.get_in_hand_area.assert_called_once_with(True)

    def test_unknown_post_sale_evidence_stops_sparse_cleanup_without_repeating_drag(self):
        self.empty_board()
        self.task.max_team_size = 1
        self.observe("on_field", 0, self.character(), stars=1)
        self.task._population_current = 1
        self.observe("in_hand", 0, self.character("佩拉"), stars=1)
        before = self.task._observations["in_hand"][0]
        unknown = self.logic.SlotObservation(0, self.logic.SlotState.UNKNOWN, evidence="unrecognized")
        self.task._observe_slot = Mock(side_effect=[before, unknown, unknown])
        self.task.get_coins = Mock(side_effect=[50, 52, 52])
        self.task.get_in_hand_area = Mock()
        result = self.task.sell_character()
        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual((result.attempted, result.confirmed), (1, 0))
        self.assertEqual(len(self.operator.drags()), 1)
        self.task.get_in_hand_area.assert_not_called()

    def test_stop_during_active_sale_releases_pointer_and_prevents_confirmation(self):
        self.empty_board()
        self.task.max_team_size = 1
        self.observe("on_field", 0, self.character(), stars=1)
        self.task._population_current = 1
        self.observe("in_hand", 0, self.character("佩拉"), stars=1)
        self.task._observe_slot = Mock(side_effect=lambda area, index, **kwargs:
                                     self.task._observations[area][index])
        self.task._release_pointer_unconditionally = Mock(return_value=True)
        self.task._confirm_sale = Mock()

        def stop_during_drag(*args, **kwargs):
            self.operator.record("drag", *args, **kwargs)
            self.operator.stop_event.set()
            return True

        self.operator.drag_to = Mock(side_effect=stop_during_drag)
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.sell_character()
        self.task._release_pointer_unconditionally.assert_called_once()
        self.task._confirm_sale.assert_not_called()

    def test_real_store_scan_maps_sparse_cards_to_physical_slots(self):
        def token(slot, text):
            x = (self.task.store_area[slot][0] - 0.19) * 1920
            return (
                [[x - 10, 0], [x + 10, 0], [x + 10, 16], [x - 10, 16]],
                text, 0.99,
            )

        self.operator.ocr_results = [
            token(4, "佩拉"), token(2, "灵砂")
        ]
        result = self.task._scan_store()
        self.assertEqual(result.state, self.logic.ShopState.READY)
        self.assertEqual(
            {card.slot_index for card in result.cards}, {2, 4}
        )
        for card in result.cards:
            self.assertEqual(card.target, self.task.store_area[card.slot_index])

    def test_full_store_never_refreshes_or_buys_experience(self):
        self.scan_sequence(self.shop(self.logic.ShopState.FULL))
        result = self.task.shopping()
        self.assertEqual(result.reason, "full")
        self.assertNotIn("d", self.operator.keys())
        self.assertNotIn("f", self.operator.keys())

    def test_unknown_store_never_refreshes_or_buys_experience(self):
        self.scan_sequence(self.shop(self.logic.ShopState.UNKNOWN))
        self.task.shopping()
        self.assertNotIn("d", self.operator.keys())
        self.assertNotIn("f", self.operator.keys())

    def test_post_purchase_balance_prevents_extra_refresh(self):
        card = self.card()
        self.task.strategy_characters = {card.character.name: 2}
        self.task.min_level = 3
        self.task.mid_level = 3
        self.task.min_coins = 40
        balances = iter([45, 39])
        self.task.get_coins = Mock(
            side_effect=lambda: next(balances, 39)
        )
        self.scan_sequence(
            self.shop(self.logic.ShopState.READY, card),
            self.shop(self.logic.ShopState.EMPTY),
        )
        self.task._confirm_purchase = Mock(
            return_value=self.logic.ActionResult.CONFIRMED
        )
        result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertGreaterEqual(self.task.get_coins.call_count, 2)
        self.assertNotIn("d", self.operator.keys())

    def test_confirmed_purchase_does_not_take_no_purchase_upgrade_branch(self):
        card = self.card()
        self.task.strategy_characters = {card.character.name: 2}
        self.task.min_level = 3
        self.task.mid_level = 8
        self.task.min_coins = 40
        self.scan_sequence(
            self.shop(self.logic.ShopState.READY, card),
            self.shop(self.logic.ShopState.EMPTY),
            self.shop(self.logic.ShopState.EMPTY),
            self.shop(self.logic.ShopState.UNKNOWN),
        )
        self.task._confirm_purchase = Mock(
            return_value=self.logic.ActionResult.CONFIRMED
        )
        result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertIn("d", self.operator.keys())
        self.assertNotIn("f", self.operator.keys())

    def test_indeterminate_purchase_is_not_treated_as_no_purchase(self):
        card = self.card()
        self.task.strategy_characters = {card.character.name: 2}
        self.task.min_level = 3
        self.task.mid_level = 8
        self.scan_sequence(self.shop(self.logic.ShopState.READY, card))
        self.task._confirm_purchase = Mock(
            return_value=self.logic.ActionResult.INDETERMINATE
        )
        result = self.task.shopping()
        self.assertEqual(result.attempted_purchases, 1)
        self.assertEqual(result.confirmed_purchases, 0)
        self.assertNotIn("f", self.operator.keys())
        self.assertNotIn("d", self.operator.keys())

    def test_main_c_purchase_returns_for_placement_without_unlocking(self):
        self.empty_board()
        self.configure_main_c()
        self.task.min_level = 7
        self.task.mid_level = 8
        card = self.card()
        self.scan_sequence(self.shop(self.logic.ShopState.READY, card))
        self.task._confirm_purchase = Mock(
            return_value=self.logic.ActionResult.CONFIRMED
        )
        result = self.task.shopping()
        self.assertEqual(result.reason, "main_c_placement")
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertFalse(self.task.main_c_first_fielded_confirmed)
        self.assertNotIn("f", self.operator.keys())
        self.assertNotIn("d", self.operator.keys())



    def install_board_observer(self, unknown_source=None):
        """Model drag effects separately from the task's cached observations."""
        areas = ("on_field", "off_field", "in_hand")
        board = {
            area: list(getattr(self.task, area + "_character")) for area in areas
        }
        stars = {area: [obs.stars for obs in self.task._observations[area]] for area in areas}
        coordinates = {
            point: (area, index)
            for area in areas
            for index, point in enumerate(getattr(self.task, area + "_area"))
        }

        def drag(from_x, from_y, to_x, to_y, **kwargs):
            self.operator.record("drag", from_x, from_y, to_x, to_y, **kwargs)
            source_area, source_index = coordinates[(from_x, from_y)]
            target_area, target_index = coordinates[(to_x, to_y)]
            source = board[source_area][source_index]
            board[source_area][source_index] = board[target_area][target_index]
            board[target_area][target_index] = source
            stars[source_area][source_index], stars[target_area][target_index] = (
                stars[target_area][target_index], stars[source_area][source_index])
            return True

        def observe(area, index, *args, **kwargs):
            if (area, index) == unknown_source:
                return self.logic.SlotObservation(
                    index, self.logic.SlotState.UNKNOWN,
                    evidence="test incomplete observation",
                )
            char = board[area][index]
            return self.logic.SlotObservation(
                index,
                self.logic.SlotState.KNOWN if char else self.logic.SlotState.EMPTY,
                character=char, occupied=char is not None,
                evidence="test observed board", stars=stars[area][index] if char else None,
            )

        self.operator.drag_to = Mock(side_effect=drag)
        self.task._observe_slot = Mock(side_effect=observe)
        return board

    def test_back_field_main_c_is_deployed_before_front_field_teammate(self):
        self.empty_board()
        front = self.character("灵砂")
        main = self.character("佩拉")
        teammate = self.character("希儿")
        main.position = self.characters.Positioning.OffField
        main.priority, teammate.priority = 1, 99
        self.task.main_c = main.name
        self.task.main_c_search_level = 5
        self.task.strategy_characters = {main.name: 2, teammate.name: 2}
        self.task.max_team_size = 2
        self.observe("on_field", 0, front, stars=1)
        front.is_placed = True
        self.observe("in_hand", 0, teammate, stars=1)
        self.observe("in_hand", 1, main, stars=1)
        self.install_board_observer()
        self.task.place_character()
        first_drag = self.operator.drags()[0]
        self.assertEqual(tuple(first_drag[:2]), self.task.in_hand_area[1])
        self.assertEqual(tuple(first_drag[2:4]), self.task.off_field_area[0])
        self.assertTrue(self.task.main_c_first_fielded_confirmed)
        self.assertLessEqual(self.task.current_team_size, 2)

    def test_reserves_population_when_front_teammate_would_strand_back_main(self):
        self.empty_board()
        main = self.character("佩拉")
        main.position = self.characters.Positioning.OffField
        self.task.main_c = main.name
        self.task.main_c_search_level = 5
        self.task.strategy_characters = {main.name: 2, "希儿": 2}
        self.task.max_team_size = 3
        for index, name in enumerate(("灵砂", "景元")):
            character = self.character(name)
            self.observe("on_field", index, character, stars=1)
            character.is_placed = True
        self.observe("in_hand", 0, self.character("希儿"), stars=1)
        self.install_board_observer()
        self.task.place_character()
        self.assertEqual(self.operator.drags(), [])
        self.assertEqual(self.task.current_team_size, 2)
        self.assertFalse(self.task.main_c_first_fielded_confirmed)

    def test_indeterminate_swap_with_unknown_source_does_not_double_count_population(self):
        self.empty_board()
        character = self.character("爻光")
        self.observe("on_field", 0, character, stars=1)
        character.is_placed = True
        self.install_board_observer(unknown_source=("on_field", 0))
        self.assertFalse(self.task.swap_character_between_areas(
            "on_field", 0, "off_field", 0
        ))
        self.assertEqual(self.task._last_move_result.status, self.module.MoveStatus.INDETERMINATE)
        self.assertEqual(self.task.current_team_size, 1)
        self.assertIsNone(self.task.on_field_character[0])
        self.assertIs(self.task.off_field_character[0], character)
        self.assertEqual(
            self.task._observations["on_field"][0].state,
            self.logic.SlotState.UNKNOWN,
        )
        self.assertTrue(self.task._placement_pending)
        self.assertTrue(character.is_placed)

    def test_drag_without_target_confirmation_does_not_unlock_main_c(self):
        self.empty_board()
        character = self.configure_main_c()
        self.observe("in_hand", 0, character, stars=1)
        self.install_board_observer(unknown_source=("on_field", 0))
        self.assertFalse(self.task.swap_character_between_areas(
            "in_hand", 0, "on_field", 0
        ))
        self.assertEqual(len(self.operator.drags()), 1)
        self.assertFalse(self.task.main_c_first_fielded_confirmed)
        self.assertFalse(self.task._can_upgrade(5))

    def test_strategy_reload_invalidates_field_evidence_before_unlocking(self):
        self.empty_board()
        character = self.configure_main_c()
        self.observe("on_field", 0, character, stars=1)
        self.assertTrue(self.task._confirm_main_c_fielded())
        strategy = {
            "on_field": {"灵砂": 2}, "off_field": {},
            "main_c": "灵砂", "main_c_search_level": 5,
        }
        with patch("builtins.open", mock_open(read_data=json.dumps(strategy))):
            self.task.load_strategy("reload.json")
        self.assertIs(self.task.on_field_character[0], character)
        self.assertEqual(self.task.current_team_size, 1)
        self.assertTrue(self.task._placement_pending)
        self.assertFalse(self.task.main_c_first_fielded_confirmed)
        self.assertFalse(self.task._can_upgrade(5))
        self.observe("on_field", 0, character, stars=1)
        self.assertTrue(self.task._can_upgrade(5))

    def test_level_rechecked_after_refresh_cannot_bypass_main_c_gate(self):
        self.empty_board()
        self.configure_main_c()
        self.task.min_level = 3
        self.task.mid_level = 8
        self.task.min_coins = 40
        levels = iter([4, 5])
        self.task.get_level = Mock(side_effect=lambda: next(levels, 5))
        self.scan_sequence(
            self.shop(self.logic.ShopState.EMPTY),
            self.shop(self.logic.ShopState.EMPTY),
            self.shop(self.logic.ShopState.UNKNOWN),
        )
        self.task.shopping()
        self.assertIn("d", self.operator.keys())
        self.assertNotIn("f", self.operator.keys())
        self.assertGreaterEqual(self.task.get_level.call_count, 2)

    def test_experience_purchase_invalidates_real_level_cache(self):
        self.task.get_level = self.module.CurrencyWars.get_level.__get__(
            self.task, type(self.task)
        )
        self.operator.ocr_results = [([], "Lv.4", 0.99)]
        self.assertEqual(self.task.get_level(), 4)
        self.assertEqual(self.task.get_level(), 4)
        self.assertEqual(sum(name == "ocr" for name, _, _ in self.operator.calls), 1)
        self.assertTrue(self.task._buy_experience(4))
        self.operator.ocr_results = [([], "Lv.5", 0.99)]
        self.assertEqual(self.task.get_level(), 5)
        self.assertEqual(sum(name == "ocr" for name, _, _ in self.operator.calls), 2)

    def test_coin_gain_with_unknown_slot_cannot_confirm_sale(self):
        character = self.character("佩拉")
        self.task._sale_source_stars = 1
        self.task.get_coins = Mock(return_value=50 + character.cost)
        self.task._observe_slot = Mock(return_value=self.logic.SlotObservation(
            0, self.logic.SlotState.UNKNOWN, evidence="unrecognized"
        ))
        self.assertEqual(
            self.task._confirm_sale(0, character, 50),
            self.logic.ActionResult.INDETERMINATE,
        )

    def test_coin_gain_with_unchanged_same_name_cannot_confirm_sale(self):
        character = self.character("佩拉")
        self.task._sale_source_stars = 1
        self.task.get_coins = Mock(return_value=50 + character.cost)
        self.task._observe_slot = Mock(return_value=self.logic.SlotObservation(
            0, self.logic.SlotState.KNOWN, character=character,
            occupied=True, evidence="same name", stars=1,
        ))
        self.assertEqual(
            self.task._confirm_sale(0, character, 50),
            self.logic.ActionResult.INDETERMINATE,
        )

    def test_start_retry_uses_real_do_while_semantics(self):
        source = ROOT / "SRACore" / "operators" / "ioperator.py"
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        cls = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef) and node.name == "IOperator")
        method = next(node for node in cls.body
                      if isinstance(node, ast.FunctionDef) and node.name == "do_while")
        method.decorator_list = []
        namespace = {
            "time": types.SimpleNamespace(sleep=self.operator.sleep),
            "Callable": self.module.Callable, "Any": object,
        }
        exec(compile(ast.Module(body=[method], type_ignores=[]),
                     str(source), "exec"), namespace)
        self.operator.do_while = namespace["do_while"]
        for label, observations, success, clicks in (
            ("logo appears after first click", [FakeBox()], True, 1),
            ("logo appears after retry", [None, FakeBox()], True, 2),
            ("logo never appears", [None], False, 11),
        ):
            with self.subTest(label=label):
                self.operator.calls.clear()
                self.operator.wait_any_img = Mock(
                    side_effect=[(0, FakeBox()), (0, FakeBox())]
                )
                values = iter(observations)
                self.operator.locate = Mock(
                    side_effect=lambda *args, **kwargs:
                        next(values, observations[-1])
                )
                self.task._enter_new_game = Mock(return_value=True)
                self.assertEqual(self.task._enter_from_start_page(), success)
                self.assertEqual(
                    sum(name == "click_box" for name, _, _ in self.operator.calls),
                    clicks,
                )
                self.assertEqual(self.task._enter_new_game.call_count, int(success))



    def test_equipment_inputs_are_bounded_without_claiming_confirmed_effects(self):
        self.empty_board()
        character = self.character()
        self.task.strategy_characters = {character.name: 2}
        observation = self.observe("on_field", 0, character, stars=1)
        self.task._observe_slot = Mock(return_value=observation)
        self.operator.locate = Mock(return_value=FakeBox(source="recommend"))
        self.operator.locate_any = Mock(return_value=(0, FakeBox(source="equip")))
        self.operator.click_box = Mock(return_value=True)
        for _ in range(5):
            self.task._get_character_in_area(self.task.on_field_area[:1],
                self.task.on_field_character, force=True, equip=True, count_stars=True)
        self.assertEqual(self.operator.click_box.call_count, 4)
        self.assertNotIn(character.name, self.task._equipment_checked)
        self.task._invalidate_equipment_resources("new_reward")
        self.task._get_character_in_area(self.task.on_field_area[:1],
            self.task.on_field_character, force=True, equip=True, count_stars=True)
        self.assertEqual(self.operator.click_box.call_count, 6)


    def test_unknown_level_can_buy_verified_affordable_target_without_d_or_f(self):
        self.task.get_level = Mock(return_value=None)
        character = self.character("灵砂")
        self.task.strategy_characters = {character.name: 2}
        card = self.logic.ShopCard(
            2, character, self.task.store_area[2], raw_text=character.name, price=2
        )
        self.scan_sequence(self.shop(self.logic.ShopState.READY, card))
        self.task._confirm_purchase = Mock(
            return_value=self.logic.ActionResult.CONFIRMED
        )
        result = self.task.shopping()
        self.assertEqual(result.attempted_purchases, 1)
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertNotIn("d", self.operator.keys())
        self.assertNotIn("f", self.operator.keys())

    def test_unknown_level_and_unknown_price_cannot_buy(self):
        self.task.get_level = Mock(return_value=None)
        card = self.card()
        self.task.strategy_characters = {card.character.name: 2}
        self.scan_sequence(self.shop(self.logic.ShopState.READY, card))
        self.task._confirm_purchase = Mock()
        result = self.task.shopping()
        self.assertEqual(result.attempted_purchases, 0)
        self.task._confirm_purchase.assert_not_called()
        self.assertNotIn("d", self.operator.keys())
        self.assertNotIn("f", self.operator.keys())

    def test_unknown_coins_cannot_buy_even_with_known_card_price(self):
        self.task.get_coins = Mock(return_value=None)
        character = self.character("灵砂")
        self.task.strategy_characters = {character.name: 2}
        card = self.logic.ShopCard(
            2, character, self.task.store_area[2], raw_text=character.name, price=2
        )
        self.scan_sequence(self.shop(self.logic.ShopState.READY, card))
        self.task._confirm_purchase = Mock()
        result = self.task.shopping()
        self.assertEqual(result.attempted_purchases, 0)
        self.task._confirm_purchase.assert_not_called()
        self.assertNotIn("d", self.operator.keys())
        self.assertNotIn("f", self.operator.keys())

    def test_configured_event_keyword_mismatch_never_picks_last_option(self):
        self.operator.ocr_boxes = Mock(
            return_value=[FakeBox(source="数据拷贝仪"), FakeBox(source="其他伙伴")]
        )
        self.operator.click_box = Mock(return_value=True)
        self.operator.click_img = Mock(return_value=True)
        result = self.task._handle_selection_event(
            (0.22, 0.34, 0.85, 0.4), "银狼"
        )
        self.assertFalse(result)
        self.operator.click_box.assert_not_called()
        self.operator.click_img.assert_not_called()
        self.assertLessEqual(self.operator.ocr_boxes.call_count, 3)

    def test_failed_event_option_click_does_not_press_confirmation(self):
        self.operator.ocr_boxes = Mock(
            return_value=[FakeBox(source="数据拷贝仪"), FakeBox(source="银狼LV.999")]
        )
        self.operator.click_box = Mock(return_value=False)
        self.operator.click_img = Mock(return_value=True)
        result = self.task._handle_selection_event(
            (0.22, 0.34, 0.85, 0.4), "银狼"
        )
        self.assertFalse(result)
        self.operator.click_img.assert_not_called()

    def test_known_empty_board_clears_missing_main_c_purchase_pending(self):
        self.empty_board()
        character = self.configure_main_c()
        self.task._purchase_pending_names.add(character.name)
        self.task._observe_slot = Mock(
            side_effect=lambda area, index, *args, **kwargs:
                self.task._observations[area][index]
        )
        self.task.get_in_hand_area(True)
        self.assertNotIn(character.name, self.task._purchase_pending_names)
        self.assertFalse(self.task.main_c_first_fielded_confirmed)

    def test_explicitly_empty_shop_and_matching_spend_confirm_last_purchase(self):
        character = self.character("灵砂")
        card = self.logic.ShopCard(
            2, character, self.task.store_area[2], raw_text=character.name, price=2
        )
        self.task.get_coins = Mock(return_value=48)
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY))
        self.assertEqual(
            self.task._confirm_purchase(card, 50),
            self.logic.ActionResult.CONFIRMED,
        )

    def test_stop_propagates_out_of_character_scan_without_actions(self):
        self.operator.stop_event.set()
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.get_in_hand_area(True)
        self.assertEqual(self.operator.calls, [])




    def test_safe_drag_releases_pointer_and_propagates_stop(self):
        for interruption in ("exception", "stop_flag"):
            with self.subTest(interruption=interruption):
                self.operator.stop_event.clear()
                self.task._release_pointer_unconditionally = Mock(return_value=True)

                def interrupted(*args, **kwargs):
                    self.operator.stop_event.set()
                    if interruption == "exception":
                        raise self.module.ThreadStoppedError("test stop during drag")
                    return True

                self.operator.drag_to = Mock(side_effect=interrupted)
                with self.assertRaises(self.module.ThreadStoppedError):
                    self.task._safe_drag_to(0.2, 0.8, 0.4, 0.4)
                self.task._release_pointer_unconditionally.assert_called_once()

    def test_safe_drag_success_does_not_send_redundant_release(self):
        self.operator.drag_to = Mock(return_value=True)
        self.task._release_pointer_unconditionally = Mock(return_value=True)
        self.assertTrue(self.task._safe_drag_to(0.2, 0.8, 0.4, 0.4))
        self.task._release_pointer_unconditionally.assert_not_called()

    def test_form_invalidation_clears_all_star_evidence_and_protects_duplicates(self):
        self.empty_board()
        character = self.character("银狼LV.999")
        self.task.strategy_characters = {character.name: 2}
        character.stars = 2
        self.observe("on_field", 0, character, stars=2)
        self.observe("off_field", 0, character, stars=2)
        self.observe("in_hand", 0, character, stars=1)
        self.assertEqual(self.task._confirmed_field_stars(character.name), 2)
        self.task._invalidate_character_evidence(character.name, "form_upgrade")
        self.assertEqual(self.task._confirmed_field_stars(character.name), 0)
        self.assertEqual(character.stars, 0)
        self.assertNotIn(character.name,
                         [candidate.name for _, candidate in self.task._sell_candidates()])
        new_form = self.logic.SlotObservation(
            0, self.logic.SlotState.KNOWN, character=character,
            occupied=True, evidence="new form observed", stars=1,
        )
        self.task._set_observation("on_field", new_form)
        self.assertEqual(self.task._confirmed_field_stars(character.name), 1)
        self.assertEqual(character.stars, 1)

    def test_confirmed_silver_wolf_event_invalidates_old_stars(self):
        self.empty_board()
        character = self.character("银狼LV.999")
        self.task.strategy_characters = {character.name: 2}
        self.task.strategy_special_events = {"头号玩家": "银狼"}
        self.observe("on_field", 0, character, stars=2)
        character.stars = 2
        self.task._handle_selection_event = Mock(return_value=True)
        self.assertTrue(self.task.handle_silver_wolf_lv999())
        self.assertEqual(self.task._confirmed_field_stars(character.name), 0)
        self.assertEqual(character.stars, 0)

    def test_failed_silver_wolf_event_does_not_invent_form_change(self):
        self.empty_board()
        character = self.character("银狼LV.999")
        self.observe("on_field", 0, character, stars=2)
        character.stars = 2
        self.task._observed_prices[character.name] = 3
        self.task._handle_selection_event = Mock(return_value=False)
        self.assertFalse(self.task.handle_silver_wolf_lv999())
        # Discarding uncertain stars is allowed; inventing the next price is not.
        self.assertNotEqual(self.task._observed_prices.get(character.name), 4)




    def test_safe_drag_false_result_also_releases_pointer(self):
        self.operator.drag_to = Mock(return_value=False)
        self.task._release_pointer_unconditionally = Mock(return_value=True)
        self.assertFalse(self.task._safe_drag_to(0.2, 0.8, 0.4, 0.4))
        self.task._release_pointer_unconditionally.assert_called_once()

    def test_unaffordable_priority_card_does_not_block_affordable_target(self):
        self.task.get_level = Mock(return_value=None)
        self.task.get_coins = Mock(return_value=3)
        expensive = self.character("银狼LV.999")
        affordable = self.character("佩拉")
        expensive.priority, affordable.priority = 99, 98
        self.task.strategy_characters = {expensive.name: 2, affordable.name: 2}
        cards = [
            self.logic.ShopCard(0, expensive, self.task.store_area[0],
                                raw_text=expensive.name, price=5),
            self.logic.ShopCard(2, affordable, self.task.store_area[2],
                                raw_text=affordable.name, price=2),
        ]
        self.scan_sequence(self.shop(self.logic.ShopState.READY, *cards))
        self.task._confirm_purchase = Mock(
            return_value=self.logic.ActionResult.CONFIRMED
        )
        result = self.task.shopping()
        self.assertEqual(result.confirmed_purchases, 1)
        self.assertEqual(self.task._confirm_purchase.call_args.args[0].character.name,
                         affordable.name)
        self.assertNotIn("f", self.operator.keys())
        self.assertNotIn("d", self.operator.keys())



    def load_final_silver_wolf_strategy(self):
        self.task.load_strategy(str(TASKS / "strategies" / "silver_wolf_lv999_aha_time_stop.json"))
        self.empty_board()
        return self.task.formation_config

    def test_final_strategy_blocks_direct_swap_of_protected_blade(self):
        self.load_final_silver_wolf_strategy()
        self.observe("on_field", 0, self.character("银狼LV.999"), stars=1)
        self.observe("off_field", 0, self.character("千冶·刃"), stars=1)
        self.observe("in_hand", 0, self.character("银狼"), stars=1)
        self.assertFalse(self.task.swap_character_between_areas("in_hand", 0, "off_field", 0))
        self.assertEqual(self.operator.drags(), [])

    def test_final_strategy_direct_swap_preserves_existing_trait_thresholds(self):
        for protected_trait in ("欢愉", "星核猎手"):
            with self.subTest(trait=protected_trait):
                self.load_final_silver_wolf_strategy()
                self.operator.calls.clear()
                if protected_trait == "欢愉":
                    field = ("银狼LV.999", "爻光", "绯英")
                    target = 1
                else:
                    field = ("银狼LV.999", "银狼")
                    target = 1
                for index, name in enumerate(field):
                    self.observe("on_field", index, self.character(name), stars=1)
                self.observe("in_hand", 0, self.character("缇宝"), stars=1)
                self.assertFalse(self.task.swap_character_between_areas("in_hand", 0, "on_field", target))
                self.assertEqual(self.operator.drags(), [])

    def test_full_nine_unit_board_reaches_final_four_front_five_back(self):
        config = self.load_final_silver_wolf_strategy()
        initial = {
            "on_field": ("银狼LV.999", "爻光", "绯英"),
            "off_field": ("千冶·刃", "花火", "开拓者", "符玄", "缇宝", "火花"),
            "in_hand": ("银狼",),
        }
        for area, names in initial.items():
            for index, name in enumerate(names):
                self.observe(area, index, self.character(name), stars=2 if name == "火花" else 1)
        self.task.max_team_size = 9
        self.task._reconcile_placed()
        self.install_board_observer()
        snapshots = []
        actual_swap = self.task.swap_character_between_areas

        def checked_swap(*args):
            result = actual_swap(*args)
            counts = self.module.confirmed_trait_counts(config, self.task._observations)
            snapshots.append(counts)
            self.assertGreaterEqual(counts.get("欢愉", 0), 3)
            self.assertGreaterEqual(counts.get("星核猎手", 0), 2)
            self.assertLessEqual(self.task.current_team_size, 9)
            return result

        self.task.swap_character_between_areas = checked_swap
        self.assertTrue(self.task.place_character())
        expected = config.stages[-1]
        for area in ("on_field", "off_field"):
            actual = {o.character.name for o in self.task._observations[area]
                      if o.state == self.logic.SlotState.KNOWN}
            self.assertEqual(actual, set(getattr(expected, area)), area)
        self.assertTrue(snapshots)
        self.assertTrue(any(c and c.name == "千冶·刃" for c in self.task.in_hand_character))

    def test_zero_refresh_budget_stops_before_refresh_input(self):
        self.task.min_level = self.task.mid_level = 3
        self.task.get_level = Mock(return_value=7)
        self.task.shopping_budget["refreshes"] = 0
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY))
        result = self.task.shopping()
        self.assertEqual(result.reason, "refresh_budget")
        self.assertEqual(result.refreshes, 0)
        self.assertNotIn("d", self.operator.keys())

    def test_zero_experience_budget_covers_both_upgrade_branches(self):
        for minimum in (3, 7):
            with self.subTest(min_level=minimum):
                self.operator.calls.clear()
                self.task.min_level, self.task.mid_level = minimum, 8
                self.task.shopping_budget["experiences"] = 0
                self.scan_sequence(self.shop(self.logic.ShopState.EMPTY),
                                   self.shop(self.logic.ShopState.EMPTY))
                result = self.task.shopping()
                self.assertEqual(result.reason, "experience_budget")
                self.assertEqual(result.experience_purchases, 0)
                self.assertNotIn("f", self.operator.keys())
                self.assertEqual(self.operator.keys().count("d"), int(minimum == 3))

    def test_zero_purchase_budget_stops_before_card_click(self):
        card = self.card()
        self.task.strategy_characters = {card.character.name: 2}
        self.task.shopping_budget["purchases"] = 0
        self.scan_sequence(self.shop(self.logic.ShopState.READY, card))
        self.task._confirm_purchase = Mock()
        result = self.task.shopping()
        self.assertEqual(result.reason, "purchase_budget")
        self.assertEqual(result.attempted_purchases, 0)
        self.task._confirm_purchase.assert_not_called()
        self.assertFalse(any(name == "click" and args[:2] == card.target
                             for name, args, kwargs in self.operator.calls))

    def test_action_budget_remains_bounded_without_fixed_shop_seconds(self):
        self.task.shopping_budget["actions"] = 1
        self.task.min_level = self.task.mid_level = 3
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY),
                           self.shop(self.logic.ShopState.EMPTY))
        result = self.task.shopping()
        self.assertEqual(result.reason, "action_budget")
        self.assertEqual(result.refreshes, 0)  # Reserve an input for the new page.
        self.operator.calls.clear()
        self.task.shopping_budget["seconds"] = 1
        with patch.object(self.module.time, "monotonic", side_effect=(10, 11)):
            result = self.task.shopping()
        self.assertEqual(result.reason, "action_budget")
        self.assertEqual(self.operator.keys(), [])

    def test_shop_price_three_four_five_requires_new_star_observations(self):
        self.empty_board()
        character = self.character("银狼LV.999")
        self.task.strategy_characters = {character.name: 2}
        self.observe("on_field", 0, character, stars=2)
        character.stars = 2

        def token(text, width, offset=0):
            x = (self.task.store_area[2][0] - 0.19) * 1920 - width / 2 + offset
            return ([[x, 0], [x + width, 0], [x + width, 20], [x, 20]], text, 0.99)

        for price in (3, 4, 5):
            with self.subTest(price=price):
                self.operator.ocr_results = [token(character.name, 40), token(str(price), 10, 35)]
                if price > 3:
                    self.task._form_change_pending[character.name] = price - 1
                offer = self.task._scan_store()
                self.assertEqual(offer.state, self.logic.ShopState.READY)
                self.assertEqual(offer.cards[0].price, price)
                self.assertEqual(self.task._observed_prices[character.name], price)
                self.assertEqual(character.cost, 5)
                if price == 3:
                    self.assertEqual(self.task._confirmed_field_stars(character.name), 2)
                    continue
                self.assertEqual(self.task._confirmed_field_stars(character.name), 0)
                self.assertEqual(character.stars, 0)
                self.assertIn(("on_field", 0), self.task._dirty_slots)
                self.assertNotIn(character.name, self.task._form_change_pending)
                for stars in (1, 2):
                    fresh = self.logic.SlotObservation(
                        0, self.logic.SlotState.KNOWN, character=character,
                        occupied=True, evidence="new form stars observed", stars=stars)
                    self.task._set_observation("on_field", fresh)
                    self.assertEqual(self.task._confirmed_field_stars(character.name), stars)
                    self.assertEqual(character.stars, stars)

    def test_reliable_empty_bench_observation_clears_stale_full_flag(self):
        self.empty_board()
        self.task._bench_full = True
        self.task._observe_slot = Mock(side_effect=lambda area, index, *args, **kwargs:
                                       self.task._observations[area][index])
        self.task.get_in_hand_area(True)
        self.assertFalse(self.task._bench_full)
        self.task._bench_full = True
        result = self.task.sell_character()
        self.assertEqual(result.reason, "space_confirmed")
        self.assertFalse(self.task._bench_full)
        card = self.card()
        self.task.strategy_characters = {card.character.name: 2}
        self.scan_sequence(self.shop(self.logic.ShopState.READY, card))
        self.task._confirm_purchase = Mock(return_value=self.logic.ActionResult.CONFIRMED)
        self.assertEqual(self.task.shopping().confirmed_purchases, 1)

    def test_unknown_bench_observation_does_not_clear_full_flag(self):
        self.task._bench_full = True
        self.task._observe_slot = Mock(side_effect=lambda area, index, *args, **kwargs:
                                       self.logic.SlotObservation(index, self.logic.SlotState.UNKNOWN))
        self.task.get_in_hand_area(True)
        self.assertTrue(self.task._bench_full)


    def test_event_same_title_with_background_ready_is_not_dismissed(self):
        self.operator.ocr_boxes = Mock(return_value=[FakeBox(source="银狼LV.999")])
        self.operator.click_box = Mock(return_value=True)
        self.operator.click_img = Mock(return_value=True)
        self.operator.locate = Mock(side_effect=lambda image, *args, **kwargs:
                                    FakeBox() if image == "PREPARATION_STAGE" else None)
        for title, expected in (("头号玩家", False), ("", True), ("盛会之星", True)):
            with self.subTest(remaining_title=title):
                elapsed = 0.0

                def advance_sleep(seconds):
                    nonlocal elapsed
                    elapsed += seconds

                self.operator.sleep = advance_sleep
                self.task.detect_special_event = Mock(return_value=title)
                with patch.object(self.module.time, "monotonic", side_effect=lambda: elapsed):
                    result = self.task._handle_selection_event(
                        (0.22, 0.34, 0.85, 0.4), "银狼", "头号玩家")
                self.assertEqual(result, expected)
                if expected:
                    self.assertEqual(self.task.detect_special_event.call_count, 1)
                else:
                    self.assertGreaterEqual(elapsed, 15)
                    self.assertLessEqual(elapsed, 15.3)


    def prepare_main_c_refresh_search(self, coins):
        self.empty_board()
        self.configure_main_c()
        self.task.min_level = self.task.mid_level = 5
        self.task.min_coins = 20
        self.task.get_coins = Mock(return_value=coins)
        self.task.get_level = Mock(return_value=5)

    def test_main_c_refresh_reserve_loads_zero_by_default_and_accepts_custom_integer(self):
        strategy = {"title": "main c", "main_c": "灵砂", "on_field": {"灵砂": 2}}
        for reserve in (None, 10):
            with self.subTest(reserve=reserve):
                if reserve is None:
                    strategy.pop("main_c_search_min_coins", None)
                else:
                    strategy["main_c_search_min_coins"] = reserve
                with patch("builtins.open", mock_open(read_data=json.dumps(strategy))):
                    self.task.load_strategy("main_c.json")
                self.assertEqual(self.task.main_c_search_min_coins, 0 if reserve is None else reserve)
                self.task.reset_character()
                self.assertEqual(self.task.main_c_search_min_coins, 0 if reserve is None else reserve)
        self.task.unload_strategy()
        self.assertEqual(self.task.main_c_search_min_coins, 0)

    def test_main_c_refresh_reserve_rejects_bool_negative_and_noninteger_without_mutation(self):
        strategy = {"title": "main c", "main_c": "灵砂", "on_field": {"灵砂": 2}}
        for value in (True, False, -1, 1.5, "0", None):
            with self.subTest(value=value):
                strategy["main_c_search_min_coins"] = value
                with patch("builtins.open", mock_open(read_data=json.dumps(strategy))):
                    with self.assertRaisesRegex(ValueError, "main_c_search_min_coins"):
                        self.task.load_strategy("main_c.json")
                self.assertIsNone(self.task.main_c)
                self.assertEqual(self.task.main_c_search_min_coins, 0)

    def test_main_c_search_can_refresh_below_normal_reserve_and_four_coin_floor(self):
        self.prepare_main_c_refresh_search(3)
        self.task.get_coins = Mock(side_effect=[3, 1, 1])
        other = self.card("黑塔", 0)
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY),
                           self.shop(self.logic.ShopState.READY, other),
                           self.shop(self.logic.ShopState.READY, other))
        result = self.task.shopping()
        self.assertEqual(result.refreshes, 1)
        self.assertEqual(result.reason, "low_coins")
        self.assertEqual(self.operator.keys(), ["d"])
        self.assertEqual(result.attempted_purchases, 0)

    def test_main_c_search_stops_when_less_than_real_refresh_cost(self):
        self.prepare_main_c_refresh_search(1)
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY))
        result = self.task.shopping()
        self.assertEqual(result.reason, "low_coins")
        self.assertEqual(result.refreshes, 0)
        self.assertEqual(self.operator.keys(), [])

    def test_main_c_search_custom_reserve_is_kept_after_paying_refresh(self):
        self.prepare_main_c_refresh_search(12)
        self.task.main_c_search_min_coins = 10
        self.task.get_coins = Mock(side_effect=[12, 10, 10])
        other = self.card("黑塔", 0)
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY),
                           self.shop(self.logic.ShopState.READY, other),
                           self.shop(self.logic.ShopState.READY, other))
        result = self.task.shopping()
        self.assertEqual(result.refreshes, 1)
        self.assertEqual(result.reason, "coin_reserve")
        self.assertEqual(self.operator.keys(), ["d"])

    def test_main_c_search_does_not_refresh_when_payment_would_cross_custom_reserve(self):
        self.prepare_main_c_refresh_search(11)
        self.task.main_c_search_min_coins = 10
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY))
        result = self.task.shopping()
        self.assertEqual(result.reason, "coin_reserve")
        self.assertEqual(result.refreshes, 0)

    def test_main_c_refresh_reserve_does_not_apply_below_search_level(self):
        self.prepare_main_c_refresh_search(19)
        self.task.get_level = Mock(return_value=4)
        self.task.min_level = self.task.mid_level = 3
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY))
        result = self.task.shopping()
        self.assertEqual(result.reason, "coin_reserve")
        self.assertEqual(result.refreshes, 0)

    def test_confirmed_main_c_restores_normal_refresh_reserve(self):
        self.prepare_main_c_refresh_search(19)
        self.observe("on_field", 0, self.character(), stars=1)
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY))
        result = self.task.shopping()
        self.assertTrue(self.task.main_c_first_fielded_confirmed)
        self.assertEqual(result.reason, "coin_reserve")
        self.assertEqual(result.refreshes, 0)

    def test_no_main_c_keeps_legacy_coin_floor_and_reserve(self):
        self.task.min_coins = 20
        self.task.min_level = self.task.mid_level = 5
        for coins, expected in ((3, "low_coins"), (19, "coin_reserve")):
            with self.subTest(coins=coins):
                self.task.get_coins = Mock(return_value=coins)
                self.scan_sequence(self.shop(self.logic.ShopState.EMPTY))
                result = self.task.shopping()
                self.assertEqual(result.reason, expected)
                self.assertEqual(result.refreshes, 0)

    def test_main_c_in_hand_or_pending_returns_for_placement_without_more_spending(self):
        for pending in (False, True):
            with self.subTest(pending=pending):
                self.prepare_main_c_refresh_search(0)
                self.operator.calls.clear()
                self.task._purchase_pending_names.clear()
                if pending:
                    self.task._purchase_pending_names.add(self.task.main_c)
                else:
                    self.observe("in_hand", 0, self.character(), stars=1)
                self.task._scan_store = Mock()
                result = self.task.shopping()
                self.assertEqual(result.reason, "main_c_placement")
                self.task._scan_store.assert_not_called()
                self.assertEqual(self.operator.keys(), [])
                self.assertEqual(result.attempted_purchases, 0)

    def test_low_coin_purchase_still_prioritizes_visible_main_c_over_other_target(self):
        self.prepare_main_c_refresh_search(3)
        main = self.logic.ShopCard(2, self.character(), self.task.store_area[2],
                                   raw_text="灵砂", price=3, price_evidence="test")
        other = self.logic.ShopCard(0, self.character("黑塔"), self.task.store_area[0],
                                    raw_text="黑塔", price=1, price_evidence="test")
        other.character.priority = 999
        self.task.strategy_characters[other.character.name] = 2
        self.scan_sequence(self.shop(self.logic.ShopState.READY, other, main))
        self.task._confirm_purchase = Mock(return_value=self.logic.ActionResult.CONFIRMED)
        result = self.task.shopping()
        self.assertEqual(result.reason, "main_c_placement")
        self.assertEqual(result.confirmed_purchases, 1)
        self.task._confirm_purchase.assert_called_once_with(main, 3)
        self.assertEqual(self.operator.keys(), [])

    def test_main_c_low_reserve_keeps_action_budget(self):
        self.prepare_main_c_refresh_search(3)
        self.task.shopping_budget["actions"] = 2
        other = self.card("黑塔", 0)
        self.scan_sequence(self.shop(self.logic.ShopState.EMPTY),
                           self.shop(self.logic.ShopState.READY, other),
                           self.shop(self.logic.ShopState.EMPTY),
                           self.shop(self.logic.ShopState.READY, other))
        result = self.task.shopping()
        self.assertEqual(result.reason, "action_budget")
        self.assertEqual(result.refreshes, 1)
        self.assertEqual(self.operator.keys(), ["d"])


if __name__ == "__main__":
    unittest.main()
