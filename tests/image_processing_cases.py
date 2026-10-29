"""离线像素样本；不截图、不加载用户配置、不发送游戏输入。"""
from __future__ import annotations

from PIL import Image, ImageDraw
import numpy as np


def row(text, score=.999, box=None):
    return (box or [[10, 10], [150, 10], [150, 30], [10, 30]], text, score)


def equipment_frame(*, size=(1920, 1080), fault=None, color=(210, 170, 70)):
    image = Image.new("RGB", (1920, 1080), (15, 25, 35))
    draw = ImageDraw.Draw(image)
    for index, x in enumerate((679, 970, 1260)):
        if fault == "partial" and index == 0 or fault == "empty":
            continue
        draw.rectangle((x, 115, x + 258, 292), outline=color, width=2)
        if fault in {"gap1", "gap2", "gap3"}:
            gap = int(fault[-1])
            for dx in (40, 120, 200):
                draw.rectangle((x + dx, 114, x + dx + gap - 1, 118), fill=(15, 25, 35))
                draw.rectangle((x + dx, 289, x + dx + gap - 1, 294), fill=(15, 25, 35))
        if fault == "sides_missing":
            draw.rectangle((x - 2, 120, x + 3, 286), fill=(15, 25, 35))
            draw.rectangle((x + 255, 120, x + 261, 286), fill=(15, 25, 35))
        if fault == "content_changed" and index == 2:
            draw.rectangle((x + 4, 120, x + 254, 286), fill=(190, 80, 200))
    draw.rectangle((1025, 25, 1100, 32), fill="white")
    if fault == "no_title_pixels":
        draw.rectangle((1018, 15, 1200, 105), fill=(15, 25, 35))
    if fault == "clipped":
        draw.rectangle((675, 110, 690, 300), fill=(15, 25, 35))
    if fault == "roi_boundary":
        draw.rectangle((575, 115, 833, 292), outline=color, width=2)
        draw.rectangle((1500, 115, 1758, 292), outline=color, width=2)
    return image.resize(size, Image.Resampling.NEAREST)


def equipment_cases():
    title = [row("选择装备"), row("请选择1个", box=[[10, 45], [150, 45], [150, 65], [10, 65]])]
    for fault in (None, "empty", "partial", "gap1", "gap2", "gap3", "sides_missing",
                  "content_changed", "no_title_pixels", "clipped", "roi_boundary"):
        yield str(fault), equipment_frame(fault=fault), title
    for size in ((640, 360), (1280, 720), (1600, 900), (1024, 576), (640, 359), (1920, 1000)):
        yield f"size-{size}", equipment_frame(size=size), title
    for color in ((160, 125, 100), (159, 125, 70), (160, 124, 70), (160, 161, 70),
                  (160, 125, 115), (160, 125, 116), (210, 170, 255), (255, 255, 255)):
        yield f"color-{color}", equipment_frame(color=color), title
    for mode in ("L", "RGBA", "P", "CMYK", "F"):
        yield mode, equipment_frame().convert(mode), title
    for score in (.95, .949999, float("nan"), float("inf"), True, "bad"):
        yield f"score-{score}", equipment_frame(), [row("选择装备", score), title[1]]
    for index, rows in enumerate((None, [], [None], [row("请选择")], [row("选择装备", box=[[True, 0]])],
                                  [row("选择装备", box=[[0, 0]] * 4)], title * 20)):
        yield f"rows-{index}", equipment_frame(), rows
    for seed in range(8):
        pixels = np.random.default_rng(seed).integers(0, 256, (360, 640, 3), dtype=np.uint8)
        yield f"noise-{seed}", Image.fromarray(pixels), title
    for index, image in enumerate((None, object(), [], np.zeros((3, 3)), Image.new("RGB", (0, 0)))):
        yield f"invalid-{index}", image, title


def probability_frame(*, fault=None, blue=(20, 50, 210), dark=(20, 20, 20)):
    image = Image.new("RGB", (1920, 1080), (15, 25, 35))
    draw = ImageDraw.Draw(image)
    draw.rectangle((374, 238, 1527, 300), fill=blue)
    draw.rectangle((394, 325, 1526, 820), fill=dark)
    draw.rectangle((390, 246, 450, 261), fill="white")
    columns = ((835, (30, 180, 30)), (1025, (30, 60, 210)),
               (1217, (160, 50, 210)), (1405, (210, 140, 40)))
    for index, (x, color) in enumerate(columns):
        if fault != f"column-{index}":
            draw.rectangle((x, 335, x + 35, 352), fill=color)
    draw.line((1484, 251, 1516, 283), fill="white", width=3)
    draw.line((1516, 251, 1484, 283), fill="white", width=3)
    if fault in {"no_cross", "clipped_cross", "plus_cross"}:
        draw.rectangle((1471, 242, 1525, 296), fill=blue)
        if fault == "clipped_cross":
            draw.line((1471, 242, 1503, 274), fill="white", width=3)
            draw.line((1503, 242, 1471, 274), fill="white", width=3)
        if fault == "plus_cross":
            draw.line((1484, 267, 1516, 267), fill="white", width=3)
            draw.line((1500, 251, 1500, 283), fill="white", width=3)
    if fault == "no_title_pixels":
        draw.rectangle((374, 238, 874, 300), fill=blue)
    if fault == "no_body":
        draw.rectangle((394, 325, 1526, 820), fill="white")
    return image


def probability_cases():
    title = [row("商店刷新概率", box=[[10, 10], [300, 10], [300, 40], [10, 40]])]
    for fault in (None, "no_cross", "clipped_cross", "plus_cross", "no_title_pixels", "no_body",
                  "column-0", "column-1", "column-2", "column-3"):
        yield str(fault), probability_frame(fault=fault), title
    for blue in ((90, 100, 141), (90, 100, 140), (90, 100, 142), (159, 169, 210),
                 (160, 169, 210), (159, 170, 210), (250, 50, 210), (255, 255, 255)):
        yield f"blue-{blue}", probability_frame(blue=blue), title
    for dark in ((70, 70, 70), (71, 70, 70), (70, 71, 70), (70, 70, 71)):
        yield f"dark-{dark}", probability_frame(dark=dark), title
    for mode in ("L", "RGBA", "P", "CMYK", "F"):
        yield mode, probability_frame().convert(mode), title
    for score in (.95, .949999, float("nan"), float("inf"), True, "bad"):
        yield f"score-{score}", probability_frame(), [row("商店刷新概率", score, title[0][0])]
    for index, rows in enumerate((None, [], [None], [row("商店刷新")], [row("商店刷新概率", box=[[True, 0]])],
                                  [row("商店刷新概率", box=[[0, 0]] * 4)], title * 30)):
        yield f"rows-{index}", probability_frame(), rows
    for size in ((640, 360), (1280, 720), (640, 359), (1920, 1000)):
        yield f"size-{size}", probability_frame().resize(size), title
    for seed in range(4):
        pixels = np.random.default_rng(seed).integers(0, 256, (360, 640, 3), dtype=np.uint8)
        yield f"noise-{seed}", Image.fromarray(pixels), title
    for index, image in enumerate((None, object(), [], np.zeros((3, 3)), Image.new("RGB", (0, 0)))):
        yield f"invalid-{index}", image, title
