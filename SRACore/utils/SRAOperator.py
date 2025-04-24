#   This file is part of StarRailAssistant.

#   StarRailAssistant is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the Free Software Foundation,
#   either version 3 of the License, or (at your option) any later version.

#   StarRailAssistant is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#   without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#   See the GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License along with StarRailAssistant.
#   If not, see <https://www.gnu.org/licenses/>.

#   yukikage@qq.com

"""
崩坏：星穹铁道助手
作者：雪影
SRA操作
"""
from os import PathLike

import cv2
import pyautogui
import pygetwindow
import pyperclip
import pyscreeze
import time
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

from SRACore.utils.Exceptions import WindowNoFoundException, MultipleWindowsException, MatchFailureException, \
    WindowInactiveException
from SRACore.utils.Logger import logger, internal


class SRAOperator:
    location_proportion = 1.0
    screenshot_proportion = 1.0
    area_top = 0
    area_left = 0
    zoom = 1.5
    confidence = 0.9
    ocr_engine: RapidOCR = None

    @classmethod
    def _screenshot_region_calculate(cls, region: tuple[int, int, int, int]):
        """
        计算截图区域的实际坐标和尺寸。

        Args:
            region (tuple[int, int, int, int]): 包含窗口左上角坐标和宽高的元组，格式为 (left, top, width, height)。

        Returns:
            tuple[int, int, int, int]: 计算后的截图区域，格式为 (area_left, area_top, area_width, area_height)。
        """
        left, top, width, height = region
        # 计算截图区域的宽度，将宽度调整为 160 的倍数
        area_width = width // 160 * 160
        # 计算截图区域的高度，将高度调整为 90 的倍数
        area_height = height // 90 * 90
        # 根据缩放比例调整顶部坐标，如果顶部坐标不为 0 则加上偏移量
        cls.area_top = (top + int(30 * cls.zoom)) if top != 0 else top
        # 根据缩放比例调整左侧坐标，如果左侧坐标不为 0 则加上偏移量
        cls.area_left = (left + int(8 * cls.zoom)) if left != 0 else left
        return cls.area_left, cls.area_top, area_width, area_height

    @classmethod
    def get_screenshot_region(cls, title: str) -> tuple[int, int, int, int]:
        """
        根据给定的窗口标题获取截图区域。

        该方法会查找包含指定标题的窗口，若未找到则抛出 WindowNoFoundException 异常，
        若找到多个窗口则抛出 MultipleWindowsException 异常。找到唯一窗口后，会激活该窗口，
        并计算其截图区域。

        Args:
            title (str): 用于查找窗口的标题。

        Returns:
            tuple[int, int, int, int]: 计算后的截图区域，格式为 (area_left, area_top, area_width, area_height)。

        Raises:
            WindowNoFoundException: 未找到包含指定标题的窗口。
            MultipleWindowsException: 找到多个包含指定标题的窗口。
        """
        matching_windows = pygetwindow.getWindowsWithTitle(title)
        if len(matching_windows) == 0:
            raise WindowNoFoundException('Could not find a window with %s in the title' % title)
        elif len(matching_windows) > 1:
            raise MultipleWindowsException(
                'Found multiple windows with %s in the title: %s' % (
                    title, [str(win) for win in matching_windows])
            )
        win = matching_windows[0]
        win.activate()
        region = (win.left, win.top, win.width, win.height)
        region = cls._screenshot_region_calculate(region)
        return region

    @classmethod
    def get_screenshot(cls, title: str = "崩坏：星穹铁道",
                       region: tuple[int, int, int, int] | None = None) -> Image.Image:
        """
        根据指定的窗口标题和区域获取截图，并对截图进行尺寸调整。

        Args:
            title (str): 用于查找窗口的标题。
            region (tuple[int, int, int, int] | None): 截图区域，格式为 (left, top, width, height)。
                如果为 None，则通过 `get_screenshot_region` 方法根据标题自动计算截图区域。

        Returns:
            Image.Image: 调整尺寸后的 Pillow 图像对象。
        """
        if region is None:
            region = cls.get_screenshot_region(title)
        pillow_img = pyscreeze.screenshot(region=region)
        # pillow_img.show()
        return cls._image_resize(pillow_img)
        # return pillow_img

    @classmethod
    def _image_resize(cls, pillow_image: Image.Image) -> Image.Image:
        """
        调整 Pillow 图像的尺寸，若图像宽度已经为 1920 则直接返回原图像，
        否则将图像调整为宽度为 1920 的图像，并保持宽高比。

        Args:
            pillow_image (Image.Image): 待调整尺寸的 Pillow 图像对象。

        Returns:
            Image.Image: 调整尺寸后的 Pillow 图像对象。
        """
        if pillow_image.width == 1920:
            return pillow_image
        cls.screenshot_proportion = 1920 / pillow_image.width
        resized_image = pillow_image.resize(
            (int(pillow_image.width * cls.screenshot_proportion),
             int(pillow_image.height * cls.screenshot_proportion)),
            Image.Resampling.BICUBIC)
        # resized_image.show()
        return resized_image

    @classmethod
    def _location_calculator(cls, x, y):
        """
        根据截图缩放比例和截图区域偏移量，计算实际屏幕坐标。

        Args:
            x (int): 截图上的 x 坐标。
            y (int): 截图上的 y 坐标。

        Returns:
            tuple[int, int]: 实际屏幕上的坐标 (x, y)。
        """
        cls.location_proportion = 1 / cls.screenshot_proportion
        return x * cls.location_proportion + cls.area_left, y * cls.location_proportion + cls.area_top
        # return x, y

    @classmethod
    def locate(cls, img_path: str, title="崩坏：星穹铁道"):
        """
        在指定标题的窗口截图中定位指定图像的位置。

        该方法会读取指定路径的图像文件，若文件无法找到或读取，会抛出 FileNotFoundError 异常。
        接着会在指定标题的窗口截图中查找该图像，若未找到，会抛出 MatchFailureException 异常。
        若在查找过程中出现 ValueError 异常，会抛出 WindowInactiveException 异常，提示窗口未激活。

        Args:
            img_path (str): 要定位的图像文件的路径。
            title (str, optional): 用于查找窗口的标题，默认为 "崩坏：星穹铁道"。

        Returns:
            tuple: 图像在截图中的位置，格式为 (left, top, width, height)，若未找到则抛出异常。

        Raises:
            FileNotFoundError: 无法找到或读取指定路径的图像文件。
            MatchFailureException: 在截图中未找到指定的图像。
            WindowInactiveException: 查找过程中出现 ValueError，提示窗口未激活。
        """
        try:
            img = cv2.imread(img_path)
            if img is None:
                raise FileNotFoundError("无法找到或读取文件 " + img_path)
            # location = pyautogui.locateOnWindow(img, title, confidence=cls.confidence)
            location = pyscreeze.locate(img, cls.get_screenshot(title), confidence=cls.confidence)
            return location
        except pyscreeze.ImageNotFoundException as e:
            raise MatchFailureException(f"{img_path}匹配失败 {e}")
        except ValueError:
            raise WindowInactiveException("窗口未激活")
        except FileNotFoundError:
            raise

    @classmethod
    def locateAny(cls, img_list: list):
        """
        在截图中依次定位图像列表中的图像，返回第一个匹配成功的图像的索引和位置。

        Args:
            img_list (list): 包含要定位的图像文件路径的列表。

        Returns:
            tuple: 第一个匹配成功的图像的索引和位置，格式为 (index, location)。

        Raises:
            MatchFailureException: 当图像列表中的所有图像都未匹配成功时抛出此异常。
        """
        screenshot = cls.get_screenshot()
        for index, img_path in enumerate(img_list):
            try:
                img = cv2.imread(img_path)
                if img is None:
                    raise FileNotFoundError("无法找到或读取文件 " + img_path)
                # location = pyautogui.locateOnWindow(img, title, confidence=cls.confidence)
                location = pyscreeze.locate(img, screenshot, confidence=cls.confidence)
                return index, location
            except pyscreeze.ImageNotFoundException:
                continue
            except ValueError:
                continue
            except FileNotFoundError:
                continue
        else:
            raise MatchFailureException(f"{img_list}匹配失败")

    @classmethod
    def locateAll(cls, img_list: list):
        """
        在截图中依次定位图像列表中的所有图像，返回所有匹配成功的图像的索引和位置。

        Args:
            img_list (list): 包含要定位的图像文件路径的列表。

        Returns:
            list: 所有匹配成功的图像的索引和位置，格式为 [(index1, location1), (index2, location2), ...]。

        Raises:
            MatchFailureException: 当图像列表中的所有图像都未匹配成功时抛出此异常。
        """
        screenshot = cls.get_screenshot()
        result = []
        for index, img_path in enumerate(img_list):
            try:
                img = cv2.imread(img_path)
                if img is None:
                    raise FileNotFoundError("无法找到或读取文件 " + img_path)
                location = pyscreeze.locate(img, screenshot, confidence=cls.confidence)
                result.append((index, location))
            except pyscreeze.ImageNotFoundException:
                continue
            except ValueError:
                continue
            except FileNotFoundError:
                continue
        if len(result) == 0:
            raise MatchFailureException(f"{img_list}匹配失败")
        return result

    @classmethod
    def locateCenter(cls, img_path, x_add=0, y_add=0, title="崩坏：星穹铁道") -> tuple[int, int]:
        """
        在指定标题的窗口截图中定位指定图像的中心位置，并根据偏移量进行调整，最后计算出实际屏幕坐标。

        Args:
            img_path (str): 要定位的图像文件的路径。
            x_add (int, optional): 图像中心位置在 x 轴上的偏移量，默认为 0。
            y_add (int, optional): 图像中心位置在 y 轴上的偏移量，默认为 0。
            title (str, optional): 用于查找窗口的标题，默认为 "崩坏：星穹铁道"。

        Returns:
            tuple[int, int]: 实际屏幕上的坐标 (x, y)。

        Raises:
            FileNotFoundError: 无法找到或读取指定路径的图像文件。
            MatchFailureException: 在截图中未找到指定的图像。
            WindowInactiveException: 查找过程中出现 ValueError，提示窗口未激活。
        """
        location = cls.locate(img_path, title)
        x, y = pyscreeze.center(location)
        x += x_add
        y += y_add
        x, y = cls._location_calculator(x, y)
        return x, y

    @classmethod
    def exist(cls, img_path: str | PathLike, wait_time=2) -> bool:
        """
        检查指定路径的图像是否存在于截图中。

        该方法会先等待指定的时间，等待游戏加载过程，然后尝试在截图中定位指定路径的图像。
        如果定位成功，则返回 True；如果定位过程中出现异常，则记录异常信息并返回 False。

        Args:
            img_path (str): 要定位的图像文件的路径。
            wait_time (float, optional): 等待游戏加载的时间，默认为 2 秒。

        Returns:
            bool: 如果图像存在则返回 True，否则返回 False。
        """
        time.sleep(wait_time)  # 等待游戏加载
        try:
            cls.locate(img_path)
            return True
        except Exception as e:
            logger.log(internal, e.__str__())
            return False

    @classmethod
    def existAny(cls, img_list: list, wait_time: float = 2) -> int | None:
        """
        检查图像列表中是否有任何图像存在于截图中。

        该方法会先等待指定的时间，等待游戏加载过程，然后尝试在截图中依次定位图像列表中的图像。
        如果有任何图像定位成功，则返回该图像在列表中的索引；如果所有图像都未定位成功，则记录异常信息并返回 None。

        Args:
            img_list (list): 包含要定位的图像文件路径的列表。
            wait_time (float, optional): 等待游戏加载的时间，默认为 2 秒。

        Returns:
            int | None: 如果有图像存在则返回该图像在列表中的索引，否则返回 None。
        """
        time.sleep(wait_time)  # 等待游戏加载
        try:
            result = cls.locateAny(img_list)[0]
            return result
        except Exception as e:
            logger.log(internal, e)
            return None

    @classmethod
    def check(cls, img_path: str | PathLike, interval=0.5, max_time=40):
        """
        持续检查指定路径的图像是否出现在截图中。

        该方法会按照指定的时间间隔持续检查图像，直到图像出现或者达到最大检查次数。

        Args:
            img_path (str): 要检查的图像文件的路径。
            interval (float, optional): 每次检查之间的时间间隔，默认为 0.5 秒。
            max_time (int, optional): 最大检查次数，默认为 40 次。

        Returns:
            bool: 如果在最大检查次数内找到图像，则返回 True；否则返回 False。
        """
        times = 0
        while True:
            time.sleep(interval)
            if cls.exist(img_path, wait_time=1):
                return True
            else:
                times += 1
                if times == max_time:
                    return False

    @classmethod
    def checkAny(cls, img_list: list, interval=0.5, max_time=40):
        """依次检查图像列表中的图像是否出现。

        Args:
            img_list: 存储图像文件路径的列表。
            interval: 每次检查之间的时间间隔。
            max_time: 最大检查次数。

        Returns:
            如果有任何图像出现，则返回该图像在列表中的索引；如果所有图像都未出现且达到最大检查次数，则返回 None。
        """
        times = 0
        while True:
            time.sleep(interval)
            result = cls.existAny(img_list, wait_time=1)
            if result is not None:
                return result
            else:
                times += 1
                if times == max_time:
                    return None

    @classmethod
    def get_screen_center(cls):
        """
        获取当前活动窗口的中心点坐标。

        Returns:
            tuple: 中心点坐标 (x, y)。
        """
        active_window = pygetwindow.getActiveWindow()
        x, y, screen_width, screen_height = (
            active_window.left,
            active_window.top,
            active_window.width,
            active_window.height,
        )
        return x + screen_width // 2, y + screen_height // 2

    @classmethod
    def click_img(
            cls,
            img_path: str | PathLike,
            x_add=0,
            y_add=0,
            wait_time=2.0,
            title="崩坏：星穹铁道"):
        """在屏幕上点击对应的图像

        Args:
            img_path (str): 图像文件路径。
            x_add (int): X 轴偏移量（像素）。
            y_add (int): Y 轴偏移量（像素）。
            wait_time (float): 执行点击前的等待时间（秒）。
            title (str): 窗口标题。
        Returns:
            若点击成功则返回 True，否则返回 False。
        """
        try:
            time.sleep(wait_time)
            logger.debug(f"点击对象{img_path}")
            x, y = cls.locateCenter(img_path, x_add, y_add, title)
            pyautogui.click(x, y)
            return True
        except Exception as e:
            logger.log(internal, f"点击对象时出错{e}")
            return False

    @classmethod
    def click_point(cls, x: int | None, y: int | None) -> bool:
        """
        在指定的坐标处点击。如果不填入参数，则点击当前光标所在的位置。

        该方法会尝试在指定的坐标处执行点击操作。如果不填入参数，则会点击当前光标所在的位置。
        如果点击成功，则返回 True；否则返回 False。
        如果在点击过程中出现异常，则会记录异常信息并返回 False。

        Args:
            x (int | None): 横坐标。
            y (int | None): 纵坐标。

        Returns:
            bool: 如果点击成功则返回 True，否则返回 False。
        """
        try:
            pyautogui.click(x, y)
            return True
        except Exception as e:
            logger.log(internal, f"点击坐标时出错{e}")
            return False

    @classmethod
    def press_key(cls, key: str, presses: int = 1, interval: float = 2) -> bool:
        """按下按键
        
        Args:
            key: 按键
            presses: 按下次数
            interval: 按键间隔时间(如果填入,程序会等待interval秒再按下按键)
        Returns:
            按键成功返回True，否则返回False
        """
        try:
            logger.debug("按下按键" + key)
            pyautogui.press(key, presses=presses, interval=interval)
            return True
        except Exception as e:
            logger.log(internal, f"按下按键失败{e}")
            return False

    @classmethod
    def press_key_for_a_while(cls, key: str, during: float = 0) -> bool:
        """
        按下按键一段时间

        Args:
            key: 按键
            during: 按下时间

        Returns:
            按键成功返回True，否则返回False
        """
        try:
            logger.debug("按下按键" + key)
            pyautogui.keyDown(key)
            time.sleep(during)
            pyautogui.keyUp(key)
            return True
        except Exception as e:
            logger.log(internal, f"按下按键失败{e}")
            return False

    @staticmethod
    def _key_in_utf8(key):
        """
        将按键转换为 UTF-8 编码。

        Args:
            key (str): 要转换的按键。

        Returns:
            str: 转换后的 UTF-8 编码。

        Raises:
            ValueError: 如果输入的按键不在预定义的列表中。
        """
        match key:
            case "esc":
                return "\uE00C"
            case "f1":
                return "\uE031"
            case "f2":
                return "\uE032"
            case "f3":
                return "\uE033"
            case "f4":
                return "\uE034"
            case "f5":
                return "\uE035"
            case "enter":
                return "\uE006"
            case "w":
                return "w"
            case "v":
                return "v"
            case _:
                raise ValueError("意料之外的按键")

    @classmethod
    def write(cls, content: str = "") -> bool:
        """
        输入文本内容。

        Args:
            content (str): 要输入的文本内容。

        Returns:
            bool: 如果输入成功则返回 True，否则返回 False。
        """
        try:
            pyautogui.write(content)
            return True
        except Exception as e:
            logger.log(internal, f"输入时发生错误{e}")
            return False

    @classmethod
    def moveRel(cls, x_offset: int, y_offset: int) -> bool:
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
            logger.log(internal, f"移动光标时出错{e}")
            return False

    @classmethod
    def moveTo(cls, *args):
        """
        移动光标到指定位置。

        Args:
            *args: 参见 pyautogui.moveTo 的参数。

        Returns:
            bool: 如果移动成功则返回 True，否则返回 False。
        """
        return pyautogui.moveTo(*args)

    @classmethod
    def dragTo(cls, *args):
        """
        拖动光标到指定位置。

        Args:
            *args: 参见 pyautogui.dragTo 的参数。

        Returns:
            bool: 如果拖动成功则返回 True，否则返回 False。
        """
        return pyautogui.dragTo(*args)

    @classmethod
    def dragRel(cls, *args, **kwargs):
        """
        相对当前位置拖动光标。

        Args:
            *args: 参见 pyautogui.dragRel 的参数。

        Returns:
            bool: 如果拖动成功则返回 True，否则返回 False。
        """
        return pyautogui.dragRel(*args, **kwargs)

    @classmethod
    def scroll(cls, distance: int) -> bool:
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
            logger.log(internal, f"指针滚动时发生错误{e}")
            return False

    @classmethod
    def copy(cls, text: str):
        """
        Copy the text to clipboard.
        :param text: The text to copy.
        :return: none
        """
        return pyperclip.copy(text)

    @classmethod
    def paste(cls):
        """
        Paste the latest content in clipboard.
        :return: none
        """
        pyautogui.keyDown("ctrl")
        pyautogui.keyDown("v")
        pyautogui.keyUp("v")
        pyautogui.keyUp("ctrl")

    @classmethod
    def ocr_in_region(cls, area_left: int, area_top: int, width: int, height: int):
        """
        在指定区域内执行 OCR 识别。(相对于截图区域)

        该方法会在指定的区域内进行截图，并使用 RapidOCR 引擎对截图进行 OCR 识别。
        如果 OCR 引擎尚未初始化，则会先对其进行初始化。

        Args:
            area_left (int): 指定区域相对于截图区域的左侧偏移量。
            area_top (int): 指定区域相对于截图区域的顶部偏移量。
            width (int): 指定区域的宽度。
            height (int): 指定区域的高度。

        Returns:
            list: OCR 识别的结果列表。
        """
        # 若 OCR 引擎未初始化，则进行初始化
        if cls.ocr_engine is None:
            cls.ocr_engine = RapidOCR()
        # 在指定区域内进行截图
        left, top = cls.get_screenshot_region("崩坏：星穹铁道")[0:2]
        img = pyscreeze.screenshot(region=(left + area_left, top + area_top, width, height))
        # 执行 OCR 识别
        result, elapse = cls.ocr_engine(img, use_det=True, use_cls=False, use_rec=True)
        return result
