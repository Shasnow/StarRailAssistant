import pyautogui
import cv2
from .Logger import logger
from ._types import Point
from ..Exceptions import StarRailException
import time

class ImageLocator:
    """
    获取屏幕上图像的位置
    """

    def __init__(self):
        self.log = logger

    def getLocation(self, image_path, x_add: int = 0, y_add: int = 0) -> Point:
        """
        获取屏幕上图像的位置
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                self.log.error("图片未找到")
                raise StarRailException("Image not found")
            location = pyautogui.locateOnWindow(img, "崩坏：星穹铁道", confidence=0.95)
            x , y = pyautogui.center(location) #type: ignore
            return x + x_add, y + y_add
        except Exception:
            self.log.exception("在尝试获取图像位置时发生错误", is_fatal=True)
            return 0.0, 0.0
        
    def checkOnWindow(self, image_path: str, waiting_time: float = 0.5, check_times: int = 1) -> bool:
        """
        检查图像是否在屏幕上
        """
        time.sleep(waiting_time)
        result = set()
        while True:
            if waiting_time > 0:
                try:
                    img = cv2.imread(image_path)
                    if img is None:
                        self.log.error("图片未找到")
                        raise StarRailException("Image not found")
                    location = pyautogui.locateOnWindow(img, "崩坏：星穹铁道", confidence=0.95)
                    if location is None:
                        result.add(False)
                    else:
                        result.add(True)
                except Exception:
                    self.log.exception("在尝试检查图像是否在屏幕上时发生错误", is_fatal=True)
                    return False
                finally:
                    waiting_time -= check_times
            else:
                if False not in result:
                    return True
                else:
                    return False