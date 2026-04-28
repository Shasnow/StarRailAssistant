import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable

# noinspection PyPackageRequirements
# (pyperclip is in pyautogui requirements)
import pyperclip
import pyscreeze
from PIL.Image import Image
from loguru import logger
from rapidocr_onnxruntime import RapidOCR  # type: ignore

from SRACore.operators.model import Box
from SRACore.util.data_persister import load_app_settings
from SRACore.util.errors import ThreadStoppedError


class IOperator(ABC):
    ocr_engine = None

    def __init__(self, stop_event: threading.Event | None = None):
        self.type = "Local"
        self.settings = load_app_settings()
        self.confidence: float = self.settings.General.templateMatchConfidence
        self.top = 0
        self.left = 0
        self.width = 0
        self.height = 0
        self.is_developer_mode: bool = self.settings.Advanced.isDeveloperModeEnabled
        self.is_save_ocr_image: bool = self.settings.Advanced.isSaveOcrImage if self.is_developer_mode else False
        self.stop_event: threading.Event | None = stop_event

    @classmethod
    def _get_ocr_instance(cls):
        """获取OCR引擎实例"""
        if cls.ocr_engine is None:
            cls.ocr_engine = RapidOCR(config_path='rapidocr_onnxruntime/config.yaml')
        return cls.ocr_engine

    @abstractmethod
    def is_window_active(self) -> bool:
        """检查目标窗口是否为当前活动窗口"""
        ...

    @abstractmethod
    def screenshot(self, *,
                   from_x: float | None = None,
                   from_y: float | None = None,
                   to_x: float | None = None,
                   to_y: float | None = None) -> Image:
        """截取屏幕截图
        Args:
            from_x (float, optional): 起始点X坐标比例 (0-1)，相对于窗口左上角
            from_y (float, optional): 起始点Y坐标比例 (0-1)，相对于窗口左上角
            to_x (float, optional): 结束点X坐标比例 (0-1)，相对于窗口左上角
            to_y (float, optional): 结束点Y坐标比例 (0-1)，相对于窗口左上角
        Returns:
            PIL.Image.Image: 返回截取的屏幕区域图像对象
        Note:
            - 坐标比例是基于当前窗口区域计算的
            - 如果不提供坐标参数，则截取整个窗口
        Raises:
            ValueError: 如果坐标比例参数不完整或不在0-1范围内
            SRAError: 截图出现错误
        """
        ...

    def locate_all(self,
                   template: str,
                   *,
                   from_x: float | None = None,
                   from_y: float | None = None,
                   to_x: float | None = None,
                   to_y: float | None = None,
                   confidence: float | None = None,
                   trace: bool = True) -> list[Box] | None:
        """在窗口内查找所有匹配的图片位置

        Args:
            template (str): 模板图片路径
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
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("图像识别中断", "线程已停止")
        match_confidence = self.confidence if confidence is None else confidence
        try:
            if not Path(template).exists():
                raise FileNotFoundError("无法找到或读取文件 " + template)
            # noinspection PyTypeChecker
            boxes = pyscreeze.locateAll(template, self.screenshot(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y), confidence=match_confidence)
            self.sleep(0.5)
            result = []
            for box in boxes:
                left, top, width, height = box
                if from_x is not None and from_y is not None:
                    left += int(from_x * self.width)
                    top += int(from_y * self.height)
                result.append(Box(left, top, width, height, source=template)) # type: ignore
            return result # type: ignore
        except Exception as e:
            if trace:
                logger.trace(f"ImageNotFound: {template} -> {e}")
            return None

    def locate_any(self,
                   templates: list[str],
                   *,
                   from_x: float | None = None,
                   from_y: float | None = None,
                   to_x: float | None = None,
                   to_y: float | None = None,
                   confidence: float | None = None,
                   trace: bool = True) -> tuple[int, Box | None]:
        """在窗口内查找任意一张图片位置
        
        Args:
            templates (list[str]): 模板图片路径列表
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
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("图像识别中断", "线程已停止")
        match_confidence = self.confidence if confidence is None else confidence
        try:
            screenshot = self.screenshot(from_x=from_x, from_y=from_y,to_x=to_x, to_y=to_y)
            self.sleep(0.5)
        except Exception as e:
            logger.trace(f"Error taking screenshot: {e}")
            return -1, None
        for img_path in templates:
            if not Path(img_path).exists():
                raise FileNotFoundError("无法找到或读取文件 " + img_path)
            try:
                # noinspection PyTypeChecker
                box = pyscreeze.locate(img_path, screenshot, confidence=match_confidence)
            except (pyscreeze.ImageNotFoundException, ValueError) as e:
                if trace:
                    logger.trace(f"ImageNotFound: {img_path} -> {e}")
                continue
            if box is not None:
                left, top, width, height = box
                if from_x is not None and from_y is not None:
                    left += int(from_x * self.width)
                    top += int(from_y * self.height)
                return templates.index(img_path), Box(left, top, width, height, source=img_path)
        return -1, None

    def locate(self,
               template: str,
               *,
               from_x: float | None = None,
               from_y: float | None = None,
               to_x: float | None = None,
               to_y: float | None = None,
               confidence: float | None = None,
               trace: bool = True) -> Box | None:
        """在窗口内查找模板图片位置

        Args:
            template (str): 模板图片路径
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
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("图像识别中断", "线程已停止")
        if confidence is not None:
            match_confidence = confidence
        else:
            match_confidence = self.confidence
        try:
            if not Path(template).exists():
                raise FileNotFoundError("无法找到或读取文件 " + template)
            box = pyscreeze.locate(template,
                                   self.screenshot(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y),
                                   confidence=match_confidence)
            if box is None:
                return None
            left, top, width, height = box
            if from_x is not None and from_y is not None:
                left += int(from_x * self.width)
                top += int(from_y * self.height)
            self.sleep(0.5)
            return Box(left, top, width, height, source=template)
        except Exception as e:
            if trace:
                logger.trace(f"ImageNotFound: {template} -> {e}")
            return None

    def ocr(self,
            *,
            from_x: float | None = None,
            from_y: float | None = None,
            to_x: float | None = None,
            to_y: float | None = None,
            trace: bool = True) -> list[Any] | None:
        """执行 OCR 文字识别

        考虑使用 ocr_match 或 ocr_match_any 方法来处理文本匹配和位置获取，而不是直接使用此方法。
        Args:
            from_x (float, optional): 起始点X坐标比例 (0-1)，相对于窗口左上角
            from_y (float, optional): 起始点Y坐标比例 (0-1)，相对于窗口左上角
            to_x (float, optional): 结束点X坐标比例 (0-1)，相对于窗口左上角
            to_y (float, optional): 结束点Y坐标比例 (0-1)，相对于窗口左上角
            trace (bool, optional): 是否打印调试信息。默认为True。
        Returns:
            list[Any] | None: OCR 引擎返回的原始结果。如果发生错误，返回None。
        Raises:
            ValueError: 如果坐标比例参数不完整或不在0-1范围内
        """
        if self.stop_event is not None and self.stop_event.is_set():
            raise RuntimeError("Operation stopped")
        try:
            if self.ocr_engine is None:
                self.ocr_engine = IOperator._get_ocr_instance()
            screenshot = self.screenshot(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y)
            if screenshot is None:
                raise RuntimeError("Failed to capture screenshot for OCR")
            result, _ = self.ocr_engine(screenshot, use_det=True, use_cls=False, use_rec=True)  # NOQA # type: ignore
            if self.is_save_ocr_image:
                screenshot.save(f"log/ocr/{int(time.time())}.png")
            if trace:
                logger.debug(f"OCR Result: {result}")
            return result
        except Exception as e:
            if trace:
                logger.trace(f"OCR Error: {e}")
            return None

    def ocr_match(self,
                  text: str,
                  confidence: float = 0.9,
                  *,
                  from_x: float | None = None,
                  from_y: float | None = None,
                  to_x: float | None = None,
                  to_y: float | None = None,
                  trace: bool = True) -> Box | None:
        """
        OCR识别并匹配指定文本，返回文本位置

        Args:
            text (str): 要识别的文本
            confidence (float, optional): 识别置信度。默认为0.9。
            from_x (float, optional): 识别区域起始x坐标比例(0-1)。
            from_y (float, optional): 识别区域起始y坐标比例(0-1)。
            to_x (float, optional): 识别区域结束x坐标比例(0-1)。
            to_y (float, optional): 识别区域结束y坐标比例(0-1)。
            trace (bool, optional): 是否打印调试信息。默认为True。
        Returns:
            Box | None: 找到的文本位置，如果未找到则返回None。
        """
        results = self.ocr(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y, trace=trace)
        if results is None:
            return None
        for result in results:
            if result[2] >= confidence and text in result[1]:
                left, top = result[0][0]
                width = result[0][2][0] - left
                height = result[0][2][1] - top
                if from_x is not None and from_y is not None and to_x is not None and to_y is not None:
                    left += int(self.width * from_x)
                    top += int(self.height * from_y)
                return Box(left, top, width, height, source=text)
        if trace:
            logger.debug(f"OCR Result not match text: {text}")
        return None

    def ocr_match_any(self,
                      texts: list[str],
                      confidence: float = 0.9,
                      *,
                      from_x: float | None = None,
                      from_y: float | None = None,
                      to_x: float | None = None,
                      to_y: float | None = None,
                      trace: bool = True) -> tuple[int, Box | None]:
        """
        OCR识别并匹配任意指定文本，返回文本索引和位置

        Args:
            texts (list[str]): 要识别的文本列表
            confidence (float, optional): 识别置信度。默认为0.9。
            from_x (float, optional): 识别区域起始x坐标比例(0-1)。
            from_y (float, optional): 识别区域起始y坐标比例(0-1)。
            to_x (float, optional): 识别区域结束x坐标比例(0-1)。
            to_y (float, optional): 识别区域结束y坐标比例(0-1)。
            trace (bool, optional): 是否打印调试信息。默认为True。
        Returns:
            tuple[int, Box | None]: 找到的文本索引和位置，如果未找到则返回-1和None
        """
        results = self.ocr(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y, trace=trace)
        if results is None:
            return -1, None
        for index, text in enumerate(texts):
            for result in results:
                if result[2] >= confidence and text in result[1]:
                    left, top = result[0][0]
                    width = result[0][2][0] - left
                    height = result[0][2][1] - top
                    if from_x is not None and from_y is not None and to_x is not None and to_y is not None:
                        left += int(self.width * from_x)
                        top += int(self.height * from_y)
                    return index, Box(left, top, width, height, source=text)
        logger.debug(f"OCR Result not match any text: {texts}")
        return -1, None

    def wait_ocr(self, text: str,
                 confidence: float = 0.9,
                 interval: float = 0.2,
                 timeout: float = 10,
                 *args: Any,
                 **kwargs: Any) -> Box | None:
        """
        等待OCR识别到指定文本

        Args:
            text (str): 要识别的文本
            timeout (float, optional): 超时时间，单位秒。默认值为10秒。
            interval (float, optional): 检查间隔时间，单位秒。默认值为0.2秒。
            confidence (float, optional): 识别置信度。默认值为0.9。
            *args: 传递给ocr_match的其他位置参数。
            **kwargs: 传递给ocr_match的其他关键字参数。
        Returns:
            Box | None: 找到的文本位置，如果未找到则返回None。
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            box = self.ocr_match(text, confidence, *args, **kwargs)
            if box is not None:
                return box
            time.sleep(interval)
        logger.debug(f"Timeout: '{text}' -> NotFound in {timeout} seconds")
        return None

    def wait_ocr_any(self,
                     texts: list[str],
                     confidence: float = 0.9,
                     interval: float = 0.2,
                     timeout: float = 10,
                     *args: Any,
                     **kwargs: Any) -> tuple[int, Box | None]:
        """
        等待OCR识别到任意指定文本

        Args:
            texts (list[str]): 要识别的文本列表
            timeout (float, optional): 超时时间，单位秒。默认值为10秒。
            interval (float, optional): 检查间隔时间，单位秒。默认值为0.2秒。
            confidence (float, optional): 识别置信度。默认值为0.9。
            *args: 传递给ocr_match_any的其他位置参数。
            **kwargs: 传递给ocr_match_any的其他关键字参数。
        Returns:
            tuple[int, Box | None]: 找到的文本索引和位置，如果未找到则返回-1和None
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
                    after_sleep: float = 0, tag: str = "", trace: bool = False) -> bool:
        """
        点击指定位置

        如果x和y是整数，则直接点击坐标(x, y)
        如果x和y是浮点数，则将其转换为相对于窗口区域的坐标
        Args:
            x (int | float): 点击位置的x坐标
            y (int | float): 点击位置的y坐标
            x_offset (int | float, optional): x偏移量(px)或百分比(float)。默认值为0。
            y_offset (int | float, optional): y偏移量(px)或百分比(float)。默认值为0。
            after_sleep (float, optional): 点击后等待时间，单位秒。默认值为0。
            tag (str, optional): 日志标记。默认值为空字符串。
            trace (bool): 是否打印日志
        Returns:
            bool: 点击成功返回True，否则返回False
        """
        ...

    def click_box(self, box: Box, x_offset: int | float = 0, y_offset: int | float = 0, after_sleep: float = 0) -> bool:
        """
        点击Box区域中心
        
        计算box中心点坐标并调用click_point方法进行点击
        Args:
            box (Box): Box对象，表示要点击的区域
            x_offset (int | float, optional): x偏移量(px)或百分比(float)。默认值为0。
            y_offset (int | float, optional): y偏移量(px)或百分比(float)。默认值为0。
            after_sleep (float, optional): 点击后等待时间，单位秒。默认值为0。
        Returns:
            bool: 点击成功返回True，否则返回False
        """
        x, y = box.center
        logger.debug(
            f"Click box center:({x}, {y}), source: {box.source}, offset:({x_offset}, {y_offset}), wait {after_sleep}s")
        return self.click_point(x, y, x_offset, y_offset, after_sleep)

    def click_img(self, template: str, x_offset: int | float = 0, y_offset: int | float = 0,
                  after_sleep: float = 0) -> bool:
        """
        查找图片并点击其中心位置
        
        先调用locate方法查找图片位置，如果找到则调用click_box方法点击
        Args:
            template (str): 模板图片路径
            x_offset (int | float, optional): x偏移量(px)或百分比(float)。默认值为0。
            y_offset (int | float, optional): y偏移量(px)或百分比(float)。默认值为0。
            after_sleep (float, optional): 点击后等待时间，单位秒。默认值为0。
        Returns:
            bool: 点击成功返回True，否则返回False
        """
        box = self.locate(template)
        if box is None:
            return False
        return self.click_box(box, x_offset, y_offset, after_sleep)

    def wait_img(self, template: str, timeout: int = 10, interval: float = 0.5) -> Box | None:
        """
        等待模板图片出现
        
        Args:
            template (str): 模板图片路径
            timeout (int, optional): 超时时间，单位秒。默认值为10秒。
            interval (float, optional): 检查间隔时间，单位秒，默认为0.5秒。默认值为0.5秒。
        Returns:
            Box | None: 找到的图片位置，如果未找到则返回None
        """
        start_time = time.time()
        logger.debug(f"Waiting for image: {template}")
        while time.time() - start_time < timeout:
            box = self.locate(template)
            if box is not None:
                return box
            time.sleep(interval)
        logger.debug(f"Timeout: {template} -> NotFound in {timeout} seconds")
        return None

    def wait_any_img(self, templates: list[str], timeout: int = 10, interval: float = 0.5, trace: bool = True) -> tuple[int, Box | None]:
        """
        等待任意一张图片出现
        
        Args:
            templates (list[str]): 模板图片路径列表
            timeout (int, optional): 超时时间，单位秒。默认值为10秒。
            interval (float, optional): 检查间隔时间，单位秒，默认为0.2秒。默认值为0.2秒。
            trace (bool, optional): 是否打印调试信息。默认为True。
        Returns:
            tuple[int, Box | None]: 找到的图片索引(如果未找到则返回-1)和图片位置(如果未找到则返回None)
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            index, box = self.locate_any(templates, trace = trace)
            if index != -1:
                return index, box
            time.sleep(interval)
        logger.debug(f"Timeout: {templates} -> NotFound in {timeout} seconds")
        return -1, None

    @abstractmethod
    def press_key(self, key: str, presses: int = 1, interval: float = 0, wait: float = 0, trace: bool = True) -> bool:
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
        ...

    @abstractmethod
    def hold_key(self, key: str, duration: float = 0) -> bool:
        """
        按下按键一段时间

        Args:
            key: 按键
            duration: 按下时间

        Returns:
            按键成功返回True，否则返回False
        """
        ...

    @staticmethod
    def sleep(seconds: float) -> None:
        """
        Sleep for the specified number of seconds.
        
        Args:
            seconds (float): The number of seconds to sleep.
        Returns:
            None
        """
        time.sleep(seconds)

    @staticmethod
    def copy(text: str) -> None:
        """
        Copy the text to clipboard.
        
        Args:
            text (str): The text to copy.
        Returns:
            None
        """
        pyperclip.copy(text)

    @abstractmethod
    def paste(self) -> None:
        """
        Paste the text from clipboard.
        
        Returns:
            None
        """
        ...

    @abstractmethod
    def move_rel(self, x_offset: int, y_offset: int) -> bool:
        """
        相对当前位置移动光标。

        Args:
            x_offset (int): X 轴偏移量。
            y_offset (int): Y 轴偏移量。

        Returns:
            bool: 如果移动成功则返回 True，否则返回 False。
        """
        ...

    @abstractmethod
    def move_to(self, x: int | float, y: int | float, duration: float = 0.0, trace: bool = True) -> bool:
        """
        将鼠标移动到指定位置。

        Args:
            x (int | float): X 坐标。
            y (int | float): Y 坐标。
            duration (float): 移动持续时间，单位为秒。
            trace (bool): 是否打印调试信息。默认为 True。
        Returns:
            bool: 如果移动成功则返回 True，否则返回 False。
        """
        ...

    @abstractmethod
    def mouse_down(self, x: int | float, y: int | float, trace: bool = True) -> bool:
        """
        按下鼠标按钮。

        Args:
            x (int | float): X 坐标。
            y (int | float): Y 坐标。
            trace (bool): 是否打印调试信息。默认为 True。
        Returns:
            bool: 如果按下成功则返回 True，否则返回 False。
        """
        ...

    @abstractmethod
    def mouse_up(self, x: int | float | None = None, y: int | float | None = None, trace: bool = True) -> bool:
        """
        释放鼠标按钮。
        
        Args:
            x (int | float): X 坐标。
            y (int | float): Y 坐标。
            trace (bool): 是否打印调试信息。默认为 True。
        Returns:
            bool: 如果释放成功则返回 True，否则返回 False。
        """
        ...

    @abstractmethod
    def scroll(self, distance: int) -> bool:
        """
        滚动鼠标滚轮。

        Args:
            distance (int): 滚动距离。

        Returns:
            bool: 如果滚动成功则返回 True，否则返回 False。
        """
        ...

    def drag_to(self,
                from_x: int | float,
                from_y: int | float,
                to_x: int | float,
                to_y: int | float,
                duration: float = 0.5,
                trace: bool = True) -> bool:
        """
        拖动鼠标到指定位置。

        Args:
            from_x (int | float): 目标 X 坐标。
            from_y (int | float): 目标 Y 坐标。
            to_x (int | float): 目标 X 坐标。
            to_y (int | float): 目标 Y 坐标。
            duration (float): 拖动持续时间，单位为秒。
            trace (bool): 是否打印调试信息。默认为 True。
        Returns:
            bool: 如果拖动成功则返回 True，否则返回 False。
        """
        self.mouse_down(from_x, from_y, trace=trace)
        self.move_to(to_x, to_y, duration, trace=trace)
        self.mouse_up(trace=trace)
        return True

    @staticmethod
    def do_while(action: Callable[[], Any], condition: Callable[[], bool], interval: float = 0.1,
                 max_iterations: int = 50) -> bool:
        """
        在满足条件时重复执行操作。

        操作函数会先被执行一次，然后在每次检查条件前等待指定的时间。如果条件不再满足或达到最大迭代次数，循环将停止。
        Args:
            action (Callable[[], None]): 操作函数。
            condition (Callable[[], bool]): 条件函数，返回布尔值。
            interval (float): 每次检查条件前的等待时间，单位为秒。
            max_iterations (int): 最大迭代次数，防止无限循环。
        Returns:
            bool: 因不再满足条件而退出返回 True，达到最大迭代次数返回 False。
        """
        iterations = 0
        action()
        time.sleep(interval)
        while condition() and iterations < max_iterations:
            action()
            time.sleep(interval)
            iterations += 1
        return iterations != max_iterations
