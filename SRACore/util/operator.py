import dataclasses
import time
from pathlib import Path
from typing import overload

import cv2
import pyautogui
import pygetwindow
import pyperclip
import pyscreeze
from PIL.Image import Image

from SRACore.util.config import GlobalConfigManager
from SRACore.util.logger import logger


@dataclasses.dataclass
class Region:
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
    def __init__(self):
        self.gcm = GlobalConfigManager.get_instance()
        self.confidence = self.gcm.get('confidence', 0.9)
        self.zoom = self.gcm.get('zoom', 1.25)
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
                raise Exception("窗口未激活") from e
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
        """截图"""
        if region is None:
            region = self.get_win_region()
            time.sleep(0.5)
        return pyscreeze.screenshot(region=region.tuple)

    def screenshot_tuple(self, from_x: float, from_y: float, to_x: float, to_y: float):
        """根据比例截图"""
        region = self.get_win_region()
        time.sleep(0.5)
        left = int(region.left + region.width * from_x)
        top = int(region.top + region.height * from_y)
        width = int(region.width * (to_x - from_x))
        height = int(region.height * (to_y - from_y))
        return pyscreeze.screenshot(region=(left, top, width, height))

    @overload
    def screenshot(self, region: Region | None = None) -> Image:
        ...

    @overload
    def screenshot(self, from_x: float, from_y: float, to_x: float, to_y: float) -> Image:
        ...

    def screenshot(self, *args, **kwargs):
        """截图"""
        if len(args) == 0:
            return self.screenshot_region()
        elif len(args) == 1 and (args[0] is None or isinstance(args[0], Region)):
            return self.screenshot_region(args[0])
        elif len(args) == 4 and all(isinstance(arg, (int, float)) for arg in args):
            return self.screenshot_tuple(*args)
        else:
            raise ValueError(
                f"Invalid arguments: expected 'Region' or 'float, float, float, float', got '{' '.join([arg.__class__.__name__ for arg in args])}'")

    def locate_in_region(self,
                         img_path: str,
                         region: Region | None = None,
                         trace: bool = True,
                         **_) -> Box | None:
        """在窗口内查找图片位置"""
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

    def locate_any_in_region(self, img_paths: list[str], region: Region | None = None, trace: bool = True) -> tuple[
        int, pyscreeze.Box | None]:
        """在窗口内查找任意一张图片位置"""
        for img_path in img_paths:
            box = self.locate_in_region(img_path, region, trace)
            if box is not None:
                return img_paths.index(img_path), box
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
        for img_path in img_paths:
            box = self.locate_in_tuple(img_path, from_x, from_y, to_x, to_y, trace)
            if box is not None:
                return img_paths.index(img_path), box
        return -1, None

    @overload
    def locate_any(self, img_paths: list[str], region: Region | None = None, trace: bool = True) -> tuple[
        int, pyscreeze.Box | None]:
        ...

    @overload
    def locate_any(self, img_paths: list[str], from_x: float, from_y: float, to_x: float, to_y: float,
                   trace: bool = True) -> tuple[int, pyscreeze.Box | None]:
        ...

    def locate_any(self, img_paths: list[str], *args, **kwargs) -> tuple[int, pyscreeze.Box | None]:
        """在窗口内查找任意一张图片位置"""
        if len(args) == 0:
            return self.locate_any_in_region(img_paths, **kwargs)
        elif len(args) == 1 and (args[0] is None or isinstance(args[0], Region)):
            return self.locate_any_in_region(img_paths, args[0], **kwargs)
        elif len(args) == 4 and all(isinstance(arg, (int, float)) for arg in args):
            return self.locate_any_in_tuple(img_paths, *args, **kwargs)
        else:
            raise ValueError(
                f"Invalid arguments: expected 'Region' or 'float, float, float, float', got '{' '.join([arg.__class__.__name__ for arg in args])}'")

    @overload
    def locate(self, template: str, region: Region | None = None, trace: bool = True) -> Box | None:
        ...

    @overload
    def locate(self, template: str, from_x: float, from_y: float, to_x: float, to_y: float,
               trace: bool = True) -> Box | None:
        ...

    def locate(self, template: str, *args, **kwargs):
        """在窗口内查找图片位置"""
        if len(args) == 0:
            return self.locate_in_region(template, **kwargs)
        elif len(args) == 1 and (args[0] is None or isinstance(args[0], Region)):
            return self.locate_in_region(template, args[0], **kwargs)
        elif len(args) == 4 and all(isinstance(arg, (int, float)) for arg in args):
            return self.locate_in_tuple(template, *args, **kwargs)
        else:
            raise ValueError(
                f"Invalid arguments: expected 'Region' or 'float, float, float, float', got '{' '.join([arg.__class__.__name__ for arg in args])}'")

    def click_point(self, x: int | float, y: int | float, x_offset: int = 0, y_offset: int = 0,
                    after_sleep: float = 0) -> bool:
        """
        点击指定位置
        如果x和y是整数，则直接点击坐标(x, y)
        如果x和y是浮点数，则将其转换为相对于窗口区域的坐标
        :param x: int或float类型，表示点击位置的x坐标
        :param y: int或float类型，表示点击位置的y坐标
        :param x_offset: x偏移量(px)
        :param y_offset: y偏移量(px)
        :param after_sleep: 点击后等待时间，单位秒
        :return: None
        """
        logger.debug(f"点击位置: ({x}, {y}), 偏移: ({x_offset}, {y_offset}), 等待时间: {after_sleep}秒")
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

    def click_box(self, box: Box, x_offset: int = 0, y_offset: int = 0, after_sleep: float = 0) -> bool:
        """点击图片位置"""
        if box is None:
            logger.trace("Could not click a Empty Box")
            return False
        x, y = box.center
        return self.click_point(int(x), int(y), x_offset, y_offset, after_sleep)

    def click_img(self, img_path: str, x_offset: int = 0, y_offset: int = 0, after_sleep: float = 0) -> bool:
        """点击图片中心"""
        box = self.locate(img_path)
        if box is None:
            return False
        return self.click_box(box, x_offset, y_offset, after_sleep)

    def wait_img(self, img_path: str, timeout: int = 10, interval: float = 0.5) -> bool:
        """
        等待图片出现
        :param img_path: 模板图片路径
        :param timeout: 超时时间，单位秒
        :param interval: 检查间隔时间，单位秒，默认为0.2秒
        :return: bool - 是否找到图片
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.locate(img_path) is not None:
                return True
            time.sleep(interval)
        logger.debug(f"Timeout: {img_path} -> Not found in {timeout} seconds")
        return False

    def wait_any_img(self, img_paths: list[str], timeout: int = 10, interval: float = 0.5) -> int:
        """
        等待任意一张图片出现
        :param img_paths: 模板图片路径列表
        :param timeout: 超时时间，单位秒
        :param interval: 检查间隔时间，单位秒，默认为0.2秒
        :return: int - 找到的图片索引，如果未找到则返回-1
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            for img_path in img_paths:
                if self.locate(img_path) is not None:
                    return img_paths.index(img_path)
            time.sleep(interval)
        logger.debug(f"Timeout: {img_paths} -> Not found in {timeout} seconds")
        return -1

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
                logger.debug("按下按键" + key)
            pyautogui.press(key, presses=presses, interval=interval)
            return True
        except Exception as e:
            if trace:
                logger.debug(f"按下按键失败: {e}")
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
            logger.debug("按下按键 " + key)
            pyautogui.keyDown(key)
            time.sleep(duration)
            pyautogui.keyUp(key)
            return True
        except Exception as e:
            logger.debug(f"按下按键失败: {e}")
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
            logger.debug(f"移动光标时出错{e}")
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
            logger.debug(f"移动光标时发生错误{e}")
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
            logger.debug(f"指针滚动时发生错误{e}")
            return False


class Executable(Operator): pass
