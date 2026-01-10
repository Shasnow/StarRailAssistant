from pathlib import Path

import cv2
import pyautogui
import pygetwindow
# noinspection PyPackageRequirements
# (pyperclip is in pyautogui requirements)
import pyscreeze

from SRACore.operators.ioperator import *


class Operator(IOperator):
    def __init__(self):
        super().__init__()
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
        # 将窗口尺寸对齐到 160x90 的比例，但避免出现 0 尺寸
        aligned_width = (width // 160) * 160
        aligned_height = (height // 90) * 90
        # 当窗口较小或对齐后为 0 时，回退到原始尺寸以避免截屏高度为 0
        self.width = aligned_width if aligned_width > 0 else width
        self.height = aligned_height if aligned_height > 0 else height
        self.top = (top + int(30 * self.zoom)) if top != 0 else top
        self.left = (left + int(8 * self.zoom)) if left != 0 else left
        return Region(self.left, self.top, self.width, self.height)

    def screenshot_in_region(self, region: Region | None = None):
        if region is None:
            region = self.get_win_region(active_window=True)
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
        return pyscreeze.screenshot(region=region.sub_region(from_x,from_y,to_x,to_y).tuple)

    def locate_in_region(self,
                         img_path: str,
                         region: Region | None = None,
                         confidence: float | None = None,
                         trace: bool = True,
                         **_) -> Box | None:
        if confidence is None:
            confidence = self.confidence
        try:
            if region is None:
                region = self.get_win_region()
                time.sleep(0.5)
            if not Path(img_path).exists():
                raise FileNotFoundError("无法找到或读取文件 " + img_path)
            img = cv2.imread(img_path)
            box = pyscreeze.locate(img, self.screenshot(region), confidence=confidence)
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
        return self.locate_in_region(templates, region.sub_region(from_x, from_y, to_x, to_y), confidence, trace)

    def locate_any_in_region(self, templates: list[str], region: Region | None = None, confidence: float | None = None,
                             trace: bool = True) -> tuple[int, Box | None]:
        if confidence is None:
            confidence = self.confidence
        try:
            screenshot = self.screenshot(region=region)
        except Exception as e:
            logger.trace(f"Error taking screenshot: {e}")
            return -1, None
        for img_path in templates:
            if not Path(img_path).exists():
                raise FileNotFoundError("无法找到或读取文件 " + img_path)
            img = cv2.imread(img_path)
            try:
                box = pyscreeze.locate(img, screenshot, confidence=confidence)
            except pyscreeze.ImageNotFoundException as e:
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
        return self.locate_any_in_region(templates, region.sub_region(from_x, from_y, to_x, to_y), confidence, trace)

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

    def move_to(self, x: int | float, y: int | float, duration: float = 0.0) -> bool:
        try:
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

    def mouse_down(self, x: int | float, y: int | float) -> bool:
        try:
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

    def mouse_up(self, x: int | float | None = None, y: int | float | None = None) -> bool:
        try:
            logger.debug(f"Mouse up")
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
