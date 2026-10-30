"""预转换图像的首个匹配必须与 Pyscreeze 1.0.1 的逐行顺序一致。"""
from __future__ import annotations

import cv2
import numpy as np
import pyscreeze
import pytest

from extensions.cw_plus.unicode_templates import locate_first


def original_match(needle, haystack, confidence):
    try:
        result = pyscreeze.locate(needle, haystack, grayscale=False, confidence=confidence)
        return tuple(result) if result is not None else None
    except pyscreeze.ImageNotFoundException:
        return None


def arrays(channels=1):
    rng = np.random.default_rng(521)
    shape = (17, 13) if channels == 1 else (17, 13, channels)
    needle = rng.integers(0, 256, shape, dtype=np.uint8)
    shape = (96, 128) if channels == 1 else (96, 128, channels)
    return needle, rng.integers(0, 64, shape, dtype=np.uint8)


@pytest.mark.parametrize("channels", [1, 3])
@pytest.mark.parametrize("equal", [True, False])
def test_first_row_major_candidate_is_not_replaced_by_later_best(channels, equal):
    needle, haystack = arrays(channels)
    haystack[5:22, 70:83] = needle
    haystack[50:67, 4:17] = needle
    if not equal:
        haystack[5, 70] = 0
    actual = locate_first(needle, haystack, confidence=.95)
    assert actual == (70, 5, 13, 17)
    assert actual == original_match(needle, haystack, .95)


@pytest.mark.parametrize("corner", [(0, 0), (115, 0), (0, 79), (115, 79)])
def test_boundary_coordinates_are_preserved(corner):
    needle, haystack = arrays()
    x, y = corner
    haystack[y:y + 17, x:x + 13] = needle
    assert locate_first(needle, haystack, confidence=.95) == (*corner, 13, 17)


@pytest.mark.parametrize("confidence", [0, .7, .95, 1, 1.1, float("nan"), float("inf"), -float("inf"), "0.95"])
@pytest.mark.parametrize("channels", [1, 3])
def test_thresholds_and_empty_results_match_original(confidence, channels):
    needle, haystack = arrays(channels)
    haystack[30:47, 40:53] = needle
    assert locate_first(needle, haystack, confidence=confidence) == original_match(needle, haystack, confidence)


def test_score_equal_to_threshold_is_not_accepted():
    needle, _ = arrays()
    image = needle.copy()
    image[0, 0] = 0
    score = float(cv2.matchTemplate(image, needle, cv2.TM_CCOEFF_NORMED)[0, 0])
    assert locate_first(needle, image, confidence=score) is None
    assert locate_first(needle, image, confidence=score) == original_match(needle, image, score)
    below = float(np.nextafter(np.float32(score), np.float32(-np.inf)))
    assert locate_first(needle, image, confidence=below) == (0, 0, 13, 17)


def test_constant_images_keep_dense_match_order():
    needle = np.zeros((5, 7), dtype=np.uint8)
    haystack = np.zeros((80, 100), dtype=np.uint8)
    assert locate_first(needle, haystack, confidence=.95) == original_match(needle, haystack, .95) == (0, 0, 7, 5)


@pytest.mark.parametrize("kind", ["empty", "oversized", "channels", "float64", "rank1", "float32", "strided"])
def test_unusual_arrays_preserve_result_or_exception_class(kind):
    needle, haystack = arrays()
    if kind == "empty":
        haystack = haystack[:0]
    elif kind == "oversized":
        haystack = haystack[:3, :4]
    elif kind == "channels":
        haystack = np.repeat(haystack[..., None], 3, axis=2)
    elif kind == "float64":
        needle, haystack = needle.astype(np.float64), haystack.astype(np.float64)
    elif kind == "rank1":
        needle = needle[0]
    elif kind == "float32":
        needle, haystack = needle.astype(np.float32), haystack.astype(np.float32)
    elif kind == "strided":
        needle, haystack = needle[:, ::-1], haystack[:, ::-1]
    try:
        expected = original_match(needle, haystack, .95)
    except Exception as error:
        with pytest.raises(type(error)):
            locate_first(needle, haystack, confidence=.95)
    else:
        assert locate_first(needle, haystack, confidence=.95) == expected
