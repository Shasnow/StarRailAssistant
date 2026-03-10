import ctypes
import time
from ctypes.wintypes import RECT, POINT
from pathlib import Path

import pyautogui
import pygetwindow
import pyscreeze

from SRACore.operators.ioperator import IOperator
from SRACore.operators.model import Box, Region
from SRACore.util.errors import SRAError, ErrorCode
from SRACore.util.logger import logger


class Operator(IOperator):
    def __init__(self):
        super().__init__()
        self.window_title = "崩坏：星穹铁道"
        self.top = 0
        self.left = 0
        self.width = 0
        self.height = 0
        self._win = None
        self._hwnd = None

    def _get_hwnd(self) -> int | None:
        """获取有效的窗口句柄，无效时自动刷新"""
        if self._hwnd is not None and ctypes.windll.user32.IsWindow(self._hwnd):  # NOQA
            return self._hwnd

        self._win = None
        self._hwnd = None
        try:
            windows = pygetwindow.getWindowsWithTitle(self.window_title)
            for w in windows:
                if w.title == self.window_title:
                    self._win = w
                    self._hwnd = w._hWnd  # NOQA
                    break
        except Exception as e:
            logger.trace(f"WindowNotFound: {self.window_title} -> {e}")
        return self._hwnd

    def is_window_active(self) -> bool:
        hwnd = self._get_hwnd()
        if hwnd is None or self._win is None:
            return False
        return self._win.isActive

    def get_win_region(self, active_window: bool = True, raise_exception: bool = True) -> Region | None:
        """
        获取崩坏：星穹铁道窗口客户区区域
        :return: Region - 窗口客户区区域
        :raises Exception: 如果未找到窗口或窗口未激活
        """
        try:
            hwnd = self._get_hwnd()
            if hwnd is None:
                if raise_exception:
                    raise SRAError(ErrorCode.WINDOW_NOT_FOUND, f"未找到窗口: {self.window_title}")
                return None
            if active_window and self._win is not None and not self._win.isActive:
                self._win.activate()
            region = self._get_client_region(hwnd)
            if region is None:
                if raise_exception:
                    raise SRAError(
                        ErrorCode.WINDOW_REGION_INVALID,
                        f"无法获取窗口客户区区域 '{self.window_title}'", "窗口可能被最小化")
                return None
            return region
        except Exception:  # NOQA
            if raise_exception:
                raise
            return None

    def _get_client_region(self, hwnd) -> Region | None:
        """通过 Win32 API 获取窗口客户区的精确屏幕坐标"""
        client_rect = RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))  # NOQA
        left_top = POINT(client_rect.left, client_rect.top)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(left_top))  # NOQA
        width = client_rect.right - client_rect.left
        height = client_rect.bottom - client_rect.top
        if width <= 0 or height <= 0:
            return None
        self.left = left_top.x
        self.top = left_top.y
        self.width = width
        self.height = height
        return Region(self.left, self.top, self.width, self.height)

    def screenshot_in_region(self, region: Region | None = None):
        if region is None:
            region = self.get_win_region(active_window=True)
            if region is None:# 兜底，并非重复判断
                return pyscreeze.screenshot()
        # 保护：避免出现宽或高为 0 的区域
        if region.width <= 0 or region.height <= 0:
            # 尝试使用未对齐的窗口区域重新计算
            fallback = self.get_win_region(active_window=True)
            if fallback and fallback.width > 0 and fallback.height > 0:
                region = fallback
            else:
                # 返回整个屏幕截图作为最后回退，避免下游报错
                return pyscreeze.screenshot()
        return pyscreeze.screenshot(region=region.tuple)

    def screenshot_in_tuple(self, from_x: float, from_y: float, to_x: float, to_y: float):
        region = self.get_win_region()
        if region is None:
            return pyscreeze.screenshot()
        return pyscreeze.screenshot(region=region.sub_region(from_x,from_y,to_x,to_y).tuple)

    def locate_in_region(self,
                         img_path: str,
                         region: Region | None = None,
                         confidence: float | None = None,
                         trace: bool = True,
                         **_) -> Box | None:
        match_confidence = float(self.confidence if confidence is None else confidence)
        try:
            if region is None:
                region = self.get_win_region()
                time.sleep(0.5)
            if region is None:
                return None
            if not Path(img_path).exists():
                raise FileNotFoundError("无法找到或读取文件 " + img_path)
            box = pyscreeze.locate(img_path, self.screenshot(region), confidence=match_confidence)
            if box is None:
                return None
            return Box(box.left, box.top, box.width, box.height, source=img_path)
        except Exception as e:
            if trace:
                logger.trace(f"ImageNotFound: {img_path} -> {e}")
            return None

    def locate_in_tuple(self, templates: str, from_x: float, from_y: float, to_x: float, to_y: float,
                        confidence: float | None = None, trace: bool = True, **_) -> Box | None:
        try:
            region = self.get_win_region()
        except Exception as e:
            logger.trace(f"ImageNotFound: {templates} -> {e}")
            return None
        if region is None:
            return None
        return self.locate_in_region(templates, region.sub_region(from_x, from_y, to_x, to_y), confidence, trace)

    def locate_any_in_region(self, templates: list[str], region: Region | None = None, confidence: float | None = None,
                             trace: bool = True) -> tuple[int, Box | None]:
        match_confidence = float(self.confidence if confidence is None else confidence)
        try:
            screenshot = self.screenshot(region=region)
        except Exception as e:
            logger.trace(f"Error taking screenshot: {e}")
            return -1, None
        for img_path in templates:
            if not Path(img_path).exists():
                raise FileNotFoundError("无法找到或读取文件 " + img_path)
            try:
                box = pyscreeze.locate(img_path, screenshot, confidence=match_confidence)
            except pyscreeze.ImageNotFoundException as e:
                if trace:
                    logger.trace(f"ImageNotFound: {img_path} -> {e}")
                continue
            except ValueError as e:
                if trace:
                    logger.trace(f"ImageNotFound: {img_path} -> {e}")
                continue
            if box is not None:
                return templates.index(img_path), Box(box.left, box.top, box.width, box.height, source=img_path)
        return -1, None

    def locate_any_in_tuple(self, templates: list[str], from_x: float, from_y: float, to_x: float, to_y: float,
                            confidence: float | None = None, trace: bool = False) -> tuple[int, Box | None]:
        try:
            region = self.get_win_region()
        except Exception as e:
            logger.trace(f"UnexceptedInterrupt: {templates} -> {e}")
            return -1, None
        if region is None:
            return -1, None
        return self.locate_any_in_region(templates, region.sub_region(from_x, from_y, to_x, to_y), confidence, trace)

    def locate_all_in_region(self, template: str, region: Region | None = None, confidence: float | None = None,
                             trace: bool = True) -> list[Box] | None:
        match_confidence = float(self.confidence if confidence is None else confidence)
        try:
            if region is None:
                region = self.get_win_region()
                time.sleep(0.5)
            if region is None:
                return None
            if not Path(template).exists():
                raise FileNotFoundError("无法找到或读取文件 " + template)
            boxes = pyscreeze.locateAll(template, self.screenshot(region), confidence=match_confidence)
            result = []
            for box in boxes:
                result.append(Box(box.left, box.top, box.width, box.height, source=template))
            return result
        except Exception as e:
            if trace:
                logger.trace(f"ImageNotFound: {template} -> {e}")
            return None

    def locate_all_in_tuple(self, template: str, from_x: float, from_y: float, to_x: float, to_y: float,
                            confidence: float | None = None, trace: bool = True) -> list[Box] | None:
        try:
            region = self.get_win_region()
        except Exception as e:
            logger.trace(f"ImageNotFound: {template} -> {e}")
            return None
        if region is None:
            return None
        return self.locate_all_in_region(template, region.sub_region(from_x, from_y, to_x, to_y), confidence, trace)

    def click_point(self, x: int | float, y: int | float, x_offset: int | float = 0, y_offset: int | float = 0,
                    after_sleep: float = 0, tag: str = "") -> bool:
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
            logger.debug(f"Click point: ({x}, {y}), tag: {tag}")
            pyautogui.click(x, y)
            self.sleep(after_sleep)
            return True
        else:
            raise ValueError(
                f"Invalid arguments: expected 'int, int' or 'float, float', got '{type(x).__name__}, {type(y).__name__}'")

    def press_key(self, key: str, presses: int = 1, interval: float = 0, wait: float = 0, trace: bool = True) -> bool:
        try:
            time.sleep(wait)
            if trace:
                logger.debug(f"Press key: {key}")
            pyautogui.press(key, presses=presses, interval=interval)
            return True
        except Exception as e:
            if trace:
                logger.debug(f"Failed to press key: {e}")
            return False

    def hold_key(self, key: str, duration: float = 0) -> bool:
        try:
            logger.debug(f"Hold key {key}")
            pyautogui.keyDown(key)
            time.sleep(duration)
            pyautogui.keyUp(key)
            return True
        except Exception as e:
            logger.debug(f"Failed to hold key: {e}")
            return False

    def paste(self) -> None:
        pyautogui.keyDown("ctrl")
        pyautogui.keyDown("v")
        pyautogui.keyUp("v")
        pyautogui.keyUp("ctrl")

    def move_rel(self, x_offset: int, y_offset: int) -> bool:
        try:
            pyautogui.moveRel(x_offset, y_offset)
            return True
        except Exception as e:
            logger.debug(f"Error moving cursor: {e}")
            return False

    def move_to(self, x: int | float, y: int | float, duration: float = 0.0, trace:bool = True) -> bool:
        try:
            if trace:
                logger.debug(f"Move cursor to ({x}, {y}), duration: {duration}s")
            if isinstance(x, int) and isinstance(y, int):
                pyautogui.moveTo(x + self.left, y + self.top, duration=duration)
            elif isinstance(x, float) and isinstance(y, float):
                x = int(self.left + self.width * x)
                y = int(self.top + self.height * y)
                pyautogui.moveTo(x, y, duration=duration)
            else:
                raise ValueError(
                    f"Invalid arguments: expected 'int, int' or 'float, float', got '{type(x).__name__}, {type(y).__name__}'")
            return True
        except Exception as e:
            logger.debug(f"Error moving cursor: {e}")
            return False

    def mouse_down(self, x: int | float, y: int | float, trace: bool = True) -> bool:
        try:
            if trace:
                logger.debug(f"Mouse down: ({x}, {y})")
            if isinstance(x, int) and isinstance(y, int):
                pyautogui.mouseDown(x + self.left, y + self.top)
            elif isinstance(x, float) and isinstance(y, float):
                x = int(self.left + self.width * x)
                y = int(self.top + self.height * y)
                pyautogui.mouseDown(x, y)
            else:
                raise ValueError(
                    f"Invalid arguments: expected 'int, int' or 'float, float', got '{type(x).__name__}, {type(y).__name__}'")
            return True
        except Exception as e:
            logger.debug(f"Error pressing mouse button: {e}")
            return False

    def mouse_up(self, x: int | float | None = None, y: int | float | None = None, trace:bool = True) -> bool:
        try:
            if trace:
                logger.debug("Mouse up")
            pyautogui.mouseUp()
            return True
        except Exception as e:
            logger.debug(f"Error releasing mouse button: {e}")
            return False

    def scroll(self, distance: int) -> bool:
        try:
            pyautogui.scroll(distance)
            return True
        except Exception as e:
            logger.debug(f"Error scrolling: {e}")
            return False
