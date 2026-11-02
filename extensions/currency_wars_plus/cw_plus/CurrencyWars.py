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
from .characters import Character, Characters, Positioning
from tasks.img import IMG, DUIMG
from .images import CWIMG
from .game_input import adapt_game_input
from .unicode_templates import load_template, load_match_template, template_cache_key, locate_first
from .paths import CALIBRATION_ROOT, RESOURCE_ROOT, default_data_dir, resolve_strategy_path
from .logic import (
    SlotState, SlotObservation, ShopState, ActionResult, SellResult, ShoppingResult,
    parse_character_name, scan_store_cards, validate_main_c_config,
    parse_shop_level, evaluate_purchase, ShopObservation,
)

from .formation import (
    validate_formation_config, select_formation_stage, formation_change_allowed,
    plan_formation_move, confirmed_trait_counts, stage_upgrade_allowed,
    UNRELIABLE_EVIDENCE,
    evaluate_role_requirements, role_purchase_targets, role_protected_names,
    resolve_effective_targets, plan_formation_sequence, validate_formation_sequence,
    _placement_areas,
)
from .vision import (
    CurrencyWarsVision, image_distance, RESULT_HEALTH_ROI, FINAL_HEALTH_ROI,
    TERMINAL_STATES, TERMINAL_STATE_ORDER,
)
from .preparation import (
    MoveStatus, MoveResult, PreparationResult, Readiness, classify_move,
    observation_identity, validate_preparation_budget, recovery_signature,
)
from .layout import (LayoutObservation, validate_backend_layout,
    backend_rectangle_candidates, revalidate_backend_layout, layout_diagnostics)
from .bench_full import FullBenchObservation, observe_full_bench
from .session import SessionStore
from .runtime_rebuild import (RuntimeFlowFailure, capture_runtime_recovery,
                             restore_runtime_recovery)
from .shop_overlay import (
    SHOP_PROBABILITY_TITLE_ROI, detect_shop_probability_overlay, observe_shop_probability_panel,
)
from .equipment_choice import (
    EQUIPMENT_CHOICE_TITLE_ROI, EquipmentChoiceObservation, equipment_choice_geometry,
    detect_equipment_choice, same_equipment_choice,
)
from .economy import (
    parse_economy_config, select_economy_stage, next_economy_action, can_afford_purchase,
    evaluate_all_in_policy, next_final_round_action,
)
from .policy import (
    parse_preparation_round, parse_experience_progress, parse_experience_cap,
    parse_opening_policy_config,
)
from .equipment_policy import parse_equipment_config, allowed_order
from .shopping_batch import ShoppingBatch
from .shop_stall_recovery import (purchase_noop_evidence, prepare_stalled_shop_rebuild,
    reliable_balance, shop_signature, capture_purchase_noop_state, resolve_page_purchase_noop)
from .reward_fast import (parse_reward_fast_rounds, is_reward_fast_round,
    reward_fast_cached_demand, RewardPurchaseEvidence)
from .coins import (
    coin_roi_evidence, coin_recovery_roi, select_coin_read, choose_coin_read, validate_coin_change,
    select_action_cost, EXPERIENCE_COST_ROI, REFRESH_COST_ROI, ground_coin_rows,
)


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
    # 这些限制适用于页面切换，不适用于购物或布阵动作。
    FLOW_REVISION = "plusv1"
    PAGE_LOCATE_TIMEOUT = 45
    ENTRY_TRANSITION_TIMEOUT = 30
    STAGE_TRANSITION_TIMEOUT = 60
    BATTLE_BUTTON_TIMEOUT = 15
    PREPARATION_GRACE_SECONDS = 45
    PREPARATION_CONFIRM_SECONDS = 3
    REWARD_TRANSITION_TIMEOUT = 120
    EVENT_TRANSITION_TIMEOUT = 15
    SHOP_STATE_TIMEOUT = 30
    SHOP_CLOSE_ATTEMPTS = 3
    STAGE_SETTLE_SECONDS = 3
    BATTLE_TIMEOUT = 600
    BATTLE_MAX_WAIT_SECONDS = 3600  # 已确认战斗可延长等待；同一战斗及恢复共享总上限。
    FLOW_RECOVERY_ATTEMPTS = 2
    FLOW_RECOVERY_STEPS = 12
    FLOW_RECOVERY_SECONDS = 90
    AUTO_RESUME_DELAYS = (10, 30, 60)  # 同一处无进展故障的额外续跑轮次。
    STARTUP_RECOVERY_ATTEMPTS = 5  # 两次立即尝试，加三次延迟续试。
    STARTUP_RECOVERY_SECONDS = 300  # 同一启动的准备页认证共享无进展上限。
    DIFFICULTY_SELECTION_TIMEOUT = 60
    DIFFICULTY_MAX_CLICKS = 40
    STRATEGY_APPLIED_IMAGE = str(RESOURCE_ROOT / "cancel_apply.png")
    SHOP_REFRESH_COST = 2  # 真实日志中的连续余额 51 → 49 → 47 已确认此费用。
    FINAL_ROUND_REFRESH_LIMIT = 80  # 包含免费刷新和同回合恢复。

    SHOP_EXPERIENCE_COST = 4  # 这是本玩法单次 F 输入的价格，并非整级升级价格。

    def __init__(self, operator, runtimes, *, data_dir=None):
        super().__init__(adapt_game_input(operator))
        # 扩展存档和诊断使用独立目录，避免与原版任务互相覆盖。
        self._data_dir = Path(data_dir) if data_dir is not None else default_data_dir()
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
        self._startup_observation_retryable = False
        self._observation_sample_times = {}
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
        self.main_c_search_purchase_reserve_gold = 0
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
        self._bench_full_failure_pending = False
        self._bench_full_sale_receipt = None
        self._equipment_resource_revision = 0
        self._equipment_attempts = {}
        self._equipment_choice_pending = None
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
        self._formation_successor_prefix_pending = False
        self.economy_config = None
        self.opening_policy_config = None
        self.reward_fast_rounds = ()
        self._reward_fast_active = False
        self._reward_fast_page_ledger = None
        self._economy_stage_index = None
        self._economy_evidence_recheck_attempted = False
        self._economy_level_rechecked = False
        self._preparation_round = None
        self._round_read_attempts = 0
        self._all_in_decision = None
        self._all_in_budget = None
        self._confirmed_battle_count = 0
        self._confirmed_battle_lower_bound = 0
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
        self._selection_event_pending = None
        self._runtime_node_pending = None
        self._invest_simple_equipment_pending = False
        self._last_shopping_result = None
        self._last_level_read = None
        self._last_coins_read = None
        self._coin_shop_open = None
        self._last_coin_observation = None
        self._coin_action_costs = {}
        self._experience_before = None
        self._purchase_before_copies = {}
        self.preparation_budget = validate_preparation_budget(None)
        self._snapshot_revision = 0
        self._layout_revision = 0
        self._layout_valid = False
        self._confirmed_layout_positions = ()
        self._backend_support_slots = {}
        self._backend_unknown_slots = set()
        self._backend_ordinary_slots = ()
        self._backend_identity_confirmed = False
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
        # 只接纳真实完整观测；缓存复用和逻辑赋值不能延长有效期。
        self._slot_evidence = {}
        self._backend_layout_observed_at = None
        self._experience_input_revision = 0
        self._bench_observed_at = None
        self._bench_dirty = True
        self._population_current = None
        self._population_read_key = None
        self._sale_population_retry_used = False
        self._population_auto_retries = 0
        self._population_next_retry_at = 0.0
        self._last_health_read = None
        self._health_read_attempts = 0
        self._last_battle_outcome = "unknown"
        self._cycle_number = 0
        self._session_store = None
        self._session_context_tracking = False
        self._checkpoint_write_failed = False
        self._preparation_id = None
        self._runtime_flow_failure = None
        self._runtime_retired = False
        self._runtime_rebuild_active = False
        self._runtime_game_index = 0
        self._flow_recovery_attempts = 0
        self._strategy_fingerprint = "default"
        self._health_roi = None
        self._empty_roster_needs_shop = False
        self._vision = CurrencyWarsVision(
            operator, CALIBRATION_ROOT / "profile.json",
            self._data_dir / "diagnostics", stop_check=self._check_stop)
        self._vision.layout_api = (LayoutObservation, backend_rectangle_candidates,
            layout_diagnostics, revalidate_backend_layout, validate_backend_layout)

    def _check_stop(self):
        if getattr(self, "_runtime_retired", False):
            raise ThreadStoppedError("旧货币战争任务已完成串行交接")
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
        self._session_context_tracking = False
        if self._session_store is None:
            self._session_store = SessionStore(self._data_dir / "state" / "current_run.json")
        fingerprint = self._strategy_fingerprint
        if len(fingerprint) != 64:
            fingerprint = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        current_round, level = None, None
        if self.is_continue:
            # 先读取现场，再恢复历史；这些读数不能写回待核验的旧会话。
            self._preparation_round = None
            self._round_read_attempts = 0
            self._level_cache = None
            context = {}
            for label, reader in (("round", self._read_preparation_round), ("level", self.get_level)):
                try:
                    if label == "level" and (context["round"] is None or not self._set_shop_open(True)):
                        context[label] = None
                    else:
                        # 等级ROI属于展开商店，不能拿收起商店或战斗页的数字核验。
                        context[label] = reader()
                except (ThreadStoppedError, InterruptedError):
                    raise
                except Exception as error:
                    self._check_stop()
                    context[label] = None
                    logger.warning(f"[续跑恢复] 无法核验{label}：{type(error).__name__}；不沿用旧历史")
            self._check_stop()
            current_round, level = context["round"], context["level"]
            self._preparation_round, self._level_cache = current_round, level
        recovery = self._session_store.begin(fingerprint, resume=self.is_continue,
            verify_context=True, session_mode="overclock" if self.is_overclock else "standard",
            observed_round=current_round, observed_level=level)
        checkpoint = recovery.checkpoint
        self._cycle_number = checkpoint.completed_cycles
        self._confirmed_battle_count = checkpoint.confirmed_battle_count
        self._confirmed_battle_lower_bound = checkpoint.confirmed_battle_lower_bound
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
                    f"confirmed_battle_lower_bound={checkpoint.confirmed_battle_lower_bound} "
                    f"battle_count_unknown={checkpoint.confirmed_battle_count is None} "
                    f"economy_stage={self._economy_stage_index} equipment_since_check={self._equipment_battles_since_check}；现场状态重新观察")
        if not recovery.persisted:
            self._checkpoint_write_failed = True
            logger.warning(f"[续跑恢复] 检查点写入失败：{self._session_store.last_error}")
        self._session_context_tracking = True
        self._record_checkpoint(phase="recovering" if self.is_continue else "preparation")

    def _record_checkpoint(self, **changes):
        if self._session_store is None:
            return True
        changes.setdefault("completed_cycles", self._cycle_number)
        if self._session_context_tracking:
            if self._preparation_round is not None:
                changes.setdefault("observed_round", self._preparation_round)
            if self._level_cache is not None:
                changes.setdefault("observed_level", self._level_cache)
        result = self._session_store.record(**changes)
        if not result:
            self._checkpoint_write_failed = True
            logger.warning(f"[续跑恢复] 无法保存检查点：{self._session_store.last_error}")
        return result

    def _clear_transaction_evidence(self):
        """新局或新准备阶段开始时，统一清理上一阶段的消费观测。"""
        self._coin_action_costs.clear()
        self._experience_before = None
        self._purchase_before_copies.clear()
        self._last_coins_read = None
        self._last_coin_observation = None

    # Yukki：同一准备期共享恢复额度，不能靠重入重置。
    def _begin_preparation(self):
        if self._preparation_deadline is not None:
            return
        ledger = getattr(self, "_reward_fast_page_ledger", None) or {}
        if ledger.get("pending") is not None:
            raise RuntimeError("奖励交易未确认，不能重置准备期或购买额度")
        now = time.monotonic()
        # 此标识只在真正创建新准备期时变化。
        # 计时补偿、页面恢复和引擎交接均保留同一标识。
        self._preparation_id = str(uuid.uuid4())
        self._preparation_deadline = now + self.preparation_budget["total_seconds"]
        self._reward_fast_active = False
        self._reward_fast_page_ledger = None
        self._preparation_rewards_collected = False
        self._preparation_departure_confirmed = False
        self._formation_deadline = None
        self._preparation_attempts = self._preparation_recoveries = 0
        self._post_purchase_placement_pending = False
        self._preparation_optimization_finished = False
        self._purchase_finish_used = False
        self._purchase_finish_deadline = None
        self._purchase_finish_attempt_limit = None
        self._purchase_finish_names = set()
        self._preparation_moves = 0
        self._last_preparation_result = None
        self._fielding_rejections.clear()
        self._preparation_assessment_cache = None
        self._equipment_batch_attempts = 0
        self._economy_recovery_attempts = 0
        self._economy_evidence_recheck_attempted = False
        self._economy_level_rechecked = False
        self._preparation_round = None
        self._round_read_attempts = 0
        self._all_in_decision = None
        self._all_in_budget = None
        self._preparation_shop_counts = dict(purchases=0, attempts=0, refreshes=0, experiences=0)
        self._shop_stall_rebuild_used = False
        self._shop_stall_failed_cards = set()
        self._shop_stall_page_signature = None
        self._final_purchase_names = set()
        self._final_finish_context = None
        self._final_finish_active = False
        self._deferred_purchase_cycle = None
        self._population_read_key = None
        self._sale_population_retry_used = False
        self._population_auto_retries = 0
        self._population_next_retry_at = 0.0
        self._clear_transaction_evidence()
        self._record_checkpoint(phase="preparation", pending_actions=[] if self._pending_move is None else None)

    def _effective_formation(self):
        # 同时冻结可变角色属性；部分观测替换
        # 不经过 _set_observation。历史目标仍传入解析器。
        identity_ready = self._backend_identity_ready()
        cache_key = (self.formation_config, self._snapshot_revision, identity_ready, self.main_c,
            recovery_signature(self._observations, layout_revision=self._layout_revision,
                layout_valid=self._layout_valid, capacity=self.max_team_size, population=None))
        if self._effective_targets is not None and self._effective_targets_key == cache_key:
            return self._effective_targets
        self._effective_targets = resolve_effective_targets(self.formation_config,
            self._observations, self.max_team_size, self._effective_targets,
            npc_population_confirmed=identity_ready,
            protected_names=(self.main_c,) if self.main_c else ())
        self._effective_targets_key = cache_key
        if self.formation_config is not None:
            npc_count = self._effective_targets.npc_count
            strategy_capacity = self._effective_targets.strategy_capacity
            stage = self._effective_targets.stage
            fallbacks = tuple(sorted(self._effective_targets.position_fallbacks.items()))
            key = (self.max_team_size, npc_count, strategy_capacity, stage.name if stage else None,
                   fallbacks, identity_ready)
            if key != getattr(self, "_formation_population_log_key", None):
                self._formation_population_log_key = key
                npc_description = str(npc_count) if identity_ready else "未确认"
                logger.info(f"[攻略人口] 游戏总上限={self.max_team_size} NPC占用={npc_description} "
                            f"普通角色名额={strategy_capacity} 阶段={key[3]} 临时站位={dict(fallbacks)}")
        return self._effective_targets

    def _backend_identity_ready(self):
        """完整几何不代表已确定所有支援身份或普通人口名额。"""
        return (self._layout_valid and self._backend_identity_confirmed
                and not self._backend_unknown_slots)

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
        # 移动失败仍属于关键布阵缺口；只有已确认
        # 没有合法移动时，才能使用配置的软性要求。
        if plan_formation_move(self.formation_config, stage, self._observations,
                               self.max_team_size, excluded_moves=self._excluded_moves()) is not None:
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
                self._invalidate_roster_evidence("move_intent_missing")
                self.refresh_character(equip=False)
            return not self._placement_pending
        touches_backend = "off_field" in (pending["source"][0], pending["target"][0])
        if touches_backend and not self._layout_valid:
            # 布局恢复认证坐标前，绝不检查旧后台移动端点。
            # 不能重放拖拽。
            self._placement_pending = True
            return False
        if pending["layout"] != self._layout_revision and touches_backend:
            # 旧后台索引已不再对应拖拽目标。
            # 重建该行及另一受影响区域，
            # 保留可靠且无关的前台观测。
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
            if self._formation_plan and self._formation_plan[0].reason == "protected_successor_prefix":
                self._formation_successor_prefix_pending = False
                self._formation_plan_incomplete = False
        else:
            self._reconcile_purchase_pending()
            if self._formation_plan:
                move = self._formation_plan[0]
                if ((move.source_area, move.source_index), (move.target_area, move.target_index)) == (
                        pending["source"], pending["target"]):
                    self._formation_plan = self._formation_plan[1:]
                    self._formation_plan_incomplete = (bool(self._formation_plan)
                        or self._formation_successor_prefix_pending)
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
        # 星级未读到，不能证明这是不同角色。
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
        return (self._backend_identity_ready(), tuple(sorted(self._backend_unknown_slots)),
                recovery_signature(self._observations,
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
        # 仅恢复缺失证据；可靠备战区角色无须再次执行完整 OCR。
        if reason in {"purchase_recheck_unknown", "purchase_transaction_unconfirmed"}:
            ledger = getattr(self, "_reward_fast_page_ledger", None) or {}
            if ledger.get("pending") is not None:
                # 此收据独立保留仅一次的库存补证额度，普通准备阶段
                # 恢复不能清除该额度记录，也不能重复读取补证。
                return
            names = set(self._purchase_pending_names)
            if names:
                active = self._shopping_active
                self._shopping_active = True  # 收据恢复期间不执行补给或事件输入。
                try:
                    self._recheck_purchased_characters(names)
                finally:
                    self._shopping_active = active
            elif self._bench_dirty:
                self.get_in_hand_area(True)
            return
        if (reason in {"backend_layout_not_confirmed", "backend_identity_not_confirmed"}
                or not self._layout_valid or self._backend_unknown_slots
                or any(observation_identity(obs) is None for obs in self._observations["off_field"])):
            self.refresh_backend_character(equip=False, recover_layout=True)
            if (not self._layout_valid or self._backend_unknown_slots
                    or time.monotonic() >= self._formation_deadline):
                return
            # 后台补读不代表前台和备战席的缺口已经完成。
            # 继续使用原截止时间，不能为这次恢复重开整备额度。
        if reason == "pending_move_unresolved":
            # 下一轮在 _resolve_pending_move 中验证移动端点或变化后的布局。
            # 此处全量扫描会重复该恢复。
            return
        if reason in {"no_confirmed_frontline", "population_capacity_conflict",
                      "population_observation_conflict"}:
            if reason.startswith("population_"):
                self._invalidate_roster_evidence(reason)
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
        self._complete_incremental_field_observation()

    # ssyb：普通出战和超时收尾共用同一组未确认输入门槛。
    def _preparation_hard_blocker(self, *, reward_fast=False, skip_reward=False):
        """预算耗尽前后及采用就绪缓存前，统一检查同一组待确认事实。"""
        ledger = getattr(self, "_reward_fast_page_ledger", None) or {}
        if ledger.get("pending") is not None:
            return "purchase_transaction_unconfirmed"
        if self._placement_pending or self._pending_move is not None:
            return "pending_move_unresolved"
        if self._form_change_pending:
            return "form_change_not_confirmed"
        if (self._runtime_node_pending or self._selection_event_pending is not None
                or self._equipment_choice_pending is not None):
            return "page_action_not_confirmed"
        if skip_reward:
            # 跳过奖励不发起真实战斗，不需要可出战阵容；待确认输入仍须先结清。
            return None
        if not self._layout_valid:
            return "backend_layout_not_confirmed"
        if not self._backend_identity_ready():
            return "backend_identity_not_confirmed"
        if not reward_fast:
            if self._purchase_pending_names or self._bench_dirty:
                return "purchase_recheck_unknown"
            if self._unknown_field_gaps() or any(area in ("on_field", "off_field")
                    for area, _ in self._dirty_slots):
                return "field_observation_not_confirmed"
        return None

    def _assess_preparation(self):
        hard_reason = self._preparation_hard_blocker()
        if hard_reason:
            return PreparationResult(Readiness.BLOCKED, hard_reason, gaps=self._unknown_field_gaps())
        self._complete_incremental_field_observation()
        if getattr(self, "_preparation_optimization_finished", False):
            return self._assess_existing_roster()
        # 这里评估记录的证据，不读取实时屏幕；
        # 在任何决策输入变化前，与战斗门槛和日志共享结果。
        key = (self.formation_config, self._snapshot_revision,
               self._preparation_recovery_signature(), self._formation_plan_incomplete,
               self.main_c, self.main_c_first_fielded_confirmed, self._backend_identity_ready())
        cached = self._preparation_assessment_cache
        if cached is not None and cached[0] == key:
            return cached[1]
        result = self._evaluate_preparation()
        self._preparation_assessment_cache = (key, result)
        return result

    def _evaluate_preparation(self):
        gaps = []
        field_gaps = self._unknown_field_gaps()
        hard_reason = self._preparation_hard_blocker()
        if hard_reason:
            return PreparationResult(Readiness.BLOCKED, hard_reason, gaps=field_gaps)
        if not self._layout_valid:
            return PreparationResult(Readiness.BLOCKED, "backend_layout_not_confirmed", gaps=field_gaps)
        if self._placement_pending or self._pending_move is not None:
            return PreparationResult(Readiness.BLOCKED, "pending_move_unresolved", gaps=field_gaps)
        if not self._backend_identity_ready():
            return PreparationResult(Readiness.BLOCKED, "backend_identity_not_confirmed", gaps=field_gaps)
        if self._formation_plan_incomplete or self._formation_successor_prefix_pending:
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
        moves = plan_formation_sequence(self.formation_config, stage, self._observations,
                                       self.max_team_size, (), excluded_moves=self._excluded_moves())
        if moves:
            return PreparationResult(Readiness.BLOCKED, "safe_improvement_remaining", gaps=tuple(gaps))
        return PreparationResult(Readiness.DEGRADED if gaps else Readiness.READY,
                                 "confirmed_gaps" if gaps else "roster_confirmed", gaps=tuple(gaps))

    @contextmanager
    def _pause_formation_for_auxiliary(self):
        """普通布阵计时排除出售和事件耗时，总计时仍包含这些耗时。

        购物已自行补偿耗时，嵌套辅助调用不得重复补偿同一时间段。
        单次收尾继续使用真实经过时间。
        """
        outer = not getattr(self, "_formation_auxiliary_active", False)
        started = time.monotonic()
        deadline = self._formation_deadline
        credit = (outer and deadline is not None and deadline > started
                  and getattr(self, "_shopping_clock_started", None) is None
                  and not getattr(self, "_purchase_finish_used", False))
        if outer:
            self._formation_auxiliary_active = True
        try:
            yield
        finally:
            if outer:
                self._formation_auxiliary_active = False
            if credit and self._formation_deadline == deadline:
                self._formation_deadline = min(self._preparation_deadline,
                    deadline + time.monotonic() - started)

    def _try_purchase_finish(self):
        now = time.monotonic()
        if (not getattr(self, "_post_purchase_placement_pending", False)
                or getattr(self, "_preparation_optimization_finished", False)
                or getattr(self, "_purchase_finish_used", False)
                or self._preparation_deadline is None or now >= self._preparation_deadline
                or self._formation_deadline is None or now < self._formation_deadline
                or self._preparation_attempts >= self.preparation_budget["actions"]
                or self._placement_pending or self._pending_move is not None):
            return False
        names = {self.main_c} if self._main_c_in_hand() else set()
        for evaluation in self._role_evaluations().values():
            if self._role_placement_unresolved(evaluation):
                names.update(evaluation.bench_candidates)
        if not names:
            return False
        self._purchase_finish_used = True
        self._purchase_finish_names = names
        self._formation_plan = ()
        self._purchase_finish_deadline = min(self._preparation_deadline, now + 60)
        self._formation_deadline = self._purchase_finish_deadline
        self._purchase_finish_attempt_limit = min(self.preparation_budget["actions"],
                                                  self._preparation_attempts + 3)
        logger.warning(f"[购后收尾] 本准备期仅一次，最多60秒/3次移动，目标={sorted(names)}")
        return True

    def _purchase_finish_exhausted(self):
        return (getattr(self, "_purchase_finish_used", False)
                and (time.monotonic() >= self._purchase_finish_deadline
                     or self._preparation_attempts >= self._purchase_finish_attempt_limit))

    def _preparation_budget_spent(self):
        if (not getattr(self, "_preparation_optimization_finished", False)
                and self._preparation_deadline is None and self._formation_deadline is None
                and not getattr(self, "_purchase_finish_used", False)):
            return False
        now = time.monotonic()
        return (getattr(self, "_preparation_optimization_finished", False)
                or (self._preparation_deadline is not None and now >= self._preparation_deadline)
                or (self._formation_deadline is not None and now >= self._formation_deadline)
                or self._purchase_finish_exhausted())

    def _assess_existing_roster(self):
        """优化结束后，仅依据真实的出战安全证据决定是否进入战斗。"""
        gaps = self._unknown_field_gaps()
        dirty = any(area in ("on_field", "off_field") for area, _ in self._dirty_slots)
        desired = self._evaluate_preparation()
        reason = (self._preparation_hard_blocker() or
                  ("formation_plan_incomplete" if self._formation_successor_prefix_pending else
                  "field_observation_not_confirmed" if gaps or dirty else
                  "no_confirmed_frontline" if not self._confirmed_frontline() else
                  self._population_conflict()))
        if reason:
            if desired.state == Readiness.BLOCKED:
                # 超时仍保留当前硬性缺口及角色职责，不让通用的场地未知
                # 描述覆盖最初阻止就绪的原因。
                return replace(desired, reason="preparation_time_budget", blocked_reason=desired.reason)
            return PreparationResult(Readiness.BLOCKED, "preparation_time_budget",
                                     gaps=gaps, blocked_reason=reason)
        return replace(desired, state=Readiness.DEGRADED, reason="budget_finished_continue_battle",
                       blocked_reason="")

    def prepare_for_battle(self):
        """有界的观测、布阵、确认流程，由所有入口共用。"""
        self._begin_preparation()
        if self._health_roi is not None and self._last_preparation_result is None:
            self._last_health_read = self._vision.read_squad_health(self._health_roi)
        if self._formation_deadline is None:
            self._formation_deadline = min(self._preparation_deadline,
                time.monotonic() + self.preparation_budget["seconds"])
        self._try_purchase_finish()
        recovery_baseline = recovery_reason = None
        for _ in range(self.preparation_budget["recoveries"] + 2):
            self._check_stop()
            ledger = getattr(self, "_reward_fast_page_ledger", None) or {}
            if ledger.get("pending") is not None:
                result = PreparationResult(Readiness.BLOCKED, "purchase_transaction_unconfirmed",
                                           gaps=self._unknown_field_gaps())
                break
            self._try_purchase_finish()
            if time.monotonic() >= self._formation_deadline or self._purchase_finish_exhausted():
                self._preparation_optimization_finished = True
                result = self._assess_existing_roster()
                if result.state != Readiness.BLOCKED:
                    logger.info(f"[整备收尾] 预算已用尽，跳过后续运营，使用已确认阵容出战；攻略缺口={result.gaps}")
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
                self._refresh_dirty_field()
                self.update_max_team_size()
                # 拖拽会使人口缓存失效，须在此前检查冲突。
                if not self._population_conflict():
                    self.place_character()
                    if self._population_current is None and time.monotonic() < self._formation_deadline:
                        self.update_max_team_size()
                result = self._assess_preparation()
            if result.state != Readiness.BLOCKED:
                break
            signature = self._preparation_recovery_signature()
            if (recovery_baseline == signature and recovery_reason == result.reason
                    and not (result.reason in {"backend_layout_not_confirmed", "backend_identity_not_confirmed"}
                             and self._preparation_recoveries < self.preparation_budget["recoveries"])):
                result = replace(result, reason="preparation_no_progress", blocked_reason=result.reason)
                logger.warning(f"[整备恢复] 补读后无新增有效证据，原因={result.blocked_reason} 缺口={result.gaps}")
                break
            if (self._preparation_recoveries >= self.preparation_budget["recoveries"]
                    or time.monotonic() >= self._formation_deadline):
                if self._try_purchase_finish():
                    continue
                if time.monotonic() >= self._formation_deadline:
                    result = replace(result, reason="preparation_time_budget", blocked_reason=result.reason)
                break
            self._preparation_recoveries += 1
            recovery_baseline, recovery_reason = signature, result.reason
            logger.info(f"[整备恢复] 第{self._preparation_recoveries}次补读，原因={result.reason} 缺口={result.gaps}")
            self._recover_preparation_observations(result.reason)
        if self._preparation_budget_spent():
            self._preparation_optimization_finished = True
            result = self._assess_existing_roster()
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
        if screen.state in {"result_ready", "result_animation"}:
            self._finish_result_observation(screen)

    def _finish_result_observation(self, screen=None, *, template=False, context=False, departed=False):
        """离开本场结算前补读血量；胜负与页面身份分别认证。"""
        self._check_stop()
        if departed:
            if self._last_health_read is None or self._last_health_read.current is None:
                self._result_health_status = {"state": "failed" if self._health_read_attempts else "skipped",
                    "reason": (self._last_health_read.reason if self._last_health_read is not None
                        else "page_departed_before_health"), "page_departed": True,
                    "attempts": self._health_read_attempts}
                logger.info("[结算血量] 页面已交接，保留未知；不在后续页面读取旧ROI")
            return
        ocr_result = (getattr(screen, "state", None) in {"result_ready", "result_animation"}
            and getattr(screen, "outcome", "unknown") in {"success", "failure"})
        if not (ocr_result or template and context):
            self._result_health_status = {"state": "not_attempted", "reason": "result_page_not_authenticated",
                "attempts": self._health_read_attempts, "page_state": getattr(screen, "state", "unknown"),
                "result_text": getattr(screen, "raw_text", "")[:480]}
            logger.debug(f"[结算血量] {self._result_health_status}")
            return
        if (self._health_read_attempts >= 2 or self._last_health_read is not None
                and self._last_health_read.current is not None):
            return
        expected_outcome = getattr(screen, "outcome", "unknown")

        def same_result_page(frame):
            self._check_stop()
            observed = self._vision.read_battle_screen(frame)
            if observed.state in TERMINAL_STATES:
                return False
            outcome = getattr(observed, "outcome", "unknown")
            if (expected_outcome in {"success", "failure"} and outcome in {"success", "failure"}
                    and expected_outcome != outcome):
                return False
            if (observed.state in {"result_ready", "result_animation"}
                    and outcome in {"success", "failure"}):
                return True
            return bool(template and context and
                self._locate_page_template(CWIMG.CONTINUE, frame) is not None)

        self._health_read_attempts += 1
        self._last_health_read = self._vision.read_squad_health(
            RESULT_HEALTH_ROI, page_validator=same_result_page)
        self._result_health_status = {"state": "confirmed" if self._last_health_read.current is not None else "failed",
            "reason": self._last_health_read.reason, "attempts": self._health_read_attempts,
            "current": self._last_health_read.current, "outcome": self._last_battle_outcome,
            "page_evidence": "stable_result_template_context" if template else getattr(screen, "evidence", ""),
            "result_text": getattr(screen, "raw_text", "")[:480]}
        logger.info(f"[结算血量] {self._result_health_status}")

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
        # 不能把此前注册的 OCR 噪声当成真实角色定义。
        if name.strip().isdecimal() and name.strip() != Characters.username:
            return None
        return char

    def _area_name(self, characters):
        for name in ("on_field", "off_field", "in_hand"):
            if characters is getattr(self, name + "_character"):
                return name
        raise ValueError("未知角色区域")

    @staticmethod
    def _complete_slot_observation(observation):
        if observation_identity(observation) is None:
            return False
        return (observation.state != SlotState.KNOWN or observation.character.is_npc
                or type(observation.stars) is int and 1 <= observation.stars <= 3)

    def _record_slot_evidence(self, area_type, observation, *, observed_at=None):
        """登记一次真实读取，绝不以缓存对象、人口或逻辑空场刷新时效。"""
        key = (area_type, observation.slot_index)
        self._slot_evidence.pop(key, None)
        if not self._complete_slot_observation(observation):
            return
        if observation.evidence == "two_frame_locked_support":
            observed_at = self._backend_layout_observed_at
        elif observation.evidence in {"name_match", "empty_detector", "two_empty_frames",
                                      "two_locked_frames", "backend_ordinary_panel_review",
                                      "backend_empty_review"}:
            observed_at = time.monotonic() if observed_at is None else observed_at
        else:
            return
        if observed_at is not None:
            self._slot_evidence[key] = (observation, observed_at)

    def _slot_needs_scan(self, area, index, now=None):
        observation = self._observations[area][index]
        key = (area, index)
        # 逻辑空场基线没有逐槽OCR时间；只有未受动作或未知事件影响的槽仍可使用。
        if (area != "in_hand" and observation.state == SlotState.EMPTY
                and observation.evidence in {"new_game_empty", "zero_population"}
                and key not in self._dirty_slots
                and (area != "off_field" or self._layout_valid
                     and index in self._backend_ordinary_slots
                     and index not in self._backend_unknown_slots
                     and index not in self._backend_support_slots)):
            return False
        receipt = self._slot_evidence.get(key)
        return (key in self._dirty_slots or not self._complete_slot_observation(observation)
                or receipt is None or receipt[0] is not observation
                or (time.monotonic() if now is None else now) - receipt[1]
                    >= self.preparation_budget["field_refresh_seconds"])

    def _invalidate_roster_evidence(self, reason):
        """未知来源可同时改动任意身份/星级；保留历史，但恢复完整读取。"""
        if not reason.startswith("purchase_recheck"):
            self._mark_reward_transaction_context_change(reason)
        self._slot_evidence.clear()
        self._field_observed_at = self._bench_observed_at = None
        self._bench_dirty = True
        self._purchase_scan_baseline = None
        self._invalidate_backend_layout(reason)
        for area in ("on_field", "in_hand"):
            for index in range(len(self._observations[area])):
                self._set_observation(area, SlotObservation(index, SlotState.UNKNOWN,
                    evidence=reason))
        self._dirty_slots.update((area, index) for area, observations in self._observations.items()
                                 for index in range(len(observations)))
        logger.info(f"[角色证据失效] 来源={reason}，奖励身份/合成影响未知，恢复完整识别")

    # ssyb：分区证据齐备时保留真实时间，避免重复全场扫描。
    def _complete_incremental_field_observation(self):
        """分区真实补读完成后恢复全场标记；不读取画面、不刷新槽位时效。"""
        if self._field_observed_at is not None:
            return False
        if (not self._backend_identity_ready() or self._pending_move is not None
                or self._placement_pending or self._purchase_pending_names
                or self._runtime_node_pending or self._selection_event_pending is not None
                or self._equipment_choice_pending is not None or self._form_change_pending
                or self._population_conflict() is not None):
            return False
        now = time.monotonic()
        observed_times = []
        for area in ("on_field", "off_field"):
            slots = self._observations[area]
            if len(slots) != len(getattr(self, area + "_area")):
                return False
            for index, observation in enumerate(slots):
                if self._slot_needs_scan(area, index, now):
                    return False
                receipt = self._slot_evidence.get((area, index))
                if receipt is None:
                    # 通过上方检查的逻辑空场不是一次截图，不为它伪造时间。
                    continue
                if receipt[1] > now:
                    return False
                observed_times.append(receipt[1])
        if not observed_times:
            return False
        # 保留最早的真实观测时间，不延长证据有效期。
        self._field_observed_at = min(observed_times)
        logger.debug("[分区识别收尾] 前后台真实观测已齐全，恢复全场标记，不追加扫描")
        return True

    def _set_observation(self, area_type, observation):
        reviewed = (getattr(self, "_backend_identity_review_receipts", {}).get(observation.slot_index)
                    if area_type == "off_field" else None)
        if (area_type == "off_field" and observation.slot_index in self._backend_unknown_slots):
            # 只有本轮实际完成的有限身份复核可以解除疑点；普通 OCR、容量或旧空位不能授权。
            receipt = getattr(self, "_backend_identity_review_receipts", {}).get(observation.slot_index)
            if (receipt is not None and receipt[0] is observation
                    and receipt[1:] == (self._layout_revision, self._backend_identity_context())
                    and self._layout_valid
                    and observation.slot_index not in self._backend_support_slots):
                self._backend_unknown_slots.discard(observation.slot_index)
                self._backend_ordinary_slots = tuple(sorted(set(self._backend_ordinary_slots)
                                                          | {observation.slot_index}))
                self._backend_identity_confirmed = not self._backend_unknown_slots
                self._invalidate_backend_identity_dependents(observation.slot_index)
                logger.info(f"[后台身份] 槽={observation.slot_index} 当前准备页两帧普通身份复核完成；"
                            f"剩余疑点={sorted(self._backend_unknown_slots)}")
            else:
                observation = SlotObservation(observation.slot_index, SlotState.UNKNOWN,
                    evidence="backend_identity_unknown", revision=observation.revision)
        self._snapshot_revision += 1
        observations = self._observations[area_type]
        if observation.slot_index >= len(observations):
            observations.extend(SlotObservation(i, SlotState.UNKNOWN)
                                for i in range(len(observations), observation.slot_index + 1))
        observations[observation.slot_index] = observation
        if (reviewed is not None and reviewed[1:] ==
                (self._layout_revision, self._backend_identity_context())
                and observation_identity(reviewed[0]) == observation_identity(observation)
                and self._complete_slot_observation(observation)):
            self._backend_identity_review_receipts[observation.slot_index] = (
                observation, reviewed[1], reviewed[2])
        key = (area_type, observation.slot_index)
        complete = self._complete_slot_observation(observation)
        if observation.state != SlotState.UNKNOWN:
            self._dirty_slots.discard(key)
        receipt = self._slot_evidence.get(key)
        if not complete or receipt is None or receipt[0] is not observation:
            self._slot_evidence.pop(key, None)
        identity = observation_identity(observation)
        if identity is not None:
            # 替换或升级确认后，清除旧角色的拒绝记录。
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
        # UNKNOWN 保留历史值，但任何动作都不能使用该值。
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
        self._experience_input_revision += 1
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
            observation_identity(obs) == ("known", self.main_c)
            for obs in self._observations["in_hand"]))

    def _buy_experience(self, level, *, final_push=False, final_round=False,
                        confirmed_progress=None):
        if type(level) is not int:
            return False
        if not final_round:
            if (self.economy_config is not None
                    and level >= self.economy_config.stages[-1].target_level):
                return False
            if not final_push and not self._can_upgrade(level):
                return False
        reusable = (confirmed_progress is not None and final_round
                    and confirmed_progress[0] == self._experience_context_key(level))
        progress = (confirmed_progress[1] if reusable
                    else self._experience_progress_before_input(level))
        self._experience_before = (level, progress)
        self._experience_cost_before = self._read_action_cost("experience")
        self._check_stop()
        self._experience_input_revision += 1
        if not self.operator.press_key("f"):
            return False
        self._coin_action_costs.clear()
        self.operator.sleep(0.5)
        self._population_read_key = None
        self._invalidate_level()
        return True

    def _observe_slot(self, area_type, index, count_stars=False, use_backup_ocr=False):
        observed_at = time.monotonic()
        observation = self._observe_slot_impl(area_type, index, count_stars, use_backup_ocr)
        self._record_slot_evidence(area_type, observation, observed_at=observed_at)
        return observation

    def _observe_slot_impl(self, area_type, index, count_stars=False, use_backup_ocr=False):
        self._check_stop()
        if area_type == "off_field" and not self._layout_valid:
            return SlotObservation(index, SlotState.UNKNOWN, evidence="layout_changed")
        if area_type == "off_field" and index in self._backend_unknown_slots:
            return self._observe_backend_identity(index)
        if (area_type == "off_field" and index not in self._backend_support_slots
                and index not in self._backend_ordinary_slots):
            return SlotObservation(index, SlotState.UNKNOWN, evidence="backend_slot_not_authenticated")
        area = getattr(self, area_type + "_area")[index]
        previous = self._observations[area_type][index]
        self._observation_revision += 1
        support = getattr(self, "_backend_support_slots", {}).get(index) if area_type == "off_field" else None
        if support is not None:
            # 布局读取器已在两张当前帧上认证该锁定占位。
            # 它没有普通角色面板或星级面板。
            return SlotObservation(index, SlotState.KNOWN, support, True,
                "two_frame_locked_support", self._observation_revision, None)
        # 始终关闭旧面板，包括身份未知或无需装备的情况。
        self.operator.click_point(0.5, 0.5, trace=False)
        try:
            if not self.operator.click_point(*area, after_sleep=0.2, trace=False):
                return SlotObservation(index, SlotState.UNKNOWN, evidence="click_failed",
                                       revision=self._observation_revision)
            results = self._vision.operator_ocr(from_x=0.775, from_y=0.175, to_x=0.880, to_y=0.2315)
            char = parse_character_name(results, self._lookup_known_character)
            if char is None and use_backup_ocr:
                backup = self._vision.operator_ocr(from_x=0.775, from_y=0.445, to_x=0.880, to_y=0.486)
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
            # 检测器必须提供明确的空位证据；仅 OCR 缺失不能证明空位。
            detector = getattr(self.operator, "currency_wars_slot_is_empty", None)
            empty = detector(area_type, index) if callable(detector) else None
            if empty is None:
                empty = self._vision.slot_is_empty(area_type, index, area)
            if empty is True:
                return SlotObservation(index, SlotState.EMPTY, occupied=False,
                                       evidence="empty_detector", revision=self._observation_revision)
            # 场上空位基线持续有效，直到动作以该槽位为目标。
            # 续局也可通过实时 0/N 读数建立同样的基线。
            # 文本冲突会使该基线也失效。
            if (area_type != "in_hand" and previous.state == SlotState.EMPTY
                    and (area_type, index) not in self._dirty_slots
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

    def _invalidate_backend_identity_dependents(self, index):
        """单槽身份改变仅撤销其证据及依赖计划；不改其他槽对象或真实读取时间。"""
        self._population_current = self._population_read_key = None
        self._effective_targets_key = None
        self._preparation_assessment_cache = None
        self._formation_plan = ()
        self._formation_plan_stage = None
        self._equipment_dirty = True
        self._move_failures.clear()
        self._fielding_rejections = {key for key in self._fielding_rejections
                                    if key[:2] != ("off_field", index)}

    def _backend_identity_context(self):
        preparation_id = getattr(self, "_preparation_id", None)
        if preparation_id is not None:
            checkpoint = getattr(getattr(self, "_session_store", None), "checkpoint", None)
            return (getattr(checkpoint, "run_id", None), preparation_id)
        # 旧夹具尚未真正进入准备期；正式运行以稳定准备期ID为准，绝不关联deadline。
        return (self._cycle_number, self._preparation_round)

    def _backend_new_identity_doubts(self, layout):
        """布局复核不能遗漏其他槽的新疑点；仅当前仍新鲜的真实回执可解释旧角标。"""
        reviews = getattr(self, "_backend_identity_review_receipts", {})
        observations = self._observations["off_field"]
        context = (self._layout_revision, self._backend_identity_context())
        new_doubts = set(layout.unknown_protected_slots) - self._backend_unknown_slots
        return {index for index in new_doubts if not (
            index in range(len(observations)) and index in reviews
            and reviews[index][0] is observations[index]
            and reviews[index][1:] == context
            and index not in layout.protected_slots
            and not self._slot_needs_scan("off_field", index))}

    def _backend_review_layout_matches(self, layout, positions, index):
        return (layout.valid and layout.geometry_valid
                and len(layout.positions) == len(positions)
                and all(abs(a - b) <= 0.002 for old, new in zip(positions, layout.positions)
                        for a, b in zip(old, new))
                and index not in layout.protected_slots
                and set(layout.protected_slots) == set(self._backend_support_slots)
                and not self._backend_new_identity_doubts(layout)
                and (layout.ordinary_count_confirmed or layout.reason == "backend_identity_partial"))

    def _reject_backend_identity_review(self, layout, positions):
        geometry_same = (layout.valid and layout.geometry_valid
            and len(layout.positions) == len(positions)
            and all(abs(a - b) <= .002 for old, new in zip(positions, layout.positions)
                    for a, b in zip(old, new)))
        if not geometry_same or layout.reason == "backend_support_profile_unavailable":
            self._invalidate_backend_layout("backend_identity_review_layout_unconfirmed")
            return
        # 新支援头像与当前分类冲突时只隔离改变的身份，未改变槽的观测时效保持不变。
        changed = ((set(layout.protected_slots) ^ set(self._backend_support_slots))
                   | self._backend_new_identity_doubts(layout))
        self._backend_unknown_slots.update(changed)
        self._backend_identity_confirmed = False
        self._backend_ordinary_slots = tuple(i for i in self._backend_ordinary_slots if i not in changed)
        self._backend_support_slots = {i: char for i, char in self._backend_support_slots.items()
                                       if i not in changed}
        for index in changed:
            self._invalidate_backend_identity_dependents(index)
            self._set_observation("off_field", SlotObservation(index, SlotState.UNKNOWN,
                evidence="backend_support_identity_conflict"))

    def _read_backend_review_panel(self, frame):
        """姓名、星级和页面必须来自同一新鲜帧，不使用过去的角色面板。"""
        import pyscreeze
        if frame is None or self._observe_page_frame(frame, full_navigation=False) != ("preparation", None):
            return None
        width, height = frame.size
        crop = frame.crop((round(.775 * width), round(.175 * height),
                           round(.880 * width), round(.2315 * height)))
        # 复核与普通姓名使用同一配置，且不低于0.7；仍要求姓名、星级、两帧与前后布局一致。
        confidence = max(0.7, getattr(self.operator, "ocr_confidence", 0.7))
        rows = self._vision._engine_ocr(crop.convert("L"), minimum_confidence=confidence)
        char = parse_character_name(rows, self._lookup_known_character)
        if char is None or char.is_npc or char.is_locked:
            return None
        pixels = frame.crop((round(.83 * width), round(.15 * height),
                             round(.87 * width), round(.17 * height)))
        template = load_match_template(CWIMG.STAR, pyscreeze.GRAYSCALE_DEFAULT)
        matches = []
        try:
            for box in pyscreeze.locateAll(template, pixels,
                    grayscale=pyscreeze.GRAYSCALE_DEFAULT, confidence=self.operator.tm_confidence):
                self._check_stop()
                if not any(abs(box.left - other.left) < 3 and abs(box.top - other.top) < 3
                           for other in matches):
                    matches.append(box)
        except pyscreeze.ImageNotFoundException:
            pass
        return (char, len(matches)) if 1 <= len(matches) <= 3 else None

    def _observe_backend_identity(self, index):
        """疑点槽只允许一次面板打开、两帧身份读取；复核期间仍禁止拖拽和出售。"""
        unknown = SlotObservation(index, SlotState.UNKNOWN, evidence="backend_identity_unknown")
        if not self._layout_valid or index in self._backend_support_slots:
            return unknown
        if not self._set_shop_open(False):
            return unknown
        positions, revision = tuple(self.off_field_area), self._layout_revision
        context = self._backend_identity_context()
        before = self._vision.read_backend_layout(positions)
        if not self._backend_review_layout_matches(before, positions, index):
            self._reject_backend_identity_review(before, positions)
            return unknown
        observed = None
        try:
            if self._observe_page_frame(self._capture_page_frame(), full_navigation=False) != ("preparation", None):
                return unknown
            self.operator.click_point(.5, .5, trace=False)
            # 明确双帧空位也可解除疑点；单次检测器或 OCR 空白不构成空位证据。
            empty_frames = []
            for frame_index in range(2):
                if frame_index:
                    self.operator.sleep(.15)
                frame = self._capture_page_frame()
                if self._observe_page_frame(frame, full_navigation=False) != ("preparation", None):
                    return unknown
                empty_frames.append(frame)
            empty = self._vision._slot_is_empty("off_field", index, positions[index],
                frame_source=lambda number: empty_frames[number], identity_review=True)
            if empty is True:
                self._observation_revision += 1
                observed = SlotObservation(index, SlotState.EMPTY, occupied=False,
                    evidence="backend_empty_review", revision=self._observation_revision)
            else:
                if not self.operator.click_point(*positions[index], after_sleep=.2, trace=False):
                    return unknown
                first = self._read_backend_review_panel(self._capture_page_frame())
                self.operator.sleep(.15)
                self._check_stop()
                second = self._read_backend_review_panel(self._capture_page_frame())
                if (first is None or second is None
                        or first[0].name != second[0].name or first[1] != second[1]):
                    return unknown
                self._observation_revision += 1
                observed = SlotObservation(index, SlotState.KNOWN, second[0], True,
                    "backend_ordinary_panel_review", self._observation_revision, second[1])
        finally:
            # 读取期间页面可能已离开；仅当前准备页仍可授权关面板坐标。
            if self._observe_page_frame(self._capture_page_frame(), full_navigation=False) == ("preparation", None):
                self.operator.click_point(.5, .5, trace=False)
            else:
                self._layout_valid = self._backend_identity_confirmed = False
        if (not self._set_shop_open(False) or revision != self._layout_revision
                or context != self._backend_identity_context()):
            return unknown
        after = self._vision.read_backend_layout(positions)
        if not self._backend_review_layout_matches(after, positions, index):
            self._reject_backend_identity_review(after, positions)
            return unknown
        if not hasattr(self, "_backend_identity_review_receipts"):
            self._backend_identity_review_receipts = {}
        self._backend_identity_review_receipts[index] = (observed, revision, context)
        return observed

    def _scan_store(self):
        self._check_stop()
        # 同一页未变化的文字像素可复用 OCR；每次仍取新截图确认实际牌面。
        frame = self._capture_page_frame()
        results = None
        width = self.operator.window_context.width
        same_frame = (frame is not None and callable(getattr(frame, "crop", None))
                      and callable(getattr(self.operator, "ocr_engine", None)))
        if same_frame:
            try:
                width, height = frame.size
                crop = frame.crop((round(0.19 * width), round(0.26 * height),
                                   round(0.88 * width), round(0.31 * height))).convert("RGB")
                results = self._vision._engine_ocr(crop.convert("L"))
            except ThreadStoppedError:
                raise
            except Exception as error:
                self._check_stop()
                same_frame = False
                logger.debug(f"[商店识别] 同帧读取未完成：{type(error).__name__}；转现场OCR")
        if not same_frame:
            width = self.operator.window_context.width
            results = self.operator.ocr(from_x=0.19, from_y=0.26, to_x=0.88, to_y=0.31)
        offer = scan_store_cards(results, self._lookup_known_character, self.store_area,
                                 width)
        if same_frame and (offer.state == ShopState.UNKNOWN or offer.reason.startswith("partial")):
            # 只有名称/槽位识别不完整才使用同帧彩色后备；价格未知直接交给采购。
            try:
                color_offer = scan_store_cards(self._vision._engine_ocr(crop),
                    self._lookup_known_character, self.store_area, width)
                original_names = {card.slot_index: card.character.name for card in offer.cards}
                color_names = {card.slot_index: card.character.name for card in color_offer.cards}
                if (color_offer.state == ShopState.READY and not color_offer.reason.startswith("partial")
                        and all(color_names.get(slot) == name for slot, name in original_names.items())):
                    offer = color_offer
                    logger.debug("[商店识别] 同帧彩色后备补全名称与槽位")
            except ThreadStoppedError:
                raise
            except Exception as error:
                self._check_stop()
                logger.debug(f"[商店识别] 彩色后备未完成：{type(error).__name__}")
        if offer.state == ShopState.UNKNOWN:
            empty_slots = self._vision.slot_is_empty_batch("store", self.store_area)
            if (len(empty_slots) == len(self.store_area)
                    and all(value is True for value in empty_slots.values())):
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
        self._reconcile_form_change_pending()
        return offer

    def _confirm_purchase(self, card, before_coins):
        self._confirmed_purchase_snapshot = None
        after = self._scan_store()
        if after.state == ShopState.FULL:
            return ActionResult.FAILED
        remaining = next((c for c in after.cards if c.slot_index == card.slot_index), None)
        coins = self._read_coins_after_action(before_coins, card.price, "purchase")
        spent = before_coins - coins if before_coins is not None and coins is not None else None
        observations = getattr(self, "_purchase_confirmation_observations", None)
        if observations is not None:
            observations.append(purchase_noop_evidence(card,
                getattr(self, "_purchase_offer_before", None), after, before_coins, coins,
                getattr(self, "_purchase_coin_read_before", None), self._last_coin_observation))
        changed = (after.state == ShopState.EMPTY or
                   (after.state == ShopState.READY and remaining is None
                    and not after.reason.startswith("partial")))
        if not changed and remaining is None:
            changed = self._vision.slot_is_empty("store", card.slot_index, card.target) is True
        price_match = validate_coin_change(before_coins, coins,
            expected_spend=card.price, allow_zero=True)
        if card.price is None:
            balance_read = self._last_coin_observation
            reliable_balance = (balance_read is not None and balance_read.reliable
                                and balance_read.value == coins)
            if changed and reliable_balance and spent is not None and spent > 0:
                logger.info(f"[未知价格购后确认] {card.character.name} 商品已消失，"
                            f"实际金币={before_coins}->{coins}，支出={spent}")
                self._confirmed_purchase_snapshot = (after, coins)
                return ActionResult.CONFIRMED
            if (after.state == ShopState.READY and not after.reason.startswith("partial")
                    and remaining is not None and remaining.character.name == card.character.name
                    and reliable_balance and coins == before_coins):
                # 外层会再确认一次；只跳过本页这个未成交槽位，不重复点击。
                self._confirmed_purchase_snapshot = (after, coins)
                return ActionResult.FAILED
        if changed and price_match.accepted is True and spent != 0:
            self._confirmed_purchase_snapshot = (after, coins)
            return ActionResult.CONFIRMED
        if changed:
            # 免费或折扣输入需要真实库存证据；
            # 仅余额不变不能区分点击未生效。
            before = self._purchase_before_copies.get(card.character.name)
            if before is None:
                before = self._held_purchase_copies(card.character.name)
            if self._recheck_purchased_characters({card.character.name}):
                actual = self._held_purchase_copies(card.character.name)
                if before is not None and actual is not None and actual >= before + 1:
                    if not self._set_shop_open(True):
                        return ActionResult.INDETERMINATE
                    coins = self.get_coins()
                    logger.info(f"[金币校验] action=purchase name={card.character.name} "
                        f"before={before_coins} after={coins} reason=inventory_confirmed "
                        f"charge={price_match.reason}；按现场金额继续")
                    self._confirmed_purchase_snapshot = (None, coins)
                    return ActionResult.CONFIRMED
        return ActionResult.INDETERMINATE

    def _confirm_sale(self, index, character, before_coins):
        after = self._observe_slot("in_hand", index, count_stars=True)
        self._set_observation("in_hand", after)
        if after.state == SlotState.EMPTY:
            return ActionResult.CONFIRMED
        # 金币收入仅在此独立拖拽窗口内作为佐证。
        coins = self.get_coins()
        if before_coins is not None and coins is not None and coins > before_coins:
            if after.state == SlotState.KNOWN and after.character.name != character.name:
                return ActionResult.CONFIRMED
            receipt = getattr(self, "_bench_full_sale_receipt", None)
            if (receipt is not None and receipt["index"] == index and receipt["queued"] > 0
                    and after.state == SlotState.KNOWN):
                pressure = self._read_full_bench_recovery()
                if pressure.known and pressure.queued == receipt["queued"] - 1:
                    # 仅该故障处理链中，金币增加和队列恰好减少一张共同证明
                    # 出售成功；同名补位不再触发第二次拖拽。
                    logger.info(f"[满员恢复] 出售已确认，溢出同名补位：{character.name} "
                                f"队列={receipt['queued']}->{pressure.queued}")
                    return ActionResult.CONFIRMED

        return ActionResult.INDETERMINATE

    def run(self):
        self._report_runtime_identity()
        self.is_running = True
        self._runtime_flow_failure = None
        return self._run_remaining_games(0)

    # Yukki：串行交接延续当前局，不能重置原定运行次数。
    def _run_remaining_games(self, start_index, *, resume_current=False):
        """替换当前任务对象时，保留原局序号及剩余运行局数。"""
        if self.runtimes == 0:
            return True
        for i in range(start_index, self.runtimes):
            if not self.is_running:
                break
            self._runtime_game_index = i
            logger.info(f"第{i + 1}次进入货币战争，剩余{self.runtimes - i - 1}次")
            try:
                self._check_stop()
                if resume_current and i == start_index:
                    # 此路径不调用重新开局或创建会话的方法，避免
                    # 丢弃旧收据，或从头重跑配置的局数。
                    battle_before = self._last_completed_battle_id
                    started = self._recover_runtime_flow(
                        "existing recovery exhausted; serial engine handoff",
                        self.FLOW_RECOVERY_ATTEMPTS + len(self.AUTO_RESUME_DELAYS) + 1)
                    if not started:
                        self._mark_runtime_rebuild_failure(RuntimeError("重建后当前页面仍未确认"))
                        self._record_execution_stop("error")
                        return False
                    if (self._last_completed_battle_id != battle_before
                            or self._preparation_departure_confirmed):
                        self._cycle_number += 1
                        self._preparation_deadline = self._formation_deadline = None
                        self._preparation_departure_confirmed = False
                        if self._last_completed_battle_id != battle_before:
                            self._flow_recovery_attempts = self._auto_resume_attempts = 0
                        self._record_checkpoint(phase="preparation")
                    transaction_recheck = getattr(self,
                        "_resume_reward_fast_transaction_after_rebuild", None)
                    ledger = self._reward_fast_page_ledger
                    if ledger is not None and ledger.get("pending") is not None:
                        if not callable(transaction_recheck) or not transaction_recheck():
                            self._mark_runtime_rebuild_failure(RuntimeError("重建后原奖励交易仍未确认"))
                            self._record_execution_stop("error")
                            return False
                else:
                    started = self.start_game()
                if self._startup_failed:
                    return False
                if started and not self.is_game_over:
                    self.game_loop()
                self._runtime_game_index = i + 1
            except ThreadStoppedError:
                self._record_execution_stop("stopped")
                raise
            except InterruptedError:
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
        except InterruptedError:
            self._record_execution_stop("stopped")
            raise
        except Exception as error:
            self._record_execution_stop("error")
            logger.error(error)
            return False

    def _mark_runtime_rebuild_failure(self, error):
        """只有原运行导航恢复额度耗尽的故障，才可申请外层交接。"""
        if (isinstance(error, RuntimeError) and self.is_running and not self.is_game_over
                and not self._startup_failed
                and getattr(self, "_flow_recovery_attempts", 0) >= self.FLOW_RECOVERY_ATTEMPTS
                and getattr(self, "_auto_resume_attempts", 0) >= len(self.AUTO_RESUME_DELAYS)):
            clock = getattr(self, "_battle_wait_clock", None)
            if (self._pending_battle_id and clock is not None
                    and clock[0] == self._pending_battle_id
                    and time.monotonic() - clock[1] >= self.BATTLE_MAX_WAIT_SECONDS):
                return False
            self._runtime_flow_failure = RuntimeFlowFailure(
                "runtime_recovery_exhausted", str(error)[:240])
            return True
        return False

    def export_runtime_rebuild_context(self):
        return capture_runtime_recovery(self)

    def resume_runtime_rebuild(self, context):
        """携带原收据及已消耗额度，继续同一局游戏。"""
        self._check_stop()
        try:
            restore_runtime_recovery(self, context)
        except (ValueError, TypeError, OSError) as error:
            logger.error(f"[串行任务重建] 原存档或上下文未通过核验：{error}")
            return False
        logger.warning("[串行任务重建] 原任务已返回，在同一宿主线程认证当前页面并恢复原对局")
        return self._run_remaining_games(self._runtime_game_index, resume_current=True)

    def handle_ending(self):
        """ 处理游戏结束逻辑，默认退出货币战争页面 """
        self._check_stop()
        if self.operator.wait_img(CWIMG.START_CURRENCY_WARS, timeout=self.PAGE_LOCATE_TIMEOUT) is None:
            self._fail_battle("result_main_menu_missing")
        self._check_stop()
        return self.operator.press_key("esc")

    def reset_character(self):
        """仅重置游戏状态，保留攻略优先级及角色定义。"""
        self._session_context_tracking = False
        self._preparation_id = None
        self._runtime_rebuild_active = False
        self._reward_fast_active = False
        self._reward_fast_page_ledger = None
        for char in {id(c): c for c in Characters.characters.values()}.values():
            char.is_placed = False
            char.stars = 0
        self.on_field_character[:] = [None] * len(self.on_field_area)
        self.off_field_area = list(self._default_off_field_area)
        self.off_field_character[:] = [None] * len(self.off_field_area)
        self._backend_support_slots = {}
        self._backend_unknown_slots = set()
        self._backend_ordinary_slots = ()
        self._backend_identity_confirmed = False
        self._vision.reset_backend_layout()
        self.in_hand_character[:] = [None] * len(self.in_hand_area)
        self._observations = {
            area: [SlotObservation(i, SlotState.UNKNOWN) for i in range(len(getattr(self, area + "_area")))]
            for area in ("on_field", "off_field", "in_hand")
        }
        self.max_team_size = 3
        self.is_continue = False
        self._runtime_node_pending = None
        self._invest_simple_equipment_pending = False
        self._last_selection_sent = False
        self._selection_event_pending = None
        self._economy_stage_index = None
        self._economy_evidence_recheck_attempted = False
        self._economy_level_rechecked = False
        self._preparation_round = None
        self._round_read_attempts = 0
        self._all_in_decision = None
        self._equipment_others_checked = False
        self._coin_shop_open = None
        self._clear_transaction_evidence()
        self._all_in_budget = None
        self._confirmed_battle_count = 0
        self._confirmed_battle_lower_bound = 0
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
        self._bench_full_failure_pending = False
        self._bench_full_sale_receipt = None
        self._equipment_attempts.clear()
        self._equipment_choice_pending = None
        self._equipment_resource_revision += 1
        self._population_read_key = None
        self._sale_population_retry_used = False
        self._population_auto_retries = 0
        self._population_next_retry_at = 0.0
        self._effective_targets = None
        self._effective_targets_key = None
        self._preparation_assessment_cache = None
        self._terminal_route_screen = None
        self._formation_plan = ()
        self._formation_plan_stage = None
        self._formation_plan_incomplete = False
        self._formation_successor_prefix_pending = False
        self._purchase_pending_names.clear()
        self._placement_pending = False
        self._observed_prices.clear()
        self._form_change_pending.clear()
        self._dirty_slots.clear()
        self.phase_seconds.clear()
        self._last_shopping_result = None
        self._last_level_read = None

        self._pending_move = None
        self._move_failures.clear()
        self._fielding_rejections.clear()
        self._preparation_deadline = self._formation_deadline = None
        self._preparation_rewards_collected = False
        self._preparation_departure_confirmed = False
        self._field_observed_at = self._bench_observed_at = None
        self._slot_evidence.clear()
        self._backend_layout_observed_at = None
        self._experience_input_revision += 1
        self._bench_dirty = True
        self._population_current = None
        self._last_health_read = None
        self._last_battle_outcome = "unknown"
        self._terminal_health_read = False
        self._snapshot_revision += 1
        self._layout_revision += 1
        self._layout_valid = False

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
        if depth > 5:
            raise RuntimeError("页面定位递归过深，可能存在无限循环")
        deadline = time.monotonic() + self.PAGE_LOCATE_TIMEOUT
        entry_attempts, previous = depth, None
        while time.monotonic() < deadline:
            self._check_stop()
            frame = self._capture_page_frame()
            observed = self._observe_page_frame(frame)
            if time.monotonic() >= deadline:
                break
            phase, _ = observed
            # 启动定位也使用上层弹窗优先级，不接受露出的准备按钮。
            if phase in {"terminal", "combat", "settlement", "node", "advance",
                         "equipment_choice", "selection_event", "shop_probability"}:
                self._recovery_page = phase if phase in {"terminal", "combat", "settlement"} else "node"
                return CurrencyWarsPage.RECOVERY
            stable = previous is not None and self._same_runtime_page(previous, observed)
            previous = observed
            if stable and phase == "main_menu":
                logger.info("[页面定位] 已定位到货币战争开始页面")
                return CurrencyWarsPage.START
            if stable and phase == "preparation":
                logger.info("[页面定位] 已定位到货币战争准备阶段")
                return CurrencyWarsPage.PREPARATION
            if stable and phase == "boss_preview":
                logger.info("[页面定位] 已定位到对局首领展示页面")
                return CurrencyWarsPage.BOSS_PREVIEW
            if stable and phase == "bonus_points":
                self.operator.press_key("esc")
                previous = None
                continue  # 输入后必须重新认证页面。
            if stable and phase == "entry":
                if entry_attempts >= 6:
                    break
                entry_attempts += 1
                if self._locate_page_template(CWIMG.CURRENCY_WARS, frame) is not None:
                    self.operator.press_key("f")
                else:
                    logger.info("[页面定位] 正在定位到货币战争开始页面")
                    guide_hotkey = self.settings.General.hotkeyF4
                    self.operator.press_key(str(guide_hotkey).lower())
                    remaining = min(self.ENTRY_TRANSITION_TIMEOUT, max(0, deadline - time.monotonic()))
                    if not self.operator.wait_img(IMG.F4, timeout=remaining):
                        logger.error(SRAError(ErrorCode.WAIT_TIMEOUT, "等待指南界面超时"))
                        self.operator.press_key("esc")
                        break
                    remaining = min(self.ENTRY_TRANSITION_TIMEOUT, max(0, deadline - time.monotonic()))
                    box = self.operator.wait_img(IMG.COSMIC_STRIFE, timeout=remaining)
                    if box is None or time.monotonic() >= deadline:
                        break
                    self.operator.click_box(box, after_sleep=1)
                    self.operator.click_point(0.242, 0.30, after_sleep=0.8)
                    self.operator.click_point(0.7786, 0.8194, after_sleep=1)
                previous = None
            self.operator.sleep(min(0.5, max(0, deadline - time.monotonic())))
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
        # 一次性的进入/攻略钩子使用其原有边界；共享预算从首次初始化开始。
        started = time.monotonic()
        context = self._startup_recovery_context = dict(active=True, started=started,
            deadline=started + self.STARTUP_RECOVERY_SECONDS, attempts=0,
            confirmed_flow_seconds=0.0, budget_reason="")
        try:
            # 只重试初始化观测；会话、攻略和新局角色初始化均不重放。
            while True:
                self._check_stop()
                if context["attempts"] >= self.STARTUP_RECOVERY_ATTEMPTS:
                    context["budget_reason"] = "attempt_limit"
                elif time.monotonic() >= context["deadline"]:
                    context["budget_reason"] = "time_limit"
                if context["budget_reason"]:
                    return self._fail_startup("startup_recovery_exhausted", "准备页初始化共享恢复额度已耗尽")
                if context["attempts"] >= 2:
                    delay = self.AUTO_RESUME_DELAYS[context["attempts"] - 2]
                    self.operator.sleep(min(delay, max(0, context["deadline"] - time.monotonic())))
                    self._check_stop()
                    if time.monotonic() >= context["deadline"]:
                        context["budget_reason"] = "time_limit"
                        return self._fail_startup("startup_recovery_exhausted", "准备页初始化共享等待时间已耗尽")
                context["attempts"] += 1
                self._startup_observation_retryable = False
                try:
                    initialized = self._initialize_game()
                except (ThreadStoppedError, InterruptedError):
                    raise
                except RuntimeError as error:
                    # 子导航可能在首次输入前因自己的短时限抛错；只接管
                    # 已明确耗尽的导航额度，其他初始化错误仍按原语义传播。
                    if (time.monotonic() < context["deadline"]
                            and not str(error).startswith("页面导航额度已耗尽")):
                        raise
                    self._startup_observation_retryable = True
                    initialized = False
                    self._record_observation_issue("startup_navigation_timeout", str(error))
                if initialized:
                    break
                if not self._startup_observation_retryable:
                    return self._fail_startup("startup_initialization_failed", "对局初始化失败")
                self._record_observation_issue("startup_shop_not_closed",
                    f"继续进度的商店收起尚未确认，保留同一对局；"
                    f"尝试={context['attempts']}/{self.STARTUP_RECOVERY_ATTEMPTS}")
                if time.monotonic() >= context["deadline"]:
                    continue
                try:
                    observed = self._probe_runtime_page()
                    self._check_stop()
                    if time.monotonic() >= context["deadline"]:
                        continue
                    self.operator.sleep(min(0.3, max(0, context["deadline"] - time.monotonic())))
                    current = self._probe_runtime_page()
                    self._check_stop()
                    if not self._same_runtime_page(observed, current):
                        continue
                    phase = current[0]
                    # 战斗和终局交给各自既有边界；其余页面不得越过共享导航期限。
                    if phase in {"terminal", "combat", "settlement"} or (
                            time.monotonic() < context["deadline"] and phase in {
                            "node", "advance", "equipment_choice", "selection_event", "shop_probability"}):
                        self._recovery_page = phase if phase in {"terminal", "combat", "settlement"} else "node"
                        if self._recover_live_page() and self.is_game_over:
                            return True
                except (ThreadStoppedError, InterruptedError):
                    raise
                except Exception as error:
                    self._record_observation_issue("startup_page_recheck",
                        f"现场页面恢复尚未完成：{type(error).__name__} {error}")
            if not self.handle_game_initialized():
                return False
            logger.info("[启动流程] 对局启动成功")
            self.is_game_over = False
            return True
        finally:
            context["active"] = False

    # Yukki：启动失败先保留原因，再交回有限恢复流程。
    def _fail_startup(self, reason: str, message: str) -> bool:
        # RerollStart 的生命周期钩子有意返回 False；
        # 只有已确认的进入或初始化失败才能中止整个任务。
        self._startup_failed = True
        self.is_running = False
        context = getattr(self, "_startup_recovery_context", None)
        details = {"evidence": message}
        if context is not None and context["active"]:
            details.update(attempts=context["attempts"],
                elapsed_seconds=max(0, time.monotonic() - context["started"]),
                no_progress_seconds=max(0, time.monotonic() - context["started"]
                    - context["confirmed_flow_seconds"]), budget_reason=context["budget_reason"])
        logger.error(f"[启动流程] 原因={reason}；{message}；恢复={details}")
        self._check_stop()
        try:
            sample = self._vision.capture_sample(reason, details, critical=True)
            logger.info(f"[启动诊断] 保存原因={self._vision.last_sample_reason}")
            if sample is not None:
                logger.warning(f"[启动诊断] 已保存失败时游戏画面：{sample}")
        except (ThreadStoppedError, InterruptedError):
            raise
        except Exception as error:
            self._check_stop()
            logger.warning(f"[启动诊断] 采样未完成，保留启动失败结果：{type(error).__name__} {error}")
        return False

    def _record_observation_issue(self, reason, message):
        """识别缺口留存运行日志；采样故障不妨碍后续自动复核。"""
        self._check_stop()
        logger.warning(f"[识别继续] 原因={reason}；{message}；任务保持运行")
        now = time.monotonic()
        sample_times = getattr(self, "_observation_sample_times", None)
        if sample_times is None:
            self._observation_sample_times = sample_times = {}
        if now - sample_times.get(reason, float("-inf")) < 30:
            return
        sample_times[reason] = now
        try:
            sample = self._vision.capture_sample(reason, {"evidence": str(message)[:480]}, critical=True)
            logger.info(f"[识别留证] 原因={reason} 截图={sample} "
                        f"保存结果={getattr(self._vision, 'last_sample_reason', 'unknown')}")
        except (ThreadStoppedError, InterruptedError):
            raise
        except Exception as error:
            self._check_stop()
            logger.warning(f"[识别留证] 原因={reason} 采样未完成：{type(error).__name__} {error}；"
                           "错误仍保留在独立运行日志，继续自动复核")

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
            # 启动停止时可能已进入新局；继续执行现有首领或环境钩子，
            # 不再重复点击进入。
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
        """共用接管已观测的战斗或结果页，绝不重放战斗输入。"""
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
        # 完成状态由结果认证，与导航点击是否成功无关。
        # 同一场战斗的计数保持幂等。
        self._confirm_completed_battle(evidence)
        if ready:
            return True
        self._check_stop()
        if box is not None:
            return self.operator.click_box(box, after_sleep=after_sleep)
        return self.operator.click_point(*point, after_sleep=after_sleep, tag="恢复：继续挑战")

    def _recover_live_page(self):
        # 当前观测页面决定恢复方式；已保存摘要
        # 仅为历史，绝不授权重复购买、拖拽或选择。
        phase = getattr(self, "_recovery_page", "node")
        if phase in ("terminal", "combat", "settlement"):
            context = getattr(self, "_startup_recovery_context", None)
            active = context is not None and context["active"]
            started = time.monotonic()
            previous_pause = getattr(self, "_startup_recovery_paused", False)
            navigation_deadline = getattr(self, "_page_navigation_deadline", None)
            self._startup_recovery_paused = True
            self._page_navigation_deadline = None
            try:
                if phase == "terminal":
                    return self.handle_game_over(None)
                # 原战斗 ID 和累计 3600 秒计时留在 _resume_battle_phase 内。
                if not self._resume_battle_phase(phase, after_sleep=self.STAGE_SETTLE_SECONDS,
                                                 evidence="resumed_settlement_or_stage"):
                    return False
            finally:
                self._startup_recovery_paused = previous_pause
                self._page_navigation_deadline = navigation_deadline
                if active:
                    elapsed = max(0, time.monotonic() - started)
                    context["deadline"] += elapsed
                    context["confirmed_flow_seconds"] += elapsed
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
        # 保留原有成功进入顺序：目标 LOGO 出现时停止点击。
        # 若等待它消失，会在页面已经变化后再次点击，
        # 这是 2026-10-08 启动回归问题。
        if not self.operator.do_while(
            lambda: self.operator.click_box(box),  # NOQA  # pyright: ignore[reportArgumentType]  # 保留操作器兼容调用的静态检查指令。
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

        # 4. 处理首领信息。
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
            # 仅箭头消失不能证明已到最低难度；
            # 选择页面本身必须在两次读取中仍可见。
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
        """处理首领信息流程，抽离为独立方法。"""
        # 等待下一步提示
        next_step_box = self.operator.wait_img(
            CWIMG.NEXT_STEP,
            timeout=self.ENTRY_TRANSITION_TIMEOUT
        )
        if not next_step_box:
            logger.error("[Boss信息] 未识别到下一步提示")
            return False

        # 处理首领信息并点击下一步。
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
        deadline = self._page_navigation_limit(self.STARTUP_RECOVERY_SECONDS)
        self.operator.sleep(min(1, max(0, deadline - time.monotonic())))
        self._check_stop()
        if time.monotonic() >= deadline:
            self._startup_observation_retryable = True
            return False
        if self.is_continue:
            # 继续进度：获取前台角色信息
            logger.info("[初始化] 继续进度")
            if not self._set_shop_open(False):
                self._startup_observation_retryable = True
                logger.warning("[初始化] 继续进度的准备界面尚未确认，继续自动复核")
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
        # 新局从空场开始；续局必须观测实际场地。
        return True

    def handle_boss_info(self) -> None:
        """处理进入对局后可能出现的首领信息提示框。
若需额外操作，例如记录首领信息或调整攻略，可在此方法中实现。
"""
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

    def _strategy_code_controls(self, frame):
        """同帧认证1080p攻略码弹窗，不能在其他页面盲点剪贴板坐标。"""
        self._check_stop()
        if frame is None or tuple(frame.size) != (1920, 1080) or tuple(frame.size) != (
                self.operator.window_context.width, self.operator.window_context.height):
            return None
        title = self._locate_page_template(CWIMG.STRATEGY_CODE_TITLE, frame)
        paste = self._locate_page_template(CWIMG.STRATEGY_CODE_PASTE, frame)
        if title is None or paste is None:
            return None
        tx, ty = title.center
        px, py = paste.center
        if not (870 <= tx <= 1050 and 320 <= ty <= 365 and 1410 <= px <= 1480 and 500 <= py <= 570):
            return None
        return paste

    def _strategy_code_text_state(self, frame):
        """占位文字消失不等于成功，须在输入区域读到配置码的连续片段。"""
        if self._strategy_code_controls(frame) is None:
            return "unknown"
        field = frame.crop((445, 430, 1395, 635))
        if self._locate_page_template(CWIMG.STRATEGY_CODE_PLACEHOLDER, field) is not None:
            return "empty"
        rows = self._vision._engine_ocr(field, minimum_confidence=0.7)
        for row in rows or ():
            if not isinstance(row, (list, tuple)) or len(row) != 3:
                continue
            if (not isinstance(row[1], str) or not isinstance(row[2], (int, float))
                    or isinstance(row[2], bool) or not 0.7 <= row[2] <= 1):
                continue
            text = re.sub(r"\s", "", row[1])
            # 只证明配置码已经可见；游戏是否接受仍由后续应用结果认证。
            if any(text[i:i + 12] in self.strategy_code for i in range(len(text) - 11)):
                return "visible"
        return "unknown"

    def handle_game_entered(self) -> bool:  # NOQA  # 保留原有静态检查指令。
        """初始化前应用新局攻略；开局重刷钩子保持独立。"""
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
            # 实际成功流程在 HOT_STRATEGIES 未出现时已显示口令输入按钮。
            # 仅在需要时才导航。
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
            frame = self._capture_page_frame()
            paste = self._strategy_code_controls(frame)
            if paste is None:
                return self._fail_startup("strategy_code_dialog_unconfirmed", "攻略码标题与游戏粘贴按钮未确认")
            step = "paste_code"
            self._check_stop()
            self.operator.copy(self.strategy_code)
            self._check_stop()
            if not self.operator.click_box(paste, after_sleep=0.5):
                return self._fail_startup("strategy_code_paste_failed", "游戏粘贴按钮点击失败")
            # 只粘贴一次，有限读取新的字段截图；未知或空白不能授权提交。
            for _ in range(3):
                frame = self._capture_page_frame()
                state = self._strategy_code_text_state(frame)
                self._check_stop()
                if state == "visible":
                    break
                self.operator.sleep(0.3)
            else:
                return self._fail_startup("strategy_code_empty" if state == "empty" else
                    "strategy_code_text_unconfirmed", "攻略码字段文字未确认，禁止提交")

            step = "confirm_code"
            confirm = self._locate_page_template(IMG.ENSURE2, frame)
            self._check_stop()
            if confirm is None or not self.operator.click_box(confirm, after_sleep=1):
                return self._fail_startup("strategy_code_confirm_failed", "攻略码提交失败")
            step = "apply_strategy"
            apply = self.operator.wait_img(CWIMG.APPLY_STRATEGY, timeout=self.ENTRY_TRANSITION_TIMEOUT)
            self._check_stop()
            if apply is None or not self.operator.click_box(apply, after_sleep=1):
                return self._fail_startup("strategy_apply_failed", "未能应用分享码对应攻略")
            # 已有的“取消应用”图像是攻略已应用的明确证据；
            # 仅发送点击或按钮消失都不是。
            if not self._confirm_startup_images((self.STRATEGY_APPLIED_IMAGE,),
                                                self.ENTRY_TRANSITION_TIMEOUT):
                return self._fail_startup("strategy_apply_unconfirmed", "攻略应用结果未确认")

            step = "return_to_preparation"
            if self._return_to_startup_preparation():
                logger.info("[启动流程] 攻略已应用并返回准备界面")
                return True
            return self._fail_startup("strategy_return_unconfirmed", "应用攻略后未能确认准备界面")
        except ThreadStoppedError:
            raise
        except Exception as error:
            return self._fail_startup("strategy_import_error",
                                      f"攻略导入异常，步骤={step}：{error}")

    def _startup_equipment_tracking_close(self, frame):
        """只返回同一帧中与此弹窗标题配对的关闭控件。"""
        self._check_stop()
        if frame is None or tuple(frame.size) != (
                self.operator.window_context.width, self.operator.window_context.height):
            return None
        title = self._locate_page_template(CWIMG.EQUIPMENT_TRACKING_TITLE, frame)
        if title is None:
            return None
        close = self._locate_page_template(CWIMG.EQUIPMENT_TRACKING_CLOSE, frame)
        if close is None:
            return None
        width, height = frame.size
        tx, ty = title.center
        cx, cy = close.center
        # 关闭按钮必须属于同一标题栏，且位于标题右侧。
        # 屏幕其他位置的普通叉号不能作为点击依据。
        if not (0.25 * width <= tx <= 0.42 * width
                and 0.15 * height <= ty <= 0.38 * height
                and 0.30 * width <= cx - tx <= 0.48 * width
                and abs(cy - ty) <= 0.035 * height):
            return None
        self._check_stop()
        return close

    def _startup_return_phase(self, frame):
        """在当前同一帧中核实两个准备页控件，并明确排除遮挡弹窗。

        此处不进行文字识别、额外截图、模板操作器等待或界面输入。
        左上退出图标也会出现在准备页，因此不能单独用作排除条件。
        """
        self._check_stop()
        if frame is None or tuple(frame.size) != (
                self.operator.window_context.width, self.operator.window_context.height):
            return "unknown"
        locate = lambda template: self._locate_page_template(template, frame)
        # 这些标签属于确认或退出弹窗；即使后方仍显示准备页控件，
        # 也不能据此启动流程或再次按下退出键。
        for template in (IMG.ENSURE, IMG.ENSURE2, CWIMG.CONFIRM_SELECTION,
                         CWIMG.WITHDRAW_AND_SETTLE):
            if locate(template) is not None:
                return "blocked"
        # 应用攻略后，离开攻略页面时可能弹出装备追踪窗口。
        # 弹窗后方可见的准备页控件不能证明已返回准备页。
        if locate(CWIMG.EQUIPMENT_TRACKING_TITLE) is not None:
            return ("equipment_tracking"
                    if self._startup_equipment_tracking_close(frame) is not None else "blocked")
        # 攻略导航的每一层都必须有明确的页面身份。
        # 未知页面和退出菜单不接收试探性的退出按键。
        for template in (self.STRATEGY_APPLIED_IMAGE, CWIMG.ENTER_STRATEGY_CODE,
                         CWIMG.HOT_STRATEGIES, CWIMG.BACK_PREPARE_PAGE,
                         CWIMG.APPLY_STRATEGY):
            if locate(template) is not None:
                return "strategy"
        if locate(CWIMG.PREPARATION_STAGE) is None:
            return "unknown"
        if locate(CWIMG.BATTLE) is not None or locate(CWIMG.FOLD) is not None:
            return "preparation"
        return "unknown"

    def _return_to_startup_preparation(self):
        """以两张新鲜帧确认准备页，避免使用固定三秒的轮询分段。

        总预算限制后续观测与导航；预算内开始的第二次有效读取，
        可以完成准备页确认。超过截止时间后不能授权输入或第三次截图。
        """
        started = time.monotonic()
        deadline = started + self.ENTRY_TRANSITION_TIMEOUT
        previous, stable, escapes, frames, misses = None, 0, 0, 0, 0
        tracking_closes = 0
        slowest = 0.0
        while time.monotonic() < deadline:
            self._check_stop()
            observed_at = time.monotonic()
            frame = self._capture_page_frame()
            phase = self._startup_return_phase(frame)
            self._check_stop()
            now = time.monotonic()
            frames += 1
            slowest = max(slowest, now - observed_at)
            stable = stable + 1 if phase == previous else 1
            previous = phase
            if phase == "preparation" and stable >= 2:
                if now - started >= 3 or misses or tracking_closes:
                    logger.info(f"[启动返回确认] 结果=confirmed 帧数={frames} "
                                f"Esc={escapes} 追踪关闭={tracking_closes} 耗时={now - started:.2f}s "
                                f"最慢帧={slowest:.2f}s")
                return True
            if now >= deadline:
                break
            if phase == "equipment_tracking":
                if stable >= 2 and tracking_closes == 0:
                    close = self._startup_equipment_tracking_close(frame)
                    self._check_stop()
                    if time.monotonic() >= deadline:
                        break
                    if close is not None:
                        tracking_closes += 1
                        if not self.operator.click_box(close):
                            logger.warning("[启动返回确认] 结果=tracking_close_failed")
                            return False
                        logger.info("[启动返回确认] 已确认装备追踪弹窗，尝试关闭一次；重新观察准备界面")
                        previous, stable = None, 0
                        self.operator.sleep(min(0.5, max(0, deadline - time.monotonic())))
                        continue
                # 同一弹窗持续存在或再次出现时，不重复发送关闭输入。
                misses += 1
                self.operator.sleep(min(0.2, max(0, deadline - time.monotonic())))
                continue
            if phase == "strategy" and stable >= 2:
                if escapes >= 3:
                    break
                self._check_stop()
                if time.monotonic() >= deadline:
                    break
                if not self.operator.press_key("esc"):
                    logger.warning(f"[启动返回确认] 结果=escape_failed 帧数={frames} "
                                   f"Esc={escapes} 耗时={time.monotonic() - started:.2f}s")
                    return False
                escapes += 1
                previous, stable = None, 0
                self.operator.sleep(min(0.5, max(0, deadline - time.monotonic())))
            elif phase not in ("preparation", "strategy"):
                misses += 1
                # 仅在观测失败或受阻时退避；成功的双帧确认路径
                # 不额外等待，也不依赖后续输入才被接受。
                self.operator.sleep(min(0.2, max(0, deadline - now)))
        self._check_stop()
        logger.warning(f"[启动返回确认] 结果=unconfirmed 阶段={previous} 帧数={frames} "
                       f"连续证据={stable} Esc={escapes} 追踪关闭={tracking_closes} "
                       f"耗时={time.monotonic() - started:.2f}s 最慢帧={slowest:.2f}s")
        return False

    def _confirm_startup_images(self, templates, timeout):
        """要求两次新鲜的明确观测，不再发送输入。"""
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

    def handle_game_initialized(self) -> bool:  # NOQA  # 保留原有静态检查指令。
        """对局初始化完成后的处理逻辑，默认不操作；子类可重写以添加逻辑。
        在角色放置和备战席识别完成后、正式进入游戏循环前调用。
        返回值：True 表示继续游戏循环，False 表示中止进入流程。
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
        """打开经济运营商店前，先解决不完整的棋盘证据。"""
        self._complete_incremental_field_observation()
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
            # 使用准备阶段已有的恢复额度；首个主力
            # 仍可能尚未获得，只要求已有证据明确。
            if not self._resume_shopping_after(ShoppingResult(
                    ActionResult.INDETERMINATE, reason="purchase_targets_unknown")):
                return False

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

    # ssyb：购物离开后的恢复仍须核对当前页面和交易证据。
    def _resume_shopping_after(self, result):
        """继续同一购物额度前，重新观测缺失证据。"""
        if getattr(result, "confirmed_purchases", 0) > 0:
            self._post_purchase_placement_pending = True
        if (result.reason == "purchase_evidence_unknown" and not self._purchase_pending_names
                and getattr(result, "attempted_purchases", 0) == 0):
            logger.warning("[购前识别] 未发送购买输入，结束本轮购物并继续整备；原因=" + result.reason)
            return False
        if result.reason in {"economy_evidence_not_confirmed", "shop_not_open",
                             "final_round_page_unknown"} and not self._purchase_pending_names:
            self._record_observation_issue(result.reason,
                "本轮购物证据不足，保留余额并继续已确认棋盘的整备，后续准备阶段重新读取")
            return False
        if result.reason == "shopping_evidence_deferred":
            if self._purchase_pending_names:
                raise RuntimeError("购后动作尚未确认，不能降级跳过："
                                   + ",".join(sorted(self._purchase_pending_names)))
            return False
        if result.reason in {"unknown_coins", "unknown_coins_after_refresh",
                "economy_gold_not_confirmed", "unknown_xp_cost", "unknown_roll_cost",
                "unknown_action_cost", "experience_no_progress", "refresh_no_progress",
                "final_round_refresh_not_confirmed"}:
            if self._purchase_pending_names:
                attempts = getattr(self, "_economy_recovery_attempts", 0)
                if attempts < self.preparation_budget["recoveries"]:
                    self._economy_recovery_attempts = attempts + 1
                    self._recover_preparation_observations("purchase_recheck_unknown")
            logger.warning(f"[金币校验] 本轮消费结束：{result.reason}；记录错误，继续整备和后续任务")
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
                # 已发送购买输入必须结清观测；不能把未确认合成或落位
                # 当作可跳过的优化。仅纯识别不足允许转入整备门槛。
                if self._purchase_pending_names or result.reason in {
                        "purchase_recheck_unknown", "purchase_evidence_unknown"}:
                    raise RuntimeError("购后证据恢复无进展：" + result.reason
                                       + "；当前缺口=" + self._shopping_evidence_gaps())
                logger.warning("[购物恢复] 补读额度已用完，暂停消费并转入整备："
                               + result.reason + "；当前缺口=" + self._shopping_evidence_gaps())
                return False
            self._economy_recovery_attempts = attempts + 1
            logger.info(f"[购物恢复] 原因={result.reason} 补读={attempts + 1}，沿用本准备期购物额度")
            self._check_stop()
            if not self._set_shop_open(False):
                raise RuntimeError("购物恢复未确认准备界面")
            self._invalidate_level()
            if result.reason == "upgrade_gate_unknown":
                from .silver_wolf_fee_recovery import recover_unknown_silver_wolf_fee
                if recover_unknown_silver_wolf_fee(self, result,
                        battle_template=CWIMG.BATTLE, stop_type=ThreadStoppedError, logger=logger):
                    return True
            if result.reason == "final_round_unknown":
                self._round_read_attempts = 0
            if not self._layout_valid or self._backend_unknown_slots:
                logger.info("[购物恢复] 后台布局失效，先重新确认完整布局和角色")
                self.refresh_backend_character(equip=False, recover_layout=True)
                if not self._layout_valid:
                    # 后续有界恢复可以重试布局；
                    # 读取单个槽位不能修复缺失的布局证据。
                    logger.warning("[购物恢复] 后台布局仍未确认，保留未知状态等待下一次恢复")
                    return True
            for area in ("on_field", "off_field"):
                for i, obs in enumerate(self._observations[area]):
                    if obs.state == SlotState.UNKNOWN or (obs.character is not None
                            and not obs.character.is_npc and obs.stars is None):
                        self._dirty_slots.add((area, i))
            self._refresh_dirty_field()
            if self._bench_dirty or any(o.state == SlotState.UNKNOWN for o in self._observations["in_hand"]):
                self.get_in_hand_area(True)
            return True
        if (self.economy_config is None and self._preparation_round != (3, 7)
                and not result.reason.startswith("final_round_")):
            if result.result != ActionResult.CONFIRMED:
                raise RuntimeError("购物动作未确认：" + result.reason)
            return False
        if result.reason not in prepare_reasons:
            if result.result != ActionResult.CONFIRMED:
                raise RuntimeError("购物动作未确认：" + result.reason)
            return False
        before = self._preparation_recovery_signature()
        recovered = self.prepare_for_battle()
        if recovered.state == Readiness.BLOCKED:
            self._fail_battle("preparation_" + recovered.reason)
        self._check_stop()
        if getattr(self, "_purchase_finish_used", False) or self._preparation_budget_spent():
            # 完成已确认阵容的整理后，结束本回合购物。
            return False
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
        """一张帧属于一次观测流程，绝不沿用到下一输入动作。"""
        self._check_stop()
        self._page_match_frame = None
        self._page_match_results = {}
        self._page_match_pixels = {}
        self._vision._terminal_action_frame = None
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
        if getattr(self, "_page_match_frame", None) is not frame:
            self._page_match_frame = frame
            self._page_match_results = {}
            self._page_match_pixels = {}
        # 自有图片读取错误仍直接报告；非自有路径错误保持原匹配失败语义。
        image = load_template(template)
        try:
            import pyscreeze
            grayscale = pyscreeze.GRAYSCALE_DEFAULT
            version = template_cache_key(template)
        except ThreadStoppedError:
            raise
        except Exception:
            return None
        # 文件版本变更立即失效。此结果缓存最多属于一张截图，包含未命中结果。
        key = (version, self.operator.tm_confidence, grayscale)
        if version is not None and key in self._page_match_results:
            match = self._page_match_results[key]
            self._check_stop()
            return Box(*match, source=template) if match is not None else None
        try:
            haystack = frame
            if getattr(pyscreeze, "_useOpenCV", False):
                if grayscale not in self._page_match_pixels:
                    self._page_match_pixels[grayscale] = pyscreeze._load_cv2(frame, grayscale)
                haystack = self._page_match_pixels[grayscale]
                image = load_match_template(template, grayscale)
                match = locate_first(image, haystack, confidence=self.operator.tm_confidence)
            else:
                match = pyscreeze.locate(image, haystack,
                    confidence=self.operator.tm_confidence)
        except ThreadStoppedError:
            raise
        except pyscreeze.ImageNotFoundException:
            match = None
        except Exception:
            return None
        self._check_stop()
        if version is not None:
            self._page_match_results[key] = match
        return Box(*match, source=template) if match is not None else None

    def _runtime_advance_candidate(self, frame=None, *, allow_ocr=True):
        """识别导航标签，绝不识别任意可点击的商店选项。"""
        for template, label in ((CWIMG.CLICK_BLANK, "点击空白处关闭"),
                                (CWIMG.NEXT_STEP, "下一步")):
            self._check_stop()
            box = self._locate_page_template(template, frame)
            if box is not None:
                return label, box
        if not allow_ocr:
            return None
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
                    # 遵循 operator.ocr_boxes 的严格置信度阈值，
                    # 也适用于返回未过滤旧式元组的引擎。
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

    def _observe_page_frame(self, frame, *, ignore_pending_equipment=False,
                            ignore_pending_selection=False, full_navigation=True):
        """同帧只读分类：终局、阻挡弹窗、节点、底层页面依次认证。

        pending 的忽略开关仅用于各自确认循环读取退场证据；普通入口
        不得忽略未完成的输入，也不得在截图失败后拼接多张帧的命中结果。
        """
        self._check_stop()
        if frame is None:
            return "unknown", None
        window = self.operator.window_context.width, self.operator.window_context.height
        if tuple(frame.size) != window:
            return "unknown", None
        # 高频商店确认只对终局模板候选执行结果 OCR。所有终局认证本就
        # 依赖这四个按钮，快检只减少 OCR，不会由孤立按钮授权终局输入。
        terminal_candidate = full_navigation or any(
            self._vision._terminal_template_point(frame, name) is not None
            for name in ("settle.png", "next_page.png", "back_currency_wars.png", "next_step.png"))
        screen = self._vision.read_battle_screen(frame) if terminal_candidate else None
        if screen is not None and screen.state in TERMINAL_STATES:
            return "terminal", screen
        equipment_choice = self._read_equipment_choice(frame)
        if equipment_choice is not None and equipment_choice.matched:
            return "equipment_choice", equipment_choice
        if self._equipment_choice_pending is not None and equipment_choice is None:
            # 识别失败不能证明已离开弹窗，包括专门的退场确认循环。
            return "unknown", None
        if self._equipment_choice_pending is not None and not ignore_pending_equipment:
            # 选择输入未完成认证时，露出的底层按钮不能恢复普通流程。
            return ("equipment_choice", equipment_choice) if (
                equipment_choice is not None and not equipment_choice.present) else ("unknown", None)
        if equipment_choice is not None and equipment_choice.present:
            return "unknown", None
        if self._locate_page_template(CWIMG.SELECT_SIMPLE_EQUIPMENT, frame) is not None:
            return "unknown", None  # 简易奖励装备仍覆盖底层节点/准备页。
        blank = self._locate_page_template(CWIMG.CLICK_BLANK, frame)
        if blank is not None:
            return "advance", ("点击空白处关闭", blank)
        # 投资策略自身具有确认按钮；完整标题须先于通用未知选择阻挡判定。
        if self._locate_page_template(CWIMG.SELECT_INVEST_STRATEGY, frame) is not None:
            return "node", CWIMG.SELECT_INVEST_STRATEGY
        event = self.detect_special_event(frame)
        if event:
            return "selection_event", event
        for node in (CWIMG.ENCOUNTER_NODE, CWIMG.REPLENISH_STAGE, CWIMG.FORTUNE_TELLER):
            if self._locate_page_template(node, frame) is not None:
                return "node", node
        if self._locate_page_template(CWIMG.CONFIRM_SELECTION, frame) is not None:
            return "unknown", None  # 未识别的选择弹窗不能透传底层准备按钮。
        if self._selection_event_pending is not None and not ignore_pending_selection:
            return "unknown", None
        probability_close = self._read_shop_probability_overlay(frame)
        if probability_close is not None:
            return "shop_probability", probability_close
        if screen is not None and screen.state in ("result_ready", "result_animation"):
            return "settlement", screen
        if self._locate_page_template(CWIMG.CONTINUE, frame) is not None:
            return "settlement", None
        if self._locate_page_template(CWIMG.SETTLE, frame) is not None:
            return "settlement", None
        if self._combat_screen_confirmed(frame):
            return "combat", None
        if self._locate_page_template(CWIMG.START_CURRENCY_WARS, frame) is not None:
            return "main_menu", None
        if self._locate_page_template(CWIMG.BOSS_PREVIEW, frame) is not None:
            return "boss_preview", None
        if self._locate_page_template(DUIMG.BONUS_POINTS, frame) is not None:
            return "bonus_points", None
        # 首领等专用页面先于通用“下一步”，保留各自初始化钩子。
        # 常规商店操作不扫描大范围导航文字；不能确认时交给有界恢复。
        advance = self._runtime_advance_candidate(frame, allow_ocr=full_navigation)
        if advance is not None:
            return "advance", advance
        fold = self._locate_page_template(CWIMG.FOLD, frame)
        if fold is not None:
            return "preparation", fold
        if any(self._locate_page_template(template, frame) is not None
               for template in (CWIMG.PREPARATION_STAGE, CWIMG.BATTLE)):
            return "preparation", None
        if self._locate_page_template(IMG.ENTER, frame) is not None:
            return "entry", None
        return "unknown", None

    def _confirmation_outside_event_button(self, template, frame, event_button):
        """排除同一事件按钮的子图后，检查是否另有独立确认按钮。"""
        self._check_stop()
        try:
            import pyscreeze
        except ImportError:
            return True
        try:
            image = load_match_template(template, pyscreeze.GRAYSCALE_DEFAULT)
            haystack = self._page_match_pixels.get(pyscreeze.GRAYSCALE_DEFAULT, frame)
            for match in pyscreeze.locateAll(image, haystack,
                    confidence=self.operator.tm_confidence):
                self._check_stop()
                x, y, width, height = match
                if not (event_button.left <= x and event_button.top <= y
                        and x + width <= event_button.left + event_button.width
                        and y + height <= event_button.top + event_button.height):
                    return True
            return False
        except (ThreadStoppedError, InterruptedError):
            raise
        except pyscreeze.ImageNotFoundException:
            return False
        except Exception:
            return True  # 完整匹配结果不可用时，继续阻挡。

    def _observe_selection_return(self, frame, *, full_navigation=False):
        """观测事件是否离开，避免旧收据遮蔽准备页证据。

        仅确认与恢复调用方可以忽略旧收据；可见的确认、退出和装备
        追踪弹窗仍会遮挡后方准备页控件。本方法不发送任何输入。
        """
        self._check_stop()
        if frame is None:
            return "unknown", None
        for template in (CWIMG.WITHDRAW_AND_SETTLE, CWIMG.EQUIPMENT_TRACKING_TITLE):
            if self._locate_page_template(template, frame) is not None:
                return "unknown", None
        confirmations = [box for template in (IMG.ENSURE, IMG.ENSURE2)
                         if (box := self._locate_page_template(template, frame)) is not None]
        if confirmations:
            event_button = self._locate_page_template(CWIMG.CONFIRM_SELECTION, frame)
            # “确认”是“确认选择”的子图。只有同一按钮内的命中才可交给
            # 完整页面识别；另一个位置的确认弹窗依然阻挡，不能透传准备页。
            if event_button is None or any(not (
                    event_button.left <= box.left
                    and event_button.top <= box.top
                    and box.left + box.width <= event_button.left + event_button.width
                    and box.top + box.height <= event_button.top + event_button.height)
                    for box in confirmations):
                return "unknown", None
            if any(self._confirmation_outside_event_button(template, frame, event_button)
                   for template in (IMG.ENSURE, IMG.ENSURE2)):
                return "unknown", None
        observed = self._observe_page_frame(frame, ignore_pending_selection=True,
                                             full_navigation=full_navigation)
        if confirmations and observed[0] != "selection_event":
            return "unknown", None  # 按钮重叠不能代替精确事件标题认证。
        return observed

    def _probe_runtime_page(self, *, ignore_pending_selection=False):
        """重新开始页面分类，不重置当前对局或准备预算。"""
        frame = self._capture_page_frame()
        if ignore_pending_selection:
            return self._observe_selection_return(frame, full_navigation=True)
        return self._observe_page_frame(frame)

    def _page_navigation_limit(self, seconds, deadline=None):
        """嵌套导航共享调用方剩余额度，不能重新取得完整等待时间。"""
        limits = [time.monotonic() + seconds]
        limits.extend(value for value in (deadline, getattr(self, "_page_navigation_deadline", None))
                      if value is not None)
        context = getattr(self, "_startup_recovery_context", None)
        if context is not None and context["active"] and not getattr(self, "_startup_recovery_paused", False):
            limits.append(context["deadline"])
        return min(limits)

    @contextmanager
    def _page_navigation_scope(self, deadline):
        previous = getattr(self, "_page_navigation_deadline", None)
        self._page_navigation_deadline = min(previous, deadline) if previous is not None else deadline
        try:
            yield self._page_navigation_deadline
        finally:
            self._page_navigation_deadline = previous

    def _check_page_navigation_deadline(self, deadline=None):
        self._check_stop()
        limits = [deadline, getattr(self, "_page_navigation_deadline", None)]
        context = getattr(self, "_startup_recovery_context", None)
        if context is not None and context["active"] and not getattr(self, "_startup_recovery_paused", False):
            limits.append(context["deadline"])
        if any(limit is not None and time.monotonic() >= limit for limit in limits):
            raise RuntimeError("页面导航额度已耗尽，保留待确认状态并停止发送输入")

    def _handle_page_overlay(self, observed, deadline):
        """调用者已用两张新鲜帧确认的弹窗；输入之后由调用者重新分类。"""
        self._check_stop()
        deadline = self._page_navigation_limit(self.EVENT_TRANSITION_TIMEOUT, deadline)
        if time.monotonic() >= deadline:
            return False
        phase, payload = observed
        if phase == "equipment_choice":
            return self._handle_equipment_choice(payload, deadline)
        if phase == "selection_event":
            with self._page_navigation_scope(deadline):
                if not self.special_events[payload][1]():
                    return False
            self._coin_action_costs.clear()
            self._equipment_dirty = True
            return True
        if phase == "shop_probability":
            return self.operator.click_point(*payload, after_sleep=0.5,
                                              tag="恢复：关闭商店刷新概率")
        return False

    @staticmethod
    def _same_runtime_page(first, second):
        if first[0] != second[0] or first[0] == "unknown":
            return False
        if first[0] == "advance":
            a, b = first[1], second[1]
            return a[0] == b[0] and max(abs(x - y) for x, y in zip(a[1].center, b[1].center)) <= 24
        if first[0] == "shop_probability":
            return max(abs(a - b) for a, b in zip(first[1], second[1])) <= 0.005
        if first[0] == "equipment_choice":
            return same_equipment_choice(first[1], second[1]) or (
                first[1] is not None and second[1] is not None
                and not first[1].present and not second[1].present)
        return first[1] == second[1] if first[0] in ("node", "selection_event") else True

    def _record_runtime_node_input(self, node):
        """紧接改变节点的输入前记账；读取失败不构成已尝试输入。"""
        if self._runtime_node_pending is not None:
            raise RuntimeError("节点已有待确认输入，禁止重复选择")
        self._runtime_node_pending = node
        self._runtime_node_receipt = dict(node=node, selection_attempted=True,
            selection_returned=False, confirmation_attempted=False)

    def _accept_runtime_node_departure(self, first, current):
        """仅由两张新鲜、稳定的下一页面证据解除旧节点收据。"""
        if not self._same_runtime_page(first, current):
            return
        phase, payload = current
        event_receipt = self._selection_event_pending
        if (event_receipt is not None and phase == "selection_event"
                and payload != event_receipt[0]):
            logger.info(f"[事件交接] 双帧确认 {event_receipt[0]} -> {payload}，结束旧收据并重新选择新事件")
            self._selection_event_pending = None
            self._last_selection_sent = False
        pending = self._runtime_node_pending
        if pending is None:
            return
        departed = (phase in {"preparation", "main_menu", "terminal", "combat", "settlement"}
                    or (phase == "node" and payload != pending)
                    or (phase == "selection_event" and
                        (pending != CWIMG.FORTUNE_TELLER or payload != "命运卜者")))
        if not departed:
            return
        self._runtime_node_pending = None
        self._invest_simple_equipment_pending = False
        if (pending == CWIMG.FORTUNE_TELLER and self._selection_event_pending is not None
                and self._selection_event_pending[0] == "命运卜者"):
            self._selection_event_pending = None
        if self._selection_event_pending is None:
            self._last_selection_sent = False
        logger.info(f"[节点退场] 已连续两帧确认阶段={phase}，解除节点输入收据={pending}")

    def _recover_runtime_flow(self, error, attempt=1):
        """有界的页面恢复：仅执行导航，保留进行中的动作。"""
        self._check_stop()
        clock = getattr(self, "_battle_wait_clock", None)
        if (self._pending_battle_id and clock is not None and clock[0] == self._pending_battle_id
                and time.monotonic() - clock[1] >= self.BATTLE_MAX_WAIT_SECONDS):
            logger.warning("[流程恢复] 同一战斗总等待上限已到，不重置计时或重复发送战斗输入")
            return False
        logger.warning(f"[流程恢复] 第{attempt}次，从当前画面重新定位：{error}")
        self._vision.capture_sample("runtime_recovery", {"evidence": str(error)[:240]}, critical=True)
        recovery_started = time.monotonic()
        deadline = recovery_started + self.FLOW_RECOVERY_SECONDS
        old_deadlines = self._preparation_deadline, self._formation_deadline
        battle_before_recovery = self._last_completed_battle_id
        # 页面导航使用独立边界，不能重置准备阶段预算。
        self._preparation_deadline = self._formation_deadline = None
        actions = {}
        try:
            for _ in range(self.FLOW_RECOVERY_STEPS):
                self._check_stop()
                if time.monotonic() >= deadline:
                    break
                # 重新观测已发送选择的结果，不重放输入；旧收据
                # 不能遮蔽证明事件离开的两张准备页截图，
                # 普通页面探测仍保留待确认输入的保护。
                probe_options = ({"ignore_pending_selection": True}
                                 if self._selection_event_pending is not None else {})
                first = self._probe_runtime_page(**probe_options)
                self.operator.sleep(0.3)
                current = self._probe_runtime_page(**probe_options)
                if not self._same_runtime_page(first, current):
                    continue
                phase, payload = current
                if phase != "terminal" and time.monotonic() >= deadline:
                    break
                self._accept_runtime_node_departure(first, current)
                logger.info(f"[流程恢复] 已定位阶段={phase}")
                if phase == "selection_event":
                    key = "selection_event:" + payload
                    if actions.get(key, 0) >= 1:
                        break
                    actions[key] = 1
                    if not self._handle_page_overlay(current, deadline):
                        return False
                    self._coin_action_costs.clear()
                    self._equipment_dirty = True
                    continue  # 必须重新定位，不能把露出的准备按钮当作退场。
                if phase == "equipment_choice":
                    actions[phase] = actions.get(phase, 0) + 1
                    if not self._handle_equipment_choice(payload, deadline):
                        return False
                    continue
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
                    if self._selection_event_pending is not None:
                        event, target = self._selection_event_pending
                        self._check_stop()
                        self._selection_event_pending = None
                        self._last_selection_sent = False
                        logger.info(f"[事件恢复] 事件={event} 已连续两帧确认返回准备界面，"
                                    f"清除待确认选择={target!r}，不重复选择")
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
                        and not any(action not in {"shop_probability", "equipment_choice"}
                                    and not action.startswith("selection_event:")
                                    for action in actions))
                    if same_preparation:
                        logger.info("[准备恢复] 仍在同一准备期，保留已完成收集和可靠槽位，只补读缺口")
                        if self._purchase_pending_names:
                            # 输入可能成功，而其后确认失败。
                            # 即使尚未记录脏状态，也要重新检查可能发生的合成。
                            self._bench_dirty = True
                            self._dirty_slots.update((area, index)
                                for area in ("on_field", "off_field")
                                for index, obs in enumerate(self._observations[area])
                                if obs.character is not None
                                and obs.character.name in self._purchase_pending_names)
                    else:
                        # 战斗、奖励节点或页面推进都可能改变角色列表。
                        self._preparation_rewards_collected = False
                        self._preparation_round = None
                        self._round_read_attempts = 0
                        self._invalidate_roster_evidence("runtime_context_changed")
                    # 原流程已失败且连续两帧确认准备界面；错误名称不应
                    # 再挡住提示检查。先查提示，避免商店状态确认提前跳过。
                    bench_recovered = self._recover_full_bench_failure(error, deadline)
                    if bench_recovered is False:
                        return False
                    # 满员分支已经完成页面、库存和场上复核；耗时扫描后
                    # 不再用过期的导航额度否定其成功结果。
                    if bench_recovered is not True and not self._set_shop_open(False, deadline=deadline):
                        continue
                    if not self._layout_valid:
                        self.refresh_backend_character(equip=False, recover_layout=True)
                        if not self._layout_valid:
                            return False
                    self._runtime_node_pending = None
                    self._selection_event_pending = None
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
                    # 真实战斗可能持续超过短暂的页面导航预算。
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
                    if self._runtime_node_pending == payload:
                        # 已尝试的选择不重放；有独立按钮时仅沿用合法确认。
                        if actions.get(payload, 0) < 1:
                            actions[payload] = 1
                            with self._page_navigation_scope(deadline):
                                if (payload == CWIMG.FORTUNE_TELLER
                                        and self._selection_event_pending is not None):
                                    event, target = self._selection_event_pending
                                    self._confirm_selection_event(target, event, deadline=deadline)
                                elif payload == CWIMG.SELECT_INVEST_STRATEGY:
                                    self._confirm_invest_strategy(deadline)
                                elif payload in (CWIMG.ENCOUNTER_NODE, CWIMG.REPLENISH_STAGE):
                                    receipt = getattr(self, "_runtime_node_receipt", None)
                                    logger.warning(f"[节点待确认] {payload} 收据={receipt}；缺少可靠选中态证据，只观察退场")
                                    self._vision.capture_sample("node_confirmation_evidence_required",
                                        {"node": str(payload), "receipt": receipt,
                                         "required": "selected_state_and_enabled_confirmation"}, critical=True)
                        logger.warning("[流程恢复] 节点输入已尝试，仅观察退场，不重复选择")
                        continue
                    if actions.get(payload, 0) >= 1 or self._last_selection_sent:
                        logger.warning("[流程恢复] 选择动作尚未确认，保留现场，禁止重复选择")
                        continue
                    self._confirm_completed_battle("recovered_post_battle_node")
                    handlers = {CWIMG.ENCOUNTER_NODE: self.handle_encounter_node,
                        CWIMG.REPLENISH_STAGE: self.handle_replenish_stage,
                        CWIMG.FORTUNE_TELLER: self._handle_fortune_teller_after_battle,
                        CWIMG.SELECT_INVEST_STRATEGY: self.handle_invest_strategy}
                    actions[payload] = 1
                    with self._page_navigation_scope(deadline):
                        handlers[payload](None)
            self._vision.capture_sample("runtime_recovery_no_progress",
                {"evidence": "no_confirmed_preparation_or_terminal_after_bounded_recovery"}, critical=True)
            return False
        except (ThreadStoppedError, InterruptedError):
            raise
        except Exception as recovery_error:
            logger.warning(f"[流程恢复] 未能完成：{recovery_error}")
            return False
        finally:
            elapsed = time.monotonic() - recovery_started
            # 导航拥有独立的有限额度；保留剩余准备时间，
            # 但绝不能恢复已经耗尽的预算。
            self._preparation_deadline, self._formation_deadline = (
                value + elapsed if value is not None and value > recovery_started else value
                for value in old_deadlines)

    # Yukki：延迟续跑沿用本局收据，不重放旧输入。
    def _auto_resume_failed_flow(self, error):
        """重新启动当前页面恢复，保留对局、交易收据和同一战斗总计时。"""
        while self._auto_resume_attempts < len(self.AUTO_RESUME_DELAYS):
            self._check_stop()
            clock = getattr(self, "_battle_wait_clock", None)
            if (self._pending_battle_id and clock is not None
                    and clock[0] == self._pending_battle_id
                    and time.monotonic() - clock[1] >= self.BATTLE_MAX_WAIT_SECONDS):
                logger.warning("[自动续跑] 同一战斗等待总上限已到，保留存档后停止")
                return False
            delay = self.AUTO_RESUME_DELAYS[self._auto_resume_attempts]
            self._auto_resume_attempts += 1
            logger.warning(f"[自动续跑] 第{self._auto_resume_attempts}/{len(self.AUTO_RESUME_DELAYS)}轮，"
                           f"等待{delay}秒后重新定位当前对局：{error}")
            started = time.monotonic()
            old_deadlines = self._preparation_deadline, self._formation_deadline
            try:
                for _ in range(delay):
                    self._check_stop()
                    self.operator.sleep(1)
                self._check_stop()
            finally:
                elapsed = time.monotonic() - started
                self._preparation_deadline, self._formation_deadline = (
                    value + elapsed if value is not None and value > started else value
                    for value in old_deadlines)
            # 不调用 start_game/reset_character：未确认输入仍由原来的收据核验。
            if self._recover_runtime_flow(error, self.FLOW_RECOVERY_ATTEMPTS + self._auto_resume_attempts):
                self._record_checkpoint(execution_status="running")
                logger.info("[自动续跑] 当前页面已确认，继续原对局；无进展重试次数仍保留")
                return True
        logger.error("[自动续跑] 同一处故障的续跑轮次已用完，保留诊断与存档")
        return False

    def handle_next_step(self, _previous=None):
        # NEXT_STEP 由开局、过渡和终局页面共用；
        # 只有终局识别器可以将它解释为对局结果。
        screen = self._vision.read_battle_screen()
        if screen.state in TERMINAL_STATES:
            return self.handle_game_over(None, first_screen=screen)
        self._check_page_navigation_deadline()
        first = self.operator.locate(CWIMG.NEXT_STEP, trace=False)
        self.operator.sleep(0.3)
        second = self.operator.locate(CWIMG.NEXT_STEP, trace=False)
        self._check_page_navigation_deadline()
        if first is None or second is None or max(abs(x - y) for x, y in zip(first.center, second.center)) > 24:
            raise RuntimeError("下一步按钮尚未稳定")
        if not self.operator.click_box(second, after_sleep=0.5):
            raise RuntimeError("下一步按钮点击失败")
        return False

    def game_loop(self):
        first_preparation = self._confirmed_battle_count == 0
        recovery_attempts = (getattr(self, "_flow_recovery_attempts", 0)
                             if self._runtime_rebuild_active else 0)
        if not self._runtime_rebuild_active:
            self._auto_resume_attempts = 0
        self._flow_recovery_attempts = recovery_attempts
        try:
            while self.is_running and not self.is_game_over:
                battle_before = self._last_completed_battle_id
                try:
                    round_started = time.monotonic()
                    phase_before = dict(self.phase_seconds)
                    self._check_stop()
                    resuming_preparation = self._preparation_deadline is not None
                    self._begin_preparation()
                    self._reward_fast_active = bool(self.reward_fast_rounds
                        and not self._placement_pending and self._pending_move is None
                        and is_reward_fast_round(self.reward_fast_rounds, self._read_preparation_round()))
                    if self._reward_fast_active:
                        with self._timed("reward_fast_shopping"):
                            reward_shopping = self._reward_fast_shopping()
                        if reward_shopping.result != ActionResult.CONFIRMED:
                            raise RuntimeError("奖励回合自然商店未确认：" + reward_shopping.reason)
                        sale = SellResult(ActionResult.CONFIRMED, reason="reward_fast_deferred")
                    else:
                        if not self._preparation_rewards_collected:
                            with self._timed("crystals"):
                                self.harvest_crystals()
                        else:
                            logger.info("[准备恢复] 本准备期已收集水晶，跳过重复收集")
                        with self._timed("bench_scan"):
                            # 奖励可能改变任意备战区槽位；准备阶段内，
                            # 购买与移动已经标记其受影响证据。
                            if self._bench_dirty or self._bench_observed_at is None:
                                self.get_in_hand_area(True)
                        self._complete_incremental_field_observation()
                        if self._field_observed_at is None:
                            with self._timed("field_full_scan"):
                                self.refresh_character(equip=False)
                        elif not resuming_preparation:
                            # 60秒是逐槽检查点。局部复核已得到的新证据不因
                            # 较旧的整场扫描时间而被重复读取；后台结构仍取新双帧。
                            with self._timed("backend_layout_scan"):
                                self.refresh_backend_character(equip=False)
                            now = time.monotonic()
                            due = {("on_field", i) for i in range(len(self.on_field_area))
                                   if self._slot_needs_scan("on_field", i, now)}
                            self._dirty_slots.update(due)
                            logger.debug(f"[角色时效检查] 前台待补读={len(due)}，"
                                         f"检查点={self.preparation_budget['field_refresh_seconds']}秒")
                        if self._placement_pending and not self._resolve_pending_move():
                            recovered = self.prepare_for_battle()
                            if recovered.state == Readiness.BLOCKED:
                                self._fail_battle("preparation_" + recovered.reason)
                        with self._timed("dirty_field_scan"):
                            self._refresh_dirty_field()
                        if not self._layout_valid:
                            # 奖励会增加支援并移动整排后台；先重新建模，
                            # 再读取人口和选择攻略阶段。
                            self.refresh_backend_character(equip=False, recover_layout=True)
                        self._empty_roster_needs_shop = False
                        self.handle_characters_updated()
                        self.update_max_team_size()
                        with self._timed("placement"):
                            self.place_character()
                        with self._timed("selling"):
                            sale = self.sell_character()
                        if sale.attempted and sale.result != ActionResult.CONFIRMED:
                            raise RuntimeError("出售动作未确认：" + sale.reason)
                        # 开局保护也会在可用起手角色上场后，
                        # 从自然出现的第一个商店购买目标。
                        if (not first_preparation or self.opening_policy_config is not None
                                or self._read_preparation_round() in (None, (3, 7))):
                            shopping_passes = 0
                            while True:
                                with self._timed("shopping"):
                                    shopping_result = self.shopping()
                                if not self._resume_shopping_after(shopping_result):
                                    break
                                shopping_passes += 1
                                # 最终回合恢复受证据恢复边界限制，
                                # 绝不受攻略普通购物额度限制。
                                if (self._preparation_round is not None and self._preparation_round != (3, 7)
                                        and shopping_passes >= self.shopping_budget["actions"] + 1):
                                    break
                        with self._timed("preparation_confirmation"):
                            prepared = self.prepare_for_battle()
                        if prepared.state == Readiness.BLOCKED:
                            self._fail_battle("preparation_" + prepared.reason)
                        # 没有多余角色时，用缓存观测跳过本轮处理。
                        if not self._preparation_budget_spent() and self._needs_pre_battle_cleanup():
                            with self._timed("selling"):
                                final_sale = self.sell_character()
                            if final_sale.attempted and final_sale.result != ActionResult.CONFIRMED:
                                raise RuntimeError("出战前出售动作未确认：" + final_sale.reason)
                            sale = replace(final_sale, attempted=sale.attempted + final_sale.attempted,
                                           confirmed=sale.confirmed + final_sale.confirmed)
                            if final_sale.confirmed:
                                logger.info(f"[出战前余牌清理] 已确认出售={final_sale.confirmed}")
                            if self._preparation_round == (3, 7) and final_sale.confirmed:
                                # 最终回合新获得的金币仍使用相同的
                                # 累计购物限制与恢复处理来花费。
                                while True:
                                    with self._timed("shopping"):
                                        shopping_result = self.shopping()
                                    if not self._resume_shopping_after(shopping_result):
                                        break
                                with self._timed("preparation_confirmation"):
                                    prepared = self.prepare_for_battle()
                                if prepared.state == Readiness.BLOCKED:
                                    self._fail_battle("preparation_" + prepared.reason)
                        if not self._preparation_budget_spent() and self._equipment_due():
                            with self._timed("equipment"):
                                equipment_completed = self._process_equipment()
                                if self.equipment_interval_battles is not None and not equipment_completed:
                                    raise RuntimeError("装备批次中断，重新定位准备界面")
                                self._equipment_dirty = self._needs_equipment_check()
                            # 装备操作可能残留面板或使某一身份失效。
                            # 使用同一实际目标重新评估所有硬性门槛。
                            if (self.equipment_interval_battles is None
                                    and not self._set_shop_open(False)):
                                self._fail_battle("equipment_preparation_not_confirmed")
                            self._preparation_assessment_cache = None
                            final_ready = self._assess_preparation()
                            if final_ready.state == Readiness.BLOCKED:
                                final_ready = self.prepare_for_battle()
                                if final_ready.state == Readiness.BLOCKED:
                                    self._fail_battle("equipment_" + final_ready.reason)
                        elif self.equipment_interval_battles is not None and not self._preparation_budget_spent():
                            self._process_equipment()  # 记录跳过的区间，不打开面板。
                        if time.monotonic() >= self._preparation_deadline:
                            prepared = self.prepare_for_battle()
                            if prepared.state == Readiness.BLOCKED:
                                self._fail_battle("preparation_" + prepared.reason)
                    self._record_checkpoint(phase="ready", pending_actions=[])
                    completed = (self.battle(reward_fast=True) if self._reward_fast_active
                                 else self.battle())
                    if not completed:
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
                    self._flow_recovery_attempts = 0
                    self._auto_resume_attempts = 0
                except (ThreadStoppedError, InterruptedError):
                    raise
                except Exception as error:
                    if self._last_completed_battle_id != battle_before:
                        recovery_attempts = 0
                        self._flow_recovery_attempts = 0
                        self._auto_resume_attempts = 0
                    recovered = False
                    if recovery_attempts < self.FLOW_RECOVERY_ATTEMPTS:
                        recovery_attempts += 1
                        self._flow_recovery_attempts = recovery_attempts
                        recovered = self._recover_runtime_flow(error, recovery_attempts)
                    if not recovered and not self._auto_resume_failed_flow(error):
                        self._mark_runtime_rebuild_failure(error)
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
                        if self._last_completed_battle_id != battle_before:
                            recovery_attempts = 0
                            self._flow_recovery_attempts = 0
                            self._auto_resume_attempts = 0
                    # 带着相同待处理动作和额度重新进入页面检查。
                    # 仅到达准备页面不算进展。
        finally:
            if self._session_store is not None and not self._session_store.checkpoint.finalized:
                event = getattr(self.operator, "stop_event", None)
                self._record_execution_stop("stopped" if not self.is_running
                    or event is not None and event.is_set() else "error")
            # 符合外层交接条件时必须保留完整收据；此清理块返回后，
            # 旧任务不再执行任何界面输入。
            if self._runtime_flow_failure is None:
                self.reset_character()
        return True

    def refresh_character(self, equip=True, *, recover_layout=False):
        """刷新完整角色列表；局部布局恢复使用后台入口。"""
        self._check_stop()
        # 扫描前台前也须认证页面，否则概率弹窗
        # 可能使商店文本被误当成角色面板观测。
        if not self._set_shop_open(False):
            self._invalidate_backend_layout("preparation_not_confirmed")
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
        self.refresh_backend_character(equip=scan_equip, recover_layout=recover_layout,
                                       force_characters=True)
        if self._pending_move is None:
            self._placement_pending = False
        self._field_observed_at = time.monotonic()
        self._reconcile_placed()
        self._confirm_main_c_fielded()
        if equip:
            self._equipment_dirty = self._needs_equipment_check()

    def _invalidate_backend_layout(self, reason):
        """撤销动作所需的后台证据，保留历史仅供重建定位。"""
        self._layout_valid = False
        self._backend_layout_observed_at = None
        self._backend_identity_confirmed = False
        self._population_current = self._population_read_key = None
        self._effective_targets_key = None
        self._preparation_assessment_cache = None
        self._formation_plan = ()
        self._formation_plan_stage = None
        for i in range(len(self._observations["off_field"])):
            self._set_observation("off_field", SlotObservation(
                i, SlotState.UNKNOWN, evidence=reason))

    def refresh_backend_character(self, equip=False, *, recover_layout=False,
                                  force_characters=False):
        """每次认证布局/支援双帧，普通身份仅补读失效、过期或显式全扫槽。"""
        self._check_stop()
        if recover_layout or not self._layout_valid:
            # 普通恢复与备用恢复都必须先认证准备页面；
            # 隐藏的商店不能成为布局候选。
            if not self._set_shop_open(False):
                self._invalidate_backend_layout("layout_unconfirmed")
                self._vision.last_layout_diagnostics = {"evidence": "layout_preparation_not_confirmed"}
                self._vision.capture_layout_failure("layout_preparation_not_confirmed")
                return False
            self.operator.move_to(0.5, 0.5)
            self.operator.sleep(0.5 if recover_layout else 0.2)
        layout_observed_at = time.monotonic()
        layout = self._vision.read_backend_layout(
            self._confirmed_layout_positions if recover_layout else self.off_field_area,
            recover=recover_layout)
        if layout.valid and not layout.geometry_valid:
            layout = replace(layout, valid=False, reason="layout_geometry_not_confirmed")
        initial_empty = {}
        if layout.valid:
            same_positions = (len(layout.positions) == len(self.off_field_area) and
                all(abs(a - b) <= 0.002 for old, new in zip(self.off_field_area, layout.positions)
                    for a, b in zip(old, new)))
            if (not self._confirmed_layout_positions and same_positions
                    and layout.ordinary_count_confirmed and not layout.protected_slots
                    and not layout.unknown_protected_slots and self._pending_move is None):
                # 首次认证标准布局时保留已确认的新局空场；不继承历史角色身份。
                initial_empty = {i: observation for i, observation in
                    enumerate(self._observations["off_field"])
                    if i in layout.ordinary_slots and observation.state == SlotState.EMPTY
                    and observation.evidence == "new_game_empty"}
            # 恢复会把当前帧与近期锚点比较；提交布局变化时，
            # 也须相对于棋盘动作实际使用的坐标判断。
            # 坐标变化才重建整行；单槽身份变化不删除其他槽观测或延长读取时间。
            changed = (len(layout.positions) != len(self.off_field_area) or
                any(abs(a - b) > 0.002 for old, new in zip(self.off_field_area, layout.positions)
                    for a, b in zip(old, new)))
            if not changed:
                reviews = getattr(self, "_backend_identity_review_receipts", {})
                # 当前准备期内、仍有效的实际面板复核可继续解释通用角标。
                resolved = {i for i in layout.unknown_protected_slots if i in reviews
                    and layout.reason == "backend_identity_partial"
                    and reviews[i][0] is self._observations["off_field"][i]
                    and reviews[i][1:] == (self._layout_revision, self._backend_identity_context())
                    and i not in layout.protected_slots and not self._slot_needs_scan("off_field", i)}
                unknown = tuple(i for i in layout.unknown_protected_slots if i not in resolved)
                ordinary = tuple(sorted(set(layout.ordinary_slots) | resolved))
                layout = replace(layout, unknown_protected_slots=unknown, ordinary_slots=ordinary,
                    ordinary_count_confirmed=not unknown,
                    ordinary_count=len(ordinary) if not unknown else None)
            layout = replace(layout, changed=changed)
        if layout.valid and layout.changed:
            self._layout_revision += 1
            self.off_field_area = list(layout.positions)
            self.off_field_character[:] = [None] * len(layout.positions)
            self._observations["off_field"] = [SlotObservation(i, SlotState.UNKNOWN,
                evidence="layout_changed") for i in range(len(layout.positions))]
            for i, observation in initial_empty.items():
                self._observations["off_field"][i] = observation
            self._equipment_checked.clear()
            self._equipment_dirty = True
            self._population_current = self._population_read_key = None
            self._effective_targets_key = None
            self._preparation_assessment_cache = None
            self._formation_plan = ()
            self._formation_plan_stage = None
            # 保留未确认拖拽本身，由 _resolve_pending_move 按新版本重建端点。
            self._move_failures.clear()
            self._fielding_rejections.clear()
            self._snapshot_revision += 1
            self._dirty_slots = {(area, i) for area, i in self._dirty_slots if area != "off_field"}
            self._slot_evidence = {key: value for key, value in self._slot_evidence.items()
                                   if key[0] != "off_field"}
            logger.info(f"[布局确认] 后台布局版本={self._layout_revision} "
                        f"总槽位={len(layout.positions)} 支援槽={layout.protected_slots}，重建坐标及动作证据")
        if layout.valid:
            old_classes = {i: ("support" if i in self._backend_support_slots else
                              "unknown" if i in self._backend_unknown_slots else "ordinary")
                           for i in range(len(self.off_field_area))}
            self._backend_layout_observed_at = layout_observed_at
            self._layout_valid = True
            self._confirmed_layout_positions = tuple(layout.positions)
            self._backend_unknown_slots = set(layout.unknown_protected_slots)
            self._backend_ordinary_slots = tuple(layout.ordinary_slots)
            self._backend_identity_confirmed = bool(
                layout.ordinary_count_confirmed and not self._backend_unknown_slots)
            self._backend_support_slots = {
                index: Character("锁定支援单位", 0, Positioning.OffField,
                                 is_locked=True, is_npc=True)
                for index in layout.protected_slots
            }
            if not layout.changed:
                for i in range(len(self.off_field_area)):
                    category = ("support" if i in self._backend_support_slots else
                                "unknown" if i in self._backend_unknown_slots else "ordinary")
                    if old_classes.get(i) != category:
                        self._invalidate_backend_identity_dependents(i)
                        self._set_observation("off_field", SlotObservation(i, SlotState.UNKNOWN,
                            evidence="backend_identity_changed"))
            if layout.protected_slots:
                logger.info(f"[布局确认] 锁定支援单位已通过两帧认证，后台槽={layout.protected_slots}，计入人口并禁止移动")
            logger.info(f"[后台身份] 总槽位={len(layout.positions)} 支援={len(layout.protected_slots)} "
                        f"普通候选={len(layout.ordinary_slots)} 未知={sorted(self._backend_unknown_slots)} "
                        f"身份结构确认={self._backend_identity_confirmed}")
            if self._backend_unknown_slots:
                logger.warning(f"[布局确认] 完整边框已确认，身份未知槽={sorted(self._backend_unknown_slots)}；"
                               "保留坐标并禁止操作，不推算NPC数量或空位")
                self._vision.capture_layout_failure("backend_identity_partial")
        else:
            logger.warning(f"[布局确认] 拒绝本帧候选，旧坐标等待复核：{layout.reason}")
            self._vision.capture_layout_failure(layout.reason)
            self._invalidate_backend_layout("layout_unconfirmed")
        if self._layout_valid:
            # 锁定支援由刚完成的布局双帧提供证据，无须打开普通角色面板。
            for index in self._backend_support_slots:
                self._set_observation("off_field", self._observe_slot("off_field", index, True))
            now = time.monotonic()
            indices = {i for i in range(len(self.off_field_area))
                       if i not in self._backend_support_slots and
                       (force_characters or equip or self._slot_needs_scan("off_field", i, now))}
            if indices:
                self.get_off_field_area(True, equip=equip and self.equipment_interval_battles is None,
                                        indices=indices)
            logger.debug(f"[后台增量识别] 普通槽待读={len(indices)}，支援已重新双帧认证")
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
            # 先解析身份，避免优先角色身份未知时被跳过，
            # 反而给低优先级角色分配装备。
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
                    # 输入成功不能确认库存或装备变化。
                    # 未验证效果时，仅保留次数有界的尝试记录；
                    # 新的资源修订号允许重新检查。
                    status = "input_completed"
        finally:
            self._check_stop()
            self.operator.click_point(0.5, 0.5, trace=False)
        if status == "unconfirmed":
            self._equipment_metrics["unconfirmed"] += 1
        logger.debug(f"[装备检查] {char.name} 资源版本={self._equipment_resource_revision} 状态={status}")

    def get_coins(self):
        # 首次读取与横向恢复共用原图，不能把两种裁剪当成两帧确认。
        self._check_stop()
        frame = self._capture_page_frame()
        opened = self._coin_shop_open
        if opened is None:
            opened = self._locate_page_template(CWIMG.FOLD, frame) is not None
        original_region = coin_roi_evidence(opened, frame)
        attempts = []
        sample_images = []

        def read(*, wider=False):
            self._check_stop()
            region = coin_recovery_roi(original_region, frame) if wider else original_region
            roi = region.roi
            context = getattr(self.operator, "window_context", None)
            width, height = getattr(context, "width", 1920), getattr(context, "height", 1080)
            source = region.reason
            numeric_x_min = None
            crop_box = None
            geometry = None
            same_frame = (frame is not None and callable(getattr(frame, "crop", None))
                and callable(getattr(self.operator, "ocr_engine", None)))
            if same_frame:
                try:
                    width, height = frame.size
                    crop_box = tuple(round(value * (width if index % 2 == 0 else height))
                                     for index, value in enumerate(roi))
                    source_crop = frame.crop(crop_box).convert("RGB")
                    image = source_crop.convert("L" if wider else "RGB")
                    sample_images.append(("coin_recovery" if wider else "coin_original", image))
                    size = image.size
                    rows = self._vision._engine_ocr(image, minimum_confidence=0.0)
                    rows, geometry = ground_coin_rows(rows, source_crop)
                    source += ":same_frame_gray" if wider else ":same_frame_color"
                    if wider and region.anchored and region.icon_exclusion_right is not None:
                        numeric_x_min = max(0, round(region.icon_exclusion_right * width) - crop_box[0])
                except ThreadStoppedError:
                    raise
                except Exception as error:
                    same_frame = False
                    self._check_stop()
                    logger.warning(f"[金币识别] 同帧引擎未完成：{type(error).__name__}；转现场OCR")
            if not same_frame:
                # 现场 OCR 会另取截图，不能沿用旧帧上的图标锚点或裁剪认证。
                fallback = coin_roi_evidence(opened)
                roi = fallback.roi
                if wider:
                    roi = (roi[0], 0.818, roi[2], 0.890)
                rows = self.operator.ocr(from_x=roi[0], from_y=roi[1], to_x=roi[2], to_y=roi[3],
                    grayscale=wider, confidence=0.0, trace=False)
                size = (round(roi[2]*width)-round(roi[0]*width),
                        round(roi[3]*height)-round(roi[1]*height))
                source = fallback.reason + ":ocr_new_frame"
                numeric_x_min = None
                crop_box = None
                geometry = None
            self._check_stop()
            observation = select_coin_read(rows, roi_size=size, source=source,
                                           numeric_x_min=numeric_x_min)
            attempts.append({"method": "horizontal_recovery" if wider else "original",
                "source": source, "roi": list(roi), "crop_box": list(crop_box) if crop_box else None,
                "numeric_x_min": numeric_x_min, "coins": observation.value,
                "reliable": observation.reliable, "reason": observation.reason,
                "geometry": geometry,
                "rows": [{"text": candidate.raw_text, "score": candidate.confidence,
                          "box": list(candidate.bounds) if candidate.bounds else None,
                          "issues": list(candidate.issues)} for candidate in observation.candidates[:8]],
                "text": " | ".join(candidate.raw_text for candidate in observation.candidates)[:240],
                "scores": [candidate.confidence for candidate in observation.candidates[:16]]})
            return observation
        observation = read()
        if not observation.reliable:
            other = read(wider=True)
            observation = choose_coin_read((observation, other))
            logger.warning(f"[金币识别] 来源={observation.source} 候选={observation.candidates} "
                f"选择={observation.value} 原因={observation.reason} 可靠={observation.reliable}；按证据继续")
            if (not observation.reliable and frame is not None
                    and all(":same_frame_" in attempt["source"] for attempt in attempts)):
                self._vision.capture_sample("unknown_coins_geometry",
                    {"source": observation.source, "evidence": observation.reason,
                     "ocr_attempts": attempts}, frame=frame, related_images=sample_images)
        self._last_coin_observation = observation
        self._last_coins_read = observation.value
        return self._last_coins_read

    # ssyb：费用来自当前界面观测，不能由消费结果反推。
    def _read_action_cost(self, action):
        """输入前读取展开商店内经验或刷新按钮的实际费用。"""
        if action in self._coin_action_costs:
            return self._coin_action_costs[action]
        default = self.SHOP_EXPERIENCE_COST if action == "experience" else self.SHOP_REFRESH_COST
        if self._coin_shop_open is not True:
            # 价格按钮只在展开商店中可用；不能读取同坐标下的棋盘或角色。
            return default
        # 余额上方是利息预估，不能据此推断免费刷新。
        roi = EXPERIENCE_COST_ROI if action == "experience" else REFRESH_COST_ROI
        frame = self._capture_page_frame()
        context = getattr(self.operator, "window_context", None)
        width, height = getattr(context, "width", 1920), getattr(context, "height", 1080)
        source = "experience_price" if action == "experience" else "refresh_price"
        same_frame = (frame is not None and callable(getattr(frame, "crop", None))
            and callable(getattr(self.operator, "ocr_engine", None)))
        if same_frame:
            try:
                width, height = frame.size
                image = frame.crop(tuple(value * (width if index % 2 == 0 else height)
                                         for index, value in enumerate(roi))).convert("RGB")
                size = image.size
                rows = self._vision._engine_ocr(image, minimum_confidence=0.0)
                source += ":same_frame"
                # 小裁剪的 OCR 框可能覆盖整图；沿用金币的原图字形核实，
                # 真正截断、低置信度或字数冲突仍保留未知。
                rows, geometry = ground_coin_rows(rows, image, kind="action_cost")
                if geometry.get("bounds_source") == "source_pixels":
                    source += ":source_pixels"
            except ThreadStoppedError:
                raise
            except Exception as error:
                same_frame = False
                self._check_stop()
                logger.warning(f"[费用识别] 同帧引擎未完成：{type(error).__name__}；转现场OCR")
        if not same_frame:
            rows = self.operator.ocr(from_x=roi[0], from_y=roi[1], to_x=roi[2], to_y=roi[3],
                grayscale=False, confidence=0.0, trace=False)
            size = (round(roi[2]*width)-round(roi[0]*width),
                    round(roi[3]*height)-round(roi[1]*height))
            source += ":ocr_new_frame"
        self._check_stop()
        reading = select_action_cost(rows, action=action, default_cost=default,
                                     roi_size=size, source=source)
        if not hasattr(self, "_coin_action_cost_observations"):
            self._coin_action_cost_observations = {}
        self._coin_action_cost_observations[action] = reading
        if reading.reliable:
            self._coin_action_costs[action] = reading.cost
            logger.info(f"[费用识别] action={action} fee={reading.cost} "
                f"来源={source} 原因={reading.reason} 证据={reading.observation.candidates}")
        else:
            logger.debug(f"[费用识别] action={action} fee={reading.cost} "
                f"原因={reading.reason} 证据={reading.observation.candidates}；使用默认预算")
        return reading.cost

    def _experience_progress_before_input(self, level):
        raw = getattr(self._last_level_read, "raw_text", "")
        progress = parse_experience_progress(raw, level=level) if raw else None
        if progress is None:
            progress = self._read_experience_progress(level, recognize_cap=True)
        return progress

    def _experience_context_key(self, level):
        # 该凭据只由终局同一次决策传给首次 F；中间路径只有只读费用检查。
        # F、等级失效和面板认证入口递增版本；角色事件改变快照版本。
        # 凭据不保存为会话缓存，不允许跨另一动作或另一次决策传递。
        return (level, self._experience_input_revision, self._coin_shop_open,
                self._preparation_round, self._snapshot_revision, self._layout_revision,
                self._level_cache, id(self._last_level_read))

    def _get_character_in_area(self, areas, target_character_list, force=False,
                               equip=False, count_stars=False, use_backup_ocr=False,
                               indices=None):
        area_type = self._area_name(target_character_list)
        self._last_scan_completed[area_type] = True
        for index in range(len(areas)):
            if indices is not None and index not in indices:
                continue
            self._check_stop()
            old = self._observations[area_type][index]
            if not force and old.state == SlotState.KNOWN:
                continue
            try:
                overrides = (getattr(self, "_bench_scan_overrides", None) if area_type == "in_hand" else
                             getattr(self, "_backend_scan_overrides", None) if area_type == "off_field" else None)
                obs = overrides.get(index) if overrides is not None else None
                if obs is old:
                    continue  # 此交易未影响该已确认身份。
                if obs is None:
                    obs = self._observe_slot(area_type, index, count_stars, use_backup_ocr)
                self._set_observation(area_type, obs)
                if obs.state != SlotState.KNOWN or not equip:
                    continue
                self._equip_observation(area_type, index, obs)
            except ThreadStoppedError:
                raise
            except Exception as error:
                self._set_observation(area_type, SlotObservation(
                    index, SlotState.UNKNOWN, evidence="observation_error"))
                logger.warning(f"角色识别失败 {area_type}[{index}]: {error}")
        self._last_scan_completed[area_type] = all(
            observation_identity(obs) is not None and (
                not count_stars or obs.state != SlotState.KNOWN or obs.character.is_npc
                or type(obs.stars) is int and 1 <= obs.stars <= 3)
            for obs in self._observations[area_type])
        if equip and self.equipment_interval_battles is not None and not self._equipment_batch_running:
            # 扫描仅登记工作；到期批次在最终布阵后执行。
            self._equipment_dirty = True
        return target_character_list

    def get_off_field_area(self, force=False, equip=False, *, indices=None):
        # 支援退场留下的空位与其他普通空位使用同一对新鲜帧；
        # 不逐个点击空位并重复 OCR，从而为布阵保留整备时间。
        overrides = {}
        positions = {i: self.off_field_area[i] for i in self._backend_ordinary_slots
                     if (indices is None or i in indices)
                     and i not in self._backend_unknown_slots and i not in self._backend_support_slots
                     and (force or self._observations["off_field"][i].state != SlotState.KNOWN)}
        if self._layout_valid and positions:
            self._check_stop()
            self.operator.click_point(0.5, 0.5, trace=False)
            try:
                observed_at = time.monotonic()
                values = self._vision.read_empty_slots("off_field", positions)
                reasons = getattr(self._vision, "last_empty_slot_reasons", {})
                if any(reasons.get(i) == "dynamic_layout_changed" for i in positions):
                    self._last_scan_completed["off_field"] = False
                    self._invalidate_backend_layout("dynamic_layout_changed")
                    if not getattr(self, "_backend_auto_rebuild_active", False):
                        logger.info("[后台动态恢复] 新帧数量或坐标变化，自动重建完整后台并重新确认人口")
                        self._backend_auto_rebuild_active = True
                        try:
                            self.refresh_backend_character(equip=False, recover_layout=True)
                        finally:
                            self._backend_auto_rebuild_active = False
                    return
                for i, empty in values.items():
                    if i in positions and empty is True:
                        self._observation_revision += 1
                        overrides[i] = SlotObservation(i, SlotState.EMPTY, occupied=False,
                            evidence="two_empty_frames", revision=self._observation_revision)
                        self._record_slot_evidence("off_field", overrides[i], observed_at=observed_at)
            except ThreadStoppedError:
                raise
            except Exception as error:
                self._vision._failure(error)
                logger.debug(f"[后台空位] 批量读取未确认，继续逐槽识别：{type(error).__name__}")
        self._backend_scan_overrides = overrides
        try:
            self._get_character_in_area(self.off_field_area, self.off_field_character, force,
                                        equip, True, True, indices=indices)
        finally:
            self._backend_scan_overrides = None
        self._reconcile_placed()

    def get_on_field_area(self, force=False, equip=False):
        self._get_character_in_area(self.on_field_area, self.on_field_character, force,
                                    equip, True)
        self._reconcile_placed()

    def _supply_pause(self, seconds):
        # 打包操作器的 sleep 不支持取消，因此每次等待须短。
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
        # 保留原始按下与松开输入路径；失败时始终释放。
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
                return None  # OCR 失败不能证明弹窗已关闭。
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
        # 选择点击周围的游戏区域为 (0.73, 0.13) 到 (0.87, 0.40)。
        # 输入帧已裁剪为 (0.08, 0.05) 到 (0.92, 0.65)。
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
            equipment_choice = self._read_equipment_choice()
            if self._equipment_choice_pending is not None or (
                    equipment_choice is not None and equipment_choice.present):
                # 通用三选一卡片与旧补给默认坐标不同，使用真实卡框中心处理。
                if not self._handle_equipment_choice(equipment_choice,
                        time.monotonic() + self.ENTRY_TRANSITION_TIMEOUT):
                    self._fail_supply("supply_equipment_choice_unconfirmed")
                continue
            # 保留原有奖励偏好，但只有实际的装备或角色
            # 选项可见且稳定后才能应用。
            self._invalidate_roster_evidence("supply_reward_unknown")
            if not self.operator.click_point(0.8, 0.25, tag="补给箱：选择已稳定的奖励"):
                self._fail_supply("supply_choice_click_failed")
            self._wait_supply_result(choice_frame)
            self._invalidate_equipment_resources("supply_reward")
            self._invalidate_level()
        if self.operator.locate(CWIMG.OPEN) is not None:
            self._fail_supply("supply_item_limit")

    def _read_bench_empty_observations(self):
        """读取空位及不可用锁定槽位；两者均不代表存在角色。"""
        self._check_stop()
        reader = getattr(self._vision, "read_empty_slots", None)
        if not callable(reader):
            return {}
        try:
            observed_at = time.monotonic()
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
                self._record_slot_evidence("in_hand", observations[index], observed_at=observed_at)
        locked_reader = getattr(self._vision, "read_locked_bench_slots", None)
        if callable(locked_reader):
            unresolved = {index: point for index, point in enumerate(self.in_hand_area)
                          if index not in observations}
            locked_observed_at = time.monotonic()
            locked = locked_reader(unresolved)
            self._check_stop()
            if isinstance(locked, (set, frozenset)):
                for index in sorted(locked & unresolved.keys()):
                    self._observation_revision += 1
                    observations[index] = SlotObservation(index, SlotState.LOCKED,
                        occupied=False, evidence="two_locked_frames", revision=self._observation_revision)
                    self._record_slot_evidence("in_hand", observations[index], observed_at=locked_observed_at)
        return observations

    def get_in_hand_area(self, force=False, *, collect_supply=True):
        # 补给在购物前处理；当前商店商品仍在确认时，
        # 合成验证不能启动另一轮奖励流程。
        self._check_stop()
        if collect_supply and not self._shopping_active:
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

    def _read_equipment_choice(self, frame=None):
        """只使用同一张新鲜帧认证通用装备三选一的标题与实际卡框。"""
        self._check_stop()
        if not callable(getattr(self.operator, "screenshot", None)) or not callable(
                getattr(self.operator, "ocr_engine", None)):
            return None
        cards, partial = (), False
        try:
            frame = self._capture_page_frame() if frame is None else frame
            window = self.operator.window_context.width, self.operator.window_context.height
            if frame is None or tuple(frame.size) != window:
                return None
            geometry = equipment_choice_geometry(frame)
            if geometry is None:
                return None
            cards, partial = geometry
            if not cards and not partial and self._equipment_choice_pending is None:
                return EquipmentChoiceObservation(False, False, (), None, "equipment_no_three_cards")
            title_roi = tuple(round(value * window[index % 2])
                              for index, value in enumerate(EQUIPMENT_CHOICE_TITLE_ROI))
            title = self._vision._engine_ocr(frame.crop(title_roi), minimum_confidence=0.95)
            self._check_stop()
            return detect_equipment_choice(frame, title, cards=cards, partial=partial)
        except ThreadStoppedError:
            raise
        except Exception as error:
            self._check_stop()
            logger.debug(f"[装备三选一] 同帧识别未确认：{type(error).__name__}")
            if cards or partial or self._equipment_choice_pending is not None:
                # 几何已证明上层弹窗，OCR 异常不能授权点击其露出的底层按钮。
                return EquipmentChoiceObservation(False, True, cards or (), None,
                                                   "equipment_ocr_failed_with_pending_modal")
            return None

    def _handle_equipment_choice(self, first, deadline):
        """只选择稳定的真实卡片一次，并等待弹窗消失和底层准备页面重新认证。"""
        self._check_stop()
        deadline = self._page_navigation_limit(self.EVENT_TRANSITION_TIMEOUT, deadline)
        if self._equipment_choice_pending is None:
            if first is None or not first.matched:
                return False
            self.operator.sleep(0.25)
            self._check_stop()
            if time.monotonic() >= deadline:
                return False
            second = self._read_equipment_choice()
            self._check_stop()
            if not same_equipment_choice(first, second) or time.monotonic() >= deadline:
                return False
            # 点击可能已生效但其返回值或后续识别失败，因此输入前就保留待确认状态。
            self._equipment_choice_pending = second
            if not self.operator.click_point(*second.choice_point, after_sleep=0.2,
                    tag="装备三选一：选择已认证的最右卡片"):
                return False
            logger.info(f"[装备三选一] 已发送最右卡片选择，位置={second.choice_point}；等待页面确认")
        confirmed, previous_state = 0, None
        for _ in range(30):
            self._check_stop()
            if time.monotonic() >= deadline:
                break
            frame = self._capture_page_frame()
            phase, payload = self._observe_page_frame(frame, ignore_pending_equipment=True,
                                                       full_navigation=False)
            state = ("shop" if payload is not None else "preparation") if phase == "preparation" else None
            self._check_stop()
            if time.monotonic() >= deadline:
                break
            confirmed = confirmed + 1 if state is not None and state == previous_state else (
                1 if state is not None else 0)
            previous_state = state
            if confirmed >= 2:
                self._equipment_choice_pending = None
                self._invalidate_equipment_resources("equipment_choice_confirmed")
                self._invalidate_level()
                # 奖励可能改变折扣或免费次数，必须重新读取消费证据。
                self._coin_action_costs.clear()
                self._last_coins_read = None
                self._last_coin_observation = None
                self._experience_before = None
                logger.info("[装备三选一] 已连续确认弹窗消失和底层准备页面，恢复当前准备期")
                return True
            self.operator.sleep(0.25)
        logger.warning("[装备三选一] 输入结果尚未确认，保留待确认状态，禁止重复选择或点击底层控件")
        return False

    def _read_shop_probability_overlay(self, frame=None):
        """在同一张客户区帧上认证标题与关闭控件。"""
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
            panel = observe_shop_probability_panel(frame)
            if not panel.present:
                return None
            roi = tuple(round(value * window[i % 2])
                        for i, value in enumerate(SHOP_PROBABILITY_TITLE_ROI))
            title = self._vision._engine_ocr(frame.crop(roi), minimum_confidence=0.9)
            result = detect_shop_probability_overlay(frame, title, panel_observation=panel)
            return result.close_point if result.matched else None
        except ThreadStoppedError:
            raise
        except Exception as error:
            self._check_stop()
            logger.debug(f"[商店概率弹窗] 识别未确认：{type(error).__name__}")
            return None

    def _set_shop_open(self, opened, *, deadline=None):
        """使用商店或棋盘坐标前，先确认面板状态。"""
        self._experience_input_revision += 1
        deadline = self._page_navigation_limit(self.SHOP_STATE_TIMEOUT, deadline)
        # 收店是页面核验及超时收尾，使用自身和上层导航的有限时间；
        # 不能被已耗尽的运营时间挡住，否则恢复成功后连新帧都读不到。
        # 展店仍沿用准备额度，不因此重新开放购买、布阵或装备操作。
        if opened and self._preparation_deadline is not None and not self._shopping_active:
            deadline = min(deadline, self._preparation_deadline)
        acted = False
        close_attempts, opposite_frames = 0, 0
        last_toggle_at = float("-inf")
        probability_close_sent = False
        previous_overlay = None
        overlay_deadline = None
        handled_overlays = set()
        handled_investment = False
        previous_page = None
        confirmed = 0
        for _ in range(30):
            self._check_stop()
            if time.monotonic() >= deadline:
                break
            frame = self._capture_page_frame()
            observed = self._observe_page_frame(frame, full_navigation=False)
            self._check_stop()
            if time.monotonic() >= deadline:
                break
            if previous_page is not None:
                self._accept_runtime_node_departure(previous_page, observed)
            previous_page = observed
            phase, payload = observed
            if phase != "preparation":
                # 所有入口共享弹窗优先级，底层 FOLD/战斗按钮不再授权切换。
                if overlay_deadline is None:
                    overlay_deadline = min(deadline, time.monotonic() + self.EVENT_TRANSITION_TIMEOUT)
                if time.monotonic() >= overlay_deadline:
                    break
                confirmed = opposite_frames = 0
                stable = previous_overlay is not None and self._same_runtime_page(previous_overlay, observed)
                previous_overlay = observed
                if phase in {"terminal", "combat", "settlement", "main_menu"}:
                    break
                if not stable:
                    self.operator.sleep(0.3)
                    continue
                if phase in {"equipment_choice", "selection_event", "shop_probability"}:
                    key = (phase, payload if phase == "selection_event" else None)
                    if key in handled_overlays or (phase == "shop_probability" and probability_close_sent):
                        break
                    handled_overlays.add(key)
                    probability_close_sent |= phase == "shop_probability"
                    if not self._handle_page_overlay(observed, overlay_deadline):
                        break
                elif phase == "advance" and payload[0] == "点击空白处关闭":
                    key = (phase, payload[0])
                    if key in handled_overlays:
                        break
                    handled_overlays.add(key)
                    with self._page_navigation_scope(overlay_deadline):
                        self.handle_click_blank(None)
                elif phase == "node" and payload == CWIMG.SELECT_INVEST_STRATEGY:
                    if handled_investment:
                        break
                    handled_investment = True
                    with self._page_navigation_scope(overlay_deadline):
                        if self._runtime_node_pending == payload:
                            self._confirm_invest_strategy(overlay_deadline)
                        else:
                            self.handle_invest_strategy(None)
                else:
                    break  # 未知弹窗/其他节点交由页面恢复，不发送底层输入。
                previous_overlay = None
                continue  # 操作后不能复用任何底层页面确认结果。
            previous_overlay = None
            overlay_deadline = None
            fold = payload
            state = fold is not None
            if state is opened:
                opposite_frames = 0
                confirmed += 1
                if confirmed >= 2:
                    if self._coin_shop_open is not opened:
                        self._coin_action_costs.clear()
                    self._coin_shop_open = opened
                    self._last_coins_read = None
                    return True
            else:
                confirmed = 0
                opposite_frames = opposite_frames + 1 if state is not None else 0
                # 只重试收起：需两帧仍看见展开按钮，并给动画至少两秒。
                # 未知画面、已收起画面和展开操作都不会盲目反复切换。
                retry_close = (not opened and close_attempts < self.SHOP_CLOSE_ATTEMPTS and opposite_frames >= 2
                               and time.monotonic() - last_toggle_at >= 2.0)
                if state is not None and (not acted or retry_close):
                    self._check_stop()
                    if time.monotonic() >= deadline:
                        break
                    acted = True
                    last_toggle_at = time.monotonic()
                    opposite_frames = 0
                    if opened:
                        clicked = self.operator.click_point(0.8438, 0.8481,
                            after_sleep=0.5, tag="准备阶段：展开商店")
                    else:
                        close_attempts += 1
                        logger.info(f"[商店界面] 收起尝试={close_attempts}/3")
                        clicked = self.operator.click_box(fold, after_sleep=0.5)
                    if not clicked:
                        break
            self.operator.sleep(0.3)
        logger.warning(f"[商店界面] 未确认{'展开' if opened else '收起'}，已发送切换={acted}")
        self._record_observation_issue("shop_state_unconfirmed",
            f"目标={'展开' if opened else '收起'} 已发送切换={acted} 连续确认帧={confirmed}")
        return False

    def harvest_crystals(self):
        if self._preparation_rewards_collected:
            return
        # 战后页面可能仍被商店遮住掉落物。
        if not self._set_shop_open(False):
            self._fail_battle("crystals_shop_not_closed")
        # 水晶奖励沿用同页批量采购的复核节奏，允许批次内暂时多买。
        # 保留既有身份、星级和读取时效，交给原有购后局部复核/常规扫描更新，
        # 不因未知奖励清空全场记录，也不增加领取专用的全场复核。
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

        # 事件识别可能需要页面恢复，因此先提交领取状态。
        self._preparation_rewards_collected = True
        self._bench_dirty = True
        self._invalidate_equipment_resources("preparation_rewards_collected")
        self.detect_silver_wolf_lv999()  # 也许开出银狼了

    @property
    def in_hand_unknown_count(self):
        return sum(obs.state == SlotState.UNKNOWN for obs in self._observations["in_hand"])

    def _read_full_bench_recovery(self):
        """故障分支专用；相同提示和队列数量必须在两张新截图中稳定。"""
        first = observe_full_bench(self._capture_page_frame())
        self.operator.sleep(0.2)
        self._check_stop()
        second = observe_full_bench(self._capture_page_frame())
        if (first.known and second.known
                and (first.full, first.queued) == (second.full, second.queued)):
            return second
        return FullBenchObservation(False)

    # Yukki：先排清满员队列，再恢复场上识别与普通整备。
    def _recover_full_bench_failure(self, error, deadline):
        """返回 None 沿用旧恢复；True 为已恢复；False 为仍有缺口。"""
        pending = getattr(self, "_bench_full_failure_pending", False)
        pressure = self._read_full_bench_recovery()
        logger.info(f"[满员检查] 原失败={error}，证据稳定={pressure.known}，"
                    f"提示={pressure.full}，匹配={pressure.score:.3f}，"
                    f"溢出={pressure.queued}，续接={pending}")
        if not pressure.known or not pressure.full and not pending:
            return False if pending else None
        if (self._pending_move is not None
                or self._purchase_pending_names or self._selection_event_pending is not None):
            logger.warning("[满员恢复] 尚有未确认输入，保留角色和原动作等待复核")
            return False
        self._bench_full_failure_pending = True
        self._bench_full = True
        logger.info(f"[满员恢复] 原失败={error}，已确认备战席已满提示，溢出={pressure.queued}")
        if not self._set_shop_open(False, deadline=deadline):
            logger.warning("[满员恢复] 备战席可见页面未确认，暂停出售")
            return False
        if self._bench_dirty or any(observation_identity(o) is None
                                   for o in self._observations["in_hand"]):
            self.get_in_hand_area(True, collect_supply=False)
        # 溢出卡遮挡后台时，不把重新扫描场上当作出售入口条件。
        # 这里只卖静态保护名单之外的备战席角色；每次输入前仍重读源槽。
        # 补位造成的场上变化先标脏，提示消失后统一扫描，不用于中途选牌。
        sold = 0
        for _ in range(18):
            self._check_stop()
            if not pressure.known or time.monotonic() >= deadline:
                logger.warning("[满员恢复] 提示尚未稳定或恢复额度结束，保留进展等待后续恢复")
                return False
            if pressure.known and not pressure.full and pressure.queued == 0:
                logger.info("[满员恢复] 提示已消失且溢出已清空，开始统一扫描场上与库存")
                self.get_in_hand_area(True, collect_supply=False)
                before_field = self._read_full_bench_recovery()
                if not before_field.known or before_field.full or before_field.queued != 0:
                    self._bench_dirty = True
                    logger.warning("[满员恢复] 库存复核期间提示或队列发生变化，暂缓场上扫描")
                    return False
                self.refresh_character(equip=False, recover_layout=True)
                if not self._layout_valid:
                    logger.warning("[满员恢复] 清理后场上布局尚未确认，暂停返回原流程")
                    return False
                self._population_read_key = None
                self.update_max_team_size()
                final_pressure = self._read_full_bench_recovery()
                if not final_pressure.known or final_pressure.full or final_pressure.queued != 0:
                    self._bench_dirty = True
                    logger.warning("[满员恢复] 统一复核期间提示或队列发生变化，保留恢复状态")
                    return False
                complete = (not self._bench_dirty and self._sale_transition_blocker() is None
                    and all(observation_identity(o) is not None
                            for o in self._observations["in_hand"]))
                if not complete:
                    return False
                self._bench_full_failure_pending = False
                self._bench_full = not self._has_confirmed_bench_space()
                logger.info("[满员恢复] 提示已消失、溢出队列已清空、库存已复核，返回原准备流程")
                self._record_checkpoint(phase="preparation", pending_actions=[])
                return True
            if not pressure.full:
                logger.info("[满员恢复] 提示已退但队列尚未清空，等待补位，不追加出售")
                return False
            if not self._opening_action_allowed("sell"):
                logger.warning("[满员恢复] 当前攻略尚未允许出售，不改变原有开局限制")
                return False
            candidates = self._full_bench_sell_candidates()
            if not candidates:
                logger.warning("[满员恢复] 无安全余牌可卖，保留主C、职责、攻略材料及过渡角色；"
                               "不强制刷新或绕过攻略购买经验")
                return False
            index, _ = candidates[0]
            self._record_checkpoint(phase="preparation", pending_actions=[f"满员恢复出售槽位{index}"])
            before_pressure = pressure
            self._bench_full_sale_receipt = {"index": index, "queued": pressure.queued,
                                            "bench_only": True, "deadline": deadline}
            try:
                sale = self._sell_character_batch(candidates[:1])
            finally:
                self._bench_full_sale_receipt = None
            if sale.attempted == 0 and sale.reason in (
                    "source_changed", "full_bench_queue_changed", "full_bench_warning_cleared"):
                logger.info("[满员恢复] 出售前提示、队列或源槽位已变化，按新观测重判，不发送旧计划")
                pressure = self._read_full_bench_recovery()
                continue
            if sale.result != ActionResult.CONFIRMED or sale.confirmed != 1:
                logger.warning(f"[满员恢复] 出售尚未确认，停止追加输入：{sale.reason}")
                return False
            sold += 1
            self._field_observed_at = self._backend_layout_observed_at = None
            self._population_current = self._population_read_key = None
            self._layout_valid = self._backend_identity_confirmed = False
            self._dirty_slots.update((area, i) for area in ("on_field", "off_field")
                                     for i in range(len(self._observations[area])))
            for settle_attempt in range(4):
                self.operator.sleep(0.5)
                self._check_stop()
                pressure = self._read_full_bench_recovery()
                if (pressure.known and (not pressure.full and pressure.queued == 0
                        or type(pressure.queued) is int and 0 < pressure.queued < before_pressure.queued)):
                    break
                if time.monotonic() >= deadline:
                    return False
            else:
                logger.warning("[满员恢复] 出售已确认，补位或提示退场尚未确认，停止追加输入")
                return False
            logger.info(f"[满员恢复] 本轮已确认出售={sold}，提示={pressure.full}，"
                        f"剩余溢出={pressure.queued}；提示消失前暂缓场上扫描")
        logger.warning("[满员恢复] 达到本轮出售上限，未将满员状态标记为恢复")
        return False

    def _full_bench_sell_candidates(self):
        """失败清理专用：不依赖场上几何，只选所有保护名单外的角色。"""
        if not getattr(self, "_bench_full_failure_pending", False):
            return []
        config = self.formation_config
        if config is None:
            return self._sell_candidates()  # 旧攻略继续要求原有场上证据。
        protected = set(self.strategy_characters) | set(config.purchase_targets) | set(config.root_positions)
        protected.add(self.main_c)
        protected.update(config.protect_until_fielded)
        protected.update(config.protect_until_fielded.values())
        requirements = list(config.role_requirements.values())
        for stage in config.stages:
            protected.update(stage.on_field + stage.off_field + stage.requires_fielded
                             + stage.requires_available + stage.priority)
            protected.update(stage.requires_stars)
            protected.update(stage.position_fallbacks)
            requirements.extend(stage.role_requirements.values())
        for providers in config.roles.values():
            protected.update(provider.name for provider in providers)
        for requirement in requirements:
            protected.update(requirement.candidates + requirement.interim_candidates)
        for group in config.assignment_groups.values():
            protected.update(candidate.name for candidate in group.candidates)
            protected.update(group.replace_from)
        for rule in config.position_rules:
            protected.add(rule.name)
            protected.update(rule.requires_assignment.values())
        traits = set(config.preserve_traits)
        if config.upgrade_gate is not None:
            protected.update(config.upgrade_gate.fielded)
            protected.update(config.upgrade_gate.prices)
            traits.update(config.upgrade_gate.traits)
        protected.update(name for name, tags in config.traits.items() if traits.intersection(tags))
        # 保留场上当前及待确认的历史身份，不用旧星级证明某份攻略材料多余。
        for area in ("on_field", "off_field"):
            protected.update(char.name for char in getattr(self, area + "_character") if char is not None)
            protected.update(obs.character.name for obs in self._observations[area] if obs.character is not None)
        return [(obs.slot_index, obs.character) for obs in self._observations["in_hand"]
                if self._sale_usable_observation(obs) and obs.character.name not in protected]

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
        """仅保留可靠开局或前台仍需要的备战区角色。"""
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
        # 在场上或备战区保留一个实际完成的实例。
        # 按名称整体保护会永久保留所有多余副本；
        # 但未绑定实例便取消保护，又可能卖掉已经完成的那个实例。
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
        """场上情况不确定，不能证明临时备战区角色已多余。"""
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
        # 人口 OCR 缺失不能冻结多余备战区角色清理；
        # 已确认的场上身份与临时预留仍会保护占位角色。
        if type(capacity) is not int or type(current) is not int:
            return None
        if not 1 <= capacity <= len(field) or not 0 <= current <= capacity:
            return "population_conflict"
        # 锁定 NPC 虽不能移动或出售，仍占用游戏人口。
        # 不能用可出售资格来统计场上人数。
        known = sum(obs.state == SlotState.KNOWN for obs in field)
        if known != current:
            return "population_conflict"
        return None

    def _needs_pre_battle_cleanup(self):
        """仅依据缓存证据决策，不重复扫描已干净的备战区。"""
        if (self._preparation_deadline is not None
                and time.monotonic() >= self._preparation_deadline):
            return False
        return bool(self._sell_candidates())

    def _log_sale_transition_blocker(self):
        reason = self._sale_transition_blocker()
        if reason:
            logger.info(f"[过渡牌保护] 场地证据未确认或冲突，保留非攻略角色：{reason}")

    def sell_character(self):
        self._check_stop()
        if self._preparation_budget_spent():
            return SellResult(ActionResult.CONFIRMED, 0, 0, "preparation_budget_finished")
        with self._pause_formation_for_auxiliary():
            return self._sell_character_impl()

    def _sell_character_impl(self):
        """清理可靠的多余备战区角色，不等待备战区满员。"""
        self._check_stop()
        if not self._opening_action_allowed("sell"):
            return SellResult(ActionResult.CONFIRMED, reason=("opening_round_unknown"
                if self._preparation_round is None else "opening_sales_locked"))
        self._log_sale_transition_blocker()
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
        # 为调用方保留 force，但它不能绕过角色保护。
        self._check_stop()
        if not self._opening_action_allowed("sell"):
            return SellResult(ActionResult.CONFIRMED, reason=("opening_round_unknown"
                if self._preparation_round is None else "opening_sales_locked"))
        self._log_sale_transition_blocker()
        return self._sell_character_batch(self._sell_candidates())

    def _sell_character_batch(self, candidates):
        """入口检查仅消耗一次；每次尝试出售后重新规划。"""
        attempted = confirmed = 0
        receipt = getattr(self, "_bench_full_sale_receipt", None)
        candidate_reader = (self._full_bench_sell_candidates
            if receipt is not None and receipt.get("bench_only")
            and getattr(self, "_bench_full_failure_pending", False) else self._sell_candidates)
        deadline = time.monotonic() + 30
        if self._preparation_deadline is not None:
            deadline = min(deadline, self._preparation_deadline)
        if receipt is not None and receipt.get("bench_only") and "deadline" in receipt:
            deadline = min(deadline, receipt["deadline"])

        def finish_timed_batch():
            # 预算检查发生在拖拽之间；已确认出售保持确认状态，
            # 即使另一多余角色须等到下批次才能处理。
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
            # 拖拽前重新观测，不能信任偏移或溢出槽位。
            obs = self._observe_slot("in_hand", index, count_stars=True)
            self._set_observation("in_hand", obs)
            if (not self._sale_usable_observation(obs) or obs.character.name != char.name
                    or (index, char) not in candidate_reader()):
                return SellResult(ActionResult.INDETERMINATE, attempted, confirmed, "source_changed")
            before_coins = self.get_coins()
            if time.monotonic() >= deadline:
                return finish_timed_batch()
            if receipt is not None and receipt.get("bench_only") and self._bench_full_failure_pending:
                current_pressure = self._read_full_bench_recovery()
                if not current_pressure.known:
                    return SellResult(ActionResult.INDETERMINATE, attempted, confirmed, "full_bench_warning_unknown")
                if not current_pressure.full:
                    return SellResult(ActionResult.CONFIRMED, attempted, confirmed, "full_bench_warning_cleared")
                if current_pressure.queued != receipt["queued"]:
                    return SellResult(ActionResult.INDETERMINATE, attempted, confirmed, "full_bench_queue_changed")
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
                # 只重新观测一次，绝不再次发送不确定的拖拽。
                result = self._confirm_sale(index, char, before_coins)
                if result != ActionResult.CONFIRMED:
                    return SellResult(result, attempted, confirmed, "sale_not_confirmed")
            confirmed += 1
            self._reconcile_placed()
            logger.info(f"已确认出售 {char.name}")
            if getattr(self, "_bench_full_sale_receipt", None) is not None:
                # 失败专用处理链负责等待队列补位和重读库存；普通批量出售不变。
                return SellResult(ActionResult.CONFIRMED, attempted, confirmed, "full_bench_one_sale_confirmed")
            # 源槽位为空，确认实际备战区位置保持不变。
            # 若变为其他身份，可能发生压缩或合成，此时重新扫描。
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
        if self._preparation_budget_spent():
            self._preparation_optimization_finished = True
            return self._assess_existing_roster().state != Readiness.BLOCKED
        if (self._preparation_deadline is not None
                and time.monotonic() >= self._preparation_deadline):
            return False
        if (self._formation_deadline is not None
                and time.monotonic() >= self._formation_deadline
                and (self._unknown_field_gaps() or any(area in ("on_field", "off_field")
                                                     for area, _ in self._dirty_slots))):
            return False
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
            # 即使普通未知样本在此前已用完会话配额，
            # 仍保留最后一次实际识别。
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

    def _post_battle_stage(self, allow_preparation=False, *, deadline=None):
        frame = self._capture_page_frame()
        phase, payload = self._observe_page_frame(frame, full_navigation=False)
        if phase == "equipment_choice":
            if not self._handle_equipment_choice(payload,
                    self._page_navigation_limit(self.EVENT_TRANSITION_TIMEOUT, deadline)):
                raise RuntimeError("装备三选一尚未完成，交由有界页面恢复")
            return None  # 输入后由下一次新帧确认，不能复用底层控件。
        if phase == "node":
            return payload
        if phase == "selection_event":
            return CWIMG.CONFIRM_SELECTION  # 已确认事件标题，交由关卡入口处理。
        if phase == "advance" and payload[0] == "点击空白处关闭":
            return CWIMG.CLICK_BLANK
        if allow_preparation and phase == "preparation":
            return CWIMG.FOLD if payload is not None else CWIMG.PREPARATION_STAGE
        if allow_preparation and phase == "main_menu":
            return CWIMG.START_CURRENCY_WARS
        return None

    def _combat_screen_confirmed(self, frame=None):
        """入战、等待和恢复共用同帧的 Q 或组合战斗控件证据。"""
        if frame is None:
            frame = self._capture_page_frame()
        self._check_stop()
        confirmed = (self._locate_page_template(IMG.Q, frame) is not None
                     or self._vision.read_combat_screen(frame).state == "combat")
        self._check_stop()
        return confirmed

    def _battle_wait_limits(self):
        """同一待确认战斗跨入战、等待和异常恢复共享一个总计时。"""
        clock = getattr(self, "_battle_wait_clock", None)
        if clock is None or clock[0] != self._pending_battle_id:
            clock = self._battle_wait_clock = (self._pending_battle_id, time.monotonic())
        return clock[1], clock[1] + self.BATTLE_MAX_WAIT_SECONDS

    def _wait_battle_entry(self, allow_combat=True):
        # 货币战争可能完全不出现 Q。等待明确的战斗或结果证据，
        # 不能声明 UNKNOWN 帧证明已进入战斗。
        started = time.monotonic()
        deadline = started + (self.BATTLE_TIMEOUT if allow_combat else self.REWARD_TRANSITION_TIMEOUT)
        confirmation_sent = False
        preparation_since = None
        next_stage, next_stage_frames = None, 0
        pending_logged = False
        combat_frames = 0
        if allow_combat:
            self._battle_wait_limits()
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
            if allow_combat:
                combat_frames = combat_frames + 1 if self._combat_screen_confirmed() else 0
                if combat_frames >= 2:
                    self._battle_entry_confirmed = bool(self._pending_battle_id)
                    self._record_checkpoint(phase="combat", pending_actions=[],
                        confirmed_event="battle_entered:" + self._pending_battle_id
                        if self._pending_battle_id else None)
                    logger.info("[入战识别] 已连续确认战斗控件与角色栏，等待实际结算")
                    return 0
            stage = self._post_battle_stage()
            next_stage_frames = (next_stage_frames + 1 if stage == next_stage else 1) if stage else 0
            next_stage = stage
            if stage is not None and next_stage_frames >= 2:
                logger.info(f"[出战检查] 已连续确认战斗后节点={stage}，转交关卡切换")
                self._finish_result_observation(departed=True)
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
        """返回继续按钮框、继续点击点及下一阶段是否就绪。"""
        self._terminal_route_screen = None
        deadline = time.monotonic() + (self.BATTLE_TIMEOUT if in_combat else self.REWARD_TRANSITION_TIMEOUT)
        started, hard_deadline = self._battle_wait_limits() if in_combat else (None, None)
        if in_combat:
            deadline = min(deadline, hard_deadline)
        reward_seen = not in_combat
        accelerated = False
        next_stage, next_stage_frames = None, 0
        # 明确奖励证据出现后，为结算设置独立截止时间。
        while True:
            self._check_stop()
            if in_combat and not reward_seen and time.monotonic() >= hard_deadline:
                break
            frame = self._capture_page_frame()
            button = self._locate_page_template(CWIMG.CONTINUE, frame)
            self._check_stop()
            if button is not None:
                screen = (self._vision.read_battle_screen(frame)
                    if frame is not None else self._vision.read_battle_screen())
                self._record_battle_screen(screen)
                self._finish_result_observation(screen, template=True,
                    context=bool(self._pending_battle_id and self._battle_entry_confirmed)
                        or reward_seen and self._last_battle_outcome in {"success", "failure"})
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
                    self._finish_result_observation(departed=True)
                    return None, None, True
            if time.monotonic() >= deadline:
                if (in_combat and not reward_seen and time.monotonic() < hard_deadline
                        and self._combat_screen_confirmed(frame)):
                    self.operator.sleep(0.5)
                    self._check_stop()
                    if self._combat_screen_confirmed():
                        deadline = min(time.monotonic() + self.BATTLE_TIMEOUT, hard_deadline)
                        logger.info(f"[战斗等待] 连续两帧仍在战斗，继续等待结算；"
                                    f"累计={time.monotonic() - started:.0f}s 总上限={self.BATTLE_MAX_WAIT_SECONDS}s")
                        continue
                break
            self.operator.sleep(min(0.5, max(0, deadline - time.monotonic())))
        self._check_stop()
        if reward_seen:
            self._fail_battle("result_timeout")
        return None, None, False

    def _reward_fast_reserve(self, coins):
        """只确认日常采购保留量，不执行经验、刷新或阵容门槛。"""
        level = self.get_level() if self.economy_config is not None else None
        if self.economy_config is not None and level is None:
            return None, None
        searching_main = bool(self.main_c and not self.main_c_first_fielded_confirmed
            and level is not None and level >= self.main_c_search_level)
        if self.economy_config is None:
            # 旧配置的金币门槛限制经验与刷新，不限制当前页买牌。
            return coins, 0
        args = dict(confirmed_battle_count=self._confirmed_battle_count,
            confirmed_battle_lower_bound=getattr(self, "_confirmed_battle_lower_bound", 0),
            recheck_level_lower_bound=getattr(self, "_economy_level_rechecked", False),
            previous_index=self._economy_stage_index, current_level=level)
        baseline = select_economy_stage(self.economy_config, **args)
        confirmed_coins = None
        if any(stage.upgrade_gold is not None and coins >= stage.upgrade_gold
               for stage in self.economy_config.stages[baseline.index + 1:]):
            self.operator.sleep(0.1)
            confirmed_coins = self.get_coins()
            if confirmed_coins != coins:
                return None, None
        selected = select_economy_stage(self.economy_config, coins=coins,
            confirmed_coins=confirmed_coins, **args)
        if selected.index != self._economy_stage_index:
            if not self._record_checkpoint(active_economy_stage_index=selected.index):
                return None, None
            self._economy_stage_index = selected.index
        reserve = (self.main_c_search_min_coins if searching_main else
                   self.economy_config.stages[selected.index].reserve_gold)
        return coins, reserve

    def _mark_reward_transaction_context_change(self, reason):
        self._reward_transaction_epoch = getattr(self, "_reward_transaction_epoch", 0) + 1
        ledger = getattr(self, "_reward_fast_page_ledger", None) or {}
        if ledger.get("pending") is not None:
            ledger["pending"]["context_change"] = reason

    def _reward_fast_transaction_context_valid(self, pending):
        evidence = pending["evidence"]
        return (evidence.page_key == (self._cycle_number, self._preparation_round)
            and evidence.preparation_id == getattr(self, "_preparation_id", None)
            and evidence.context_epoch == getattr(self, "_reward_transaction_epoch", 0)
            and evidence.layout_revision == self._layout_revision
            and self._pending_move is None and not self._placement_pending
            and not self._form_change_pending and not self._runtime_node_pending
            and self._selection_event_pending is None and self._equipment_choice_pending is None)

    def _reward_fast_capture_pending(self, card, coins, offer, was_pending, ledger):
        complete = (self._layout_valid and self._backend_identity_ready()
            and not self._bench_dirty and not self._dirty_slots
            and all(not self._slot_needs_scan(area, index)
                for area, slots in self._observations.items() for index in range(len(slots))))
        copies = self._held_purchase_copies(card.character.name) if complete else None
        evidence = RewardPurchaseEvidence(
            getattr(self, "_preparation_id", None), ledger["key"], str(uuid.uuid4()),
            card.slot_index, card.character.name, card.price, card.price_evidence, coins,
            getattr(self, "_last_coin_observation", None), copies,
            tuple((item.slot_index, item.character.name, item.price) for item in offer.cards),
            frozenset(ledger["attempted"]), self._layout_revision,
            getattr(self, "_reward_transaction_epoch", 0))
        return dict(evidence=evidence, card=card, offer=offer, was_pending=was_pending,
            baseline=(self._layout_revision,
                {area: tuple(slots) for area, slots in self._observations.items()}),
            quick_recheck_used=False, inventory_recheck_used=False,
            recovery_required=False, rebuild_receipt_used=False, resolution="pending")

    # ssyb：库存补证只结清已有动作，不能把现阵容当成购前事实。
    def _reward_fast_inventory_receipt(self, pending, offer, coins):
        """只允许一次有界的真实库存补读；当前阵容识别本身不能充当购前收据。"""
        evidence = pending["evidence"]
        pending["inventory_recheck_used"] = True  # 在全部界面读写或可能失败的操作前消耗额度。
        if not self._reward_fast_transaction_context_valid(pending):
            pending["resolution"] = "context_changed"
            return ActionResult.INDETERMINATE
        name = evidence.name
        other_pending = set(self._purchase_pending_names) - {name}
        self._purchase_scan_baseline = pending["baseline"]
        try:
            checked = self._recheck_purchased_characters({name},
                allow_verified_absent={name} if evidence.before_copies == 0 else ())
        finally:
            self._purchase_scan_baseline = None
            self._purchase_pending_names.update(other_pending)
        actual = self._held_purchase_copies(name) if checked and not self._bench_dirty else None
        pending["inventory_copies"] = actual
        trusted = (self._reward_fast_transaction_context_valid(pending)
            and reliable_balance(evidence.before_reading, evidence.before_coins)
            and reliable_balance(getattr(self, "_last_coin_observation", None), coins)
            and type(evidence.before_copies) is int and type(actual) is int)
        reliable_page = (offer.state in (ShopState.READY, ShopState.EMPTY)
            and not offer.reason.startswith("partial"))
        current = {(item.slot_index, item.character.name) for item in offer.cards}
        before = {(slot, name) for slot, name, _ in evidence.shop_signature}
        expected = before - {(evidence.slot_index, evidence.name)}
        page_matches = reliable_page and current in (before, expected)
        if trusted:
            delta, spent = actual - evidence.before_copies, evidence.before_coins - coins
            paid = type(evidence.price) is int and evidence.price > 0
            if delta == 1 and (paid and spent == evidence.price
                    and (not reliable_page or page_matches)
                    or not paid and spent >= 0 and page_matches):
                pending["resolution"] = "inventory_purchase_confirmed"
                return ActionResult.CONFIRMED
            if delta == 0 and spent == 0 and reliable_page and current == before:
                pending["resolution"] = "inventory_no_effect"
                return ActionResult.FAILED
        # 采购待确认复核可能清除当前已识别的角色名标记，
        # 但无权清除更早动作尚未确定的交易结果。
        self._purchase_pending_names.add(name)
        pending["resolution"] = "inventory_cannot_attribute"
        return ActionResult.INDETERMINATE

    def _reward_fast_pending_receipt(self, pending):
        evidence = pending["evidence"]
        offer, coins = pending["offer"], evidence.before_coins
        if pending["recovery_required"] or not self._reward_fast_transaction_context_valid(pending):
            pending["recovery_required"] = True
            return ActionResult.INDETERMINATE, offer, coins
        confirmation = ActionResult.INDETERMINATE
        if not pending["quick_recheck_used"]:
            pending["quick_recheck_used"] = True
            confirmation, offer, coins = self._reward_fast_purchase_receipt(
                pending["card"], evidence.before_coins, pending["offer"],
                before_reading=evidence.before_reading)
        if confirmation == ActionResult.INDETERMINATE and not pending["inventory_recheck_used"]:
            confirmation = self._reward_fast_inventory_receipt(pending, offer, coins)
            # 库存读取会关闭商店；须先结清当前动作，再重新开店，
            # 之后才可对新的自然商店页执行输入。
            if confirmation != ActionResult.INDETERMINATE and not self._set_shop_open(True):
                confirmation = ActionResult.INDETERMINATE
            if not self._reward_fast_transaction_context_valid(pending):
                self._purchase_pending_names.add(evidence.name)
                confirmation = ActionResult.INDETERMINATE
        if confirmation == ActionResult.INDETERMINATE:
            pending["recovery_required"] = True
        return confirmation, offer, coins

    def _resume_reward_fast_transaction_after_rebuild(self):
        """外层唯一重建只可提供一次新的商店观测收据，不能重放购买输入。"""
        ledger = getattr(self, "_reward_fast_page_ledger", None) or {}
        pending = ledger.get("pending")
        if pending is None:
            return True
        if pending["rebuild_receipt_used"] or not self._reward_fast_transaction_context_valid(pending):
            return False
        pending["rebuild_receipt_used"] = True
        evidence = pending["evidence"]
        if not self._set_shop_open(True):
            return False
        try:
            confirmation, offer, _ = self._reward_fast_purchase_receipt(
                pending["card"], evidence.before_coins, pending["offer"],
                before_reading=evidence.before_reading)
        finally:
            closed = self._set_shop_open(False)
        if confirmation == ActionResult.INDETERMINATE or not closed:
            return False
        name = evidence.name
        if confirmation == ActionResult.CONFIRMED:
            ledger["receipts"][name] = ledger["receipts"].get(name, 0) + 1
            self._preparation_shop_counts["purchases"] += 1
            self._post_purchase_placement_pending = self._equipment_dirty = True
        elif not pending["was_pending"] and name not in ledger["receipts"]:
            self._purchase_pending_names.discard(name)
        pending["resolution"] = "rebuild_" + confirmation.value
        ledger.setdefault("transactions", []).append(pending)
        ledger["pending"] = None
        return self._record_checkpoint(phase="preparation", pending_actions=[])

    # ssyb：速战采购仍保留逐笔收据，免费合成须独立核实。
    def _reward_fast_purchase_receipt(self, card, before_coins, offer, *, before_reading=None):
        """用商店变化与现场余额认证交易，绝不在此打开角色面板。"""
        signature = {(item.slot_index, item.character.name) for item in offer.cards}
        expected = signature - {(card.slot_index, card.character.name)}
        last = None
        for attempt in range(2):
            self._check_stop()
            after = self._scan_store()
            coins = self._read_coins_after_action(before_coins, card.price, "purchase")
            reliable = (after.state in (ShopState.READY, ShopState.EMPTY)
                        and not after.reason.startswith("partial"))
            current = {(item.slot_index, item.character.name) for item in after.cards}
            trusted = (reliable_balance(before_reading, before_coins)
                and reliable_balance(getattr(self, "_last_coin_observation", None), coins))
            if not trusted or type(coins) is not int or coins < 0 or coins > before_coins:
                last = None
            elif (after.state == ShopState.FULL and coins == before_coins
                    and type(card.price) is int and card.price > 0):
                return ActionResult.FAILED, after, coins
            elif reliable and current == signature and coins == before_coins:
                # 判定输入未生效，仍须两次完整的价格与卡片身份观测，
                # 并取得可靠的操作前后余额；不能仅因两次文字识别
                # 返回相同整数，就清除状态未知的交易。
                noop = purchase_noop_evidence(card, offer, after, before_coins, coins,
                    before_reading, getattr(self, "_last_coin_observation", None),
                    allow_zero_unpriced=False)
                if noop is not None and last == ("unchanged", noop):
                    return ActionResult.FAILED, after, coins
                last = ("unchanged", noop) if noop is not None else None
            elif reliable and current == expected:
                spent = before_coins - coins
                exact_paid = type(card.price) is int and card.price > 0 and spent == card.price
                if exact_paid or last == ("changed", coins):
                    return ActionResult.CONFIRMED, after, coins
                # 免费、折扣或未知费用需要第二个独立页面/余额证据。
                if card.price is None or spent <= card.price:
                    last = ("changed", coins)
                else:
                    last = None
            else:
                last = None
            if attempt == 0:
                self.operator.sleep(0.3)
        return ActionResult.INDETERMINATE, after, coins

    def _reward_fast_shopping(self):
        """只采购自然商店这一页，真实合成和落位留待下一普通准备期。"""
        self._check_stop()
        key = (self._cycle_number, self._preparation_round)
        ledger = getattr(self, "_reward_fast_page_ledger", None)
        if ledger is not None and ledger.get("pending") is not None and ledger["key"] != key:
            return ShoppingResult(ActionResult.INDETERMINATE,
                reason="reward_fast_transaction_context_changed")
        if ledger is not None and ledger.get("pending") is not None and ledger["pending"]["recovery_required"]:
            return ShoppingResult(ActionResult.INDETERMINATE,
                reason="reward_fast_transaction_recovery_required")
        if ledger is None or ledger["key"] != key:
            ledger = dict(key=key, attempted=set(), receipts={}, demand=None, pending=None,
                          attempted_count=0, completed=False, free_stale_names=set())
            self._reward_fast_page_ledger = ledger
        if ledger["completed"]:
            return self._last_shopping_result
        prior = dict(self._preparation_shop_counts)
        attempted = purchased = 0
        result, reason = ActionResult.CONFIRMED, "reward_fast_natural_page"
        self._shopping_active = True
        try:
            if not self._set_shop_open(True):
                result, reason = ActionResult.INDETERMINATE, "reward_fast_shop_not_open"
            else:
                offer = None
                if ledger["pending"] is not None:
                    pending = ledger["pending"]
                    card, was_pending = pending["card"], pending["was_pending"]
                    confirmation, offer, _ = self._reward_fast_pending_receipt(pending)
                    if confirmation == ActionResult.INDETERMINATE:
                        result, reason = confirmation, "reward_fast_transaction_recovery_required"
                    else:
                        ledger.setdefault("transactions", []).append(pending)
                        ledger["pending"] = None
                        name = card.character.name
                        if confirmation == ActionResult.CONFIRMED:
                            ledger["receipts"][name] = ledger["receipts"].get(name, 0) + 1
                            purchased += 1
                            self._post_purchase_placement_pending = True
                            self._equipment_dirty = True
                        else:
                            # 免费购买可能已经触发合成，而商店卡片仍然显示；
                            # 应暂时冻结该角色，等待正常的脏区域复核，
                            # 不再要求购买可能已经不存在的额外副本。
                            if card.price in (None, 0) and offer.state != ShopState.FULL:
                                ledger.setdefault("free_stale_names", set()).add(name)
                            if not was_pending and name not in ledger["receipts"]:
                                self._purchase_pending_names.discard(name)
                        if not self._record_checkpoint(phase="preparation", pending_actions=[]):
                            result, reason = ActionResult.INDETERMINATE, "reward_fast_checkpoint_failed"
                if result == ActionResult.CONFIRMED and offer is None:
                    offer = self._read_shopping_offer(None)
                if result != ActionResult.CONFIRMED:
                    pass
                elif offer.state == ShopState.FULL:
                    reason = "reward_fast_bench_full"
                elif (offer.state not in (ShopState.READY, ShopState.EMPTY)
                        or offer.reason.startswith("partial")):
                    result, reason = ActionResult.INDETERMINATE, "reward_fast_shop_unknown"
                else:
                    if ledger["demand"] is None:
                        goals = self._purchase_goals()
                        for name, stars in self._role_purchase_goals().items():
                            goals[name] = max(goals.get(name, 0), stars)
                        ledger["demand"] = reward_fast_cached_demand(goals, self._observations)
                    targets = [card for card in offer.cards
                        if ledger["demand"].get(card.character.name, 0) > ledger["receipts"].get(card.character.name, 0)
                        and card.character.name not in ledger.get("free_stale_names", ())
                        and not card.character.is_locked and not card.character.is_npc]
                    targets.sort(key=lambda card: (
                        not (card.character.name == self.main_c and not self.main_c_first_fielded_confirmed),
                        -(card.character.priority or 0), card.slot_index))
                    coins = self.get_coins() if targets else None
                    reserve = None
                    if targets and coins is not None:
                        coins, reserve = self._reward_fast_reserve(coins)
                    if targets and (coins is None or reserve is None):
                        result, reason = ActionResult.INDETERMINATE, "reward_fast_economy_unknown"
                    for planned in targets if result == ActionResult.CONFIRMED else ():
                        self._check_stop()
                        name = planned.character.name
                        identity = (planned.slot_index, name)
                        if (identity in ledger["attempted"]
                                or name in ledger.get("free_stale_names", ())
                                or ledger["receipts"].get(name, 0) >= ledger["demand"].get(name, 0)):
                            continue
                        card = next((item for item in offer.cards
                            if (item.slot_index, item.character.name) == identity), None)
                        if card is None:
                            continue
                        # 沿用普通商店的未知价格单次尝试，之后必须读取实际支出。
                        if card.price is not None and not can_afford_purchase(coins, card.price, reserve):
                            continue
                        actions = sum(prior[k] for k in ("attempts", "refreshes", "experiences")) + attempted
                        if actions >= self.shopping_budget["actions"]:
                            reason = "reward_fast_action_budget"
                            break
                        if prior["purchases"] + purchased >= self.shopping_budget["purchases"]:
                            reason = "reward_fast_purchase_budget"
                            break
                        if not self._record_checkpoint(phase="purchase_pending", pending_actions=[
                                f"奖励速战购买复核：{name} 商店槽位{card.slot_index}"]):
                            result, reason = ActionResult.INDETERMINATE, "reward_fast_checkpoint_failed"
                            break
                        ledger["attempted"].add(identity)
                        ledger["attempted_count"] += 1
                        attempted += 1
                        was_pending = name in self._purchase_pending_names
                        ledger["pending"] = self._reward_fast_capture_pending(
                            card, coins, offer, was_pending, ledger)
                        self._purchase_pending_names.add(name)
                        self._bench_dirty = True
                        self._invalidate_character_evidence(name, "reward_fast_purchase", level_changed=False)
                        if not self.operator.click_point(*card.target, after_sleep=0.5):
                            result, reason = ActionResult.FAILED, "reward_fast_purchase_click_failed"
                            break
                        self._coin_action_costs.clear()
                        self.operator.move_to(0.5, 0.5)
                        confirmation, after, balance = self._reward_fast_purchase_receipt(
                            card, coins, offer, before_reading=ledger["pending"]["evidence"].before_reading)
                        if confirmation == ActionResult.INDETERMINATE:
                            result, reason = confirmation, "reward_fast_purchase_not_confirmed"
                            break
                        ledger["pending"]["resolution"] = "shop_" + confirmation.value
                        ledger.setdefault("transactions", []).append(ledger["pending"])
                        ledger["pending"] = None
                        offer, coins = after, balance
                        if confirmation == ActionResult.FAILED:
                            if card.price in (None, 0) and offer.state != ShopState.FULL:
                                ledger.setdefault("free_stale_names", set()).add(name)
                                logger.info(f"[奖励速战] {name} 免费/未知价画面未变，"
                                            "本页不再点击同名槽，保留库存待下普通准备期复核")
                            if not was_pending and name not in ledger["receipts"]:
                                self._purchase_pending_names.discard(name)
                            if offer.state == ShopState.FULL:
                                reason = "reward_fast_bench_full"
                                break
                            continue
                        ledger["receipts"][name] = ledger["receipts"].get(name, 0) + 1
                        purchased += 1
                        self._post_purchase_placement_pending = True
                        self._equipment_dirty = True
                        if not self._record_checkpoint(phase="preparation", pending_actions=[]):
                            result, reason = ActionResult.INDETERMINATE, "reward_fast_checkpoint_failed"
                            break
                        logger.info(f"[奖励速战] 已确认购买 {name}；余额={coins} 保留={reserve}，下轮统一整备")
        finally:
            self._shopping_active = False
            self._preparation_shop_counts = dict(prior,
                attempts=prior["attempts"] + attempted, purchases=prior["purchases"] + purchased)
            if sys.exc_info()[0] is None and not self._set_shop_open(False):
                result, reason = ActionResult.INDETERMINATE, "reward_fast_shop_not_closed"
        self._last_shopping_result = ShoppingResult(result, attempted, purchased, 0, 0, reason)
        if result == ActionResult.CONFIRMED:
            ledger["completed"] = True
        logger.info(f"[奖励速战] 自然商店结束：{self._last_shopping_result}")
        return self._last_shopping_result

    def battle(self, *, reward_fast=False) -> bool:
        self._check_stop()
        reward_fast = bool(reward_fast and is_reward_fast_round(
            self.reward_fast_rounds, self._preparation_round))
        index, battle_box = self.operator.wait_any_img([CWIMG.BATTLE, CWIMG.SKIP],
                                                       timeout=self.BATTLE_BUTTON_TIMEOUT, interval=0.5)
        if battle_box is None or index not in (0, 1):
            self._fail_battle("battle_button_missing")
        if index == 0 and not reward_fast:
            if not self._ensure_battle_roster():
                if not self._confirmed_frontline():
                    self._fail_battle("no_confirmed_frontline")
                prepared = self.prepare_for_battle()
                if prepared.state == Readiness.BLOCKED:
                    self._fail_battle("preparation_" + prepared.reason)
            # 扫描与布阵可能同时改变界面和按钮位置。
            battle_box = self.operator.wait_img(CWIMG.BATTLE, timeout=self.BATTLE_BUTTON_TIMEOUT)
        self._check_stop()
        if self._placement_pending or self._pending_move is not None:
            self._fail_battle("preparation_pending_move_unresolved")
        hard_reason = self._preparation_hard_blocker(reward_fast=reward_fast, skip_reward=index == 1)
        if hard_reason:
            self._fail_battle("preparation_" + hard_reason)
        if (index == 0 and not reward_fast and self._preparation_deadline is not None
                and time.monotonic() >= self._preparation_deadline):
            if not self._ensure_battle_roster():
                self._fail_battle("preparation_" + self._assess_existing_roster().blocked_reason)
        if reward_fast:
            logger.info(f"[奖励速战] 回合={self._preparation_round} 沿用现有阵容出战；完整整备留到下一准备阶段")
        else:
            self._report_preflight("battle" if index == 0 else "skip_reward")
        self._last_battle_outcome = "unknown"
        self._last_health_read = None
        self._health_read_attempts = 0
        if index == 0:
            # 同一未解决战斗绝不创建新身份标识。
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
        # 已确认的跳过切换也会结束本轮准备，
        # 但不计为真实战斗，也不借用战斗奖励领取状态。
        self._preparation_departure_confirmed = True
        if index == 0:
            # 此独立战斗输入后，明确的战斗、结算
            # 或两帧一致的战后节点可认证已进入战斗。
            self._battle_entry_confirmed = True
            if not self._record_checkpoint(confirmed_event="battle_entered:" + self._pending_battle_id):
                self._fail_battle("battle_checkpoint_not_saved")
        if entry == 4:
            self._confirm_completed_battle("post_battle_node")
            return True
        if entry == 0:
            # Q 证明进入战斗，不能证明自动战斗已启用。V 会切换
            # 当前设置，较晚读取后按 V 可能反而关闭自动战斗。
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

    def _wait_stage_ready(self, img_list, deadline=None):
        # 过渡标题可能在稳定等待期间改变；
        # 仅在固定等待窗口内重新观测到同一阶段后操作。
        deadline = self._page_navigation_limit(self.STAGE_TRANSITION_TIMEOUT, deadline)
        handled = set()
        while True:
            self._check_stop()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return -1
            first = self._probe_runtime_page()
            if first[0] == "terminal":
                self._terminal_route_screen = (time.monotonic(), first[1])
                return -2
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return -1
            if first[0] == "unknown":
                self._supply_pause(min(0.5, remaining))
                continue
            self._supply_pause(min(self.STAGE_SETTLE_SECONDS, remaining))
            current = self._probe_runtime_page()
            self._check_stop()
            if current[0] == "terminal":
                self._terminal_route_screen = (time.monotonic(), current[1])
                return -2
            if time.monotonic() >= deadline:
                return -1
            if self._same_runtime_page(first, current):
                self._accept_runtime_node_departure(first, current)
                phase, payload = current
                if phase in {"equipment_choice", "selection_event", "shop_probability"}:
                    key = (phase, payload if phase == "selection_event" else None)
                    if key in handled:
                        return -1
                    handled.add(key)
                    if not self._handle_page_overlay(current, deadline):
                        return -1
                    continue  # 弹窗处理完成后，重新取得整张帧再分类。
                template = None
                if phase == "node":
                    template = payload
                elif phase == "advance":
                    template = {"点击空白处关闭": CWIMG.CLICK_BLANK, "下一步": CWIMG.NEXT_STEP}.get(payload[0])
                elif phase == "preparation":
                    template = CWIMG.FOLD if payload is not None else CWIMG.PREPARATION_STAGE
                elif phase == "main_menu":
                    template = CWIMG.START_CURRENCY_WARS
                if template not in img_list:
                    continue
                index = img_list.index(template)
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
        transition_deadline = self._page_navigation_limit(self.STAGE_TRANSITION_TIMEOUT)
        stage_index = self._wait_stage_ready(img_list, transition_deadline)
        prev_stage_name: StageName | None = None
        advance_attempts = 0

        while True:  # 用无限循环 + 内部break控制退出
            self._check_stop()
            if stage_index == -2:
                terminal = self._terminal_route_screen
                self._terminal_route_screen = None
                return self.handle_game_over(None, first_screen=terminal[1] if terminal else None)
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
            # 页面恢复期间保留不确定的选择输入。
            if img_path in (CWIMG.ENCOUNTER_NODE, CWIMG.REPLENISH_STAGE,
                            CWIMG.FORTUNE_TELLER, CWIMG.SELECT_INVEST_STRATEGY):
                if self._runtime_node_pending == img_path:
                    raise RuntimeError("节点选择尚未确认，转交页面恢复")
            # 执行状态处理函数
            try:
                with self._page_navigation_scope(transition_deadline):
                    self._check_page_navigation_deadline()
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
            stage_index = self._wait_stage_ready(img_list, transition_deadline)

    def handle_main_menu(self, _: StageName | None) -> bool:
        """处理主菜单界面的逻辑"""
        store = self._session_store
        if store is not None and (store.checkpoint is None or not store.checkpoint.finalized
                                  or getattr(store, "_finalization_pending", False)):
            for _ in range(2):
                self._check_stop()
                if store.finalize("returned_to_main_menu"):
                    break
            else:
                raise RuntimeError(f"对局结束检查点保存失败：{store.last_error}")
        self.is_game_over = True
        return True

    def _handle_fortune_teller_after_battle(self, _: StageName | None) -> bool:
        """战斗结束后触发命运卜者事件"""
        if not self.handle_fortune_teller():
            raise RuntimeError("命运卜者事件未确认完成，停止重复选择")
        self._check_page_navigation_deadline()
        # 成功也可能表示已交接下一事件。交回页面分派，准备页上的
        # 商店需求由 _set_shop_open 重新认证，旧页面坐标没有授权。
        return False

    def handle_stage_transitioned(self) -> bool:  # NOQA  # 保留原有静态检查指令。
        """关卡切换完成后的处理逻辑，默认不操作；子类可重写以添加逻辑。
        在关卡切换流程完成后、正式进入下一轮游戏循环前调用。
        返回值：True 表示继续游戏循环，False 表示中止任务。
        """
        return True

    def handle_characters_updated(self):
        """角色信息更新后的处理逻辑（如有）。默认实现为无操作，可重写此方法以添加额外逻辑。"""
        if all(c is None for c in self.on_field_character + self.off_field_character + self.in_hand_character):
            # 如果所有角色信息均为None，打开商店界面购买角色
            self._empty_roster_needs_shop = True

    def handle_game_over(self, _: StageName | None, *, first_screen=None) -> bool:
        """导航已认证的终局页面；仅在主菜单结束记录。"""
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
                # 生命值 OCR 已使用新帧，绝不能复用旧按钮。
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

    def _wait_post_battle_departure(self, excluded_stage, *, deadline=None):
        """一次确认输入后，等待连续两帧相同的下一阶段，不重复发送输入。"""
        deadline = self._page_navigation_limit(self.ENTRY_TRANSITION_TIMEOUT, deadline)
        next_stage, next_stage_frames = None, 0
        while True:
            self._check_stop()
            if time.monotonic() >= deadline:
                return None
            stage = self._post_battle_stage(allow_preparation=True, deadline=deadline)
            if time.monotonic() >= deadline:
                return None
            if stage == excluded_stage:
                stage = None
            next_stage_frames = (next_stage_frames + 1 if stage == next_stage else 1) if stage else 0
            next_stage = stage
            if stage is not None and next_stage_frames >= 2:
                # 两次 _post_battle_stage 均从新帧取得同一下一阶段。
                self._accept_runtime_node_departure(("node", stage), ("node", stage))
                return stage
            if time.monotonic() >= deadline:
                return None
            self.operator.sleep(min(0.5, max(0, deadline - time.monotonic())))

    def handle_click_blank(self, _: StageName | None) -> bool:
        """仅关闭一次已确认的强敌提示，然后等待离开。"""
        deadline = self._page_navigation_limit(self.ENTRY_TRANSITION_TIMEOUT)
        self._check_page_navigation_deadline(deadline)
        prompt = self.operator.locate(CWIMG.CLICK_BLANK, trace=False)
        self._check_page_navigation_deadline(deadline)
        if prompt is None:
            # 页面可能已在阶段稳定等待期间推进。
            return False
        if not self.operator.click_point(0.5, 0.70, after_sleep=1,
                                         tag="关闭已确认的强敌来袭提示"):
            raise RuntimeError("强敌提示关闭失败")
        stage = self._wait_post_battle_departure(CWIMG.CLICK_BLANK, deadline=deadline)
        if stage is not None:
            logger.info(f"[强敌提示] 已确认退场，下一阶段={stage}")
            return False
        self._vision.capture_sample("boss_notice_departure_timeout",
            {"evidence": "no_confirmed_next_stage_after_boss_notice"}, critical=True)
        raise RuntimeError("强敌提示确认后仍未退场")

    def handle_invest_strategy(self, prev_stage: StageName | None) -> bool:
        """处理投资策略选择界面的逻辑"""
        deadline = self._page_navigation_limit(self.EVENT_TRANSITION_TIMEOUT)
        self._check_page_navigation_deadline(deadline)
        collection = self.operator.locate(CWIMG.COLLECTION)
        self._check_page_navigation_deadline(deadline)
        self._invalidate_roster_evidence("investment_reward_unknown")
        self._check_page_navigation_deadline(deadline)
        self._record_runtime_node_input(CWIMG.SELECT_INVEST_STRATEGY)
        selected = (self.operator.click_box(collection) if collection is not None else
                    self.operator.click_point(0.5, 0.3, after_sleep=0.5, tag="选择中间的投资策略"))
        if not selected:
            return False  # False 也可能已经生效，保留收据，不能改点另一选项。
        self._confirm_invest_strategy(deadline)
        return False

    def _confirm_invest_strategy(self, deadline):
        """仅使用现有独立确认按钮，不重复投资策略的选择输入。"""
        self._check_page_navigation_deadline(deadline)
        if self._invest_simple_equipment_pending:
            return  # 后续装备输入结果不明，仅由新页面证据解除，不能再点奖励。
        confirmation = self.operator.locate(IMG.ENSURE2)
        self._check_page_navigation_deadline(deadline)
        if confirmation is not None:
            self.operator.click_box(confirmation, after_sleep=1)
        with self._page_navigation_scope(deadline):
            self.post_invest_strategy()

    def post_invest_strategy(self, strategy_name: str | None = None):
        """投资策略选择后的后续处理逻辑"""
        deadline = self._page_navigation_limit(self.EVENT_TRANSITION_TIMEOUT)
        self._check_page_navigation_deadline(deadline)
        if self._invest_simple_equipment_pending:
            return
        equipment_choice = self._read_equipment_choice()
        self._check_page_navigation_deadline(deadline)
        if self._equipment_choice_pending is not None or (
                equipment_choice is not None and equipment_choice.present):
            if not self._handle_equipment_choice(equipment_choice, deadline):
                raise RuntimeError("投资策略后的装备选择尚未完成")
            return
        if strategy_name == "阿哈大悦" or self.operator.locate(CWIMG.SELECT_SIMPLE_EQUIPMENT):
            self._check_page_navigation_deadline(deadline)
            if self._runtime_node_pending is None:
                self._record_runtime_node_input(CWIMG.SELECT_INVEST_STRATEGY)
            self._invest_simple_equipment_pending = True
            self.operator.click_point(0.8, 0.25, after_sleep=1, tag="阿哈大悦选择装备4")

    def handle_replenish_stage(self, _: StageName | None):
        """处理补给阶段的逻辑"""
        self._check_page_navigation_deadline()
        self._invalidate_roster_evidence("replenish_reward_unknown")
        self._check_page_navigation_deadline()
        self._record_runtime_node_input(CWIMG.REPLENISH_STAGE)
        if not self.operator.click_point(0.53, 0.52, after_sleep=1):  # 选择固定位置
            return False
        self._runtime_node_receipt["selection_returned"] = True
        self._check_page_navigation_deadline()
        self._runtime_node_receipt["confirmation_attempted"] = True
        self.operator.click_point(0.88, 0.91, after_sleep=1)  # 点击确认按钮
        self._invalidate_equipment_resources("replenish_reward")
        self._invalidate_level()
        self._check_page_navigation_deadline()
        self.detect_silver_wolf_lv999()  # 也许选到银狼了
        return False

    def handle_encounter_node(self, _: StageName | None) -> bool:
        """处理遭遇节点的逻辑"""
        deadline = self._page_navigation_limit(self.ENTRY_TRANSITION_TIMEOUT)
        self._check_page_navigation_deadline(deadline)
        self._record_runtime_node_input(CWIMG.ENCOUNTER_NODE)
        if not self.operator.click_point(0.35, 0.50, after_sleep=1):  # 简单难度
            raise RuntimeError("遭遇节点选择失败")
        self._runtime_node_receipt["selection_returned"] = True
        self._check_page_navigation_deadline(deadline)
        self._runtime_node_receipt["confirmation_attempted"] = True
        if not self.operator.click_point(0.56, 0.84, after_sleep=1):  # 选择按钮中心
            raise RuntimeError("遭遇节点确认失败")
        if self._wait_post_battle_departure(CWIMG.ENCOUNTER_NODE, deadline=deadline) is not None:
            return False
        self._vision.capture_sample("encounter_selection_timeout",
                                     {"evidence": "no_confirmed_next_stage_after_node_selection"})
        raise RuntimeError("遭遇节点确认后仍未退场，停止重复选择")

    def handle_fortune_teller(self):
        """处理命运卜者事件的逻辑"""
        return self._handle_selection_event((0.22, 0.34, 0.85, 0.4),
                                            self.strategy_special_events.get("命运卜者", ""), "命运卜者")

    def _invalidate_selection_event_evidence(self, event_name):
        """按事件影响失效；保留已有缺口、动作收据及每个槽位的真实读取时间。"""
        self._mark_reward_transaction_context_change("selection_event:" + event_name)
        if event_name == "头号玩家":
            self._invalidate_character_evidence(Characters.SilverWolfLV999.name,
                "silver_wolf_event_input", level_changed=False)
            self._bench_dirty = True
        elif event_name in {"领航员", "盛会之星"}:
            # 选择已上场成员的羁绊/巨星增益，不增减角色、不合成、不移动后台。
            # 上场动作已标脏移动两端，并会在事件退场后真实重读。
            # 不清理其他脏槽、不补写新时间、不将已有未知证据恢复为已确认。
            self._effective_targets_key = None
            self._preparation_assessment_cache = None
            self._formation_plan = ()
            self._formation_plan_stage = None
            logger.info(f"[事件局部复核] 事件={event_name} 保留角色身份、星级和布局；"
                        "沿用移动两端及已有待确认槽位，刷新装备和消费证据")
        else:
            # 试炼、占卜和未知事件仍可能发放角色或引起合成，保留完整复核。
            self._invalidate_roster_evidence("selection_event:" + event_name)
        # 输入可能已经生效但返回 False/抛异常；必须在输入前撤销效果缓存，
        # 后续只确认退场时也不会漏掉复制装备、折扣等变化。
        self._invalidate_equipment_resources("selection_event")
        self._invalidate_level()
        self._coin_action_costs.clear()
        self._last_coins_read = self._last_coin_observation = None
        self._experience_before = None

    def _handle_selection_event(self, ocr_region, keyword, event_name=""):
        deadline = self._page_navigation_limit(self.EVENT_TRANSITION_TIMEOUT)
        self._check_stop()
        if time.monotonic() >= deadline:
            return False
        if self._selection_event_pending is not None:
            pending_event, pending_target = self._selection_event_pending
            self._last_selection_sent = True
            # 新事件标题的一次调用不能证明旧选择已离开；旧确认循环会
            # 用两张新鲜帧认证交接，调用方随后重新定位当前事件。
            completed = self._confirm_selection_event(pending_target, pending_event, deadline=deadline)
            if pending_event == event_name or not completed:
                return completed
            # 旧事件的离开收据不能证明新事件已完成；读取本次
            # 处理器的选项前，须重新确认当前事件身份。
            self._check_page_navigation_deadline(deadline)
            frame = self._capture_page_frame()
            if self._observe_selection_return(frame) != ("selection_event", event_name):
                return False
        self._last_selection_sent = False
        # 由 > 分隔的组按顺序具有优先级；组内空格仍表示别名。
        priority_groups = [group.split() for group in keyword.replace("＞", ">").split(">")]
        for attempt in range(2):
            self._check_stop()
            if time.monotonic() >= deadline:
                return False
            boxes = self.operator.ocr_boxes(from_x=ocr_region[0], from_y=ocr_region[1],
                                            to_x=ocr_region[2], to_y=ocr_region[3])
            self._check_stop()
            if time.monotonic() >= deadline:
                return False
            logger.info(f"事件={event_name} 关键词={keyword!r} 复核={attempt + 1} "
                        f"候选={[box.source[:120] for box in boxes or ()]}")
            target = next((box for group in priority_groups for box in boxes or ()
                           if any(k in box.source.strip() for k in group)), None)
            if target is None and boxes and not any(priority_groups):
                target = boxes[-1]
                logger.info(f"事件 {event_name} 未配置关键词，采用末项默认规则")
            if target is None:
                if attempt == 0:
                    self.operator.sleep(min(0.3, max(0, deadline - time.monotonic())))
                    continue
                self._vision.capture_sample("event_keyword_mismatch", {"event": event_name,
                    "keyword": keyword, "options": [box.source for box in boxes or ()]})
                logger.warning(f"事件 {event_name} 未找到配置关键词 {keyword!r}，停止选择")
                return False
            if time.monotonic() >= deadline:
                return False
            self._invalidate_selection_event_evidence(event_name)
            if time.monotonic() >= deadline:
                return False
            if event_name == "命运卜者":
                self._record_runtime_node_input(CWIMG.FORTUNE_TELLER)
            # 点击返回 False、抛异常或后续截图失败均不能证明没有输入。
            self._last_selection_sent = True
            self._selection_event_pending = (event_name, target.source)
            if not self.operator.click_box(target, after_sleep=0.5):
                return False
            return self._confirm_selection_event(target.source, event_name, deadline=deadline)
        return False

    # Yukki：每次确认都重新核验事件标题与离开证据。
    def _confirm_selection_event(self, target_name, event_name, *, deadline=None):
        """只重试当前事件的确认按钮，不重复选择卡片；退场仍需可见证据。"""
        started = time.monotonic()
        deadline = self._page_navigation_limit(self.EVENT_TRANSITION_TIMEOUT, deadline)
        self._check_stop()
        if time.monotonic() >= deadline:
            return False
        # 通用按钮可能已属于下一个事件；包含首次确认在内的
        # 每次输入，都须由新鲜且标题一致的截图授权。
        attempts, same_frames, ready_frames = 0, 0, 0
        last_sent = time.monotonic()
        previous_next_event, next_event_frames = "", 0
        previous_departure, departure_frames = None, 0
        frames, slowest, last_phase, frame = 0, 0.0, "unobserved", None
        for _ in range(40):
            self._check_stop()
            if time.monotonic() >= deadline:
                break
            observed_at = time.monotonic()
            frame = self._capture_page_frame()
            phase, payload = self._observe_selection_return(frame)
            still_confirm = self._locate_page_template(CWIMG.CONFIRM_SELECTION, frame) if frame is not None else None
            frames += 1
            elapsed = time.monotonic() - observed_at
            slowest = max(slowest, elapsed)
            if phase != last_phase or elapsed >= 1:
                logger.debug(f"[事件退场观察] 事件={event_name} 帧={frames} 阶段={phase} "
                             f"确认按钮={still_confirm is not None} 耗时={elapsed:.2f}s")
            last_phase = phase
            ready = phase == "preparation"
            ready_frames = ready_frames + 1 if ready else 0
            next_event = payload if phase == "selection_event" and event_name else ""
            self._check_stop()
            candidate = next_event if next_event and next_event != event_name else ""
            next_event_frames = (next_event_frames + 1 if candidate == previous_next_event
                                 else 1) if candidate else 0
            previous_next_event = candidate
            departed = (not still_confirm and phase in {
                "equipment_choice", "terminal", "node", "advance", "main_menu"})
            departure_frames = (departure_frames + 1 if previous_departure is not None
                and self._same_runtime_page(previous_departure, (phase, payload)) else 1) if departed else 0
            previous_departure = (phase, payload) if departed else None
            # 在预算内开始的读取可以完成离开状态的确认。
            # 预算到期后，该读取不能授权再次截图或发送任何输入。
            if (next_event_frames >= 2 or departure_frames >= 2
                    or (not still_confirm and ready_frames >= 2 and not next_event)):
                logger.info(f"事件 {event_name} 已确认选择 {target_name!r}")
                self._last_selection_sent = False
                self._selection_event_pending = None
                if event_name == "命运卜者" and self._runtime_node_pending == CWIMG.FORTUNE_TELLER:
                    self._runtime_node_pending = None
                return True
            if time.monotonic() >= deadline:
                break
            same_frames = same_frames + 1 if next_event == event_name and event_name and still_confirm else 0
            if (same_frames >= 2 and (attempts == 0 or
                    event_name == "领航员" and attempts < 3
                    and time.monotonic() - last_sent >= 2.0)):
                self._check_stop()
                # 使用本轮定位的新按钮；下一事件、标题未知时禁止重试。
                attempts += 1
                logger.info(f"[事件确认] 事件={event_name} 确认重试={attempts}/3，不重复选择")
                if time.monotonic() >= deadline:
                    break
                self.operator.click_box(still_confirm, after_sleep=0.5)
                last_sent, same_frames = time.monotonic(), 0
            self.operator.sleep(min(0.5, max(0, deadline - time.monotonic())))
        logger.warning(f"[事件退场确认] 事件={event_name} 结果=unconfirmed 阶段={last_phase} "
                       f"帧数={frames} 准备连续帧={ready_frames} 下一事件连续帧={next_event_frames} "
                       f"确认次数={attempts} 耗时={time.monotonic() - started:.2f}s 最慢帧={slowest:.2f}s")
        self._vision.capture_sample("event_not_dismissed", {"event": event_name,
            "confirm_attempts": attempts, "phase": last_phase, "frames": frames,
            "ready_frames": ready_frames, "next_event_frames": next_event_frames,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "slowest_frame_seconds": round(slowest, 3)}, frame=frame)
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

    def detect_special_event(self, frame=None) -> str:
        """检测精确事件标题；页面分类传入截图时绝不另取一帧 OCR。"""
        if frame is None:
            result = self.operator.ocr(from_x=0.49, from_y=0.038, to_x=0.60, to_y=0.11)
        else:
            try:
                width, height = frame.size
                region = frame.crop((round(0.49 * width), round(0.038 * height),
                                     round(0.60 * width), round(0.11 * height)))
                result = self._vision._engine_ocr(region, minimum_confidence=0.9)
            except ThreadStoppedError:
                raise
            except Exception as error:
                self._check_stop()
                logger.debug(f"[事件标题] 同帧读取未确认：{type(error).__name__}")
                return ""
        if not result:
            return ""
        labels = {row[1].strip() for row in result
                  if isinstance(row, (tuple, list)) and len(row) >= 2 and isinstance(row[1], str)}
        matched = []
        for event, (title, handler) in self.special_events.items():
            if title in labels:
                matched.append(event)
        return matched[0] if len(matched) == 1 else ""

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
            self._bench_dirty = True
            self._purchase_pending_names.discard(name)
        return result

    def handle_special_event(self):
        with self._pause_formation_for_auxiliary():
            return self._handle_special_event_impl()

    def _handle_special_event_impl(self):
        """使用有界且可中断的循环处理连锁事件。"""
        for _ in range(8):
            self._check_stop()
            event = self.detect_special_event()
            if not event:
                return
            logger.info(f"检测到特殊事件：{event}")
            if not self.special_events[event][1]():
                raise RuntimeError("特殊事件处理失败")
            self._coin_action_costs.clear()
            self._equipment_dirty = True
            self._invalidate_level()
        raise RuntimeError("特殊事件连续处理达到上限")

    def _read_preparation_round(self):
        """读取两个当前准备阶段标签，绝不根据战斗次数推断。"""
        if self._preparation_round is not None or self._round_read_attempts >= 2:
            return self._preparation_round
        self._round_read_attempts += 1
        answers, texts = [], []
        rois = ((0.105, 0.02, 0.18, 0.135), (0.205, 0.02, 0.285, 0.105))
        for frame in range(2):
            candidates = set()
            for index, roi in enumerate(rois):
                self._check_stop()
                rows = self._vision.operator_ocr(from_x=roi[0], from_y=roi[1], to_x=roi[2], to_y=roi[3],
                                         grayscale=False, confidence=0.9, trace=False)
                raw = " | ".join(str(row[1]).strip() for row in rows or ())
                texts.append(raw)
                # 分别认证每种布局中的标签；打开商店后被遮挡的
                # 第二标题不能当成额外回合。
                answer = parse_preparation_round(raw) if "备战阶段" in re.sub(r"\s", "", raw) else None
                if answer is not None:
                    candidates.add((index, answer))
            answers.append(candidates if len({value for _, value in candidates}) == 1 else set())
            if frame == 0:
                self.operator.sleep(0.15)
        stable = answers[0] & answers[1]
        if stable:
            self._preparation_round = next(iter(stable))[1]
            self._preparation_round_context = (self._cycle_number,
                self._last_completed_battle_id, self._preparation_departure_confirmed)
            if self._session_context_tracking:
                self._record_checkpoint(observed_round=self._preparation_round)
        logger.info(f"[备战关卡] round={self._preparation_round} OCR={texts}")
        return self._preparation_round

    def _opening_action_allowed(self, action):
        """仅依据已确认的当前准备回合解锁出售或刷新。"""
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
            rows = self._vision.operator_ocr(from_x=0.115, from_y=0.76, to_x=0.195, to_y=0.94,
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

    def _recheck_economy_evidence(self):
        """每个准备阶段只补读一次关卡和等级，未知历史不由回合反推。"""
        self._check_stop()
        if self._economy_evidence_recheck_attempted:
            return self._economy_level_rechecked
        self._economy_evidence_recheck_attempted = True
        self._economy_level_rechecked = False
        deadline = self._preparation_deadline
        if deadline is not None and time.monotonic() >= deadline:
            return False
        if not self._set_shop_open(False):
            return False
        self._preparation_round = None
        previous_attempts = self._round_read_attempts
        self._round_read_attempts = 0
        try:
            current_round = self._read_preparation_round()
        finally:
            # 保险补读不重新授予常规关卡读取额度。
            self._round_read_attempts = max(previous_attempts, 2)
        self._check_stop()
        if deadline is not None and time.monotonic() >= deadline:
            return False
        if not self._set_shop_open(True):
            return False
        self._invalidate_level()
        level = self.get_level()
        self._economy_level_rechecked = (current_round is not None and level is not None
            and (deadline is None or time.monotonic() < deadline))
        logger.info(f"[经济复核] round={current_round} L={level} "
                    f"confirmed={self._economy_level_rechecked} "
                    f"battle_lower_bound={self._confirmed_battle_lower_bound}；本准备阶段最多一次")
        return self._economy_level_rechecked

    def _economy_context(self, level, coins):
        # 只有可能触发永久金币阶段升级时，才需要第二次读取。
        # 普通决策仅使用一次真实的动作后余额。
        self._check_stop()
        if coins is None:
            return None
        baseline = select_economy_stage(self.economy_config,
            confirmed_battle_count=self._confirmed_battle_count,
            confirmed_battle_lower_bound=getattr(self, "_confirmed_battle_lower_bound", 0),
            recheck_level_lower_bound=getattr(self, "_economy_level_rechecked", False),
            previous_index=self._economy_stage_index, current_level=level)
        confirmed_coins = None
        if any(stage.upgrade_gold is not None and coins >= stage.upgrade_gold
               for stage in self.economy_config.stages[baseline.index + 1:]):
            self.operator.sleep(0.1)
            confirmed_coins = self.get_coins()
            if confirmed_coins != coins:
                logger.warning(f"[经济决策] 金币读数冲突={coins}/{confirmed_coins}；复读后继续，不中止任务")
                reread = self.get_coins()
                stable = reread is not None and reread == confirmed_coins
                coins = reread if reread is not None else confirmed_coins if confirmed_coins is not None else coins
                confirmed_coins = coins if stable else None
        self._economy_balance = coins
        selected = select_economy_stage(self.economy_config,
            confirmed_battle_count=self._confirmed_battle_count,
            confirmed_battle_lower_bound=getattr(self, "_confirmed_battle_lower_bound", 0),
            recheck_level_lower_bound=getattr(self, "_economy_level_rechecked", False),
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
                experience_required=progress[1] if progress else None,
                xp_cost=self._read_action_cost("experience"))
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

    def _recheck_purchased_characters(self, names, *, allow_verified_absent=()):
        """重读已购角色及新落位，复用未受影响的身份。
        基线仅适用于普通购买交易。
        事件、布局变化、移动、证据冲突或首轮失败，都会要求完整读取后，才允许布阵或出售使用结果。
        """
        baseline = getattr(self, "_purchase_scan_baseline", None)
        allow_verified_absent = set(allow_verified_absent)
        try:
            self._check_stop()
            if not self._set_shop_open(False):
                return False
            reusable = (isinstance(baseline, tuple) and len(baseline) == 2
                and baseline is getattr(self, "_purchase_scan_baseline", None)
                and baseline[0] == self._layout_revision and self._layout_valid
                and self._pending_move is None and not self._runtime_node_pending
                and not self._form_change_pending and isinstance(baseline[1], dict)
                and all(area in baseline[1] and len(baseline[1][area]) == len(slots)
                    for area, slots in self._observations.items()))
            before = baseline[1] if reusable else None
            # 无关观测发生变化，是另一动作的证据，
            # 不能据此继续把较旧快照视为权威状态。
            if reusable:
                reusable = all(old is current or old.character is not None and old.character.name in names
                    for area, slots in self._observations.items()
                    for old, current in zip(before[area], slots))
            self._complete_incremental_field_observation()
            missing_marker = self._field_observed_at is None
            full_scan = ((baseline is not None and not reusable) or not self._layout_valid
                         or bool(allow_verified_absent))
            if missing_marker and not full_scan:
                logger.info("[购后增量核实] 缺全场完成标记，按真实逐槽收据补缺；不作废未受影响观测")
            for attempt in range(2):
                self._check_stop()
                # 以本次扫描开始时判断旧证据是否过期；串行读取自身可能超过60秒。
                # 保留逐槽真实时间、脏标记与交易检查，不续签旧观测。
                scan_started = time.monotonic()
                incremental = reusable and not full_scan and attempt == 0
                vacancies = self._read_bench_empty_observations()
                if incremental and any(before["in_hand"][index].state == SlotState.KNOWN
                        and before["in_hand"][index].character.name not in names for index in vacancies):
                    # 购买不可能使无关的已占用槽位消失。
                    full_scan, incremental = True, False
                if full_scan:
                    # 不明来源变化不能只切换局部循环标志；撤销旧布局/身份，
                    # 重建真实后台坐标后再读取所有场上角色及备战席。
                    self._invalidate_roster_evidence("purchase_recheck_conflict")
                    self.refresh_character(equip=False, recover_layout=True)
                    vacancies = self._read_bench_empty_observations()
                # 完整身份扫描仍必须遵守当前锁定槽位；
                # 点击它们不会出现角色面板。
                # 完整恢复不能丢弃布局重建后刚读取的双帧空位证据。
                overrides = dict(vacancies)
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
                        if (not full_scan and ((area, index) in self._dirty_slots
                                or character is not None and character.name in names
                                or self._slot_needs_scan(area, index, scan_started))):
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
                self._complete_incremental_field_observation()
                unexpected = incremental and any(obs.state == SlotState.KNOWN
                    and obs.character.name not in names and (old.character is None
                        or old.character.name != obs.character.name)
                    for area, slots in self._observations.items()
                    for old, obs in zip(before[area], slots))
                matches = {name: [obs for slots in self._observations.values() for obs in slots
                    if obs.character is not None and obs.character.name == name] for name in names}
                if (not unexpected and not self._bench_dirty and all(observation_identity(obs) is not None
                        for obs in self._observations["in_hand"]) and all(
                        (all(obs.state == SlotState.KNOWN and observation_identity(obs) is not None
                             and type(obs.stars) is int for obs in matches[name]) if matches[name] else
                         name in allow_verified_absent and full_scan and self._layout_valid
                         and self._backend_identity_ready()
                         and self._held_purchase_copies(name) == 0
                         and all(self._complete_slot_observation(obs) and (area, index) not in self._dirty_slots
                             for area, slots in self._observations.items()
                             for index, obs in enumerate(slots))) for name in names)
                        and all(not self._slot_needs_scan(area, index, scan_started)
                            for area in ("on_field", "off_field")
                            for index, obs in enumerate(self._observations[area]))):
                    return True
                full_scan = True
                if attempt == 0:
                    logger.info("[购后增量核实] 观察不完整或与交易前记录冲突，恢复完整识别")
                    self._check_stop()
                    self.operator.sleep(0.3)
            # 让外层恢复路径仍能看到未解决的交易。
            self._invalidate_roster_evidence("purchase_recheck_unresolved")
            self._purchase_pending_names.update(names)
            return False
        finally:
            self._bench_scan_overrides = None
            self._purchase_scan_baseline = None

    def _recover_full_shop_offer(self):
        """考虑安全经验输入前，先关闭备战区满员遮罩。"""
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
        """区分可采购补齐的业务缺口与缺失证据。"""
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
            # 场上角色的备战区副本属于合成材料。
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
        # 备战区满员时，只有明确观测到可合成，才允许接收新卡。
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
        before_progress = self._experience_before[1] if self._experience_before else None
        expected_cost = getattr(self, "_experience_cost_before", self.SHOP_EXPERIENCE_COST)
        for _ in range(2):
            self._check_stop()
            level = self.get_level()
            coins = self._read_coins_after_action(before_coins, expected_cost, "experience")
            change = validate_coin_change(before_coins, coins,
                expected_spend=expected_cost, allow_zero=True)
            paid_confirmed = (change.accepted is True and change.delta is not None and change.delta < 0)
            advanced = type(level) is int and level > before_level
            if not paid_confirmed and level == before_level and before_progress is not None:
                raw = getattr(self._last_level_read, "raw_text", "")
                progress = parse_experience_progress(raw, level=level) if raw else None
                if progress is None:
                    progress = self._read_experience_progress(level, recognize_cap=True)
                advanced = (progress is not None and progress[1] == before_progress[1]
                    and progress[0] > before_progress[0])
            if type(level) is int and type(coins) is int and level >= before_level:
                if advanced or paid_confirmed:
                    if change.reason != "expected_spend":
                        logger.info(f"[金币校验] action=experience before={before_coins} after={coins} "
                            f"reason={change.reason} progress={advanced}；按现场结果继续")
                    self._coin_action_costs.pop("experience", None)
                    return level, coins
            self.operator.sleep(0.3)
            self._invalidate_level()
        self._coin_action_costs.pop("experience", None)
        logger.warning(f"[金币校验] action=experience 未观察到经验进展，before={before_coins} "
            f"after={coins}；结束本轮购物后继续任务")
        return None

    def _read_coins_after_action(self, before, cost, action):
        """对付费和免费读数排序，其他变化仍保留观测余额。"""
        ledger = getattr(self, "_reward_fast_page_ledger", None) or {}
        if action != "purchase" and ledger.get("pending") is not None:
            self._mark_reward_transaction_context_change("later_spending:" + action)
        coins = self.get_coins()
        change = validate_coin_change(before, coins, expected_spend=cost, allow_zero=True)
        if coins is None or change.accepted is not False:
            return coins
        first = self._last_coin_observation
        self.operator.sleep(0.1)
        reread = self.get_coins()
        second = self._last_coin_observation
        # 注入或测试读取器可能提供整数，而没有 OCR 证据。
        # 此时绝不复用其他输入留下的过期观测。
        if (first is not None and second is not None and first.value == coins
                and second.value == reread):
            chosen = choose_coin_read((first, second), before=before,
                expected_spend=cost, allow_zero=True)
            coins = chosen.value if chosen.value is not None else reread
            self._last_coin_observation = chosen
        elif reread is not None:
            coins = reread
        self._last_coins_read = coins
        actual = before - coins if type(before) is int and type(coins) is int else None
        logger.warning(f"[金币校验] action={action} expected={cost} actual={actual} "
            f"before={before} after={coins} reread={reread}；记录差异并按现场余额继续")
        return coins

    def _confirm_completed_battle(self, evidence):
        if not self._pending_battle_id or not self._battle_entry_confirmed:
            return False
        battle_id = self._pending_battle_id
        if self._session_store is not None:
            if not self._session_store.confirm_battle(battle_id):
                # 使用同一 ID 重试，绝不通过第二笔交易推进。
                if not self._session_store.confirm_battle(battle_id):
                    self._fail_battle("battle_checkpoint_not_saved")
            checkpoint = self._session_store.checkpoint
            self._confirmed_battle_count = checkpoint.confirmed_battle_count
            self._confirmed_battle_lower_bound = checkpoint.confirmed_battle_lower_bound
            self._equipment_battles_since_check = checkpoint.equipment_battles_since_check
        else:
            if self._confirmed_battle_count is not None:
                self._confirmed_battle_count += 1
            self._confirmed_battle_lower_bound += 1
            self._equipment_battles_since_check += 1
        self._last_completed_battle_id = battle_id
        self._pending_battle_id = None
        self._battle_entry_confirmed = False
        logger.info(f"[真实战斗] id={battle_id} confirmed={self._confirmed_battle_count} "
                    f"lower_bound={self._confirmed_battle_lower_bound} "
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

    def _shopping_finish_after_recheck(self, offer, level, coins, context, *, action_costs=None):
        """结合真实持有量、余额与最后一页有用商品判断是否结束。"""
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
            return None  # 保留主循环的终局冲刺升级策略。
        decision = next_economy_action(level=level, coins=coins, target_level=target,
            reserve_gold=reserve, purchase_reserve_gold=0 if all_in else self.economy_config.purchase_reserve_gold,
            xp_cost=(self._read_action_cost("experience") if action_costs is None else action_costs["experience"]),
            roll_cost=(self._read_action_cost("refresh") if action_costs is None else action_costs["refresh"]),
            upgrade_allowed=allowed, has_purchase_targets=bool(unmet),
            space_safe=self._economy_space_safe(unmet), needs_prepare=needs_prepare,
            first_main_search=searching_main, gate_has_purchase_targets=actionable,
            first_main_purchase_reserve_gold=self.main_c_search_purchase_reserve_gold)
        if decision.action == "roll" and not self._opening_action_allowed("refresh"):
            return "opening_round_unknown" if self._preparation_round is None else "opening_refresh_locked"
        return decision.reason if decision.action in ("save", "prepare") else None

    def _shopping_cleanup_state(self):
        """购后扫描可更新星级；布局、移动、事件和经济条件变化则不可复用。"""
        return (self._layout_revision, self._equipment_resource_revision,
            self._preparation_attempts, self._preparation_moves, self._preparation_round,
            self._economy_stage_index, self._level_cache, self.main_c_first_fielded_confirmed,
            tuple(sorted(self._observed_prices.items())))

    def _shopping_finish_before_reopen(self, offer, level, context, progress, snapshot):
        """仅授权结束购物；任何消费仍须展开商店并重新读取。"""
        self._check_stop()
        before_coins, before_state, costs = snapshot
        coins = progress.get("coins")
        reading = self._last_coin_observation
        if (offer is None or context is None or not progress.get("closed")
                or progress.get("result") != ActionResult.CONFIRMED or progress.get("reason")
                or progress.get("sale_attempts", 0) or self._coin_shop_open is not False
                or type(level) is not int or self._level_cache != level
                or type(coins) is not int or coins != before_coins
                or reading is None or not reading.reliable or reading.value != coins
                or not self._layout_valid or self._bench_dirty or self._dirty_slots
                or self._placement_pending or self._pending_move is not None
                or self._purchase_pending_names or self._form_change_pending or self._runtime_node_pending
                or before_state != self._shopping_cleanup_state()
                or any(type(costs.get(action)) is not int or costs[action] < 0
                       for action in ("experience", "refresh"))
                or any(observation_identity(obs) is None
                       for slots in self._observations.values() for obs in slots)):
            return None
        reason = self._shopping_finish_after_recheck(offer, level, coins, context, action_costs=costs)
        self._check_stop()
        return reason

    def _credit_shopping_time(self):
        """购物期间暂停准备阶段限制；棋盘清理期间不暂停。"""
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
        """仅从真实且已核对的观测统计等价一星副本数。"""
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

    # ssyb：采购数量只依据本周期已经结清的真实收据。
    def _settle_demand_purchases(self, cycle, progress):
        """将本轮购买用于布阵或经验门槛前，先观测这一轮购物结果。"""
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
        if self._preparation_round == (3, 7):
            # 库存确认和首次上场是两项独立事实。
            # 这里只结清本周期已核实的购买收据。
            self._purchase_pending_names.difference_update(receipts)
            names = getattr(self, "_final_purchase_names", set())
            names.update(receipts)
            self._final_purchase_names = names
            self._post_purchase_placement_pending = True
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
            if not self._preparation_budget_spent():
                self.place_character()
            elif self._preparation_round == (3, 7):
                self._finish_final_purchases()
            self._check_stop()
            if self._placement_pending or self._pending_move is not None:
                progress["reason"] = "candidate_needs_preparation"
                return
            sale = self.sell_character()
            progress["sale_attempts"] = sale.attempted
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
                              spendable_coins=None, transaction_coins=None,
                              verified_failed_cards=()):
        """跨页面保留临时购买账本，在真实边界确认。
        每页结束后读取一次金币。
        角色商品消失仅允许下一次购物输入；星级门槛、布阵与出售必须依赖真实库存证据，绝不能依赖预测合成或预测空位。
        """
        progress.update(offer=offer, closed=False, coins=None, reset_offer=False, sale_attempts=0,
                        result=ActionResult.CONFIRMED, reason="", stall=None)
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
                   and (c.slot_index, c.character.name, c.price) not in verified_failed_cards
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
                if card.price is not None and not can_afford_purchase(spendable_coins, card.price, 0):
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
                    # 同页另一商品可能立即合成，
                    # 即使这个更高优先级角色需要空闲备战区槽位。
                    continue
            noop_state = capture_purchase_noop_state(self, card.character)
            noop_before_copies = self._held_purchase_copies(name)
            noop_before_reading = self._last_coin_observation
            noop_before_coins = (transaction_coins if transaction_coins is not None
                else getattr(noop_before_reading, "value", None))
            progress["coins"] = None
            self._record_checkpoint(phase="purchase_pending", pending_actions=[
                f"搜牌购买复核：{name} 商店槽位{card.slot_index}"])
            self._purchase_pending_names.add(name)
            progress["attempts"] += 1
            logger.info(f"[连续采购] 尝试购买 商店[{card.slot_index}] {name} 价格={card.price}")
            self._bench_dirty = True
            self._invalidate_character_evidence(name, "purchase_input", level_changed=False)
            if not self.operator.click_point(*card.target, after_sleep=0.5):
                progress.update(result=ActionResult.FAILED, reason="purchase_click_failed")
                return
            self._coin_action_costs.clear()
            self._check_stop()
            self.operator.move_to(0.5, 0.5)
            signature = {(c.slot_index, c.character.name) for c in offer.cards}
            expected = signature - {(card.slot_index, name)}
            changed = unchanged = False
            noop_frames = []
            for _ in range(2):
                self._check_stop()
                after = self._scan_store()
                noop_frames.append(after)
                self._check_stop()
                reliable = after.state in (ShopState.READY, ShopState.EMPTY) and not after.reason.startswith("partial")
                current = {(c.slot_index, c.character.name) for c in after.cards}
                changed = reliable and current == expected
                unchanged = reliable and current == signature
                if changed:
                    break
                self.operator.sleep(0.3)
            if unchanged:
                observations = []
                for frame in noop_frames:
                    balance = self.get_coins()
                    observations.append(purchase_noop_evidence(card, offer, frame,
                        noop_before_coins, balance, noop_before_reading, self._last_coin_observation,
                        allow_zero_unpriced=True))
                ticket = dict(card=card, before_coins=noop_before_coins,
                    before_copies=noop_before_copies, was_pending=noop_state["pending"],
                    observations=observations, state=noop_state, verified=False)
                progress["stall"] = ticket
                verified = resolve_page_purchase_noop(self, ticket)
                if ticket.get("closed"):
                    progress["closed"] = True
                if not verified:
                    progress.update(result=ActionResult.INDETERMINATE, reason="purchase_not_confirmed")
                    return
                ticket["verified"] = True
                progress["coins"] = balance
                if ticket.get("closed"):
                    # 免费或价格未知的输入已经通过真实库存核实，
                    # 不得恢复旧阵容或再次点击原购买目标。
                    progress["closed"] = True
                    if ticket.get("inventory_confirmed"):
                        receipts[name] = receipts.get(name, 0) + 1
                        cycle["spaces"] = max(0, cycle["spaces"] - 1)
                        cycle["baseline"] = None
                        self._purchase_pending_names.add(name)
                        progress["offer"] = None
                        logger.info(f"[连续采购] {name} 店牌尚未退场，但真实库存已确认新增；只计本次输入一份")
                    else:
                        skipped_slots.add(card.slot_index)
                        progress["offer"] = after
                        logger.info(f"[连续采购] {name} 真实库存确认未成交，退出旧页并跳过槽位{card.slot_index}")
                    if receipts:
                        self._settle_demand_purchases(cycle, progress)
                    if not receipts and not self._purchase_pending_names:
                        self._record_checkpoint(phase="preparation", pending_actions=[])
                    return
                skipped_slots.add(card.slot_index)
                offer = after
                progress["offer"] = offer
                logger.info(f"[连续采购] {name} 两帧完整牌面及可靠余额未变，已确认未成交，当前页跳过槽位{card.slot_index}")
                continue
            receipts[name] = receipts.get(name, 0) + 1
            if spendable_coins is not None:
                if card.price is not None:
                    spendable_coins -= card.price
                else:
                    # 未知价格只影响这次购前预算；继续输入前改用现场余额。
                    spendable_coins = self.get_coins()
                    if spendable_coins is None:
                        progress.update(result=ActionResult.INDETERMINATE, reason="unknown_coins")
            cycle["spaces"] -= 1
            offer = after
            progress["offer"] = offer if changed else None
            if progress["reason"]:
                settle_now = True
                break
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
            if progress["coins"] is None:
                progress["coins"] = self.get_coins()
            if progress["coins"] is None:
                progress.update(result=ActionResult.INDETERMINATE, reason="unknown_coins")
            logger.info(f"[连续采购] 本页结束，累计待复核={receipts} 实际金币={progress['coins']}；保留商店等待经济判断")
        if not receipts and not self._purchase_pending_names:
            self._record_checkpoint(phase="preparation", pending_actions=[])


    def _read_shopping_offer(self, offer):
        """复用当前页；识别未知时按原间隔补读一次，恢复决策留给调用方。"""
        if offer is None:
            offer = self._scan_store()
        if offer.state == ShopState.UNKNOWN:
            self.operator.sleep(0.3)
            offer = self._scan_store()
        return offer

    def _read_shopping_economy(self):
        """商店重开后按顺序读取金币、等级，并采用经济阶段复核后的余额。"""
        balance = self.get_coins()
        level = self.get_level()
        context = self._economy_context(level, balance) if level is not None else None
        balance = self._economy_balance if context is not None else balance
        return level, balance, context

    def _finish_final_purchases(self):
        """每个终局准备期只收尾一次，且仅处理已核实的新购角色。

        此处独立的绝对截止时间不补偿购物耗时，也不因恢复而延长。
        普通布阵和装备检查已消耗的额度保持不变。
        """
        self._check_stop()
        if self._preparation_round != (3, 7) or not self._preparation_budget_spent():
            return False
        if (self._purchase_pending_names or self._pending_move is not None
                or self._placement_pending or self._runtime_node_pending
                or self._selection_event_pending or self._equipment_choice_pending
                or self._form_change_pending or not self._layout_valid
                or not self._backend_identity_ready() or self._population_conflict()
                or self._dirty_slots or self._bench_dirty):
            return False
        bought = getattr(self, "_final_purchase_names", set())
        needed = {self.main_c} if self._main_c_in_hand() else set()
        for role in self._role_evaluations().values():
            if self._role_placement_unresolved(role):
                needed.update(role.bench_candidates)
        names = needed & bought
        if not names:
            return False
        context = getattr(self, "_final_finish_context", None)
        if context is None:
            context = dict(deadline=time.monotonic() + 60, attempts=0,
                           names=frozenset(names), done=False, permitted=None)
            self._final_finish_context = context
        if context["done"]:
            return False
        changed = False
        self._final_finish_active = True
        try:
            with self._page_navigation_scope(context["deadline"]):
                for _ in range(3):
                    self._check_stop()
                    if time.monotonic() >= context["deadline"] or context["attempts"] >= 3:
                        break
                    if not self._set_shop_open(False):
                        break
                    if (self._pending_move is not None or self._placement_pending
                            or self._runtime_node_pending or self._selection_event_pending
                            or self._equipment_choice_pending or self._purchase_pending_names):
                        break
                    candidates = []
                    stage = self._formation_stage()
                    if self.formation_config is not None and stage is not None:
                        planned = plan_formation_sequence(self.formation_config, stage,
                            self._observations, self.max_team_size, (self.main_c,),
                            excluded_moves=self._excluded_moves())
                        if planned:
                            m = planned[0]
                            candidates = [(m.source_area, m.source_index, m.target_area, m.target_index)]
                    else:
                        for index, obs in enumerate(self._observations["in_hand"]):
                            if obs.state != SlotState.KNOWN or obs.character.name not in context["names"]:
                                continue
                            for area, position in (("on_field", Positioning.OnField),
                                                   ("off_field", Positioning.OffField)):
                                if obs.character.position not in (position, Positioning.OnOffField):
                                    continue
                                candidates.extend(("in_hand", index, area, i)
                                    for i, target in enumerate(self._observations[area])
                                    if target.state == SlotState.EMPTY)
                    moved = False
                    for move in candidates:
                        if context["attempts"] >= 3 or time.monotonic() >= context["deadline"]:
                            break
                        area, index, target_area, target_index = move
                        obs = self._observations[area][index]
                        if (area != "in_hand" or target_area not in ("on_field", "off_field")
                                or obs.state != SlotState.KNOWN
                                or obs.character.name not in context["names"]):
                            continue
                        context["permitted"] = move
                        moved = self.swap_character_between_areas(*move)
                        context["permitted"] = None
                        changed |= moved
                        if moved or self._pending_move is not None or self._placement_pending:
                            break
                    if not moved or self._pending_move is not None or self._placement_pending:
                        break
            return changed
        finally:
            context["done"] = True
            context["permitted"] = None
            self._final_finish_active = False
            logger.info(f"[终局购后收尾] 尝试={context['attempts']}/3 主C已上场={self.main_c_first_fielded_confirmed}；不续预算")

    def _tracked_purchase_demand_page(self, offer, **kwargs):
        """只保留尚未结清的收据，不改变副本计数算法。"""
        cycle = kwargs.setdefault("cycle", {})
        # 价格未知的购买发生后，开店时记录的单个余额值即已过期。
        # 每张收据改用对应的最新金币观测 CoinRead；该观测仍须可靠，
        # 并与输入后两次独立读取的结果一致。
        kwargs["transaction_coins"] = None
        self._active_demand_cycle = cycle
        try:
            return self._purchase_demand_page(offer, **kwargs)
        finally:
            self._active_demand_cycle = None
            if cycle.get("receipts"):
                self._deferred_purchase_cycle = cycle
            elif getattr(self, "_deferred_purchase_cycle", None) is cycle:
                self._deferred_purchase_cycle = None

    # Yukki：异常恢复不能把未确认的额外输入并入旧账。
    def _recover_purchase_accounting(self):
        cycle = getattr(self, "_deferred_purchase_cycle", None)
        if not cycle or not cycle.get("receipts"):
            return True
        receipts = dict(cycle["receipts"])
        pending_before = set(self._purchase_pending_names)
        try:
            confirmed = self._recheck_purchased_characters(set(receipts))
        finally:
            self._purchase_pending_names.update(pending_before)
        if not confirmed:
            return False
        if (self._pending_move is not None or self._placement_pending or self._bench_dirty
                or any(self._held_purchase_copies(name) != cycle["before"][name] + count
                       for name, count in receipts.items())):
            self._purchase_pending_names.update(receipts)
            return False
        # 严格相等检查可防止把额外且不确定的输入误归到先前
        # 已确认收据中，也防止误清除该输入的待确认状态。
        self._preparation_shop_counts["purchases"] += sum(receipts.values())
        self._purchase_pending_names.difference_update(receipts)
        if self._preparation_round == (3, 7):
            self._final_purchase_names.update(receipts)
        cycle.clear()
        self._deferred_purchase_cycle = None
        logger.info(f"[采购记账恢复] 已按真实库存补记且仅记一次：{receipts}")
        return True

    def _shopping_final_round(self):
        """应用攻略经济规则前，先花费最终准备阶段的金币。"""
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
            if result == ActionResult.CONFIRMED and not self._ensure_shopping_observations(force=True):
                result, reason = ActionResult.INDETERMINATE, "shopping_evidence_deferred"
            if result == ActionResult.CONFIRMED and getattr(self, "_final_purchase_names", None):
                # 库存可能直到后续恢复时才确定；重新核实页面和阵容后，
                # 仍使用同一个仅执行一次的收尾上下文。
                with self._shopping_cleanup_window():
                    self._finish_final_purchases()
            while result == ActionResult.CONFIRMED:
                self._check_stop()
                # 终局经济只豁免普通优化超时，未确认交易、移动和页面
                # 仍须沿用原收据复核；不能为消费重放它们或降级成就绪。
                if self._pending_move is not None and not self._resolve_pending_move():
                    result, reason = ActionResult.INDETERMINATE, "pending_move_unresolved"
                    break
                self._reconcile_form_change_pending()
                if (self._placement_pending or self._purchase_pending_names
                        or self._form_change_pending or self._runtime_node_pending
                        or self._selection_event_pending is not None
                        or self._equipment_choice_pending is not None):
                    result, reason = ActionResult.INDETERMINATE, "shopping_evidence_deferred"
                    break
                if not self._set_shop_open(True):
                    result, reason = ActionResult.INDETERMINATE, "shop_not_open_after_recheck"
                    break
                self._invalidate_level()
                coins = self.get_coins()
                level = self.get_level()
                if level is None or coins is None:
                    result, reason = ActionResult.INDETERMINATE, "unknown_level" if level is None else "unknown_coins"
                    break
                xp_cost, roll_cost = self._read_action_cost("experience"), self._read_action_cost("refresh")
                if xp_cost is None or roll_cost is None:
                    result, reason = ActionResult.INDETERMINATE, "unknown_action_cost"
                    break
                progress = (self._read_experience_progress(level, recognize_cap=True)
                            if coins >= xp_cost else None)
                progress_receipt = ((self._experience_context_key(level), progress)
                                    if progress is not None else None)
                decision = next_final_round_action(level=level, coins=coins,
                    experience_current=progress[0] if progress else None,
                    experience_required=progress[1] if progress else None,
                    level_capped=progress == (0, 0), xp_cost=xp_cost)
                logger.info(f"[终局运营] L={level} gold={coins} xp={progress} "
                    f"next_level={decision.target_level} upgrade_cost={decision.upgrade_cost} "
                    f"action={decision.action} reason={decision.reason}")
                if decision.action == "save" and coins == 0:
                    # 即使没有足够的付费下一等级预算，
                    # 也须检查当前免费角色与免费刷新。
                    decision = replace(decision, action="shop")
                if decision.action in ("recover", "save"):
                    result = ActionResult.INDETERMINATE if decision.action == "recover" else ActionResult.CONFIRMED
                    reason = decision.reason
                    break
                if decision.action == "buy_xp":
                    # 仅承诺一次完全可负担的整级升级，并确认每次输入。
                    for _ in range(decision.purchases):
                        self._check_stop()
                        current_cost = self._read_action_cost("experience")
                        if (current_cost is None or current_cost != xp_cost
                                or coins < current_cost):
                            reason = "final_round_cost_changed"
                            break
                        current_progress, progress_receipt = progress_receipt, None
                        if not self._buy_experience(level, final_round=True,
                                                    confirmed_progress=current_progress):
                            result, reason = ActionResult.FAILED, "experience_click_failed"
                            break
                        experiences += 1
                        confirmed = self._confirm_experience(level, coins)
                        if confirmed is None:
                            result, reason = ActionResult.CONFIRMED, "experience_no_progress"
                            break
                        level, coins = confirmed
                        if level >= decision.target_level:
                            break
                    if result != ActionResult.CONFIRMED:
                        break
                    if reason == "experience_no_progress":
                        break
                    if reason == "final_round_cost_changed":
                        # 下一整级的报价已失效；重新循环可能在初读低价、
                        # 输入前高价之间永远往返，也可能买出不可负担的半级。
                        # 保留已确认的经验结果，以明确无进展原因有限结束。
                        break
                    if level < decision.target_level:
                        result, reason = ActionResult.INDETERMINATE, "final_round_upgrade_not_confirmed"
                        break
                    with self._shopping_cleanup_window():
                        if not self._set_shop_open(False):
                            self._fail_battle("final_round_preparation_not_confirmed")
                        self.update_max_team_size()
                        if not self._preparation_budget_spent():
                            self.place_character()
                    if not self._ensure_shopping_observations(force=True):
                        result, reason = ActionResult.INDETERMINATE, "shopping_evidence_deferred"
                        break
                    offer = None
                    skipped_slots.clear()
                    continue
                offer = self._read_shopping_offer(offer)
                if offer.state == ShopState.FULL:
                    self._bench_full = True
                    offer = self._recover_full_shop_offer()
                if offer is None or offer.state == ShopState.UNKNOWN:
                    result, reason = ActionResult.INDETERMINATE, "unknown"
                    break
                page = dict(attempts=0, purchases=0)
                # 保留攻略的有用角色列表，但不保留金币。
                try:
                    self._tracked_purchase_demand_page(offer, max_attempts=5, max_purchases=5,
                        skipped_slots=skipped_slots, progress=page, spendable_coins=coins,
                        transaction_coins=coins)
                finally:
                    # 后续移动或截图异常不能清除已经确认的购买，
                    # 也不能抹去已经尝试输入的事实。
                    attempted += page["attempts"]
                    purchased += page["purchases"]
                offer = None if page["closed"] or page["reset_offer"] else page["offer"]
                if page["reason"]:
                    if (page["reason"] in {"main_c_placement", "role_placement", "candidate_needs_preparation"}
                            and self._pending_move is None and not self._placement_pending):
                        if not self._ensure_shopping_observations(force=True):
                            result, reason = ActionResult.INDETERMINATE, "shopping_evidence_deferred"
                            break
                    else:
                        result, reason = page["result"], page["reason"]
                        break
                if page["purchases"]:
                    if not self._ensure_shopping_observations(force=True):
                        result, reason = ActionResult.INDETERMINATE, "shopping_evidence_deferred"
                        break
                    continue  # 出售或合成可能已改变下一等级预算。
                if page["closed"]:
                    # 免费或价格未知的输入失败后，可能曾关闭商店以核验
                    # 真实库存；判断是否还能按普通终局规则刷新前，
                    # 须重新开店并读取当前费用。
                    # 保留本页已跳过槽位和累计动作计数。
                    continue
                if page["coins"] is not None:
                    coins = page["coins"]
                roll_cost = self._read_action_cost("refresh")
                if roll_cost is None:
                    result, reason = ActionResult.INDETERMINATE, "unknown_roll_cost"
                    break
                if coins < roll_cost:
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
                # 即使确认失败，也计算此次输入；恢复不能重新授予该额度。
                refreshes += 1
                if not self.operator.press_key("d"):
                    result, reason = ActionResult.FAILED, "refresh_click_failed"
                    break
                self._coin_action_costs.clear()
                self.operator.sleep(0.5)
                after = self._scan_store()
                if after.state == ShopState.FULL:
                    after = self._recover_full_shop_offer()
                if after is None or after.state == ShopState.UNKNOWN:
                    result, reason = ActionResult.INDETERMINATE, "unknown"
                    break
                after_coins = self._read_coins_after_action(coins, roll_cost, "refresh")
                self._coin_action_costs.pop("refresh", None)
                if after_coins is None:
                    result, reason = ActionResult.INDETERMINATE, "final_round_refresh_not_confirmed"
                    break
                new_signature = tuple((card.slot_index, card.character.name) for card in after.cards)
                logger.info(f"[终局运营] 搜牌={prior['refreshes'] + refreshes}/{self.FINAL_ROUND_REFRESH_LIMIT} "
                            f"金币={coins}->{after_coins} 牌面变化={signature != new_signature}")
                if after_coins == coins:
                    unchanged_refreshes = unchanged_refreshes + 1 if signature == new_signature else 0
                    if unchanged_refreshes >= 2:
                        result, reason = ActionResult.CONFIRMED, "refresh_no_progress"
                        break
                else:
                    unchanged_refreshes = 0
                # 刷新实际花费金币时，即使商品完全相同也算进展。
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
        """先应用强制最终回合规则，再应用攻略购物规则。"""
        self._check_stop()
        if not self._recover_purchase_accounting():
            self._last_shopping_result = ShoppingResult(ActionResult.INDETERMINATE,
                reason="purchase_recheck_unknown")
            return self._last_shopping_result
        budget_spent = self._preparation_budget_spent()
        if not self._set_shop_open(False):
            self._last_shopping_result = ShoppingResult(ActionResult.INDETERMINATE,
                reason="final_round_page_unknown")
            return self._last_shopping_result
        # 超时豁免只能使用本准备期两张认证帧得到的回合。
        # 无来源或跨战斗的旧缓存不授权消费，重读仍消耗原有最多两次额度。
        if (budget_spent and self._preparation_round is not None
                and getattr(self, "_preparation_round_context", None) != (
                    self._cycle_number, self._last_completed_battle_id,
                    self._preparation_departure_confirmed)):
            self._preparation_round = None
        current_round = self._read_preparation_round()
        if budget_spent and current_round != (3, 7):
            self._last_shopping_result = ShoppingResult(ActionResult.CONFIRMED,
                reason="preparation_budget_finished")
            return self._last_shopping_result
        # 无经济配置或仍有购后待确认动作，也不能绕过动态布局认证。
        if not self._layout_valid:
            self.refresh_backend_character(equip=False, recover_layout=True)
            if not self._layout_valid:
                self._last_shopping_result = ShoppingResult(ActionResult.INDETERMINATE,
                    reason="shopping_evidence_deferred")
                return self._last_shopping_result
        if current_round == (3, 7):
            return self._shopping_final_round()
        if (self.economy_config is not None
                and (current_round is None or self._confirmed_battle_count is None)):
            if not self._recheck_economy_evidence():
                self._set_shop_open(False)
                self._last_shopping_result = ShoppingResult(ActionResult.INDETERMINATE,
                    reason="final_round_unknown" if current_round is None else "economy_evidence_not_confirmed")
                return self._last_shopping_result
            current_round = self._preparation_round
        if current_round == (3, 7):
            return self._shopping_final_round()
        if self._preparation_budget_spent():
            self._last_shopping_result = ShoppingResult(ActionResult.CONFIRMED,
                reason="preparation_budget_finished")
            return self._last_shopping_result
        if current_round is None:
            self._last_shopping_result = ShoppingResult(ActionResult.INDETERMINATE,
                reason="final_round_unknown")
            return self._last_shopping_result
        self._invalidate_level()
        attempted = purchased = refreshes = experiences = 0
        purchased_in_offer = False
        recheck_names = set(self._purchase_pending_names)
        checked_purchase_names = set(self._purchase_pending_names)
        unchanged_refreshes = 0
        purchase_rechecks = set()
        skipped_purchase_cards = set()
        verified_failed_cards = getattr(self, "_shop_stall_failed_cards", set())
        self._shop_stall_failed_cards = verified_failed_cards
        result = ActionResult.CONFIRMED
        reason = "finished"
        self._shopping_clock_started = time.monotonic()
        self._shopping_active = True
        prior = dict(self._preparation_shop_counts)
        shop_opened = False
        self._shopping_deadline = None
        limits = dict(self.shopping_budget)
        batch = None
        batch_goals = {}
        batch_prices = {}
        batch_level = None
        batch_upgrade_gate = None
        batch_gate_goals = {}
        batch_gate_names = set()
        normal_exit = False
        balance = None
        skipped_page_slots = set()
        page_progress = dict(attempts=0, purchases=0)
        purchase_cycle = {}
        try:
            if not self._purchase_pending_names and not self._ensure_shopping_observations():
                self._last_shopping_result = ShoppingResult(ActionResult.INDETERMINATE,
                    reason="shopping_evidence_deferred")
                return self._last_shopping_result
            # 商店关闭时读取标题，并在整个准备阶段复用，
            # 包括购买后清理并重开商店的过程。
            refresh_allowed = self._opening_action_allowed("refresh")
            shop_opened = self._set_shop_open(True)
            if not shop_opened:
                self._last_shopping_result = ShoppingResult(ActionResult.INDETERMINATE,
                    0, 0, 0, 0, "shop_not_open")
                logger.warning(f"商店本轮结束：{self._last_shopping_result}")
                return self._last_shopping_result
            # 读取与合成恢复各自拥有有限保护；
            # 动作预算仅统计购买、刷新和经验输入。
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
                finish_snapshot = None
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
                    # 关闭商店前保存当前规划帧。
                    # 事件处理器会丢弃较早的帧与余额。
                    if offer is None:
                        offer = self._scan_store()
                    if balance is None:
                        balance = self.get_coins()
                    # 所有配置保留量共用同一收尾判断，不只适用于 R=0 的
                    # 连续采购。费用须在商店仍展开时读取；旧费用只授权
                    # 结束购物，绝不授权闭店状态下继续消费。
                    recheck_level = self.get_level()
                    recheck_context = (self._economy_context(recheck_level, balance)
                        if recheck_level is not None else None)
                    if recheck_context is not None:
                        balance = self._economy_balance
                    recheck_costs = {action: self._read_action_cost(action)
                                     for action in ("experience", "refresh")}
                    finish_snapshot = (balance, self._shopping_cleanup_state(),
                        {action: cost for action, cost in recheck_costs.items()
                         if self._coin_action_costs.get(action) == cost})
                    # 下一批次前重新确认实际空间；
                    # 预测合成绝不会生成虚拟的备战区空位。
                    logger.info(f"[购物批次] 提前复核={sorted(recheck_names)} 原因=需要现场状态或备战空间")
                    if not self._recheck_purchased_characters(recheck_names):
                        result, reason = ActionResult.INDETERMINATE, "purchase_recheck_unknown"
                        break
                    checked_purchase_names.update(recheck_names)
                    recheck_names.clear()
                    batch = None
                    shop_opened = False
                    closed_balance = self.get_coins()
                    finish_reason = self._shopping_finish_before_reopen(offer,
                        recheck_level, recheck_context,
                        {"closed": True, "result": ActionResult.CONFIRMED,
                         "reason": "", "coins": closed_balance}, finish_snapshot)
                    if finish_reason is not None:
                        reason = finish_reason
                        logger.info(f"[购物收尾] 购后复核无经济变化，保持收起直接结束，原因={reason} 金币={closed_balance}")
                        break
                    shop_opened = self._set_shop_open(True)
                    if not shop_opened:
                        result, reason = ActionResult.INDETERMINATE, "shop_not_open_after_recheck"
                        break
                    recheck_level, balance, recheck_context = self._read_shopping_economy()
                    finish_reason = self._shopping_finish_after_recheck(offer, recheck_level, balance, recheck_context)
                    if finish_reason is not None:
                        reason = finish_reason
                        logger.info(f"[购物收尾] 展开复读后无需继续消费，原因={reason}")
                        break
                    if recheck_context is None:
                        result, reason = ActionResult.INDETERMINATE, "economy_gold_not_confirmed"
                        break
                    offer = None
                    continue  # 根据新棋盘重新计算功能角色与主力需求。
                offer = self._read_shopping_offer(offer)
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
                    balance = None
                if offer.state == ShopState.UNKNOWN:
                    result, reason = ActionResult.INDETERMINATE, "unknown"
                    break
                # 经验购买、重新开店及其他槽位购买不会清除本槽位的失败记录。
                # 只有槽位身份变化或真实刷新输入才能清除此记录。
                current_signature = shop_signature(offer)
                if offer.state == ShopState.EMPTY and not offer.reason.startswith("partial"):
                    current_signature = ()
                if current_signature is not None:
                    verified_failed_cards.intersection_update(current_signature)
                    self._shop_stall_page_signature = current_signature
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
                    # 已确认交易可能在场上或备战区触发合成。
                    # 再次购买同名角色前重读，然后在关闭角色面板后
                    # 重建商店商品信息。
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
                    # 检查合成角色与购物前棋盘扫描一样，会关闭商店。
                    # 下一次 OCR 前须恢复商店。
                    if not self._set_shop_open(True):
                        result, reason = ActionResult.INDETERMINATE, "shop_not_open_after_recheck"
                        break
                    balance = None
                    offer = None
                    continue
                level = self.get_level()
                if self.economy_config is not None and level is None:
                    # 阶段恢复与首个主力保留量都依赖等级；
                    # 绝不能按猜测的更低保留量花费。
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
                economy_context = None
                if self.economy_config is not None:
                    economy_context = self._economy_context(level, coins)
                    if economy_context is None:
                        result, reason = ActionResult.INDETERMINATE, "economy_gold_not_confirmed"
                        break
                    coins = balance = self._economy_balance
                searching_main = bool(self.main_c and not self.main_c_first_fielded_confirmed
                                      and level is not None and level >= self.main_c_search_level)
                reserve = (self.main_c_search_min_coins if searching_main else
                           (0 if self.is_overclock else self.min_coins))
                if economy_context is not None:
                    stage_selection, effective_target, reserve, searching_main = economy_context
                    if batch is not None and level != batch_level:
                        batch = None
                        if recheck_names:
                            continue  # 等级变化后先核实库存，再重算升级门槛。
                    if (reserve != 0 and batch is None and not recheck_names and not role_goals
                            and not self._purchase_pending_names and not self._bench_dirty
                            and not self._placement_pending and not self._form_change_pending
                            and not self._dirty_slots and all(observation_identity(o) is not None
                                for slots in self._observations.values() for o in slots)):
                        candidate = ShoppingBatch.from_observations(self._observations)
                        if candidate is not None and candidate.space_safe:
                            batch = candidate
                            batch_goals = self._purchase_goals()
                            batch_prices = dict(self._observed_prices)
                            batch_level = level
                            # 仅保存购物前真实棋盘的升级结论。副本账本用于
                            # 限制重复买牌，不能据此放行买经验或预测合成空位。
                            batch_upgrade_gate = self._economy_upgrade_gate(
                                level, batch.missing_goals(batch_goals))
                            gate = self.formation_config.upgrade_gate if self.formation_config else None
                            batch_gate_goals, batch_gate_names = {}, set()
                            if gate is not None and level >= gate.from_level:
                                field = [o for area in ("on_field", "off_field")
                                         for o in self._observations[area] if o.state == SlotState.KNOWN]
                                batch_gate_goals = {name: stars for name, stars in gate.fielded.items()
                                    if not any(o.character.name == name and o.stars >= stars for o in field)}
                                batch_gate_names = {name for name, price in gate.prices.items()
                                    if self._observed_prices.get(name, -1) < price
                                    or not any(o.character.name == name for o in field)}
                                counts = confirmed_trait_counts(self.formation_config, self._observations)
                                batch_gate_names.update(name for name, traits in self.formation_config.traits.items()
                                    if any(counts.get(trait, 0) < count and trait in traits
                                           for trait, count in gate.traits.items()))
                            logger.info(f"[购物批次] 按已确认持有量连续采购，待购目标={batch.missing_goals(batch_goals)}")
                all_in = self._all_in_decision is not None and self._all_in_decision.enabled
                final_push = all_in and level < self._all_in_decision.target_level
                if all_in:
                    # 每个准备阶段只固定一次由余额推导的额度；
                    # 余额未变时，恢复不能重新授予额度。
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
                        result, reason = ActionResult.CONFIRMED, "experience_no_progress"
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
                    self._tracked_purchase_demand_page(offer,
                        max_attempts=max(0, limits["actions"] - actions),
                        max_purchases=max(0, limits["purchases"] - prior["purchases"] - purchased
                            - sum(purchase_cycle.get("receipts", {}).values())),
                        skipped_slots=skipped_page_slots, progress=page_progress,
                        # 零保留只取消储备线，仍须逐张检查实际可支付余额。
                        cycle=purchase_cycle, defer=True, spendable_coins=coins,
                        transaction_coins=coins,
                        verified_failed_cards=verified_failed_cards)
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
                            xp_cost=self._read_action_cost("experience"), roll_cost=self._read_action_cost("refresh"),
                            upgrade_allowed=allowed, has_purchase_targets=bool(unmet),
                            space_safe=purchase_cycle["spaces"] > 0 and not full_bench_recovered,
                            needs_prepare=needs_prepare, first_main_search=searching_main,
                            first_main_purchase_reserve_gold=self.main_c_search_purchase_reserve_gold,
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
                            # 费用缓存仅包含本次展开期间可靠识别的费用。
                            # 复核期间无经济变化，才允许它们支持一次结束判断。
                            finish_snapshot = (coins, self._shopping_cleanup_state(),
                                               dict(self._coin_action_costs))
                            self._settle_demand_purchases(purchase_cycle, page_progress)
                        else:
                            # 此边界判断与下方刷新判断之间
                            # 没有任何输入或观测。
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
                        planning_offer = replace(offer, cards=tuple(c for c in offer.cards
                            if c.slot_index not in skipped_page_slots)) if offer is not None else None
                        finish_reason = (self._shopping_finish_before_reopen(planning_offer,
                            level, economy_context, page_progress, finish_snapshot)
                            if finish_snapshot is not None else None)
                        if finish_reason:
                            reason = finish_reason
                            logger.info(f"[购物收尾] 购后复核无经济变化，保持收起直接结束，原因={reason} 金币={page_progress['coins']}")
                            break
                        # 提交经济阶段前，重新打开商店并读取；
                        # 关闭面板状态下的余额不能为下一输入提供资金依据。
                        shop_opened = self._set_shop_open(True)
                        if not shop_opened:
                            result, reason = ActionResult.INDETERMINATE, "shop_not_open_after_recheck"
                            break
                        level, balance, context = self._read_shopping_economy()
                        finish_reason = self._shopping_finish_after_recheck(planning_offer,
                            level, balance, context) if planning_offer is not None else None
                        if finish_reason:
                            reason = finish_reason
                            break
                        if offer is None:
                            skipped_page_slots.clear()
                        offer = None
                        continue  # 出售或布阵后重新计算阶段与目标。
                    if page_progress.get("offer") is None:
                        continue
                targets = []
                restart_offer = False
                role_goals = {} if batch is not None else self._role_purchase_goals()
                for card in (() if page_mode else offer.cards):
                    char = card.character
                    card_key = (card.slot_index, char.name)
                    if (card.slot_index, char.name, card.price) in verified_failed_cards:
                        continue
                    if card_key in skipped_purchase_cards:
                        continue
                    goal = max((batch_goals if batch is not None else self._purchase_goals()).get(char.name, 0),
                               role_goals.get(char.name, 0))
                    if goal <= 0:
                        continue
                    if batch is not None:
                        if not batch.can_buy(char.name, goal):
                            logger.info(f"买牌决策=batch_target_covered {char.name} 目标星级={goal}；持有及已确认购买份数已足够")
                            continue
                        decision = evaluate_purchase(card, target_stars=goal, coins=coins,
                            slot_available=batch.space_safe, star_source="batch_purchase_count",
                            protected=char.is_locked or char.is_npc, require_price=False)
                        logger.info(f"买牌决策={decision.reason} {decision.details}")
                        if decision.can_buy and (card.price is None or can_afford_purchase(coins, card.price, reserve)):
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
                    if (self.economy_config is not None and not is_first_main
                            and any(o.stars is None for o in fields + bench)):
                        recheck_key = (offer_revision, card.slot_index, char.name, "stars")
                        if recheck_key in purchase_rechecks:
                            if char.name in self._purchase_pending_names:
                                result, reason = ActionResult.INDETERMINATE, "purchase_evidence_unknown"
                                break
                            skipped_purchase_cards.add(card_key)
                            logger.warning(f"[购前识别] 跳过商店[{card.slot_index}] {char.name}："
                                           "持有星级补读后仍未知，继续评估其他牌")
                            continue
                        purchase_rechecks.add(recheck_key)
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
                        offer, balance = None, None
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
                        protected=char.is_locked or char.is_npc, require_price=False)
                    if any(type(o.stars) is int and o.stars >= goal for o in bench):
                        logger.info(f"买牌决策=target_reached_on_bench {char.name} 目标星级={goal}")
                        continue
                    logger.info(f"买牌决策={decision.reason} {decision.details}")
                    if decision.can_buy:
                        if self.economy_config is not None and self._economy_space_safe({char.name: goal}) is not True:
                            logger.info(f"[经济决策] action=prepare reason=purchase_space_unconfirmed name={char.name}")
                            continue
                        if (self.economy_config is not None and card.price is not None
                                and not can_afford_purchase(coins, card.price, reserve)):
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
                    self._purchase_before_copies[card.character.name] = self._held_purchase_copies(card.character.name)
                    was_bench_dirty = self._bench_dirty
                    was_purchase_pending = card.character.name in self._purchase_pending_names
                    self._bench_dirty = True
                    self._purchase_pending_names.add(card.character.name)
                    if card.price is not None:
                        self._invalidate_character_evidence(card.character.name, "purchase_attempt", level_changed=False)
                    else:
                        logger.info(f"[未知价格采购] {card.character.name} 已确认目标与槽位，"
                                    f"直接尝试购买，购后读取实际余额；购前金币={coins}")
                    self._purchase_confirmation_observations = []
                    self._purchase_offer_before = offer
                    self._purchase_coin_read_before = self._last_coin_observation
                    attempted += 1
                    if not self.operator.click_point(*card.target, after_sleep=0.5):
                        result, reason = ActionResult.FAILED, "purchase_click_failed"
                        break
                    self._coin_action_costs.clear()
                    self.operator.move_to(0.5, 0.5)
                    self._confirmed_purchase_snapshot = None
                    confirmation = self._confirm_purchase(card, coins)
                    unpriced_noop = (card.price is None and confirmation == ActionResult.FAILED
                                     and self._confirmed_purchase_snapshot is not None)
                    if confirmation != ActionResult.CONFIRMED:
                        self.operator.sleep(0.3)
                        confirmation = self._confirm_purchase(card, coins)
                    if (unpriced_noop and confirmation == ActionResult.FAILED
                            and self._confirmed_purchase_snapshot is not None):
                        skipped_purchase_cards.add((card.slot_index, card.character.name))
                        self._bench_dirty = was_bench_dirty
                        if not was_purchase_pending:
                            self._purchase_pending_names.discard(card.character.name)
                        offer, balance = self._confirmed_purchase_snapshot or (None, None)
                        self._record_checkpoint(phase="preparation", pending_actions=[])
                        logger.info(f"[未知价格采购] {card.character.name} 连续复核未成交，"
                                    "当前页不重复点击，继续评估其他购买和经验")
                        continue
                    if confirmation != ActionResult.CONFIRMED and card.price is not None:
                        stall = prepare_stalled_shop_rebuild(self, card,
                            before_coins=coins,
                            before_copies=self._purchase_before_copies.get(card.character.name),
                            was_pending=was_purchase_pending,
                            observations=self._purchase_confirmation_observations,
                            actions=prior["attempts"] + prior["refreshes"] + prior["experiences"]
                                + attempted + refreshes + experiences,
                            purchases=prior["purchases"] + purchased
                                + sum(purchase_cycle.get("receipts", {}).values()),
                            refreshes=prior["refreshes"] + refreshes,
                            limits=limits, reserve=reserve, opening_allowed=refresh_allowed)
                        if stall.status == "noop":
                            verified_failed_cards.add((card.slot_index, card.character.name, card.price))
                            self._shop_stall_page_signature = shop_signature(stall.offer)
                            offer, balance = stall.offer, stall.coins
                            # 库存复核已结清先前确认的收据。
                            # 应依据真实库存重算需求，不使用旧预测。
                            batch, batch_goals, batch_prices = None, {}, {}
                            checked_purchase_names.update(recheck_names)
                            recheck_names.clear()
                            self._coin_action_costs.clear()
                            self._purchase_scan_baseline = None
                            logger.warning("[商店恢复] 已确认本槽未成交，跳过该槽并继续原采购与经济判断")
                            continue
                        if stall.reason != "purchase_not_confirmed":
                            result, reason = ActionResult.INDETERMINATE, stall.reason
                            break
                    if confirmation != ActionResult.CONFIRMED:
                        if card.price is None:
                            self._invalidate_character_evidence(card.character.name, "purchase_unconfirmed", level_changed=False)
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
                            # 只有真实事件才能改变形态、价格或奖励。
                            batch = None
                            offer, balance = None, None
                            self._invalidate_level()
                    if card.character.name == self.main_c and not self.main_c_first_fielded_confirmed:
                        reason = "main_c_placement"
                        break
                    if card.character.name in role_goals:
                        # 一星材料尚不能满足要求两星或三星的功能角色；
                        # 确认合成，并继续保留当前购物批次，
                        # 直到实际满足该功能要求。
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
                                offer, balance = None, None
                                continue
                        reason = "role_placement"
                        break
                    continue  # 根据已确认的购买后页面规划。
                if level is None:
                    result, reason = ActionResult.INDETERMINATE, "unknown_level"
                    break
                if offer.reason.startswith("partial"):
                    result, reason = ActionResult.INDETERMINATE, "partial_store"
                    break
                if refresh_stalled:
                    result, reason = ActionResult.CONFIRMED, "refresh_no_progress"
                    break
                if actions >= limits["actions"]:
                    reason = "action_budget"
                    break
                economy_decision = None
                xp_cost, roll_cost = self._read_action_cost("experience"), self._read_action_cost("refresh")
                if self.economy_config is not None:
                    if purchase_cycle.get("receipts"):
                        unmet, demand_unknown = self._demand_cycle_goals(purchase_cycle), False
                        allowed, gate_actionable, needs_prepare, gate_reason = purchase_cycle["gate"]
                        space_safe = purchase_cycle["spaces"] > 0
                    elif batch is not None:
                        unmet, demand_unknown = batch.missing_goals(batch_goals), False
                        if level < effective_target:
                            allowed, gate_actionable, needs_prepare, gate_reason = batch_upgrade_gate
                            gate_missing = batch.missing_goals(batch_gate_goals)
                            gate_ready = (any(name in recheck_names and name not in gate_missing
                                              for name in batch_gate_goals)
                                          or bool(recheck_names & batch_gate_names))
                            if recheck_names and ((allowed is not False and not searching_main)
                                                  or needs_prepare or gate_ready):
                                # 当前页已买完。买经验、布阵或可能满足升级门槛
                                # 前统一复核；门槛仍明确缺牌时，可跨页继续搜牌。
                                logger.info(f"[购物批次] 当前页采购完成，统一复核后重算升级门槛 "
                                            f"等级={level} 目标={effective_target} 门槛={gate_reason}")
                                batch = None
                                continue
                        else:
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
                            xp_cost=xp_cost, roll_cost=roll_cost,
                            upgrade_allowed=allowed, has_purchase_targets=None if demand_unknown else bool(unmet),
                            space_safe=False if full_bench_recovered else space_safe, needs_prepare=needs_prepare,
                            first_main_search=searching_main, gate_has_purchase_targets=gate_actionable,
                            first_main_purchase_reserve_gold=self.main_c_search_purchase_reserve_gold)
                    logger.info(f"[经济决策] mode=stages stage={stage_selection.index} stage_reason={stage_selection.reason} "
                        f"battles={self._confirmed_battle_count} L={level} target={effective_target} gold={coins} R={reserve} "
                        f"P={0 if all_in else self.main_c_search_purchase_reserve_gold if searching_main else self.economy_config.purchase_reserve_gold} xp_cost={xp_cost} "
                        f"roll_cost={roll_cost} action={economy_decision.action} "
                        f"reason={economy_decision.reason} gate={gate_reason}")
                    if economy_decision.action in ("save", "prepare", "recover"):
                        result = ActionResult.INDETERMINATE if economy_decision.action == "recover" else ActionResult.CONFIRMED
                        reason = economy_decision.reason
                        break
                elif (xp_cost is None or roll_cost is None):
                    result, reason = ActionResult.INDETERMINATE, "unknown_action_cost"
                    break
                elif coins < (roll_cost if searching_main else 0 if xp_cost == 0 or roll_cost == 0 else 4):
                    reason = "low_coins"
                    break
                if (economy_decision is not None and economy_decision.action == "buy_xp" or
                        economy_decision is None and (level < self.min_level or refreshed_offer and allow_mid_upgrade and level < self.mid_level
                        and not purchased_in_offer) and coins >= xp_cost and self._can_upgrade(level)):
                    if prior["experiences"] + experiences >= limits["experiences"]:
                        reason = "experience_budget"
                        break
                    if not self._buy_experience(level):
                        result, reason = ActionResult.FAILED, "experience_click_failed"
                        break
                    experiences += 1
                    balance = None
                    post_experience_level = None
                    confirmed_experience = self._confirm_experience(level, coins)
                    if confirmed_experience is None:
                        result, reason = ActionResult.CONFIRMED, "experience_no_progress"
                        break
                    post_experience_level, balance = confirmed_experience
                    if full_bench_recovered and type(post_experience_level) is int and post_experience_level > level:
                        # 新增人口槽位只有布阵后才有用；
                        # 备战区仍满员时，不能继续刷新或购买。
                        reason = "purchase_space_blocked"
                        break
                    if (economy_decision is None or post_experience_level != level
                            or self._form_change_pending or self._runtime_node_pending is not None):
                        offer = None
                    refreshed_offer = False
                    continue
                if economy_decision is None and roll_cost != 0 and ((searching_main and
                        coins - roll_cost < reserve + self.main_c_search_purchase_reserve_gold)
                        or (not searching_main and not self.is_overclock and coins < reserve)):
                    reason = "coin_reserve"
                    break
                # 个别目标未成交或星级未知，不妨碍有独立可靠证据的经验购买；
                # 但不能直接刷新丢弃该页目标。经验分支已经在上方处理。
                if skipped_purchase_cards:
                    reason = "shopping_evidence_deferred"
                    break
                recovery_refresh = bool(verified_failed_cards)
                if recovery_refresh and getattr(self, "_shop_stall_rebuild_used", False):
                    reason = "purchase_stall_deferred"
                    break
                if prior["refreshes"] + refreshes >= limits["refreshes"]:
                    reason = "refresh_budget"
                    break
                # 没有剩余购买输入额度时，绝不刷新生成新商品页。
                # 每次确认都保留有限的恢复边界。
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
                if recovery_refresh:
                    # 刷新输入仍由上方已有的经济、开局和输入门槛决定。
                    if not reliable_balance(self._last_coin_observation, coins):
                        reason = "purchase_stall_refresh_balance_unknown"
                        break
                    refresh_reading = getattr(self, "_coin_action_cost_observations", {}).get("refresh")
                    if (type(roll_cost) is not int or roll_cost < 0 or refresh_reading is None
                            or getattr(refresh_reading, "reliable", False) is not True
                            or type(getattr(refresh_reading, "cost", None)) is not int
                            or refresh_reading.cost != roll_cost):
                        reason = "purchase_stall_refresh_cost_unknown"
                        break
                    # 检查准备阶段的实际时限前，先补偿已用购物时间。
                    self._credit_shopping_time()
                    self._shopping_clock_started = time.monotonic()
                    self._check_stop()
                    if self._preparation_budget_spent():
                        reason = "preparation_budget_finished"
                        break
                    self._shop_stall_rebuild_used = True
                    self._observed_prices.clear()
                    self._purchase_scan_baseline = None
                    logger.warning("[商店恢复] 原经济规则允许刷新，使用本准备期唯一故障重建输入")
                if not self.operator.press_key("d"):
                    result, reason = ActionResult.FAILED, "refresh_click_failed"
                    break
                verified_failed_cards.clear()
                self._shop_stall_page_signature = None
                self._coin_action_costs.clear()
                refreshes += 1
                offer_revision += 1
                skipped_page_slots.clear()
                self.operator.sleep(0.5)
                after = self._scan_store()
                if recovery_refresh and (after.state not in (ShopState.READY, ShopState.EMPTY)
                        or after.reason.startswith("partial")):
                    self._invalidate_roster_evidence("shop_stall_refresh_unconfirmed")
                    result, reason = ActionResult.INDETERMINATE, "purchase_stall_refresh_unconfirmed"
                    break
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
                coins_after = self._read_coins_after_action(coins, roll_cost, "refresh")
                self._coin_action_costs.pop("refresh", None)
                balance = coins_after
                if recovery_refresh:
                    charge = validate_coin_change(coins, coins_after,
                        expected_spend=roll_cost, allow_zero=True)
                    if (after.state not in (ShopState.READY, ShopState.EMPTY)
                            or after.reason.startswith("partial")
                            or not reliable_balance(self._last_coin_observation, coins_after)
                            or charge.accepted is not True):
                        self._invalidate_roster_evidence("shop_stall_refresh_unconfirmed")
                        result, reason = ActionResult.INDETERMINATE, "purchase_stall_refresh_unconfirmed"
                        break
                if coins_after is None:
                    result, reason = ActionResult.INDETERMINATE, "unknown_coins_after_refresh"
                    break
                unchanged_refreshes = (unchanged_refreshes + 1
                    if signature == new_signature and coins_after == coins else 0)
                refresh_stalled = unchanged_refreshes >= 2
                # 下一决策复用此真实余额；
                # 商品变化即使未扣标准两金币，也可能有效。
                logger.info(f"[刷新结果] 金币={coins}->{coins_after} "
                            f"牌面变化={signature != new_signature} 连续未变化={unchanged_refreshes}")
                # 任何 F 输入、刷新边界或时间边界前，都须先评估刷新后的页面。
                # 其快照可以复用，直到真实输入
                # 或角色面板检查使它失效。
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
                # 恢复相同额度，停止或关闭失败时也如此。
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
        # 未知历史占位仍计数，避免不安全的超员布阵。
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
        if observation.level is not None and self._session_context_tracking:
            self._record_checkpoint(observed_level=observation.level)
        logger.info(f"商店等级={observation.level} 来源={observation.evidence} "
                    f"原因={observation.reason} OCR={observation.raw_text!r}")
        if observation.level is None:
            attempts = getattr(self._vision, "last_level_attempts", ())
            details = [f"{item.get('method')}:{item.get('reason')}" for item in attempts
                       if isinstance(item, dict)]
            logger.warning(f"[等级读取] 重试明细={details}；本轮暂停搜牌和购买经验")
        return observation.level

    def _population_observation_key(self):
        return (self._layout_revision, self._layout_valid, self._backend_identity_ready(),
            tuple(sorted(self._backend_unknown_slots)), tuple(sorted(self._backend_support_slots)),
            self.max_team_size, tuple(
            (observation_identity(o), bool(getattr(o.character, "is_npc", False)),
             bool(getattr(o.character, "is_locked", False))) for area in ("on_field", "off_field")
            for o in self._observations[area]))

    def _record_population_issue(self, reason, raw_text=""):
        """识别不足是可恢复事件；日志持续留存，不改变任务运行状态。"""
        self._population_next_retry_at = time.monotonic() + 2.0
        attempts = getattr(self._vision, "last_population_attempts", ())
        details = [{key: item.get(key) for key in ("frame_index", "text", "scores", "reason", "variants")}
                   for item in attempts[:2] if isinstance(item, dict)] if isinstance(attempts, (list, tuple)) else []
        logger.warning(f"[人口继续] 原因={reason} 当前人数未知，保留此前上限={self.max_team_size}；"
                       f"继续已确认棋盘的整备，自动补读最多2次/间隔至少2秒；"
                       f"文本={str(raw_text)[:240]} OCR={details} "
                       f"截图={getattr(self._vision, 'last_population_sample', None)} "
                       f"采样={getattr(self._vision, 'last_sample_reason', 'unknown')}")

    # ssyb：人口上限与实际人数分别核实，避免单次识别污染状态。
    def update_max_team_size(self, *, retry_failed=False):
        self._check_stop()
        if not self._layout_valid:
            # 总人口可能已含新支援，未知后台不能按零 NPC 解释。
            self._population_current = self._population_read_key = None
            return
        key = self._population_observation_key()
        retrying = self._population_read_key == key
        if retrying:
            if self._population_current is not None:
                return
            if (self._preparation_deadline is not None
                    and time.monotonic() >= self._preparation_deadline):
                return
            if retry_failed:
                if self._sale_population_retry_used:
                    return
                # 卖出前的专用额度不因自动补读或页面恢复而重新授予。
                self._sale_population_retry_used = True
                logger.info("[人口确认] 卖出前重试失败读数，使用增强对比度的两帧识别")
            else:
                if (self._population_auto_retries >= 2
                        or time.monotonic() < self._population_next_retry_at):
                    return
                self._population_auto_retries += 1
                logger.info(f"[人口继续] 自动补读={self._population_auto_retries}/2，使用新的两帧证据")
        self._population_read_key = key
        try:
            population = (self._vision.read_population(enhance=True) if retrying
                          else self._vision.read_population())
            current, capacity = population.current, population.capacity
        except (ThreadStoppedError, InterruptedError):
            raise
        except Exception as error:
            self._population_current = None
            try:
                self._vision.last_population_sample = self._vision.capture_sample("unknown_population", {
                    "population_reason": "population_read_error:" + type(error).__name__,
                    "error_type": type(error).__name__}, critical=True)
            except (ThreadStoppedError, InterruptedError):
                raise
            except Exception as sample_error:
                logger.warning(f"[人口留证] 采样未完成：{type(sample_error).__name__} {sample_error}；继续扩展日志留存")
            self._record_population_issue("population_read_error:" + type(error).__name__, str(error))
            return
        self._population_current = current if capacity is not None else None
        if population.capacity is not None:
            self.max_team_size = population.capacity
            if self._population_current is None:
                self._record_population_issue(population.reason, population.raw_text)
            self._population_read_key = self._population_observation_key()
            logger.info(f"[人口确认] 当前={population.current}/{population.capacity} "
                        f"来源={population.evidence}")
            if population.current == 0:
                if not self._backend_identity_ready():
                    logger.warning("[人口确认] 零读数不能解除未知支援保护，保留槽位证据等待认证")
                    return
                if self._population_conflict():
                    logger.warning("[人口确认] 零人口与已确认角色冲突，保留场地证据等待补读")
                    return
                first = self._observe_page_frame(self._capture_page_frame(), full_navigation=False)
                self.operator.sleep(0.15)
                second = self._observe_page_frame(self._capture_page_frame(), full_navigation=False)
                if first[0] == second[0] == "preparation":
                    # 实时、稳定且完整的分子证明整个场地为空；
                    # 孤立的容量数字绝不能提供此证据。
                    for area in ("on_field", "off_field"):
                        for i in range(len(self._observations[area])):
                            self._observation_revision += 1
                            self._set_observation(area, SlotObservation(
                                i, SlotState.EMPTY, occupied=False, evidence="zero_population",
                                revision=self._observation_revision))
                    self._reconcile_placed()
                    logger.info("[人口确认] 已确认空战斗区，允许放置起手角色")
                else:
                    self._population_current = self._population_read_key = None
                    logger.warning("[人口确认] 准备页未通过弹窗优先检查，保留场地证据")
                    return
            self._population_read_key = self._population_observation_key()
            return
        attempts = getattr(self._vision, "last_population_attempts", ())
        self._record_population_issue(population.reason, population.raw_text)
        details = [{key: item.get(key) for key in ("text", "scores", "reason")}
                   for item in attempts if isinstance(item, dict)] if isinstance(attempts, (list, tuple)) else []
        logger.debug(f"[人口确认] 完整读数未确认：{population.reason}，当前人口未知，OCR={details}")
        # 独立容量现在也由视觉层以真实 /N 结构和两帧一致确认。
        # 两帧都未读到时保留上一次容量，不再拿另一处单帧裸数字覆盖它。
        logger.debug(f"[人口确认] 沿用此前队伍上限={self.max_team_size}，当前人数继续未知")
        self._population_read_key = self._population_observation_key()

    def load_strategy(self, name):
        path = resolve_strategy_path(name)
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        main_c, search_level = validate_main_c_config(data, self._lookup_known_character)
        # 改变当前攻略前，验证所有状态修改输入。
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
                             ("main_c_search_purchase_reserve_gold", 0),
                             ("min_level", 7), ("mid_level", 7)):
            value = data.get(key, default)
            if type(value) is not int or value < 0:
                raise ValueError(f"攻略参数 {key} 无效")
        economy = parse_economy_config(data.get("economy"),
            main_c_search_level=search_level if main_c else None)
        opening_policy = parse_opening_policy_config(data.get("opening_policy"))
        reward_fast_rounds = parse_reward_fast_rounds(data.get("reward_fast_rounds"))
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
        for keyword in events.values():
            groups = keyword.replace("＞", ">").split(">")
            if len(groups) > 1 and any(not group.strip() for group in groups):
                raise ValueError("special_events 的优先级组不能为空，请用 > 分隔非空关键词组")
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
        self.reward_fast_rounds = reward_fast_rounds
        self.main_c_search_level = search_level
        self.main_c_search_min_coins = data.get("main_c_search_min_coins", 0)
        self.main_c_search_purchase_reserve_gold = data.get("main_c_search_purchase_reserve_gold", 0)
        self.main_c_first_fielded_confirmed = False
        self._invalidate_level()
        self._equipment_dirty = True
        logger.info(f"[经济配置] mode={'stages' if economy else 'legacy'} stages={getattr(economy, 'stages', ())} "
                    f"purchase_reserve={getattr(economy, 'purchase_reserve_gold', 0)} "
                    f"main_search_purchase_reserve={self.main_c_search_purchase_reserve_gold} "
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
        self.reward_fast_rounds = ()
        self._reward_fast_active = False
        self._reward_fast_page_ledger = None
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
        self._formation_successor_prefix_pending = False
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
        self.main_c_search_purchase_reserve_gold = 0
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
        if not self._layout_valid:
            logger.info("[布阵保护] 后台布局或支援身份未确认，等待重建后再规划")
            return False
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

        # 前后台都优先安排首个主力，再用队友填充。
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
        if any(o.state == SlotState.KNOWN and observation_identity(o) is not None
               for o in self._observations["on_field"]):
            return True
        if not self._layout_valid:
            return False

        for off_index, char in enumerate(self.off_field_character):
            obs = self._observations["off_field"][off_index]
            if (char is None or char.is_locked or char.is_npc or obs.state != SlotState.KNOWN
                    or observation_identity(obs) is None):
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
            # 若填满另一区域会使首个主力无处上场，则保留一个人口槽位。
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
        final_finish = getattr(self, "_final_finish_active", False)
        if final_finish:
            context = self._final_finish_context
            move = (source_area_type, source_index, target_area_type, target_index)
            if (context["done"] or context["permitted"] != move or context["attempts"] >= 3
                    or time.monotonic() >= context["deadline"]):
                return False
            context["attempts"] += 1
        elif self._preparation_deadline is not None:
            if self._purchase_finish_exhausted():
                self._last_move_result = replace(self._last_move_result, reason="purchase_finish_budget")
                return False
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
        if any(area == "off_field" and index in self._backend_unknown_slots
               for area, index in ((source_area_type, source_index), (target_area_type, target_index))):
            self._last_move_result = replace(self._last_move_result, reason="backend_slot_protected_unknown")
            return False
        if "off_field" in (source_area_type, target_area_type) and not self._layout_valid:
            self._last_move_result = replace(self._last_move_result, reason="backend_layout_not_confirmed")
            return False
        if any(area == "off_field" and index not in self._backend_ordinary_slots
               for area, index in ((source_area_type, source_index), (target_area_type, target_index))):
            self._last_move_result = replace(self._last_move_result, reason="backend_slot_not_authenticated")
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
        # 中央保护规则也覆盖备用布阵和优先级排序。
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
        if final_finish:
            self._check_page_navigation_deadline(self._final_finish_context["deadline"])
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
        # 拖拽一旦以槽位为目标，初始空位基线就失效。
        # 历史占位仅作为受保护且未确认的值保留。
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
        # 确认两个端点，包括返回备战区角色的星级。
        # 复用这些已打开的面板，避免后续强制全量扫描备战区。
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
            # 历史身份可保护占位角色，但绝不能认证移动。
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
        else:  # 后台区域。
            characters = self.off_field_character
            area_name = "后台"

        if (area_type == "off_field" and not self._layout_valid
                or any(observation_identity(obs) is None for obs in self._observations[area_type])):
            return False
        logger.info(f"开始对{area_name}区域角色按优先级排序")

        # 创建包含角色、索引和优先级的列表
        char_info_list = []
        for i, char in enumerate(characters):
            if (self._observations[area_type][i].state == SlotState.LOCKED
                    or char is not None and (char.is_locked or char.is_npc)
                    or area_type == "off_field" and i in self._backend_support_slots):
                continue
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
        movable_positions = [info['index'] for info in char_info_list]
        for target_pos, target_info in zip(movable_positions, sorted_char_info):
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

    # Yukki：拖动异常后的按键释放不依赖原移动是否成功。
    def _release_pointer_unconditionally(self):
        # 紧急释放绕过带停止检查的操作器包装，但绝不绕过停止请求本身。
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
        if getattr(self, "_final_finish_active", False):
            self._check_page_navigation_deadline(self._final_finish_context["deadline"])
        completed = False
        try:
            completed = bool(self.operator.drag_to(*args, **kwargs))
            self._check_stop()
            return completed
        finally:
            event = getattr(self.operator, "stop_event", None)
            if not completed or (event is not None and event.is_set()):
                self._release_pointer_unconditionally()

    def _reconcile_form_change_pending(self):
        """事件退场并重新确认库存后结束形态待核实，不要求商店价格变化。"""
        if (not self._form_change_pending or self._bench_dirty
                or self._selection_event_pending is not None or self._pending_move is not None):
            return
        observations = [(area, index, obs) for area, slots in self._observations.items()
                        for index, obs in enumerate(slots)]
        complete = all(observation_identity(obs) is not None and (area, index) not in self._dirty_slots
                       for area, index, obs in observations)
        for name in tuple(self._form_change_pending):
            matches = [(area, index, obs) for area, index, obs in observations
                       if obs.character is not None and obs.character.name == name]
            confirmed = (all(obs.state == SlotState.KNOWN and observation_identity(obs) is not None
                             and type(obs.stars) is int and 1 <= obs.stars <= 3
                             and (area, index) not in self._dirty_slots
                             for area, index, obs in matches) if matches else complete)
            if confirmed:
                self._form_change_pending.pop(name, None)
                logger.info(f"[形态复核] {name} 事件已退场且库存已重新确认，清除待确认标记；"
                            f"最近实际价格={self._observed_prices.get(name)}")

    def _reconcile_purchase_pending(self):
        if self._bench_dirty:
            return  # 未观测的购买落位或合成槽位，不能沿用旧 EMPTY。
        self._reconcile_form_change_pending()
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
                    # 形态事件后身份和占用证据仍保留，但星级证据失效。
                    observations[index] = replace(obs, stars=None)
                    self._slot_evidence.pop((area, index), None)
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
            if (self._placement_pending or time.monotonic() >= self._formation_deadline
                    or self._purchase_finish_exhausted()):
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
                # 成功重新建立目标后，关闭被中断的中间计划；
                # 仅要求实际持有目标到位，尚未买到的角色不能永久保留旧计划标记。
                # 全部区域身份仍须可靠，不能因未读到备战区目标就认为它已消失。
                held = {o.character.name for slots in self._observations.values() for o in slots
                        if o.state == SlotState.KNOWN and observation_identity(o) is not None}
                if (all(observation_identity(o) is not None
                        for slots in self._observations.values() for o in slots)
                        and all(any(o.state == SlotState.KNOWN and observation_identity(o) is not None
                                    and o.character.name == name for o in self._observations[area])
                                for area in ("on_field", "off_field")
                                for name in getattr(stage, area) if name in held)):
                    self._formation_plan_incomplete = False
                    self._formation_successor_prefix_pending = False
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
            prefix_was_pending = self._formation_successor_prefix_pending
            prefix_attempt = move.reason == "protected_successor_prefix"
            if prefix_attempt:
                # 在输入前保留交接意图；只有双端确认后才会重算并释放旧保护。
                self._formation_successor_prefix_pending = True
                self._formation_plan_incomplete = True
            changed = self.swap_character_between_areas(move.source_area, move.source_index,
                move.target_area, move.target_index)
            if self._preparation_attempts == attempts_before:
                self._preparation_attempts += 1
            if changed:
                placed = True
                self._move_failures.pop(key, None)
                self._formation_plan = self._formation_plan[1:]
                self._formation_plan_incomplete = (bool(self._formation_plan)
                    or self._formation_successor_prefix_pending)
            elif self._last_move_result.status == MoveStatus.INDETERMINATE or self._placement_pending:
                break
            else:
                self._formation_plan = ()
                if prefix_attempt:
                    self._formation_successor_prefix_pending = prefix_was_pending
                    self._formation_plan_incomplete = prefix_was_pending
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
        # 仅磁盘哈希不能识别运行中应用缓存的类。
        logger.info(f"货币战争内存流程版本={self.FLOW_REVISION} "
                    f"阶段等待秒数：页面={self.PAGE_LOCATE_TIMEOUT} "
                    f"入局={self.ENTRY_TRANSITION_TIMEOUT} 关卡={self.STAGE_TRANSITION_TIMEOUT} "
                    f"出战按钮={self.BATTLE_BUTTON_TIMEOUT} 准备宽限={self.PREPARATION_GRACE_SECONDS} "
                    f"结算={self.REWARD_TRANSITION_TIMEOUT} 事件={self.EVENT_TRANSITION_TIMEOUT} "
                    f"稳定={self.STAGE_SETTLE_SECONDS} 战斗复核={self.BATTLE_TIMEOUT} "
                    f"战斗总上限={self.BATTLE_MAX_WAIT_SECONDS}")
        paths = [Path(__file__).resolve()]
        for name in ("logic", "formation", "vision", "characters", "preparation", "layout", "session", "economy", "shop_overlay", "equipment_choice", "policy", "equipment_policy", "shopping_batch", "coins", "images", "paths", "stop_compat", "game_input"):
            module = sys.modules.get(f"{__package__}.{name}")
            location = getattr(module, "__file__", None)
            if location:
                paths.append(Path(location).resolve())
            else:
                logger.warning(f"无法核验已导入模块路径：{__package__}.{name}")
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
                    f"main_c_search_purchase_reserve_gold={self.main_c_search_purchase_reserve_gold} "
                    f"refresh_cost={self.SHOP_REFRESH_COST} xp_cost={self.SHOP_EXPERIENCE_COST} "
                    f"economy={self.economy_config} equipment_interval={self.equipment_interval_battles} "
                    f"budgets={self.shopping_budget} shopping_total_seconds=unlimited")
