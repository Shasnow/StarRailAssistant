import time
from abc import ABC, abstractmethod
from typing import Any, Callable

# noinspection PyPackageRequirements
# (pyperclip is in pyautogui requirements)
import pyperclip
from PIL.Image import Image
from loguru import logger

from SRACore.operator.model import Region, Box


class IOperator(ABC):
    @property
    @abstractmethod
    def is_window_active(self) -> bool:
        ...

    @abstractmethod
    def get_win_region(self, active_window: bool | None = None, raise_exception: bool = True) -> Region | None:
        ...

    @abstractmethod
    def screenshot_in_region(self, region: Region | None = None) -> Image:
        ...

    @abstractmethod
    def screenshot_in_tuple(self, from_x: float, from_y: float, to_x: float, to_y: float) -> Image:
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
            return self.screenshot_in_tuple(from_x, from_y, to_x, to_y)
        else:
            return self.screenshot_in_region(region)

    @abstractmethod
    def locate_in_region(self, img_path: str,
                         region: Region | None = None,
                         confidence: float | None = None,
                         trace: bool = True,
                         **_) -> Box | None:
        ...

    @abstractmethod
    def locate_in_tuple(self,
                        img_path: str,
                        from_x: float,
                        from_y: float,
                        to_x: float,
                        to_y: float,
                        confidence: float | None = None,
                        trace: bool = True,
                        **_) -> Box | None:
        ...

    @abstractmethod
    def locate_any_in_region(self,
                             img_paths: list[str],
                             region: Region | None = None,
                             confidence: float | None = None,
                             trace: bool = True) -> tuple[int, Box | None]:
        ...

    @abstractmethod
    def locate_any_in_tuple(self,
                            img_paths: list[str],
                            from_x: float,
                            from_y: float,
                            to_x: float,
                            to_y: float,
                            confidence: float | None = None,
                            trace: bool = False) -> tuple[int, Box | None]:
        ...

    def locate_any(self,
                   img_paths: list[str],
                   region: Region | None = None,
                   *,
                   from_x: float | None = None,
                   from_y: float | None = None,
                   to_x: float | None = None,
                   to_y: float | None = None,
                   confidence: float | None = None,
                   trace: bool = True) -> tuple[int, Box | None]:
        """在窗口内查找任意一张图片位置
        Args:
            img_paths (list[str]): 模板图片路径列表
            region (Region | None, optional): 要查找的区域对象，包含left, top, width, height属性。
                如果为None，则默认查找当前活动窗口的区域。默认为None。
            from_x (float, optional): 起始点X坐标比例 (0-1)，相对于窗口左上角
            from_y (float, optional): 起始点Y坐标比例 (0-1)，相对于窗口左上角
            to_x (float, optional): 结束点X坐标比例 (0-1)，相对于窗口左上角
            to_y (float, optional): 结束点Y坐标比例 (0-1)，相对于窗口左上角
            confidence (float | None, optional): 匹配度, 0-1之间的浮点数, 默认为self.confidence
            trace (bool, optional): 是否打印调试信息。默认为True。
        Returns:
            tuple[int, Box | None]: 找到的图片索引和位置，如果未找到则返回-1和None
        Raises:
            ValueError: 如果坐标比例参数不完整或不在0-1范围内
        """
        if all(v is not None for v in [from_x, from_y, to_x, to_y]):
            return self.locate_any_in_tuple(img_paths, from_x, from_y, to_x, to_y, confidence, trace)
        else:
            return self.locate_any_in_region(img_paths, region, confidence, trace)

    def locate(self,
               template: str,
               region: Region | None = None,
               *,
               from_x: float | None = None,
               from_y: float | None = None,
               to_x: float | None = None,
               to_y: float | None = None,
               confidence: float | None = None,
               trace: bool = True) -> Box | None:
        """在窗口内查找图片位置

        Args:
            template (str): 模板图片路径
            region (Region | None, optional): 要查找的区域对象，包含left, top, width, height属性。
                如果为None，则默认查找当前活动窗口的区域。默认为None。
            from_x (float, optional): 起始点X坐标比例 (0-1), 相对于窗口左上角
            from_y (float, optional): 起始点Y坐标比例 (0-1), 相对于窗口左上角
            to_x (float, optional): 结束点X坐标比例 (0-1), 相对于窗口左上角
            to_y (float, optional): 结束点Y坐标比例 (0-1), 相对于窗口左上角
            confidence (float | None, optional): 匹配置信度阈值 (0-1), 如果为None则使用默认值。默认为None。
            trace (bool, optional): 是否打印调试信息。默认为True。
        Returns:
            Box | None: 找到的图片位置，如果未找到则返回None
        Raises:
            ValueError: 如果坐标比例参数不完整或不在0-1范围内
        """
        if all(v is not None for v in [from_x, from_y, to_x, to_y]):
            return self.locate_in_tuple(template, from_x, from_y, to_x, to_y, confidence, trace)
        else:
            return self.locate_in_region(template, region, confidence, trace)

    @abstractmethod
    def ocr_in_region(
            self,
            region: Region = None,
            trace: bool = True) -> list[Any] | None:
        ...

    @abstractmethod
    def ocr_in_tuple(
            self,
            from_x: float,
            from_y: float,
            to_x: float,
            to_y: float,
            trace: bool = True) -> list[Any] | None:
        ...

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
                return Box(left, top, width, height, source=text)
        if trace:
            logger.debug(f"OCR Result not match text: {text}")
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
                    return index, Box(left, top, width, height, source=text)
        logger.debug(f"OCR Result not match any text: {texts}")
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
        logger.debug(f"Timeout: '{text}' -> NotFound in {timeout} seconds")
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
        logger.debug(f"Timeout: '{texts}' -> NotFound in {timeout} seconds")
        return -1, None

    @abstractmethod
    def click_point(self, x: int | float, y: int | float, x_offset: int | float = 0, y_offset: int | float = 0,
                    after_sleep: float = 0, tag: str = "") -> bool:
        ...

    def click_box(self, box: Box, x_offset: int | float = 0, y_offset: int | float = 0, after_sleep: float = 0) -> bool:
        """点击图片位置"""
        if box is None:
            logger.trace("Could not click a Empty Box")
            return False
        x, y = box.center
        logger.debug(
            f"Click box center:({x}, {y}), source: {box.source}, offset:({x_offset}, {y_offset}), wait {after_sleep}s")
        return self.click_point(int(x), int(y), x_offset, y_offset, after_sleep)

    def click_img(self, img_path: str, x_offset: int | float = 0, y_offset: int | float = 0,
                  after_sleep: float = 0) -> bool:
        """点击图片中心"""
        box = self.locate(img_path)
        if box is None:
            return False
        return self.click_box(box, x_offset, y_offset, after_sleep)

    def wait_img(self, img_path: str, timeout: int = 10, interval: float = 0.5) -> Box | None:
        """
        等待图片出现
        :param img_path: 模板图片路径
        :param timeout: 超时时间，单位秒
        :param interval: 检查间隔时间，单位秒，默认为0.5秒
        :return: bool - 是否找到图片
        """
        start_time = time.time()
        logger.debug(f"Waiting for image: {img_path}")
        while time.time() - start_time < timeout:
            box = self.locate(img_path)
            if box is not None:
                return box
            time.sleep(interval)
        logger.debug(f"Timeout: {img_path} -> NotFound in {timeout} seconds")
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
        logger.debug(f"Timeout: {img_paths} -> NotFound in {timeout} seconds")
        return -1, None

    @abstractmethod
    def press_key(self, key: str, presses: int = 1, interval: float = 0, wait: float = 0, trace: bool = True) -> bool:
        ...

    @abstractmethod
    def hold_key(self, key: str, duration: float = 0) -> bool:
        ...

    @staticmethod
    def sleep(seconds) -> None:
        """
        Sleep for the specified number of seconds.
        :param seconds: The number of seconds to sleep.
        :return: None
        """
        return time.sleep(seconds)

    @staticmethod
    def copy(text: str) -> None:
        """
        Copy the text to clipboard.
        :param text: The text to copy.
        :return: None
        """
        return pyperclip.copy(text)

    @abstractmethod
    def paste(self) -> str:
        """
        Paste the text from clipboard.
        :return: The text from clipboard.
        """
        ...

    @abstractmethod
    def move_rel(self, x_offset: int, y_offset: int) -> bool:
        ...

    @abstractmethod
    def move_to(self, x: int | float | None, y: int | float | None, duration: float = 0.0) -> bool:
        ...

    @abstractmethod
    def mouse_down(self, x: int | float | None, y: int | float | None) -> bool:
        ...

    @abstractmethod
    def mouse_up(self, x: int | float | None = None, y: int | float | None = None) -> bool:
        ...

    @abstractmethod
    def scroll(self, distance: int) -> bool:
        ...

    def drag_to(self, from_x: int | float, from_y: int | float, to_x: int | float, to_y: int | float,
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

    @staticmethod
    def do_while(action: Callable[[], Any], condition: Callable[[], bool], interval: float = 0.1,
                 max_iterations: int = 50) -> bool:
        """
        在满足条件时重复执行操作。

        Args:
            action (Callable[[], None]): 操作函数。
            condition (Callable[[], bool]): 条件函数，返回布尔值。
            interval (float): 每次检查条件前的等待时间，单位为秒。
            max_iterations (int): 最大迭代次数，防止无限循环。
        Returns:
            bool: 因不再满足条件而退出返回 True，达到最大迭代次数返回 False。
        """
        iterations = 0
        while condition() and iterations < max_iterations:
            action()
            time.sleep(interval)
            iterations += 1
        return iterations != max_iterations