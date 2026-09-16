"""
通用颜色目标检测算法
=====================
适用于任意 HSV 颜色范围内的游戏/画面目标检测。
核心思路：HSV 色彩过滤 → 形态学去噪 → 轮廓提取 → 质心 + 外接框定位。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional, Tuple, List

import cv2
import numpy as np


# ============================================================
#  数据结构定义
# ============================================================

class ContourSort(StrEnum):
    """轮廓排序方式"""
    AREA_DESC = "area_desc"       # 按面积降序（默认，找最大目标）
    AREA_ASC = "area_asc"          # 按面积升序（找最小目标）
    Y_POSITION = "y_position"      # 按 Y 坐标排序（找画面最上方/最近的目标）
    X_POSITION = "x_position"      # 按 X 坐标排序（找最左/右目标）


@dataclass
class DetectionParams:
    """
    检测参数集合。

    属性说明:
    ----------
    hsv_lower : Tuple[int, int, int]
        HSV 下界 (H, S, V)。
        H 范围 0-179 (OpenCV 约定，实际色相 / 2)，
        S 范围 0-255，
        V 范围 0-255。
        例: 随意门 → (140, 80, 150)

    hsv_upper : Tuple[int, int, int]
        HSV 上界 (H, S, V)。
        例: 随意门 → (170, 255, 255)

    min_area : int
        最小有效轮廓面积（像素），小于此值的轮廓视为噪点被丢弃。
        面积太小 → 漏检；太大 → 抗噪但可能漏掉远处小目标。
        例: 500 (近处大目标) ~ 50 (远处小目标)

    max_area : int
        最大有效轮廓面积，超过此值视为误检（如全屏同色背景）。
        0 表示不限制。

    open_kernel : int
        开运算核大小（像素）。开运算 = 先腐蚀后膨胀，消除孤立小噪点。
        0 = 跳过开运算。
        例: 5

    close_kernel : int
        闭运算核大小（像素）。闭运算 = 先膨胀后腐蚀，填充目标内部空洞。
        0 = 跳过闭运算。
        例: 15

    blur_size : int
        高斯模糊核大小（奇数）。平滑掩码边缘，减少碎片化轮廓。
        0 = 跳过模糊。

    sort_by : ContourSort
        多个有效轮廓时的排序/选取方式。

    max_targets : int
        最多返回的目标数量。0 = 返回全部。

    min_aspect_ratio : float
        最小宽高比 (w/h)，用于过滤形状不符合的目标。
        0 = 不检查。

    max_aspect_ratio : float
        最大宽高比 (w/h)。
        0 = 不检查。

    roi : Optional[Tuple[int, int, int, int]]
        感兴趣区域 (x, y, w, h)，只在此矩形内做检测，提升性能 + 减少误检。
        None = 全图检测。

    fallback_hsv_ranges : List[Tuple[Tuple[int,int,int], Tuple[int,int,int]]]
        备用 HSV 范围列表。当主范围匹配结果为空时，依次尝试这些范围。
        适用于目标颜色会变化（如门在不同场景下颜色偏移）的场景。
    """
    hsv_lower: Tuple[int, int, int] = (0, 0, 0)
    hsv_upper: Tuple[int, int, int] = (179, 255, 255)
    min_area: int = 500
    max_area: int = 0
    open_kernel: int = 5
    close_kernel: int = 15
    blur_size: int = 5
    sort_by: ContourSort = ContourSort.AREA_DESC
    max_targets: int = 1
    min_aspect_ratio: float = 0.0
    max_aspect_ratio: float = 0.0
    roi: Optional[Tuple[int, int, int, int]] = None
    fallback_hsv_ranges: List = field(default_factory=list)


@dataclass
class DetectionResult:
    """
    单个目标的检测结果。

    属性说明:
    ----------
    found : bool
        是否检测到目标。

    center_x : int
        目标质心 X 坐标（像素），画面左上角为原点。

    center_y : int
        目标质心 Y 坐标（像素）。

    bbox_x : int
        外接矩形左上角 X。

    bbox_y : int
        外接矩形左上角 Y。

    bbox_w : int
        外接矩形宽度。

    bbox_h : int
        外接矩形高度。

    area : float
        轮廓面积（像素²）。可用于判断目标远近：
        面积越大 → 越近；面积越小 → 越远。

    aspect_ratio : float
        宽高比 = bbox_w / bbox_h。

    confidence : float
        置信度 0.0~1.0。定义为:
        目标面积 / ROI(或全图)面积 × 100 后 clamp。
        值越高表示目标在画面中占比越大、检测越可靠。

    contour : np.ndarray
        原始轮廓点数组，可用于绘制或进一步分析（如凸包、轮廓矩）。

    hsv_range_used : Tuple[Tuple[int,int,int], Tuple[int,int,int]]
        实际命中时使用的 HSV 范围（主范围或某个 fallback）。
    """
    found: bool = False
    center_x: int = 0
    center_y: int = 0
    bbox_x: int = 0
    bbox_y: int = 0
    bbox_w: int = 0
    bbox_h: int = 0
    area: float = 0.0
    aspect_ratio: float = 0.0
    confidence: float = 0.0
    contour: Optional[np.ndarray] = None
    hsv_range_used: Tuple = ((0, 0, 0), (179, 255, 255))


# ============================================================
#  核心检测器
# ============================================================

class ColorTargetDetector:
    """
    通用颜色目标检测器。

    用法:
        detector = ColorTargetDetector(
            hsv_lower=(140, 80, 150),
            hsv_upper=(170, 255, 255),
            min_area=500,
        )
        results = detector.detect(frame)
        if results:
            r = results[0]
            print(f"目标中心: ({r.center_x}, {r.center_y}), 面积: {r.area}")
    """

    def __init__(
        self,
        hsv_lower: Tuple[int, int, int] = (0, 0, 0),
        hsv_upper: Tuple[int, int, int] = (179, 255, 255),
        min_area: int = 500,
        max_area: int = 0,
        open_kernel: int = 5,
        close_kernel: int = 15,
        blur_size: int = 5,
        sort_by: ContourSort = ContourSort.AREA_DESC,
        max_targets: int = 1,
        min_aspect_ratio: float = 0.0,
        max_aspect_ratio: float = 0.0,
        roi: Optional[Tuple[int, int, int, int]] = None,
        fallback_hsv_ranges: Optional[List] = None,
    ):
        self.params = DetectionParams(
            hsv_lower=hsv_lower,
            hsv_upper=hsv_upper,
            min_area=min_area,
            max_area=max_area,
            open_kernel=open_kernel,
            close_kernel=close_kernel,
            blur_size=blur_size,
            sort_by=sort_by,
            max_targets=max_targets,
            min_aspect_ratio=min_aspect_ratio,
            max_aspect_ratio=max_aspect_ratio,
            roi=roi,
            fallback_hsv_ranges=fallback_hsv_ranges or [],
        )

    def update_params(self, **kwargs):
        """运行时更新参数，支持热调整"""
        for key, val in kwargs.items():
            if hasattr(self.params, key):
                setattr(self.params, key, val)
            else:
                raise ValueError(f"未知参数: {key}")

    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        """
        在 BGR 图像帧中检测颜色目标。

        参数:
            frame : np.ndarray
                BGR 格式图像 (H, W, 3)，uint8。

        返回:
            List[DetectionResult]
                按 sort_by 排序的目标列表，最多 max_targets 个。
                空列表 = 未检测到。
        """
        all_ranges = [
            (self.params.hsv_lower, self.params.hsv_upper)
        ] + self.params.fallback_hsv_ranges

        for hsv_lower, hsv_upper in all_ranges:
            results = self._detect_with_range(frame, hsv_lower, hsv_upper)
            if results:
                return results

        return [DetectionResult(found=False, hsv_range_used=all_ranges[0])]

    def _detect_with_range(
        self,
        frame: np.ndarray,
        hsv_lower: Tuple[int, int, int],
        hsv_upper: Tuple[int, int, int],
    ) -> List[DetectionResult]:
        """用指定 HSV 范围执行单次检测流程"""

        # 1. ROI 裁剪
        search_area = frame
        roi_offset = (0, 0)
        if self.params.roi:
            rx, ry, rw, rh = self.params.roi
            search_area = frame[ry:ry + rh, rx:rx + rw]
            roi_offset = (rx, ry)

        if search_area.size == 0:
            return []

        # 2. BGR → HSV
        hsv = cv2.cvtColor(search_area, cv2.COLOR_BGR2HSV)

        # 3. 颜色掩码
        mask = cv2.inRange(hsv, np.array(hsv_lower), np.array(hsv_upper))

        # 4. 形态学操作
        if self.params.open_kernel > 0:
            k = np.ones((self.params.open_kernel, self.params.open_kernel), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)

        if self.params.close_kernel > 0:
            k = np.ones((self.params.close_kernel, self.params.close_kernel), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

        # 5. 高斯模糊
        if self.params.blur_size > 0:
            sz = self.params.blur_size | 1  # 确保奇数
            mask = cv2.GaussianBlur(mask, (sz, sz), 0)

        # 6. 轮廓提取
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return []

        # 7. 过滤 + 计算属性
        candidates = []
        total_area = search_area.shape[0] * search_area.shape[1]

        for c in contours:
            area = cv2.contourArea(c)
            if area < self.params.min_area:
                continue
            if self.params.max_area > 0 and area > self.params.max_area:
                continue

            x, y, w, h = cv2.boundingRect(c)
            ar = w / h if h > 0 else 0

            if self.params.min_aspect_ratio > 0 and ar < self.params.min_aspect_ratio:
                continue
            if self.params.max_aspect_ratio > 0 and ar > self.params.max_aspect_ratio:
                continue

            # 还原到全图坐标（补偿 ROI 偏移）
            ox, oy = roi_offset
            cx = x + w // 2 + ox
            cy = y + h // 2 + oy

            confidence = min(1.0, area / total_area * 10)  # 归一化到 0-1

            candidates.append(DetectionResult(
                found=True,
                center_x=cx,
                center_y=cy,
                bbox_x=x + ox,
                bbox_y=y + oy,
                bbox_w=w,
                bbox_h=h,
                area=area,
                aspect_ratio=round(ar, 3),
                confidence=round(confidence, 4),
                contour=c,
                hsv_range_used=(hsv_lower, hsv_upper),
            ))

        if not candidates:
            return []

        # 8. 排序
        sort_map = {
            ContourSort.AREA_DESC: lambda r: -r.area,
            ContourSort.AREA_ASC: lambda r: r.area,
            ContourSort.Y_POSITION: lambda r: r.center_y,
            ContourSort.X_POSITION: lambda r: r.center_x,
        }
        candidates.sort(key=sort_map[self.params.sort_by])

        # 9. 截断
        if self.params.max_targets > 0:
            candidates = candidates[:self.params.max_targets]

        return candidates

    def draw_results(
        self,
        frame: np.ndarray,
        results: List[DetectionResult],
        draw_center: bool = True,
        draw_bbox: bool = True,
        draw_label: bool = True,
        color: Tuple[int, int, int] = (0, 255, 0),
    ) -> np.ndarray:
        """在帧上绘制检测结果，返回标注后的图像副本"""
        annotated = frame.copy()
        for i, r in enumerate(results):
            if not r.found:
                continue
            if draw_bbox:
                cv2.rectangle(annotated,
                              (r.bbox_x, r.bbox_y),
                              (r.bbox_x + r.bbox_w, r.bbox_y + r.bbox_h),
                              color, 2)
            if draw_center:
                cv2.circle(annotated, (r.center_x, r.center_y), 6, (0, 0, 255), -1)
            if draw_label:
                text = f"#{i} A={r.area:.0f} ({r.center_x},{r.center_y})"
                cv2.putText(annotated, text,
                            (r.bbox_x, r.bbox_y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return annotated
