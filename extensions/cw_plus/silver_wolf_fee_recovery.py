"""仅在升级所需费用未知时，读取银狼详情面板中的费用。"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
import time
import unicodedata

from .logic import SlotState
from .preparation import observation_identity

SILVER_WOLF = '银狼LV.999'
PANEL_ROI = (.775, .15, .975, .50)
VERIFIED_FEES = frozenset((3, 4, 5))


@dataclass(frozen=True)
class PanelFeeObservation:
    known: bool
    fee: int | None = None
    reason: str = 'not_observed'
    name: str = ''
    name_box: tuple[float, ...] = ()
    price_box: tuple[float, ...] = ()


def _name_key(value):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value)).casefold()


# Yukki：角色标题与费用位置共同约束详情面板读数。
def parse_panel_fee(rows, *, frame_size, crop_box, expected_name=SILVER_WOLF, scale=1):
    """将准确的标题角色名与其右上费用关联，不使用星级或属性数值代替费用。"""
    if (not isinstance(frame_size, (tuple, list)) or len(frame_size) != 2
            or any(type(v) is not int or v <= 0 for v in frame_size)
            or not isinstance(crop_box, (tuple, list)) or len(crop_box) != 4
            or type(scale) is not int or scale not in (1, 2)):
        return PanelFeeObservation(False, reason='invalid_geometry')
    width, height = frame_size
    left, top, right, bottom = crop_box
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        return PanelFeeObservation(False, reason='invalid_crop')
    if not isinstance(rows, (tuple, list)):
        return PanelFeeObservation(False, reason='no_ocr')
    tokens = []
    for row in rows:
        if not isinstance(row, (tuple, list)) or len(row) < 3 or not isinstance(row[1], str):
            continue
        box, text, score = row[:3]
        if (isinstance(score, bool) or not isinstance(score, (int, float))
                or not math.isfinite(score) or not .90 <= score <= 1
                or not isinstance(box, (tuple, list)) or len(box) != 4):
            continue
        try:
            if any(len(p) != 2 or any(isinstance(v, bool) or not math.isfinite(float(v)) for v in p) for p in box):
                continue
            xs, ys = [float(p[0]) / scale for p in box], [float(p[1]) / scale for p in box]
        except (TypeError, ValueError, OverflowError):
            continue
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        # 被裁断的文本不能作为独立的费用或角色名观测。
        if not (1 < x0 < x1 < right - left - 1 and 1 < y0 < y1 < bottom - top - 1):
            continue
        tokens.append((_name_key(text), (x0 + left, y0 + top, x1 + left, y1 + top)))
    expected = _name_key(expected_name)
    name_matches = []
    for text, box in tokens:
        if text == expected and .775 * width <= box[0] < box[2] <= .93 * width:
            name_matches.append(box)
    # 现有文字识别有时会把拉丁字母后缀与中文角色名分开。
    for text, box in tokens:
        for other, other_box in tokens:
            if text + other != expected:
                continue
            overlap = min(box[3], other_box[3]) - max(box[1], other_box[1])
            if (box[2] <= other_box[0] <= box[2] + .035 * width
                    and overlap >= min(box[3] - box[1], other_box[3] - other_box[1]) * .5):
                joined = min(box[0], other_box[0]), min(box[1], other_box[1]), max(box[2], other_box[2]), max(box[3], other_box[3])
                if .775 * width <= joined[0] < joined[2] <= .93 * width:
                    name_matches.append(joined)
    distinct_names = set(name_matches)
    if len(distinct_names) != 1:
        return PanelFeeObservation(False, reason='panel_name_unknown_or_ambiguous')
    name_box = next(iter(distinct_names))
    name_y = (name_box[1] + name_box[3]) / 2
    fees = []
    for text, box in tokens:
        if not re.fullmatch(r'[1-5]', text):
            continue
        delta = (box[1] + box[3]) / 2 - name_y
        if (.950 * width <= box[0] < box[2] <= .975 * width
                and -.045 * height <= delta <= .015 * height
                and box[0] > name_box[2]):
            fees.append((int(text), box))
    if len(set(fees)) != 1:
        return PanelFeeObservation(False, reason='panel_price_unknown_or_ambiguous', name=expected_name, name_box=name_box)
    fee, price_box = fees[0]
    return PanelFeeObservation(True, fee, 'same_frame_named_panel_fee', expected_name, name_box, price_box)


def _source_signature(task, area, index):
    obs = task._observations[area][index]
    return (task._layout_revision, area, index, obs.revision, observation_identity(obs), obs.stars)


# ssyb：补测受既有恢复额度约束，不独立消费金币。
def recover_unknown_silver_wolf_fee(task, result, *, battle_template, stop_type, logger):
    """在现有恢复内进行一次有界补测，不发送任何消费输入。"""
    if result.reason != 'upgrade_gate_unknown':
        return False
    gate = task.formation_config.upgrade_gate if task.formation_config else None
    if gate is None or SILVER_WOLF not in gate.prices or SILVER_WOLF in task._observed_prices:
        return False
    # 截图、点击面板或进行文字识别前，重新核实最初的未知原因。
    last = getattr(task, '_last_level_read', None)
    level = getattr(last, 'level', None)
    if type(level) is not int or level < gate.from_level:
        return False
    if task._economy_upgrade_gate(level, {})[3] != 'upgrade_gate_price_unknown':
        return False
    if any(name != SILVER_WOLF and name not in task._observed_prices for name in gate.prices):
        return False
    if (task._coin_shop_open is not False or not task._layout_valid
            or task._purchase_pending_names or task._pending_move is not None
            or task._selection_event_pending is not None or task._form_change_pending
            or task._preparation_round is None or task._preparation_round == (3, 7)
            or task._preparation_budget_spent()):
        return False
    preparation_id = getattr(task, '_preparation_id', None)
    if preparation_id is None:
        return False
    checkpoint = task._session_store.checkpoint if task._session_store is not None else None
    scope = (checkpoint.run_id if checkpoint is not None else None, preparation_id)
    if getattr(task, '_silver_wolf_fee_retest_scope', None) == scope:
        return False
    sources = [(area, index) for area in ('on_field', 'off_field', 'in_hand')
        for index, obs in enumerate(task._observations[area])
        if (obs.state == SlotState.KNOWN and observation_identity(obs) == ('known', SILVER_WOLF)
            and type(obs.stars) is int and obs.stars in (1, 2, 3)
            and not obs.character.is_npc and not obs.character.is_locked
            and (area, index) not in task._dirty_slots)]
    if not sources:
        return False
    field_sources = [entry for entry in sources if entry[0] != 'in_hand']
    if len(field_sources) > 1:
        return False
    area, index = (field_sources or sources)[0]
    if area == 'off_field' and (index in task._backend_unknown_slots or index not in task._backend_ordinary_slots):
        return False
    if not callable(getattr(task.operator, 'ocr_engine', None)):
        return False
    task._check_stop()
    task._silver_wolf_fee_retest_scope = scope
    record = dict(state='unknown', reason='not_completed', source=(area, index), frames=0,
                  ocr_calls=0, fee=None, spending_inputs=0)
    task._silver_wolf_fee_retest_last = record
    logger.info(f'[银狼费用复测] 已判定费用未知，进入本准备期唯一补测，来源={area}[{index}]')
    signature = _source_signature(task, area, index)
    readings = []
    opened = False
    failure = None
    close_failed = False
    deadline = min(task._preparation_deadline or math.inf, time.monotonic() + 12)

    def check():
        task._check_stop()
        if time.monotonic() >= deadline or task._preparation_budget_spent():
            raise TimeoutError('fee_retest_deadline')
        if signature != _source_signature(task, area, index):
            raise ValueError('fee_retest_source_changed')

    try:
        check()
        frame = task._capture_page_frame()
        if frame is None or task._locate_page_template(battle_template, frame) is None:
            raise ValueError('preparation_not_confirmed')
        check()
        position = getattr(task, area + '_area')[index]
        if not task.operator.click_point(*position, after_sleep=.2, trace=False):
            raise ValueError('panel_click_failed')
        opened = True
        for frame_index in range(2):
            check()
            frame = task._capture_page_frame()
            if frame is None:
                raise ValueError('panel_frame_unavailable')
            record['frames'] += 1
            width, height = frame.size
            crop_box = tuple(round(value * (width if i % 2 == 0 else height)) for i, value in enumerate(PANEL_ROI))
            crop = frame.crop(crop_box).convert('RGB')
            reading = PanelFeeObservation(False, reason='panel_price_not_read')
            for scale in (1, 2):
                check()
                image = crop if scale == 1 else crop.resize((crop.width * 2, crop.height * 2))
                record['ocr_calls'] += 1
                rows = task._vision._engine_ocr(image, minimum_confidence=.90)
                reading = parse_panel_fee(rows, frame_size=frame.size, crop_box=crop_box, scale=scale)
                if reading.known:
                    break
            readings.append(reading)
            if not reading.known or reading.fee not in VERIFIED_FEES:
                raise ValueError(reading.reason if not reading.known else 'silver_wolf_fee_outside_verified_range')
            if frame_index == 0:
                task.operator.sleep(.15)
        check()
        if readings[0].fee != readings[1].fee:
            raise ValueError('panel_fee_frames_disagree')
    except (stop_type, InterruptedError):
        raise
    except Exception as error:
        failure = str(error) if isinstance(error, (ValueError, TimeoutError)) else type(error).__name__
    finally:
        if opened:
            # 收到停止请求后立即结束全部输入，也不再点击清理控件。
            task._check_stop()
            if not task.operator.click_point(.5, .5, trace=False):
                close_failed = True
            else:
                closed_frame = task._capture_page_frame()
                close_failed = (closed_frame is None or task._locate_page_template(battle_template, closed_frame) is None)
    if close_failed:
        record['reason'] = 'fee_panel_close_not_confirmed'
        raise RuntimeError('银狼费用补测后未确认返回准备界面')
    task._check_stop()
    if failure is not None:
        record['reason'] = failure
        logger.warning(f'[银狼费用复测] 补测未确认：{failure}；沿用原有恢复，不推断费用')
        return False
    try:
        check()
    except (stop_type, InterruptedError):
        raise
    except (ValueError, TimeoutError) as error:
        record['reason'] = str(error)
        return False
    if SILVER_WOLF in task._observed_prices or task._form_change_pending or task._selection_event_pending is not None:
        record['reason'] = 'evidence_changed_before_commit'
        return False
    fee = readings[0].fee
    task._observed_prices[SILVER_WOLF] = fee
    record.update(state='confirmed', reason='two_named_panel_frames', fee=fee)
    logger.info(f'[银狼费用复测] 双帧确认费用={fee}，返回原购物决策；本次无刷新、买牌或买经验输入')
    return True
