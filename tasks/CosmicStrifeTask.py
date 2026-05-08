from SRACore.task import BaseTask, task
from SRACore.util.logger import logger
from tasks.cosmic_strife.periodic_progress import (
    GuideCycleProbeResult,
    close_guide_return_to_map,
    probe_shared_cycle_via_guide,
    read_cw_start_cycle_progress,
    read_du_hub_cycle_progress,
)
from tasks.cosmic_strife.policy_defs import CosmicStrifeRunPolicy, normalize_cosmic_policy
from tasks.cosmic_strife.state_store import (
    CosmicStrifePolicyState,
    load_policy_state,
    register_completed_run,
    remaining_daily,
    remaining_weekly,
    save_policy_state,
)
from tasks.currency_wars.characters import Characters


def _currency_wars_reroll_and_overclock(config: dict) -> tuple[bool, bool]:
    """解析玩法与入口：刷开局 vs 刷等级，标准 vs 超频。新配置为 Objective+Ruleset；旧配置仅 CurrencyWarsMode 打包（mode=Objective*2+Ruleset）。"""
    obj = config.get("CurrencyWarsObjective")
    rules = config.get("CurrencyWarsRuleset")
    if obj is not None and rules is not None:
        try:
            return int(obj) == 1, int(rules) == 1
        except (TypeError, ValueError):
            pass
    m = int(config.get("CurrencyWarsMode", 0))
    return (m // 2) == 1, (m % 2) == 1


@task(order=3)
class CosmicStrifeTask(BaseTask):
    def run(self):
        """主任务执行函数"""
        state = load_policy_state()

        is_reroll, is_overclock = _currency_wars_reroll_and_overclock(self.config)
        cw_enable = self.config.get("CurrencyWarsEnable", False)
        du_policy_raw = int(self.config.get("DUPolicy", 0))
        cw_policy_raw = int(self.config.get("CurrencyWarsPolicy", 0))
        du_fill = self.config.get("DUEnable", False) and normalize_cosmic_policy(du_policy_raw) == CosmicStrifeRunPolicy.FILL_CYCLE_REWARD
        cw_fill = (
            cw_enable
            and (not is_reroll)
            and normalize_cosmic_policy(cw_policy_raw) == CosmicStrifeRunPolicy.FILL_CYCLE_REWARD
        )
        shared_probe: GuideCycleProbeResult | None = None
        if du_fill or cw_fill:
            logger.info("旷宇纷争：在指南「旷宇纷争」总览页进行共用周期积分 OCR（差分与货币战争进度一致）")
            shared_probe = probe_shared_cycle_via_guide(self.operator, self.operator.settings)
            if shared_probe.navigated and shared_probe.progress is not None and shared_probe.progress.is_full:
                logger.info("旷宇纷争：指南页周期积分已满，共用进度 —「刷满周期」策略下差分与货币战争本次均跳过")
            if shared_probe.navigated:
                close_guide_return_to_map(self.operator)

        if self.config.get("DUEnable", False):
            logger.info("执行任务：旷宇纷争-模拟宇宙")
            du_policy_raw = int(self.config.get("DUPolicy", 0))
            daily_du = int(self.config.get("DURunTimes", 5))
            weekly_du = int(self.config.get("DUWeeklyTotalCap", 20))
            eff_du = self._resolve_du_effective_runs(state, du_policy_raw, daily_du, weekly_du, shared_probe)
            if eff_du <= 0:
                logger.info("差分宇宙：本次有效次数为 0，跳过")
            else:
                on_du = self._callback_for_module(state, du_policy_raw, "du")
                from tasks.differential_universe import DifferentialUniverse

                du_fill_loop = normalize_cosmic_policy(du_policy_raw) == CosmicStrifeRunPolicy.FILL_CYCLE_REWARD
                if du_fill_loop:
                    for attempt in range(eff_du):
                        if attempt > 0:
                            probe_du = DifferentialUniverse(
                                self.operator,
                                0,
                                self.config.get("DUUseTechnique", False),
                            )
                            if probe_du.page_locate():
                                prog_du = read_du_hub_cycle_progress(self.operator)
                                probe_du._return_to_main_menu()
                                if prog_du is not None and prog_du.is_full:
                                    logger.info(
                                        "差分宇宙：乐园漫记 hub 周期已满，提前结束剩余次数"
                                    )
                                    break
                            else:
                                logger.warning(
                                    "差分宇宙：复检前无法进入乐园漫记入口，继续下一局"
                                )
                        du_once = DifferentialUniverse(
                            self.operator,
                            1,
                            self.config.get("DUUseTechnique", False),
                            on_run_completed=on_du,
                        )
                        if not du_once.run():
                            logger.error("旷宇纷争-模拟宇宙任务失败")
                            return False
                else:
                    du_task = DifferentialUniverse(
                        self.operator,
                        eff_du,
                        self.config.get("DUUseTechnique", False),
                        on_run_completed=on_du,
                    )
                    if not du_task.run():
                        logger.error("旷宇纷争-模拟宇宙任务失败")
                        return False

        if not cw_enable:
            logger.info("旷宇纷争任务全部完成")
            return True

        username = self.config.get("CurrencyWarsUsername", "")
        strategy = self.config.get("CurrencyWarsStrategy", "template")
        difficulty = self.config.get("CurrencyWarsDifficulty", 0)

        if username is None or username.strip() == "":
            logger.error("货币战争开拓者名称为空，请在前端配置中填写。")
            return False
        Characters.set_username(username)

        cw_policy_raw = int(self.config.get("CurrencyWarsPolicy", 0))
        daily_cw = int(self.config.get("CurrencyWarsRunTimes", 1))
        weekly_cw = int(self.config.get("CurrencyWarsWeeklyTotalCap", 3))

        if is_reroll:
            oc_tag = "超频" if is_overclock else "标准"
            logger.info(f"执行任务：旷宇纷争-货币战争 刷开局（{oc_tag}入口）")
            from tasks.currency_wars import RerollStart

            rs_task = RerollStart(operator=self.operator, runtimes=1)
            rs_task.set_difficulty(difficulty)
            rs_task.set_overclock(is_overclock)
            rs_task.load_strategy(strategy)
            rs_task.set_boss_name(self.config.get("CwRsBossNames", ""))
            rs_task.set_boss_affix(self.config.get("CwRsBossAffixes", ""))
            rs_task.set_invest_env(self.config.get("CwRsInvestEnvironments", ""))
            rs_task.set_invest_strategy(self.config.get("CwRsInvestStrategies", ""))
            if not rs_task.run():
                logger.error("旷宇纷争-货币战争刷开局任务失败")
                return False

        else:
            eff_cw = self._resolve_cw_effective_runs(state, cw_policy_raw, daily_cw, weekly_cw, shared_probe)
            if eff_cw <= 0:
                logger.info("货币战争：本次有效局数为 0，跳过")
                logger.info("旷宇纷争任务全部完成")
                return True

            on_cw = self._callback_for_module(state, cw_policy_raw, "cw")
            oc_tag = "超频" if is_overclock else "标准"
            logger.info(f"执行任务：旷宇纷争-货币战争 刷等级（{oc_tag}）")
            from tasks.currency_wars import CurrencyWars

            cw_fill_loop = (
                normalize_cosmic_policy(cw_policy_raw) == CosmicStrifeRunPolicy.FILL_CYCLE_REWARD
            )
            if cw_fill_loop:
                from tasks.currency_wars.CurrencyWars import CurrencyWarsPage

                for attempt in range(eff_cw):
                    if attempt > 0:
                        probe_cw = CurrencyWars(operator=self.operator, runtimes=0)
                        page = probe_cw.page_locate()
                        if page == CurrencyWarsPage.START:
                            prog_cw = read_cw_start_cycle_progress(self.operator)
                            if prog_cw is not None and prog_cw.is_full:
                                logger.info(
                                    "货币战争：大厅积分已满，提前结束剩余局数"
                                )
                                break
                        else:
                            logger.warning(
                                "货币战争：复检前未能定位到大厅 START，继续下一局"
                            )
                    cw_once = CurrencyWars(
                        operator=self.operator, runtimes=1, on_run_completed=on_cw
                    )
                    cw_once.load_strategy(strategy)
                    cw_once.set_difficulty(difficulty)
                    cw_once.set_overclock(is_overclock)
                    if not cw_once.run():
                        logger.error("旷宇纷争-货币战争任务失败")
                        return False
            else:
                cw_task = CurrencyWars(
                    operator=self.operator, runtimes=eff_cw, on_run_completed=on_cw
                )
                cw_task.load_strategy(strategy)
                cw_task.set_difficulty(difficulty)
                cw_task.set_overclock(is_overclock)
                if not cw_task.run():
                    logger.error("旷宇纷争-货币战争任务失败")
                    return False

        logger.info("旷宇纷争任务全部完成")
        return True

    def _resolve_du_effective_runs(
        self,
        state: CosmicStrifePolicyState,
        policy_raw: int,
        daily_cfg: int,
        weekly_total_cfg: int,
        shared: GuideCycleProbeResult | None = None,
    ) -> int:
        p = normalize_cosmic_policy(policy_raw)
        if p == CosmicStrifeRunPolicy.PER_INVOCATION:
            return max(0, daily_cfg)
        if p == CosmicStrifeRunPolicy.WEEKLY_AND_DAILY:
            d = remaining_daily(daily_cfg, state.du)
            w = remaining_weekly(weekly_total_cfg, state.du)
            return max(0, min(d, w))
        if p == CosmicStrifeRunPolicy.FILL_CYCLE_REWARD:
            if shared and shared.navigated:
                if shared.progress is not None and shared.progress.is_full:
                    logger.info("差分宇宙：周期奖励已满（指南页共用 OCR），跳过")
                    return 0
                if shared.progress is not None:
                    # 与前端「运行次数」一致：本轮按固定次数尝试，不用「自然日剩余额度」以免与周累计策略混淆
                    return max(0, daily_cfg)
            if shared and shared.navigated and shared.progress is None:
                logger.warning(
                    "差分宇宙：指南页未能解析周期进度，按配置运行次数执行（不用每日剩余额度）"
                )
            elif not (shared and shared.navigated):
                logger.warning(
                    "差分宇宙：未能打开指南旷宇纷争页，按配置运行次数执行（不用每日剩余额度）"
                )
            return max(0, daily_cfg)
        return max(0, daily_cfg)

    def _resolve_cw_effective_runs(
        self,
        state: CosmicStrifePolicyState,
        policy_raw: int,
        daily_cfg: int,
        weekly_total_cfg: int,
        shared: GuideCycleProbeResult | None = None,
    ) -> int:
        p = normalize_cosmic_policy(policy_raw)
        if p == CosmicStrifeRunPolicy.PER_INVOCATION:
            return max(0, daily_cfg)
        if p == CosmicStrifeRunPolicy.WEEKLY_AND_DAILY:
            d = remaining_daily(daily_cfg, state.cw)
            w = remaining_weekly(weekly_total_cfg, state.cw)
            return max(0, min(d, w))
        if p == CosmicStrifeRunPolicy.FILL_CYCLE_REWARD:
            if shared and shared.navigated:
                if shared.progress is not None and shared.progress.is_full:
                    logger.info("货币战争：周期奖励已满（指南页共用 OCR），跳过")
                    return 0
                if shared.progress is not None:
                    return max(0, daily_cfg)
            if shared and shared.navigated and shared.progress is None:
                logger.warning(
                    "货币战争：指南页未能解析周期进度，按配置运行次数执行"
                )
            elif not (shared and shared.navigated):
                logger.warning(
                    "货币战争：未能打开指南旷宇纷争页，按配置运行次数执行"
                )
            return max(0, daily_cfg)
        return max(0, daily_cfg)

    def _callback_for_module(self, state: CosmicStrifePolicyState, policy_raw: int, module: str):
        p = normalize_cosmic_policy(policy_raw)
        if p == CosmicStrifeRunPolicy.PER_INVOCATION:
            return None
        counters = state.du if module == "du" else state.cw

        def bump() -> None:
            register_completed_run(counters)
            save_policy_state(state)

        return bump
