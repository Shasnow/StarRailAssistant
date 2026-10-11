import enum
import hashlib
import sys
from pathlib import Path
from dataclasses import replace
import json
import re
import time
import uuid
from contextlib import contextmanager
from collections.abc import Callable
from typing import Any

from loguru import logger

from SRACore.operators.model import Box
from SRACore.task import Executable
from SRACore.util.errors import ErrorCode, SRAError, ThreadStoppedError
from tasks.currency_wars.characters import Character, Characters, Positioning
from tasks.img import CWIMG, IMG, DUIMG
from tasks.currency_wars.logic import (
    SlotState, SlotObservation, ShopState, ActionResult, SellResult, ShoppingResult,
    parse_character_name, scan_store_cards, validate_main_c_config,
    parse_shop_level, evaluate_purchase, ShopObservation,
)

from tasks.currency_wars.formation import (
    validate_formation_config, select_formation_stage, formation_change_allowed,
    plan_formation_move, confirmed_trait_counts, stage_upgrade_allowed,
    UNRELIABLE_EVIDENCE,
    evaluate_role_requirements, role_purchase_targets, role_protected_names,
    resolve_effective_targets, plan_formation_sequence, validate_formation_sequence,
    _placement_areas,
)
from tasks.currency_wars.vision import (
    CurrencyWarsVision, image_distance, RESULT_HEALTH_ROI, FINAL_HEALTH_ROI,
    TERMINAL_STATES, TERMINAL_STATE_ORDER,
)
from tasks.currency_wars.preparation import (
    MoveStatus, MoveResult, PreparationResult, Readiness, classify_move,
    observation_identity, validate_preparation_budget, recovery_signature,
)
from tasks.currency_wars.layout import (LayoutObservation, validate_backend_layout,
    backend_rectangle_candidates, revalidate_backend_layout, layout_diagnostics)
from tasks.currency_wars.session import SessionStore
from tasks.currency_wars.shop_overlay import (
    SHOP_PROBABILITY_TITLE_ROI, detect_shop_probability_overlay,
)
from tasks.currency_wars.economy import (
    parse_economy_config, select_economy_stage, next_economy_action, can_afford_purchase,
    evaluate_all_in_policy, next_final_round_action,
)
from tasks.currency_wars.policy import (
    parse_preparation_round, parse_experience_progress, parse_experience_cap,
    parse_opening_policy_config,
)
from tasks.currency_wars.equipment_policy import parse_equipment_config, allowed_order
from tasks.currency_wars.shopping_batch import ShoppingBatch


class Difficulty(enum.IntEnum):
    """难度模式枚举"""
    LOWEST = 0
    HIGHEST = 1
    CURRENT = 2


class CurrencyWarsPage(enum.IntEnum):
    """货币战争页面枚举"""
    START = 1
    PREPARATION = 2
    BOSS_PREVIEW = 3
    RECOVERY = 4
    UNKNOWN = -1


class StageName(enum.StrEnum):
    """关卡阶段名称枚举"""
    FORTUNE_TELLER = '命运卜者'
    REPLENISH_STAGE = '补给阶段'
    ENCOUNTER_NODE = '遭遇节点'
    FOLD = '无'
    SELECT_INVEST_STRATEGY = '选择投资策略'
    CLICK_BLANK = '点击空白处关闭'
    GAME_OVER = '游戏结束'
    MAIN_MENU = '主界面'


class CurrencyWars(Executable):
    # These limits apply to page transitions, not shop or formation actions.
    FLOW_REVISION = "mandatory-final-round-spending-cap-ocr-release-20261011-v29-bench-sale-fix-preparation-stop-fix"
    PAGE_LOCATE_TIMEOUT = 45
    ENTRY_TRANSITION_TIMEOUT = 30
    STAGE_TRANSITION_TIMEOUT = 60
    BATTLE_BUTTON_TIMEOUT = 15
    PREPARATION_GRACE_SECONDS = 45
    PREPARATION_CONFIRM_SECONDS = 3
    REWARD_TRANSITION_TIMEOUT = 120
    EVENT_TRANSITION_TIMEOUT = 15
    STAGE_SETTLE_SECONDS = 3
    BATTLE_TIMEOUT = 600
    FLOW_RECOVERY_ATTEMPTS = 2
    FLOW_RECOVERY_STEPS = 12
    FLOW_RECOVERY_SECONDS = 90
    DIFFICULTY_SELECTION_TIMEOUT = 60
    DIFFICULTY_MAX_CLICKS = 40
    STRATEGY_APPLIED_IMAGE = "resources/img/currency_wars/cancel_apply.png"
    SHOP_REFRESH_COST = 2  # Confirmed by consecutive real-log balances 51 -> 49 -> 47.
    FINAL_ROUND_REFRESH_LIMIT = 80  # Includes free refreshes and same-round recovery.

    SHOP_EXPERIENCE_COST = 4  # Single F input in this gameplay, not a whole-level price.

    def __init__(self, operator, runtimes):
        super().__init__(operator)
        self.runtimes = runtimes
        self.special_events: dict[str, tuple[str, Callable[[], bool]]] = {
            "领航员": ("选择伙伴", self.handle_choose_partner),
            "盛会之星": ("盛会之星", self.handle_the_planet_of_festivities),
            "命运圣杯": ("祈愿试炼", self.handle_wish_trial),
            "头号玩家": ("我来当策划", self.handle_silver_wolf_lv999),
            "命运卜者": ("命运卜者", self.handle_fortune_teller)
        }
        self.is_continue = False  # 是否是继续挑战
        self.is_game_over = False
        self.difficulty: int = Difficulty.LOWEST
        self.on_field_character: list[Character | None] = [None, None, None, None]  # 前台角色列表
        self.on_field_area: list[tuple[float, float]] = [
            (0.386, 0.365),
            (0.464, 0.365),
            (0.536, 0.365),
            (0.611, 0.365)
        ]
        self.off_field_character: list[Character | None] = [None, None, None, None, None, None]  # 后台角色列表
        self.off_field_area: list[tuple[float, float]] = [
            (0.3056, 0.620),
            (0.3806, 0.620),
            (0.4525, 0.620),
            (0.5264, 0.620),
            (0.6004, 0.620),
            (0.6738, 0.620)
        ]
        self.in_hand_character: list[Character | None] = [None, None, None, None, None, None, None, None,
                                                          None]  # 备战席角色列表
        self.in_hand_area: list[tuple[float, float]] = [
            (0.229, 0.844),
            (0.297, 0.844),
            (0.358, 0.844),
            (0.426, 0.844),
            (0.488, 0.844),
            (0.556, 0.844),
            (0.618, 0.844),
            (0.684, 0.844),
            (0.749, 0.844)
        ]  # 备战席区域
        self.store_area: list[tuple[float, float]] = [
            (0.25, 0.18),
            (0.40, 0.18),
            (0.55, 0.18),
            (0.68, 0.18),
            (0.80, 0.18)
        ]
        self.max_team_size = 3  # 最大队伍人数
        self.is_running = False
        self._startup_failed = False
        self.min_coins = 40  # 最小金币数
        self.min_level = 7  # 商店等级
        self.mid_level = 7  # 商店等级
        self.strategy_characters: dict[str, int] = dict()  # 在攻略中的角色及其预期星级
        self.strategy_code = ""  # 当前使用的攻略代码
        self.strategy_special_events: dict[str, str] = dict()  # 攻略中的特殊事件处理
        self.is_overclock = False  # 超频博弈
        self.is_complex_invest_strategy_selection_enabled = False  # 是否启用复杂投资策略选择逻辑
        self._default_off_field_area = list(self.off_field_area)
        self.main_c = None
        self.main_c_search_level = 5
        self.main_c_search_min_coins = 0
        self.main_c_first_fielded_confirmed = False
        self._observation_revision = 0
        self._observations = {
            area: [SlotObservation(i, SlotState.UNKNOWN) for i in range(len(getattr(self, area + "_area")))]
            for area in ("on_field", "off_field", "in_hand")
        }
        self._level_cache = None
        self._bench_full = False
        self._equipment_dirty = True
        self._equipment_checked = {}
        self._equipment_resource_revision = 0
        self._equipment_attempts = {}
        self._last_scan_completed = {}
        self._purchase_pending_names = set()
        self._placement_pending = False
        self.phase_seconds = {}
        self.formation_config = None
        self._effective_targets = None
        self._effective_targets_key = None
        self._preparation_assessment_cache = None
        self._terminal_route_screen = None
        self._formation_plan = ()
        self._formation_plan_stage = None
        self._formation_plan_incomplete = False
        self.economy_config = None
        self.opening_policy_config = None
        self._economy_stage_index = None
        self._preparation_round = None
        self._round_read_attempts = 0
        self._all_in_decision = None
        self._all_in_budget = None
        self._confirmed_battle_count = 0
        self._pending_battle_id = None
        self._battle_entry_confirmed = False
        self._last_completed_battle_id = None
        self.equipment_interval_battles = None
        self.equipment_config = None
        self._equipment_others_checked = False
        self._equipment_battles_since_check = 0
        self._equipment_batch_running = False
        self._equipment_batch_attempts = 0
        self._equipment_metrics = dict(skipped=0, due=0, unconfirmed=0)
        self._shopping_active = False
        self._preparation_shop_counts = dict(purchases=0, attempts=0, refreshes=0, experiences=0)
        self.shopping_budget = {"actions": 60, "seconds": 90, "purchases": 60,
                                "refreshes": 60, "experiences": 60}
        self._strategy_path = None
        self._observed_prices = {}
        self._form_change_pending = {}
        self._dirty_slots = set()
        self._last_selection_sent = False
        self._runtime_node_pending = None
        self._last_shopping_result = None
        self._last_level_read = None
        self._last_coins_read = None
        self.preparation_budget = validate_preparation_budget(None)
        self._snapshot_revision = 0
        self._layout_revision = 0
        self._layout_valid = True
        self._confirmed_layout_positions = ()
        self._pending_move = None
        self._last_move_result = MoveResult(MoveStatus.REJECTED, "no_move_attempted")
        self._move_failures = {}
        self._fielding_rejections = set()
        self._last_preparation_result = None
        self._preparation_deadline = None
        self._preparation_rewards_collected = False
        self._preparation_departure_confirmed = False
        self._formation_deadline = None
        self._preparation_attempts = 0
        self._preparation_moves = 0
        self._preparation_recoveries = 0
        self._field_observed_at = None
        self._bench_observed_at = None
        self._bench_dirty = True
        self._population_current = None
        self._population_read_key = None
        self._sale_population_retry_used = False
        self._last_health_read = None
        self._health_read_attempts = 0
        self._last_battle_outcome = "unknown"
        self._cycle_number = 0
        self._session_store = None
        self._strategy_fingerprint = "default"
        self._health_roi = None
        self._empty_roster_needs_shop = False
        self._vision = CurrencyWarsVision(
            operator, Path(__file__).parent / "calibration" / "profile.json",
            Path(__file__).parent / "diagnostics", stop_check=self._check_stop)
        self._vision.layout_api = (LayoutObservation, backend_rectangle_candidates,
            layout_diagnostics, revalidate_backend_layout, validate_backend_layout)

    def _check_stop(self):
        event = getattr(self.operator, "stop_event", None)
        if event is not None and event.is_set():
            raise ThreadStoppedError("货币战争任务已停止")

    @contextmanager
    def _timed(self, phase):
        started = time.monotonic()
        try:
            yield
        finally:
            elapsed = time.monotonic() - started
            self.phase_seconds[phase] = self.phase_seconds.get(phase, 0.0) + elapsed
            logger.debug(f"[货币战争耗时] {phase}: {elapsed:.2f}s")

    def _begin_session(self):
        if self._session_store is None:
            self._session_store = SessionStore(Path(__file__).parent / "state" / "current_run.json")
        fingerprint = self._strategy_fingerprint
        if len(fingerprint) != 64:
            fingerprint = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        recovery = self._session_store.begin(fingerprint, resume=self.is_continue)
        checkpoint = recovery.checkpoint
        self._cycle_number = checkpoint.completed_cycles
        self._confirmed_battle_count = checkpoint.confirmed_battle_count
        self._pending_battle_id = checkpoint.pending_battle_id
        self._battle_entry_confirmed = bool(checkpoint.pending_battle_id and
            (checkpoint.phase in ("combat", "settlement", "terminal_navigation")
             or "battle_entered:" + checkpoint.pending_battle_id in checkpoint.confirmed_events))
        self._equipment_battles_since_check = checkpoint.equipment_battles_since_check
        self._economy_stage_index = (checkpoint.active_economy_stage_index
            if checkpoint.confirmed_battle_count is not None or checkpoint.active_economy_stage_index > 0
            else None)
        self._vision.begin_sample_scope(checkpoint.run_id, str(time.time_ns()))
        logger.info(f"[续跑恢复] 局标识={checkpoint.run_id} 累计脚本循环={self._cycle_number} "
                    f"原因={recovery.reason} 关联={checkpoint.association} "
                    f"历史页面={checkpoint.phase} 历史待确认={checkpoint.pending_actions} "
                    f"confirmed_battles={checkpoint.confirmed_battle_count} "
                    f"battle_count_unknown={checkpoint.confirmed_battle_count is None} "
                    f"economy_stage={self._economy_stage_index} equipment_since_check={self._equipment_battles_since_check}；现场状态重新观察")
        if not recovery.persisted:
            logger.warning(f"[续跑恢复] 检查点写入失败：{self._session_store.last_error}")
        self._record_checkpoint(phase="recovering" if self.is_continue else "preparation")

    def _record_checkpoint(self, **changes):
        if self._session_store is None:
            return True
        changes.setdefault("completed_cycles", self._cycle_number)
        result = self._session_store.record(**changes)
        if not result:
            logger.warning(f"[续跑恢复] 无法保存检查点：{self._session_store.last_error}")
        return result

    def _begin_preparation(self):
        if self._preparation_deadline is not None:
            return
        now = time.monotonic()
        self._preparation_deadline = now + self.preparation_budget["total_seconds"]
        self._preparation_rewards_collected = False
        self._preparation_departure_confirmed = False
        self._formation_deadline = None
        self._preparation_attempts = self._preparation_recoveries = 0
        self._preparation_moves = 0
        self._last_preparation_result = None
        self._fielding_rejections.clear()
        self._preparation_assessment_cache = None
        self._equipment_batch_attempts = 0
        self._economy_recovery_attempts = 0
        self._preparation_round = None
        self._round_read_attempts = 0
        self._all_in_decision = None
        self._all_in_budget = None
        self._preparation_shop_counts = dict(purchases=0, attempts=0, refreshes=0, experiences=0)
        self._population_read_key = None
        self._sale_population_retry_used = False
        self._record_checkpoint(phase="preparation", pending_actions=[] if self._pending_move is None else None)

    def _effective_formation(self):
        # Freeze mutable character attributes too; some observation replacements
        # do not go through _set_observation. Historical targets still feed the resolver.
        cache_key = (self.formation_config, self._snapshot_revision,
            recovery_signature(self._observations, layout_revision=self._layout_revision,
                layout_valid=self._layout_valid, capacity=self.max_team_size, population=None))
        if self._effective_targets is not None and self._effective_targets_key == cache_key:
            return self._effective_targets
        self._effective_targets = resolve_effective_targets(self.formation_config,
            self._observations, self.max_team_size, self._effective_targets)
        self._effective_targets_key = cache_key
        if self.formation_config is not None:
            npc_count = self._effective_targets.npc_count
            strategy_capacity = self._effective_targets.strategy_capacity
            stage = self._effective_targets.stage
            key = (self.max_team_size, npc_count, strategy_capacity, stage.name if stage else None)
            if key != getattr(self, "_formation_population_log_key", None):
                self._formation_population_log_key = key
                logger.info(f"[攻略人口] 游戏总上限={self.max_team_size} NPC占用={npc_count} "
                            f"普通角色名额={strategy_capacity} 阶段={key[-1]}")
        return self._effective_targets

    def _formation_stage(self):
        return self._effective_formation().stage

    def _purchase_goals(self):
        goals = dict(self.strategy_characters)
        for name, stars in self._effective_formation().purchase_targets.items():
            goals[name] = max(goals.get(name, 0), stars)
        if self.economy_config is not None and self.formation_config is not None:
            gate = self.formation_config.upgrade_gate
            if gate is not None:
                for name, stars in gate.fielded.items():
                    goals[name] = max(goals.get(name, 0), stars)
        return goals

    def _role_evaluations(self):
        stage = self._formation_stage()
        return evaluate_role_requirements(self.formation_config, stage, self._observations)

    def _role_purchase_goals(self):
        stage = self._formation_stage()
        return role_purchase_targets(self.formation_config, stage, self._observations)

    def _role_placement_unresolved(self, evaluation):
        if not evaluation.bench_candidates:
            return False
        stage = self._formation_stage()
        # Failed moves are still a critical placement gap. Only a confirmed
        # lack of legal moves may use the configured soft requirement.
        if plan_formation_move(self.formation_config, stage, self._observations,
                               self.max_team_size) is not None:
            return True
        field = [o for area in ("on_field", "off_field") for o in self._observations[area]]
        if all(observation_identity(o) is not None for o in field):
            return False
        known = sum(o.state == SlotState.KNOWN and observation_identity(o) is not None for o in field)
        return not (self._population_current == self.max_team_size == known)

    def _resolve_pending_move(self):
        pending = self._pending_move
        if pending is None:
            if self._placement_pending:
                self.refresh_character(equip=False)
            return not self._placement_pending
        touches_backend = "off_field" in (pending["source"][0], pending["target"][0])
        if touches_backend and not self._layout_valid:
            # Never inspect old backend endpoints until the layout recovery
            # pass has authenticated their coordinates. Do not replay the drag.
            self._placement_pending = True
            return False
        if pending["layout"] != self._layout_revision and touches_backend:
            # Old backend indices no longer describe the drag destination.
            # Rebuild that row and only the other affected area, preserving
            # reliable, unrelated frontline observations.
            self.refresh_backend_character(equip=False)
            if not self._layout_valid:
                self._placement_pending = True
                return False
            affected = {"off_field"}
            for area, index in (pending["source"], pending["target"]):
                if area == "in_hand":
                    self.get_in_hand_area(True)
                    affected.add(area)
                elif area == "on_field":
                    self._set_observation(area, self._observe_slot(area, index, count_stars=True))
                    if observation_identity(self._observations[area][index]) is None:
                        return False
            if not self._layout_valid or any(observation_identity(o) is None
                    for area in affected for o in self._observations[area]):
                self._placement_pending = True
                return False
            self._pending_move = None
            self._placement_pending = False
            self._reconcile_placed()
            self._confirm_main_c_fielded()
            self._reconcile_purchase_pending()
            self._record_checkpoint(phase="preparation", pending_actions=[])
            return True
        verify_same_name_stars = (observation_identity(pending["source_before"]) ==
            observation_identity(pending["target_before"]) and
            pending["source_before"].stars != pending["target_before"].stars)
        ends = []
        for (area, index), (other_area, _) in (
                (pending["source"], pending["target"]), (pending["target"], pending["source"])):
            if index >= len(self._observations[area]):
                return False
            observation = self._observe_slot(area, index,
                count_stars=verify_same_name_stars or area != "in_hand" or other_area != "in_hand",
                use_backup_ocr=area == "off_field")
            self._set_observation(area, observation)
            ends.append(observation)
        result = classify_move(pending["source_before"], pending["target_before"], *ends)
        result = self._confirm_fielding_rejection(pending, result)
        self._last_move_result = replace(result, source=pending["source"], target=pending["target"])
        if result.status == MoveStatus.INDETERMINATE:
            return False
        if result.status == MoveStatus.CONFIRMED_UNCHANGED:
            key = self._move_key(*pending["source"], *pending["target"])
            self._move_failures[key] = self._move_failures.get(key, 0) + 1
        else:
            self._reconcile_purchase_pending()
            if self._formation_plan:
                move = self._formation_plan[0]
                if ((move.source_area, move.source_index), (move.target_area, move.target_index)) == (
                        pending["source"], pending["target"]):
                    self._formation_plan = self._formation_plan[1:]
                    self._formation_plan_incomplete = bool(self._formation_plan)
        self._pending_move = None
        self._placement_pending = False
        self._reconcile_placed()
        self._confirm_main_c_fielded()
        self._reconcile_purchase_pending()
        self._record_checkpoint(phase="preparation", pending_actions=[])
        return True

    def _move_key(self, source_area, source_index, target_area, target_index):
        source = self._observations[source_area][source_index]
        target = self._observations[target_area][target_index]
        effective = self._effective_formation()
        return (source_area, source_index, target_area, target_index, self._layout_revision,
                observation_identity(source), observation_identity(target), self.max_team_size,
                source.stars, target.stars,
                (effective.stage.on_field, effective.stage.off_field,
                 tuple(sorted(effective.assignments.items()))) if effective.stage is not None else None)

    def _fielding_rejection_key(self, source_area, source_index, target_area):
        source = self._observations[source_area][source_index]
        return (source_area, source_index, target_area, self._layout_revision,
                observation_identity(source), source.stars, self.max_team_size)

    def _fielding_rejection_matches(self, key):
        source_area, source_index, target_area = key[:3]
        if source_index >= len(self._observations[source_area]):
            return False
        current = self._fielding_rejection_key(source_area, source_index, target_area)
        # A missing star read is not evidence that this is a different unit.
        return (key[:5] == current[:5] and key[6:] == current[6:]
                and (key[5] is None or current[5] is None or key[5] == current[5]))

    def _confirm_fielding_rejection(self, pending, result):
        source_area, source_index = pending["source"]
        target_area, _ = pending["target"]
        if (pending.get("fielding_rejected") and source_area == "in_hand"
                and target_area in ("on_field", "off_field")
                and result.status == MoveStatus.CONFIRMED_UNCHANGED):
            before_stars = pending["source_before"].stars
            after_stars = self._observations[source_area][source_index].stars
            if before_stars is not None and after_stars is not None and before_stars != after_stars:
                return result
            key = self._fielding_rejection_key(source_area, source_index, target_area)
            if key[5] is None and before_stars is not None:
                key = key[:5] + (before_stars,) + key[6:]
            self._fielding_rejections.add(key)
            name = pending["source_before"].character.name
            logger.warning(f"[布阵跳过] 游戏提示{name}当前无法上场且两端未变化，"
                           f"本整备期跳过备战[{source_index}]进入{target_area}的全部槽位")
            return replace(result, reason="game_cannot_be_fielded")
        return result

    def _excluded_moves(self):
        threshold = self.preparation_budget["move_retries"] + 1
        result = set()
        for key, count in self._move_failures.items():
            source_area, source_index, target_area, target_index = key[:4]
            if (count >= threshold and source_index < len(self._observations[source_area])
                    and target_index < len(self._observations[target_area])
                    and key == self._move_key(source_area, source_index, target_area, target_index)):
                result.add(key[:4])
        for key in self._fielding_rejections:
            source_area, source_index, target_area = key[:3]
            if self._fielding_rejection_matches(key):
                result.update((source_area, source_index, target_area, target_index)
                              for target_index in range(len(self._observations[target_area])))
        return result

    def _unknown_field_gaps(self):
        return tuple(f"field_unknown:{area}[{i}]:{o.evidence}"
                     for area in ("on_field", "off_field")
                     for i, o in enumerate(self._observations[area])
                     if observation_identity(o) is None)

    def _preparation_recovery_signature(self):
        return (recovery_signature(self._observations,
                    layout_revision=self._layout_revision, layout_valid=self._layout_valid,
                    capacity=self.max_team_size, population=self._population_current,
                    dirty_slots=self._dirty_slots, bench_dirty=self._bench_dirty,
                    placement_pending=self._placement_pending, pending_move=self._pending_move,
                    excluded_moves=self._excluded_moves()),
                self._preparation_attempts, self._preparation_moves)

    def _population_conflict(self, known=None):
        if known is None:
            known = sum(o.state == SlotState.KNOWN and observation_identity(o) is not None
                        for area in ("on_field", "off_field") for o in self._observations[area])
        if known > self.max_team_size:
            return "population_capacity_conflict"
        if self._population_current is not None and (
                known > self._population_current or self._population_current > self.max_team_size):
            return "population_observation_conflict"
        return None

    def _recover_preparation_observations(self, reason):
        # Recover only missing evidence; reliable bench cards do not need another full OCR pass.
        if reason == "backend_layout_not_confirmed" or not self._layout_valid:
            self.refresh_backend_character(equip=False,
                recover_layout=self._preparation_recoveries >= 2)
            return
        if reason == "pending_move_unresolved":
            # The next pass verifies the move endpoints (or changed layout) in
            # _resolve_pending_move. A full scan here duplicates that recovery.
            return
        if reason in {"no_confirmed_frontline", "population_capacity_conflict",
                      "population_observation_conflict"}:
            self.refresh_character(equip=False)
        else:
            for area in ("on_field", "off_field"):
                for i, old in enumerate(tuple(self._observations[area])):
                    self._check_stop()
                    if time.monotonic() >= self._formation_deadline:
                        return
                    if observation_identity(old) is None or (
                            old.state == SlotState.KNOWN and old.stars is None and not old.character.is_npc):
                        self._set_observation(area, self._observe_slot(
                            area, i, count_stars=True, use_backup_ocr=area == "off_field"))
            self._reconcile_placed()
            self._confirm_main_c_fielded()
        if time.monotonic() >= self._formation_deadline:
            return
        if self._bench_dirty or any(observation_identity(o) is None or (
                o.state == SlotState.KNOWN and o.stars is None and not o.character.is_npc)
                for o in self._observations["in_hand"]):
            self.get_in_hand_area(True)
            self._bench_dirty = False

    def _assess_preparation(self):
        # This evaluates recorded evidence, not the live screen. Share its result
        # with the battle gate and logging until any decision input changes.
        key = (self.formation_config, self._snapshot_revision,
               self._preparation_recovery_signature(), self._formation_plan_incomplete,
               self.main_c, self.main_c_first_fielded_confirmed)
        cached = self._preparation_assessment_cache
        if cached is not None and cached[0] == key:
            return cached[1]
        result = self._evaluate_preparation()
        self._preparation_assessment_cache = (key, result)
        return result

    def _evaluate_preparation(self):
        gaps = []
        field_gaps = self._unknown_field_gaps()
        if not self._layout_valid:
            return PreparationResult(Readiness.BLOCKED, "backend_layout_not_confirmed", gaps=field_gaps)
        if self._placement_pending or self._pending_move is not None:
            return PreparationResult(Readiness.BLOCKED, "pending_move_unresolved", gaps=field_gaps)
        if self._formation_plan_incomplete:
            return PreparationResult(Readiness.BLOCKED, "formation_plan_incomplete", gaps=field_gaps)
        if not self._confirmed_frontline():
            return PreparationResult(Readiness.BLOCKED, "no_confirmed_frontline", gaps=field_gaps)
        if self._main_c_in_hand():
            return PreparationResult(Readiness.BLOCKED, "main_c_waiting_for_placement", gaps=field_gaps)
        known_count = sum(o.state == SlotState.KNOWN and observation_identity(o) is not None
                          for area in ("on_field", "off_field") for o in self._observations[area])
        conflict = self._population_conflict(known_count)
        if conflict:
            return PreparationResult(Readiness.BLOCKED, conflict, gaps=field_gaps)
        effective = self._effective_formation()
        stage = effective.stage
        desired = set(stage.on_field + stage.off_field) if stage else set()
        if effective.gaps:
            return PreparationResult(Readiness.BLOCKED, "effective_target_unknown", gaps=effective.gaps + field_gaps)
        for role, evaluation in self._role_evaluations().items():
            if evaluation.state == "satisfied":
                continue
            gaps.append(f"role:{role}:{evaluation.state}:{evaluation.reason}")
            if self._role_placement_unresolved(evaluation) or evaluation.on_missing == "block":
                return PreparationResult(Readiness.BLOCKED, "role_not_ready", gaps=tuple(gaps) + field_gaps)
        missing = sorted(desired - {o.character.name for area in ("on_field", "off_field")
                                   for o in self._observations[area] if o.state == SlotState.KNOWN})
        if missing:
            gaps.append("stage_missing:" + ",".join(missing))
        required_region_gap = False
        if stage is not None:
            for area in ("on_field", "off_field"):
                present = {o.character.name for o in self._observations[area]
                           if o.state == SlotState.KNOWN and observation_identity(o) is not None}
                expected = set(getattr(stage, area)) - present
                misplaced = [o.character.name for other in ("on_field", "off_field", "in_hand")
                             if other != area for o in self._observations[other]
                             if observation_identity(o) is not None and o.state == SlotState.KNOWN
                             and o.character.name in expected]
                if misplaced:
                    gaps.append("target_area:" + area + ":" + ",".join(misplaced))
                    required = set(effective.assignments.values()) | {
                        rule.name for rule in self.formation_config.position_rules
                        if rule.area == area and rule.name in getattr(stage, area)}
                    required_region_gap = required_region_gap or bool(set(misplaced) & required)
        if self._population_current is not None and self._population_current < self.max_team_size:
            gaps.append(f"population:{self._population_current}/{self.max_team_size}")
        held_missing = any(o.state == SlotState.KNOWN and observation_identity(o) is not None
                           and not o.character.is_locked and not o.character.is_npc
                           and o.character.name in missing for o in self._observations["in_hand"])
        if field_gaps and held_missing and known_count < self.max_team_size:
            return PreparationResult(Readiness.BLOCKED, "deployment_target_unknown",
                                     gaps=tuple(gaps) + field_gaps)
        if required_region_gap:
            return PreparationResult(Readiness.BLOCKED, "effective_target_not_placed", gaps=tuple(gaps))
        move = plan_formation_move(self.formation_config, stage, self._observations,
                                   self.max_team_size, (), excluded_moves=self._excluded_moves())
        if move is not None:
            return PreparationResult(Readiness.BLOCKED, "safe_improvement_remaining", gaps=tuple(gaps))
        return PreparationResult(Readiness.DEGRADED if gaps else Readiness.READY,
                                 "confirmed_gaps" if gaps else "roster_confirmed", gaps=tuple(gaps))

    def prepare_for_battle(self):
        """Bounded observation -> placement -> confirmation, shared by all entry paths."""
        self._begin_preparation()
        if self._health_roi is not None and self._last_preparation_result is None:
            self._last_health_read = self._vision.read_squad_health(self._health_roi)
        if self._formation_deadline is None:
            self._formation_deadline = min(self._preparation_deadline,
                time.monotonic() + self.preparation_budget["seconds"])
        recovery_baseline = recovery_reason = None
        for _ in range(self.preparation_budget["recoveries"] + 2):
            self._check_stop()
            if time.monotonic() >= self._formation_deadline:
                # Expiry stops further actions; it does not invalidate a confirmed roster.
                result = self._assess_preparation()
                field_gaps = self._unknown_field_gaps()
                if time.monotonic() >= self._preparation_deadline:
                    result = replace(result, state=Readiness.BLOCKED, reason="preparation_time_budget",
                                     blocked_reason="preparation_total_time_budget")
                elif result.state == Readiness.BLOCKED:
                    result = replace(result, reason="preparation_time_budget",
                                     blocked_reason=result.blocked_reason or result.reason)
                elif field_gaps or any(area in ("on_field", "off_field")
                                       for area, _ in self._dirty_slots):
                    result = replace(result, state=Readiness.BLOCKED, reason="preparation_time_budget",
                                     blocked_reason="field_observation_not_confirmed",
                                     gaps=result.gaps + field_gaps)
                else:
                    logger.info("[整备检查] 布阵时间已用尽，现有场上证据确认就绪，停止移动并继续战斗流程")
                break
            if not self._layout_valid:
                result = PreparationResult(Readiness.BLOCKED, "backend_layout_not_confirmed",
                                           gaps=self._unknown_field_gaps())
            elif ((self._placement_pending or self._pending_move is not None)
                    and not self._resolve_pending_move()):
                result = PreparationResult(Readiness.BLOCKED, "pending_move_unresolved",
                                           gaps=self._unknown_field_gaps())
            else:
                if self._bench_dirty:
                    self.get_in_hand_area(True)
                    self._bench_dirty = False
                self._refresh_dirty_field()
                self.update_max_team_size()
                # A drag invalidates the population cache. Check conflicts before that happens.
                if not self._population_conflict():
                    self.place_character()
                    if self._population_current is None and time.monotonic() < self._formation_deadline:
                        self.update_max_team_size()
                result = self._assess_preparation()
            if result.state != Readiness.BLOCKED:
                break
            signature = self._preparation_recovery_signature()
            if (recovery_baseline == signature and recovery_reason == result.reason
                    and not (result.reason == "backend_layout_not_confirmed"
                             and self._preparation_recoveries < self.preparation_budget["recoveries"])):
                result = replace(result, reason="preparation_no_progress", blocked_reason=result.reason)
                logger.warning(f"[整备恢复] 补读后无新增有效证据，原因={result.blocked_reason} 缺口={result.gaps}")
                break
            if (self._preparation_recoveries >= self.preparation_budget["recoveries"]
                    or time.monotonic() >= self._formation_deadline):
                if time.monotonic() >= self._formation_deadline:
                    result = replace(result, reason="preparation_time_budget", blocked_reason=result.reason)
                break
            self._preparation_recoveries += 1
            recovery_baseline, recovery_reason = signature, result.reason
            logger.info(f"[整备恢复] 第{self._preparation_recoveries}次补读，原因={result.reason} 缺口={result.gaps}")
            self._recover_preparation_observations(result.reason)
        self._last_preparation_result = replace(result, moves=self._preparation_moves,
            attempts=self._preparation_attempts, recoveries=self._preparation_recoveries)
        logger.info(f"[整备检查] {self._last_preparation_result} "
                    f"观察版本={self._snapshot_revision} 布局版本={self._layout_revision}")
        if result.state == Readiness.BLOCKED:
            if (not self._layout_valid or result.reason == "backend_layout_not_confirmed"
                    or result.blocked_reason == "backend_layout_not_confirmed"):
                self._vision.capture_layout_failure("backend_layout_not_confirmed", terminal=True)
            sample = self._vision.capture_sample("preparation_blocked",
                {"evidence": result.reason + ";cause=" + result.blocked_reason + ";" + ";".join(result.gaps)}, critical=True)
            logger.error(f"[整备检查] 未确认就绪，截图={sample} "
                         f"采样原因={self._vision.last_sample_reason}")
        return self._last_preparation_result

    def _record_battle_screen(self, screen):
        outcome = getattr(screen, "outcome", "unknown")
        if outcome in ("success", "failure"):
            newly_confirmed = self._last_battle_outcome != outcome
            self._last_battle_outcome = outcome
            if newly_confirmed:
                self._record_checkpoint(phase="settlement", last_outcome=outcome,
                                        last_battle_outcome=outcome, pending_actions=[])
            if (screen.state == "result_ready" and self._health_read_attempts < 2
                    and (self._last_health_read is None or self._last_health_read.current is None)):
                self._health_read_attempts += 1
                self._last_health_read = self._vision.read_squad_health(RESULT_HEALTH_ROI)
                logger.info(f"[结算状态] 本场结果={outcome} 小队生命值={self._last_health_read.current} "
                            f"识别原因={self._last_health_read.reason}")

    def _record_execution_stop(self, status):
        if (self._session_store is not None and self._session_store.checkpoint is not None
                and not self._session_store.checkpoint.finalized):
            self._record_checkpoint(phase="stopped", execution_status=status)

    def _stable_terminal_screen(self, first):
        if first.state not in TERMINAL_STATES:
            return None
        self._check_stop()
        self.operator.sleep(0.3)
        second = self._vision.read_battle_screen()
        self._check_stop()
        a, b = getattr(first, "terminal_point", None), getattr(second, "terminal_point", None)
        if (second.state != first.state or second.outcome != first.outcome or a is None or b is None
                or max(abs(a[i] - b[i]) for i in (0, 1)) > 0.01):
            return None
        return second

    def _record_terminal_screen(self, screen):
        self._confirm_completed_battle("stable_terminal:" + screen.state)
        changes = dict(phase="terminal_navigation", execution_status="running",
                       terminal_navigation_step=screen.state,
                       pending_actions=["确认终局页面操作与返回主菜单"])
        if screen.state == "final_summary" and screen.outcome in ("success", "failure"):
            changes.update(terminal_outcome="won" if screen.outcome == "success" else "lost",
                           last_battle_outcome=screen.outcome,
                           terminal_evidence=screen.evidence,
                           confirmed_event="terminal:" + screen.outcome)
            self._last_battle_outcome = screen.outcome
        self._record_checkpoint(**changes)

    def _lookup_known_character(self, name):
        char = Characters.get_character(name)
        if char is None or char.is_locked or (char.cost <= 0 and not char.is_npc):
            return None
        # Do not accept previously registered OCR noise as a real definition.
        if name.strip().isdecimal() and name.strip() != Characters.username:
            return None
        return char

    def _area_name(self, characters):
        for name in ("on_field", "off_field", "in_hand"):
            if characters is getattr(self, name + "_character"):
                return name
        raise ValueError("未知角色区域")

    def _set_observation(self, area_type, observation):
        self._snapshot_revision += 1
        observations = self._observations[area_type]
        if observation.slot_index >= len(observations):
            observations.extend(SlotObservation(i, SlotState.UNKNOWN)
                                for i in range(len(observations), observation.slot_index + 1))
        observations[observation.slot_index] = observation
        if observation.state != SlotState.UNKNOWN:
            self._dirty_slots.discard((area_type, observation.slot_index))
        identity = observation_identity(observation)
        if identity is not None:
            # Retire the old card's refusal after a confirmed replacement or upgrade.
            for key in tuple(self._fielding_rejections):
                if key[:2] != (area_type, observation.slot_index):
                    continue
                stars_changed = (key[5] is not None and observation.stars is not None
                                 and key[5] != observation.stars)
                if key[4] != identity or stars_changed:
                    self._fielding_rejections.discard(key)
        characters = getattr(self, area_type + "_character")
        if observation.state == SlotState.KNOWN:
            characters[observation.slot_index] = observation.character
        elif observation.state in (SlotState.EMPTY, SlotState.LOCKED):
            characters[observation.slot_index] = None
        # UNKNOWN keeps the historical value, but no action may use it.
        if area_type != "in_hand" and observation.state == SlotState.KNOWN:
            char = observation.character
            char.is_placed = True
            if observation.stars is not None:
                char.stars = max(observation.stars, self._confirmed_field_stars(char.name))

    def _confirmed_field_stars(self, name):
        return max((obs.stars or 0 for area in ("on_field", "off_field")
                    for obs in self._observations[area]
                    if obs.state == SlotState.KNOWN and obs.character.name == name), default=0)

    def _reconcile_placed(self):
        field_observations = self._observations["on_field"] + self._observations["off_field"]
        for char in {id(c): c for c in Characters.characters.values()}.values():
            if any(obs.state == SlotState.KNOWN and obs.character is char for obs in field_observations):
                char.is_placed = True
            elif not any(obs.state == SlotState.UNKNOWN and
                         getattr(self, area + "_character")[i] is char
                         for area in ("on_field", "off_field")
                         for i, obs in enumerate(self._observations[area])):
                char.is_placed = False

    def _invalidate_level(self):
        self._level_cache = None

    def _confirm_main_c_fielded(self):
        if not self.main_c or self.main_c_first_fielded_confirmed:
            return self.main_c_first_fielded_confirmed
        if self._pending_move is not None:
            return False
        char = self._lookup_known_character(self.main_c)
        if char is None:
            return False
        areas = ("on_field",) if char.position == Positioning.OnField else (
            ("off_field",) if char.position == Positioning.OffField else ("on_field", "off_field"))
        for area in areas:
            if any(obs.state == SlotState.KNOWN and obs.character.name == self.main_c
                   and obs.evidence != "pending_drag" for obs in self._observations[area]):
                self.main_c_first_fielded_confirmed = True
                logger.info(f"主C {self.main_c} 已确认上阵，恢复当前阶段运营" if self.economy_config is not None
                            else f"主C {self.main_c} 已确认上阵，恢复正常升级条件和刷新门槛 min_coins={self.min_coins}")
                return True
        return False

    def _can_upgrade(self, level):
        self._confirm_main_c_fielded()
        if level is None:
            return False
        if self.main_c and not self.main_c_first_fielded_confirmed and level >= self.main_c_search_level:
            return False
        decision = stage_upgrade_allowed(self.formation_config, self._observations,
                                         level, self._observed_prices)
        if not decision.allowed:
            logger.info(f"阵容升级条件未满足：{decision.reason}")
        return decision.allowed

    def _main_c_in_hand(self):
        return bool(self.main_c and not self.main_c_first_fielded_confirmed and any(
            obs.state == SlotState.KNOWN and obs.character.name == self.main_c
            for obs in self._observations["in_hand"]))

    def _buy_experience(self, level, *, final_push=False, final_round=False):
        if type(level) is not int:
            return False
        if not final_round:
            if (self.economy_config is not None
                    and level >= self.economy_config.stages[-1].target_level):
                return False
            if not final_push and not self._can_upgrade(level):
                return False
        self._check_stop()
        if not self.operator.press_key("f"):
            return False
        self.operator.sleep(0.5)
        self._population_read_key = None
        self._invalidate_level()
        return True

    def _observe_slot(self, area_type, index, count_stars=False, use_backup_ocr=False):
        self._check_stop()
        if area_type == "off_field" and not self._layout_valid:
            return SlotObservation(index, SlotState.UNKNOWN, evidence="layout_changed")
        area = getattr(self, area_type + "_area")[index]
        previous = self._observations[area_type][index]
        self._observation_revision += 1
        support = getattr(self, "_backend_support_slots", {}).get(index) if area_type == "off_field" else None
        if support is not None:
            # The layout reader authenticated this locked occupant on two
            # current frames. It has no ordinary character or star panel.
            return SlotObservation(index, SlotState.KNOWN, support, True,
                "two_frame_locked_support", self._observation_revision, None)
        # Always clear the old panel, including unknown and non-equipment cases.
        self.operator.click_point(0.5, 0.5, trace=False)
        try:
            if not self.operator.click_point(*area, after_sleep=0.2, trace=False):
                return SlotObservation(index, SlotState.UNKNOWN, evidence="click_failed",
                                       revision=self._observation_revision)
            results = self.operator.ocr(from_x=0.775, from_y=0.175, to_x=0.880, to_y=0.2315)
            char = parse_character_name(results, self._lookup_known_character)
            if char is None and use_backup_ocr:
                backup = self.operator.ocr(from_x=0.775, from_y=0.445, to_x=0.880, to_y=0.486)
                char = parse_character_name(backup, self._lookup_known_character)
            if char is not None:
                stars = None
                if count_stars and not char.is_npc:
                    boxes = self.operator.locate_all(CWIMG.STAR, from_x=0.83, from_y=0.15,
                                                     to_x=0.87, to_y=0.17, trace=False)
                    valid = []
                    for box in boxes or ():
                        if not any(box.distance(other) < 3 for other in valid):
                            valid.append(box)
                    if 1 <= len(valid) <= 3:
                        stars = len(valid)
                return SlotObservation(index, SlotState.KNOWN, char, True, "name_match",
                                       self._observation_revision, stars)
            # A detector must provide positive empty evidence. OCR absence alone cannot.
            detector = getattr(self.operator, "currency_wars_slot_is_empty", None)
            empty = detector(area_type, index) if callable(detector) else None
            if empty is None:
                empty = self._vision.slot_is_empty(area_type, index, area)
            if empty is True:
                return SlotObservation(index, SlotState.EMPTY, occupied=False,
                                       evidence="empty_detector", revision=self._observation_revision)
            # Empty field baselines remain valid until an action targets the slot.
            # A continued game may acquire the same baseline from a live 0/N read.
            # Conflicting text invalidates even that baseline.
            if (area_type != "in_hand" and previous.state == SlotState.EMPTY
                    and empty is not False
                    and previous.evidence in ("new_game_empty", "zero_population")
                    and not any(str(item[1]).strip() and not str(item[1]).strip().isdecimal()
                                for item in results or ())):
                return SlotObservation(index, SlotState.EMPTY, occupied=False,
                                       evidence=previous.evidence, revision=self._observation_revision)
            self._vision.capture_sample("unknown_slot_" + area_type,
                                        {"area": area_type, "index": index})
            reason = ("occupied_name_unknown" if empty is False else
                      getattr(self._vision, "last_slot_reason", "") or "unrecognized_name")
            return SlotObservation(index, SlotState.UNKNOWN, evidence=reason,
                                   revision=self._observation_revision)
        finally:
            self.operator.click_point(0.5, 0.5, trace=False)

    def _scan_store(self):
        self._check_stop()
        results = self.operator.ocr(from_x=0.19, from_y=0.26, to_x=0.88, to_y=0.31)
        offer = scan_store_cards(results, self._lookup_known_character, self.store_area,
                                 self.operator.window_context.width)
        if offer.state == ShopState.UNKNOWN:
            if all(self._vision.slot_is_empty("store", i, position) is True
                   for i, position in enumerate(self.store_area)):
                offer = ShopObservation(ShopState.EMPTY, reason="verified_empty_slots")
            else:
                self._vision.capture_sample("unknown_store", {"reason": offer.reason})
        for card in offer.cards:
            if card.price is None:
                continue
            name = card.character.name
            previous = self._observed_prices.get(name)
            if name == Characters.SilverWolfLV999.name and previous is not None and previous != card.price:
                self._invalidate_character_evidence(name, f"observed_price:{previous}->{card.price}")
            self._observed_prices[name] = card.price
            if name in self._form_change_pending and previous != card.price:
                logger.info(f"角色实际商店费用已重识别：{name} {previous}->{card.price}")
                self._form_change_pending.pop(name, None)
        return offer

    def _confirm_purchase(self, card, before_coins):
        self._confirmed_purchase_snapshot = None
        after = self._scan_store()
        if after.state == ShopState.FULL:
            return ActionResult.FAILED
        remaining = next((c for c in after.cards if c.slot_index == card.slot_index), None)
        coins = self.get_coins()
        spent = before_coins - coins if before_coins is not None and coins is not None else None
        changed = (after.state == ShopState.EMPTY or
                   (after.state == ShopState.READY and remaining is None
                    and not after.reason.startswith("partial")))
        if not changed and remaining is None:
            changed = self._vision.slot_is_empty("store", card.slot_index, card.target) is True
        if changed and spent is not None and (
                spent == card.price if card.price is not None else spent > 0):
            self._confirmed_purchase_snapshot = (after, coins)
            return ActionResult.CONFIRMED
        return ActionResult.INDETERMINATE

    def _confirm_sale(self, index, character, before_coins):
        after = self._observe_slot("in_hand", index, count_stars=True)
        self._set_observation("in_hand", after)
        if after.state == SlotState.EMPTY:
            return ActionResult.CONFIRMED
        # Coin income is only corroboration within this isolated drag window.
        coins = self.get_coins()
        if before_coins is not None and coins is not None and coins > before_coins:
            if after.state == SlotState.KNOWN and after.character.name != character.name:
                return ActionResult.CONFIRMED

        return ActionResult.INDETERMINATE

    def run(self):
        self._report_runtime_identity()
        self.is_running = True
        if self.runtimes == 0:
            return True
        for i in range(self.runtimes):
            if not self.is_running:
                break
            logger.info(f"第{i + 1}次进入货币战争，剩余{self.runtimes - i - 1}次")
            try:
                started = self.start_game()
                if self._startup_failed:
                    return False
                if started:
                    self.game_loop()
            except ThreadStoppedError:
                self._record_execution_stop("stopped")
                raise
            except Exception as e:
                self._record_execution_stop("error")
                logger.error(e)
                return False
        try:
            self.handle_ending()
            return True
        except ThreadStoppedError:
            self._record_execution_stop("stopped")
            raise
        except Exception as error:
            self._record_execution_stop("error")
            logger.error(error)
            return False

    def handle_ending(self):
        """ 处理游戏结束逻辑，默认退出货币战争页面 """
        self._check_stop()
        if self.operator.wait_img(CWIMG.START_CURRENCY_WARS, timeout=self.PAGE_LOCATE_TIMEOUT) is None:
            self._fail_battle("result_main_menu_missing")
        self._check_stop()
        return self.operator.press_key("esc")

    def reset_character(self):
        """Reset only game state; preserve strategy priorities and definitions."""
        for char in {id(c): c for c in Characters.characters.values()}.values():
            char.is_placed = False
            char.stars = 0
        self.on_field_character[:] = [None] * len(self.on_field_area)
        self.off_field_area = list(self._default_off_field_area)
        self.off_field_character[:] = [None] * len(self.off_field_area)
        self._backend_support_slots = {}
        self.in_hand_character[:] = [None] * len(self.in_hand_area)
        self._observations = {
            area: [SlotObservation(i, SlotState.UNKNOWN) for i in range(len(getattr(self, area + "_area")))]
            for area in ("on_field", "off_field", "in_hand")
        }
        self.max_team_size = 3
        self.is_continue = False
        self._runtime_node_pending = None
        self._last_selection_sent = False
        self._economy_stage_index = None
        self._preparation_round = None
        self._round_read_attempts = 0
        self._all_in_decision = None
        self._equipment_others_checked = False
        self._all_in_budget = None
        self._confirmed_battle_count = 0
        self._pending_battle_id = None
        self._battle_entry_confirmed = False
        self._last_completed_battle_id = None
        self._equipment_battles_since_check = 0
        self._equipment_batch_running = False
        self._equipment_batch_attempts = 0
        self._equipment_metrics = dict(skipped=0, due=0, unconfirmed=0)
        self._confirmed_layout_positions = ()
        self.main_c_first_fielded_confirmed = False
        self._level_cache = None
        self._bench_full = False
        self._equipment_dirty = True
        self._equipment_checked.clear()
        self._equipment_attempts.clear()
        self._equipment_resource_revision += 1
        self._population_read_key = None
        self._sale_population_retry_used = False
        self._effective_targets = None
        self._effective_targets_key = None
        self._preparation_assessment_cache = None
        self._terminal_route_screen = None
        self._formation_plan = ()
        self._formation_plan_stage = None
        self._formation_plan_incomplete = False
        self._purchase_pending_names.clear()
        self._placement_pending = False
        self._observed_prices.clear()
        self._form_change_pending.clear()
        self._dirty_slots.clear()
        self.phase_seconds.clear()
        self._last_shopping_result = None
        self._last_level_read = None
        self._last_coins_read = None

        self._pending_move = None
        self._move_failures.clear()
        self._fielding_rejections.clear()
        self._preparation_deadline = self._formation_deadline = None
        self._preparation_rewards_collected = False
        self._preparation_departure_confirmed = False
        self._field_observed_at = self._bench_observed_at = None
        self._bench_dirty = True
        self._population_current = None
        self._last_health_read = None
        self._last_battle_outcome = "unknown"
        self._terminal_health_read = False
        self._snapshot_revision += 1
        self._layout_revision += 1
        self._layout_valid = True

    def set_difficulty(self, mode: int):
        """设置难度模式：0=最低难度，1=最高难度，2=当前难度（不切换）"""
        self.difficulty = mode

    def set_overclock(self, overclock: bool):
        self.is_overclock = overclock

    def page_locate(self, depth = 0) -> CurrencyWarsPage:
        """
        定位到货币战争页面

        :return: CurrencyWarsPage 枚举值，表示当前所在页面；如果未识别到任何目标页面，则返回 CurrencyWarsPage.UNKNOWN
        """
        if depth>5:
            raise RuntimeError("页面定位递归过深，可能存在无限循环")
        screen = self._vision.read_battle_screen()
        if screen.state in TERMINAL_STATES:
            self._recovery_page = "terminal"
            return CurrencyWarsPage.RECOVERY
        page, _ = self.operator.wait_any_img([IMG.ENTER,
                                              CWIMG.START_CURRENCY_WARS,
                                              CWIMG.PREPARATION_STAGE,
                                              DUIMG.BONUS_POINTS,
                                              CWIMG.BOSS_PREVIEW,
                                              CWIMG.BATTLE, IMG.Q, CWIMG.SETTLE, CWIMG.CONTINUE,
                                              CWIMG.ENCOUNTER_NODE, CWIMG.REPLENISH_STAGE,
                                              CWIMG.FORTUNE_TELLER, CWIMG.SELECT_INVEST_STRATEGY,
                                              CWIMG.NEXT_STEP, CWIMG.CLICK_BLANK],
                                             timeout=self.PAGE_LOCATE_TIMEOUT, interval=0.5)
        if page == 0:
            if self.operator.locate(CWIMG.CURRENCY_WARS): # 货币战争门口
                self.operator.press_key("f")
            else:
                logger.info("[页面定位] 正在定位到货币战争开始页面")
                guide_hotkey = self.settings.General.hotkeyF4
                self.operator.press_key(str(guide_hotkey).lower())
                if not self.operator.wait_img(IMG.F4, timeout=self.ENTRY_TRANSITION_TIMEOUT):
                    logger.error(SRAError(ErrorCode.WAIT_TIMEOUT, "等待指南界面超时"))
                    self.operator.press_key("esc")
                box = self.operator.wait_img(IMG.COSMIC_STRIFE, timeout=self.ENTRY_TRANSITION_TIMEOUT)
                self.operator.click_box(box, after_sleep=1)  # 旷宇纷争
                self.operator.click_point(0.242, 0.30, after_sleep=0.8)  # 货币战争
                self.operator.click_point(0.7786, 0.8194, after_sleep=1)  # 前往参与
            return self.page_locate(depth + 1)
        elif page == 1:
            logger.info("[页面定位] 已定位到货币战争开始页面")
            return CurrencyWarsPage.START
        elif page in (2, 5):
            # An expanded shop can cover the preparation header, but its
            # battle button is still positive evidence of the same page.
            logger.info("[页面定位] 已定位到货币战争准备阶段")
            return CurrencyWarsPage.PREPARATION
        elif page == 3:
            self.operator.press_key("esc")
            return CurrencyWarsPage.START
        elif page == 4:
            logger.info("[页面定位] 已定位到对局首领展示页面")
            return CurrencyWarsPage.BOSS_PREVIEW
        elif page in range(6, 15):
            self._recovery_page = "combat" if page == 6 else "settlement" if page in (7, 8) else "node"
            return CurrencyWarsPage.RECOVERY
        else:
            screen = self._vision.read_battle_screen()
            if screen.state in ("result_ready", "result_animation"):
                self._recovery_page = "settlement"
                return CurrencyWarsPage.RECOVERY
            logger.error("[页面定位] 检测超时，未识别到任何目标页面")
            return CurrencyWarsPage.UNKNOWN

    def start_game(self):
        """开始一局货币战争。
        拆分原复杂流程为多个独立步骤，提升可读性与可维护性。
        返回 True 表示进入对局并完成初始策略与备战席识别
            False 表示流程中断或失败。
        """
        self._startup_failed = False
        self._vision.begin_sample_scope("startup", str(time.time_ns()))
        page = self.page_locate()
        if page == CurrencyWarsPage.UNKNOWN:
            return self._fail_startup("startup_page_not_found", "页面定位失败，无法开始游戏")
        self.is_running = True  # 标记任务运行中
        if not self._handle_page_enter(page):
            return self._fail_startup("startup_entry_failed", "进入对局流程失败")

        self._begin_session()
        if page == CurrencyWarsPage.RECOVERY:
            if not self._recover_live_page():
                return self._fail_startup("startup_recovery_failed", "无法确认恢复后的准备界面")
            if self.is_game_over:
                return True
        if not self.handle_game_entered():
            return False
        # 对局初始化
        init_success = self._initialize_game()
        if not init_success:
            return self._fail_startup("startup_initialization_failed", "对局初始化失败")
        if not self.handle_game_initialized():
            return False
        logger.info("[启动流程] 对局启动成功")
        self.is_game_over = False
        return True

    def _fail_startup(self, reason: str, message: str) -> bool:
        # RerollStart deliberately returns False from lifecycle hooks; only
        # confirmed entry/initialization failures must abort the whole task.
        self._startup_failed = True
        self.is_running = False
        logger.error(f"[启动流程] {message}")
        sample = self._vision.capture_sample(reason, {"evidence": message}, critical=True)
        logger.info(f"[启动诊断] 保存原因={self._vision.last_sample_reason}")
        if sample is not None:
            logger.warning(f"[启动诊断] 已保存失败时游戏画面：{sample}")
        return False

    def _handle_page_enter(self, page: CurrencyWarsPage) -> bool:
        """
        根据页面类型处理进入逻辑
        :param page: 页面枚举值
        :return: True-进入成功，False-进入失败
        """
        if page == CurrencyWarsPage.START:
            # 开始页面 → 执行进入流程
            return self._enter_from_start_page()
        elif page == CurrencyWarsPage.BOSS_PREVIEW:
            # A stopped startup may already have entered a new game. Resume
            # the existing boss/environment hooks without re-clicking entry.
            logger.info("[进入流程] 已在对局首领展示页，继续下一步")
            self.reset_character()
            if not self._handle_boss_info_flow():
                return False
            return self._handle_invest_environment_flow()
        elif page == CurrencyWarsPage.PREPARATION:
            # 准备阶段 → 跳过进入流程
            self.is_continue = True
            logger.info("[进入流程] 已处于准备阶段，跳过进入流程")
            return True
        elif page == CurrencyWarsPage.RECOVERY:
            self.is_continue = True
            self.is_game_over = False
            return True
        else:
            return False

    def _resume_battle_phase(self, phase, *, after_sleep, evidence):
        """Shared takeover of an observed combat/result page; never replay Battle."""
        if phase == "combat" and self._pending_battle_id is None:
            self._pending_battle_id = str(uuid.uuid4())
            if not self._record_checkpoint(pending_battle_id=self._pending_battle_id):
                return None
        if self._pending_battle_id is not None:
            self._battle_entry_confirmed = True
            if not self._record_checkpoint(confirmed_event="battle_entered:" + self._pending_battle_id):
                return None
        box, point, ready = self._wait_battle_result(in_combat=phase == "combat")
        if box is None and point is None and not ready:
            return None
        # Completion is authenticated by the result, independent of whether the
        # navigation click succeeds. Counting the same battle remains idempotent.
        self._confirm_completed_battle(evidence)
        if ready:
            return True
        self._check_stop()
        if box is not None:
            return self.operator.click_box(box, after_sleep=after_sleep)
        return self.operator.click_point(*point, after_sleep=after_sleep, tag="恢复：继续挑战")

    def _recover_live_page(self):
        # The current observed page decides recovery. Stored summaries are
        # history only and never authorize repeating a purchase/drag/selection.
        phase = getattr(self, "_recovery_page", "node")
        if phase == "terminal":
            return self.handle_game_over(None)
        if phase in ("combat", "settlement"):
            if not self._resume_battle_phase(phase, after_sleep=self.STAGE_SETTLE_SECONDS,
                                             evidence="resumed_settlement_or_stage"):
                return False
        if not self.stage_transition():
            return False
        self._confirm_completed_battle("resumed_post_battle_node")
        if self.is_game_over:
            return True
        self._record_checkpoint(phase="preparation", pending_actions=[])
        return True

    # ==================== 进入流程辅助方法 ====================
    def _enter_from_start_page(self) -> bool:
        """
        从开始页面进入对局
        :return: True-进入成功，False-进入失败
        """
        # 等待开始按钮
        index, box = self.operator.wait_any_img(
            [CWIMG.START_CURRENCY_WARS, CWIMG.INSTRUCTIONS],
            timeout=self.PAGE_LOCATE_TIMEOUT,
            interval=0.5
        )
        if index == -1:
            logger.error("[进入流程] 未识别到开始按钮")
            return False
        if index == 1:
            self.operator.press_key("esc")  # 赛季扩充说明
            box = self.operator.wait_img(CWIMG.START_CURRENCY_WARS,
                                         timeout=self.PAGE_LOCATE_TIMEOUT)  # 重新获取开始游戏按钮
        if box is None:
            logger.error("[进入流程] 关闭说明后仍未找到开始按钮")
            return False
        # Preserve the original successful entry sequence: stop clicking when
        # the destination LOGO appears. Waiting for disappearance clicks again
        # after the page has already changed (2026-10-08 startup regression).
        if not self.operator.do_while(
            lambda: self.operator.click_box(box),  # NOQA  # pyright: ignore[reportArgumentType]
            lambda: self.operator.locate(CWIMG.LOGO) is None,
            interval=2,
            max_iterations=10
        ):
            logger.warning('点击开始按钮达到重试上限')
            return False
        self.operator.sleep(1)  # 等待界面响应
        if self.is_overclock:
            self.operator.click_point(0.15625, 0.4167, after_sleep=1, tag="点击超频博弈")
        else:
            self.operator.click_point(0.15625, 0.2315, after_sleep=1, tag="点击标准博弈")

        # 选择进入方式（标准进入/继续进度）
        enter_type, enter_box = self.operator.wait_any_img(
            [CWIMG.ENTER_GAME, CWIMG.CONTINUE_PROGRESS],
            timeout=self.ENTRY_TRANSITION_TIMEOUT
        )
        if enter_box is None:
            logger.error("[进入流程] 未识别到任何进入方式（标准/继续）")
            return False

        # 执行对应进入逻辑
        if enter_type == 0:  # 标准进入
            return self._enter_new_game(enter_box)
        elif enter_type == 1:  # 继续进度
            return self._enter_continue_game(enter_box)

        return False

    def _enter_new_game(self, enter_button_box) -> bool:
        """
        新游戏进入流程
        :param enter_button_box: 进入按钮坐标框
        :return: True-成功，False-失败
        """
        self.reset_character()
        # 1. 点击进入按钮
        if not self.operator.click_box(enter_button_box, after_sleep=1.5):
            logger.error("[新游戏] 点击进入按钮失败")
            return False

        # 2. 难度选择
        if not self._select_difficulty():
            return False

        # 3. 点击开始对局
        if not self.operator.click_img(CWIMG.START_GAME, after_sleep=1):
            logger.error("[新游戏] 点击开始对局按钮失败")
            return False

        # 4. 处理Boss信息
        if not self._handle_boss_info_flow():
            return False

        # 5. 处理投资环境
        return self._handle_invest_environment_flow()

    def _select_difficulty(self) -> bool:
        """难度选择逻辑（抽离后更易维护）"""
        self._check_stop()
        if self.difficulty == Difficulty.HIGHEST:
            # 最高难度：点击返回最高职级
            logger.info("[难度选择] 选择最高难度")
            self.operator.click_img(CWIMG.RETURN_HIGHEST_RANK, after_sleep=0.8)
        elif self.difficulty == Difficulty.LOWEST:
            # The arrow disappearing alone is not evidence of the lowest rank:
            # the selection page itself must still be visible on two reads.
            logger.info("[难度选择] 选择最低难度")
            deadline = time.monotonic() + self.DIFFICULTY_SELECTION_TIMEOUT
            clicks, ready_frames = 0, 0
            while time.monotonic() < deadline:
                self._check_stop()
                index, box = self.operator.locate_any(
                    [CWIMG.DOWN_ARROW, CWIMG.START_GAME], trace=False)
                self._check_stop()
                if time.monotonic() >= deadline:
                    break
                if box is not None and index == 1:
                    ready_frames += 1
                    if ready_frames >= 2:
                        return True
                else:
                    ready_frames = 0
                    if box is not None and index == 0:
                        if clicks >= self.DIFFICULTY_MAX_CLICKS:
                            logger.error("[难度选择] 降低职级达到点击上限，停止启动")
                            return False
                        if not self.operator.click_box(box, after_sleep=0.5):
                            logger.error("[难度选择] 降低职级点击失败，停止启动")
                            return False
                        clicks += 1
                self.operator.sleep(0.3)
            logger.error("[难度选择] 未能在时限内确认最低职级，停止启动")
            return False
        elif self.difficulty == Difficulty.CURRENT:
            # 当前难度：不操作
            logger.info("[难度选择] 保持当前难度")
        else:
            logger.warning(f"[难度选择] 未知难度模式：{self.difficulty}，使用当前难度")
        self._check_stop()
        return True

    def _handle_boss_info_flow(self) -> bool:
        """处理Boss信息流程（抽离独立方法）"""
        # 等待下一步提示
        next_step_box = self.operator.wait_img(
            CWIMG.NEXT_STEP,
            timeout=self.ENTRY_TRANSITION_TIMEOUT
        )
        if not next_step_box:
            logger.error("[Boss信息] 未识别到下一步提示")
            return False

        # 处理Boss信息 + 点击下一步
        self.operator.sleep(0.5)
        self.handle_boss_info()
        if not self.operator.click_box(next_step_box, after_sleep=2):
            logger.error("[Boss信息] 点击下一步按钮失败")
            return False
        # 点击空白处
        self.operator.click_point(0.5, 0.5, after_sleep=0.5, tag="点击空白处")
        return True

    def _handle_invest_environment_flow(self) -> bool:
        # 检查投资环境界面
        if not self.operator.wait_img(CWIMG.INVEST_ENVIRONMENT,
                                      timeout=self.ENTRY_TRANSITION_TIMEOUT):
            logger.error("[投资环境] 未识别到投资环境界面")
            return False
        self.operator.sleep(1)  # 等待界面稳定
        self.handle_invest_environment()
        # 有些情况下点击投资环境界面后会再次弹出投资环境界面，需要再次处理
        if self.operator.locate(CWIMG.INVEST_ENVIRONMENT):
            self.handle_invest_environment()
        self.operator.sleep(4)
        return True

    # ==================== 继续进度进入逻辑（重构后） ====================
    def _enter_continue_game(self, continue_button_box) -> bool:
        """
        继续进度进入流程（重构后，异常处理更规范）
        :param continue_button_box: 继续按钮坐标框
        :return: True-成功，False-失败
        """
        self.is_continue = True
        # 点击继续按钮
        if not self.operator.click_box(continue_button_box, after_sleep=1):
            logger.error("[继续进度] 点击继续按钮失败")
            return False

        try:
            # 等待空白提示并点击
            self.operator.sleep(2)
            click_blank_box = self.operator.wait_img(
                CWIMG.CLICK_BLANK,
                timeout=self.ENTRY_TRANSITION_TIMEOUT
            )
            if not click_blank_box:
                logger.error("[继续进度] 未识别到点击空白提示")
                return False
            self.operator.click_box(click_blank_box, after_sleep=2)
            logger.info("[继续进度] 进入对局成功")
            return True
        except ThreadStoppedError:
            raise
        except Exception as e:
            logger.error(f"[继续进度] 流程异常：{str(e)}", exc_info=True)
            return False

    # ==================== 对局初始化（重构后） ====================
    def _initialize_game(self) -> bool:
        """
        对局初始化（重构后，区分继续进度和新游戏）
        :return: True-初始化成功，False-初始化失败
        """
        self.operator.sleep(1)
        if self.is_continue:
            # 继续进度：获取前台角色信息
            logger.info("[初始化] 继续进度")
            if not self._set_shop_open(False):
                logger.warning("[初始化] 继续进度的准备界面尚未确认，暂停场地识别")
                return False
            if self._pending_battle_id is not None:
                if self._battle_entry_confirmed:
                    self._confirm_completed_battle("resumed_confirmed_preparation")
                else:
                    if not self._record_checkpoint(pending_battle_id=None):
                        self._fail_battle("battle_checkpoint_not_saved")
                    self._pending_battle_id = None
                    logger.warning("[真实战斗] 准备页已确认；清除缺入战证据的旧点击意图，不计战斗")
            self.refresh_character(equip=False)
        else:
            for area in ('on_field', 'off_field'):
                self._observations[area] = [SlotObservation(i, SlotState.EMPTY, occupied=False,
                    evidence='new_game_empty') for i in range(len(getattr(self, area + '_area')))]
        # Fresh games start with an empty field; continued games must be observed.
        return True

    def handle_boss_info(self) -> None:
        """处理进入对局后可能出现的Boss信息提示框。

        如果需要额外的操作（如记录Boss信息、调整策略等），可以在此方法中实现。"""
        ...

    def handle_invest_environment(self) -> None:
        """处理投资环境界面

        标准模式下，简单地选择中间的投资环境或选择尚未收集的投资环境，点击确定即可。
        """
        if not self.operator.click_img(CWIMG.COLLECTION):
            self.operator.click_point(0.5, 0.5, tag="选择中间的投资环境")
        self.operator.click_img(IMG.ENSURE2, after_sleep=1)
        if self.operator.locate(CWIMG.INVEST_ENVIRONMENT):
            self.operator.click_point(0.5, 0.5, after_sleep=1)
            self.operator.click_img(IMG.ENSURE2, after_sleep=1)

    def handle_game_entered(self) -> bool:  # NOQA
        """Apply a new game's guide before initialization; reroll hooks stay independent."""
        if not self.strategy_code or self.is_continue:
            return True
        step = "open_strategy"
        try:
            self._check_stop()
            box = self.operator.wait_img(CWIMG.STRATEGY, timeout=self.ENTRY_TRANSITION_TIMEOUT)
            self._check_stop()
            if box is None or not self.operator.click_box(box, after_sleep=1):
                return self._fail_startup("strategy_open_failed", "未能打开攻略页面")

            step = "open_code_entry"
            # Real successful runs already show the code-entry button while
            # HOT_STRATEGIES is absent. Only navigate when necessary.
            entry = self.operator.locate(CWIMG.ENTER_STRATEGY_CODE, trace=False)
            if entry is None:
                hot = self.operator.locate(CWIMG.HOT_STRATEGIES, trace=False)
                self._check_stop()
                if hot is not None and not self.operator.click_box(hot, after_sleep=1):
                    return self._fail_startup("strategy_navigation_failed", "切换攻略页面失败")
                entry = self.operator.wait_img(CWIMG.ENTER_STRATEGY_CODE,
                                               timeout=self.ENTRY_TRANSITION_TIMEOUT)
            self._check_stop()
            if entry is None or not self.operator.click_box(entry, after_sleep=1):
                return self._fail_startup("strategy_code_entry_failed", "未能打开攻略码输入框")
            if self.operator.wait_img(IMG.ENSURE2, timeout=self.ENTRY_TRANSITION_TIMEOUT) is None:
                return self._fail_startup("strategy_code_dialog_missing", "攻略码输入页面未确认")
            self._check_stop()
            if not self.operator.click_point(0.5, 0.5, after_sleep=1, tag="攻略码输入框"):
                return self._fail_startup("strategy_code_focus_failed", "攻略码输入框点击失败")
            step = "paste_code"
            self._check_stop()
            self.operator.copy(self.strategy_code)
            self._check_stop()
            self.operator.paste()
            self.operator.sleep(1)

            step = "confirm_code"
            confirm = self.operator.wait_img(IMG.ENSURE2, timeout=self.ENTRY_TRANSITION_TIMEOUT)
            self._check_stop()
            if confirm is None or not self.operator.click_box(confirm, after_sleep=1):
                return self._fail_startup("strategy_code_confirm_failed", "攻略码提交失败")
            step = "apply_strategy"
            apply = self.operator.wait_img(CWIMG.APPLY_STRATEGY, timeout=self.ENTRY_TRANSITION_TIMEOUT)
            self._check_stop()
            if apply is None or not self.operator.click_box(apply, after_sleep=1):
                return self._fail_startup("strategy_apply_failed", "未能应用分享码对应攻略")
            # Existing 'cancel application' artwork is positive evidence that
            # the guide was applied. A sent click or a vanished button is not.
            if not self._confirm_startup_images((self.STRATEGY_APPLIED_IMAGE,),
                                                self.ENTRY_TRANSITION_TIMEOUT):
                return self._fail_startup("strategy_apply_unconfirmed", "攻略应用结果未确认")

            step = "return_to_preparation"
            for escapes in range(4):
                if self._confirm_startup_images((CWIMG.PREPARATION_STAGE, CWIMG.BATTLE), 3):
                    logger.info("[启动流程] 攻略已应用并返回准备界面")
                    return True
                self._check_stop()
                if escapes == 3:
                    break
                if not self.operator.press_key("esc"):
                    return self._fail_startup("strategy_return_failed", "退出攻略页面失败")
                self.operator.sleep(0.5)
            return self._fail_startup("strategy_return_unconfirmed", "应用攻略后未能确认准备界面")
        except ThreadStoppedError:
            raise
        except Exception as error:
            return self._fail_startup("strategy_import_error",
                                      f"攻略导入异常，步骤={step}：{error}")

    def _confirm_startup_images(self, templates, timeout):
        """Require two fresh positive observations without sending more input."""
        deadline = time.monotonic() + timeout
        stable = 0
        while time.monotonic() < deadline:
            self._check_stop()
            index, box = self.operator.locate_any(list(templates), trace=False)
            self._check_stop()
            if time.monotonic() >= deadline:
                break
            stable = stable + 1 if box is not None and index >= 0 else 0
            if stable >= 2:
                return True
            self.operator.sleep(0.3)
        return False

    def handle_game_initialized(self) -> bool:  # NOQA
        """对局初始化完成后的处理逻辑（如有）。默认实现为无操作，子类可重写此方法以添加额外逻辑。

        调用时机：在完成角色放置和备战席识别后、正式进入游戏循环前调用
        Returns:
            True-继续执行游戏循环；False-中止进入流程
        """
        return True

    def abort_and_return(self) -> bool:
        """中止当前对局并返回开始页面"""
        logger.info("中止当前对局并返回开始页面")
        index, box = self.operator.wait_any_img([CWIMG.QUIT, CWIMG.WITHDRAW_AND_SETTLE])
        if index<0:
            return False
        if index == 0:
            self.operator.click_box(box, after_sleep=1)
            self.operator.click_img(CWIMG.WITHDRAW_AND_SETTLE)
        elif index == 1:
            self.operator.click_box(box)
        b = self.operator.wait_img(CWIMG.NEXT_STEP)
        if b is None:
            return False
        self.handle_game_over(None)
        return True

    def _ensure_shopping_observations(self, *, force=False):
        """Resolve incomplete board evidence before opening an economy shop."""
        if self.economy_config is None and not force:
            return True
        while True:
            self._check_stop()
            for area, observations in self._observations.items():
                for index, obs in enumerate(observations):
                    missing = observation_identity(obs) is None or (
                        obs.state == SlotState.KNOWN and not getattr(obs.character, "is_npc", False)
                        and (type(obs.stars) is not int or not 1 <= obs.stars <= 3))
                    if missing or (area, index) in self._dirty_slots:
                        if area == "in_hand":
                            self._bench_dirty = True
                        else:
                            self._dirty_slots.add((area, index))
            if self._layout_valid and not self._dirty_slots and not self._bench_dirty:
                return True
            # Use the preparation's existing recovery allowance. A first main
            # carry may still be absent; only existing evidence must be known.
            self._resume_shopping_after(ShoppingResult(
                ActionResult.INDETERMINATE, reason="purchase_targets_unknown"))

    def _shopping_evidence_gaps(self):
        gaps = []
        if not self._layout_valid:
            diagnostics = getattr(self._vision, "last_layout_diagnostics", {})
            reason = (diagnostics.get("evidence", "backend_layout_not_confirmed")
                      if isinstance(diagnostics, dict) else "backend_layout_not_confirmed")
            gaps.append("layout=" + str(reason))
        for area, observations in self._observations.items():
            missing = [f"{index}:{obs.evidence}" for index, obs in enumerate(observations)
                       if observation_identity(obs) is None or (area, index) in self._dirty_slots
                       or (obs.state == SlotState.KNOWN and not getattr(obs.character, "is_npc", False)
                           and (type(obs.stars) is not int or not 1 <= obs.stars <= 3))]
            if missing:
                gaps.append(area + "=[" + ",".join(missing) + "]")
        return "; ".join(gaps) or "no_slot_gap"

    def _resume_shopping_after(self, result):
        """Re-observe missing evidence before continuing the same shop allowance."""
        if (self.economy_config is None and self._preparation_round != (3, 7)
                and not result.reason.startswith("final_round_")):
            if result.result != ActionResult.CONFIRMED:
                raise RuntimeError("购物动作未确认：" + result.reason)
            return False
        prepare_reasons = {"main_c_placement", "role_placement",
                           "candidate_needs_preparation", "purchase_space_blocked"}
        recover_reasons = {"purchase_recheck_unknown", "purchase_targets_unknown",
            "purchase_space_unknown", "upgrade_gate_unknown", "upgrade_gate_demand_unknown",
            "unknown_level", "unknown_coins", "economy_gold_not_confirmed",
            "purchase_evidence_unknown", "full_shop_recovery_unknown",
            "shop_not_open_after_recheck", "unknown", "partial_store",
            "final_round_unknown", "final_round_page_unknown",
            "final_round_experience_unknown", "final_round_upgrade_not_confirmed",
            "final_round_refresh_not_confirmed"}
        if result.reason in recover_reasons:
            attempts = getattr(self, "_economy_recovery_attempts", 0)
            if attempts >= self.preparation_budget["recoveries"]:
                raise RuntimeError("购物证据恢复无进展：" + result.reason
                                   + "；当前缺口=" + self._shopping_evidence_gaps())
            self._economy_recovery_attempts = attempts + 1
            logger.info(f"[购物恢复] 原因={result.reason} 补读={attempts + 1}，沿用本准备期购物额度")
            self._check_stop()
            if not self._set_shop_open(False):
                raise RuntimeError("购物恢复未确认准备界面")
            self._invalidate_level()
            if result.reason == "final_round_unknown":
                self._round_read_attempts = 0
            if not self._layout_valid:
                logger.info("[购物恢复] 后台布局失效，先重新确认完整布局和角色")
                self.refresh_backend_character(equip=False, recover_layout=True)
                if not self._layout_valid:
                    # A later bounded recovery may retry the layout. Reading
                    # individual slots cannot repair missing layout evidence.
                    logger.warning("[购物恢复] 后台布局仍未确认，保留未知状态等待下一次恢复")
                    return True
            for area in ("on_field", "off_field"):
                for i, obs in enumerate(self._observations[area]):
                    if obs.state == SlotState.UNKNOWN or (obs.character is not None and obs.stars is None):
                        self._dirty_slots.add((area, i))
            self._refresh_dirty_field()
            if self._bench_dirty or any(o.state == SlotState.UNKNOWN for o in self._observations["in_hand"]):
                self.get_in_hand_area(True)
            return True
        if result.reason not in prepare_reasons:
            if result.result != ActionResult.CONFIRMED:
                raise RuntimeError("购物动作未确认：" + result.reason)
            return False
        before = self._preparation_recovery_signature()
        recovered = self.prepare_for_battle()
        if recovered.state == Readiness.BLOCKED:
            self._fail_battle("preparation_" + recovered.reason)
        self._check_stop()
        sale = self.sell_character()
        if sale.attempted and sale.result != ActionResult.CONFIRMED:
            raise RuntimeError("出售动作未确认：" + sale.reason)
        if before == self._preparation_recovery_signature():
            if self._preparation_round == (3, 7):
                raise RuntimeError("3-7终局整备无进展，禁止在金币尚未消费完时进入战斗")
            logger.info("[经济决策] action=save reason=preparation_no_progress")
            return False
        return True

    def _capture_page_frame(self):
        """A frame belongs to one observation pass, never to the next input action."""
        self._check_stop()
        capture = getattr(self.operator, "screenshot", None)
        if not callable(capture):
            return None
        try:
            frame = capture()
        except ThreadStoppedError:
            raise
        except Exception:
            return None
        self._check_stop()
        return frame

    def _locate_page_template(self, template, frame):
        self._check_stop()
        if frame is None:
            return self.operator.locate(template, trace=False)
        try:
            import pyscreeze
            match = pyscreeze.locate(template, frame, confidence=self.operator.tm_confidence)
        except ThreadStoppedError:
            raise
        except Exception:
            return None
        self._check_stop()
        return Box(*match, source=template) if match is not None else None

    def _runtime_advance_candidate(self, frame=None):
        """Recognize navigation labels, never arbitrary clickable shop choices."""
        for template, label in ((CWIMG.CLICK_BLANK, "点击空白处关闭"),
                                (CWIMG.NEXT_STEP, "下一步")):
            self._check_stop()
            box = self._locate_page_template(template, frame)
            if box is not None:
                return label, box
        read_boxes = getattr(self.operator, "ocr_boxes", None)
        if frame is None and not callable(read_boxes):
            return None
        allowed = {"下一步", "下一页", "继续", "继续挑战", "进入下阶段", "进入下一阶段",
                   "前往下一阶段", "点击屏幕", "点击屏幕继续", "点击任意处继续",
                   "点击任意位置继续", "点击空白处继续", "点击空白继续",
                   "点击空白处关闭", "点击空白加速"}
        if frame is None:
            boxes = read_boxes(from_x=0.05, from_y=0.35, to_x=0.95, to_y=0.98,
                               confidence=0.9, trace=False)
        else:
            width, height = self.operator.window_context.width, self.operator.window_context.height
            roi = (width * 0.05, height * 0.35, width * 0.95, height * 0.98)
            left, top = int(roi[0]), int(roi[1])
            try:
                rows = self._vision._engine_ocr(frame.crop(roi).convert("L"),
                                                minimum_confidence=0.9)
            except ThreadStoppedError:
                raise
            except Exception:
                rows = None
            boxes = []
            for row in rows or ():
                try:
                    # Match operator.ocr_boxes' strict confidence threshold,
                    # including engines that return unfiltered legacy tuples.
                    if not isinstance(row[1], str) or not row[2] > 0.9:
                        continue
                    boxes.append(Box(row[0][0][0] + left, row[0][0][1] + top,
                        row[0][2][0] - row[0][0][0], row[0][2][1] - row[0][0][1], source=row[1]))
                except (IndexError, TypeError, ValueError):
                    continue
        self._check_stop()
        candidates = []
        for box in boxes or ():
            label = re.sub(r"[\s·。！!…]", "", box.source)
            if label in allowed:
                candidates.append((label, box))
        return candidates[0] if len(candidates) == 1 else None

    def _probe_runtime_page(self):
        """Restart page classification without resetting the current game."""
        self._check_stop()
        frame = self._capture_page_frame()
        probability_close = self._read_shop_probability_overlay(frame)
        if probability_close is not None:
            return "shop_probability", probability_close
        screen = self._vision.read_battle_screen(frame) if frame is not None else self._vision.read_battle_screen()
        if screen.state in TERMINAL_STATES:
            return "terminal", screen
        if screen.state in ("result_ready", "result_animation"):
            return "settlement", screen
        if self._locate_page_template(CWIMG.CONTINUE, frame) is not None:
            return "settlement", None
        if self._locate_page_template(CWIMG.SETTLE, frame) is not None:
            return "settlement", None
        if self._locate_page_template(IMG.Q, frame) is not None:
            return "combat", None
        advance = self._runtime_advance_candidate(frame)
        if advance is not None:
            return "advance", advance
        nodes = (CWIMG.ENCOUNTER_NODE, CWIMG.REPLENISH_STAGE,
                 CWIMG.FORTUNE_TELLER, CWIMG.SELECT_INVEST_STRATEGY)
        for node in nodes:
            if self._locate_page_template(node, frame) is not None:
                return "node", node
        if self._locate_page_template(CWIMG.START_CURRENCY_WARS, frame) is not None:
            return "main_menu", None
        if any(self._locate_page_template(template, frame) is not None
               for template in (CWIMG.FOLD, CWIMG.PREPARATION_STAGE, CWIMG.BATTLE)):
            return "preparation", None
        return "unknown", None

    @staticmethod
    def _same_runtime_page(first, second):
        if first[0] != second[0] or first[0] == "unknown":
            return False
        if first[0] == "advance":
            a, b = first[1], second[1]
            return a[0] == b[0] and max(abs(x - y) for x, y in zip(a[1].center, b[1].center)) <= 24
        if first[0] == "shop_probability":
            return max(abs(a - b) for a, b in zip(first[1], second[1])) <= 0.005
        return first[1] == second[1] if first[0] == "node" else True

    def _recover_runtime_flow(self, error, attempt=1):
        """Bounded page recovery: navigation only, preserving in-flight actions."""
        self._check_stop()
        logger.warning(f"[流程恢复] 第{attempt}次，从当前画面重新定位：{error}")
        self._vision.capture_sample("runtime_recovery", {"evidence": str(error)[:240]}, critical=True)
        recovery_started = time.monotonic()
        deadline = recovery_started + self.FLOW_RECOVERY_SECONDS
        old_deadlines = self._preparation_deadline, self._formation_deadline
        battle_before_recovery = self._last_completed_battle_id
        # Page navigation has a separate bound; do not renew preparation budgets.
        self._preparation_deadline = self._formation_deadline = None
        actions = {}
        try:
            for _ in range(self.FLOW_RECOVERY_STEPS):
                self._check_stop()
                if time.monotonic() >= deadline:
                    break
                first = self._probe_runtime_page()
                self.operator.sleep(0.3)
                current = self._probe_runtime_page()
                if not self._same_runtime_page(first, current):
                    continue
                phase, payload = current
                logger.info(f"[流程恢复] 已定位阶段={phase}")
                if phase == "shop_probability":
                    if actions.get(phase, 0) >= 1:
                        break
                    self._check_stop()
                    actions[phase] = 1
                    if not self.operator.click_point(*payload, after_sleep=0.5,
                            tag="恢复：关闭商店刷新概率"):
                        return False
                    continue
                if phase == "preparation":
                    if not self._set_shop_open(False):
                        continue
                    if self._pending_battle_id is not None:
                        if self._battle_entry_confirmed:
                            self._confirm_completed_battle("recovered_confirmed_preparation")
                        else:
                            if not self._record_checkpoint(pending_battle_id=None):
                                return False
                            self._pending_battle_id = None
                    self._invalidate_level()
                    self._population_read_key = None
                    same_preparation = (old_deadlines[0] is not None
                        and not self._preparation_departure_confirmed
                        and self._last_completed_battle_id == battle_before_recovery
                        and not any(action != "shop_probability" for action in actions))
                    if same_preparation:
                        logger.info("[准备恢复] 仍在同一准备期，保留已完成收集和可靠槽位，只补读缺口")
                        if self._purchase_pending_names:
                            # An input can succeed before its confirmation fails.
                            # Recheck possible merges even if dirtiness was not recorded yet.
                            self._bench_dirty = True
                            self._dirty_slots.update((area, index)
                                for area in ("on_field", "off_field")
                                for index, obs in enumerate(self._observations[area])
                                if obs.character is not None
                                and obs.character.name in self._purchase_pending_names)
                    else:
                        # A battle, reward node or page advance may alter the roster.
                        self._preparation_rewards_collected = False
                        self._preparation_round = None
                        self._round_read_attempts = 0
                        self._bench_dirty = True
                        self._field_observed_at = None
                    if not self._layout_valid:
                        self.refresh_backend_character(equip=False, recover_layout=True)
                        if not self._layout_valid:
                            return False
                    self._runtime_node_pending = None
                    self._last_selection_sent = False
                    self._record_checkpoint(phase="preparation", execution_status="running")
                    return True
                if phase == "main_menu":
                    self.handle_main_menu(None)
                    return True
                if phase == "terminal":
                    return self.handle_game_over(None, first_screen=payload)
                if phase in ("combat", "settlement"):
                    if actions.get(phase, 0) >= 1:
                        break
                    actions[phase] = 1
                    resumed = self._resume_battle_phase(phase, after_sleep=0.5,
                                                        evidence="recovered_settlement_or_stage")
                    if resumed is None:
                        break
                    if not resumed:
                        continue
                    # A real battle can outlast the short page-navigation budget.
                    deadline = time.monotonic() + self.FLOW_RECOVERY_SECONDS
                    continue
                if phase == "advance":
                    label, box = payload
                    if actions.get(label, 0) >= 2:
                        break
                    actions[label] = actions.get(label, 0) + 1
                    self._check_stop()
                    if label == "点击空白处关闭":
                        self.operator.click_point(0.5, 0.70, after_sleep=0.5, tag="恢复：" + label)
                    else:
                        self.operator.click_box(box, after_sleep=0.5)
                    logger.info(f"[流程恢复] 推进={label}，重新识别下一画面")
                    continue
                if phase == "node":
                    pending_node = getattr(self, "_runtime_node_pending", None)
                    if pending_node is not None and pending_node != payload:
                        # Two fresh frames prove the previous node departed.
                        self._runtime_node_pending = None
                        self._last_selection_sent = False
                    if (actions.get(payload, 0) >= 1 or self._runtime_node_pending == payload
                            or self._last_selection_sent):
                        logger.warning("[流程恢复] 选择动作尚未确认，保留现场，禁止重复选择")
                        break
                    self._confirm_completed_battle("recovered_post_battle_node")
                    handlers = {CWIMG.ENCOUNTER_NODE: self.handle_encounter_node,
                        CWIMG.REPLENISH_STAGE: self.handle_replenish_stage,
                        CWIMG.FORTUNE_TELLER: self._handle_fortune_teller_after_battle,
                        CWIMG.SELECT_INVEST_STRATEGY: self.handle_invest_strategy}
                    actions[payload] = 1
                    self._runtime_node_pending = payload
                    handlers[payload](None)
            self._vision.capture_sample("runtime_recovery_no_progress",
                {"evidence": "no_confirmed_preparation_or_terminal_after_bounded_recovery"}, critical=True)
            return False
        except ThreadStoppedError:
            raise
        except Exception as recovery_error:
            logger.warning(f"[流程恢复] 未能完成：{recovery_error}")
            return False
        finally:
            elapsed = time.monotonic() - recovery_started
            # Navigation has its own finite allowance. Preserve any remaining
            # preparation time, but never revive a budget already exhausted.
            self._preparation_deadline, self._formation_deadline = (
                value + elapsed if value is not None and value > recovery_started else value
                for value in old_deadlines)

    def handle_next_step(self, _previous=None):
        # NEXT_STEP is shared by startup/transition/final pages. Only the
        # terminal recognizer may interpret it as a game result.
        screen = self._vision.read_battle_screen()
        if screen.state in TERMINAL_STATES:
            return self.handle_game_over(None, first_screen=screen)
        self._check_stop()
        first = self.operator.locate(CWIMG.NEXT_STEP, trace=False)
        self.operator.sleep(0.3)
        second = self.operator.locate(CWIMG.NEXT_STEP, trace=False)
        self._check_stop()
        if first is None or second is None or max(abs(x - y) for x, y in zip(first.center, second.center)) > 24:
            raise RuntimeError("下一步按钮尚未稳定")
        if not self.operator.click_box(second, after_sleep=0.5):
            raise RuntimeError("下一步按钮点击失败")
        return False

    def game_loop(self):
        first_preparation = self._confirmed_battle_count == 0
        recovery_attempts = 0
        try:
            while self.is_running and not self.is_game_over:
                battle_before = self._last_completed_battle_id
                try:
                    round_started = time.monotonic()
                    phase_before = dict(self.phase_seconds)
                    self._check_stop()
                    resuming_preparation = self._preparation_deadline is not None
                    self._begin_preparation()
                    if not self._preparation_rewards_collected:
                        with self._timed("crystals"):
                            self.harvest_crystals()
                    else:
                        logger.info("[准备恢复] 本准备期已收集水晶，跳过重复收集")
                    with self._timed("bench_scan"):
                        # Rewards can alter any bench slot. Within a preparation,
                        # purchases and moves already mark the affected evidence.
                        if self._bench_dirty or self._bench_observed_at is None:
                            self.get_in_hand_area(True)
                    if (self._field_observed_at is None or (not resuming_preparation
                            and time.monotonic() - self._field_observed_at
                            >= self.preparation_budget["field_refresh_seconds"])):
                        with self._timed("field_full_scan"):
                            self.refresh_character(equip=False)
                    if self._placement_pending and not self._resolve_pending_move():
                        recovered = self.prepare_for_battle()
                        if recovered.state == Readiness.BLOCKED:
                            self._fail_battle("preparation_" + recovered.reason)
                    with self._timed("dirty_field_scan"):
                        self._refresh_dirty_field()
                    self._empty_roster_needs_shop = False
                    self.handle_characters_updated()
                    self.update_max_team_size()
                    with self._timed("placement"):
                        self.place_character()
                    with self._timed("selling"):
                        sale = self.sell_character()
                    if sale.attempted and sale.result != ActionResult.CONFIRMED:
                        raise RuntimeError("出售动作未确认：" + sale.reason)
                    # Opening protection also buys targets from the natural
                    # first shop, after deploying the available starting hand.
                    if (not first_preparation or self.opening_policy_config is not None
                            or self._read_preparation_round() in (None, (3, 7))):
                        shopping_passes = 0
                        while True:
                            with self._timed("shopping"):
                                shopping_result = self.shopping()
                            if not self._resume_shopping_after(shopping_result):
                                break
                            shopping_passes += 1
                            # Final-round recovery is bounded by evidence recovery,
                            # never by a strategy's ordinary shopping allowance.
                            if (self._preparation_round is not None and self._preparation_round != (3, 7)
                                    and shopping_passes >= self.shopping_budget["actions"] + 1):
                                break
                    with self._timed("preparation_confirmation"):
                        prepared = self.prepare_for_battle()
                    if prepared.state == Readiness.BLOCKED:
                        self._fail_battle("preparation_" + prepared.reason)
                    # Use cached observations to skip this entire pass unless
                    # there is surplus, or an unknown population can be retried.
                    if self._needs_pre_battle_cleanup():
                        population_before_sale = self._population_current, self.max_team_size
                        with self._timed("selling"):
                            final_sale = self.sell_character()
                        if final_sale.attempted and final_sale.result != ActionResult.CONFIRMED:
                            raise RuntimeError("出战前出售动作未确认：" + final_sale.reason)
                        sale = replace(final_sale, attempted=sale.attempted + final_sale.attempted,
                                       confirmed=sale.confirmed + final_sale.confirmed)
                        if final_sale.confirmed:
                            logger.info(f"[出战前余牌清理] 已确认出售={final_sale.confirmed}")
                        if self._preparation_round == (3, 7) and final_sale.confirmed:
                            # Spend newly gained final-round gold under the same
                            # cumulative shop limits and recovery handling.
                            while True:
                                with self._timed("shopping"):
                                    shopping_result = self.shopping()
                                if not self._resume_shopping_after(shopping_result):
                                    break
                            with self._timed("preparation_confirmation"):
                                prepared = self.prepare_for_battle()
                            if prepared.state == Readiness.BLOCKED:
                                self._fail_battle("preparation_" + prepared.reason)
                        elif population_before_sale != (self._population_current, self.max_team_size):
                            # Only new population evidence can invalidate the
                            # field readiness established immediately above.
                            final_ready = self._assess_preparation()
                            if final_ready.state == Readiness.BLOCKED:
                                final_ready = self.prepare_for_battle()
                                if final_ready.state == Readiness.BLOCKED:
                                    self._fail_battle("preparation_" + final_ready.reason)
                    if self._equipment_due():
                        with self._timed("equipment"):
                            equipment_completed = self._process_equipment()
                            if self.equipment_interval_battles is not None and not equipment_completed:
                                raise RuntimeError("装备批次中断，重新定位准备界面")
                            self._equipment_dirty = self._needs_equipment_check()
                        # Equipment may leave a panel or invalidate one identity.
                        # Reassess all hard gates using the same effective target.
                        if (self.equipment_interval_battles is None
                                and not self._set_shop_open(False)):
                            self._fail_battle("equipment_preparation_not_confirmed")
                        self._preparation_assessment_cache = None
                        final_ready = self._assess_preparation()
                        if final_ready.state == Readiness.BLOCKED:
                            final_ready = self.prepare_for_battle()
                            if final_ready.state == Readiness.BLOCKED:
                                self._fail_battle("equipment_" + final_ready.reason)
                    elif self.equipment_interval_battles is not None:
                        self._process_equipment()  # Record the skipped interval without opening panels.
                    if time.monotonic() >= self._preparation_deadline:
                        self._fail_battle("preparation_total_time_budget")
                    self._record_checkpoint(phase="ready", pending_actions=[])
                    if not self.battle():
                        if self.is_game_over:
                            break
                        raise RuntimeError("出战流程未完成，重新定位当前页面")
                    if not self.stage_transition():
                        raise RuntimeError("关卡切换未完成，重新定位当前页面")
                    if self.is_game_over:
                        break
                    self._cycle_number += 1
                    first_preparation = self._confirmed_battle_count == 0
                    self._record_checkpoint(phase="preparation", confirmed_event=f"cycle:{self._cycle_number}")
                    self._report_round(self._cycle_number, round_started, phase_before, sale)
                    self._preparation_deadline = self._formation_deadline = None
                    recovery_attempts = 0
                except ThreadStoppedError:
                    raise
                except Exception as error:
                    if (self._last_completed_battle_id != battle_before
                            or self._preparation_departure_confirmed):
                        recovery_attempts = 0
                    if recovery_attempts >= self.FLOW_RECOVERY_ATTEMPTS:
                        raise
                    recovery_attempts += 1
                    if not self._recover_runtime_flow(error, recovery_attempts):
                        raise
                    if self.is_game_over:
                        break
                    if (self._last_completed_battle_id != battle_before
                            or self._preparation_departure_confirmed):
                        self._cycle_number += 1
                        first_preparation = self._confirmed_battle_count == 0
                        self._preparation_deadline = self._formation_deadline = None
                        self._preparation_departure_confirmed = False
                        self._record_checkpoint(phase="preparation")
                        recovery_attempts = 0
                    # Re-enter page checks with the same pending actions and
                    # allowances. Reaching preparation alone is not progress.
        finally:
            if self._session_store is not None and not self._session_store.checkpoint.finalized:
                event = getattr(self.operator, "stop_event", None)
                self._record_execution_stop("stopped" if not self.is_running
                    or event is not None and event.is_set() else "error")
            self.reset_character()
        return True

    def refresh_character(self, equip=True, *, recover_layout=False):
        """Refresh the complete roster; local layout recovery uses the backend entry."""
        self._check_stop()
        # Authenticate before the frontline scan too: a probability popup can
        # otherwise turn shop text into false character-panel observations.
        if not self._set_shop_open(False):
            self._layout_valid = False
            self._field_observed_at = None
            self._population_current = self._population_read_key = None
            for area in ("on_field", "off_field"):
                for i in range(len(self._observations[area])):
                    self._set_observation(area, SlotObservation(i, SlotState.UNKNOWN,
                        evidence="preparation_not_confirmed"))
            self._vision.last_layout_diagnostics = {"evidence": "layout_preparation_not_confirmed"}
            self._vision.capture_layout_failure("layout_preparation_not_confirmed")
            logger.warning("[场地识别] 未确认商店及浮层收起，暂停前后台扫描")
            return False
        scan_equip = equip and self.equipment_interval_battles is None
        self.get_on_field_area(True, equip=scan_equip)
        self.refresh_backend_character(equip=scan_equip, recover_layout=recover_layout)
        if self._pending_move is None:
            self._placement_pending = False
        self._field_observed_at = time.monotonic()
        self._reconcile_placed()
        self._confirm_main_c_fielded()
        if equip:
            self._equipment_dirty = self._needs_equipment_check()

    def refresh_backend_character(self, equip=False, *, recover_layout=False):
        """Authenticate and scan only the backend, leaving reliable frontline evidence intact."""
        self._check_stop()
        if recover_layout or not self._layout_valid:
            # Both normal and alternative recovery must first authenticate the
            # preparation page; a hidden shop must not become a layout candidate.
            if not self._set_shop_open(False):
                self._layout_valid = False
                self._vision.last_layout_diagnostics = {"evidence": "layout_preparation_not_confirmed"}
                self._vision.capture_layout_failure("layout_preparation_not_confirmed")
                for i in range(len(self._observations["off_field"])):
                    self._set_observation("off_field", SlotObservation(i, SlotState.UNKNOWN,
                        evidence="layout_unconfirmed"))
                return False
            self.operator.move_to(0.5, 0.5)
            self.operator.sleep(0.5 if recover_layout else 0.2)
        previously_unconfirmed = not self._layout_valid
        layout = self._vision.read_backend_layout(
            self._confirmed_layout_positions if recover_layout else self.off_field_area,
            recover=recover_layout)
        if previously_unconfirmed and layout.valid and not layout.changed and not recover_layout:
            first_details = dict(self._vision.last_layout_diagnostics)
            self.operator.sleep(0.2)
            second = self._vision.read_backend_layout(layout.positions)
            second_details = dict(self._vision.last_layout_diagnostics)
            first_details.update(layout_second_evidence=second.reason,
                layout_second_boxes=second_details.get("layout_boxes", []),
                layout_second_positions=list(second.positions))
            self._vision.last_layout_diagnostics = first_details
            if not second.valid or second.changed:
                layout = replace(layout, valid=False, reason="layout_not_stable")
        if layout.valid:
            # Recovery compares its frames to recent anchors. Commit changes
            # relative to the coordinates actually used by board actions too.
            changed = (len(layout.positions) != len(self.off_field_area) or
                any(abs(a - b) > 0.002 for old, new in zip(self.off_field_area, layout.positions)
                    for a, b in zip(old, new)))
            layout = replace(layout, changed=changed)
        if layout.valid and layout.changed:
            self._layout_revision += 1
            self.off_field_area = list(layout.positions)
            self.off_field_character[:] = [None] * len(layout.positions)
            self._observations["off_field"] = [SlotObservation(i, SlotState.UNKNOWN,
                evidence="layout_changed") for i in range(len(layout.positions))]
            self._equipment_checked.clear()
            self._equipment_dirty = True
            self._snapshot_revision += 1
            self._dirty_slots = {(area, i) for area, i in self._dirty_slots if area != "off_field"}
            logger.info(f"[布局确认] 后台布局版本={self._layout_revision} 坐标已重新识别")
        if layout.valid:
            self._layout_valid = True
            self._confirmed_layout_positions = tuple(layout.positions)
            self._backend_support_slots = {
                index: Character("锁定支援单位", 0, Positioning.OffField,
                                 is_locked=True, is_npc=True)
                for index in layout.protected_slots
            }
            if layout.protected_slots:
                logger.info(f"[布局确认] 锁定支援单位已通过两帧认证，后台槽={layout.protected_slots}，计入人口并禁止移动")
        else:
            logger.warning(f"[布局确认] 拒绝本帧候选，旧坐标等待复核：{layout.reason}")
            self._vision.capture_layout_failure(layout.reason)
            self._layout_valid = False
            for i in range(len(self._observations["off_field"])):
                self._set_observation("off_field", SlotObservation(i, SlotState.UNKNOWN,
                    evidence="layout_unconfirmed"))
        if self._layout_valid:
            self.get_off_field_area(True, equip=equip and self.equipment_interval_battles is None)
        self._reconcile_placed()
        self._confirm_main_c_fielded()
        return self._layout_valid

    def _needs_equipment_check(self):
        role_names = ({p.name for providers in self.formation_config.roles.values() for p in providers}
                      if self.formation_config is not None else set())
        eligible = set(allowed_order(self.equipment_config,
            self.strategy_characters.keys() | role_names, self._preparation_round))
        return any(o.state == SlotState.KNOWN and o.character is not None
                   and not o.character.is_locked and not o.character.is_npc and o.character.name in eligible
                   and self._equipment_checked.get(o.character.name) != self._equipment_signature(o)
                   for area in ("on_field", "off_field") for i, o in enumerate(self._observations[area]))

    def _equipment_signature(self, observation):
        return (observation.stars, self._observed_prices.get(observation.character.name),
                self._equipment_resource_revision)

    def _invalidate_equipment_resources(self, reason):
        self._equipment_resource_revision += 1
        self._equipment_attempts.clear()
        self._equipment_dirty = True
        logger.debug(f"[装备资源] 版本={self._equipment_resource_revision} 原因={reason}")

    def _process_equipment(self):
        throttled = self.equipment_interval_battles is not None
        if throttled and not self._equipment_due():
            self._equipment_metrics["skipped"] += 1
            logger.info(f"[装备节奏] skipped={self._equipment_metrics['skipped']} "
                        f"since_check={self._equipment_battles_since_check} interval={self.equipment_interval_battles}")
            return False
        if throttled and self._equipment_batch_attempts >= 2:
            logger.warning("[装备节奏] 本准备期已达有限整批尝试上限，保留到期批次")
            return False
        self._equipment_batch_attempts += 1
        self._equipment_metrics["due"] += 1
        started = time.monotonic()
        completed = False
        if throttled and not self._record_checkpoint(equipment_batch_state="in_progress"):
            self._fail_battle("equipment_checkpoint_not_saved")
        self._equipment_batch_running = True
        try:
            # Resolve identities first so an unknown priority unit cannot be
            # skipped while equipment is assigned to a lower-priority unit.
            for area in ("on_field", "off_field"):
                for index in range(len(self._observations[area])):
                    self._check_stop()
                    if self._preparation_deadline is not None and time.monotonic() >= self._preparation_deadline:
                        return False
                    obs = self._observations[area][index]
                    if (area, index) in self._dirty_slots or observation_identity(obs) is None:
                        obs = self._observe_slot(area, index, count_stars=True,
                                                 use_backup_ocr=area == "off_field")
                        self._set_observation(area, obs)
            slots = [(area, index, obs) for area in ("on_field", "off_field")
                     for index, obs in enumerate(self._observations[area])]
            priority_pending = False
            if self.equipment_config is not None:
                priority_pending = any(observation_identity(obs) is None
                    and getattr(getattr(self, area + "_character")[index], "name", None)
                    in self.equipment_config.priority_characters for area, index, obs in slots)
                slots = [(area, index, obs) for area, index, obs in slots
                         if obs.state == SlotState.KNOWN and observation_identity(obs) is not None]
                order = allowed_order(self.equipment_config,
                    [obs.character.name for _, _, obs in slots],
                    None if priority_pending else self._preparation_round)
                if priority_pending:
                    logger.info("[装备优先级] 优先角色身份补读未确认，暂缓给其他角色使用装备")
                slots = sorted((item for item in slots if item[2].character.name in order),
                               key=lambda item: order.index(item[2].character.name))
            for area, index, obs in slots:
                self._check_stop()
                if self._preparation_deadline is not None and time.monotonic() >= self._preparation_deadline:
                    return False
                self._equip_observation(area, index, obs)
            if throttled:
                if not self._set_shop_open(False):
                    return False
                if self._session_store is not None:
                    if not self._session_store.complete_equipment_check():
                        self._fail_battle("equipment_checkpoint_not_saved")
                self._equipment_battles_since_check = 0
            if self._equipment_others_available() and not priority_pending:
                self._equipment_others_checked = True
            completed = True
            return True
        finally:
            self._equipment_batch_running = False
            if throttled and not completed:
                self._record_checkpoint(equipment_batch_state="interrupted")
            logger.info(f"[装备节奏] batch_completed={completed} due={self._equipment_metrics['due']} "
                        f"unconfirmed={self._equipment_metrics['unconfirmed']} seconds={time.monotonic() - started:.2f}")

    def _equip_observation(self, area, index, obs):
        if self.equipment_interval_battles is not None and not self._equipment_batch_running:
            return
        if self._preparation_deadline is not None and time.monotonic() >= self._preparation_deadline:
            return
        if obs.state != SlotState.KNOWN or observation_identity(obs) is None:
            return
        char = obs.character
        roles = ({p.name for providers in self.formation_config.roles.values() for p in providers}
                 if self.formation_config is not None else set())
        if char.is_locked or char.is_npc or char.name not in self.strategy_characters.keys() | roles:
            return
        if char.name not in allowed_order(self.equipment_config, [char.name], self._preparation_round):
            return
        signature = self._equipment_signature(obs)
        if self._equipment_checked.get(char.name) == signature:
            return
        key = (char.name, signature)
        if self._equipment_attempts.get(key, 0) >= 2:
            return
        self._equipment_attempts[key] = self._equipment_attempts.get(key, 0) + 1
        self._check_stop()
        status = "unconfirmed"
        if not self.operator.click_point(*getattr(self, area + "_area")[index], after_sleep=0.2, trace=False):
            return
        try:
            recommend = self.operator.locate(CWIMG.EQUIPMENT_RECOMMEND)
            if self._preparation_deadline is not None and time.monotonic() >= self._preparation_deadline:
                return
            if recommend is not None and self.operator.click_box(recommend, after_sleep=1):
                _, box = self.operator.locate_any([CWIMG.EQUIP, CWIMG.SYNTHESIS], confidence=0.8)
                if self._preparation_deadline is not None and time.monotonic() >= self._preparation_deadline:
                    return
                if box is not None and self.operator.click_box(box, after_sleep=0.5):
                    # Input success is not inventory/equipment confirmation.
                    # Without a verified effect keep only the bounded attempt;
                    # a new resource revision enables a fresh check.
                    status = "input_completed"
        finally:
            self._check_stop()
            self.operator.click_point(0.5, 0.5, trace=False)
        if status == "unconfirmed":
            self._equipment_metrics["unconfirmed"] += 1
        logger.debug(f"[装备检查] {char.name} 资源版本={self._equipment_resource_revision} 状态={status}")

    def get_coins(self):
        results = self.operator.ocr(from_x=0.84, from_y=0.81, to_x=0.89, to_y=0.89)
        texts = [str(item[1]).strip() for item in results or ()]
        self._last_coins_read = int(texts[0]) if len(texts) == 1 and texts[0].isdecimal() else None
        return self._last_coins_read

    def _get_character_in_area(self, areas, target_character_list, force=False,
                               equip=False, count_stars=False, use_backup_ocr=False):
        area_type = self._area_name(target_character_list)
        self._last_scan_completed[area_type] = True
        for index in range(len(areas)):
            self._check_stop()
            old = self._observations[area_type][index]
            if not force and old.state == SlotState.KNOWN:
                continue
            try:
                overrides = getattr(self, "_bench_scan_overrides", None) if area_type == "in_hand" else None
                obs = overrides.get(index) if overrides is not None else None
                if obs is old:
                    continue  # The transaction did not touch this confirmed identity.
                if obs is None:
                    obs = self._observe_slot(area_type, index, count_stars, use_backup_ocr)
                self._set_observation(area_type, obs)
                if obs.state != SlotState.KNOWN or not equip:
                    continue
                self._equip_observation(area_type, index, obs)
            except ThreadStoppedError:
                raise
            except Exception as error:
                self._observations[area_type][index] = SlotObservation(
                    index, SlotState.UNKNOWN, evidence="observation_error")
                logger.warning(f"角色识别失败 {area_type}[{index}]: {error}")
        if equip and self.equipment_interval_battles is not None and not self._equipment_batch_running:
            # Scans only register work. The due batch runs after final placement.
            self._equipment_dirty = True
        return target_character_list

    def get_off_field_area(self, force=False, equip=False):
        self._get_character_in_area(self.off_field_area, self.off_field_character, force,
                                    equip, True, True)
        self._reconcile_placed()

    def get_on_field_area(self, force=False, equip=False):
        self._get_character_in_area(self.on_field_area, self.on_field_character, force,
                                    equip, True)
        self._reconcile_placed()

    def _supply_pause(self, seconds):
        # The packed operator's sleep is not cancellable; keep waits short.
        remaining = seconds
        while remaining > 0:
            self._check_stop()
            step = min(0.2, remaining)
            self.operator.sleep(step)
            remaining -= step
        self._check_stop()

    def _fail_supply(self, reason):
        sample = self._vision.capture_sample(reason, {"evidence": "supply_reward_not_confirmed"})
        logger.error(f"[补给箱] {reason}，停止本次任务，避免重复开启或误点角色；截图={sample}")
        raise RuntimeError(f"补给箱未完成：{reason}")

    def _press_supply_open(self, target):
        # Preserve the original down/up input path; always release on failure.
        released = False
        try:
            self._check_stop()
            if not self.operator.mouse_down(*target.center):
                return False
            self._supply_pause(0.15)
            released = bool(self.operator.mouse_up())
            self._check_stop()
            return released
        finally:
            if not released:
                self._release_pointer_unconditionally()

    def _read_supply_frame(self):
        self._check_stop()
        try:
            image = self.operator.screenshot().convert("RGB")
            width, height = image.size
            crop = image.crop((round(width * 0.08), round(height * 0.05),
                               round(width * 0.92), round(height * 0.65)))
            result = self._vision._engine_ocr(crop)
            if result is None:
                return None  # OCR failure is not evidence that a popup closed.
            text = "".join(str(item[1]) for item in result
                           if isinstance(item, (tuple, list)) and len(item) >= 2)
            text = re.sub(r"\s+", "", text)
            prompt = text if (any(word in text for word in ("选择", "挑选"))
                              and any(word in text for word in ("装备", "武器", "武装箱", "角色", "专家"))) else ""
            self._check_stop()
            return crop, prompt
        except ThreadStoppedError:
            raise
        except Exception as error:
            self._vision._failure(error)
            logger.debug(f"[补给箱] 奖励页面读取失败：{type(error).__name__}")
            return None

    @staticmethod
    def _supply_target_frame(frame):
        # Game region (0.73, 0.13)-(0.87, 0.40) around the choice click.
        # The input frame is already cropped to (0.08, 0.05)-(0.92, 0.65).
        width, height = frame.size
        return frame.crop((round(width * (0.73 - 0.08) / 0.84),
                           round(height * (0.13 - 0.05) / 0.60),
                           round(width * (0.87 - 0.08) / 0.84),
                           round(height * (0.40 - 0.05) / 0.60)))

    def _wait_supply_choice(self):
        deadline = time.monotonic() + self.ENTRY_TRANSITION_TIMEOUT
        last_frame, last_prompt, stable, stable_since = None, "", 0, None
        self._supply_pause(2.0)
        while True:
            self._check_stop()
            if time.monotonic() >= deadline:
                break
            observed = self._read_supply_frame()
            if observed is not None:
                frame, prompt = observed
                if prompt:
                    unchanged = (last_frame is not None and prompt == last_prompt
                                 and image_distance(frame, last_frame) <= 0.02
                                 and image_distance(self._supply_target_frame(frame),
                                                    self._supply_target_frame(last_frame)) <= 0.008)
                    if unchanged:
                        stable += 1
                    else:
                        stable, stable_since = 1, time.monotonic()
                    last_frame, last_prompt = frame, prompt
                    if stable >= 2 and time.monotonic() - stable_since >= 1.2:
                        logger.info("[补给箱] 奖励提示及点击区域已持续稳定，准备选择")
                        return frame, prompt
                else:
                    last_frame, last_prompt, stable, stable_since = None, "", 0, None
            else:
                last_frame, last_prompt, stable, stable_since = None, "", 0, None
            self._supply_pause(0.35)
        self._fail_supply("supply_choice_timeout")

    def _wait_supply_result(self, choice_frame):
        deadline = time.monotonic() + self.ENTRY_TRANSITION_TIMEOUT
        last_frame, stable, confirmation_sent = None, 0, False
        self._supply_pause(0.5)
        while True:
            self._check_stop()
            if time.monotonic() >= deadline:
                break
            observed = self._read_supply_frame()
            if observed is None:
                last_frame, stable = None, 0
                self._supply_pause(0.35)
                continue
            frame, prompt = observed
            if prompt:
                last_frame, stable = None, 0
                if not confirmation_sent:
                    _, confirm = self.operator.locate_any(
                        [CWIMG.CONFIRM_SELECTION, IMG.ENSURE2], trace=False)
                    if confirm is not None:
                        confirmation_sent = True
                        if not self.operator.click_box(confirm):
                            self._fail_supply("supply_confirmation_click_failed")
                        logger.info("[补给箱] 已发送奖励确认，等待返回备战界面")
            elif (image_distance(frame, choice_frame) > 0.035
                  and self.operator.locate(CWIMG.PREPARATION_STAGE, trace=False) is not None):
                stable = (stable + 1 if last_frame is not None
                          and image_distance(frame, last_frame) <= 0.02 else 1)
                last_frame = frame
                if stable >= 2:
                    logger.info("[补给箱] 已确认奖励选择完成并返回备战界面")
                    return
            else:
                last_frame, stable = None, 0
            self._supply_pause(0.35)
        self._fail_supply("supply_result_timeout")

    def _open_supply_items(self):
        attempted_points = []
        for item in range(9):
            self._check_stop()
            target = self.operator.locate(CWIMG.OPEN)
            if target is None:
                return
            point = target.center
            if any((point[0] - old[0]) ** 2 + (point[1] - old[1]) ** 2 <= 24 ** 2
                   for old in attempted_points):
                self._fail_supply("supply_source_unchanged")
            attempted_points.append(point)
            logger.info(f"[补给箱] 开启第{item + 1}件，位置={point}；完成前不重复点击")
            if not self._press_supply_open(target):
                self._fail_supply("supply_open_failed")
            self.operator.move_to(0.96, 0.5)
            choice_frame, _ = self._wait_supply_choice()
            # Preserve the old reward preference, but only after the actual
            # equipment/character choice is visible and stable.
            if not self.operator.click_point(0.8, 0.25, tag="补给箱：选择已稳定的奖励"):
                self._fail_supply("supply_choice_click_failed")
            self._wait_supply_result(choice_frame)
            self._invalidate_equipment_resources("supply_reward")
            self._invalidate_level()
        if self.operator.locate(CWIMG.OPEN) is not None:
            self._fail_supply("supply_item_limit")

    def _read_bench_empty_observations(self):
        """Read vacancies and unavailable locks; neither implies a character."""
        self._check_stop()
        reader = getattr(self._vision, "read_empty_slots", None)
        if not callable(reader):
            return {}
        try:
            empty = reader("in_hand", self.in_hand_area)
            self._check_stop()
        except (ThreadStoppedError, InterruptedError):
            raise
        except Exception as error:
            self._check_stop()
            logger.debug(f"备战席批量空位检测不可用，恢复逐槽识别：{error}")
            return {}
        if not isinstance(empty, dict):
            return {}
        observations = {}
        for index in range(len(self.in_hand_area)):
            if empty.get(index) is True:
                self._observation_revision += 1
                observations[index] = SlotObservation(index, SlotState.EMPTY, occupied=False,
                    evidence="two_empty_frames", revision=self._observation_revision)
        locked_reader = getattr(self._vision, "read_locked_bench_slots", None)
        if callable(locked_reader):
            unresolved = {index: point for index, point in enumerate(self.in_hand_area)
                          if index not in observations}
            locked = locked_reader(unresolved)
            self._check_stop()
            if isinstance(locked, (set, frozenset)):
                for index in sorted(locked & unresolved.keys()):
                    self._observation_revision += 1
                    observations[index] = SlotObservation(index, SlotState.LOCKED,
                        occupied=False, evidence="two_locked_frames", revision=self._observation_revision)
        return observations

    def get_in_hand_area(self, force=False):
        # Supply is handled before shopping. Merge verification must not start
        # another reward flow while the current shop offer is being confirmed.
        self._check_stop()
        if not self._shopping_active:
            self._open_supply_items()
        owns_overrides = getattr(self, "_bench_scan_overrides", None) is None
        try:
            if owns_overrides:
                needs_scan = force or any(obs.state != SlotState.KNOWN for obs in self._observations["in_hand"])
                self._bench_scan_overrides = self._read_bench_empty_observations() if needs_scan else {}
            self._get_character_in_area(self.in_hand_area, self.in_hand_character,
                                        force, count_stars=True)
        finally:
            if owns_overrides:
                self._bench_scan_overrides = None
        complete = self._last_scan_completed.get("in_hand", False)
        if complete:
            self._bench_observed_at = time.monotonic()
        self._bench_dirty = not complete
        self._reconcile_purchase_pending()
        if any(o.state == SlotState.EMPTY for o in self._observations["in_hand"]):
            self._bench_full = False
        locked_count = sum(o.state == SlotState.LOCKED for o in self._observations["in_hand"])
        logger.info(f"备战席已识别 {self.in_hand_character_count}，锁定 {locked_count}，未知 {self.in_hand_unknown_count}")

    def _read_shop_probability_overlay(self, frame=None):
        """Authenticate the title and close control on one client-area frame."""
        self._check_stop()
        if not callable(getattr(self.operator, "screenshot", None)) or not callable(
                getattr(self.operator, "ocr_engine", None)):
            return None
        try:
            if frame is None:
                frame = self.operator.screenshot()
            self._check_stop()
            window = (self.operator.window_context.width, self.operator.window_context.height)
            if frame is None or tuple(frame.size) != window:
                return None
            roi = tuple(round(value * window[i % 2])
                        for i, value in enumerate(SHOP_PROBABILITY_TITLE_ROI))
            title = self._vision._engine_ocr(frame.crop(roi), minimum_confidence=0.9)
            result = detect_shop_probability_overlay(frame, title)
            return result.close_point if result.matched else None
        except ThreadStoppedError:
            raise
        except Exception as error:
            self._check_stop()
            logger.debug(f"[商店概率弹窗] 识别未确认：{type(error).__name__}")
            return None

    def _set_shop_open(self, opened):
        """Confirm the panel state before using shop or board coordinates."""
        deadline = time.monotonic() + self.EVENT_TRANSITION_TIMEOUT
        if self._preparation_deadline is not None and not self._shopping_active:
            deadline = min(deadline, self._preparation_deadline)
        acted = False
        probability_close_sent = False
        confirmed = 0
        for _ in range(30):
            self._check_stop()
            if time.monotonic() >= deadline:
                break
            frame = self._capture_page_frame()
            fold = self._locate_page_template(CWIMG.FOLD, frame)
            state = True if fold is not None else None
            if state is None and (self._locate_page_template(CWIMG.BATTLE, frame) is not None
                                  or self._locate_page_template(CWIMG.PREPARATION_STAGE, frame) is not None):
                state = False
            if state is None and not probability_close_sent:
                first = self._read_shop_probability_overlay(frame)
                if first is not None:
                    self.operator.sleep(0.2)
                    second = self._read_shop_probability_overlay()
                    self._check_stop()
                    if time.monotonic() >= deadline:
                        break
                    if second is not None and max(abs(a - b) for a, b in zip(first, second)) <= 0.005:
                        probability_close_sent = True
                        if not self.operator.click_point(*second, after_sleep=0.5,
                                tag="恢复：关闭商店刷新概率"):
                            break
                        confirmed = 0
                        continue  # Re-observe the underlying shop; a click is not confirmation.
            if state is opened:
                confirmed += 1
                if confirmed >= 2:
                    return True
            else:
                confirmed = 0
                if state is not None and not acted:
                    self._check_stop()
                    if time.monotonic() >= deadline:
                        break
                    acted = True
                    if opened:
                        clicked = self.operator.click_point(0.8438, 0.8481,
                            after_sleep=0.5, tag="准备阶段：展开商店")
                    else:
                        clicked = self.operator.click_box(fold, after_sleep=0.5)
                    if not clicked:
                        break
            self.operator.sleep(0.3)
        logger.warning(f"[商店界面] 未确认{'展开' if opened else '收起'}，已发送切换={acted}")
        self._vision.capture_sample("shop_state_unconfirmed",
            {"evidence": "open" if opened else "closed"}, critical=True)
        return False

    def harvest_crystals(self):
        if self._preparation_rewards_collected:
            return
        # The post-battle page may still have the shop covering the drops.
        if not self._set_shop_open(False):
            self._fail_battle("crystals_shop_not_closed")
        logger.info("收集水晶")
        if self.operator.type == "Local":
            for points in ((0.68, 0.20, 0.82, 0.18), (0.68, 0.25, 0.82, 0.25),
                           (0.68, 0.30, 0.83, 0.30), (0.68, 0.35, 0.84, 0.35),
                           (0.68, 0.40, 0.83, 0.40)):
                if not self._safe_drag_to(*points, trace=False):
                    self._fail_battle("crystal_input_failed")
                self.operator.sleep(0.3)
        else:
            # 浏览器不支持滑动，拖动可能无法正确触发收集
            for x in range(66, 85, 2):
                for y in range(20, 41, 5):
                    self._check_stop()
                    if not self.operator.click_point(x / 100, y / 100, trace=False):
                        self._fail_battle("crystal_input_failed")

        # Commit collection before event recognition, which may need page recovery.
        self._preparation_rewards_collected = True
        self._bench_dirty = True
        self._invalidate_equipment_resources("preparation_rewards_collected")
        self.detect_silver_wolf_lv999()  # 也许开出银狼了

    @property
    def in_hand_unknown_count(self):
        return sum(obs.state == SlotState.UNKNOWN for obs in self._observations["in_hand"])

    def _has_confirmed_bench_space(self):
        return any(obs.state == SlotState.EMPTY and observation_identity(obs) is not None
                   for obs in self._observations["in_hand"])

    def _sale_usable_observation(self, obs):
        char = obs.character
        return (obs.state == SlotState.KNOWN and char is not None
                and obs.evidence not in UNRELIABLE_EVIDENCE
                and not char.is_locked and not char.is_npc
                and self._lookup_known_character(char.name) is not None)

    def _sale_requirement_goals(self):
        goals = self._purchase_goals()
        config = self.formation_config
        if config is not None:
            stage = self._formation_stage()
            for name in role_protected_names(config, stage, self._observations):
                goals[name] = None
            for stage in config.stages:
                for name in stage.on_field + stage.off_field + stage.requires_fielded + stage.requires_available:
                    goals.setdefault(name, None)
            if config.upgrade_gate is not None:
                for name, stars in config.upgrade_gate.fielded.items():
                    goals[name] = max(goals.get(name) or 0, stars)
                for name, price in config.upgrade_gate.prices.items():
                    observed = self._observed_prices.get(name)
                    if type(observed) is not int or observed < price:
                        goals[name] = None
            fielded = {obs.character.name for area in ("on_field", "off_field")
                       for obs in self._observations[area] if self._sale_usable_observation(obs)}
            for protected, successor in config.protect_until_fielded.items():
                if protected not in fielded and successor not in fielded:
                    goals.setdefault(protected, None)
        return goals

    def _sale_interim_reserve(self, goals):
        """Keep only bench units still needed for reliable openings/frontline."""
        areas = ("on_field", "off_field")
        fielded = {obs.character.name for area in areas for obs in self._observations[area]
                   if self._sale_usable_observation(obs)}
        occupied = sum(obs.state not in (SlotState.EMPTY, SlotState.LOCKED)
                       or observation_identity(obs) is None
                       for area in areas for obs in self._observations[area])
        remaining = max(0, self.max_team_size - occupied) if type(self.max_team_size) is int else 0
        openings = {area: sum(obs.state == SlotState.EMPTY and obs.evidence not in UNRELIABLE_EVIDENCE
                              for obs in self._observations[area]) for area in areas}
        hand = sorted((obs for obs in self._observations["in_hand"]
                       if self._sale_usable_observation(obs)),
                      key=lambda obs: (obs.character.name not in goals, -(obs.stars or 0), obs.slot_index))
        stage = self._formation_stage()

        def fits(obs, area):
            if stage is not None:
                return area in _placement_areas(self.formation_config, stage, obs)
            position = obs.character.position
            return position in (Positioning.OnOffField,
                                Positioning.OnField if area == "on_field" else Positioning.OffField)

        reserved = set()
        has_front = any(self._sale_usable_observation(obs) for obs in self._observations["on_field"])
        if not has_front:
            front = next((obs for obs in hand if obs.character.name not in fielded and fits(obs, "on_field")), None)
            if front is not None:
                reserved.add(front.slot_index)
                fielded.add(front.character.name)
                has_front = True
                remaining = max(0, remaining - 1)
                openings["on_field"] = max(0, openings["on_field"] - 1)
        if has_front:
            for obs in hand:
                if remaining <= 0:
                    break
                if obs.slot_index in reserved or obs.character.name in fielded:
                    continue
                area = next((area for area in areas if openings[area] and fits(obs, area)), None)
                if area is not None:
                    reserved.add(obs.slot_index)
                    fielded.add(obs.character.name)
                    openings[area] -= 1
                    remaining -= 1
        return reserved

    def _sell_candidates(self):
        goals = self._sale_requirement_goals()
        interim = self._sale_interim_reserve(goals)
        protect_interim = self._sale_transition_blocker() is not None
        # Reserve an actual completed instance on either field or bench. A
        # name-wide protection would retain all surplus copies forever, while
        # removing it without an instance binding could sell the completed one.
        retained = {}
        for name, goal in goals.items():
            if type(goal) is not int or name in self._purchase_pending_names:
                continue
            matches = [(area, o) for area in self._observations for o in self._observations[area]
                       if self._sale_usable_observation(o) and o.character.name == name]
            if any(o.stars is None for _, o in matches):
                continue
            complete = [(area, o) for area, o in matches if type(o.stars) is int and o.stars >= goal]
            if complete:
                area, best = max(complete, key=lambda pair: (pair[1].stars,
                    pair[0] != "in_hand", -pair[1].slot_index))
                retained[name] = (area, best.slot_index)
        candidates = []
        for obs in self._observations["in_hand"]:
            char = obs.character
            if not self._sale_usable_observation(obs) or obs.slot_index in interim:
                continue
            if protect_interim and char.name not in goals:
                continue
            if self.main_c == char.name and not self.main_c_first_fielded_confirmed:
                continue
            if char.name in goals:
                goal = goals[char.name]
                if goal is None or char.name not in retained or retained[char.name] == ("in_hand", obs.slot_index):
                    continue
                if any(o.state == SlotState.UNKNOWN and
                       (o.character or getattr(self, area + "_character")[i]) is not None and
                       (o.character or getattr(self, area + "_character")[i]).name == char.name
                       for area in self._observations for i, o in enumerate(self._observations[area])):
                    continue
            candidates.append((obs.slot_index, char))
        return candidates

    def _sale_transition_blocker(self):
        """An uncertain field cannot prove that a temporary bench unit is surplus."""
        if not self._layout_valid:
            return "layout_unconfirmed"
        if self._pending_move is not None or self._placement_pending:
            return "placement_pending"
        if any(area != "in_hand" for area, _ in self._dirty_slots):
            return "field_dirty"
        field = [obs for area in ("on_field", "off_field") for obs in self._observations[area]]
        if any(observation_identity(obs) is None for obs in field):
            return "field_unknown"
        capacity, current = self.max_team_size, self._population_current
        if (type(capacity) is not int or not 1 <= capacity <= len(field)
                or type(current) is not int or not 0 <= current <= capacity):
            return "population_unknown"
        # Locked NPCs count towards the game's population even though they are
        # not movable or sellable. Do not use sale eligibility to count the field.
        known = sum(obs.state == SlotState.KNOWN for obs in field)
        if known != current:
            return "population_conflict"
        return None

    def _needs_pre_battle_cleanup(self):
        """Decide from cached evidence only; do not rescan an already clean bench."""
        if (self._preparation_deadline is not None
                and time.monotonic() >= self._preparation_deadline):
            return False
        if self._sell_candidates():
            return True
        if (self._population_current is not None
                or self._sale_transition_blocker() != "population_unknown"):
            return False
        if (self._sale_population_retry_used
                and self._population_read_key == self._population_observation_key()):
            return False
        goals = self._sale_requirement_goals()
        return any(self._sale_usable_observation(obs) and obs.character.name not in goals
                   for obs in self._observations["in_hand"])

    def _refresh_sale_population(self):
        # A confirmed placement invalidates population. Re-read it once from a
        # reliable board, including one retry of a cached failed read per
        # preparation, before deciding whether its former fillers are surplus.
        # Candidate generation itself remains free of OCR and input actions.
        if (self._population_current is None and self._layout_valid
                and self._pending_move is None and not self._placement_pending
                and not any(area != "in_hand" for area, _ in self._dirty_slots)
                and all(observation_identity(obs) is not None
                    for area in ("on_field", "off_field") for obs in self._observations[area])
                and any(self._sale_usable_observation(obs)
                    and obs.character.name not in self._sale_requirement_goals()
                    for obs in self._observations["in_hand"])):
            self.update_max_team_size(retry_failed=True)
        reason = self._sale_transition_blocker()
        if reason:
            logger.info(f"[过渡牌保护] 场上或人口尚未确认，保留非攻略角色：{reason}")

    def sell_character(self):
        """Clean reliable surplus bench units without waiting for a full bench."""
        self._check_stop()
        if not self._opening_action_allowed("sell"):
            return SellResult(ActionResult.CONFIRMED, reason=("opening_round_unknown"
                if self._preparation_round is None else "opening_sales_locked"))
        self._refresh_sale_population()
        has_space = self._has_confirmed_bench_space()
        if has_space:
            self._bench_full = False
        candidates = self._sell_candidates()
        if not candidates:
            if has_space:
                return SellResult(ActionResult.CONFIRMED, reason="space_confirmed")
            if self.in_hand_unknown_count and not self._bench_full:
                return SellResult(ActionResult.INDETERMINATE, reason="unknown_occupancy")
            return SellResult(ActionResult.INDETERMINATE, reason="no_safe_candidates")
        return self._sell_character_batch(candidates)

    def _handle_sell_character(self, force=False):
        # force is retained for callers, but cannot bypass character protection.
        self._check_stop()
        if not self._opening_action_allowed("sell"):
            return SellResult(ActionResult.CONFIRMED, reason=("opening_round_unknown"
                if self._preparation_round is None else "opening_sales_locked"))
        self._refresh_sale_population()
        return self._sell_character_batch(self._sell_candidates())

    def _sell_character_batch(self, candidates):
        """Consume the entry checks once; replan after every attempted sale."""
        attempted = confirmed = 0
        deadline = time.monotonic() + 30
        if self._preparation_deadline is not None:
            deadline = min(deadline, self._preparation_deadline)

        def finish_timed_batch():
            # Budget checks occur between drags. Confirmed sales stay confirmed
            # even when another surplus unit must wait for the next batch.
            if attempted == confirmed:
                logger.info(f"[余牌清理] 本批已确认出售={confirmed}，剩余余牌留待后续清理")
                return SellResult(ActionResult.CONFIRMED, attempted, confirmed,
                                  "cleanup_deferred_time_budget")
            return SellResult(ActionResult.INDETERMINATE, attempted, confirmed, "time_budget")

        for _ in range(9):
            self._check_stop()
            if time.monotonic() >= deadline:
                return finish_timed_batch()
            if not candidates:
                has_space = self._has_confirmed_bench_space()
                if has_space:
                    self._bench_full = False
                result = ActionResult.CONFIRMED if confirmed or has_space else ActionResult.INDETERMINATE
                return SellResult(result, attempted, confirmed,
                                  "cleanup_complete" if confirmed else "no_safe_candidates")
            index, char = candidates[0]
            # Re-observe before dragging, so a shifted/overflow slot is not trusted.
            obs = self._observe_slot("in_hand", index, count_stars=True)
            self._set_observation("in_hand", obs)
            if (not self._sale_usable_observation(obs) or obs.character.name != char.name
                    or (index, char) not in self._sell_candidates()):
                return SellResult(ActionResult.INDETERMINATE, attempted, confirmed, "source_changed")
            before_coins = self.get_coins()
            if time.monotonic() >= deadline:
                return finish_timed_batch()
            source = self.in_hand_area[index]
            attempted += 1
            logger.info(f"尝试出售备战席[{index}] {char.name}")
            bench_was_dirty = self._bench_dirty
            self._bench_dirty = True
            if not self._safe_drag_to(*source, 0.05, 0.86):
                return SellResult(ActionResult.FAILED, attempted, confirmed, "drag_failed")
            self.operator.sleep(0.5)
            self._check_stop()
            result = self._confirm_sale(index, char, before_coins)
            if result != ActionResult.CONFIRMED:
                # One observation-only recheck; never send a second uncertain drag.
                result = self._confirm_sale(index, char, before_coins)
                if result != ActionResult.CONFIRMED:
                    return SellResult(result, attempted, confirmed, "sale_not_confirmed")
            confirmed += 1
            self._reconcile_placed()
            logger.info(f"已确认出售 {char.name}")
            # An empty source confirms that physical bench positions survived.
            # A replacement identity can indicate compaction/merge; rescan then.
            if self._observations["in_hand"][index].state == SlotState.EMPTY:
                self._bench_dirty = bench_was_dirty
                self._bench_full = False
            else:
                self.get_in_hand_area(True)
            if self._has_confirmed_bench_space():
                self._bench_full = False
            candidates = self._sell_candidates()
            if not candidates:
                return SellResult(ActionResult.CONFIRMED, attempted, confirmed, "cleanup_complete")
        return SellResult(ActionResult.INDETERMINATE, attempted, confirmed, "action_budget")

    def _confirmed_frontline(self):
        return [obs.character for obs in self._observations["on_field"]
                if obs.state == SlotState.KNOWN and obs.character is not None
                and not obs.character.is_npc and not obs.character.is_locked
                and obs.evidence not in UNRELIABLE_EVIDENCE]

    def _ensure_battle_roster(self):
        if self._confirmed_frontline():
            return self._assess_preparation().state != Readiness.BLOCKED
        logger.warning("[出战检查] 前台没有已确认角色，重新识别并尝试布阵")
        self._check_stop()
        self.refresh_character(equip=False)
        self.update_max_team_size()
        self.place_character()
        return self._assess_preparation().state != Readiness.BLOCKED

    def _fail_battle(self, reason):
        metadata = {"evidence": reason}
        if reason.startswith("result_"):
            # Preserve the last actual recognition even when ordinary unknown
            # samples reached their per-session quota earlier in the run.
            metadata["ocr_attempts"] = list(self._vision.last_battle_attempts)
        sample = self._vision.capture_sample("battle_" + reason, metadata, critical=True)
        phase = "结算" if reason.startswith("result_") else "出战"
        logger.error(f"[{phase}检查] {reason}，交由主流程重新定位恢复；截图={sample}")
        logger.error(f"[诊断保存] {self._vision.last_sample_reason}")
        raise RuntimeError(f"{phase}未确认：{reason}")

    def _report_preflight(self, action="battle"):
        roster = {area: [(i, o.state.value, o.character.name if o.character is not None else None,
                         o.stars, o.evidence, o.revision) for i, o in enumerate(observations)]
                  for area, observations in self._observations.items()}
        checkpoint = self._session_store.checkpoint if self._session_store is not None else None
        logger.info(f"[出战快照] 操作={action} 局标识={checkpoint.run_id if checkpoint else 'untracked'} "
                    f"累计循环={self._cycle_number} 观察版本={self._snapshot_revision} "
                    f"布局版本={self._layout_revision} 人口={self._population_current}/{self.max_team_size} "
                    f"待确认={self._pending_move} 职责={self._role_evaluations()} "
                    f"就绪={self._assess_preparation()} 阵容与备战={roster}")

    def _post_battle_stage(self, allow_preparation=False):
        # Node titles are positive evidence of progress. A preparation button
        # alone is only meaningful after settlement has already been confirmed.
        # The strong-enemy notice is already a post-battle stage. Its blank
        # prompt takes precedence over preparation controls behind the modal.
        targets = [CWIMG.CLICK_BLANK, CWIMG.ENCOUNTER_NODE, CWIMG.REPLENISH_STAGE,
                   CWIMG.FORTUNE_TELLER, CWIMG.SELECT_INVEST_STRATEGY]
        if allow_preparation:
            targets.extend([CWIMG.FOLD, CWIMG.PREPARATION_STAGE,
                            CWIMG.BATTLE, CWIMG.START_CURRENCY_WARS])
        self._check_stop()
        index, box = self.operator.locate_any(targets, trace=False)
        self._check_stop()
        return targets[index] if box is not None and 0 <= index < len(targets) else None

    def _wait_battle_entry(self, allow_combat=True):
        # Currency Wars can omit Q entirely. Await positive combat/result
        # evidence without declaring that an UNKNOWN frame proves entry.
        started = time.monotonic()
        deadline = started + (self.BATTLE_TIMEOUT if allow_combat else self.REWARD_TRANSITION_TIMEOUT)
        confirmation_sent = False
        preparation_since = None
        next_stage, next_stage_frames = None, 0
        pending_logged = False
        targets = ([IMG.Q, CWIMG.SETTLE, CWIMG.CONTINUE] if allow_combat
                   else [CWIMG.SETTLE, CWIMG.CONTINUE])
        while True:
            self._check_stop()
            index, box = self.operator.locate_any(targets, trace=False)
            self._check_stop()
            if box is not None and 0 <= index < len(targets):
                if targets[index] != IMG.Q:
                    self._record_battle_screen(self._vision.read_battle_screen())
                else:
                    self._battle_entry_confirmed = bool(self._pending_battle_id)
                    self._record_checkpoint(phase="combat", pending_actions=[],
                        confirmed_event="battle_entered:" + self._pending_battle_id
                        if self._pending_battle_id else None)
                return index if allow_combat else index + 1
            screen = self._vision.read_battle_screen()
            self._record_battle_screen(screen)
            if screen.state in TERMINAL_STATES:
                return 3
            if screen.state == "result_ready" and screen.continue_point is not None:
                return 2
            if screen.state == "result_animation":
                return 3
            stage = self._post_battle_stage()
            next_stage_frames = (next_stage_frames + 1 if stage == next_stage else 1) if stage else 0
            next_stage = stage
            if stage is not None and next_stage_frames >= 2:
                logger.info(f"[出战检查] 已连续确认战斗后节点={stage}，转交关卡切换")
                return 4
            self._check_stop()
            if time.monotonic() - started >= self.PREPARATION_GRACE_SECONDS:
                page, page_box = self.operator.locate_any(
                    [CWIMG.BATTLE, CWIMG.PREPARATION_STAGE], trace=False)
                self._check_stop()
                if page_box is not None and page in (0, 1):
                    if preparation_since is None:
                        preparation_since = time.monotonic()
                else:
                    preparation_since = None
                if (preparation_since is not None and
                        time.monotonic() - preparation_since >= self.PREPARATION_CONFIRM_SECONDS):
                    logger.error("[入战识别] 出战后仍持续处于准备界面")
                    return -1
                if not pending_logged:
                    pending_logged = True
                    logger.info("[入战识别] 暂未捕获战斗提示，继续等待明确战斗或结算画面")
            if time.monotonic() >= deadline:
                break
            if allow_combat and not confirmation_sent:
                confirmation = self.operator.locate(IMG.ENSURE, trace=False)
                if confirmation is not None:
                    confirmation_sent = True
                    if not self.operator.click_box(confirmation):
                        self._fail_battle("confirmation_click_failed")
                    logger.info("[出战检查] 已点击编队确认，等待战斗界面证据")
            self._check_stop()
            self.operator.sleep(min(0.5, max(0, deadline - time.monotonic())))
        return -1

    def _wait_battle_result(self, in_combat=False):
        """Return continue box, continue point, and whether the next stage is ready."""
        self._terminal_route_screen = None
        deadline = time.monotonic() + (self.BATTLE_TIMEOUT if in_combat else self.REWARD_TRANSITION_TIMEOUT)
        reward_seen = not in_combat
        accelerated = False
        next_stage, next_stage_frames = None, 0
        # Give settlement its own deadline once positive reward evidence appears.
        while True:
            self._check_stop()
            frame = self._capture_page_frame()
            button = self._locate_page_template(CWIMG.CONTINUE, frame)
            self._check_stop()
            if button is not None:
                self._record_battle_screen(self._vision.read_battle_screen(frame)
                    if frame is not None else self._vision.read_battle_screen())
                return button, None, False
            settlement = self._locate_page_template(CWIMG.SETTLE, frame)
            self._check_stop()
            screen = self._vision.read_battle_screen(frame) if frame is not None else self._vision.read_battle_screen()
            self._record_battle_screen(screen)
            self._check_stop()
            if screen.state in TERMINAL_STATES:
                stable = self._stable_terminal_screen(screen)
                if stable is not None:
                    self._terminal_route_screen = (time.monotonic(), stable)
                    self._record_terminal_screen(stable)
                    return None, None, True
            if screen.state == "result_ready" and screen.continue_point is not None:
                return None, screen.continue_point, False
            if settlement is not None or screen.state == "result_animation":
                if not reward_seen:
                    reward_seen = True
                    deadline = time.monotonic() + self.REWARD_TRANSITION_TIMEOUT
                    logger.info("已识别挑战结算，等待奖励动画结束和继续挑战按钮")
                if (screen.state == "result_animation" and screen.accelerate_point is not None
                        and not accelerated):
                    accelerated = True
                    if not self.operator.click_point(*screen.accelerate_point, after_sleep=0.5,
                                                     tag="结算动画：点击已识别的空白加速提示"):
                        self._fail_battle("result_acceleration_failed")
                next_stage, next_stage_frames = None, 0
            else:
                stage = self._post_battle_stage(allow_preparation=reward_seen)
                next_stage_frames = (next_stage_frames + 1 if stage == next_stage else 1) if stage else 0
                next_stage = stage
                if stage is not None and next_stage_frames >= 2:
                    logger.info(f"[结算检查] 已连续确认下一阶段={stage}，转交关卡切换")
                    return None, None, True
            if time.monotonic() >= deadline:
                break
            self.operator.sleep(min(0.5, max(0, deadline - time.monotonic())))
        self._check_stop()
        if reward_seen:
            self._fail_battle("result_timeout")
        return None, None, False

    def battle(self) -> bool:
        self._check_stop()
        index, battle_box = self.operator.wait_any_img([CWIMG.BATTLE, CWIMG.SKIP],
                                                       timeout=self.BATTLE_BUTTON_TIMEOUT, interval=0.5)
        if battle_box is None or index not in (0, 1):
            self._fail_battle("battle_button_missing")
        if index == 0:
            if not self._ensure_battle_roster():
                if not self._confirmed_frontline():
                    self._fail_battle("no_confirmed_frontline")
                prepared = self.prepare_for_battle()
                if prepared.state == Readiness.BLOCKED:
                    self._fail_battle("preparation_" + prepared.reason)
            # Scans and placement can change both the UI and button position.
            battle_box = self.operator.wait_img(CWIMG.BATTLE, timeout=self.BATTLE_BUTTON_TIMEOUT)
        self._check_stop()
        if self._placement_pending or self._pending_move is not None:
            self._fail_battle("preparation_pending_move_unresolved")
        self._report_preflight("battle" if index == 0 else "skip_reward")
        self._last_battle_outcome = "unknown"
        self._last_health_read = None
        self._health_read_attempts = 0
        if index == 0:
            # Never create a new identity for the same unresolved battle.
            if self._pending_battle_id is not None:
                self._fail_battle("previous_battle_unconfirmed")
            self._pending_battle_id = str(uuid.uuid4())
            self._battle_entry_confirmed = False
            if not self._record_checkpoint(pending_battle_id=self._pending_battle_id):
                self._fail_battle("battle_checkpoint_not_saved")
        self._record_checkpoint(phase="battle_entry_pending", pending_actions=["确认出战后实际页面"])
        if battle_box is None or not self.operator.click_box(battle_box, after_sleep=1.5):
            self._fail_battle("battle_click_failed")
        logger.info("已点击出战，等待进入战斗确认" if index == 0 else "已点击跳过，等待结算确认")
        entry = self._wait_battle_entry(allow_combat=index == 0)
        if entry < 0:
            self._fail_battle("entry_timeout")
        # A confirmed Skip transition also ends this preparation, without
        # counting it as a real battle or borrowing its reward collection state.
        self._preparation_departure_confirmed = True
        if index == 0:
            # Positive combat, settlement, or a two-frame post-battle node
            # following this isolated Battle input authenticates entry.
            self._battle_entry_confirmed = True
            if not self._record_checkpoint(confirmed_event="battle_entered:" + self._pending_battle_id):
                self._fail_battle("battle_checkpoint_not_saved")
        if entry == 4:
            self._confirm_completed_battle("post_battle_node")
            return True
        if entry == 0:
            # Q proves entry, not whether auto battle is enabled. V toggles
            # the current setting and can disable auto battle after a late read.
            logger.info("已确认进入战斗，保持当前自动战斗状态，等待挑战结束")
            continue_box, continue_point, stage_ready = self._wait_battle_result(in_combat=True)
            if continue_box is None and continue_point is None and not stage_ready:
                self._fail_battle("combat_wait_timeout")
        else:
            logger.info("已确认挑战结算，等待奖励动画结束和继续挑战按钮")
            continue_box, continue_point, stage_ready = self._wait_battle_result()
        if continue_box is None and continue_point is None and not stage_ready:
            self._fail_battle("result_not_confirmed")
        self._confirm_completed_battle("settlement_or_next_stage")
        logger.info("挑战结束")
        self._check_stop()
        if stage_ready:
            return True
        if continue_box is not None:
            return self.operator.click_box(continue_box, after_sleep=self.STAGE_SETTLE_SECONDS)
        return self.operator.click_point(*continue_point, after_sleep=self.STAGE_SETTLE_SECONDS,
                                         tag="点击已确认的继续挑战按钮")

    def _wait_stage_ready(self, img_list):
        # A transition title can change during the settling pause. Only act
        # after re-observing the same stage, within one fixed waiting window.
        deadline = time.monotonic() + self.STAGE_TRANSITION_TIMEOUT
        while True:
            self._check_stop()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return -1
            index, box = self.operator.wait_any_img(img_list, timeout=remaining, interval=1)
            self._check_stop()
            if box is None or not 0 <= index < len(img_list):
                return -1
            self._supply_pause(self.STAGE_SETTLE_SECONDS)
            current, current_box = self.operator.locate_any(img_list, trace=False)
            self._check_stop()
            if current_box is not None and current == index:
                self._record_checkpoint(phase="stage_transition",
                    confirmed_event=f"cycle:{self._cycle_number}:page:{Path(str(img_list[index])).name}")
                return index
            logger.debug("[关卡切换] 稳定等待后画面已变化，重新确认当前阶段")

    def stage_transition(self):
        """实现关卡切换逻辑，通过识别图片状态执行对应操作"""
        terminal = self._terminal_route_screen
        self._terminal_route_screen = None
        screen = (terminal[1] if terminal is not None and time.monotonic() - terminal[0] <= 2
                  else self._vision.read_battle_screen())
        if screen.state in TERMINAL_STATES:
            return self.handle_game_over(None, first_screen=screen)
        # 定义状态配置：(图片路径, 状态名称, 处理函数, 是否为终止状态)
        stage_config = [
            (
                CWIMG.FORTUNE_TELLER,
                StageName.FORTUNE_TELLER,
                self._handle_fortune_teller_after_battle
            ),
            (
                CWIMG.REPLENISH_STAGE,
                StageName.REPLENISH_STAGE,
                self.handle_replenish_stage
            ),
            (
                CWIMG.ENCOUNTER_NODE,
                StageName.ENCOUNTER_NODE,
                self.handle_encounter_node
            ),
            (
                CWIMG.FOLD,
                StageName.FOLD,
                lambda prev_stage: True,  # 目标状态，无需处理
            ),
            (
                CWIMG.SELECT_INVEST_STRATEGY,
                StageName.SELECT_INVEST_STRATEGY,
                self.handle_invest_strategy
            ),
            (
                CWIMG.CLICK_BLANK,
                StageName.CLICK_BLANK,
                self.handle_click_blank
            ),
            (
                CWIMG.NEXT_STEP,
                "下一步",
                self.handle_next_step
            ),
            (
                CWIMG.START_CURRENCY_WARS,
                StageName.MAIN_MENU,
                self.handle_main_menu
            ),
            (
                CWIMG.PREPARATION_STAGE,
                StageName.FOLD,
                lambda prev_stage: True,
            ),
            (
                CWIMG.BATTLE,
                StageName.FOLD,
                lambda prev_stage: True,
            )
        ]

        img_list = [cfg[0] for cfg in stage_config]

        # 等待初始状态
        stage_index = self._wait_stage_ready(img_list)
        prev_stage_name: StageName | None = None
        advance_attempts = 0

        while True:  # 用无限循环 + 内部break控制退出
            self._check_stop()
            # 检查是否超时（未识别到任何状态）
            if stage_index == -1:
                raise RuntimeError("关卡状态检测超时，未识别到任何图片")

            # 获取当前状态配置
            img_path, stage_name, handle_func = stage_config[stage_index]
            logger.info(f"检测到状态：{stage_name}({img_path})")
            if stage_name == prev_stage_name == StageName.ENCOUNTER_NODE:
                self._vision.capture_sample("encounter_stage_repeated",
                                             {"evidence": "encounter_reappeared_after_confirmation"})
                raise RuntimeError("遭遇节点确认后重复出现，停止重复选择")

            if img_path == CWIMG.NEXT_STEP:
                advance_attempts += 1
                if advance_attempts > 2:
                    raise RuntimeError("下一步点击后画面未推进，转交页面恢复")
            else:
                advance_attempts = 0
            # Preserve uncertain selection input across page recovery.
            pending_node = getattr(self, "_runtime_node_pending", None)
            if pending_node is not None and pending_node != img_path:
                self._runtime_node_pending = None
            if img_path in (CWIMG.ENCOUNTER_NODE, CWIMG.REPLENISH_STAGE,
                            CWIMG.FORTUNE_TELLER, CWIMG.SELECT_INVEST_STRATEGY):
                if self._runtime_node_pending == img_path:
                    raise RuntimeError("节点选择尚未确认，转交页面恢复")
                self._runtime_node_pending = img_path
            # 执行状态处理函数
            try:
                is_terminal = handle_func(prev_stage_name)
                logger.info(f"状态 {stage_name} 处理完成")
            except ThreadStoppedError:
                raise
            except Exception as e:
                raise RuntimeError(f"处理状态 {stage_name} 时发生异常: {str(e)}") from e

            # 更新上一阶段名称
            prev_stage_name = stage_name

            # 若当前是终止状态，直接退出循环
            if is_terminal:
                logger.info(f"达到终止状态：{stage_name}，退出关卡切换流程")
                return self.handle_stage_transitioned()

            # 非终止状态，继续等待下一个状态
            stage_index = self._wait_stage_ready(img_list)

    def handle_main_menu(self, _: StageName | None) -> bool:
        """处理主菜单界面的逻辑"""
        self.is_game_over = True
        if self._session_store is not None and not self._session_store.checkpoint.finalized:
            self._session_store.finalize("returned_to_main_menu")
        return True

    def _handle_fortune_teller_after_battle(self, _: StageName | None) -> bool:
        """战斗结束后触发命运卜者事件"""
        if not self.handle_fortune_teller():
            raise RuntimeError("命运卜者事件未确认完成，停止重复选择")
        self.operator.click_point(0.8438, 0.8481, after_sleep=1, tag="打开商店界面")
        return False

    def handle_stage_transitioned(self) -> bool:  # NOQA
        """关卡切换完成后的处理逻辑（如有）。默认实现为无操作，子类可重写此方法以添加额外逻辑。
        调用时机：在完成关卡切换流程后、正式进入下一轮游戏循环前调用
        Returns:
            True-继续执行游戏循环；False-中止任务
        """
        return True

    def handle_characters_updated(self):
        """角色信息更新后的处理逻辑（如有）。默认实现为无操作，可重写此方法以添加额外逻辑。"""
        if all(c is None for c in self.on_field_character + self.off_field_character + self.in_hand_character):
            # 如果所有角色信息均为None，打开商店界面购买角色
            self._empty_roster_needs_shop = True

    def handle_game_over(self, _: StageName | None, *, first_screen=None) -> bool:
        """Navigate authenticated terminal pages; finalize only at the main menu."""
        deadline = time.monotonic() + self.REWARD_TRANSITION_TIMEOUT
        attempts, last_click, rank = {}, {}, -1
        order = TERMINAL_STATE_ORDER
        while time.monotonic() < deadline:
            self._check_stop()
            if self.operator.locate(CWIMG.START_CURRENCY_WARS, trace=False) is not None:
                self.operator.sleep(0.3)
                self._check_stop()
                if self.operator.locate(CWIMG.START_CURRENCY_WARS, trace=False) is not None:
                    self.handle_main_menu(None)
                    return True
            screen = first_screen if first_screen is not None else self._vision.read_battle_screen()
            first_screen = None
            stable = self._stable_terminal_screen(screen)
            if stable is None:
                self.operator.sleep(0.5)
                continue
            if order[stable.state] < rank:
                self._fail_battle("result_terminal_page_regressed")
            rank = order[stable.state]
            self._record_terminal_screen(stable)
            if stable.state == "final_summary" and not getattr(self, "_terminal_health_read", False):
                self._terminal_health_read = True
                self._last_health_read = self._vision.read_squad_health(FINAL_HEALTH_ROI)
                logger.info(f"[终局状态] 整局结果={stable.outcome} 小队生命值={self._last_health_read.current}")
                # Health OCR consumed new frames; never reuse its old button.
                continue
            state = stable.state
            if time.monotonic() - last_click.get(state, -float("inf")) < 5:
                self.operator.sleep(0.5)
                continue
            if attempts.get(state, 0) >= 2:
                self._fail_battle("result_terminal_page_not_changed")
            self._check_stop()
            if time.monotonic() >= deadline:
                break
            attempts[state] = attempts.get(state, 0) + 1
            last_click[state] = time.monotonic()
            clicked = self.operator.click_point(*stable.terminal_point, after_sleep=0.5,
                                                tag="终局：" + state)
            self._record_checkpoint(terminal_navigation_step=state + "_pending",
                pending_actions=["等待终局页面迁移" if clicked else "终局按钮点击失败，重新观察"])
            self.operator.move_to(0.5, 0.5)
        self._fail_battle("result_terminal_navigation_timeout")

    def handle_click_blank(self, _: StageName | None) -> bool:
        """Dismiss a confirmed strong-enemy notice once, then await departure."""
        self._check_stop()
        prompt = self.operator.locate(CWIMG.CLICK_BLANK, trace=False)
        self._check_stop()
        if prompt is None:
            # The page may have advanced during the stage settling pause.
            return False
        if not self.operator.click_point(0.5, 0.70, after_sleep=1,
                                         tag="关闭已确认的强敌来袭提示"):
            raise RuntimeError("强敌提示关闭失败")
        deadline = time.monotonic() + self.ENTRY_TRANSITION_TIMEOUT
        next_stage, next_stage_frames = None, 0
        while True:
            self._check_stop()
            stage = self._post_battle_stage(allow_preparation=True)
            if stage == CWIMG.CLICK_BLANK:
                stage = None
            next_stage_frames = (next_stage_frames + 1 if stage == next_stage else 1) if stage else 0
            next_stage = stage
            if stage is not None and next_stage_frames >= 2:
                logger.info(f"[强敌提示] 已确认退场，下一阶段={stage}")
                return False
            if time.monotonic() >= deadline:
                self._vision.capture_sample("boss_notice_departure_timeout",
                    {"evidence": "no_confirmed_next_stage_after_boss_notice"}, critical=True)
                raise RuntimeError("强敌提示确认后仍未退场")
            self.operator.sleep(min(0.5, max(0, deadline - time.monotonic())))

    def handle_invest_strategy(self, prev_stage: StageName | None) -> bool:
        """处理投资策略选择界面的逻辑"""
        if not self.operator.click_img(CWIMG.COLLECTION):
            self.operator.click_point(0.5, 0.3, after_sleep=0.5, tag="选择中间的投资策略")
        self.operator.click_img(IMG.ENSURE2, after_sleep=1)
        self.post_invest_strategy()
        return False

    def post_invest_strategy(self, strategy_name: str | None = None):
        """投资策略选择后的后续处理逻辑"""
        if strategy_name == "阿哈大悦" or self.operator.locate(CWIMG.SELECT_SIMPLE_EQUIPMENT):
            self.operator.click_point(0.8, 0.25, after_sleep=1, tag="阿哈大悦选择装备4")

    def handle_replenish_stage(self, _: StageName | None):
        """处理补给阶段的逻辑"""
        self.operator.click_point(0.53, 0.52, after_sleep=1)  # 选择固定位置
        self.operator.click_point(0.88, 0.91, after_sleep=1)  # 点击确认按钮
        self._invalidate_equipment_resources("replenish_reward")
        self._invalidate_level()
        self.detect_silver_wolf_lv999()  # 也许选到银狼了
        return False

    def handle_encounter_node(self, _: StageName | None) -> bool:
        """处理遭遇节点的逻辑"""
        self._check_stop()
        if not self.operator.click_point(0.35, 0.50, after_sleep=1):  # 简单难度
            raise RuntimeError("遭遇节点选择失败")
        self._check_stop()
        if not self.operator.click_point(0.56, 0.84, after_sleep=1):  # 选择按钮中心
            raise RuntimeError("遭遇节点确认失败")
        deadline = time.monotonic() + self.ENTRY_TRANSITION_TIMEOUT
        next_stage, next_stage_frames = None, 0
        while True:
            self._check_stop()
            stage = self._post_battle_stage(allow_preparation=True)
            if stage == CWIMG.ENCOUNTER_NODE:
                stage = None
            next_stage_frames = (next_stage_frames + 1 if stage == next_stage else 1) if stage else 0
            next_stage = stage
            if stage is not None and next_stage_frames >= 2:
                return False
            if time.monotonic() >= deadline:
                self._vision.capture_sample("encounter_selection_timeout",
                                             {"evidence": "no_confirmed_next_stage_after_node_selection"})
                raise RuntimeError("遭遇节点确认后仍未退场，停止重复选择")
            self.operator.sleep(min(0.5, max(0, deadline - time.monotonic())))

    def handle_fortune_teller(self):
        """处理命运卜者事件的逻辑"""
        return self._handle_selection_event((0.22, 0.34, 0.85, 0.4),
                                            self.strategy_special_events.get("命运卜者", ""), "命运卜者")

    def _handle_selection_event(self, ocr_region, keyword, event_name=""):
        self._last_selection_sent = False
        for attempt in range(2):
            self._check_stop()
            boxes = self.operator.ocr_boxes(from_x=ocr_region[0], from_y=ocr_region[1],
                                            to_x=ocr_region[2], to_y=ocr_region[3])
            candidates = keyword.split()
            logger.info(f"事件={event_name} 关键词={keyword!r} 复核={attempt + 1} "
                        f"候选={[box.source[:120] for box in boxes or ()]}")
            target = next((box for box in boxes or ()
                           if any(k in box.source.strip() for k in candidates)), None)
            if target is None and boxes and not candidates:
                target = boxes[-1]
                logger.info(f"事件 {event_name} 未配置关键词，采用末项默认规则")
            if target is None:
                if attempt == 0:
                    self.operator.sleep(0.3)
                    continue
                self._vision.capture_sample("event_keyword_mismatch", {"event": event_name,
                    "keyword": keyword, "options": [box.source for box in boxes or ()]})
                logger.warning(f"事件 {event_name} 未找到配置关键词 {keyword!r}，停止选择")
                return False
            if not self.operator.click_box(target, after_sleep=0.5):
                return False
            # A sent confirmation may change state even when subsequent recognition fails.
            self._last_selection_sent = True
            self._invalidate_equipment_resources("selection_event")
            self._invalidate_level()
            if not self.operator.click_img(CWIMG.CONFIRM_SELECTION, after_sleep=0.5):
                return False
            deadline = time.monotonic() + self.EVENT_TRANSITION_TIMEOUT
            while True:
                self._check_stop()
                still_confirm = self.operator.locate(CWIMG.CONFIRM_SELECTION)
                ready = self.operator.locate(CWIMG.PREPARATION_STAGE) or self.operator.locate(CWIMG.FOLD)
                next_event = self.detect_special_event() if event_name else ""
                if not still_confirm and ((ready and (not event_name or next_event != event_name))
                                          or (next_event and next_event != event_name)):
                    logger.info(f"事件 {event_name} 已确认选择 {target.source!r}")
                    self._last_selection_sent = False
                    return True
                if time.monotonic() >= deadline:
                    break
                self.operator.sleep(min(0.5, max(0, deadline - time.monotonic())))
            self._vision.capture_sample("event_not_dismissed", {"event": event_name})
            return False
        return False

    def handle_the_planet_of_festivities(self):
        """处理盛会之星事件的逻辑"""
        return self._handle_selection_event((0.22, 0.29, 0.85, 0.35),
                                            self.strategy_special_events.get("盛会之星", ""), "盛会之星")

    def handle_choose_partner(self):
        """处理领航员选择事件的逻辑"""
        return self._handle_selection_event((0.25, 0.32, 0.85, 0.39),
                                            self.strategy_special_events.get("领航员", ""), "领航员")

    def handle_wish_trial(self):
        """处理命运圣杯事件的逻辑"""
        return self._handle_selection_event((0.22, 0.42, 0.85, 0.465), self.strategy_special_events.get("命运圣杯", ""), "命运圣杯")

    def detect_special_event(self) -> str:
        """检测当前是否有特殊事件发生，并返回事件名称"""
        result = self.operator.ocr(from_x=0.49, from_y=0.038, to_x=0.60, to_y=0.11)
        if not result:
            return ""
        text = result[0][1]
        # 遍历特殊事件列表，匹配标题
        for event, (title, handler) in self.special_events.items():
            if text == title:
                return event
        return ""

    def detect_silver_wolf_lv999(self):
        if self.operator.locate(CWIMG.SILVER_WOLF_LV999):
            if not self.handle_silver_wolf_lv999():
                raise RuntimeError("头号玩家事件未确认完成")
            return True
        return False

    def handle_silver_wolf_lv999(self):
        self._last_selection_sent = False
        result = self._handle_selection_event((0.22, 0.34, 0.85, 0.4),
                    self.strategy_special_events.get("头号玩家", ""), "头号玩家")
        if result or self._last_selection_sent:
            name = Characters.SilverWolfLV999.name
            self._form_change_pending[name] = self._observed_prices.get(name)
            self._invalidate_character_evidence(name, "silver_wolf_event")
            self._purchase_pending_names.discard(name)
        return result

    def handle_special_event(self):
        """Process chained events with a bounded, interruptible loop."""
        for _ in range(8):
            self._check_stop()
            event = self.detect_special_event()
            if not event:
                return
            logger.info(f"检测到特殊事件：{event}")
            if not self.special_events[event][1]():
                raise RuntimeError("特殊事件处理失败")
            self._equipment_dirty = True
            self._invalidate_level()
        raise RuntimeError("特殊事件连续处理达到上限")

    def _read_preparation_round(self):
        """Two current preparation labels, never inferred from battle count."""
        if self._preparation_round is not None or self._round_read_attempts >= 2:
            return self._preparation_round
        self._round_read_attempts += 1
        answers, texts = [], []
        rois = ((0.105, 0.02, 0.18, 0.135), (0.205, 0.02, 0.285, 0.105))
        for frame in range(2):
            candidates = set()
            for index, roi in enumerate(rois):
                self._check_stop()
                rows = self.operator.ocr(from_x=roi[0], from_y=roi[1], to_x=roi[2], to_y=roi[3],
                                         grayscale=False, confidence=0.9, trace=False)
                raw = " | ".join(str(row[1]).strip() for row in rows or ())
                texts.append(raw)
                # Authenticate the label in each layout separately; an obscured
                # second heading behind the open shop is not an extra round.
                answer = parse_preparation_round(raw) if "备战阶段" in re.sub(r"\s", "", raw) else None
                if answer is not None:
                    candidates.add((index, answer))
            answers.append(candidates if len({value for _, value in candidates}) == 1 else set())
            if frame == 0:
                self.operator.sleep(0.15)
        stable = answers[0] & answers[1]
        if stable:
            self._preparation_round = next(iter(stable))[1]
        logger.info(f"[备战关卡] round={self._preparation_round} OCR={texts}")
        return self._preparation_round

    def _opening_action_allowed(self, action):
        """Unlock sales/refreshes only from a confirmed current preparation round."""
        self._check_stop()
        if self._preparation_round == (3, 7):
            return True
        config = self.opening_policy_config
        boundary = getattr(config, action + "_from_round", None)
        if boundary is None:
            return True
        current = self._read_preparation_round()
        allowed = current is not None and current >= boundary
        if not allowed:
            logger.info(f"[开局保护] action={action} round={current} from_round={boundary}；"
                        "保留过渡牌，只采购当前商店中的攻略目标")
        return allowed

    def _read_experience_progress(self, level, *, recognize_cap=False):
        answers = []
        for frame in range(2):
            self._check_stop()
            rows = self.operator.ocr(from_x=0.115, from_y=0.76, to_x=0.195, to_y=0.94,
                                     grayscale=False, confidence=0.9, trace=False)
            raw = " | ".join(str(row[1]).strip() for row in rows or ())
            progress = parse_experience_progress(raw, level=level)
            if recognize_cap:
                cap = parse_experience_cap(raw, level=level)
                if cap is True:
                    progress = (0, 0)
                elif cap is None:
                    progress = None
            answers.append(progress)
            if frame == 0:
                self.operator.sleep(0.15)
        return answers[0] if answers[0] is not None and answers[0] == answers[1] else None

    def _economy_context(self, level, coins):
        # Only a possible permanent gold-stage promotion needs a second read.
        # Ordinary decisions consume the actual post-action balance once.
        self._check_stop()
        if coins is None:
            return None
        baseline = select_economy_stage(self.economy_config,
            confirmed_battle_count=self._confirmed_battle_count,
            previous_index=self._economy_stage_index, current_level=level)
        confirmed_coins = None
        if any(stage.upgrade_gold is not None and coins >= stage.upgrade_gold
               for stage in self.economy_config.stages[baseline.index + 1:]):
            self.operator.sleep(0.1)
            confirmed_coins = self.get_coins()
            if confirmed_coins != coins:
                logger.warning(f"[经济决策] action=recover reason=unstable_gold gold={coins}/{confirmed_coins}")
                return None
        selected = select_economy_stage(self.economy_config,
            confirmed_battle_count=self._confirmed_battle_count,
            coins=coins, confirmed_coins=confirmed_coins,
            previous_index=self._economy_stage_index, current_level=level)
        if selected.index != self._economy_stage_index:
            if not self._record_checkpoint(active_economy_stage_index=selected.index):
                return None
            self._economy_stage_index = selected.index
        stage = self.economy_config.stages[selected.index]
        searching_main = bool(self.main_c and not self.main_c_first_fielded_confirmed
            and level is not None and level >= self.main_c_search_level)
        target = stage.target_level
        if self.main_c and not self.main_c_first_fielded_confirmed and level is not None and level < self.main_c_search_level:
            target = min(target, self.main_c_search_level)
        reserve = self.main_c_search_min_coins if searching_main else stage.reserve_gold
        self._all_in_decision = None
        if self.economy_config.all_in_round is not None:
            current_round = self._read_preparation_round()
            progress = None
            if (current_round is not None and current_round >= self.economy_config.all_in_round
                    and level < self.economy_config.stages[-1].target_level):
                progress = self._read_experience_progress(level)
            self._all_in_decision = evaluate_all_in_policy(self.economy_config,
                current_round=current_round, level=level, coins=coins,
                experience_current=progress[0] if progress else None,
                experience_required=progress[1] if progress else None)
            decision = self._all_in_decision
            if decision.enabled:
                target, reserve, searching_main = decision.target_level, 0, False
            logger.info(f"[全额运营] round={current_round} L={level} target={decision.target_level} "
                        f"gold={coins} xp={progress} cost={decision.upgrade_cost} reason={decision.reason}")
        return selected, target, reserve, searching_main

    def _economy_unmet_goals(self):
        goals = self._purchase_goals()
        for name, stars in self._role_purchase_goals().items():
            goals[name] = max(goals.get(name, 0), stars)
        unmet = {}
        unknown = any(observation_identity(o) is None for slots in self._observations.values() for o in slots)
        for name, stars in goals.items():
            owned = [o for slots in self._observations.values() for o in slots
                     if o.state == SlotState.KNOWN and observation_identity(o) is not None
                     and o.character.name == name]
            if any(type(o.stars) is int and o.stars >= stars for o in owned):
                continue
            if owned and any(o.stars is None for o in owned):
                unknown = True
            unmet[name] = stars
        return unmet, unknown and bool(unmet)

    def _recheck_purchased_characters(self, names):
        """Re-read purchased names and new landings; reuse untouched identities.

        The baseline is scoped to an ordinary purchase transaction. Events,
        layout changes, moves, conflicting evidence or a failed first pass
        force a complete read before any placement or sale can use the result.
        """
        baseline = getattr(self, "_purchase_scan_baseline", None)
        try:
            self._check_stop()
            if not self._set_shop_open(False):
                return False
            reusable = (isinstance(baseline, tuple) and len(baseline) == 2
                and baseline[0] == self._layout_revision and self._layout_valid
                and self._pending_move is None and not self._runtime_node_pending
                and not self._form_change_pending and isinstance(baseline[1], dict)
                and all(area in baseline[1] and len(baseline[1][area]) == len(slots)
                    for area, slots in self._observations.items()))
            before = baseline[1] if reusable else None
            # A changed unrelated observation is evidence of another action,
            # not a reason to treat the older snapshot as still authoritative.
            if reusable:
                reusable = all(old is current or old.character is not None and old.character.name in names
                    for area, slots in self._observations.items()
                    for old, current in zip(before[area], slots))
            full_scan = baseline is not None and not reusable
            for attempt in range(2):
                self._check_stop()
                incremental = reusable and not full_scan and attempt == 0
                vacancies = self._read_bench_empty_observations()
                if incremental and any(before["in_hand"][index].state == SlotState.KNOWN
                        and before["in_hand"][index].character.name not in names for index in vacancies):
                    # An unrelated occupied slot cannot disappear in a purchase.
                    full_scan, incremental = True, False
                # Full identity scans must still respect currently locked
                # slots; clicking them cannot produce a character panel.
                overrides = {index: obs for index, obs in vacancies.items()
                             if not full_scan or obs.state == SlotState.LOCKED}
                if incremental:
                    for index, old in enumerate(before["in_hand"]):
                        if (index not in overrides and old is self._observations["in_hand"][index]
                                and old.state == SlotState.KNOWN and observation_identity(old) is not None
                                and old.character.name not in names and type(old.stars) is int
                                and 1 <= old.stars <= 3
                                and ("in_hand", index) not in self._dirty_slots):
                            overrides[index] = old
                    reused = sum(obs.state == SlotState.KNOWN for obs in overrides.values())
                    logger.info(f"[购后增量核实] 复用未变化角色={reused}，批量确认空位={len(vacancies)}，"
                                f"备战席需读身份星级={len(self.in_hand_area) - len(overrides)}")
                for area in ("on_field", "off_field"):
                    for index, obs in enumerate(self._observations[area]):
                        historical = getattr(self, area + "_character")[index]
                        character = obs.character or historical
                        if (full_scan or (area, index) in self._dirty_slots
                                or character is not None and character.name in names):
                            observed = self._observe_slot(area, index, count_stars=True,
                                use_backup_ocr=area == "off_field")
                            self._set_observation(area, observed)
                self._bench_scan_overrides = overrides
                try:
                    self.get_in_hand_area(True)
                finally:
                    self._bench_scan_overrides = None
                self._check_stop()
                self._reconcile_purchase_pending()
                unexpected = incremental and any(obs.state == SlotState.KNOWN
                    and obs.character.name not in names and (old.character is None
                        or old.character.name != obs.character.name)
                    for area, slots in self._observations.items()
                    for old, obs in zip(before[area], slots))
                matches = {name: [obs for slots in self._observations.values() for obs in slots
                    if obs.character is not None and obs.character.name == name] for name in names}
                if (not unexpected and not self._bench_dirty and all(observation_identity(obs) is not None
                        for obs in self._observations["in_hand"]) and all(matches[name] and all(
                        obs.state == SlotState.KNOWN and observation_identity(obs) is not None
                        and type(obs.stars) is int for obs in matches[name]) for name in names)):
                    return True
                full_scan = True
                if attempt == 0:
                    logger.info("[购后增量核实] 观察不完整或与交易前记录冲突，恢复完整识别")
                    self._check_stop()
                    self.operator.sleep(0.3)
            # Keep unresolved transactions visible to the outer recovery path.
            self._purchase_pending_names.update(names)
            return False
        finally:
            self._bench_scan_overrides = None
            self._purchase_scan_baseline = None

    def _recover_full_shop_offer(self):
        """Dismiss a full-bench overlay before considering a safe XP input."""
        if not self._set_shop_open(False):
            return None
        self.operator.sleep(0.3)
        if not self._set_shop_open(True):
            return None
        for _ in range(2):
            self._check_stop()
            offer = self._scan_store()
            if offer.state in (ShopState.READY, ShopState.EMPTY) and not offer.reason.startswith("partial"):
                return offer
            self.operator.sleep(0.3)
        return None

    def _economy_upgrade_gate(self, level, unmet):
        """Distinguish a purchasable business gap from missing evidence."""
        gate = self.formation_config.upgrade_gate if self.formation_config else None
        decision = stage_upgrade_allowed(self.formation_config, self._observations, level, self._observed_prices)
        if decision.allowed:
            return True, False, False, decision.reason
        if gate is None or level is None:
            return None, None, False, decision.reason
        field = [o for area in ("on_field", "off_field") for o in self._observations[area]]
        bench = self._observations["in_hand"]
        unknown_field = any(observation_identity(o) is None for o in field)
        actionable = needs_prepare = False
        for name, stars in gate.fielded.items():
            owned = [o for o in field + bench if o.state == SlotState.KNOWN and o.character.name == name]
            if any(observation_identity(o) is None or o.stars is None for o in owned):
                return None, None, False, "upgrade_gate_stars_unknown"
            if any(o.state == SlotState.KNOWN and o.character.name == name and o.stars >= stars for o in field):
                continue
            if unknown_field:
                return None, None, False, "upgrade_gate_roster_unknown"
            needs_prepare |= any(o.state == SlotState.KNOWN and o.character.name == name and o.stars >= stars for o in bench)
            actionable |= name in unmet
        for name, price in gate.prices.items():
            if name not in self._observed_prices:
                return None, None, False, "upgrade_gate_price_unknown"
            present = any(o.state == SlotState.KNOWN and o.character.name == name for o in field)
            if present and self._observed_prices[name] >= price:
                continue
            if unknown_field:
                return None, None, False, "upgrade_gate_roster_unknown"
            # Bench copies of a fielded unit are merge material.
            needs_prepare |= not present and any(
                o.state == SlotState.KNOWN and o.character.name == name for o in bench)
            actionable |= name in unmet
        counts = confirmed_trait_counts(self.formation_config, self._observations)
        for trait, count in gate.traits.items():
            if counts.get(trait, 0) >= count:
                continue
            if unknown_field:
                return None, None, False, "upgrade_gate_traits_unknown"
            field_names = {o.character.name for o in field if o.state == SlotState.KNOWN}
            members = {name for name, traits in self.formation_config.traits.items()
                       if trait in traits and name not in field_names}
            needs_prepare |= any(o.state == SlotState.KNOWN and o.character.name in members for o in bench)
            actionable |= bool(members & unmet.keys())
        return False, actionable, needs_prepare, decision.reason

    def _economy_space_safe(self, unmet):
        if any(o.state == SlotState.EMPTY and observation_identity(o) is not None for o in self._observations["in_hand"]):
            return True
        # Only a positively observed merge can receive a card on a full bench.
        for name in unmet:
            counts = {}
            for slots in self._observations.values():
                for o in slots:
                    if o.state == SlotState.KNOWN and observation_identity(o) is not None and o.character.name == name:
                        counts[o.stars] = counts.get(o.stars, 0) + 1
            if counts.get(1, 0) >= 2:
                return True
        if any(observation_identity(o) is None for o in self._observations["in_hand"]):
            return None
        return False

    def _confirm_experience(self, before_level, before_coins):
        # Single XP purchases often do not increase the level. Verify the exact
        # isolated charge and a reliable nondecreasing level instead.
        for _ in range(2):
            self._check_stop()
            level, coins = self.get_level(), self.get_coins()
            if (type(level) is int and type(coins) is int and level >= before_level
                    and coins == before_coins - self.SHOP_EXPERIENCE_COST):
                return level, coins
            self.operator.sleep(0.3)
            self._invalidate_level()
        return None

    def _confirm_completed_battle(self, evidence):
        if not self._pending_battle_id or not self._battle_entry_confirmed:
            return False
        battle_id = self._pending_battle_id
        if self._session_store is not None:
            if not self._session_store.confirm_battle(battle_id):
                # Retry the same ID, never advance using a second transaction.
                if not self._session_store.confirm_battle(battle_id):
                    self._fail_battle("battle_checkpoint_not_saved")
            checkpoint = self._session_store.checkpoint
            self._confirmed_battle_count = checkpoint.confirmed_battle_count
            self._equipment_battles_since_check = checkpoint.equipment_battles_since_check
        else:
            if self._confirmed_battle_count is not None:
                self._confirmed_battle_count += 1
            self._equipment_battles_since_check += 1
        self._last_completed_battle_id = battle_id
        self._pending_battle_id = None
        self._battle_entry_confirmed = False
        logger.info(f"[真实战斗] id={battle_id} confirmed={self._confirmed_battle_count} "
                    f"equipment_since_check={self._equipment_battles_since_check} evidence={evidence}")
        return True

    def _equipment_others_available(self):
        return (self.equipment_config is not None and self._preparation_round is not None
                and self._preparation_round >= self.equipment_config.others_from_round)

    def _equipment_due(self):
        if self.equipment_config is not None:
            self._read_preparation_round()
            if self._equipment_others_available() and not self._equipment_others_checked:
                return True
        if self.equipment_interval_battles is None:
            return self._equipment_dirty or self._needs_equipment_check()
        return self._equipment_battles_since_check >= self.equipment_interval_battles

    def _shopping_finish_after_recheck(self, offer, level, coins, context):
        """Plan from the last shop frame, without reopening just to exit.

        The frame is only for deciding whether more shopping could be useful.
        Any further input must first reopen and re-observe the actual shop.
        """
        if context is None or offer.state not in (ShopState.READY, ShopState.EMPTY) or offer.reason.startswith("partial"):
            return None
        _, target, reserve, searching_main = context
        unmet, unknown = self._economy_unmet_goals()
        if unknown:
            return None
        if any(card.character.name in unmet and (card.price is None or
               can_afford_purchase(coins, card.price, reserve)) for card in offer.cards):
            return None
        allowed, actionable, needs_prepare, _ = self._economy_upgrade_gate(level, unmet)
        all_in = self._all_in_decision is not None and self._all_in_decision.enabled
        if all_in and level < target:
            return None  # Preserve the main loop's final-push upgrade policy.
        decision = next_economy_action(level=level, coins=coins, target_level=target,
            reserve_gold=reserve, purchase_reserve_gold=0 if all_in else self.economy_config.purchase_reserve_gold,
            xp_cost=self.SHOP_EXPERIENCE_COST, roll_cost=self.SHOP_REFRESH_COST,
            upgrade_allowed=allowed, has_purchase_targets=bool(unmet),
            space_safe=self._economy_space_safe(unmet), needs_prepare=needs_prepare,
            first_main_search=searching_main, gate_has_purchase_targets=actionable)
        if decision.action == "roll" and not self._opening_action_allowed("refresh"):
            return "opening_round_unknown" if self._preparation_round is None else "opening_refresh_locked"
        return decision.reason if decision.action in ("save", "prepare") else None

    def _credit_shopping_time(self):
        """Pause preparation limits during shopping, but not during board cleanup."""
        started = getattr(self, "_shopping_clock_started", None)
        if started is None:
            return
        elapsed = time.monotonic() - started
        if self._preparation_deadline is not None:
            self._preparation_deadline += elapsed
        if self._formation_deadline is not None:
            self._formation_deadline += elapsed
        self._shopping_clock_started = None

    @contextmanager
    def _shopping_cleanup_window(self):
        self._credit_shopping_time()
        try:
            yield
        finally:
            self._shopping_clock_started = time.monotonic()

    def _held_purchase_copies(self, name):
        """Count one-star equivalents only from actual, reconciled observations."""
        copies = 0
        for slots in self._observations.values():
            for obs in slots:
                if observation_identity(obs) is None:
                    return None
                if obs.state == SlotState.KNOWN and obs.character.name == name:
                    if type(obs.stars) is not int or not 1 <= obs.stars <= 3:
                        return None
                    copies += 3 ** (obs.stars - 1)
        return copies

    def _demand_cycle_goals(self, cycle):
        return {name: stars for name, stars in cycle.get("goals", {}).items()
                if cycle["before"][name] + cycle["receipts"].get(name, 0) < 3 ** (stars - 1)}

    def _settle_demand_purchases(self, cycle, progress):
        """Observe one shopping run before using its purchases for placement/XP."""
        receipts = cycle.get("receipts", {})
        if not receipts:
            return
        self._check_stop()
        logger.info(f"[搜牌结算] 统一复核持有和合成：{receipts}")
        self._purchase_scan_baseline = cycle.get("baseline")
        try:
            if not self._recheck_purchased_characters(set(receipts)):
                progress.update(result=ActionResult.INDETERMINATE, reason="purchase_recheck_unknown")
                return
        finally:
            self._purchase_scan_baseline = None
        progress["closed"] = True
        def holdings_match():
            for name, count in receipts.items():
                actual = self._held_purchase_copies(name)
                if actual is None or (name not in cycle["transformed"]
                        and actual < cycle["before"][name] + count):
                    return False
            return True

        if not holdings_match():
            logger.info("[搜牌结算] 持有份数与采购记录不符，完整复核一次前后台和备战席")
            self._purchase_scan_baseline = (None, {})
            try:
                confirmed = self._recheck_purchased_characters(set(receipts))
            finally:
                self._purchase_scan_baseline = None
            if not confirmed or not holdings_match():
                self._purchase_pending_names.update(receipts)
                progress.update(result=ActionResult.INDETERMINATE, reason="purchase_recheck_unknown")
                return
        progress["purchases"] += sum(receipts.values())
        roles = cycle["roles"]
        handoff = cycle.get("handoff", "")
        if not handoff and any(name in roles and name not in self._role_purchase_goals() for name in receipts):
            handoff = "role_placement"
        cycle.clear()
        self._record_checkpoint(phase="preparation", pending_actions=[])
        if handoff and self._preparation_round != (3, 7):
            progress["reason"] = handoff
            return
        with self._shopping_cleanup_window():
            self._check_stop()
            self.place_character()
            self._check_stop()
            if self._placement_pending or self._pending_move is not None:
                progress["reason"] = "candidate_needs_preparation"
                return
            sale = self.sell_character()
            if sale.attempted and sale.result != ActionResult.CONFIRMED:
                progress.update(result=sale.result, reason="page_sale_not_confirmed")
                return
        self._check_stop()
        progress["coins"] = self.get_coins()
        if progress["coins"] is None:
            progress.update(result=ActionResult.INDETERMINATE, reason="unknown_coins")
        logger.info(f"[搜牌结算] 已确认购买={progress['purchases']} "
                    f"已售余牌={sale.confirmed} 整理后实际金币={progress['coins']}")

    def _purchase_demand_page(self, offer, *, max_attempts, max_purchases,
                              skipped_slots, progress, cycle=None, defer=False,
                              spendable_coins=None):
        """Keep a provisional purchase ledger across pages; confirm at a real boundary.

        Gold is read once after the page. Card disappearance only permits the
        next shopping input: star gates, placement and sales require actual
        inventory evidence, never predicted merges or predicted free slots.
        """
        progress.update(offer=offer, closed=False, coins=None, reset_offer=False,
                        result=ActionResult.CONFIRMED, reason="")
        cycle = {} if cycle is None else cycle
        if not cycle.get("receipts"):
            cycle.clear()
            goals, unknown = self._economy_unmet_goals()
            if unknown:
                progress.update(result=ActionResult.INDETERMINATE, reason="purchase_targets_unknown")
                return
            before = {name: self._held_purchase_copies(name) for name in goals}
            if any(value is None for value in before.values()):
                progress.update(result=ActionResult.INDETERMINATE, reason="purchase_targets_unknown")
                return
            cycle.update(goals=goals, roles=self._role_purchase_goals(), before=before,
                receipts={}, transformed=set(), handoff="",
                spaces=sum(o.state == SlotState.EMPTY and observation_identity(o) is not None
                           for o in self._observations["in_hand"]),
                gate=self._economy_upgrade_gate(self.get_level(), goals),
                baseline=(self._layout_revision, {area: tuple(slots)
                          for area, slots in self._observations.items()})
                    if not self._bench_dirty and not self._dirty_slots else None)
        if offer.reason.startswith("partial"):
            progress.update(result=ActionResult.INDETERMINATE, reason="partial_store")
            return
        unmet = self._demand_cycle_goals(cycle)
        roles = cycle["roles"]
        targets = [c for c in offer.cards if c.character.name in unmet
                   and c.slot_index not in skipped_slots
                   and not c.character.is_locked and not c.character.is_npc]
        targets.sort(key=lambda c: (
            not (c.character.name == self.main_c and not self.main_c_first_fielded_confirmed),
            c.character.name not in roles, -(c.character.priority or 0), c.slot_index))
        receipts = cycle["receipts"]
        starting_count = sum(receipts.values())
        settle_now = False
        for card in targets:
            self._check_stop()
            name = card.character.name
            if spendable_coins is not None:
                if card.price is None:
                    progress.update(result=ActionResult.INDETERMINATE, reason="purchase_evidence_unknown")
                    break
                if not can_afford_purchase(spendable_coins, card.price, 0):
                    continue
            if progress["attempts"] >= max_attempts:
                progress["reason"] = "action_budget"
                break
            if sum(receipts.values()) - starting_count >= max_purchases:
                progress["reason"] = "purchase_budget"
                break
            if cycle["spaces"] <= 0:
                if receipts:
                    settle_now = True
                    break
                if self._economy_space_safe({name: unmet[name]}) is not True:
                    # Another offer on this page may merge immediately even
                    # when this higher-priority card needs a free bench slot.
                    continue
            self._record_checkpoint(phase="purchase_pending", pending_actions=[
                f"搜牌购买复核：{name} 商店槽位{card.slot_index}"])
            self._purchase_pending_names.add(name)
            progress["attempts"] += 1
            logger.info(f"[连续采购] 尝试购买 商店[{card.slot_index}] {name} 价格={card.price}")
            if not self.operator.click_point(*card.target, after_sleep=0.5):
                progress.update(result=ActionResult.FAILED, reason="purchase_click_failed")
                return
            self._check_stop()
            self.operator.move_to(0.5, 0.5)
            signature = {(c.slot_index, c.character.name) for c in offer.cards}
            expected = signature - {(card.slot_index, name)}
            changed = unchanged = False
            for _ in range(2):
                self._check_stop()
                after = self._scan_store()
                self._check_stop()
                reliable = after.state in (ShopState.READY, ShopState.EMPTY) and not after.reason.startswith("partial")
                current = {(c.slot_index, c.character.name) for c in after.cards}
                changed = reliable and current == expected
                unchanged = reliable and current == signature
                if changed:
                    break
                self.operator.sleep(0.3)
            if unchanged:
                skipped_slots.add(card.slot_index)
                if name not in receipts:
                    self._purchase_pending_names.discard(name)
                offer = after
                progress["offer"] = offer
                logger.info(f"[连续采购] {name} 未成交，当前页跳过槽位{card.slot_index}")
                continue
            self._bench_dirty = True
            self._invalidate_character_evidence(name, "purchase_or_merge", level_changed=False)
            receipts[name] = receipts.get(name, 0) + 1
            if spendable_coins is not None:
                spendable_coins -= card.price
            cycle["spaces"] -= 1
            offer = after
            progress["offer"] = offer if changed else None
            if name == Characters.SilverWolfLV999.name and self.detect_silver_wolf_lv999():
                if changed:
                    cycle["transformed"].add(name)
                cycle["baseline"] = None
                progress["reset_offer"] = True
                self._invalidate_level()
                progress["offer"] = self._scan_store()
                settle_now = True
                break
            if name == self.main_c and not self.main_c_first_fielded_confirmed:
                cycle["handoff"] = "main_c_placement"
                settle_now = True
                break
            if name in roles and cycle["before"][name] + receipts[name] >= 3 ** (roles[name] - 1):
                settle_now = True
                break
            if not changed:
                cycle["baseline"] = None
                settle_now = True
                break
        if receipts and (not defer or settle_now or progress["reason"] or cycle["spaces"] <= 0):
            self._settle_demand_purchases(cycle, progress)
        elif progress["attempts"]:
            self._check_stop()
            progress["coins"] = self.get_coins()
            if progress["coins"] is None:
                progress.update(result=ActionResult.INDETERMINATE, reason="unknown_coins")
            logger.info(f"[连续采购] 本页结束，累计待复核={receipts} 实际金币={progress['coins']}；保留商店等待经济判断")
        if not receipts and not self._purchase_pending_names:
            self._record_checkpoint(phase="preparation", pending_actions=[])

    def _shopping_final_round(self):
        """Spend the final preparation's gold before applying strategy economy rules."""
        self._invalidate_level()
        self._shopping_active = True
        self._shopping_clock_started = time.monotonic()
        prior = dict(self._preparation_shop_counts)
        attempted = purchased = refreshes = experiences = 0
        result, reason = ActionResult.CONFIRMED, "final_round_gold_exhausted"
        offer = None
        skipped_slots = set()
        unchanged_refreshes = 0
        logger.info(f"[终局运营] 3-7强制消费：逐级判断升级，否则零保留买牌搜牌，"
                    f"搜牌累计上限={self.FINAL_ROUND_REFRESH_LIMIT}，覆盖所有配置经济限制")
        try:
            if self._purchase_pending_names:
                if not self._recheck_purchased_characters(set(self._purchase_pending_names)):
                    result, reason = ActionResult.INDETERMINATE, "purchase_recheck_unknown"
            if result == ActionResult.CONFIRMED:
                self._ensure_shopping_observations(force=True)
            while result == ActionResult.CONFIRMED:
                self._check_stop()
                if not self._set_shop_open(True):
                    result, reason = ActionResult.INDETERMINATE, "shop_not_open_after_recheck"
                    break
                self._invalidate_level()
                coins = self.get_coins()
                if coins == 0:
                    reason = "final_round_gold_exhausted"
                    break
                level = self.get_level()
                if level is None or coins is None:
                    result, reason = ActionResult.INDETERMINATE, "unknown_level" if level is None else "unknown_coins"
                    break
                progress = (self._read_experience_progress(level, recognize_cap=True)
                            if coins >= self.SHOP_EXPERIENCE_COST else None)
                decision = next_final_round_action(level=level, coins=coins,
                    experience_current=progress[0] if progress else None,
                    experience_required=progress[1] if progress else None,
                    level_capped=progress == (0, 0), xp_cost=self.SHOP_EXPERIENCE_COST)
                logger.info(f"[终局运营] L={level} gold={coins} xp={progress} "
                    f"next_level={decision.target_level} upgrade_cost={decision.upgrade_cost} "
                    f"action={decision.action} reason={decision.reason}")
                if decision.action in ("recover", "save"):
                    result = ActionResult.INDETERMINATE if decision.action == "recover" else ActionResult.CONFIRMED
                    reason = decision.reason
                    break
                if decision.action == "buy_xp":
                    # Commit only to one wholly affordable level, confirming each input.
                    for _ in range(decision.purchases):
                        self._check_stop()
                        if not self._buy_experience(level, final_round=True):
                            result, reason = ActionResult.FAILED, "experience_click_failed"
                            break
                        experiences += 1
                        confirmed = self._confirm_experience(level, coins)
                        if confirmed is None:
                            result, reason = ActionResult.INDETERMINATE, "final_round_upgrade_not_confirmed"
                            break
                        level, coins = confirmed
                        if level >= decision.target_level:
                            break
                    if result != ActionResult.CONFIRMED:
                        break
                    if level < decision.target_level:
                        result, reason = ActionResult.INDETERMINATE, "final_round_upgrade_not_confirmed"
                        break
                    with self._shopping_cleanup_window():
                        if not self._set_shop_open(False):
                            self._fail_battle("final_round_preparation_not_confirmed")
                        self.update_max_team_size()
                        self.place_character()
                    self._ensure_shopping_observations(force=True)
                    offer = None
                    skipped_slots.clear()
                    continue
                if offer is None:
                    offer = self._scan_store()
                if offer.state == ShopState.UNKNOWN:
                    self.operator.sleep(0.3)
                    offer = self._scan_store()
                if offer.state == ShopState.FULL:
                    self._bench_full = True
                    offer = self._recover_full_shop_offer()
                if offer is None or offer.state == ShopState.UNKNOWN:
                    result, reason = ActionResult.INDETERMINATE, "unknown"
                    break
                page = dict(attempts=0, purchases=0)
                # Retain the strategy's useful-card list, but reserve no gold.
                self._purchase_demand_page(offer, max_attempts=5, max_purchases=5,
                    skipped_slots=skipped_slots, progress=page, spendable_coins=coins)
                attempted += page["attempts"]
                purchased += page["purchases"]
                offer = None if page["closed"] or page["reset_offer"] else page["offer"]
                if page["reason"]:
                    if (page["reason"] in {"main_c_placement", "role_placement", "candidate_needs_preparation"}
                            and self._pending_move is None and not self._placement_pending):
                        self._ensure_shopping_observations(force=True)
                    else:
                        result, reason = page["result"], page["reason"]
                        break
                if page["purchases"]:
                    self._ensure_shopping_observations(force=True)
                    continue  # Sales or merges may have changed the next-level budget.
                if page["coins"] is not None:
                    coins = page["coins"]
                if coins < self.SHOP_REFRESH_COST:
                    reason = "final_round_gold_exhausted" if coins == 0 else "final_round_no_affordable_action"
                    logger.info(f"[终局运营] 剩余金币={coins}，当前商店无可买需求牌且不足刷新费用")
                    break
                if prior["refreshes"] + refreshes >= self.FINAL_ROUND_REFRESH_LIMIT:
                    reason = "final_round_refresh_limit"
                    logger.info(f"[终局运营] 已达到3-7搜牌上限={self.FINAL_ROUND_REFRESH_LIMIT}，"
                                f"当前页需求牌已处理，剩余金币={coins}，停止刷新")
                    break
                if offer is None:
                    continue
                signature = tuple((card.slot_index, card.character.name) for card in offer.cards)
                # Count the input even when its confirmation fails; recovery cannot renew it.
                refreshes += 1
                if not self.operator.press_key("d"):
                    result, reason = ActionResult.FAILED, "refresh_click_failed"
                    break
                self.operator.sleep(0.5)
                after = self._scan_store()
                if after.state == ShopState.FULL:
                    after = self._recover_full_shop_offer()
                if after is None or after.state == ShopState.UNKNOWN:
                    result, reason = ActionResult.INDETERMINATE, "unknown"
                    break
                after_coins = self.get_coins()
                if after_coins is None or coins - after_coins not in (0, self.SHOP_REFRESH_COST):
                    result, reason = ActionResult.INDETERMINATE, "final_round_refresh_not_confirmed"
                    break
                new_signature = tuple((card.slot_index, card.character.name) for card in after.cards)
                logger.info(f"[终局运营] 搜牌={prior['refreshes'] + refreshes}/{self.FINAL_ROUND_REFRESH_LIMIT} "
                            f"金币={coins}->{after_coins} 牌面变化={signature != new_signature}")
                if after_coins == coins:
                    unchanged_refreshes = unchanged_refreshes + 1 if signature == new_signature else 0
                    if unchanged_refreshes >= 2:
                        result, reason = ActionResult.INDETERMINATE, "final_round_refresh_not_confirmed"
                        break
                else:
                    unchanged_refreshes = 0
                # Even an identical offer is progress when the refresh actually spent gold.
                offer = after
                skipped_slots.clear()
        finally:
            self._invalidate_level()
            try:
                if sys.exc_info()[0] is None and not self._set_shop_open(False):
                    self._fail_battle("shopping_shop_not_closed")
            finally:
                self._credit_shopping_time()
                self._preparation_shop_counts = dict(attempts=prior["attempts"] + attempted,
                    purchases=prior["purchases"] + purchased, refreshes=prior["refreshes"] + refreshes,
                    experiences=prior["experiences"] + experiences)
                self._shopping_active = False
        self._last_shopping_result = ShoppingResult(result, attempted, purchased, refreshes, experiences, reason)
        logger.info(f"[终局运营] 本次结束：{self._last_shopping_result}")
        return self._last_shopping_result

    def shopping(self):
        """Apply the mandatory final-round rule before the strategy's shopping rules."""
        self._check_stop()
        if not self._set_shop_open(False):
            return ShoppingResult(ActionResult.INDETERMINATE, reason="final_round_page_unknown")
        current_round = self._read_preparation_round()
        if current_round is None:
            return ShoppingResult(ActionResult.INDETERMINATE, reason="final_round_unknown")
        if current_round == (3, 7):
            return self._shopping_final_round()
        self._invalidate_level()
        attempted = purchased = refreshes = experiences = 0
        purchased_in_offer = False
        recheck_names = set(self._purchase_pending_names)
        checked_purchase_names = set(self._purchase_pending_names)
        unchanged_refreshes = 0
        purchase_rechecks = set()
        result = ActionResult.CONFIRMED
        reason = "finished"
        self._shopping_clock_started = time.monotonic()
        self._shopping_active = True
        prior = dict(self._preparation_shop_counts)
        previous_experience = None
        shop_opened = False
        self._shopping_deadline = None
        limits = dict(self.shopping_budget)
        batch = None
        batch_goals = {}
        batch_prices = {}
        normal_exit = False
        balance = None
        skipped_page_slots = set()
        page_progress = dict(attempts=0, purchases=0)
        purchase_cycle = {}
        try:
            if not self._purchase_pending_names:
                self._ensure_shopping_observations()
            # Read the heading while the shop is closed and reuse it throughout
            # this preparation, including a purchase cleanup/reopen cycle.
            refresh_allowed = self._opening_action_allowed("refresh")
            shop_opened = self._set_shop_open(True)
            if not shop_opened:
                self._last_shopping_result = ShoppingResult(ActionResult.INDETERMINATE,
                    0, 0, 0, 0, "shop_not_open")
                logger.warning(f"商店本轮结束：{self._last_shopping_result}")
                return self._last_shopping_result
            # Reads and merge recovery have their own finite guard. The action
            # budget counts purchases, refreshes and experience inputs only.
            offer = None
            offer_revision, evaluated_revision = 0, -1
            refreshed_offer = allow_mid_upgrade = False
            refresh_stalled = False
            full_bench_recovered = False
            remaining_targets = []
            self._shopping_deadline = None
            passes = 0
            while passes < limits["actions"] * 4 + 10:
                passes += 1
                page_economy_decision = None
                self._check_stop()
                self._confirm_main_c_fielded()
                role_goals = {} if batch is not None else self._role_purchase_goals()
                if batch is None and any(self._role_placement_unresolved(e) and not any(n in role_goals for n in e.bench_candidates)
                       for e in self._role_evaluations().values() if e.state != "satisfied"):
                    reason = "role_placement"
                    break
                if self._main_c_in_hand() or (self.main_c and
                        not self.main_c_first_fielded_confirmed and self.main_c in self._purchase_pending_names):
                    reason = "main_c_placement"
                    break
                if self.economy_config is not None and recheck_names and (batch is None or not batch.space_safe):
                    # Save a current planning frame before closing the shop.
                    # Event handlers discard earlier frames and balances.
                    if offer is None:
                        offer = self._scan_store()
                    if balance is None:
                        balance = self.get_coins()
                    recheck_level = self.get_level()
                    recheck_context = self._economy_context(recheck_level, balance) if recheck_level is not None else None
                    # Re-establish actual space before another batch. Predicted
                    # merges never create virtual empty bench slots.
                    logger.info(f"[购物批次] 提前复核={sorted(recheck_names)} 原因=需要现场状态或备战空间")
                    if not self._recheck_purchased_characters(recheck_names):
                        result, reason = ActionResult.INDETERMINATE, "purchase_recheck_unknown"
                        break
                    checked_purchase_names.update(recheck_names)
                    recheck_names.clear()
                    batch = None
                    shop_opened = False
                    finish_reason = self._shopping_finish_after_recheck(offer, recheck_level, balance, recheck_context)
                    if finish_reason is not None:
                        reason = finish_reason
                        logger.info(f"[购物收尾] 复核后无需继续消费，保持商店关闭，原因={reason}")
                        break
                    if recheck_context is None:
                        result, reason = ActionResult.INDETERMINATE, "economy_gold_not_confirmed"
                        break
                    shop_opened = self._set_shop_open(True)
                    if not shop_opened:
                        result, reason = ActionResult.INDETERMINATE, "shop_not_open_after_recheck"
                        break
                    offer = None
                    continue  # Recompute role/main-C needs from the new board.
                if offer is None:
                    offer = self._scan_store()
                if offer.state == ShopState.UNKNOWN:
                    self.operator.sleep(0.3)
                    offer = self._scan_store()
                if offer.state == ShopState.FULL:
                    self._bench_full = True
                    if self.economy_config is None:
                        reason = "full"
                        break
                    offer = self._recover_full_shop_offer()
                    if offer is None:
                        result, reason = ActionResult.INDETERMINATE, "full_shop_recovery_unknown"
                        break
                    full_bench_recovered = True
                if offer.state == ShopState.UNKNOWN:
                    result, reason = ActionResult.INDETERMINATE, "unknown"
                    break
                if batch is not None:
                    held_names = {o.character.name for slots in self._observations.values() for o in slots
                                  if o.character is not None}
                    changed_prices = {name for name, price in batch_prices.items()
                                      if self._observed_prices.get(name) != price
                                      and name in held_names | recheck_names}
                    if changed_prices:
                        recheck_names.update(changed_prices)
                        batch = None
                        continue
                offered_pending = ({c.character.name for c in offer.cards} & recheck_names
                                   if batch is None else set())
                if offered_pending:
                    # A confirmed transaction may merge on the field or bench.
                    # Re-read before buying this name again, then rebuild the
                    # offer after closing character panels.
                    for area in ("on_field", "off_field"):
                        for i, o in enumerate(self._observations[area]):
                            historical = getattr(self, area + "_character")[i]
                            if (o.character or historical) is not None and (o.character or historical).name in offered_pending:
                                self._dirty_slots.add((area, i))
                    self._refresh_dirty_field()
                    if self._bench_dirty or any(o.state == SlotState.UNKNOWN or o.stars is None
                            and o.character is not None and o.character.name in offered_pending
                            for o in self._observations["in_hand"]):
                        self.get_in_hand_area(True)
                    checked_purchase_names.update(offered_pending)
                    recheck_names.difference_update(offered_pending)
                    # Inspecting merged cards closes the shop just like the
                    # pre-shopping board scan. Restore it before the next OCR.
                    if not self._set_shop_open(True):
                        result, reason = ActionResult.INDETERMINATE, "shop_not_open_after_recheck"
                        break
                    offer = None
                    continue
                level = self.get_level()
                if self.economy_config is not None and level is None:
                    # Stage restoration and the first-main reserve both depend
                    # on level. Never spend under a guessed cheaper reserve.
                    self.operator.sleep(0.3)
                    self._invalidate_level()
                    level = self.get_level()
                    if level is None:
                        result, reason = ActionResult.INDETERMINATE, "unknown_level"
                        break
                coins = balance if balance is not None else self.get_coins()
                balance = coins
                if coins is None:
                    result, reason = ActionResult.INDETERMINATE, "unknown_coins"
                    break
                if previous_experience == (level, coins):
                    result, reason = ActionResult.INDETERMINATE, "experience_not_confirmed"
                    break
                previous_experience = None
                economy_context = None
                if self.economy_config is not None:
                    economy_context = self._economy_context(level, coins)
                    if economy_context is None:
                        result, reason = ActionResult.INDETERMINATE, "economy_gold_not_confirmed"
                        break
                searching_main = bool(self.main_c and not self.main_c_first_fielded_confirmed
                                      and level is not None and level >= self.main_c_search_level)
                reserve = (self.main_c_search_min_coins if searching_main else
                           (0 if self.is_overclock else self.min_coins))
                if economy_context is not None:
                    stage_selection, effective_target, reserve, searching_main = economy_context
                    if batch is not None and level < effective_target:
                        batch = None
                        if recheck_names:
                            continue  # Never use projected copies to unlock XP.
                    if (reserve != 0 and batch is None and not recheck_names and not role_goals
                            and level >= effective_target and not searching_main
                            and not self._purchase_pending_names and not self._bench_dirty
                            and not self._placement_pending and not self._form_change_pending
                            and not self._dirty_slots and all(observation_identity(o) is not None
                                for slots in self._observations.values() for o in slots)):
                        candidate = ShoppingBatch.from_observations(self._observations)
                        if candidate is not None and candidate.space_safe:
                            batch = candidate
                            batch_goals = self._purchase_goals()
                            batch_prices = dict(self._observed_prices)
                            logger.info(f"[购物批次] 按已确认持有量连续采购，待购目标={batch.missing_goals(batch_goals)}")
                all_in = self._all_in_decision is not None and self._all_in_decision.enabled
                final_push = all_in and level < self._all_in_decision.target_level
                if all_in:
                    # Fix the balance-derived allowance once per preparation;
                    # unchanged balances must not renew it across recoveries.
                    if self._all_in_budget is None:
                        self._all_in_budget = (coins + prior["attempts"] + prior["refreshes"]
                            + prior["experiences"] + attempted + refreshes + experiences + 1)
                    for key in ("actions", "purchases", "refreshes", "experiences"):
                        limits[key] = max(limits[key], self._all_in_budget)
                logger.info(f"[搜牌预算] 首次主C搜索={searching_main} 等级={level} 金币={coins} "
                            f"有效保留={reserve} 刷新费用={self.SHOP_REFRESH_COST}")
                if final_push:
                    actions = prior["attempts"] + prior["refreshes"] + prior["experiences"] + attempted + refreshes + experiences
                    if actions >= limits["actions"] or prior["experiences"] + experiences >= limits["experiences"]:
                        reason = "experience_budget"
                        break
                    if not self._buy_experience(level, final_push=True):
                        result, reason = ActionResult.FAILED, "experience_click_failed"
                        break
                    experiences += 1
                    confirmed_experience = self._confirm_experience(level, coins)
                    if confirmed_experience is None:
                        result, reason = ActionResult.INDETERMINATE, "experience_not_confirmed"
                        break
                    post_experience_level, balance = confirmed_experience
                    if full_bench_recovered and type(post_experience_level) is int and post_experience_level > level:
                        reason = "purchase_space_blocked"
                        break
                    if (post_experience_level != level or self._form_change_pending
                            or self._runtime_node_pending is not None):
                        offer = None
                    refreshed_offer = False
                    continue
                page_mode = economy_context is not None and reserve == 0
                if page_mode:
                    batch = None
                    actions = prior["attempts"] + prior["refreshes"] + prior["experiences"] + attempted + refreshes + experiences
                    self._purchase_demand_page(offer,
                        max_attempts=max(0, limits["actions"] - actions),
                        max_purchases=max(0, limits["purchases"] - prior["purchases"] - purchased
                            - sum(purchase_cycle.get("receipts", {}).values())),
                        skipped_slots=skipped_page_slots, progress=page_progress,
                        cycle=purchase_cycle, defer=True)
                    page_attempts = page_progress["attempts"]
                    attempted += page_attempts
                    page_progress["attempts"] = 0
                    purchased_in_offer |= bool(page_attempts and purchase_cycle.get("receipts"))
                    if page_progress["coins"] is not None:
                        coins = balance = page_progress["coins"]
                    if purchase_cycle.get("receipts") and not page_progress["reason"]:
                        unmet = self._demand_cycle_goals(purchase_cycle)
                        allowed, actionable, needs_prepare, _ = purchase_cycle["gate"]
                        decision = next_economy_action(level=level, coins=coins, target_level=effective_target,
                            reserve_gold=reserve,
                            purchase_reserve_gold=0 if all_in else self.economy_config.purchase_reserve_gold,
                            xp_cost=self.SHOP_EXPERIENCE_COST, roll_cost=self.SHOP_REFRESH_COST,
                            upgrade_allowed=allowed, has_purchase_targets=bool(unmet),
                            space_safe=purchase_cycle["spaces"] > 0 and not full_bench_recovered,
                            needs_prepare=needs_prepare, first_main_search=searching_main,
                            gate_has_purchase_targets=actionable)
                        gate = self.formation_config.upgrade_gate if self.formation_config else None
                        gate_ready = gate is not None and any(name in purchase_cycle["receipts"] and
                            purchase_cycle["before"][name] + purchase_cycle["receipts"][name] >= 3 ** (stars - 1)
                            for name, stars in gate.fielded.items())
                        actions = prior["attempts"] + prior["refreshes"] + prior["experiences"] + attempted + refreshes + experiences
                        budget_end = (prior["refreshes"] + refreshes >= limits["refreshes"]
                            or actions + 1 >= limits["actions"]
                            or prior["purchases"] + purchased + sum(purchase_cycle["receipts"].values()) >= limits["purchases"])
                        if (decision.action != "roll" or not refresh_allowed
                                or gate_ready or budget_end or refresh_stalled):
                            logger.info(f"[搜牌结算] 边界={decision.reason} 金币={coins} "
                                        f"目标可解锁={gate_ready} 预算用尽={budget_end}")
                            self._settle_demand_purchases(purchase_cycle, page_progress)
                        else:
                            # No input or observation separates this boundary
                            # decision from the refresh decision below.
                            page_economy_decision = decision
                    purchased += page_progress["purchases"]
                    purchased_in_offer |= page_progress["purchases"] > 0
                    page_progress["attempts"] = page_progress["purchases"] = 0
                    evaluated_revision = offer_revision
                    offer = page_progress["offer"]
                    if page_progress["reset_offer"]:
                        skipped_page_slots.clear()
                    if page_progress["closed"]:
                        shop_opened = False
                    if page_progress["reason"]:
                        result, reason = page_progress["result"], page_progress["reason"]
                        break
                    if page_progress["closed"]:
                        balance = page_progress["coins"]
                        level = self.get_level()
                        context = self._economy_context(level, balance) if level is not None else None
                        planning_offer = replace(offer, cards=tuple(c for c in offer.cards
                            if c.slot_index not in skipped_page_slots)) if offer is not None else None
                        finish_reason = self._shopping_finish_after_recheck(planning_offer,
                            level, balance, context) if planning_offer is not None else None
                        if finish_reason:
                            reason = finish_reason
                            break
                        if offer is None:
                            skipped_page_slots.clear()
                        shop_opened = self._set_shop_open(True)
                        if not shop_opened:
                            result, reason = ActionResult.INDETERMINATE, "shop_not_open_after_recheck"
                            break
                        offer = None
                        continue  # Recompute the stage and goals after sales/placement.
                    if page_progress.get("offer") is None:
                        continue
                targets = []
                restart_offer = False
                role_goals = {} if batch is not None else self._role_purchase_goals()
                for card in (() if page_mode else offer.cards):
                    char = card.character
                    goal = max((batch_goals if batch is not None else self._purchase_goals()).get(char.name, 0),
                               role_goals.get(char.name, 0))
                    if goal <= 0:
                        continue
                    if batch is not None:
                        if card.price is None:
                            # Price/identity uncertainty requires actual evidence;
                            # do not build further decisions on a stale batch.
                            batch = None
                            restart_offer = True
                            if char.name in purchase_rechecks:
                                result, reason = ActionResult.INDETERMINATE, "purchase_evidence_unknown"
                            purchase_rechecks.add(char.name)
                            offer = None
                            break
                        if not batch.can_buy(char.name, goal):
                            logger.info(f"买牌决策=batch_target_covered {char.name} 目标星级={goal}；持有及已确认购买份数已足够")
                            continue
                        decision = evaluate_purchase(card, target_stars=goal, coins=coins,
                            slot_available=batch.space_safe, star_source="batch_purchase_count",
                            protected=char.is_locked or char.is_npc, require_price=True)
                        logger.info(f"买牌决策={decision.reason} {decision.details}")
                        if decision.can_buy and can_afford_purchase(coins, card.price, reserve):
                            targets.append(card)
                        continue
                    is_first_main = char.name == self.main_c and not self.main_c_first_fielded_confirmed
                    fields = [o for area in ("on_field", "off_field")
                              for o in self._observations[area]
                              if o.state == SlotState.KNOWN and o.character.name == char.name]
                    bench_copies = sum(o.state == SlotState.KNOWN and o.character.name == char.name
                                       for o in self._observations["in_hand"])
                    bench = [o for o in self._observations["in_hand"]
                             if o.state == SlotState.KNOWN and o.character.name == char.name]
                    if self.economy_config is not None and (card.price is None or
                            not is_first_main and any(o.stars is None for o in fields + bench)):
                        if char.name in purchase_rechecks:
                            result, reason = ActionResult.INDETERMINATE, "purchase_evidence_unknown"
                            break
                        purchase_rechecks.add(char.name)
                        for area in ("on_field", "off_field"):
                            for i, o in enumerate(self._observations[area]):
                                if o.state == SlotState.KNOWN and o.character.name == char.name:
                                    self._dirty_slots.add((area, i))
                        self._refresh_dirty_field()
                        if bench:
                            self.get_in_hand_area(True)
                        if not self._set_shop_open(True):
                            result, reason = ActionResult.INDETERMINATE, "shop_not_open_after_recheck"
                            break
                        self.operator.sleep(0.3)
                        offer = None
                        restart_offer = True
                        break
                    if char.name in checked_purchase_names and (not fields and not bench or
                            any(o.stars is None for o in fields + bench)):
                        logger.info(f"[购买复核] {char.name} 合成或持有星级未知，暂停同名重复购买")
                        continue
                    decision = evaluate_purchase(
                        card, target_stars=goal,
                        confirmed_stars=0 if is_first_main else self._confirmed_field_stars(char.name),
                        stars_fresh=not is_first_main and bool(fields) and all(o.stars is not None for o in fields),
                        star_source="confirmed_field" if fields else "unobserved",
                        star_revision=max((o.revision for o in fields), default=None),
                        bench_copies=bench_copies,
                        pending_purchase=(goal == 1 and not is_first_main and
                            (char.name in self._purchase_pending_names or bench_copies > 0)),
                        coins=coins, slot_available=False if self._bench_full else None,
                        protected=char.is_locked or char.is_npc, require_price=level is None or self.economy_config is not None)
                    if any(type(o.stars) is int and o.stars >= goal for o in bench):
                        logger.info(f"买牌决策=target_reached_on_bench {char.name} 目标星级={goal}")
                        continue
                    logger.info(f"买牌决策={decision.reason} {decision.details}")
                    if decision.can_buy:
                        if self.economy_config is not None and self._economy_space_safe({char.name: goal}) is not True:
                            logger.info(f"[经济决策] action=prepare reason=purchase_space_unconfirmed name={char.name}")
                            continue
                        if self.economy_config is not None and not can_afford_purchase(coins, card.price, reserve):
                            logger.info(f"[经济决策] action=save reason=purchase_reserve name={char.name} gold={coins} price={card.price} R={reserve}")
                            continue
                        targets.append(card)
                if reason in ("purchase_evidence_unknown", "shop_not_open_after_recheck"):
                    break
                if restart_offer:
                    continue
                targets.sort(key=lambda card: (
                    not (card.character.name == self.main_c and not self.main_c_first_fielded_confirmed),
                    card.character.name not in role_goals,
                    -(card.character.priority or 0), card.slot_index))
                evaluated_revision = offer_revision
                remaining_targets = [c.character.name for c in targets]
                actions = prior["attempts"] + prior["refreshes"] + prior["experiences"] + attempted + refreshes + experiences
                logger.info(f"[商店页] 当前版本={offer_revision} 已评估版本={evaluated_revision} "
                            f"需求={[c.character.name for c in targets]} 输入动作={actions}")
                if targets:
                    card = targets[0]
                    if prior["purchases"] + purchased >= limits["purchases"]:
                        reason = "purchase_budget"
                        break
                    if actions >= limits["actions"]:
                        reason = "action_budget"
                        break
                    logger.info(f"尝试购买商店[{card.slot_index}] {card.character.name}")
                    self._record_checkpoint(phase="purchase_pending", pending_actions=[
                        f"购买确认：{card.character.name} 商店槽位{card.slot_index}"])
                    self._bench_dirty = True
                    self._purchase_pending_names.add(card.character.name)
                    self._invalidate_character_evidence(card.character.name, "purchase_attempt", level_changed=False)
                    attempted += 1
                    if not self.operator.click_point(*card.target, after_sleep=0.5):
                        result, reason = ActionResult.FAILED, "purchase_click_failed"
                        break
                    self.operator.move_to(0.5, 0.5)
                    self._confirmed_purchase_snapshot = None
                    confirmation = self._confirm_purchase(card, coins)
                    if confirmation != ActionResult.CONFIRMED:
                        self.operator.sleep(0.3)
                        confirmation = self._confirm_purchase(card, coins)
                    if confirmation != ActionResult.CONFIRMED:
                        result, reason = confirmation, "purchase_not_confirmed"
                        break
                    purchased += 1
                    if batch is not None:
                        batch.record_purchase(card.character.name)
                    remaining_targets.remove(card.character.name)
                    snapshot = self._confirmed_purchase_snapshot
                    offer, balance = snapshot if snapshot is not None else (None, None)
                    recheck_names.add(card.character.name)
                    purchased_in_offer = True
                    self._purchase_pending_names.add(card.character.name)
                    self._bench_dirty = True
                    self._record_checkpoint(phase="preparation", pending_actions=[])
                    self._invalidate_character_evidence(card.character.name, "purchase_or_merge", level_changed=False)
                    self._equipment_dirty = True
                    logger.info(f"已确认购买 {card.character.name}")
                    if card.character.name == Characters.SilverWolfLV999.name:
                        if self.detect_silver_wolf_lv999():
                            # Only a real event changes form, price or rewards.
                            batch = None
                            offer, balance = None, None
                            self._invalidate_level()
                    if card.character.name == self.main_c and not self.main_c_first_fielded_confirmed:
                        reason = "main_c_placement"
                        break
                    if card.character.name in role_goals:
                        # A one-star material is not yet a two/three-star role
                        # provider. Confirm merges and keep this shopping batch
                        # available until it can actually satisfy the role.
                        if role_goals[card.character.name] > 1:
                            if self.economy_config is not None:
                                if not self._recheck_purchased_characters({card.character.name}):
                                    result, reason = ActionResult.INDETERMINATE, "purchase_recheck_unknown"
                                    break
                            else:
                                self._refresh_dirty_field()
                                self.get_in_hand_area(True)
                            checked_purchase_names.add(card.character.name)
                            recheck_names.discard(card.character.name)
                            if card.character.name in self._role_purchase_goals():
                                if not self._set_shop_open(True):
                                    result, reason = ActionResult.INDETERMINATE, "shop_not_open_after_recheck"
                                    break
                                offer = None
                                continue
                        reason = "role_placement"
                        break
                    continue  # Plan from the confirmed post-purchase page.
                if level is None:
                    result, reason = ActionResult.INDETERMINATE, "unknown_level"
                    break
                if offer.reason.startswith("partial"):
                    result, reason = ActionResult.INDETERMINATE, "partial_store"
                    break
                if refresh_stalled:
                    result, reason = ActionResult.INDETERMINATE, "refresh_no_progress"
                    break
                if actions >= limits["actions"]:
                    reason = "action_budget"
                    break
                economy_decision = None
                if self.economy_config is not None:
                    if purchase_cycle.get("receipts"):
                        unmet, demand_unknown = self._demand_cycle_goals(purchase_cycle), False
                        allowed, gate_actionable, needs_prepare, gate_reason = purchase_cycle["gate"]
                        space_safe = purchase_cycle["spaces"] > 0
                    elif batch is not None:
                        unmet, demand_unknown = batch.missing_goals(batch_goals), False
                        allowed, gate_actionable, needs_prepare, gate_reason = True, False, False, "batch_target_level_reached"
                        space_safe = batch.space_safe
                    else:
                        unmet, demand_unknown = self._economy_unmet_goals()
                        allowed, gate_actionable, needs_prepare, gate_reason = self._economy_upgrade_gate(level, unmet)
                        space_safe = self._economy_space_safe(unmet)
                    economy_decision = page_economy_decision
                    if economy_decision is None:
                        economy_decision = next_economy_action(level=level, coins=coins,
                            target_level=effective_target, reserve_gold=reserve,
                            purchase_reserve_gold=0 if all_in else self.economy_config.purchase_reserve_gold,
                            xp_cost=self.SHOP_EXPERIENCE_COST, roll_cost=self.SHOP_REFRESH_COST,
                            upgrade_allowed=allowed, has_purchase_targets=None if demand_unknown else bool(unmet),
                            space_safe=False if full_bench_recovered else space_safe, needs_prepare=needs_prepare,
                            first_main_search=searching_main, gate_has_purchase_targets=gate_actionable)
                    logger.info(f"[经济决策] mode=stages stage={stage_selection.index} stage_reason={stage_selection.reason} "
                        f"battles={self._confirmed_battle_count} L={level} target={effective_target} gold={coins} R={reserve} "
                        f"P={0 if all_in else self.economy_config.purchase_reserve_gold} xp_cost={self.SHOP_EXPERIENCE_COST} "
                        f"roll_cost={self.SHOP_REFRESH_COST} action={economy_decision.action} "
                        f"reason={economy_decision.reason} gate={gate_reason}")
                    if economy_decision.action in ("save", "prepare", "recover"):
                        result = ActionResult.INDETERMINATE if economy_decision.action == "recover" else ActionResult.CONFIRMED
                        reason = economy_decision.reason
                        break
                elif coins < (self.SHOP_REFRESH_COST if searching_main else 4):
                    reason = "low_coins"
                    break
                if (economy_decision is not None and economy_decision.action == "buy_xp" or
                        economy_decision is None and (level < self.min_level or refreshed_offer and allow_mid_upgrade and level < self.mid_level
                        and not purchased_in_offer) and self._can_upgrade(level)):
                    if prior["experiences"] + experiences >= limits["experiences"]:
                        reason = "experience_budget"
                        break
                    previous_experience = (level, coins) if economy_decision is None else None
                    if not self._buy_experience(level):
                        result, reason = ActionResult.FAILED, "experience_click_failed"
                        break
                    experiences += 1
                    balance = None
                    post_experience_level = None
                    if economy_decision is not None:
                        confirmed_experience = self._confirm_experience(level, coins)
                        if confirmed_experience is None:
                            result, reason = ActionResult.INDETERMINATE, "experience_not_confirmed"
                            break
                        post_experience_level, balance = confirmed_experience
                    elif full_bench_recovered:
                        post_experience_level = self.get_level()
                    if full_bench_recovered and type(post_experience_level) is int and post_experience_level > level:
                        # A newly gained population slot is useful only after
                        # placement. Do not roll or buy into the still-full bench.
                        reason = "purchase_space_blocked"
                        break
                    if (economy_decision is None or post_experience_level != level
                            or self._form_change_pending or self._runtime_node_pending is not None):
                        offer = None
                    refreshed_offer = False
                    continue
                if economy_decision is None and ((searching_main and coins - self.SHOP_REFRESH_COST < reserve)
                        or (not searching_main and not self.is_overclock and coins < reserve)):
                    reason = "coin_reserve"
                    break
                if prior["refreshes"] + refreshes >= limits["refreshes"]:
                    reason = "refresh_budget"
                    break
                # Never create a new offer with no input allowance left to buy
                # from it. Each confirmation retains a finite recovery bound.
                if actions + 1 >= limits["actions"]:
                    reason = "action_budget"
                    break
                if prior["purchases"] + purchased + sum(purchase_cycle.get("receipts", {}).values()) >= limits["purchases"]:
                    reason = "purchase_budget"
                    break
                signature = tuple((c.slot_index, c.character.name) for c in offer.cards)
                if not refresh_allowed:
                    reason = "opening_round_unknown" if self._preparation_round is None else "opening_refresh_locked"
                    break
                if not self.operator.press_key("d"):
                    result, reason = ActionResult.FAILED, "refresh_click_failed"
                    break
                refreshes += 1
                offer_revision += 1
                skipped_page_slots.clear()
                self.operator.sleep(0.5)
                after = self._scan_store()
                if after.state == ShopState.FULL:
                    self._bench_full = True
                    if self.economy_config is None:
                        reason = "full"
                        break
                    after = self._recover_full_shop_offer()
                    if after is None:
                        result, reason = ActionResult.INDETERMINATE, "full_shop_recovery_unknown"
                        break
                    full_bench_recovered = True
                if after.state == ShopState.UNKNOWN:
                    result, reason = ActionResult.INDETERMINATE, "unknown_after_refresh"
                    break
                new_signature = tuple((c.slot_index, c.character.name) for c in after.cards)
                if signature == new_signature:
                    unchanged_refreshes += 1
                else:
                    unchanged_refreshes = 0
                if unchanged_refreshes >= 2:
                    refresh_stalled = True
                coins_after = self.get_coins()
                balance = coins_after
                if coins_after is None:
                    result, reason = ActionResult.INDETERMINATE, "unknown_coins_after_refresh"
                    break
                # The next decision reuses this actual balance. A changed
                # offer can be valid without the standard two-gold charge.
                logger.info(f"[刷新结果] 金币={coins}->{coins_after} "
                            f"牌面变化={signature != new_signature} 连续未变化={unchanged_refreshes}")
                # The refreshed page must be evaluated before any F input or
                # refresh/time boundary. Its snapshot is reusable until an
                # actual input or a character-panel inspection invalidates it.
                offer = after
                refreshed_offer = True
                allow_mid_upgrade = not purchased_in_offer
                purchased_in_offer = False
            else:
                reason = "action_budget"
            normal_exit = True
        finally:
            self._shopping_deadline = None
            self._invalidate_level()
            try:
                if shop_opened and sys.exc_info()[0] is None:
                    self._check_stop()
                    if normal_exit and purchase_cycle.get("receipts") and result == ActionResult.CONFIRMED:
                        page_progress.update(offer=offer, closed=False, coins=None,
                                             result=ActionResult.CONFIRMED, reason="")
                        self._settle_demand_purchases(purchase_cycle, page_progress)
                        purchased += page_progress["purchases"]
                        page_progress["purchases"] = 0
                        if page_progress["reason"]:
                            result, reason = page_progress["result"], page_progress["reason"]
                    elif normal_exit and batch is not None and recheck_names and result == ActionResult.CONFIRMED:
                        logger.info(f"[购物批次] 统一复核={sorted(recheck_names)} "
                                    f"本批购买={batch.pending_count} 购物退出原因={reason}")
                        if not self._recheck_purchased_characters(recheck_names):
                            result, reason = ActionResult.INDETERMINATE, "purchase_recheck_unknown"
                    elif not self._set_shop_open(False):
                        self._fail_battle("shopping_shop_not_closed")
            finally:
                # Resume the same allowances, including when stop/close fails.
                self._credit_shopping_time()
                self._preparation_shop_counts = dict(attempts=prior["attempts"] + attempted + page_progress["attempts"],
                    purchases=prior["purchases"] + purchased + page_progress["purchases"], refreshes=prior["refreshes"] + refreshes,
                    experiences=prior["experiences"] + experiences)
                self._shopping_active = False
        logger.info(f"[商店收尾] 当前版本={offer_revision} 已评估版本={evaluated_revision} "
                    f"当前页已评估={offer_revision == evaluated_revision} 尚未处理={remaining_targets} 退出原因={reason}")
        self._last_shopping_result = ShoppingResult(result, attempted, purchased, refreshes, experiences, reason)
        logger.info(f"商店本轮结束：{self._last_shopping_result}")
        return self._last_shopping_result

    @property
    def current_team_size(self):
        # Unknown historical occupants still count, preventing unsafe overfilling.
        return sum(c is not None for c in self.on_field_character + self.off_field_character)

    @property
    def in_hand_character_count(self):
        return sum(obs.state == SlotState.KNOWN for obs in self._observations["in_hand"])

    def get_level(self):
        if self._level_cache is not None:
            return self._level_cache
        observation = self._vision.read_level(parse_shop_level)
        self._level_cache = observation.level
        self._last_level_read = observation
        logger.info(f"商店等级={observation.level} 来源={observation.evidence} "
                    f"原因={observation.reason} OCR={observation.raw_text!r}")
        if observation.level is None:
            attempts = getattr(self._vision, "last_level_attempts", ())
            details = [f"{item.get('method')}:{item.get('reason')}" for item in attempts
                       if isinstance(item, dict)]
            logger.warning(f"[等级读取] 重试明细={details}；本轮暂停搜牌和购买经验")
        return observation.level

    def _population_observation_key(self):
        return (self._layout_revision, self.max_team_size, tuple(
            observation_identity(o) for area in ("on_field", "off_field")
            for o in self._observations[area]))

    def update_max_team_size(self, *, retry_failed=False):
        key = self._population_observation_key()
        retrying = self._population_read_key == key
        if retrying:
            if (not retry_failed or self._population_current is not None
                    or self._sale_population_retry_used):
                return
            if (self._preparation_deadline is not None
                    and time.monotonic() >= self._preparation_deadline):
                return
            # Recovery and board changes must not renew this extra OCR allowance.
            self._sale_population_retry_used = True
            logger.info("[人口确认] 卖出前重试失败读数，使用增强对比度的两帧识别")
        self._population_read_key = key
        population = (self._vision.read_population(enhance=True) if retrying
                      else self._vision.read_population())
        self._population_current = population.current if population.capacity is not None else None
        if population.capacity is not None:
            self.max_team_size = population.capacity
            self._population_read_key = self._population_observation_key()
            logger.info(f"[人口确认] 当前={population.current}/{population.capacity} "
                        f"来源={population.evidence}")
            if population.current == 0:
                if self._population_conflict():
                    logger.warning("[人口确认] 零人口与已确认角色冲突，保留场地证据等待补读")
                    return
                index, box = self.operator.locate_any(
                    [CWIMG.PREPARATION_STAGE, CWIMG.BATTLE], trace=False)
                if box is not None and index in (0, 1):
                    # The live, stable complete numerator proves the whole field
                    # is empty; an isolated capacity digit never provides this.
                    for area in ("on_field", "off_field"):
                        for i in range(len(self._observations[area])):
                            self._observation_revision += 1
                            self._set_observation(area, SlotObservation(
                                i, SlotState.EMPTY, occupied=False, evidence="zero_population",
                                revision=self._observation_revision))
                    self._reconcile_placed()
                    logger.info("[人口确认] 已确认空战斗区，允许放置起手角色")
            self._population_read_key = self._population_observation_key()
            return
        logger.debug(f"[人口确认] 完整读数未确认：{population.reason}，保留场地未知状态")
        # Legacy capacity-only OCR can size the team, never certify empty slots.
        result = self.operator.ocr(from_x=0.505, from_y=0.18, to_x=0.608, to_y=0.27)
        if result:
            try:
                capacity = int(str(result[-1][1]).strip())
                if not 1 <= capacity <= len(self.on_field_area) + len(self.off_field_area):
                    raise ValueError("人口超出棋盘容量")
                self.max_team_size = capacity
                logger.info(f"最大队伍人数已更新为 {self.max_team_size}")
            except ValueError:
                logger.warning(f"无法解析最大队伍人数：{result[-1][1]}")
        self._population_read_key = self._population_observation_key()

    def load_strategy(self, name):
        if not name.strip():
            name = "template"
        path = name if name.endswith(".json") else f"tasks/currency_wars/strategies/{name}.json"
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        main_c, search_level = validate_main_c_config(data, self._lookup_known_character)
        # Validate all mutation inputs before changing the current strategy.
        normalized = {}
        placements = {}
        priorities = {}
        for area, positioning in (("on_field", Positioning.OnField), ("off_field", Positioning.OffField)):
            roster = data.get(area, {})
            if not isinstance(roster, dict):
                raise ValueError(f"攻略 {area} 必须是角色与星级的对象")
            for i, (name, goal) in enumerate(roster.items()):
                char = self._lookup_known_character(name)
                if char is None:
                    logger.warning(f"攻略角色不存在，跳过：{name}")
                    continue
                if type(goal) is not int or goal <= 0:
                    raise ValueError(f"攻略角色 {name} 的目标星级无效")
                target = 3 if goal >= 9 else (2 if goal > 3 else goal)
                normalized[char.name] = max(normalized.get(char.name, 0), target)
                placements[char.name] = placements[char.name] + positioning if char.name in placements else positioning
                priorities[char.name] = max(priorities.get(char.name, 0), 99 - i)
        for key, default in (("min_coins", 40), ("main_c_search_min_coins", 0),
                             ("min_level", 7), ("mid_level", 7)):
            value = data.get(key, default)
            if type(value) is not int or value < 0:
                raise ValueError(f"攻略参数 {key} 无效")
        economy = parse_economy_config(data.get("economy"),
            main_c_search_level=search_level if main_c else None)
        opening_policy = parse_opening_policy_config(data.get("opening_policy"))
        equipment_interval = data.get("equipment_interval_battles")
        if "equipment_interval_battles" in data and (type(equipment_interval) is not int or equipment_interval <= 0):
            raise ValueError("equipment_interval_battles 必须为正整数")
        equipment = parse_equipment_config(data.get("equipment"), self._lookup_known_character)
        if equipment is not None:
            if equipment_interval is not None and equipment_interval != equipment.interval_battles:
                raise ValueError("请在 equipment.interval_battles 中统一配置装备间隔")
            equipment_interval = equipment.interval_battles
        formation = validate_formation_config(data, self._lookup_known_character)
        preparation_budget = validate_preparation_budget(data.get("preparation_budget"))
        health_roi = data.get("health_roi")
        if health_roi is not None and (not isinstance(health_roi, list) or len(health_roi) != 4
                or any(type(v) not in (int, float) or not 0 <= v <= 1 for v in health_roi)
                or health_roi[0] >= health_roi[2] or health_roi[1] >= health_roi[3]):
            raise ValueError("health_roi must be a normalized rectangular region")
        if formation:
            formation_names = {n for stage in formation.stages
                               for n in stage.on_field + stage.off_field}
            role_names = {p.name for providers in formation.roles.values() for p in providers}
            if not formation_names <= normalized.keys() | role_names:
                raise ValueError("阶段阵容角色必须同时定义在攻略购买名单中")
        budget = {"actions": 60, "seconds": 90, "purchases": 60, "refreshes": 60, "experiences": 60}
        overrides = data.get("shopping_budget", {})
        if not isinstance(overrides, dict) or not overrides.keys() <= budget.keys():
            raise ValueError("shopping_budget 必须是有效预算参数对象")
        for key, value in overrides.items():
            if type(value) is not int or value < (1 if key in ("actions", "seconds") else 0) or value > 300:
                raise ValueError(f"shopping_budget.{key} 无效")
            budget[key] = value
        events = data.get("special_events", {})
        if not isinstance(events, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                               for k, v in events.items()):
            raise ValueError("special_events 必须是事件与关键词字符串的对象")
        self.unload_strategy()
        self.formation_config = formation
        self.preparation_budget = preparation_budget
        self._health_roi = tuple(health_roi) if health_roi is not None else None
        self._strategy_fingerprint = hashlib.sha256(json.dumps(data, ensure_ascii=False,
            sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        self.shopping_budget = budget
        self.economy_config = economy
        self.equipment_config = equipment
        self.equipment_interval_battles = equipment_interval
        self._strategy_path = Path(path).resolve()
        self.strategy_characters.update(normalized)
        for name, position in placements.items():
            char = self._lookup_known_character(name)
            char.position = position
            char.priority = priorities[name]
        self.min_coins = data.get("min_coins", 40)
        self.min_level = data.get("min_level", 7)
        self.mid_level = data.get("mid_level", 7)
        self.strategy_code = data.get("share_code", "")
        self.strategy_special_events = data.get("special_events", {})
        self.main_c = main_c
        self.opening_policy_config = opening_policy
        self.main_c_search_level = search_level
        self.main_c_search_min_coins = data.get("main_c_search_min_coins", 0)
        self.main_c_first_fielded_confirmed = False
        self._invalidate_level()
        self._equipment_dirty = True
        logger.info(f"[经济配置] mode={'stages' if economy else 'legacy'} stages={getattr(economy, 'stages', ())} "
                    f"purchase_reserve={getattr(economy, 'purchase_reserve_gold', 0)} "
                    f"all_in_round={getattr(economy, 'all_in_round', None)} equipment={equipment} "
                    f"equipment_interval={equipment_interval} opening_policy={opening_policy}；"
                    "正常购物不限制总秒数，启用阶段表时覆盖旧等级与金币门槛")
        logger.info(f"已加载攻略: {data.get('title', '')}，前期主C: {self.main_c or '未启用'}")

    def unload_strategy(self):
        for char in {id(c): c for c in Characters.characters.values()}.values():
            char.reset()
        self.min_coins, self.min_level, self.mid_level = 40, 7, 7
        self.economy_config = None
        self.opening_policy_config = None
        self._economy_stage_index = None
        self._preparation_round = None
        self._round_read_attempts = 0
        self._all_in_decision = None
        self.equipment_config = None
        self._all_in_budget = None
        self._equipment_others_checked = False
        self.equipment_interval_battles = None
        self.strategy_characters.clear()
        self.strategy_code = ""
        self.strategy_special_events.clear()
        self.formation_config = None
        self._effective_targets = None
        self._formation_plan = ()
        self._formation_plan_stage = None
        self._formation_plan_incomplete = False
        self.preparation_budget = validate_preparation_budget(None)
        self._health_roi = None
        self._strategy_fingerprint = "default"
        self._strategy_path = None
        self._observed_prices.clear()
        self._form_change_pending.clear()
        self._dirty_slots.clear()
        self.main_c = None
        self.main_c_search_level = 5
        self.main_c_search_min_coins = 0
        self.main_c_first_fielded_confirmed = False
        self._purchase_pending_names.clear()
        self._invalidate_level()
        self._equipment_checked.clear()
        self._equipment_attempts.clear()
        self._population_read_key = None
        for area in ("on_field", "off_field"):
            self._observations[area] = [SlotObservation(i, SlotState.UNKNOWN,
                evidence="strategy_changed") for i in range(len(getattr(self, area + "_area")))]
        self._placement_pending = True

    def place_character(self):
        self._begin_preparation()
        conflict = self._population_conflict()
        if conflict:
            logger.warning(f"[布阵保护] 人口证据冲突，等待补读：{conflict}")
            return False
        if self._formation_deadline is None:
            self._formation_deadline = min(self._preparation_deadline,
                time.monotonic() + self.preparation_budget["seconds"])
        if self.formation_config is not None:
            return self._place_stage_formation()
        placed = False

        def deploy(index, preferred_area=None):
            obs = self._observations["in_hand"][index]
            char = self.in_hand_character[index]
            if (obs.state != SlotState.KNOWN or char is None or char.is_locked or char.is_npc
                    or char.is_placed or self._lookup_known_character(char.name) is None):
                return False
            for area, position in (("on_field", Positioning.OnField), ("off_field", Positioning.OffField)):
                if preferred_area is not None and area != preferred_area:
                    continue
                if char.position not in (position, Positioning.OnOffField):
                    continue
                target = getattr(self, area + "_character")
                if self._place_to_target(index, target, "前台" if area == "on_field" else "后台"):
                    self._confirm_main_c_fielded()
                    return True
            return False

        # Prioritize the first main C across both areas before filling with teammates.
        if self.main_c and not self.main_c_first_fielded_confirmed:
            for index, obs in enumerate(self._observations["in_hand"]):
                self._check_stop()
                if obs.state == SlotState.KNOWN and obs.character.name == self.main_c:
                    placed = deploy(index) or placed
                    break
        for area in ("on_field", "off_field"):
            for index in range(len(self.in_hand_character)):
                self._check_stop()
                placed = deploy(index, area) or placed
        self.ensure_on_field_not_empty()
        self._confirm_main_c_fielded()
        return placed

    def place_on_field_character(self, character_in_hand: int) -> bool:
        """将手中的角色放置到前台（前台角色专用，优先占位）"""
        return self._place_to_target(
            character_in_hand,
            target_characters=self.on_field_character,
            area_type="前台"
        )

    def place_off_field_character(self, character_in_hand: int) -> bool:
        """将手中的角色放置到后台（后台角色专用）"""
        return self._place_to_target(
            character_in_hand,
            target_characters=self.off_field_character,
            area_type="后台"
        )

    def ensure_on_field_not_empty(self) -> bool:
        """校验前台角色列表是否为空。

        若前台（on_field_character）全部为空，则从后台（off_field_character）中按顺序取第一个非空角色，
        将其移动到前台第一个位置（索引 0）。

        :return: 若无需处理或移动成功返回 True；若前台为空且后台也无角色可移动则返回 False。
        """
        if any(c is not None for c in self.on_field_character):
            return True

        for off_index, char in enumerate(self.off_field_character):
            if char is None:
                continue
            logger.info(f"前台为空，提升后台角色 {char.name} (off_field[{off_index}]) 到前台 on_field[0]")
            return self.swap_character_between_areas(
                source_area_type='off_field',
                source_index=off_index,
                target_area_type='on_field',
                target_index=0,
            )

        logger.warning("前台为空且后台无角色可提升")
        return False

    def _place_to_target(self, character_in_hand, target_characters, area_type):
        if not 0 <= character_in_hand < len(self.in_hand_character):
            return False
        obs = self._observations["in_hand"][character_in_hand]
        char = self.in_hand_character[character_in_hand]
        if (obs.state != SlotState.KNOWN or char is None or char.is_locked or char.is_npc
                or char.is_placed):
            return False
        area = "on_field" if area_type == "前台" else "off_field"
        first_main = char.name == self.main_c and not self.main_c_first_fielded_confirmed
        if (self.main_c and not self.main_c_first_fielded_confirmed and not first_main
                and self.current_team_size >= self.max_team_size - 1):
            main = self._lookup_known_character(self.main_c)
            allowed_areas = ("on_field", "off_field") if main.position == Positioning.OnOffField else (
                ("on_field",) if main.position == Positioning.OnField else ("off_field",))
            replaceable = any(
                candidate.state == SlotState.KNOWN and not candidate.character.is_locked
                and not candidate.character.is_npc and candidate.character.name != self.main_c
                for main_area in allowed_areas for candidate in self._observations[main_area])
            # Keep one population slot if filling the other area would strand the first main C.
            if area not in allowed_areas and not replaceable:
                return False

        if self.current_team_size < self.max_team_size:
            for i, target in enumerate(target_characters):
                if target is None and self._observations[area][i].state == SlotState.EMPTY:
                    return self.swap_character_between_areas("in_hand", character_in_hand, area, i)
        first_main = char.name == self.main_c and not self.main_c_first_fielded_confirmed
        allowed = [
            (i, target) for i, target in enumerate(target_characters)
            if target is not None and self._observations[area][i].state == SlotState.KNOWN
            and not target.is_locked and not target.is_npc and target.name != char.name
            and (first_main or (target.priority or 0) < (char.priority or 0))
        ]
        if not allowed:
            return False
        target_index, _ = min(allowed, key=lambda pair: pair[1].priority or 0)
        return self.swap_character_between_areas("in_hand", character_in_hand, area, target_index)

    def swap_character_between_areas(self, source_area_type, source_index,
                                     target_area_type, target_index):
        self._last_move_result = MoveResult(MoveStatus.REJECTED, "invalid_move",
            (source_area_type, source_index), (target_area_type, target_index))
        conflict = self._population_conflict()
        if conflict:
            self._last_move_result = replace(self._last_move_result, reason=conflict)
            return False
        if self._preparation_deadline is not None:
            if self._preparation_attempts >= self.preparation_budget["actions"]:
                self._last_move_result = replace(self._last_move_result, reason="preparation_action_budget")
                return False
            if time.monotonic() >= min(self._preparation_deadline,
                    self._formation_deadline or self._preparation_deadline):
                self._last_move_result = replace(self._last_move_result, reason="preparation_time_budget")
                return False
            self._preparation_attempts += 1
        valid = ("on_field", "off_field", "in_hand")
        if source_area_type not in valid or target_area_type not in valid:
            return False
        source_chars = getattr(self, source_area_type + "_character")
        target_chars = getattr(self, target_area_type + "_character")
        if not (0 <= source_index < len(source_chars) and 0 <= target_index < len(target_chars)):
            return False
        source_obs = self._observations[source_area_type][source_index]
        target_obs = self._observations[target_area_type][target_index]
        source_char = source_chars[source_index]
        target_char = target_chars[target_index]
        if "off_field" in (source_area_type, target_area_type) and not self._layout_valid:
            self._last_move_result = replace(self._last_move_result, reason="backend_layout_not_confirmed")
            return False
        if (source_obs.state != SlotState.KNOWN or source_char is None
                or source_char.is_locked or source_char.is_npc
                or target_obs.state in (SlotState.UNKNOWN, SlotState.LOCKED)
                or (target_char is not None and (target_char.is_locked or target_char.is_npc))):
            return False
        if self._pending_move is not None or observation_identity(source_obs) is None or observation_identity(target_obs) is None:
            return False
        if any(key[:3] == (source_area_type, source_index, target_area_type)
               and self._fielding_rejection_matches(key) for key in self._fielding_rejections):
            self._last_move_result = replace(self._last_move_result, reason="game_cannot_be_fielded")
            return False
        if source_area_type == "in_hand" and target_area_type != "in_hand" and target_obs.state == SlotState.EMPTY:
            possible_occupied = sum(o.state not in (SlotState.EMPTY, SlotState.LOCKED)
                                   or observation_identity(o) is None
                for area in ("on_field", "off_field") for o in self._observations[area])
            if possible_occupied >= self.max_team_size:
                self._last_move_result = replace(self._last_move_result, reason="population_capacity_guard")
                return False
        # Central guard also covers fallback placement and priority sorting.
        predicted = {area: list(slots) for area, slots in self._observations.items()}
        predicted[source_area_type][source_index] = replace(target_obs, slot_index=source_index)
        predicted[target_area_type][target_index] = replace(source_obs, slot_index=target_index)
        stage = self._formation_stage()
        decision = formation_change_allowed(self.formation_config, self._observations, predicted, stage=stage)
        if not decision.allowed:
            self._last_move_result = replace(self._last_move_result, reason=decision.reason)
            logger.info(f"拒绝阵容替换：{decision.reason}")
            return False
        self._check_stop()
        source = getattr(self, source_area_type + "_area")[source_index]
        target = getattr(self, target_area_type + "_area")[target_index]
        self._population_current = None
        self._population_read_key = None
        self._equipment_dirty = True
        self._invalidate_level()
        self._placement_pending = True
        self._pending_move = {
            "source": (source_area_type, source_index), "target": (target_area_type, target_index),
            "source_before": source_obs, "target_before": target_obs,
            "layout": self._layout_revision, "positions": (source, target),
        }
        self._record_checkpoint(phase="move_pending", pending_actions=[
            f"swap:{source_area_type}:{source_index}:{source_char.name}->{target_area_type}:{target_index}"])
        # The initial empty baseline is invalid once a drag targets a slot.
        # Retain historical occupants only as protected, unconfirmed values.
        self._set_observation(source_area_type, SlotObservation(
            source_index, SlotState.UNKNOWN, evidence="pending_drag"))
        self._set_observation(target_area_type, SlotObservation(
            target_index, SlotState.UNKNOWN, evidence="pending_drag"))
        self._dirty_slots.update({(source_area_type, source_index), (target_area_type, target_index)})
        dragged = self._safe_drag_to(*source, *target, trace=False)
        self.operator.sleep(0.5)
        fielding_rejected = bool(self.operator.locate(
            CWIMG.CANNOT_BE_FIELDED, from_x=0.25, from_y=0.25, to_x=0.75, to_y=0.75))
        self._pending_move["fielding_rejected"] = bool(dragged and fielding_rejected)
        if fielding_rejected:
            self.operator.click_point(0.5, 0.5, after_sleep=1)
        if source_area_type == "in_hand" and target_area_type != "in_hand":
            if dragged and not fielding_rejected:
                self.handle_special_event()
        # Confirm both endpoints, including the stars of a unit returned to the bench.
        # Reuse these open panels instead of forcing a later full bench scan.
        verify_same_name_stars = (observation_identity(source_obs) == observation_identity(target_obs)
                                  and source_obs.stars != target_obs.stars)
        target_after = self._observe_slot(target_area_type, target_index,
                                          count_stars=(verify_same_name_stars or target_area_type != "in_hand"
                                                       or source_area_type != "in_hand"),
                                          use_backup_ocr=target_area_type == "off_field")
        self._set_observation(target_area_type, target_after)
        source_after = self._observe_slot(source_area_type, source_index,
                                          count_stars=(verify_same_name_stars or source_area_type != "in_hand"
                                                       or target_area_type != "in_hand"),
                                          use_backup_ocr=source_area_type == "off_field")
        self._set_observation(source_area_type, source_after)
        result = classify_move(source_obs, target_obs, source_after, target_after)
        result = self._confirm_fielding_rejection(self._pending_move, result)
        self._last_move_result = replace(result, source=(source_area_type, source_index),
                                        target=(target_area_type, target_index))
        if (target_after.state == SlotState.KNOWN and target_after.character.name == source_char.name
                and source_after.state == SlotState.UNKNOWN):
            # Historical identity may protect occupants, but never certify the move.
            source_chars[source_index] = target_char
        self._reconcile_placed()
        success = bool(result)
        self._placement_pending = result.status == MoveStatus.INDETERMINATE
        if not self._placement_pending:
            self._pending_move = None
            self._record_checkpoint(phase="preparation", pending_actions=[])
        if success:
            if self._preparation_deadline is not None:
                self._preparation_moves += 1
            self._confirm_main_c_fielded()
            self._reconcile_purchase_pending()
            self._record_checkpoint(phase="preparation", pending_actions=[])
        logger.info(f"[换人确认] 结果={result.status} 原因={result.reason} "
                    f"来源={source_area_type}[{source_index}]:{observation_identity(source_after)} "
                    f"目标={target_area_type}[{target_index}]:{observation_identity(target_after)} "
                    f"布局版本={self._layout_revision} 观察版本={self._snapshot_revision}")
        if not success:
            self._vision.capture_sample("formation_move_" + result.status.value,
                {"evidence": f"source={source_area_type}:{source_index};target={target_area_type}:{target_index};"
                             f"layout={self._layout_revision};reason={result.reason}"}, critical=True)
        return success

    def sort_characters_by_priority(self, area_type: str) -> bool:
        """
        对指定区域的角色按优先级进行排序，高优先级角色靠前

        :param area_type: 区域类型 ('on_field', 'off_field')
        :return: 排序操作是否成功
        """
        # 验证区域类型
        if area_type not in ['on_field', 'off_field']:
            logger.error(f"无效的区域类型: {area_type}，只支持 'on_field' 或 'off_field'")
            return False

        # 获取区域信息
        if area_type == 'on_field':
            characters = self.on_field_character
            area_name = "前台"
        else:  # off_field
            characters = self.off_field_character
            area_name = "后台"

        if any(obs.state == SlotState.UNKNOWN for obs in self._observations[area_type]):
            return False
        logger.info(f"开始对{area_name}区域角色按优先级排序")

        # 创建包含角色、索引和优先级的列表
        char_info_list = []
        for i, char in enumerate(characters):
            if char is not None:
                char_info_list.append({
                    'character': char,
                    'index': i,
                    'priority': char.priority
                })
            else:
                char_info_list.append({
                    'character': None,
                    'index': i,
                    'priority': -1  # 空位置优先级设为-1，排在最后
                })

        # 按优先级降序排序（高优先级在前）
        sorted_char_info = sorted(char_info_list, key=lambda x: x['priority'], reverse=True)

        # 执行排序交换
        success_count = 0
        for target_pos, target_info in enumerate(sorted_char_info):
            current_pos = target_info['index']

            # 如果已经在正确位置，跳过
            if current_pos == target_pos:
                continue

            # 找到目标位置当前的角色信息
            target_current_info: dict[str, Any] | None = None
            for info in char_info_list:
                if info['index'] == target_pos:
                    target_current_info = info
                    break

            # 如果目标位置为空或优先级较低，执行交换
            if (target_current_info is None or
                    target_current_info['character'] is None or
                    target_current_info['priority'] <= target_info['priority']):

                # 执行交换
                if self.swap_character_between_areas(
                        source_area_type=area_type,
                        source_index=current_pos,
                        target_area_type=area_type,
                        target_index=target_pos
                ):
                    success_count += 1
                    logger.info(f"{area_name}区域位置交换: [{current_pos}] <-> [{target_pos}]")

                    # 更新char_info_list中的索引信息
                    for info in char_info_list:
                        if info['index'] == current_pos:
                            info['index'] = target_pos
                        elif info['index'] == target_pos:
                            info['index'] = current_pos

        logger.info(f"{area_name}区域优先级排序完成，成功交换 {success_count} 次")
        return success_count > 0

    def sort_all_areas_by_priority(self) -> bool:
        """
        对所有区域（前台和后台）的角色按优先级进行排序

        :return: 排序操作是否成功
        """
        logger.info("开始对所有区域进行优先级排序")

        field_success = self.sort_characters_by_priority('on_field')
        offfield_success = self.sort_characters_by_priority('off_field')

        overall_success = field_success or offfield_success

        if overall_success:
            logger.info("所有区域优先级排序完成")
        else:
            logger.info("无需进行排序操作")

        return overall_success

    def _release_pointer_unconditionally(self):
        # Emergency release bypasses stop-aware operator wrappers, never stop itself.
        try:
            if self.operator.type == "Local":
                import pyautogui
                pyautogui.mouseUp(button="left")
            elif getattr(self.operator, "driver", None) is not None:
                from selenium.webdriver.common.actions.action_builder import ActionBuilder
                actions = ActionBuilder(self.operator.driver)
                actions.pointer_action.pointer_up()
                actions.perform()
            else:
                return False
            return True
        except Exception as error:
            logger.warning(f"中断拖动后释放鼠标失败：{error}")
            return False

    def _safe_drag_to(self, *args, **kwargs):
        self._check_stop()
        completed = False
        try:
            completed = bool(self.operator.drag_to(*args, **kwargs))
            self._check_stop()
            return completed
        finally:
            event = getattr(self.operator, "stop_event", None)
            if not completed or (event is not None and event.is_set()):
                self._release_pointer_unconditionally()

    def _reconcile_purchase_pending(self):
        if self._bench_dirty:
            return  # Unobserved purchase landing/merge slots are not old EMPTY.
        observations = [o for area in self._observations for o in self._observations[area]]
        complete = all(observation_identity(o) is not None for o in observations)
        for name in list(self._purchase_pending_names):
            matches = [o for o in observations if o.state == SlotState.KNOWN
                       and o.character is not None and o.character.name == name]
            if not matches:
                if complete:
                    self._purchase_pending_names.discard(name)
            elif (all(o.stars is not None and observation_identity(o) is not None for o in matches)
                  and (name != self.main_c or self.main_c_first_fielded_confirmed)):
                self._purchase_pending_names.discard(name)

    def _invalidate_character_evidence(self, name, reason, *, level_changed=True):
        self._snapshot_revision += 1
        char = self._lookup_known_character(name)
        if char is not None:
            char.stars = 0
        for area, observations in self._observations.items():
            for index, obs in enumerate(observations):
                if obs.character is not None and obs.character.name == name:
                    # Identity/occupancy survives a form event; star evidence does not.
                    observations[index] = replace(obs, stars=None)
                    self._dirty_slots.add((area, index))
        self._equipment_dirty = True
        self._equipment_checked.pop(name, None)
        if level_changed:
            self._invalidate_level()
        logger.info(f"角色星级证据失效：{name}，原因={reason}")

    def _refresh_dirty_field(self):
        pending = [(area, index) for area, index in sorted(self._dirty_slots.copy())
                   if area != "in_hand" and index < len(self._observations[area])]
        needs_input = any(area != "off_field" or self._layout_valid for area, _ in pending)
        if needs_input and not self._set_shop_open(False):
            self._fail_battle("field_scan_shop_not_closed")
        for area, index in pending:
            obs = self._observe_slot(area, index, count_stars=True,
                                     use_backup_ocr=area == "off_field")
            self._set_observation(area, obs)
        self._reconcile_placed()
        self._confirm_main_c_fielded()
        self._reconcile_purchase_pending()

    def _place_stage_formation(self):
        placed = False
        if self._placement_pending and self._pending_move is None and all(
                observation_identity(o) is not None for area in ("on_field", "off_field")
                for o in self._observations[area]):
            self._placement_pending = False
        self._begin_preparation()
        if self._formation_deadline is None:
            self._formation_deadline = min(self._preparation_deadline,
                time.monotonic() + self.preparation_budget["seconds"])
        while self._preparation_attempts < self.preparation_budget["actions"]:
            self._check_stop()
            if self._placement_pending or time.monotonic() >= self._formation_deadline:
                break
            stage = self._formation_stage()
            if stage is None:
                return placed
            for area, position in (("on_field", Positioning.OnField), ("off_field", Positioning.OffField)):
                for name in getattr(stage, area):
                    self._lookup_known_character(name).position = position
            preferred = (self.main_c,) if self.main_c and not self.main_c_first_fielded_confirmed else ()
            if self._formation_plan and (stage != self._formation_plan_stage or not validate_formation_sequence(
                    self.formation_config, stage, self._observations, self.max_team_size,
                    self._formation_plan, preferred, excluded_moves=self._excluded_moves())):
                self._formation_plan = ()
                logger.warning("[布阵计划] 目标或实际端点已变化，停止旧计划并重新规划")
            if not self._formation_plan:
                self._formation_plan = plan_formation_sequence(self.formation_config, stage, self._observations,
                    self.max_team_size, preferred, excluded_moves=self._excluded_moves())
                self._formation_plan_stage = stage
            if not self._formation_plan:
                # A successfully re-established target closes an interrupted
                # intermediate plan; uncertainty or wrong regions keep it blocked.
                if all(any(o.state == SlotState.KNOWN and observation_identity(o) is not None
                           and o.character.name == name for o in self._observations[area])
                       for area in ("on_field", "off_field") for name in getattr(stage, area)):
                    self._formation_plan_incomplete = False
                logger.info(f"[布阵] 阶段={stage.name} 无更多安全移动，排除候选={len(self._excluded_moves())}")
                break
            move = self._formation_plan[0]
            key = self._move_key(move.source_area, move.source_index, move.target_area, move.target_index)
            snapshot, layout = self._snapshot_revision, self._layout_revision
            logger.info(f"[布阵] 阶段={stage.name} 原因={move.reason} "
                f"{move.source_area}[{move.source_index}]->{move.target_area}[{move.target_index}] "
                f"观察版本={snapshot} 布局版本={layout}")
            self._check_stop()
            if (snapshot, layout) != (self._snapshot_revision, self._layout_revision):
                continue
            attempts_before = self._preparation_attempts
            changed = self.swap_character_between_areas(move.source_area, move.source_index,
                move.target_area, move.target_index)
            if self._preparation_attempts == attempts_before:
                self._preparation_attempts += 1
            if changed:
                placed = True
                self._move_failures.pop(key, None)
                self._formation_plan = self._formation_plan[1:]
                self._formation_plan_incomplete = bool(self._formation_plan)
            elif self._last_move_result.status == MoveStatus.INDETERMINATE or self._placement_pending:
                break
            else:
                self._formation_plan = ()
                increment = (1 if self._last_move_result.status == MoveStatus.CONFIRMED_UNCHANGED
                    else self.preparation_budget["move_retries"] + 1)
                self._move_failures[key] = self._move_failures.get(key, 0) + increment
        self._confirm_main_c_fielded()
        return placed

    def _report_round(self, number, started, phase_before, sale):
        phases = {key: round(value - phase_before.get(key, 0), 2)
                  for key, value in self.phase_seconds.items() if value > phase_before.get(key, 0)}
        counts = {area: {state.value: sum(o.state == state for o in observations) for state in SlotState}
                  for area, observations in self._observations.items()}
        roster = {area: [(o.character.name, o.stars) for o in self._observations[area]
                         if o.state == SlotState.KNOWN] for area in ("on_field", "off_field")}
        level = self._last_level_read.level if self._last_level_read else None
        stage = self._formation_stage()
        logger.info(f"货币战争回合={number} 总耗时={time.monotonic()-started:.2f}s "
                    f"阶段={stage.name if stage else '固定阵容'} 主C已上阵={self.main_c_first_fielded_confirmed} "
                    f"最近读取等级={level} 最近读取金币={self._last_coins_read} 血量={self._last_health_read.current if self._last_health_read else None} 本场结果={self._last_battle_outcome} "
                    f"场上名称与星级={roster} 羁绊={confirmed_trait_counts(self.formation_config, self._observations)} "
                    f"槽位={counts} 卖出={sale.confirmed} 商店={self._last_shopping_result} 分段={phases}")

    def _report_runtime_identity(self):
        # Disk hashes alone cannot identify a class cached by a running app.
        logger.info(f"货币战争内存流程版本={self.FLOW_REVISION} "
                    f"阶段等待秒数：页面={self.PAGE_LOCATE_TIMEOUT} "
                    f"入局={self.ENTRY_TRANSITION_TIMEOUT} 关卡={self.STAGE_TRANSITION_TIMEOUT} "
                    f"出战按钮={self.BATTLE_BUTTON_TIMEOUT} 准备宽限={self.PREPARATION_GRACE_SECONDS} "
                    f"结算={self.REWARD_TRANSITION_TIMEOUT} 事件={self.EVENT_TRANSITION_TIMEOUT} "
                    f"稳定={self.STAGE_SETTLE_SECONDS} 战斗={self.BATTLE_TIMEOUT}")
        paths = [Path(__file__).resolve()]
        for name in ("logic", "formation", "vision", "characters", "preparation", "layout", "session", "economy", "shop_overlay", "policy", "equipment_policy", "shopping_batch"):
            module = sys.modules.get("tasks.currency_wars." + name)
            location = getattr(module, "__file__", None)
            if location:
                paths.append(Path(location).resolve())
            else:
                logger.warning(f"无法核验已导入模块路径：tasks.currency_wars.{name}")
        if self._strategy_path:
            paths.append(self._strategy_path)
        for path in paths:
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                logger.info(f"货币战争运行文件={path} SHA256={digest}")
            except OSError as error:
                logger.warning(f"无法核验运行文件 {path}: {error}")
        logger.info(f"货币战争运行参数：min_coins={self.min_coins} min_level={self.min_level} "
                    f"mid_level={self.mid_level} main_c={self.main_c} "
                    f"search_level={self.main_c_search_level} "
                    f"main_c_search_min_coins={self.main_c_search_min_coins} "
                    f"refresh_cost={self.SHOP_REFRESH_COST} xp_cost={self.SHOP_EXPERIENCE_COST} "
                    f"economy={self.economy_config} equipment_interval={self.equipment_interval_battles} "
                    f"budgets={self.shopping_budget} shopping_total_seconds=unlimited")
