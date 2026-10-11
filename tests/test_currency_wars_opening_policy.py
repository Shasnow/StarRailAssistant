"""Opening hand protection exercised against the production task and physical UI."""

import unittest
from dataclasses import replace
from unittest.mock import Mock, call

import test_currency_wars_flow as flow_fixture
import test_currency_wars_page_purchase as page_fixture


class OpeningPolicyTests(unittest.TestCase):
    setUp = page_fixture.PagePurchaseTests.setUp
    configure = page_fixture.PagePurchaseTests.configure
    configure_page = page_fixture.PagePurchaseTests.configure_page
    character = page_fixture.PagePurchaseTests.character
    observe = page_fixture.PagePurchaseTests.observe
    empty_board = page_fixture.PagePurchaseTests.empty_board
    shop = page_fixture.PagePurchaseTests.shop
    card = page_fixture.PagePurchaseTests.card
    add_physical_copy = page_fixture.PagePurchaseTests.add_physical_copy
    install_game = page_fixture.PagePurchaseTests.install_game
    assert_clean_finish = page_fixture.PagePurchaseTests.assert_clean_finish
    install_local_sale_board = flow_fixture.CurrencyWarsFlowTests.install_local_sale_board

    def configure_opening(self, current_round, *, gold=40, level=7,
                          target_level=None, purchase_reserve=30):
        self.task._begin_preparation()
        self.configure_page(gold=gold, level=level, target_level=target_level,
                            purchase_reserve=purchase_reserve)
        self.task.opening_policy_config = self.module.parse_opening_policy_config({
            "sell_from_round": "1-4", "refresh_from_round": "1-4",
        })
        self.task._preparation_round = current_round
        if current_round is None:
            self.task._read_preparation_round = Mock(return_value=None)

    def configure_sale(self, current_round):
        self.configure_opening(current_round)
        self.task.max_team_size = 1
        self.task._population_current = 1
        self.task.strategy_characters = {"佩拉": 1}
        for index, name in enumerate(("藿藿", "真理医生", "远坂凛")):
            self.observe("in_hand", index, self.character(name), stars=1)
        return self.install_local_sale_board()

    def test_1_1_and_1_3_keep_all_starting_cards_without_sale_inputs(self):
        for current_round in ((1, 1), (1, 3)):
            with self.subTest(round=current_round):
                sold = self.configure_sale(current_round)
                result = self.task.sell_character()

                self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
                self.assertEqual((result.attempted, result.confirmed), (0, 0))
                self.assertEqual(result.reason, "opening_sales_locked")
                self.assertEqual(sold, set())
                self.assertEqual(self.operator.drags(), [])
                self.task._observe_slot.assert_not_called()
                self.assertEqual([self.task.in_hand_character[index].name
                                  for index in range(3)],
                                 ["藿藿", "真理医生", "远坂凛"])

    def test_1_4_reopens_sparse_surplus_cleanup(self):
        sold = self.configure_sale((1, 4))

        result = self.task.sell_character()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.attempted, result.confirmed), (3, 3))
        self.assertEqual(sold, {0, 1, 2})
        self.assertEqual(len(self.operator.drags()), 3)

    def test_unknown_round_keeps_starting_hand_with_zero_sale_actions(self):
        sold = self.configure_sale(None)

        result = self.task.sell_character()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.attempted, result.confirmed), (0, 0))
        self.assertEqual(result.reason, "opening_round_unknown")
        self.assertEqual(sold, set())
        self.assertEqual(self.operator.drags(), [])

    def test_forced_sale_cannot_bypass_early_or_unknown_round_protection(self):
        for current_round, reason in (((1, 3), "opening_sales_locked"),
                                      (None, "opening_round_unknown")):
            with self.subTest(round=current_round):
                sold = self.configure_sale(current_round)

                result = self.task._handle_sell_character(force=True)

                self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
                self.assertEqual((result.attempted, result.confirmed), (0, 0))
                self.assertEqual(result.reason, reason)
                self.assertEqual(sold, set())
                self.assertEqual(self.operator.drags(), [])

    def test_early_shop_buys_only_goals_and_settles_before_exiting_without_refresh(self):
        self.configure_opening((1, 3))
        self.task.strategy_characters = {"三月七": 1, "花火": 2}
        self.task.max_team_size = 1
        self.task._population_current = 1
        for index, name in enumerate(("藿藿", "真理医生", "远坂凛")):
            self.observe("in_hand", index, self.character(name), stars=1)
        self.install_game([[self.card("三月七", 0, price=1),
                            self.card("景元", 1, price=1)],
                           [self.card("花火", 0, price=1)]],
                          unknown_prices={"三月七"})

        result = self.task.shopping()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.attempted_purchases, result.confirmed_purchases,
                          result.refreshes), (1, 1, 0))
        self.assertEqual([name for name, _, _ in self.purchases], ["三月七"])
        self.assertEqual(self.money, 39)
        self.assertEqual(self.page_index, 0)
        self.assertNotIn("d", self.operator.keys())
        self.assertEqual([event for event in self.events if event[0] == "sold"], [])
        self.assertEqual(len(self.bench_scans), 1)
        self.assertEqual({obs.character.name for obs in self.physical["in_hand"]
                          if obs.character is not None},
                         {"藿藿", "真理医生", "远坂凛", "三月七"})
        self.assert_clean_finish()

    def test_1_1_protection_applies_to_main_search_despite_plenty_of_gold(self):
        self.configure_opening((1, 1), gold=100)
        self.task.main_c = "姬子·启行"
        self.task.main_c_search_level = 5
        self.task.main_c_first_fielded_confirmed = False
        self.task.strategy_characters = {"姬子·启行": 3}
        self.install_game([[], [self.card("姬子·启行", price=1)]])

        result = self.task.shopping()

        self.assertEqual((result.refreshes, result.confirmed_purchases), (0, 0))
        self.assertNotIn("d", self.operator.keys())
        self.assertEqual((self.money, self.page_index), (100, 0))
        self.assert_clean_finish()

    def test_unknown_round_waits_for_heading_before_buying_natural_goal_card(self):
        self.configure_opening(None)
        self.task.strategy_characters = {"三月七": 1, "花火": 2}
        self.install_game([[self.card("三月七", price=1)],
                           [self.card("花火", price=1)]])

        result = self.task.shopping()

        self.assertEqual(result.result, self.logic.ActionResult.INDETERMINATE)
        self.assertEqual(result.reason, "final_round_unknown")
        self.assertEqual((result.attempted_purchases, result.confirmed_purchases,
                          result.refreshes), (0, 0, 0))
        self.assertEqual((self.money, self.page_index), (40, 0))
        self.task._scan_store.assert_not_called()
        self.operator.click_point.assert_not_called()
        self.assertEqual(self.purchases, [])
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(self.bench_scans, [])

        self.task._read_preparation_round.return_value = (1, 3)
        recovered = self.task.shopping()

        self.assertEqual(recovered.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((recovered.confirmed_purchases, recovered.refreshes), (1, 0))
        self.assertEqual((self.money, self.page_index), (39, 0))
        self.assertNotIn("d", self.operator.keys())
        self.assertEqual(len(self.bench_scans), 1)
        self.assert_clean_finish()

    def test_early_positive_reserve_shop_buys_goal_without_refresh(self):
        self.configure_opening((1, 3))
        self.task.economy_config = self.module.parse_economy_config({
            "enabled": True, "purchase_reserve_gold": 30,
            "stages": [{"from_battles": 0, "target_level": 7, "reserve_gold": 5}],
        })
        self.task.strategy_characters = {"三月七": 1, "花火": 2}
        self.install_game([[self.card("三月七", price=1)],
                           [self.card("花火", price=1)]])

        result = self.task.shopping()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.confirmed_purchases, result.refreshes), (1, 0))
        self.assertNotIn("d", self.operator.keys())
        self.assertEqual((self.money, self.page_index), (39, 0))
        self.assert_clean_finish()

    def test_early_legacy_economy_shop_buys_goal_without_refresh(self):
        self.configure_opening((1, 3))
        self.task.economy_config = None
        self.task.min_level = self.task.mid_level = 7
        self.task.min_coins = 30
        self.task.strategy_characters = {"三月七": 1, "花火": 2}
        self.install_game([[self.card("三月七", price=1)],
                           [self.card("花火", price=1)]])

        result = self.task.shopping()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.confirmed_purchases, result.refreshes), (1, 0))
        self.assertNotIn("d", self.operator.keys())
        self.assertEqual((self.money, self.page_index), (39, 0))
        # The existing legacy purchase path hands its pending identity to the
        # following preparation pass, rather than using the economy ledger.
        self.assertFalse(self.shop_open)
        self.assertFalse(self.task._shopping_active)
        self.assertEqual(self.task._purchase_pending_names, {"三月七"})
        self.task._open_supply_items.assert_not_called()

    def test_1_4_refreshes_after_buying_natural_shop_goal(self):
        self.configure_opening((1, 4))
        self.task.strategy_characters = {"三月七": 1, "花火": 2}
        self.install_game([[self.card("三月七", price=1)],
                           [self.card("花火", price=1)]])

        result = self.task.shopping()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.confirmed_purchases, result.refreshes), (2, 1))
        self.assertEqual(self.operator.keys(), ["d"])
        self.assertEqual((self.money, self.page_index), (36, 1))
        self.assert_clean_finish()

    def test_opening_refresh_lock_preserves_existing_xp_economy_rules(self):
        self.configure_opening((1, 2), gold=40, level=6, target_level=7)
        self.task.strategy_characters = {"花火": 2}
        self.install_game([[]])
        self.task.shopping_budget.update(experiences=1)

        result = self.task.shopping()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.experience_purchases, result.refreshes), (1, 0))
        self.assertEqual(self.operator.keys(), ["f"])
        self.assertEqual(self.money, 36)
        self.assert_clean_finish()

    def test_early_shop_can_buy_configured_role_provider_outside_root_list(self):
        self.configure_opening((1, 2))
        self.task.strategy_characters = {"佩拉": 1}
        stage = self.module.FormationStage("early", 0, ("佩拉",), ())
        self.task.formation_config = self.module.FormationConfig(
            {}, {}, {}, (stage,),
            roles={"survival": (self.module.RoleProvider("符玄", ("off_field",)),)},
            role_requirements={"survival": self.module.RoleRequirement(
                1, ("符玄",), (), "warn_continue")})
        self.install_game([[self.card("符玄", 0, price=1),
                            self.card("景元", 1, price=1)]])

        result = self.task.shopping()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.confirmed_purchases, result.refreshes), (1, 0))
        self.assertEqual([name for name, _, _ in self.purchases], ["符玄"])
        self.assertEqual(self.operator.keys(), [])
        self.assertEqual(self.money, 39)
        self.assert_clean_finish()

    def test_sale_only_policy_does_not_lock_early_refresh(self):
        self.configure_opening((1, 1))
        self.task.opening_policy_config = self.module.parse_opening_policy_config({
            "sell_from_round": "1-4"})
        self.task.strategy_characters = {"花火": 2}
        self.install_game([[], [self.card("花火", price=1)]])

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, result.refreshes), (1, 1))
        self.assertEqual(self.operator.keys(), ["d"])
        self.assert_clean_finish()

    def test_refresh_only_policy_does_not_lock_reliable_early_sales(self):
        sold = self.configure_sale((1, 1))
        self.task.opening_policy_config = self.module.parse_opening_policy_config({
            "refresh_from_round": "1-4"})

        result = self.task.sell_character()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.attempted, result.confirmed), (3, 3))
        self.assertEqual(sold, {0, 1, 2})

    def test_no_opening_policy_preserves_existing_early_refresh_behavior(self):
        self.configure_opening((1, 1))
        self.task.opening_policy_config = None
        self.task.strategy_characters = {"花火": 2}
        self.install_game([[], [self.card("花火", price=1)]])

        result = self.task.shopping()

        self.assertEqual((result.confirmed_purchases, result.refreshes), (1, 1))
        self.assertEqual(self.operator.keys(), ["d"])
        self.assert_clean_finish()

    def test_new_preparation_drops_previous_round_unlock(self):
        self.configure_opening((1, 4))
        self.assertTrue(self.task._opening_action_allowed("sell"))
        self.assertTrue(self.task._opening_action_allowed("refresh"))
        self.task._preparation_deadline = None
        self.task._begin_preparation()
        self.task._read_preparation_round = Mock(return_value=None)

        self.assertIsNone(self.task._preparation_round)
        self.assertFalse(self.task._opening_action_allowed("sell"))
        self.assertFalse(self.task._opening_action_allowed("refresh"))

    def test_new_game_drops_previous_round_unlock_but_keeps_strategy_policy(self):
        self.configure_opening((3, 7))
        policy = self.task.opening_policy_config
        self.assertTrue(self.task._opening_action_allowed("sell"))

        self.task.reset_character()
        self.task._read_preparation_round = Mock(return_value=None)

        self.assertIs(self.task.opening_policy_config, policy)
        self.assertIsNone(self.task._preparation_round)
        self.assertFalse(self.task._opening_action_allowed("sell"))
        self.assertFalse(self.task._opening_action_allowed("refresh"))

    def test_round_without_preparation_heading_cannot_unlock_from_battle_count(self):
        self.configure_opening(None)
        self.task._confirmed_battle_count = 20
        self.task._read_preparation_round = self.module.CurrencyWars._read_preparation_round.__get__(
            self.task)
        self.operator.ocr = Mock(return_value=[(None, "3-7", 0.99)])

        self.assertFalse(self.task._opening_action_allowed("sell"))
        self.assertFalse(self.task._opening_action_allowed("refresh"))

        self.assertIsNone(self.task._preparation_round)
        self.assertEqual(self.operator.drags(), [])
        self.assertEqual(self.operator.keys(), [])

    def test_conflicting_preparation_frames_do_not_unlock_refresh(self):
        self.configure_opening(None)
        self.task._read_preparation_round = self.module.CurrencyWars._read_preparation_round.__get__(
            self.task)
        self.operator.ocr = Mock(side_effect=[
            [(None, "备战阶段 1-4", 0.99)], [],
            [(None, "备战阶段 1-3", 0.99)], [],
        ])

        self.assertFalse(self.task._opening_action_allowed("refresh"))

        self.assertIsNone(self.task._preparation_round)
        self.assertEqual(self.operator.keys(), [])

    def test_two_current_preparation_frames_unlock_at_1_4(self):
        self.configure_opening(None)
        self.task._read_preparation_round = self.module.CurrencyWars._read_preparation_round.__get__(
            self.task)
        self.operator.ocr = Mock(side_effect=[
            [(None, "备战阶段 1-4", 0.99)], [],
            [(None, "备战阶段 1-4", 0.99)], [],
        ])

        self.assertTrue(self.task._opening_action_allowed("refresh"))
        self.assertTrue(self.task._opening_action_allowed("sell"))

        self.assertEqual(self.task._preparation_round, (1, 4))
        self.assertEqual(self.operator.ocr.call_count, 4)

    def test_stop_remains_observable_with_zero_action_opening_sale(self):
        self.configure_sale((1, 1))
        self.operator.stop_event.set()
        calls_before = len(self.operator.calls)

        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.sell_character()
        with self.assertRaises(self.module.ThreadStoppedError):
            self.task._handle_sell_character(force=True)

        self.assertEqual(len(self.operator.calls), calls_before)

    def test_stop_during_goal_purchase_does_not_send_final_cleanup_inputs(self):
        self.configure_opening((1, 3))
        self.task.strategy_characters = {"花火": 2}
        self.install_game([[self.card("花火", price=1)]])
        click = self.operator.click_point.side_effect
        calls_when_stopped = []

        def click_and_stop(*args, **kwargs):
            result = click(*args, **kwargs)
            self.operator.stop_event.set()
            calls_when_stopped.append(len(self.operator.calls))
            return result

        self.operator.click_point.side_effect = click_and_stop

        with self.assertRaises(self.module.ThreadStoppedError):
            self.task.shopping()

        self.assertEqual(len(self.purchases), 1)
        self.assertEqual(len(self.operator.calls), calls_when_stopped[0])
        self.assertEqual(self.operator.keys(), [])
        # Only the entry close occurred, before the purchase raised stop.
        self.assertEqual(self.close_requests, [0])
        self.assertEqual(self.bench_scans, [])
        self.assertFalse(self.task._shopping_active)

    def test_unknown_backend_layout_keeps_all_temporary_cards_even_after_1_4(self):
        sold = self.configure_sale((1, 4))
        self.task.max_team_size = 4
        self.task._layout_valid = False
        for index in range(len(self.task.off_field_area)):
            self.observe("off_field", index, state=self.logic.SlotState.UNKNOWN)

        result = self.task.sell_character()

        self.assertEqual(result.result, self.logic.ActionResult.CONFIRMED)
        self.assertEqual((result.attempted, result.confirmed), (0, 0))
        self.assertEqual(sold, set())
        self.assertEqual(self.operator.drags(), [])
        self.assertEqual([self.task.in_hand_character[index].name for index in range(3)],
                         ["藿藿", "真理医生", "远坂凛"])

    def test_unknown_field_slot_keeps_all_temporary_cards_with_valid_layout(self):
        sold = self.configure_sale((2, 3))
        self.task._layout_valid = True
        self.observe("off_field", 0, state=self.logic.SlotState.UNKNOWN)

        result = self.task.sell_character()

        self.assertEqual((result.attempted, result.confirmed), (0, 0))
        self.assertEqual(sold, set())
        self.assertEqual(self.operator.drags(), [])

    def test_population_conflict_keeps_temporary_hand_instead_of_trusting_fullness(self):
        sold = self.configure_sale((1, 4))
        self.task.max_team_size = 4
        self.task._population_current = 4  # Only one field identity is confirmed.

        result = self.task.sell_character()

        self.assertEqual(self.task._sale_transition_blocker(), "population_conflict")
        self.assertEqual((result.attempted, result.confirmed), (0, 0))
        self.assertEqual(sold, set())
        self.assertEqual(self.operator.drags(), [])

    def test_capacity_only_read_cannot_certify_temporary_hand_is_surplus(self):
        sold = self.configure_sale((1, 4))
        self.task._population_current = None
        self.task._vision.read_population = Mock(return_value=self.module.PopulationObservation(
            None, None, "population_unknown", "numerator_missing", "?/4"))
        self.operator.ocr_results = [(None, "4", 0.99)]

        result = self.task.sell_character()

        self.assertEqual(self.task.max_team_size, 4)
        self.assertIsNone(self.task._population_current)
        self.assertEqual(self.task._sale_transition_blocker(), "population_unknown")
        self.assertEqual((result.attempted, result.confirmed), (0, 0))
        self.assertEqual(sold, set())
        self.task._vision.read_population.assert_called_once()

    def test_locked_npc_counts_in_population_and_allows_real_surplus_cleanup(self):
        sold = self.configure_sale((1, 4))
        npc = self.character("灵砂")
        npc.is_npc = npc.is_locked = True
        self.observe("off_field", 0, npc)
        self.task.max_team_size = self.task._population_current = 2

        result = self.task.sell_character()

        self.assertIsNone(self.task._sale_transition_blocker())
        self.assertEqual((result.attempted, result.confirmed), (3, 3))
        self.assertEqual(sold, {0, 1, 2})
        self.assertIs(self.task.off_field_character[0], npc)

    def test_post_placement_missing_population_reads_once_before_cleaning_fillers(self):
        sold = self.configure_sale((1, 4))
        self.task._population_current = None
        self.task._population_read_key = None
        self.task._vision.read_population = Mock(return_value=self.module.PopulationObservation(
            1, 1, "matching_frames", "confirmed", "1/1"))

        result = self.task.sell_character()

        self.assertEqual((result.attempted, result.confirmed), (3, 3))
        self.assertEqual(sold, {0, 1, 2})
        self.assertEqual(self.task._population_current, 1)
        self.task._vision.read_population.assert_called_once()

    def test_real_same_name_swap_invalidates_population_cache_then_reads_once(self):
        self.configure_opening((1, 4))
        self.task.max_team_size = self.task._population_current = 1
        self.task.strategy_characters = {"佩拉": 1}
        self.observe("in_hand", 0, self.character("藿藿"), stars=1)
        self.observe("in_hand", 1, self.character("真理医生"), stars=1)
        self.observe("in_hand", 2, self.character("佩拉"), stars=2)
        self.install_game([[]])
        self.task._population_read_key = (
            self.task._layout_revision, self.task.max_team_size,
            tuple(self.module.observation_identity(obs)
                  for area in ("on_field", "off_field")
                  for obs in self.task._observations[area]))
        sale_drag = self.task._safe_drag_to.side_effect

        def drag(source_x, source_y, target_x, target_y, **kwargs):
            if (target_x, target_y) == self.task.on_field_area[0]:
                source = self.physical["in_hand"][2]
                target = self.physical["on_field"][0]
                self.physical["in_hand"][2] = replace(target, slot_index=2)
                self.physical["on_field"][0] = replace(source, slot_index=0)
                return True
            return sale_drag(source_x, source_y, target_x, target_y)

        self.task._safe_drag_to.side_effect = drag
        self.task._vision.read_population = Mock(return_value=self.module.PopulationObservation(
            1, 1, "matching_frames", "confirmed", "1/1"))

        self.assertTrue(self.task.swap_character_between_areas("in_hand", 2, "on_field", 0))
        self.assertIsNone(self.task._population_current)
        self.assertIsNone(self.task._population_read_key)

        result = self.task.sell_character()

        self.assertEqual((result.attempted, result.confirmed), (3, 3))
        self.assertEqual([event[1] for event in self.events if event[0] == "sold"],
                         ["藿藿", "真理医生", "佩拉"])
        self.assertEqual(self.task._observations["on_field"][0].stars, 2)
        self.task._vision.read_population.assert_called_once()

    def test_failed_population_read_has_one_enhanced_retry_before_blocking_sales(self):
        sold = self.configure_sale((1, 4))
        self.task._population_current = None
        self.task._vision.read_population = Mock(return_value=self.module.PopulationObservation(
            None, None, "population_unknown", "numerator_missing", "?/1"))
        self.operator.ocr_results = []

        first = self.task.sell_character()
        second = self.task.sell_character()
        calls_after_retry = list(self.task._vision.read_population.call_args_list)
        third = self.task.sell_character()

        self.assertEqual((first.attempted, first.confirmed, second.attempted,
                          second.confirmed, third.attempted, third.confirmed), (0, 0, 0, 0, 0, 0))
        self.assertEqual(sold, set())
        self.assertEqual(calls_after_retry, [call(), call(enhance=True)])
        self.assertEqual(self.task._vision.read_population.call_args_list, calls_after_retry)

    def test_first_preparation_with_opening_policy_buys_natural_goal_before_battle(self):
        self.configure_opening((1, 1))
        self.task._confirmed_battle_count = 0
        self.task.strategy_characters = {"三月七": 1, "花火": 2}
        self.install_game([[self.card("三月七", price=1)],
                           [self.card("花火", price=1)]])
        now = self.module.time.monotonic()
        self.task._bench_observed_at = self.task._field_observed_at = now
        self.task.harvest_crystals = Mock()
        self.task._refresh_dirty_field = Mock()
        self.task.handle_characters_updated = Mock()
        self.task.update_max_team_size = Mock()
        self.task.prepare_for_battle = Mock(return_value=self.module.PreparationResult(
            self.module.Readiness.READY, "test_ready"))
        self.task._equipment_due = Mock(return_value=False)
        self.task.stage_transition = Mock(return_value=True)
        real_shopping = self.task.shopping
        self.task.shopping = Mock(side_effect=real_shopping)

        def battle():
            self.assertEqual([name for name, _, _ in self.purchases], ["三月七"])
            self.assertFalse(self.shop_open)
            self.assertNotIn("d", self.operator.keys())
            self.task.is_game_over = True
            return True

        self.task.battle = Mock(side_effect=battle)

        self.assertTrue(self.task.game_loop())

        self.task.shopping.assert_called_once()
        self.task.battle.assert_called_once()
        self.assertEqual((self.money, self.page_index), (39, 0))
        self.assertEqual([event for event in self.events if event[0] == "sold"], [])

    def test_continued_initialization_closes_shop_before_any_field_scan(self):
        self.configure_opening((1, 3))
        self.install_game([[]])
        self.task.is_continue = True
        self.task._pending_battle_id = None
        self.shop_open = True

        def scan_field(*, equip):
            self.assertFalse(self.shop_open)
            self.assertFalse(equip)
            self.events.append(("field_scan",))

        self.task.refresh_character = Mock(side_effect=scan_field)

        self.assertTrue(self.task._initialize_game())

        self.task._set_shop_open.assert_called_once_with(False)
        self.task.refresh_character.assert_called_once_with(equip=False)
        self.assertLess(self.events.index(("shop", False)),
                        self.events.index(("field_scan",)))

    def test_continued_initialization_cannot_scan_when_shop_close_is_unconfirmed(self):
        self.configure_opening((1, 3))
        self.install_game([[]])
        self.task.is_continue = True
        self.task._pending_battle_id = "pending-before-open-shop"
        self.task._battle_entry_confirmed = False
        self.shop_open = True
        self.task._set_shop_open = Mock(return_value=False)
        self.task.refresh_character = Mock()
        self.task._record_checkpoint = Mock()

        self.assertFalse(self.task._initialize_game())

        self.task._set_shop_open.assert_called_once_with(False)
        self.task.refresh_character.assert_not_called()
        self.task._record_checkpoint.assert_not_called()
        self.assertEqual(self.task._pending_battle_id, "pending-before-open-shop")
        self.assertTrue(self.shop_open)

    def test_full_field_refresh_authenticates_then_scans_frontline_before_backend(self):
        self.configure_opening((1, 3))
        self.observe("off_field", 0, self.character("花火"), stars=1)
        self.observe("in_hand", 0, self.character("藿藿"), stars=2)
        self.install_game([[]])
        self.shop_open = True
        bench_before = tuple(self.task._observations["in_hand"])

        def read_layout(positions, **kwargs):
            self.assertFalse(self.shop_open)
            self.events.append(("backend_layout",))
            return self.module.LayoutObservation(
                True, tuple(self.task.off_field_area), reason="physical_confirmed_layout")

        self.task._vision.read_backend_layout = Mock(side_effect=read_layout)

        self.task.refresh_character(equip=False)

        self.task._set_shop_open.assert_called_once_with(False)
        field_reads = [(index, event) for index, event in enumerate(self.events)
                       if event[0] == "read" and event[1] in ("on_field", "off_field")]
        self.assertEqual([event[1] for _, event in field_reads],
                         ["on_field"] * len(self.task.on_field_area) +
                         ["off_field"] * len(self.task.off_field_area))
        self.assertLess(self.events.index(("shop", False)), field_reads[0][0])
        last_front = max(index for index, event in field_reads if event[1] == "on_field")
        first_back = min(index for index, event in field_reads if event[1] == "off_field")
        layout_read = self.events.index(("backend_layout",))
        self.assertLess(last_front, layout_read)
        self.assertLess(layout_read, first_back)
        self.assertTrue(self.task._layout_valid)
        self.assertEqual(self.task.off_field_character[0].name, "花火")
        self.assertEqual(tuple(self.task._observations["in_hand"]), bench_before)

    def test_full_field_refresh_with_unconfirmed_close_keeps_bench_and_does_not_scan(self):
        self.configure_opening((1, 3))
        self.observe("off_field", 0, self.character("花火"), stars=1)
        self.observe("in_hand", 0, self.character("藿藿"), stars=2)
        self.install_game([[]])
        self.shop_open = True
        self.task._field_observed_at = self.module.time.monotonic()
        self.task.max_team_size = self.task._population_current = 2
        self.task._population_read_key = ("previous_confirmed_population",)
        bench_before = tuple(self.task._observations["in_hand"])
        bench_characters_before = tuple(self.task.in_hand_character)
        self.task._set_shop_open = Mock(return_value=False)
        self.task._vision.read_backend_layout = Mock()
        self.task._vision.capture_layout_failure = Mock()

        self.assertFalse(self.task.refresh_character(equip=False))

        self.task._set_shop_open.assert_called_once_with(False)
        self.task._observe_slot.assert_not_called()
        self.task._vision.read_backend_layout.assert_not_called()
        self.assertFalse(self.task._layout_valid)
        self.assertIsNone(self.task._field_observed_at)
        self.assertIsNone(self.task._population_current)
        self.assertIsNone(self.task._population_read_key)
        for area in ("on_field", "off_field"):
            self.assertTrue(all(obs.state == self.logic.SlotState.UNKNOWN
                                and obs.evidence == "preparation_not_confirmed"
                                for obs in self.task._observations[area]))
        self.assertEqual(tuple(self.task._observations["in_hand"]), bench_before)
        self.assertTrue(all(current is previous for current, previous in
                            zip(self.task._observations["in_hand"], bench_before)))
        self.assertEqual(tuple(self.task.in_hand_character), bench_characters_before)
        self.task._vision.capture_layout_failure.assert_called_once_with(
            "layout_preparation_not_confirmed")
        self.assertTrue(self.shop_open)

    def test_pending_or_dirty_field_keeps_temporary_hand_without_population_ocr(self):
        for state in ("pending", "dirty"):
            with self.subTest(state=state):
                sold = self.configure_sale((1, 4))
                self.task._population_current = None
                self.task._vision.read_population = Mock()
                self.task._placement_pending = state == "pending"
                self.task._dirty_slots = {("off_field", 0)} if state == "dirty" else set()

                result = self.task.sell_character()

                self.assertEqual((result.attempted, result.confirmed), (0, 0))
                self.assertEqual(sold, set())
                self.task._vision.read_population.assert_not_called()

    def test_unknown_field_still_allows_independently_confirmed_goal_surplus_sale(self):
        sold = self.configure_sale((1, 4))
        self.task.strategy_characters["藿藿"] = 1
        self.observe("off_field", 0, self.character("藿藿"), stars=2)
        self.observe("off_field", 1, state=self.logic.SlotState.UNKNOWN)

        result = self.task.sell_character()

        self.assertEqual((result.attempted, result.confirmed), (1, 1))
        self.assertEqual(sold, {0})
        self.assertEqual([self.task.in_hand_character[index].name for index in (1, 2)],
                         ["真理医生", "远坂凛"])


if __name__ == "__main__":
    unittest.main()
