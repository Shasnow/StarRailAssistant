import dataclasses
import time
from pathlib import Path
from typing import Any, overload

import cv2
import numpy as np
import pyautogui
import pygetwindow

# noinspection PyPackageRequirements
# (pyperclip is in pyautogui requirements)
import pyperclip
import pyscreeze
from PIL.Image import Image
from pyscreeze import Box

from rapidocr_onnxruntime import RapidOCR
from SRACore.util.config import load_settings
from SRACore.util.logger import logger
from SRACore.util.i18n import t


@dataclasses.dataclass
class Region:
    """表示屏幕上的一个矩形区域

    例如，Region(0,0,0,0) 表示屏幕左上角的一个点
    """
    left: int
    top: int
    width: int
    height: int

    @property
    def tuple(self):
        """将Region转换为元组"""
        return self.left, self.top, self.width, self.height


@dataclasses.dataclass
class Box:
    """表示窗口内的一个矩形区域

    例如，Box(0,0,0,0) 表示窗口左上角的一个点
    """
    left: int
    top: int
    width: int
    height: int

    @property
    def center(self):
        """获取Box的中心点坐标"""
        center_x = self.left + self.width // 2
        center_y = self.top + self.height // 2
        return center_x, center_y


class Operator:
    ocr_engine = None

    @classmethod
    def get_ocr_instance(cls):
        if cls.ocr_engine is None:
            cls.ocr_engine = RapidOCR(config_path='rapidocr_onnxruntime/config.yaml')
        return cls.ocr_engine

    def __init__(self):
        self.settings = load_settings()
        self.confidence = self.settings.get('ConfidenceThreshold', 0.9)
        self.zoom = self.settings.get('Zoom', 1.25)
        self.window_title = "崩坏：星穹铁道"
        self.top = 0
        self.left = 0
        self.width = 0
        self.height = 0
        self.active_window: bool = True

    @property
    def is_window_active(self) -> bool:
        try:
            win = pygetwindow.getWindowsWithTitle(self.window_title)[0]
            return win.isActive
        except IndexError:
            return False
        except pygetwindow.PyGetWindowException:
            return False

    def get_win_region(self, active_window: bool | None = None, raise_exception: bool = True) -> Region | None:
        """
        获取崩坏：星穹铁道窗口区域
        :return: Region - 窗口区域
        :raises Exception: 如果未找到窗口或窗口未激活
        """
        if active_window is None:
            active_window = self.active_window
        try:
            win = pygetwindow.getWindowsWithTitle(self.window_title)[0]
            if not win.isActive and active_window:
                win.activate()
            return self._major_win_region(win.left, win.top, win.width, win.height)
        except IndexError:
            if raise_exception:
                raise Exception("未找到崩坏：星穹铁道窗口")
            return None
        except pygetwindow.PyGetWindowException as e:
            if raise_exception:
                raise Exception(f"窗口未激活: {e}") from e
            return None
        except Exception as e:
            if raise_exception:
                raise Exception(f"获取窗口区域失败: {e}") from e
            return None

    def _major_win_region(self, left, top, width, height):
        """获取主要操作区域"""
        self.width = width // 160 * 160
        self.height = height // 90 * 90
        self.top = (top + int(30 * self.zoom)) if top != 0 else top
        self.left = (left + int(8 * self.zoom)) if left != 0 else left
        return Region(self.left, self.top, self.width, self.height)

    def screenshot_region(self, region: Region | None = None):
        """截取指定区域的屏幕截图

        Args:
            region (Region | None, optional): 要截取的区域对象，包含left, top, width, height属性。
                如果为None，则默认截取当前活动窗口的区域。默认为None。

        Returns:
            PIL.Image.Image: 返回截取的屏幕区域图像对象

        Note:
            当region为None时，会自动获取活动窗口区域
        """
        if region is None:
            region = self.get_win_region(active_window=True)
        return pyscreeze.screenshot(region=region.tuple)

    def screenshot_tuple(self, from_x: float, from_y: float, to_x: float, to_y: float):
        """根据相对坐标比例截取窗口内区域

        Args:
            from_x (float): 起始点X坐标比例 (0-1)，相对于窗口左上角
            from_y (float): 起始点Y坐标比例 (0-1)，相对于窗口左上角
            to_x (float): 结束点X坐标比例 (0-1)，相对于窗口左上角
            to_y (float): 结束点Y坐标比例 (0-1)，相对于窗口左上角

        Returns:
            PIL.Image.Image: 返回截取的屏幕区域图像对象

        Note:
            坐标比例是基于当前窗口区域计算的，会自动获取窗口区域并短暂延迟(0.5秒)
        """
        region = self.get_win_region()
        left = int(region.left + region.width * from_x)
        top = int(region.top + region.height * from_y)
        width = int(region.width * (to_x - from_x))
        height = int(region.height * (to_y - from_y))
        return pyscreeze.screenshot(region=(left, top, width, height))

    @overload
    def screenshot(self, region: Region | None = None) -> Image:
        """重载1: 截取指定区域或活动窗口"""
        ...

    @overload
    def screenshot(self, from_x: float, from_y: float, to_x: float, to_y: float) -> Image:
        """重载2: 根据相对坐标比例截取区域"""
        ...

    def screenshot(self, region: Region | None = None,
                   *,
                   from_x: float | None = None,
                   from_y: float | None = None,
                   to_x: float | None = None,
                   to_y: float | None = None) -> Image:
        """截取屏幕截图
        Args:
            region (Region | None, optional): 要截取的区域对象，包含left, top, width, height属性。
                如果为None，则默认截取当前活动窗口的区域。默认为None。
            from_x (float, optional): 起始点X坐标比例 (0-1)，相对于窗口左上角
            from_y (float, optional): 起始点Y坐标比例 (0-1)，相对于窗口左上角
            to_x (float, optional): 结束点X坐标比例 (0-1)，相对于窗口左上角
            to_y (float, optional): 结束点Y坐标比例 (0-1)，相对于窗口左上角
        Returns:
            PIL.Image.Image: 返回截取的屏幕区域图像对象
        Note:
            - 当region为None时，会自动获取活动窗口区域
            - 坐标比例是基于当前窗口区域计算的
            - 当传入完整的比例坐标时，region参数会被忽略
        Raises:
            ValueError: 如果坐标比例参数不完整或不在0-1范围内
        """
        if all(v is not None for v in [from_x, from_y, to_x, to_y]):
            return self.screenshot_tuple(from_x, from_y, to_x, to_y)
        else:
            return self.screenshot_region(region)

    def locate_in_region(self,
                         img_path: str,
                         region: Region | None = None,
                         trace: bool = True,
                         **_) -> Box | None:
        """在屏幕上查找图片位置"""
        try:
            if region is None:
                region = self.get_win_region()
                time.sleep(0.5)
            if not Path(img_path).exists():
                raise FileNotFoundError("无法找到或读取文件 " + img_path)
            img = cv2.imread(img_path)
            box = pyscreeze.locate(img, self.screenshot(region), confidence=self.confidence)
            return Box(box.left, box.top, box.width, box.height)
        except Exception as e:
            if trace:
                logger.trace(f"ImageNotFound: {img_path} -> {e}")
            return None

    def locate_in_tuple(self,
                        img_path: str,
                        from_x: float,
                        from_y: float,
                        to_x: float,
                        to_y: float,
                        trace: bool = True,
                        **_) -> Box | None:
        """
        在窗口内查找图片位置，使用比例坐标
        :param img_path: 模板图片路径
        :param from_x: 区域起始x坐标比例(0-1)
        :param from_y: 区域起始y坐标比例(0-1)
        :param to_x: 区域结束x坐标比例(0-1)
        :param to_y: 区域结束y坐标比例(0-1)
        :param trace: 是否打印调试信息
        :return: Box | None - 找到的图片位置，如果未找到则返回None
        """
        try:
            region = self.get_win_region()
        except Exception as e:
            logger.trace(f"ImageNotFound: {img_path} -> {e}")
            return None
        left = int(region.left + region.width * from_x)
        top = int(region.top + region.height * from_y)
        width = int(region.width * (to_x - from_x))
        height = int(region.height * (to_y - from_y))
        return self.locate_in_region(img_path, Region(left, top, width, height), trace)

    def locate_any_in_region(self,
                             img_paths: list[str],
                             region: Region | None = None,
                             trace: bool = True) -> tuple[int, pyscreeze.Box | None]:
        """在窗口内查找任意一张图片位置"""
        try:
            screenshot = self.screenshot(region=region)
        except Exception as e:
            logger.trace(f"Error taking screenshot: {e}")
            return -1, None
        for img_path in img_paths:
            if not Path(img_path).exists():
                raise FileNotFoundError("无法找到或读取文件 " + img_path)
            img = cv2.imread(img_path)
            try:
                box = pyscreeze.locate(img, screenshot, confidence=self.confidence)
            except pyscreeze.ImageNotFoundException as e:
                if trace:
                    logger.trace(f"ImageNotFound: {img_path} -> {e}")
                continue
            if box is not None:
                return img_paths.index(img_path), Box(box.left, box.top, box.width, box.height)
        return -1, None

    def locate_any_in_tuple(self,
                            img_paths: list[str],
                            from_x: float,
                            from_y: float,
                            to_x: float,
                            to_y: float,
                            trace: bool = False) -> tuple[int, pyscreeze.Box | None]:
        """
        在窗口内查找任意一张图片位置，使用比例坐标
        :param img_paths: 模板图片路径列表
        :param from_x: 区域起始x坐标比例(0-1)
        :param from_y: 区域起始y坐标比例(0-1)
        :param to_x: 区域结束x坐标比例(0-1)
        :param to_y: 区域结束y坐标比例(0-1)
        :param trace: 是否打印调试信息
        :return: tuple[int, Box | None] - 找到的图片索引和位置，如果未找到则返回-1和None
        """
        try:
            region = self.get_win_region()
        except Exception as e:
            logger.trace(f"UnexceptedInterrupt: {img_paths} -> {e}")
            return -1, None
        left = int(region.left + region.width * from_x)
        top = int(region.top + region.height * from_y)
        width = int(region.width * (to_x - from_x))
        height = int(region.height * (to_y - from_y))
        return self.locate_any_in_region(img_paths, Region(left, top, width, height), trace)

    @overload
    def locate_any(self, img_paths: list[str], region: Region | None = None, trace: bool = True) -> tuple[
        int, pyscreeze.Box | None]:
        ...

    @overload
    def locate_any(self, img_paths: list[str], *, from_x: float, from_y: float, to_x: float, to_y: float,
                   trace: bool = True) -> tuple[int, pyscreeze.Box | None]:
        ...

    def locate_any(self,
                   img_paths: list[str],
                   region: Region | None = None,
                   *,
                   from_x: float | None = None,
                   from_y: float | None = None,
                   to_x: float | None = None,
                   to_y: float | None = None,
                   trace: bool = True) -> tuple[int, pyscreeze.Box | None]:
        """在窗口内查找任意一张图片位置
        Args:
            img_paths (list[str]): 模板图片路径列表
            region (Region | None, optional): 要查找的区域对象，包含left, top, width, height属性。
                如果为None，则默认查找当前活动窗口的区域。默认为None。
            from_x (float, optional): 起始点X坐标比例 (0-1)，相对于窗口左上角
            from_y (float, optional): 起始点Y坐标比例 (0-1)，相对于窗口左上角
            to_x (float, optional): 结束点X坐标比例 (0-1)，相对于窗口左上角
            to_y (float, optional): 结束点Y坐标比例 (0-1)，相对于窗口左上角
            trace (bool, optional): 是否打印调试信息。默认为True。
        Returns:
            tuple[int, Box | None]: 找到的图片索引和位置，如果未找到则返回-1和None
        Raises:
            ValueError: 如果坐标比例参数不完整或不在0-1范围内
        """
        if all(v is not None for v in [from_x, from_y, to_x, to_y]):
            return self.locate_any_in_tuple(img_paths, from_x, from_y, to_x, to_y, trace)
        else:
            return self.locate_any_in_region(img_paths, region, trace)

    @overload
    def locate(self, template: str, region: Region | None = None, trace: bool = True) -> Box | None:
        ...

    @overload
    def locate(self, template: str, *, from_x: float, from_y: float, to_x: float, to_y: float,
               trace: bool = True) -> Box | None:
        ...

    def locate(self,
               template: str,
               region: Region | None = None,
               *,
               from_x: float | None = None,
               from_y: float | None = None,
               to_x: float | None = None,
               to_y: float | None = None,
               trace: bool = True) -> Box | None:
        """在窗口内查找图片位置

        Args:
            template (str): 模板图片路径
            region (Region | None, optional): 要查找的区域对象，包含left, top, width, height属性。
                如果为None，则默认查找当前活动窗口的区域。默认为None。
            from_x (float, optional): 起始点X坐标比例 (0-1)，相对于窗口左上角
            from_y (float, optional): 起始点Y坐标比例 (0-1)，相对于窗口左上角
            to_x (float, optional): 结束点X坐标比例 (0-1)，相对于窗口左上角
            to_y (float, optional): 结束点Y坐标比例 (0-1)，相对于窗口左上角
            trace (bool, optional): 是否打印调试信息。默认为True。
        Returns:
            Box | None: 找到的图片位置，如果未找到则返回None
        Raises:
            ValueError: 如果坐标比例参数不完整或不在0-1范围内
        """
        if all(v is not None for v in [from_x, from_y, to_x, to_y]):
            return self.locate_in_tuple(template, from_x, from_y, to_x, to_y, trace)
        else:
            return self.locate_in_region(template, region, trace)

    def ocr_in_region(
            self,
            region: Region = None,
            trace: bool = True) -> list[Any] | None:
        """
        在窗口的指定区域内执行 OCR 文字识别，返回原始 OCR 结果（包含文本、坐标、置信度等）。

        Args:
            region (Optional[Region]):
                要识别的区域坐标（`Region(left, top, width, height)`）。
                如果为 `None`，则自动获取整个窗口区域。默认为 `None`。
            trace (bool):
                是否打印调试信息（如 OCR 错误）。默认为 `True`。

        Returns:
            list[Any] | None:
                OCR 引擎返回的原始结果（通常为列表，每项包含文本、坐标、置信度等信息）。
                如果发生错误，返回 `None`。

        Raises:
            Exception:
                如果 OCR 引擎初始化失败或截图失败，且 `trace=False`，异常会被捕获并返回 `None`。
                如果 `trace=True`，错误会被记录到日志（`logger.trace`）。

        Examples:
            >>> # 识别整个窗口
            >>> resul1 = self.ocr_in_region()
            >>>
            >>> # 识别指定区域
            >>> regio = Region(100, 100, 200, 50)
            >>> resul2 = self.ocr_in_region(region)
        """
        try:
            if trace:
                logger.debug(t('operator.ocr_region', region=str(region)))
            if region is None:
                region = self.get_win_region()
                time.sleep(0.5)  # 等待窗口稳定
            if self.ocr_engine is None:
                self.ocr_engine = Operator.get_ocr_instance()
            screenshot = self.screenshot(region)
            screenshot = screenshot.convert("L")
            result, _ = self.ocr_engine(screenshot, use_det=True, use_cls=False, use_rec=True)  # NOQA
            if trace:
                logger.debug(t('operator.ocr_result', result=str(result)))
            return result
        except Exception as e:
            if trace:
                logger.trace(f"OCR Error: {e}")
            return None

    def ocr_in_tuple(
            self,
            from_x: float,
            from_y: float,
            to_x: float,
            to_y: float,
            trace: bool = True) -> list[Any] | None:
        """
        在窗口内通过比例坐标指定区域，并执行 OCR 文字识别。

        Args:
            from_x (float): 区域起始 X 坐标比例（0-1），相对于窗口左上角。
            from_y (float): 区域起始 Y 坐标比例（0-1），相对于窗口左上角。
            to_x (float): 区域结束 X 坐标比例（0-1），相对于窗口左上角。
            to_y (float): 区域结束 Y 坐标比例（0-1），相对于窗口左上角。
            trace (bool): 是否打印调试信息。默认为 `True`。

        Returns:
          list[Any] | None:
                OCR 引擎返回的原始结果。如果发生错误，返回 `None`。

        Raises:
            ValueError: 如果坐标比例不在 [0, 1] 范围内。
            Exception: 如果窗口区域获取失败或 OCR 过程出错（根据 `trace` 参数决定是否记录日志）。

        Examples:
            >>> # 识别窗口右半部分
            >>> result = self.ocr_in_tuple(0.5, 0.0, 1.0, 1.0)
        """
        try:
            region = self.get_win_region()
        except Exception as e:
            if trace:
                logger.trace(f"OCR Error: {e}")
            return None

        # 计算绝对坐标
        left = int(region.left + region.width * from_x)
        top = int(region.top + region.height * from_y)
        width = int(region.width * (to_x - from_x))
        height = int(region.height * (to_y - from_y))

        # 校验坐标有效性
        if width <= 0 or height <= 0:
            raise ValueError("Invalid region: width or height must be positive")

        return self.ocr_in_region(Region(left, top, width, height), trace)

    def ocr(self,
            region: Region = None,
            *,
            from_x: float | None = None,
            from_y: float | None = None,
            to_x: float | None = None,
            to_y: float | None = None,
            trace: bool = True) -> list[Any] | None:
        """执行 OCR 文字识别

        Args:
            region (Region | None, optional): 要识别的区域对象，包含left, top, width, height属性。
                如果为None，则默认识别当前活动窗口的区域。默认为None。如果传入完整的比例坐标时，region参数会被忽略
            from_x (float, optional): 起始点X坐标比例 (0-1)，相对于窗口左上角
            from_y (float, optional): 起始点Y坐标比例 (0-1)，相对于窗口左上角
            to_x (float, optional): 结束点X坐标比例 (0-1
            to_y (float, optional): 结束点Y坐标比例 (0-1)，相对于窗口左上角
            trace (bool, optional): 是否打印调试信息。默认为True。
        Returns:
            list[Any] | None: OCR 引擎返回的原始结果。如果发生错误，返回None。
        Raises:
            ValueError: 如果坐标比例参数不完整或不在0-1范围内
        """
        if all(v is not None for v in [from_x, from_y, to_x, to_y]):
            return self.ocr_in_tuple(from_x, from_y, to_x, to_y, trace)
        else:
            return self.ocr_in_region(region, trace)

    def ocr_match(self,
                  text: str,
                  confidence=0.9,
                  region: Region = None,
                  *,
                  from_x: float | None = None,
                  from_y: float | None = None,
                  to_x: float | None = None,
                  to_y: float | None = None,
                  trace: bool = True) -> Box | None:
        """
        OCR识别并匹配文本
        """
        results = self.ocr(region, from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y, trace=trace)
        if results is None:
            return None
        for result in results:
            if result[2] >= confidence and text in result[1]:
                left, top = result[0][0]
                width = result[0][2][0] - left
                height = result[0][2][1] - top
                return Box(left, top, width, height)
        if trace:
            logger.debug(t('operator.ocr_not_match', text=text))
        return None

    def ocr_match_any(self,
                      texts: list[str],
                      confidence=0.9,
                      region: Region = None,
                      *,
                      from_x: float | None = None,
                      from_y: float | None = None,
                      to_x: float | None = None,
                      to_y: float | None = None,
                      trace: bool = True) -> tuple[int, Box | None]:
        """
        OCR识别并匹配任意文本，返回第一个找到的文本索引和位置
        :returns tuple[int, Box | None] - 找到的文本索引和位置，如果未找到则返回-1和None
        """
        results = self.ocr(region, from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y, trace=trace)
        if results is None:
            return -1, None
        for index, text in enumerate(texts):
            for result in results:
                if result[2] >= confidence and text in result[1]:
                    left, top = result[0][0]
                    width = result[0][2][0] - left
                    height = result[0][2][1] - top
                    return index, Box(left, top, width, height)
        logger.debug(t('operator.ocr_not_match_any', texts=str(texts)))
        return -1, None

    def wait_ocr(self, text: str, timeout: float = 10, interval: float = 0.2, confidence=0.9, *args,
                 **kwargs) -> Box | None:
        """
        等待OCR识别到指定文本
        :param text: 要识别的文本
        :param timeout: 超时时间，单位秒
        :param interval: 检查间隔时间，单位秒，默认为0.2秒
        :param confidence: 识别置信度，默认为0.9
        :return: Box | None - 找到的文本位置，如果未找到则返回None
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            box = self.ocr_match(text, confidence, *args, **kwargs)
            if box is not None:
                return box
            time.sleep(interval)
        logger.debug(t('operator.timeout_not_found', text=text, timeout=timeout))
        return None

    def wait_ocr_any(self, texts: list[str], timeout: float = 10, interval: float = 0.2, confidence=0.9, *args,
                     **kwargs) -> tuple[int, Box | None]:
        """
        等待OCR识别到任意指定文本
        :param texts: 要识别的文本列表
        :param timeout: 超时时间，单位秒
        :param interval: 检查间隔时间，单位秒，默认为0.2秒
        :param confidence: 识别置信度，默认为0.9
        :return: tuple[int, Box | None] - 找到的文本索引和位置，如果未找到则返回-1和None
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            index, box = self.ocr_match_any(texts, confidence, *args, **kwargs)
            if index != -1:
                return index, box
            time.sleep(interval)
        logger.debug(t('operator.timeout_texts_not_found', texts=texts, timeout=timeout))
        return -1, None

    def click_point(self, x: int | float, y: int | float, x_offset: int | float = 0, y_offset: int | float = 0,
                    after_sleep: float = 0) -> bool:
        """
        点击指定位置
        如果x和y是整数，则直接点击坐标(x, y)
        如果x和y是浮点数，则将其转换为相对于窗口区域的坐标
        :param x: int或float类型，表示点击位置的x坐标
        :param y: int或float类型，表示点击位置的y坐标
        :param x_offset: x偏移量(px)或百分比(float)
        :param y_offset: y偏移量(px)或百分比(float)
        :param after_sleep: 点击后等待时间，单位秒
        :return: None
        """
        logger.debug(t('operator.click_position', x=x, y=y, x_offset=x_offset, y_offset=y_offset, after_sleep=after_sleep))
        if isinstance(x_offset, float) and isinstance(y_offset, float):
            x_offset = int(self.width * x_offset)
            y_offset = int(self.height * y_offset)
        if isinstance(x, int) and isinstance(y, int):
            pyautogui.click(x + self.left + x_offset, y + self.top + y_offset)
            self.sleep(after_sleep)
            return True
        elif isinstance(x, float) and isinstance(y, float):
            x = int(self.left + self.width * x + x_offset)
            y = int(self.top + self.height * y + y_offset)
            pyautogui.click(x, y)
            self.sleep(after_sleep)
            return True
        else:
            # NOQA
            raise ValueError(
                f"Invalid arguments: expected 'int, int' or 'float, float', got '{type(x).__name__}, {type(y).__name__}'")

    def click_box(self, box: Box, x_offset: int | float = 0, y_offset: int | float = 0, after_sleep: float = 0) -> bool:
        """点击图片位置"""
        if box is None:
            logger.trace("Could not click a Empty Box")
            return False
        x, y = box.center
        return self.click_point(int(x), int(y), x_offset, y_offset, after_sleep)

    def click_img(self, img_path: str, x_offset: int | float = 0, y_offset: int | float = 0,
                  after_sleep: float = 0) -> bool:
        """点击图片中心"""
        box = self.locate(img_path)
        if box is None:
            return False
        return self.click_box(box, x_offset, y_offset, after_sleep)

    def wait_img(self,
                 img_path: str,
                 timeout: int = 10,
                 interval: float = 0.5,
                 *,
                 debug: bool = False,
                 debug_dir: str | None = None) -> Box | None:
        """等待图片出现并可选输出调试信息

        Args:
            img_path: 模板图片路径
            timeout: 超时时间(秒)
            interval: 重试间隔(秒)
            debug: 是否输出调试匹配结果（每次循环）
            debug_dir: 调试文件输出目录（不存在则自动创建），未指定时默认使用 "debug_image_match"

        调试输出内容：
            - 每次循环保存当前窗口截图（仅在标注时）
            - 计算单尺度 matchTemplate 得分与位置（灰度 + TM_CCOEFF_NORMED）
            - 若得分达到阈值(self.confidence)则返回 Box
            - 保存标注图片：<debug_dir>/<basename>__attempt<idx>__score<val>.png

        注意：
            - 仍调用原 locate 逻辑，若 locate 返回 Box 会直接返回
            - 调试匹配仅用于记录，不会降低性能要求
        """
        start_time = time.time()
        logger.debug(t('operator.waiting_image', path=img_path))
        tmpl = None
        tmpl_gray = None
        attempt = 0
        if debug:
            if debug_dir is None:
                debug_dir = "debug_image_match"
            try:
                Path(debug_dir).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.trace(f"Create debug dir failed: {e}")
                debug = False
        else:
            debug_dir = None
        debug_path = Path(debug_dir) if (debug and debug_dir is not None) else None

        # 预读模板
        if debug:
            try:
                tmpl = cv2.imread(img_path)
                if tmpl is not None:
                    tmpl_gray = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
            except Exception as e:
                logger.trace(f"Load template failed (debug disabled): {e}")
                debug = False

        while time.time() - start_time < timeout:
            attempt += 1
            # 原始 locate 逻辑
            box = self.locate(img_path)
            if box is not None:
                if debug:
                    logger.debug(t('operator.wait_img_success', attempt=attempt))
                return box

            if debug and tmpl_gray is not None:
                try:
                    region = self.get_win_region(active_window=True)
                    screenshot_pil = self.screenshot(region)
                    scr_rgb = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2BGR)
                    scr_gray = cv2.cvtColor(scr_rgb, cv2.COLOR_BGR2GRAY)
                    # 尺寸检查
                    if tmpl_gray.shape[0] <= scr_gray.shape[0] and tmpl_gray.shape[1] <= scr_gray.shape[1]:
                        res = cv2.matchTemplate(scr_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
                        _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(res)
                        h, w = tmpl_gray.shape[:2]
                        logger.debug(t('operator.wait_img_attempt', attempt=attempt, score=max_val, loc=max_loc, conf=self.confidence))
                        # 保存标注图片
                        try:
                            annotated = scr_rgb.copy()
                            cv2.rectangle(annotated, max_loc, (max_loc[0] + w, max_loc[1] + h), (0, 0, 255), 2)
                            cv2.putText(annotated,
                                        f"s={max_val:.3f}",
                                        (max_loc[0], max(0, max_loc[1] - 10)),
                                        cv2.FONT_HERSHEY_SIMPLEX,
                                        0.5,
                                        (0, 0, 255),
                                        1)
                            out_name = f"{Path(img_path).stem}__attempt{attempt}__score{max_val:.3f}.png"
                            if debug_path is not None:
                                cv2.imwrite(str(debug_path / out_name), annotated)
                        except Exception as e:
                            logger.trace(f"[wait_img debug] save annotated failed: {e}")
                        # 若得分达到阈值，将该位置作为命中返回
                        if max_val >= self.confidence:
                            return Box(max_loc[0], max_loc[1], w, h)
                    else:
                        logger.debug(t('operator.wait_img_too_large', attempt=attempt))
                except Exception as e:
                    logger.trace(f"[wait_img debug] attempt={attempt} error: {e}")

            time.sleep(interval)
        logger.debug(t('operator.timeout_image', path=img_path, timeout=timeout))
        return None

    def wait_any_img(self, img_paths: list[str], timeout: int = 10, interval: float = 0.2) -> tuple[int, Box | None]:
        """
        等待任意一张图片出现
        :param img_paths: 模板图片路径列表
        :param timeout: 超时时间，单位秒
        :param interval: 检查间隔时间，单位秒，默认为0.2秒
        :return: int - 找到的图片索引，如果未找到则返回-1; Box | None - 找到的图片位置，如果未找到则返回None
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            index, box = self.locate_any(img_paths)
            if index != -1:
                return index, box
            time.sleep(interval)
        logger.debug(t('operator.timeout_images', paths=img_paths, timeout=timeout))
        return -1, None

    @staticmethod
    def press_key(key: str, presses: int = 1, interval: float = 0, wait: float = 0, trace: bool = True) -> bool:
        """按下按键

        Args:
            key: 按键
            presses: 按下次数
            interval: 按键间隔时间(如果填入,程序会间隔interval秒再按下按键)
            wait: 首次按下按键前的等待时间
            trace: 是否打印调试信息
        Returns:
            按键成功返回True，否则返回False
        """
        try:
            time.sleep(wait)
            if trace:
                logger.debug(t('operator.press_key', key=key))
            pyautogui.press(key, presses=presses, interval=interval)
            return True
        except Exception as e:
            if trace:
                logger.debug(t('operator.press_key_failed', error=e))
            return False

    @staticmethod
    def hold_key(key: str, duration: float = 0) -> bool:
        """
        按下按键一段时间

        Args:
            key: 按键
            duration: 按下时间

        Returns:
            按键成功返回True，否则返回False
        """
        try:
            logger.debug(t('operator.hold_key', key=key))
            pyautogui.keyDown(key)
            time.sleep(duration)
            pyautogui.keyUp(key)
            return True
        except Exception as e:
            logger.debug(t('operator.hold_key_failed', error=e))
            return False

    @staticmethod
    def sleep(seconds):
        return time.sleep(seconds)

    @staticmethod
    def copy(text: str):
        """
        Copy the text to clipboard.
        :param text: The text to copy.
        :return: None
        """
        return pyperclip.copy(text)

    @staticmethod
    def paste():
        """
        Paste the latest content in clipboard.
        :return: None
        """
        pyautogui.keyDown("ctrl")
        pyautogui.keyDown("v")
        pyautogui.keyUp("v")
        pyautogui.keyUp("ctrl")

    @staticmethod
    def move_rel(x_offset: int, y_offset: int) -> bool:
        """
        相对当前位置移动光标。

        Args:
            x_offset (int): X 轴偏移量。
            y_offset (int): Y 轴偏移量。

        Returns:
            bool: 如果移动成功则返回 True，否则返回 False。
        """
        try:
            pyautogui.moveRel(x_offset, y_offset)
            return True
        except Exception as e:
            logger.debug(t('operator.move_cursor_error', error=e))
            return False

    def move_to(self, x: int | float, y: int | float, duration: float = 0.0) -> bool:
        """
        将鼠标移动到指定位置。

        Args:
            x (int | float): X 坐标。
            y (int | float): Y 坐标。
            duration (float): 移动持续时间，单位为秒。

        Returns:
            bool: 如果移动成功则返回 True，否则返回 False。
        """
        try:
            logger.debug(t('operator.move_to', x=x, y=y, duration=duration))
            if isinstance(x, int) and isinstance(y, int):
                pyautogui.moveTo(x + self.left, y + self.top, duration=duration)
            elif isinstance(x, float) and isinstance(y, float):
                x = int(self.left + self.width * x)
                y = int(self.top + self.height * y)
                pyautogui.moveTo(x, y, duration=duration)
            else:
                # NOQA
                raise ValueError(
                    f"Invalid arguments: expected 'int, int' or 'float, float', got '{type(x).__name__}, {type(y).__name__}'")
            return True
        except Exception as e:
            logger.debug(t('operator.move_to_error', error=e))
            return False

    def mouse_down(self, x: int | float, y: int | float) -> bool:
        """
        按下鼠标按钮。

        Args:
            x (int | float): X 坐标。
            y (int | float): Y 坐标。
        Returns:
            bool: 如果按下成功则返回 True，否则返回 False。
        """
        try:
            logger.debug(t('operator.mouse_down', x=x, y=y))
            if isinstance(x, int) and isinstance(y, int):
                pyautogui.mouseDown(x + self.left, y + self.top)
            elif isinstance(x, float) and isinstance(y, float):
                x = int(self.left + self.width * x)
                y = int(self.top + self.height * y)
                pyautogui.mouseDown(x, y)
            else:
                # NOQA
                raise ValueError(
                    f"Invalid arguments: expected 'int, int' or 'float, float', got '{type(x).__name__}, {type(y).__name__}'")
            return True
        except Exception as e:
            logger.debug(t('operator.mouse_down_error', error=e))
            return False

    @staticmethod
    def mouse_up() -> bool:
        """
        释放鼠标按钮。
        Returns:
            bool: 如果释放成功则返回 True，否则返回 False。
        """
        try:
            logger.debug(t('operator.mouse_up'))
            pyautogui.mouseUp()
            return True
        except Exception as e:
            logger.debug(t('operator.mouse_up_error', error=e))
            return False

    @staticmethod
    def scroll(distance: int) -> bool:
        """
        滚动鼠标滚轮。

        Args:
            distance (int): 滚动距离。

        Returns:
            bool: 如果滚动成功则返回 True，否则返回 False。
        """
        try:
            pyautogui.scroll(distance)
            return True
        except Exception as e:
            logger.debug(t('operator.scroll_error', error=e))
            return False

    def drag(self, from_x: int | float, from_y: int | float, to_x: int | float, to_y: int | float,
             duration: float = 0.5) -> bool:
        """
        拖动鼠标到指定位置。

        Args:
            from_x (int | float): 目标 X 坐标。
            from_y (int | float): 目标 Y 坐标。
            to_x (int | float): 目标 X 坐标。
            to_y (int | float): 目标 Y 坐标。
            duration (float): 拖动持续时间，单位为秒。
        Returns:
            bool: 如果拖动成功则返回 True，否则返回 False。
        """
        self.mouse_down(from_x, from_y)
        self.move_to(to_x, to_y, duration)
        self.mouse_up()
        return True


class Executable(Operator):
    pass
