"""Probability-dialog replay without a live game, OCR engine or network."""

import importlib.util
from pathlib import Path
import sys
import unittest

from PIL import Image, ImageDraw


from tests.currency_wars_replays import REPLAY_ROOT, require_frames

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("_currency_wars_shop_overlay", ROOT / "tasks/currency_wars/shop_overlay.py")
overlay = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = overlay
spec.loader.exec_module(overlay)
DIAGNOSTICS = REPLAY_ROOT / "shop_overlay"


def title_results(size=(1920, 1080), label="商店刷新概率", confidence=0.99):
    # Crop-relative title boxes, not whole-window coordinates.
    sx, sy = size[0] / 1920, size[1] / 1080
    return [([[x * sx, y * sy] for x, y in ((27, 10), (237, 10), (237, 45), (27, 45))], label, confidence)]


def synthetic_dialog():
    """A hand-drawn structural fixture; no production detector helpers used."""
    frame = Image.new("RGB", (1920, 1080), (35, 35, 85))
    draw = ImageDraw.Draw(frame)
    draw.rectangle((360, 228, 1558, 850), fill=(75, 89, 231))
    draw.rectangle((363, 306, 1555, 841), fill=(11, 11, 14))
    # Stand-ins for the independently supplied title OCR and colored headers.
    for x in range(404, 608, 30):
        draw.rectangle((x, 252, x + 12, 270), fill="white")
    for x, color in ((843, (65, 190, 145)), (1035, (88, 126, 250)),
                     (1227, (149, 95, 235)), (1415, (245, 190, 75))):
        draw.rectangle((x, 337, x + 46, 353), fill=color)
    draw.line((1480, 250, 1514, 284), fill="white", width=3)
    draw.line((1480, 284, 1514, 250), fill="white", width=3)
    return frame


class ShopProbabilityOverlayTests(unittest.TestCase):
    def assert_rejected(self, frame, results=None):
        result = overlay.detect_shop_probability_overlay(frame, title_results() if results is None else results)
        self.assertFalse(result.matched, result)
        self.assertIsNone(result.close_point)
        return result

    def test_exact_title_and_complete_structure_return_observed_cross_center(self):
        result = overlay.detect_shop_probability_overlay(synthetic_dialog(), title_results())
        self.assertTrue(result.matched, result)
        self.assertAlmostEqual(result.close_point[0], 1497 / 1920, places=3)
        self.assertAlmostEqual(result.close_point[1], 267 / 1080, places=3)

    def test_title_alone_cannot_close_an_arbitrary_page(self):
        for color in ("white", "black", (75, 89, 231)):
            with self.subTest(color=color):
                self.assert_rejected(Image.new("RGB", (1920, 1080), color))

    def test_similar_or_low_confidence_title_is_not_accepted(self):
        for label, confidence in (("商店刷新", 0.99), ("刷新概率", 0.99), ("非商店刷新概率", 0.99),
                                  ("商店刷新概率?", 0.99), ("商店刷新概率", 0.94),
                                  ("商店刷新概率", True), ("商店刷新概率", float("nan"))):
            with self.subTest(label=label, confidence=confidence):
                self.assert_rejected(synthetic_dialog(), title_results(label=label, confidence=confidence))

    def test_missing_or_malformed_title_box_is_rejected(self):
        for results in ([], [None], [(None, "商店刷新概率", 0.99)],
                        [([[-1, 0], [200, 0], [200, 40], [0, 40]], "商店刷新概率", 0.99)],
                        [([[400, 0], [650, 0], [650, 40], [400, 40]], "商店刷新概率", 0.99)]):
            with self.subTest(results=results):
                self.assert_rejected(synthetic_dialog(), results)

    def test_erased_title_rejects_stale_ocr(self):
        frame = synthetic_dialog()
        ImageDraw.Draw(frame).rectangle((375, 238, 873, 300), fill=(75, 89, 231))
        self.assert_rejected(frame)

    def test_missing_or_wrong_cost_header_does_not_authenticate_table(self):
        for color in ("white", (11, 11, 14), (245, 190, 75)):
            frame = synthetic_dialog()
            ImageDraw.Draw(frame).rectangle((831, 333, 916, 363), fill=color)
            self.assert_rejected(frame)

    def test_close_glyph_requires_both_diagonals_and_all_four_arms(self):
        for shape in ("none", "slash", "plus", "rectangle", "truncated"):
            with self.subTest(shape=shape):
                frame = synthetic_dialog()
                draw = ImageDraw.Draw(frame)
                draw.rectangle((1470, 242, 1526, 295), fill=(75, 89, 231))
                if shape == "slash":
                    draw.line((1480, 250, 1514, 284), fill="white", width=3)
                elif shape == "plus":
                    draw.line((1480, 267, 1514, 267), fill="white", width=3)
                    draw.line((1497, 250, 1497, 284), fill="white", width=3)
                elif shape == "rectangle":
                    draw.rectangle((1480, 250, 1514, 284), outline="white", width=3)
                elif shape == "truncated":
                    draw.line((1480, 250, 1514, 284), fill="white", width=3)
                    draw.line((1480, 284, 1497, 267), fill="white", width=3)
                self.assert_rejected(frame)

    def test_wrong_viewport_and_invalid_frame_are_rejected(self):
        for frame in (None, Image.new("RGB", (400, 300)), Image.new("RGB", (1920, 1200))):
            self.assert_rejected(frame)

    def test_real_probability_frames_and_supported_scales(self):
        paths = [DIAGNOSTICS / name for name in (
            "unknown_slot_on_field.png",
            "battle_shopping_shop_not_closed.png")]
        if not all(path.exists() for path in paths):
            self.skipTest("Local October 9 probability-dialog diagnosis frames are unavailable")
        for path in paths:
            with Image.open(path) as source:
                for size in ((1920, 1080), (1280, 720), (2560, 1440)):
                    with self.subTest(path=path.name, size=size):
                        frame = source.convert("RGB").resize(size)
                        result = overlay.detect_shop_probability_overlay(frame, title_results(size))
                        self.assertTrue(result.matched, result)
                        self.assertAlmostEqual(result.close_point[0], 1497 / 1920, delta=0.002)
                        self.assertAlmostEqual(result.close_point[1], 267 / 1080, delta=0.002)

    def test_real_preparation_and_open_shop_frames_reject_even_stale_title(self):
        paths = [REPLAY_ROOT / "bench_shop_holdouts/03_shop_occupied_client.png",
                 DIAGNOSTICS / "invalid_backend_layout_layout_not_stable.png"]
        available = [path for path in paths if path.exists()]
        if len(available) != len(paths):
            self.skipTest("Local open-shop and preparation replay frames are unavailable")
        for path in available:
            with self.subTest(path=path.name), Image.open(path) as frame:
                self.assert_rejected(frame)


if __name__ == "__main__":
    unittest.main()
