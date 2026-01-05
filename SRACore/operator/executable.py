from SRACore.operator.ioperator import *


class Executable:
    def __init__(self, operator: IOperator):
        self.operator = operator
        self.settings = operator.settings

    @property
    def is_window_active(self) -> bool:
        return self.operator.is_window_active

    def get_win_region(self, active_window: bool | None = None, raise_exception: bool = True) -> Region | None:
        return self.operator.get_win_region(active_window, raise_exception)

    def screenshot(self, region: Region | None = None,
                   *,
                   from_x: float | None = None,
                   from_y: float | None = None,
                   to_x: float | None = None,
                   to_y: float | None = None) -> Image:
        """截取屏幕截图
        Args:
            region (Region | None, optional): 要截取的区域对象，包含left, top, width, height属性。
                如果为None，则默认截取当前活动窗口的区域。默认为None。
            from_x (float, optional): 起始点X坐标比例 (0-1)，相对于窗口左上角
            from_y (float, optional): 起始点Y坐标比例 (0-1)，相对于窗口左上角
            to_x (float, optional): 结束点X坐标比例 (0-1)，相对于窗口左上角
            to_y (float, optional): 结束点Y坐标比例 (0-1)，相对于窗口左上角
        Returns:
            PIL.Image.Image: 返回截取的屏幕区域图像对象
        Note:
            - 当region为None时，会自动获取活动窗口区域
            - 坐标比例是基于当前窗口区域计算的
            - 当传入完整的比例坐标时，region参数会被忽略
        Raises:
            ValueError: 如果坐标比例参数不完整或不在0-1范围内
        """
        return self.operator.screenshot(region, from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y)

    def locate_any(self,
                   templates: list[str],
                   region: Region | None = None,
                   *,
                   from_x: float | None = None,
                   from_y: float | None = None,
                   to_x: float | None = None,
                   to_y: float | None = None,
                   confidence: float | None = None,
                   trace: bool = True) -> tuple[int, Box | None]:
        """在窗口内查找任意一张图片位置
        Args:
            templates (list[str]): 模板图片路径列表
            region (Region | None, optional): 要查找的区域对象，包含left, top, width, height属性。
                如果为None，则默认查找当前活动窗口的区域。默认为None。
            from_x (float, optional): 起始点X坐标比例 (0-1)，相对于窗口左上角
            from_y (float, optional): 起始点Y坐标比例 (0-1)，相对于窗口左上角
            to_x (float, optional): 结束点X坐标比例 (0-1)，相对于窗口左上角
            to_y (float, optional): 结束点Y坐标比例 (0-1)，相对于窗口左上角
            confidence (float | None, optional): 匹配度, 0-1之间的浮点数, 默认为self.confidence
            trace (bool, optional): 是否打印调试信息。默认为True。
        Returns:
            tuple[int, Box | None]: 找到的图片索引和位置，如果未找到则返回-1和None
        Raises:
            ValueError: 如果坐标比例参数不完整或不在0-1范围内
        """
        return self.operator.locate_any(templates, region, from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y,
                                        confidence=confidence, trace=trace)

    def locate(self,
               template: str,
               region: Region | None = None,
               *,
               from_x: float | None = None,
               from_y: float | None = None,
               to_x: float | None = None,
               to_y: float | None = None,
               confidence: float | None = None,
               trace: bool = True) -> Box | None:
        """在窗口内查找图片位置

        Args:
            template (str): 模板图片路径
            region (Region | None, optional): 要查找的区域对象，包含left, top, width, height属性。
                如果为None，则默认查找当前活动窗口的区域。默认为None。
            from_x (float, optional): 起始点X坐标比例 (0-1), 相对于窗口左上角
            from_y (float, optional): 起始点Y坐标比例 (0-1), 相对于窗口左上角
            to_x (float, optional): 结束点X坐标比例 (0-1), 相对于窗口左上角
            to_y (float, optional): 结束点Y坐标比例 (0-1), 相对于窗口左上角
            confidence (float | None, optional): 匹配置信度阈值 (0-1), 如果为None则使用默认值。默认为None。
            trace (bool, optional): 是否打印调试信息。默认为True。
        Returns:
            Box | None: 找到的图片位置，如果未找到则返回None
        Raises:
            ValueError: 如果坐标比例参数不完整或不在0-1范围内
        """
        return self.operator.locate(template, region, from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y,
                                    confidence=confidence, trace=trace)

    def ocr(self,
            region: Region = None,
            *,
            from_x: float | None = None,
            from_y: float | None = None,
            to_x: float | None = None,
            to_y: float | None = None,
            trace: bool = True) -> list[Any] | None:
        """执行 OCR 文字识别

        Args:
            region (Region | None, optional): 要识别的区域对象，包含left, top, width, height属性。
                如果为None，则默认识别当前活动窗口的区域。默认为None。如果传入完整的比例坐标时，region参数会被忽略
            from_x (float, optional): 起始点X坐标比例 (0-1)，相对于窗口左上角
            from_y (float, optional): 起始点Y坐标比例 (0-1)，相对于窗口左上角
            to_x (float, optional): 结束点X坐标比例 (0-1
            to_y (float, optional): 结束点Y坐标比例 (0-1)，相对于窗口左上角
            trace (bool, optional): 是否打印调试信息。默认为True。
        Returns:
            list[Any] | None: OCR 引擎返回的原始结果。如果发生错误，返回None。
        Raises:
            ValueError: 如果坐标比例参数不完整或不在0-1范围内
        """
        return self.operator.ocr(region, from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y, trace=trace)

    def ocr_match(self,
                  text: str,
                  confidence=0.9,
                  region: Region = None,
                  *,
                  from_x: float | None = None,
                  from_y: float | None = None,
                  to_x: float | None = None,
                  to_y: float | None = None,
                  trace: bool = True) -> Box | None:
        return self.operator.ocr_match(text, confidence, region, from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y,
                                       trace=trace)

    def ocr_match_any(self,
                      texts: list[str],
                      confidence=0.9,
                      region: Region = None,
                      *,
                      from_x: float | None = None,
                      from_y: float | None = None,
                      to_x: float | None = None,
                      to_y: float | None = None,
                      trace: bool = True) -> tuple[int, Box | None]:
        return self.operator.ocr_match_any(texts, confidence, region, from_x=from_x, from_y=from_y, to_x=to_x,
                                           to_y=to_y, trace=trace)

    def wait_ocr(self, text: str, timeout: float = 10, interval: float = 0.2, confidence=0.9, *args,
                 **kwargs) -> Box | None:
        return self.operator.wait_ocr(text, timeout, interval, confidence, *args, **kwargs)

    def wait_ocr_any(self, texts: list[str], timeout: float = 10, interval: float = 0.2, confidence=0.9, *args,
                     **kwargs) -> tuple[int, Box | None]:
        return self.operator.wait_ocr_any(texts, timeout, interval, confidence, *args, **kwargs)

    def click_point(self, x: int | float, y: int | float, x_offset: int | float = 0, y_offset: int | float = 0,
                    after_sleep: float = 0, tag: str = "") -> bool:
        return self.operator.click_point(x, y, x_offset, y_offset, after_sleep, tag)

    def click_box(self, box: Box, x_offset: int | float = 0, y_offset: int | float = 0, after_sleep: float = 0) -> bool:
        return self.operator.click_box(box, x_offset, y_offset, after_sleep)

    def click_img(self, img_path: str, x_offset: int | float = 0, y_offset: int | float = 0,
                  after_sleep: float = 0) -> bool:
        return self.operator.click_img(img_path, x_offset, y_offset, after_sleep)

    def wait_img(self, img_path: str, timeout: int = 10, interval: float = 0.5) -> Box | None:
        return self.operator.wait_img(img_path, timeout, interval)

    def wait_any_img(self, img_paths: list[str], timeout: int = 10, interval: float = 0.2) -> tuple[int, Box | None]:
        return self.operator.wait_any_img(img_paths, timeout, interval)

    def press_key(self, key: str, presses: int = 1, interval: float = 0, wait: float = 0, trace: bool = True) -> bool:
        return self.operator.press_key(key, presses, interval, wait, trace)

    def hold_key(self, key: str, duration: float = 0) -> bool:
        return self.operator.hold_key(key, duration)

    def sleep(self, seconds) -> None:
        return self.operator.sleep(seconds)

    def copy(self, text: str) -> None:
        return self.operator.copy(text)

    def paste(self) -> str:
        """
        Paste the text from clipboard.
        :return: The text from clipboard.
        """
        return self.operator.paste()

    def move_rel(self, x_offset: int, y_offset: int) -> bool:
        return self.operator.move_rel(x_offset, y_offset)

    def move_to(self, x: int | float | None, y: int | float | None, duration: float = 0.0) -> bool:
        return self.operator.move_to(x, y, duration)

    def mouse_down(self, x: int | float | None, y: int | float | None) -> bool:
        return self.operator.mouse_down(x, y)

    def mouse_up(self, x: int | float | None = None, y: int | float | None = None) -> bool:
        return self.operator.mouse_up(x, y)

    def scroll(self, distance: int) -> bool:
        return self.operator.scroll(distance)

    def drag_to(self, from_x: int | float, from_y: int | float, to_x: int | float, to_y: int | float,
                duration: float = 0.5) -> bool:
        return self.operator.drag_to(from_x, from_y, to_x, to_y, duration)

    def do_while(self, action, condition, interval, max_iterations) -> bool:
        return self.operator.do_while(action, condition, interval, max_iterations)
