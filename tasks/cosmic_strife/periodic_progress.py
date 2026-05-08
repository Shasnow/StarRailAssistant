from __future__ import annotations

import re
from dataclasses import dataclass
from loguru import logger

# 周期奖励进度 OCR 区域（归一化坐标 0–1，相对游戏客户端窗口）
# 星际和平指南 → 旷宇纷争：左侧子玩法列表页，左下角「周期积分」与「剩余时间」共用区域（DU/CW 周期进度一致）
_GUIDE_COSMIC_STRIFE_CYCLE_ROI = (0.02, 0.84, 0.36, 0.97)
# 差分乐园漫记 hub：左下角周期进度条（如 18000/18000），上方常为「本期剩余时间」— hub 复检用，无需开指南
_DU_HUB_ROI = (0.012, 0.825, 0.38, 0.968)
# 货币战争 START 大厅左下「积分」— 单局结束回到大厅后复检，无需开指南
_CW_LOBBY_POINTS_ROI = (0.008, 0.8765, 0.248, 0.948)

_FRACTION_RE = re.compile(r"(\d{1,7})\s*[/／]\s*(\d{1,7})")


@dataclass(frozen=True)
class CycleProgress:
    """大厅 OCR 解析结果：斜杠左侧为当前积分，右侧为周期上限。"""

    current: int
    maximum: int

    @property
    def is_full(self) -> bool:
        """已达周期上限：上限大于 0 且当前大于等于上限（含两侧数字相等）。"""
        return self.maximum > 0 and self.current >= self.maximum


def _ocr_lines(operator, roi: tuple[float, float, float, float]) -> list[str]:
    fx, fy, tx, ty = roi
    raw = operator.ocr(from_x=fx, from_y=fy, to_x=tx, to_y=ty, trace=False)
    if not raw:
        return []
    lines: list[str] = []
    for item in raw:
        if len(item) > 1 and item[1]:
            lines.append(str(item[1]).strip())
    return lines


def parse_cycle_progress_from_texts(texts: list[str]) -> CycleProgress | None:
    """从 OCR 文本中解析「当前/上限」类周期进度；无法解析则返回 None。"""
    blob = " ".join(texts)
    if "已满" in blob or "已滿" in blob:
        return CycleProgress(1, 1)

    # 同一识别框内数字与斜杠可能被拆行，追加去空格拼接串再扫一遍
    compact = blob.replace(" ", "")
    scan_sources = list(dict.fromkeys([*texts, blob, compact]))

    best: tuple[int, int] | None = None
    best_max = -1
    for line in scan_sources:
        for m in _FRACTION_RE.finditer(line):
            cur = int(m.group(1))
            mx = int(m.group(2))
            if mx <= 0 or cur < 0:
                continue
            if cur > mx * 2:  # 明显噪声
                continue
            if mx > best_max:
                best_max = mx
                best = (cur, mx)
    if best is None:
        return None
    return CycleProgress(best[0], best[1])


def read_du_hub_cycle_progress(operator) -> CycleProgress | None:
    lines = _ocr_lines(operator, _DU_HUB_ROI)
    logger.info(f"差分宇宙乐园漫记 hub（左下）周期进度 OCR 原始行: {lines}")
    return parse_cycle_progress_from_texts(lines)


def read_cw_start_cycle_progress(operator) -> CycleProgress | None:
    lines = _ocr_lines(operator, _CW_LOBBY_POINTS_ROI)
    logger.info(f"货币战争大厅积分 OCR 原始行: {lines}")
    return parse_cycle_progress_from_texts(lines)


def read_guide_shared_cycle_progress(operator) -> CycleProgress | None:
    """指南「旷宇纷争」总览页左下角「周期积分」区域 OCR（与差分/货币战争子玩法共用进度）。"""
    lines = _ocr_lines(operator, _GUIDE_COSMIC_STRIFE_CYCLE_ROI)
    logger.info(f"旷宇纷争指南页周期积分 OCR 原始行: {lines}")
    return parse_cycle_progress_from_texts(lines)


@dataclass(frozen=True)
class GuideCycleProbeResult:
    """在指南总览页完成的共用周期探测。"""

    navigated: bool
    progress: CycleProgress | None


def navigate_cosmic_strife_guide_for_shared_cycle(operator, settings) -> bool:
    """从大地图经 F4 进入星际和平指南 → 旷宇纷争，停在左侧子玩法列表（不点「前往参与」）。"""
    from SRACore.util.errors import ErrorCode, SRAError

    from tasks.img import CWIMG, DUIMG, IMG

    _page_imgs = [
        IMG.ENTER,
        DUIMG.DIFFERENTIAL_UNIVERSE_START,
        CWIMG.START_CURRENCY_WARS,
        CWIMG.PREPARATION_STAGE,
        DUIMG.BONUS_POINTS,
    ]
    for _ in range(14):
        page, _ = operator.wait_any_img(_page_imgs, interval=0.65)
        if page == 0:
            break
        if page == -1:
            logger.warning("旷宇纷争指南：未识别到大地图或玩法界面，中止共用周期导航")
            return False
        logger.info("旷宇纷争指南：尝试 ESC 退回大地图以便打开指南")
        operator.press_key("esc")
        operator.sleep(0.55)
    else:
        logger.error("旷宇纷争指南：多次 ESC 后仍未回到大地图，中止共用周期导航")
        return False

    hotkey = str(settings.General.hotkeyF4).lower()
    operator.press_key(hotkey)
    if not operator.wait_img(IMG.F4, timeout=20):
        logger.error(SRAError(ErrorCode.WAIT_TIMEOUT, "旷宇纷争指南：等待指南界面超时"))
        operator.press_key("esc")
        return False
    operator.click_img(IMG.COSMIC_STRIFE, after_sleep=1.2)
    return True


def probe_shared_cycle_via_guide(operator, settings) -> GuideCycleProbeResult:
    """导航到指南旷宇纷争总览页并 OCR 周期积分；导航失败则 navigated=False。"""
    if not navigate_cosmic_strife_guide_for_shared_cycle(operator, settings):
        return GuideCycleProbeResult(navigated=False, progress=None)
    prog = read_guide_shared_cycle_progress(operator)
    return GuideCycleProbeResult(navigated=True, progress=prog)


def close_guide_return_to_map(operator) -> None:
    """关闭指南/上层菜单，尽量回到大地图，便于后续 page_locate。"""
    operator.press_key("esc", presses=2, interval=0.55)
