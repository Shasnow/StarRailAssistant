import math
import pyautogui

class LocateCalculator:
    """
    根据不同的分辨率计算坐标
    """
    def __init__(self, screen_size: tuple[int, int], location: tuple[int, int]) -> None:
        """
        初始化计算器
        :param screen_size: 当前屏幕的分辨率（宽, 高）
        :param location: 元素在基准分辨率下的位置（x, y）
        """
        self.screen_size = screen_size
        self.location = location

    def calculate(self, base_resolution: tuple[int, int] = (1920, 1080), x: int = 0, y: int = 0) -> tuple[int, int]:
        """
        根据屏幕分辨率和基准分辨率计算实际坐标
        :param base_resolution: 基准分辨率（宽, 高）
        :param x: 基准分辨率下的x坐标
        :param y: 基准分辨率下的y坐标
        :return: 实际坐标（x, y）
        """
        x_ratio = self.screen_size[0] / base_resolution[0]
        y_ratio = self.screen_size[1] / base_resolution[1]
        return (int(x * x_ratio) + self.location[0], int(y * y_ratio) + self.location[1])

    def calculate_distance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """
        计算两点之间的距离
        :param x1: 第一个点的x坐标
        :param y1: 第一个点的y坐标
        :param x2: 第二个点的x坐标
        :param y2: 第二个点的y坐标
        :return: 两点之间的距离
        """
        x_distance = x2 - x1
        y_distance = y2 - y1
        return math.sqrt(x_distance ** 2 + y_distance ** 2)

    def move_to(self, x: int, y: int) -> None:
        """
        移动鼠标到指定坐标
        :param x: 基准分辨率下的x坐标
        :param y: 基准分辨率下的y坐标
        """
        actual_x, actual_y = self.calculate(x=x, y=y)
        pyautogui.moveTo(actual_x, actual_y)