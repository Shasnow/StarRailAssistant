import ctypes
import sys
import threading
import time
from ctypes.wintypes import POINT, RECT

import pyautogui
import pygetwindow  # type: ignore
import pyscreeze
from PIL.Image import Image

from SRACore.operators.ioperator import IOperator
from SRACore.operators.model import Region
from SRACore.util.errors import ErrorCode, SRAError, ThreadStoppedError
from SRACore.util.logger import logger


class Operator(IOperator):
    def __init__(self, stop_event: threading.Event | None = None):
        super().__init__(stop_event)
        self.window_title = "崩坏：星穹铁道"
        self.top = 0
        self.left = 0
        self.width = 0
        self.height = 0
        self._win: pygetwindow.Win32Window | None = None
        self._hwnd: int = 0

    def _get_hwnd(self) -> int:
        """获取有效的窗口句柄，无效时自动刷新"""
        if self._hwnd is not None and ctypes.windll.user32.IsWindow(self._hwnd):  # NOQA
            return self._hwnd

        self._win = None
        self._hwnd = 0
        try:
            windows: list[pygetwindow.Win32Window] = pygetwindow.getWindowsWithTitle(self.window_title) # type: ignore
            for w in windows:
                if w.title == self.window_title:
                    self._win = w
                    self._hwnd = w._hWnd  # type: ignore # NOQA
                    break
        except Exception as e:
            logger.trace(f"WindowNotFound: {self.window_title} -> {e}")
        return self._hwnd

    def is_window_active(self) -> bool:
        hwnd = self._get_hwnd()
        if not hwnd:
            return False
        return self._win.isActive # type: ignore

    def get_win_region(self, active_window: bool = True) -> Region:
        hwnd = self._get_hwnd()
        if active_window and self._win is not None and not self._win.isActive: # type: ignore
            self._win.activate()
        region = self._get_client_region(hwnd)
        if region is None:
            raise SRAError(
                ErrorCode.WINDOW_REGION_INVALID,
                f"无法获取窗口客户区区域 '{self.window_title}'", "窗口可能被最小化")
        return region

    def _get_client_region(self, hwnd: int) -> Region | None:
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

    def screenshot(self, *,
                   from_x: float | None = None,
                   from_y: float | None = None,
                   to_x: float | None = None,
                   to_y: float | None = None) -> Image:
        region = self.get_win_region(active_window=True)
        self.sleep(0.5)
        img = self._screenshot(self._hwnd, region)
        if img is None:
            raise SRAError(ErrorCode.SCREENSHOT_FAILED, "无法截取窗口内容")
        if from_x is not None and from_y is not None and to_x is not None and to_y is not None:
            left = from_x * self.width
            upper = from_y * self.height
            right = to_x * self.width
            bottom = to_y * self.height
            return img.crop((left, upper, right, bottom))
        return img

    @staticmethod
    def _screenshot(hwnd: int, region: Region):
        """
        后台截取指定窗口，不会被其他窗口遮挡
        :param hwnd: 窗口句柄
        :param region: (left, top, width, height) 客户区坐标
        :return: PIL Image / None
        """
        if sys.platform == "win32":
            # noinspection PyPackageRequirements
            import win32gui # (in pywin32)
            import win32ui
            import ctypes
            from PIL import Image

            left, top, width, height = region.tuple

            # 句柄无效直接返回
            if not hwnd or width <= 0 or height <= 0:
                return None

            hwnd_dc = None
            mfc_dc = None
            save_dc = None
            save_bit_map = None

            try:
                # === 获取窗口 DC ===
                hwnd_dc = win32gui.GetWindowDC(hwnd)
                mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
                save_dc = mfc_dc.CreateCompatibleDC()

                # === 创建位图 ===
                save_bit_map = win32ui.CreateBitmap()
                save_bit_map.CreateCompatibleBitmap(mfc_dc, width, height)
                save_dc.SelectObject(save_bit_map)

                # === 后台截图核心===
                PW_CLIENTONLY = 1  # NOQA
                PW_RENDERFULLCONTENT = 2  # NOQA
                flags = PW_CLIENTONLY | PW_RENDERFULLCONTENT  # 游戏通用

                # noinspection PyUnresolvedReferences
                result = ctypes.windll.user32.PrintWindow(
                    hwnd,
                    save_dc.GetSafeHdc(),
                    flags
                )

                if result == 0:
                    return None

                # === 转 PIL Image（颜色正确、无偏移）===
                bmp_info = save_bit_map.GetInfo()
                bmp_data = save_bit_map.GetBitmapBits(True)

                img = Image.frombuffer(
                    "RGB",
                    (bmp_info["bmWidth"], bmp_info["bmHeight"]),
                    bmp_data,
                    "raw",
                    "BGRX",
                    0,
                    1
                )

                return img

            finally:
                # === 强制安全释放资源===
                if save_bit_map:
                    win32gui.DeleteObject(save_bit_map.GetHandle())
                if save_dc:
                    save_dc.DeleteDC()
                if mfc_dc:
                    mfc_dc.DeleteDC()
                if hwnd_dc:
                    win32gui.ReleaseDC(hwnd, hwnd_dc)
        else:
            return pyscreeze.screenshot(region=region.tuple)

    def click_point(self, x: int | float, y: int | float, x_offset: int | float = 0, y_offset: int | float = 0,
                    after_sleep: float = 0, tag: str = "", trace: bool = False) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("点击中断", "线程已停止")
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
            if trace:
                logger.debug(f"Click point: ({x}, {y}), tag: {tag}")
            pyautogui.click(x, y)
            self.sleep(after_sleep)
            return True
        else:
            raise ValueError(
                f"Invalid arguments: expected 'int, int' or 'float, float', got '{type(x).__name__}, {type(y).__name__}'")

    def press_key(self, key: str, presses: int = 1, interval: float = 0, wait: float = 0, trace: bool = True) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("按键中断", "线程已停止")
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
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("按键中断", "线程已停止")
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
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("粘贴中断", "线程已停止")
        pyautogui.keyDown("ctrl")
        pyautogui.keyDown("v")
        pyautogui.keyUp("v")
        pyautogui.keyUp("ctrl")

    def move_rel(self, x_offset: int, y_offset: int) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("鼠标移动中断", "线程已停止")
        try:
            pyautogui.moveRel(x_offset, y_offset)
            return True
        except Exception as e:
            logger.debug(f"Error moving cursor: {e}")
            return False

    def move_to(self, x: int | float, y: int | float, duration: float = 0.0, trace: bool = True) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("鼠标移动中断", "线程已停止")
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
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("点击中断", "线程已停止")
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

    def mouse_up(self, x: int | float | None = None, y: int | float | None = None, trace: bool = True) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("点击中断", "线程已停止")
        try:
            if trace:
                logger.debug("Mouse up")
            pyautogui.mouseUp()
            return True
        except Exception as e:
            logger.debug(f"Error releasing mouse button: {e}")
            return False

    def scroll(self, distance: int) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            raise ThreadStoppedError("Error scrolling", "线程已停止")
        try:
            pyautogui.scroll(distance)
            return True
        except Exception as e:
            logger.debug(f"Error scrolling: {e}")
            return False
