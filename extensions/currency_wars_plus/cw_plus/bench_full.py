"""失败恢复专用的满员提示及溢出队列证据；不发送输入。"""
from dataclasses import dataclass
from functools import lru_cache
from .paths import RESOURCE_ROOT


@dataclass(frozen=True)
class FullBenchObservation:
    known: bool
    full: bool = False
    queued: int | None = None
    score: float = 0.0


@lru_cache(maxsize=1)
def _warning_template():
    import cv2
    import numpy as np
    from PIL import Image
    with Image.open(RESOURCE_ROOT / 'bench_full_warning.png') as image:
        return cv2.cvtColor(np.asarray(image.convert('RGB')), cv2.COLOR_RGB2GRAY)


# Yukki：满员提示与队列形状须来自当前同一张截图。
def observe_full_bench(image):
    """只支持已校准客户区；文字图样和小卡片边框分别提供证据。"""
    if image is None or tuple(getattr(image, 'size', ())) != (1920, 1080):
        return FullBenchObservation(False)
    import cv2
    import numpy as np
    rgb = np.asarray(image.convert('RGB'))
    warning = cv2.cvtColor(rgb[510:558, 748:1192], cv2.COLOR_RGB2GRAY)
    score = float(cv2.minMaxLoc(cv2.matchTemplate(warning, _warning_template(),
                                                cv2.TM_CCOEFF_NORMED))[1])
    # 小卡片在已审核后台行下方，不能把正式备战区卡片计入队列。
    left, top = 192, 700
    crop = rgb[top:820, left:1652]
    dark = cv2.inRange(crop, np.array([0, 0, 0]), np.array([80, 80, 100]))
    contours, _ = cv2.findContours(dark, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if (70 <= w <= 82 and 82 <= h <= 94 and 706 <= top + y <= 736
                and cv2.contourArea(contour) >= 0.85 * w * h):
            box = (left + x, top + y, w, h)
            if not any(abs(box[0] - old[0]) <= 3 and abs(box[1] - old[1]) <= 3 for old in boxes):
                boxes.append(box)
    boxes.sort()
    if (len(boxes) > 9 or boxes and
            (max(b[1] for b in boxes) - min(b[1] for b in boxes) > 3
             or any(not 78 <= b[0] - a[0] <= 98 for a, b in zip(boxes, boxes[1:])))):
        return FullBenchObservation(False, score=score)
    return FullBenchObservation(True, score >= 0.94, len(boxes), score)
