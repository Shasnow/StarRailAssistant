from enum import IntEnum


class CosmicStrifeRunPolicy(IntEnum):
    """旷宇纷争（差分宇宙 / 货币战争）策略（与前端 ComboBox 索引一致）"""

    # 策略1：本次任务运行多少次（不跨次累计）
    PER_INVOCATION = 0
    # 策略2：周内累计上限 + 自然日每日最多尝试次数（次数框=每日，另配每周总上限）
    WEEKLY_AND_DAILY = 1
    # 策略3：大厅 OCR 已满则跳过；否则受自然日每日最多尝试次数限制
    FILL_CYCLE_REWARD = 2


def normalize_cosmic_policy(raw: int) -> CosmicStrifeRunPolicy:
    """与前端三档一致：0/1/2。仅兼容未走前端迁移、仍含旧四档索引 3 的 JSON/CLI 配置。"""
    p = int(raw)
    if p == 3:
        return CosmicStrifeRunPolicy.FILL_CYCLE_REWARD
    if p < 0:
        p = 0
    elif p > 2:
        p = 2
    return CosmicStrifeRunPolicy(p)
