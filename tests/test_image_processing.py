"""通过只读公开入口验证像素几何及识别结果，不运行游戏。"""
from __future__ import annotations

from dataclasses import asdict

import pytest

from extensions.cw_plus import equipment_choice as equipment
from extensions.cw_plus import shop_overlay as probability
from tests.image_processing_cases import equipment_cases, equipment_frame, probability_cases, probability_frame, row


@pytest.mark.parametrize("fault,matched,partial", [
    (None, True, False), ("gap1", True, False), ("gap2", True, False),
    ("gap3", False, False), ("sides_missing", False, False),
    ("partial", False, True), ("clipped", False, True), ("empty", False, False),
])
def test_equipment_requires_complete_real_borders(fault, matched, partial):
    image = equipment_frame(fault=fault)
    cards, actual_partial = equipment.equipment_choice_geometry(image)
    assert bool(cards) is matched
    assert actual_partial is partial
    assert equipment.equipment_choice_cards(image) == cards
    if matched:
        assert cards == tuple((x / 1920, 115 / 1080, (x + 258) / 1920, 292 / 1080)
                              for x in (679, 970, 1260))


def test_equipment_observation_retains_coordinates_content_and_title_rules():
    image = equipment_frame()
    rows = [row("选择装备"), row("请选择1个", box=[[10, 45], [150, 45], [150, 65], [10, 65]])]
    result = equipment.detect_equipment_choice(image, rows)
    assert result.matched and result.present
    # 上游先归一化边界再取中心；直接除像素中心会相差一个浮点 ULP。
    assert result.choice_point == (0.7234375, 0.18842592592592594)
    assert result.evidence == "equipment_exact_title_count_and_three_gold_cards"
    assert len(result.appearance) == 48 * 16 * 3
    assert equipment.same_equipment_choice(result, equipment.detect_equipment_choice(image.copy(), rows))
    assert not equipment.same_equipment_choice(result, equipment.detect_equipment_choice(
        equipment_frame(fault="content_changed"), rows))
    assert not equipment.detect_equipment_choice(image, [row("选择装备", .949999), rows[1]]).matched


@pytest.mark.parametrize("fault,evidence", [
    (None, "probability_exact_title_table_and_cross"),
    ("no_cross", "probability_close_cross_missing"),
    ("clipped_cross", "probability_close_cross_missing"),
    ("plus_cross", "probability_close_cross_missing"),
    ("no_title_pixels", "probability_title_pixels_missing"),
    ("no_body", "probability_panel_structure_missing"),
    ("column-0", "probability_columns_missing"),
    ("column-1", "probability_columns_missing"),
    ("column-2", "probability_columns_missing"),
    ("column-3", "probability_columns_missing"),
])
def test_probability_requires_title_table_columns_and_complete_cross(fault, evidence):
    image = probability_frame(fault=fault)
    rows = [row("商店刷新概率", box=[[10, 10], [300, 10], [300, 40], [10, 40]])]
    panel = probability.observe_shop_probability_panel(image)
    result = probability.detect_shop_probability_overlay(image, rows, panel_observation=panel)
    assert result.evidence == evidence
    assert result.matched is (fault is None)
    assert result.close_point == ((1500 / 1920, 267 / 1080) if fault is None else None)
    assert panel.image is image
    assert probability.shop_probability_panel_present(image) is panel.present
    assert asdict(probability.detect_shop_probability_overlay(image, rows)) == asdict(result)


def test_equipment_reused_geometry_does_not_change_full_observation():
    for name, image, rows in equipment_cases():
        geometry = equipment.equipment_choice_geometry(image)
        result = equipment.detect_equipment_choice(image, rows)
        if geometry is not None:
            reused = equipment.detect_equipment_choice(image, rows, cards=geometry[0])
            assert asdict(result) == asdict(reused), name


def test_probability_observation_reuse_belongs_to_exact_frame():
    for name, image, rows in probability_cases():
        panel = probability.observe_shop_probability_panel(image)
        result = probability.detect_shop_probability_overlay(image, rows)
        reused = probability.detect_shop_probability_overlay(image, rows, panel_observation=panel)
        assert asdict(result) == asdict(reused), name
        if hasattr(image, "copy") and not name.startswith("invalid"):
            other = image.copy()
            actual = probability.detect_shop_probability_overlay(other, rows, panel_observation=panel)
            assert asdict(actual) == asdict(result), name
