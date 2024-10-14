from .Logger import logger
from .ImgLocator import ImageLocator
import pyautogui
import time

class ComputerOperator:

    def __init__(self) -> None:
        self.image_locator = ImageLocator()
        self.log = logger

    def _click(self, x: float, y: float) -> bool:
        """
        点击屏幕
        :param x: x坐标
        :param y: y坐标
        :return: 点击成功返回True，否则返回False
        """
        try:
            pyautogui.click(x, y)
            return True
        except Exception:
            self.log.exception("点击屏幕失败", is_fatal=False)
            return False

    def click_screen(self, img_path: str, x_offset: int = 0, y_offset: int = 0, waiting_time: float = 0.5) -> bool:
        """
        点击屏幕
        :param x_offset: x轴偏移量
        :param y_offset: y轴偏移量
        :param waiting_time: 执行前等待时间
        :param img_path: 图片路径
        :return: 点击成功返回True，否则返回False
        """
        time.sleep(waiting_time)
        logger.debug(f"点击屏幕：{img_path}")
        x , y = self.image_locator.GetLocation(img_path, x_offset, y_offset)
        logger.trace(f"坐标：{x}, {y}")
        if x == -1 or y == -1:
            logger.error(f"未找到图片：{img_path}")
            return False
        self._click(x, y)
        return True
    
    def move_mouse(self, x: float, y: float, duration: float = 0.5) -> bool:
        """
        移动鼠标
        :param x: x坐标
        :param y: y坐标
        :param duration: 持续时间
        :return: 移动成功返回True，否则返回False
        """
        logger.debug(f"移动鼠标：{x}, {y}")
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return True
        except Exception:
            self.log.exception("移动鼠标失败", is_fatal=False)
            return False
        
    def move_by_offset(self, x_offset: int, y_offset: int, duration: float = 0.5) -> bool:
        """
        移动鼠标
        :param x_offset: x偏移量
        :param y_offset: y偏移量
        :param duration: 持续时间
        :return: 移动成功返回True，否则返回False
        """
        logger.debug(f"移动鼠标：{x_offset}, {y_offset}")
        try:
            pyautogui.moveRel(x_offset, y_offset, duration=duration)
            return True
        except Exception:
            self.log.exception("移动鼠标失败", is_fatal=False)
            return False
    
    def press_key(self, key: str, presses: int = 1, interval: float = 0.1) -> bool:
        """
        按下按键

        :param key: 按键
        :param presses: 按下次数
        :param interval: 按键间隔时间(如果填入,程序会等待interval秒再按下按键)
        :return: 按键成功返回True，否则返回False
        """
        logger.debug(f"按下按键：{key}")
        try:
            pyautogui.press(key, presses=presses, interval=interval)
            return True
        except Exception:
            self.log.exception("按下按键失败", is_fatal=False)
            return False
        
    def write_on_screen(self, prompt: str, interval: float = 0.1, waiting_time: float = 0.5) -> bool:
        """
        在屏幕上输入文字

        :param prompt: 文字
        :param waiting_time: 执行前等待时间
        :param interval: 按键间隔时间(如果填入,程序会等待interval秒再输入文字)
        :return: 输入成功返回True，否则返回False
        """
        logger.debug(f"在屏幕上输入文字：{prompt}")
        try:
            pyautogui.write(prompt, interval=interval)
            time.sleep(waiting_time)
            return True
        except Exception:
            self.log.exception("在屏幕上输入文字失败", is_fatal=False)
            return False