from tasks.cosmic_strife.periodic_progress import CycleProgress, parse_cycle_progress_from_texts
from tasks.cosmic_strife.policy_defs import CosmicStrifeRunPolicy, normalize_cosmic_policy
from tasks.cosmic_strife.state_store import ModuleRunCounters, remaining_daily


def test_parse_fraction_prefers_largest_max():
    texts = ["无关", "50／300", "周期 80/100"]
    got = parse_cycle_progress_from_texts(texts)
    assert got == CycleProgress(50, 300)


def test_parse_full_keyword():
    texts = ["奖励", "已满"]
    got = parse_cycle_progress_from_texts(texts)
    assert got is not None and got.is_full


def test_parse_guide_style_cycle_line():
    """指南页「周期积分」旁常见 OCR 碎片：仍能解析 18000/18000。"""
    texts = ["剩余时间", "周期积分", "18000/18000"]
    got = parse_cycle_progress_from_texts(texts)
    assert got == CycleProgress(18000, 18000)
    assert got.is_full


def test_parse_cw_lobby_equal_means_full():
    """货币战争大厅积分：左右相等视为已达上限（刷满周期策略可跳过）。"""
    texts = ["积分", "18000/18000"]
    got = parse_cycle_progress_from_texts(texts)
    assert got == CycleProgress(18000, 18000)
    assert got.is_full


def test_parse_compact_fragmented_digits():
    got = parse_cycle_progress_from_texts(["18000", "/", "18000"])
    assert got == CycleProgress(18000, 18000)
    assert got.is_full


def test_remaining_daily_resets_new_day():
    c = ModuleRunCounters(daily_date="1999-01-01", daily_runs=5, week_key="2026-W01", weekly_runs=0)
    left = remaining_daily(10, c)
    assert left == 10
    assert c.daily_runs == 0


def test_policy_enum_values_stable():
    assert CosmicStrifeRunPolicy.PER_INVOCATION == 0
    assert CosmicStrifeRunPolicy.WEEKLY_AND_DAILY == 1
    assert CosmicStrifeRunPolicy.FILL_CYCLE_REWARD == 2


def test_normalize_three_tier_and_legacy_three_alias():
    assert normalize_cosmic_policy(0) == CosmicStrifeRunPolicy.PER_INVOCATION
    assert normalize_cosmic_policy(1) == CosmicStrifeRunPolicy.WEEKLY_AND_DAILY
    assert normalize_cosmic_policy(2) == CosmicStrifeRunPolicy.FILL_CYCLE_REWARD
    assert normalize_cosmic_policy(3) == CosmicStrifeRunPolicy.FILL_CYCLE_REWARD
    assert normalize_cosmic_policy(-1) == CosmicStrifeRunPolicy.PER_INVOCATION
    assert normalize_cosmic_policy(99) == CosmicStrifeRunPolicy.FILL_CYCLE_REWARD
