from pathlib import Path

import cv2
import pyautogui
import pygetwindow
# noinspection PyPackageRequirements
# (pyperclip is in pyautogui requirements)
import pyscreeze
from rapidocr_onnxruntime import RapidOCR

from SRACore.operator.ioperator import *
from SRACore.util.config import load_settings


class Operator(IOperator):
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
        return pyscreeze.screenshot(region=region.sub_region(from_x,from_y,to_x,to_y).tuple)

    def locate_in_region(self,
                         img_path: str,
                         region: Region | None = None,
                         confidence: float | None = None,
                         trace: bool = True,
                         **_) -> Box | None:
        """在屏幕上查找图片位置"""
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

    def locate_in_tuple(self,
                        img_path: str,
                        from_x: float,
                        from_y: float,
                        to_x: float,
                        to_y: float,
                        confidence: float | None = None,
                        trace: bool = True,
                        **_) -> Box | None:
        """
        在窗口内查找图片位置，使用比例坐标
        :param img_path: 模板图片路径
        :param from_x: 区域起始x坐标比例(0-1)
        :param from_y: 区域起始y坐标比例(0-1)
        :param to_x: 区域结束x坐标比例(0-1)
        :param to_y: 区域结束y坐标比例(0-1)
        :param confidence: 匹配度, 0-1之间的浮点数, 默认为self.confidence
        :param trace: 是否打印调试信息
        :return: Box | None - 找到的图片位置，如果未找到则返回None
        """
        try:
            region = self.get_win_region()
        except Exception as e:
            logger.trace(f"ImageNotFound: {img_path} -> {e}")
            return None
        return self.locate_in_region(img_path, region.sub_region(from_x,from_y,to_x,to_y), confidence, trace)

    def locate_any_in_region(self,
                             img_paths: list[str],
                             region: Region | None = None,
                             confidence: float | None = None,
                             trace: bool = True) -> tuple[int, Box | None]:
        """在窗口内查找任意一张图片位置"""
        if confidence is None:
            confidence = self.confidence
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
                box = pyscreeze.locate(img, screenshot, confidence=confidence)
            except pyscreeze.ImageNotFoundException as e:
                if trace:
                    logger.trace(f"ImageNotFound: {img_path} -> {e}")
                continue
            if box is not None:
                return img_paths.index(img_path), Box(box.left, box.top, box.width, box.height, source=img_path)
        return -1, None

    def locate_any_in_tuple(self,
                            img_paths: list[str],
                            from_x: float,
                            from_y: float,
                            to_x: float,
                            to_y: float,
                            confidence: float | None = None,
                            trace: bool = False) -> tuple[int, Box | None]:
        """
        在窗口内查找任意一张图片位置，使用比例坐标
        :param img_paths: 模板图片路径列表
        :param from_x: 区域起始x坐标比例(0-1)
        :param from_y: 区域起始y坐标比例(0-1)
        :param to_x: 区域结束x坐标比例(0-1)
        :param to_y: 区域结束y坐标比例(0-1)
        :param confidence: 匹配度, 0-1之间的浮点数, 默认为self.confidence
        :param trace: 是否打印调试信息
        :return: tuple[int, Box | None] - 找到的图片索引和位置，如果未找到则返回-1和None
        """
        try:
            region = self.get_win_region()
        except Exception as e:
            logger.trace(f"UnexceptedInterrupt: {img_paths} -> {e}")
            return -1, None
        return self.locate_any_in_region(img_paths, region.sub_region(from_x,from_y,to_x,to_y), confidence, trace)

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
        """
        try:
            if trace:
                logger.debug(f"OCR in region: {region}")
            if region is None:
                region = self.get_win_region()
                time.sleep(0.5)  # 等待窗口稳定
            if self.ocr_engine is None:
                self.ocr_engine = Operator.get_ocr_instance()
            screenshot = self.screenshot(region)
            screenshot = screenshot.convert("L")
            result, _ = self.ocr_engine(screenshot, use_det=True, use_cls=False, use_rec=True)  # NOQA
            if trace:
                logger.debug(f"OCR Result: {result}")
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
        """
        try:
            region = self.get_win_region()
        except Exception as e:
            if trace:
                logger.trace(f"OCR Error: {e}")
            return None
        return self.ocr_in_region(region.sub_region(from_x,from_y,to_x,to_y), trace)

    def click_point(self, x: int | float, y: int | float, x_offset: int | float = 0, y_offset: int | float = 0,
                    after_sleep: float = 0, tag: str = "") -> bool:
        """
        点击指定位置
        如果x和y是整数，则直接点击坐标(x, y)
        如果x和y是浮点数，则将其转换为相对于窗口区域的坐标
        :param x: int或float类型，表示点击位置的x坐标
        :param y: int或float类型，表示点击位置的y坐标
        :param x_offset: x偏移量(px)或百分比(float)
        :param y_offset: y偏移量(px)或百分比(float)
        :param after_sleep: 点击后等待时间，单位秒
        :param tag: 日志标记
        :return: None
        """
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
            # NOQA
            raise ValueError(
                f"Invalid arguments: expected 'int, int' or 'float, float', got '{type(x).__name__}, {type(y).__name__}'")

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
        """
        按下按键一段时间

        Args:
            key: 按键
            duration: 按下时间

        Returns:
            按键成功返回True，否则返回False
        """
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
        """
        Paste the latest content in clipboard.
        :return: None
        """
        pyautogui.keyDown("ctrl")
        pyautogui.keyDown("v")
        pyautogui.keyUp("v")
        pyautogui.keyUp("ctrl")

    def move_rel(self, x_offset: int, y_offset: int) -> bool:
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
            logger.debug(f"Error moving cursor: {e}")
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
            logger.debug(f"Move cursor to ({x}, {y}), duration: {duration}s")
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
            logger.debug(f"Error moving cursor: {e}")
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
            logger.debug(f"Mouse down: ({x}, {y})")
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
            logger.debug(f"Error pressing mouse button: {e}")
            return False

    def mouse_up(self, x: int | float | None = None, y: int | float | None = None) -> bool:
        """
        释放鼠标按钮。
        Returns:
            bool: 如果释放成功则返回 True，否则返回 False。
        """
        try:
            logger.debug(f"Mouse up")
            pyautogui.mouseUp()
            return True
        except Exception as e:
            logger.debug(f"Error releasing mouse button: {e}")
            return False

    def scroll(self, distance: int) -> bool:
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
            logger.debug(f"Error scrolling: {e}")
            return False


class Executable(Operator):
    pass
