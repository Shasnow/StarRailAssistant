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
import io
import time

import cv2
import pyautogui
import pygetwindow
import pyscreeze
import pyperclip
from PIL import Image
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.webdriver import WebDriver

from StarRailAssistant.utils.Exceptions import WindowNoFoundException, MultipleWindowsException, MatchFailureException, \
    WindowInactiveException
from StarRailAssistant.utils.Logger import logger


class SRAOperator:
    cloud: bool = False
    web_driver: WebDriver = None
    location_proportion = 1.0
    screenshot_proportion = 1.0
    area_top = 0
    area_left = 0
    zoom = 1.5
    confidence = 0.9

    @classmethod
    def _screenshot_region_calculate(cls, region: tuple[int, int, int, int]):
        left, top, width, height = region
        area_width = width // 160 * 160
        area_height = height // 90 * 90
        cls.area_top = (top + int(30 * cls.zoom)) if top != 0 else top
        cls.area_left = (left + int(8 * cls.zoom)) if left != 0 else left
        return cls.area_left, cls.area_top, area_width, area_height

    @classmethod
    def get_screenshot_region(cls, title: str) -> tuple[int, int, int, int]:
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
    def get_screenshot(cls, title: str = "", region: tuple[int, int, int, int] | None = None) -> Image.Image:
        if cls.cloud:
            bytes_png = cls.web_driver.get_screenshot_as_png()
            image_stream = io.BytesIO(bytes_png)
            pillow_img = Image.open(image_stream)
            return cls._image_resize(pillow_img)
        else:
            if region is None:
                region = cls.get_screenshot_region(title)
            pillow_img = pyscreeze.screenshot(region=region)
            # pillow_img.show()
            return cls._image_resize(pillow_img)
            # return pillow_img

    @classmethod
    def _image_resize(cls, pillow_image: Image.Image) -> Image.Image:
        if pillow_image.width == 1920:
            return pillow_image
        cls.screenshot_proportion = 1920 / pillow_image.width
        resized_image = pillow_image.resize(
            (int(pillow_image.width * cls.screenshot_proportion),
             int(pillow_image.height * cls.screenshot_proportion)),
            Image.BICUBIC)
        # resized_image.show()
        return resized_image

    @classmethod
    def _location_calculator(cls, x, y):
        if cls.cloud:
            html = cls.web_driver.find_element(By.TAG_NAME, "html")
            width = html.size["width"]
            cls.location_proportion = width / 1920
            return x * cls.location_proportion, y * cls.location_proportion
        else:
            cls.location_proportion = 1 / cls.screenshot_proportion
            return x * cls.location_proportion + cls.area_left, y * cls.location_proportion + cls.area_top
            # return x, y

    @classmethod
    def _locate(cls, img_path: str, title="崩坏：星穹铁道"):
        try:
            img = cv2.imread(img_path)
            if img is None:
                raise FileNotFoundError("无法找到或读取文件 " + img_path)
            if cls.cloud:
                location = pyscreeze.locate(img, cls.get_screenshot(), confidence=cls.confidence)
            else:
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
    def _locate_center(cls, img_path, x_add=0, y_add=0, title="崩坏：星穹铁道") -> tuple[int, int]:
        location = cls._locate(img_path, title)
        x, y = pyscreeze.center(location)
        x += x_add
        y += y_add
        x, y = cls._location_calculator(x, y)
        return x, y

    @classmethod
    def exist(cls, img_path, wait_time=2):
        """Determine if a situation exists.

        Args:
            img_path (str): Img path of the situation.
            wait_time (float): Waiting time before run_flag.
        Returns:
            True if existed, False otherwise.
        """
        time.sleep(wait_time)  # 等待游戏加载
        try:
            cls._locate(img_path)
            return True
        except Exception as e:
            logger.exception(e, is_fatal=True)
            return False

    @classmethod
    def check(cls, img_path: str, interval=0.5, max_time=40):
        """Detects whether the object appears on the screen.

        Args:
            img_path (str): Img path of object.
            interval (float): Interval between checks.
            max_time (int): Maximum number of check times.
        Returns:
            True if obj appeared, False if reach maximum times.
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
    def get_screen_center(cls):
        """Get the center of game window.

        Returns:
            tuple(x, y)
        """
        if cls.cloud:
            window_size = cls.web_driver.get_window_size()
            screen_width, screen_height = window_size.values()
            x, y = cls.area_left + screen_width // 2, cls.area_top + screen_height // 2
            return x, y
        else:
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
            img_path,
            x_add=0,
            y_add=0,
            wait_time=2.0,
            title="崩坏：星穹铁道"):
        """Click the corresponding image on the screen

        Args:
            img_path (str): Img path.
            x_add (int): X-axis offset(px).
            y_add (int): Y-axis offset(px).
            wait_time (float): Waiting time before run_flag(s).
            title (str): Window title.
        Returns:
            True if clicked successfully, False otherwise.
        """
        try:
            time.sleep(wait_time)
            logger.debug("点击对象" + img_path)
            x, y = cls._locate_center(img_path, x_add, y_add, title)
            if cls.cloud:
                action = ActionBuilder(cls.web_driver)
                action.pointer_action.move_to_location(x, y).click()
                action.perform()
                time.sleep(1)
            else:
                pyautogui.click(x, y)
            return True
        except Exception:
            logger.exception("点击对象时出错", is_fatal=True)
            return False

    @classmethod
    def click_point(cls, x: int | None, y: int | None) -> bool:
        try:
            if cls.cloud:
                x, y = cls._location_calculator(x, y)
                action = ActionBuilder(cls.web_driver)
                action.pointer_action.move_to_location(x, y).click()
                action.perform()
                time.sleep(1)
            else:
                pyautogui.click(x, y)
            return True
        except Exception:
            logger.exception("点击坐标时出错", is_fatal=True)
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
            if cls.cloud:
                key = cls._key_in_utf8(key)
                for i in range(presses):
                    ActionChains(cls.web_driver).send_keys(key).perform()
                    time.sleep(interval)
                time.sleep(1)
            else:
                pyautogui.press(key, presses=presses, interval=interval)
            return True
        except Exception:
            logger.exception("按下按键失败", is_fatal=True)
            return False

    @classmethod
    def press_key_for_a_while(cls, key: str, during: float = 0) -> bool:
        try:
            logger.debug("按下按键" + key)
            if cls.cloud:
                key = cls._key_in_utf8(key)
                ActionChains(cls.web_driver).key_down(key).perform()
                time.sleep(during)
                ActionChains(cls.web_driver).key_up(key).perform()
            else:
                pyautogui.keyDown(key)
                time.sleep(during)
                pyautogui.keyUp(key)
            return True
        except Exception:
            logger.exception("按下按键失败", is_fatal=True)
            return False

    @staticmethod
    def _key_in_utf8(key):
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
        try:
            if cls.cloud:
                ActionChains(cls.web_driver).send_keys(content).perform()
            else:
                pyautogui.write(content)
            return True
        except Exception:
            logger.exception("输入时发生错误", is_fatal=True)
            return False

    @classmethod
    def moveRel(cls, x_offset: int, y_offset: int) -> bool:
        try:
            if cls.cloud:
                x_offset, y_offset = cls._location_calculator(x_offset, y_offset)
                ActionChains(cls.web_driver).move_by_offset(x_offset, y_offset).perform()
            else:
                pyautogui.moveRel(x_offset, y_offset)
            return True
        except Exception:
            logger.exception("移动光标时出错", is_fatal=True)
            return False

    @classmethod
    def find_level(cls, level: str) -> bool:
        """Fine battle level

        Returns:
            True if found.
        """
        x, y = cls.get_screen_center()
        if cls.cloud:
            action = ActionBuilder(cls.web_driver)
            action.pointer_action.move_to_location(x, y)
            action.perform()
        else:
            pyautogui.moveTo(x - 200, y)
        times = 0
        while True:
            times += 1
            if times == 60:
                return False
            if cls.exist(level, wait_time=0.5):
                return True
            else:
                cls.scroll(-5)

    @classmethod
    def scroll(cls, distance: int) -> bool:
        try:
            if cls.cloud:
                ActionChains(cls.web_driver).click_and_hold().perform()
                ActionChains(cls.web_driver).move_by_offset(0, -20).perform()
                ActionChains(cls.web_driver).release().perform()
                time.sleep(0.2)
                ActionChains(cls.web_driver).move_by_offset(0, 20).perform()
                time.sleep(0.2)
            else:
                pyautogui.scroll(distance)
            return True
        except Exception:
            logger.exception("指针滚动时发生错误", is_fatal=True)
            return False

    @classmethod
    def wait_battle_end(cls):
        """Wait battle end

        Returns:
            True if battle end.
        """
        logger.info("等待战斗结束")
        quit_battle = cv2.imread("res/img/quit_battle.png")
        while True:
            time.sleep(0.2)
            try:
                if cls.cloud:
                    pyautogui.locate(quit_battle, cls.get_screenshot(), confidence=cls.confidence)
                else:
                    pyautogui.locate(quit_battle, cls.get_screenshot("崩坏：星穹铁道"), confidence=cls.confidence)
                logger.info("战斗结束")
                return True
            except pyautogui.ImageNotFoundException:
                continue
            except pyscreeze.PyScreezeException:
                continue

    @classmethod
    def copy(cls, text:str):
        """
        Copy the text to clipboard

        Args:
            text:

        Returns:
            Any
        """
        return pyperclip.copy(text)

    @classmethod
    def paste(cls):
        pyautogui.keyDown("ctrl")
        pyautogui.keyDown("v")
        pyautogui.keyUp("v")
        pyautogui.keyUp("ctrl")
