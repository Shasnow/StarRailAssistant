"""仅为本扩展兼容 Windows 中文路径，不改变宿主的操作器与图片常量。"""
from collections import OrderedDict
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from .paths import RESOURCE_ROOT


def _private_template_path(template):
    if not isinstance(template, (str, Path)):
        return None
    path = Path(template).resolve()
    return path if path.is_relative_to(RESOURCE_ROOT.resolve()) else None


# Yukki：模板缓存按本扩展实际路径隔离。
def template_cache_key(template):
    """路径及文件版本共同失效；缺失文件仍按原读取路径明确报错。"""
    if not isinstance(template, (str, Path)):
        return None
    path = Path(template).resolve()
    stat = path.stat()
    return (str(path), stat.st_mtime_ns, stat.st_size, stat.st_ctime_ns, stat.st_ino)


@lru_cache(maxsize=64)
def _decoded_template(key, mode):
    from PIL import Image

    # 文件缺失或损坏须明确报错，不能被误当成页面未出现而反复等待。
    with Image.open(key[0]) as image:
        return image.convert(mode)


@lru_cache(maxsize=64)
def _scaled_template(key, mode, scale):
    image = _decoded_template(key, mode)
    if abs(scale - 1) > 0.001:
        image = image.resize((max(1, round(image.width * scale)),
                              max(1, round(image.height * scale))))
    return image


def load_template(template, *, mode="RGB", scale=1.0):
    """缓存自有图片的解码与原有缩放；返回副本，防止调用方改写缓存。"""
    path = _private_template_path(template)
    if path is None:
        return template
    return _scaled_template(template_cache_key(path), mode, scale).copy()


@lru_cache(maxsize=64)
def _match_template(key, grayscale, original):
    import pyscreeze

    source = (_decoded_template(key, "RGB") if _private_template_path(key[0]) is not None
              else original)
    # 直接复用 Pyscreeze 的 RGB→BGR/灰度规则，不引入另一套转换。
    return pyscreeze._load_cv2(source, grayscale)


def load_match_template(template, grayscale):
    """提供与 Pyscreeze 完全相同的匹配输入，文件改动后重新解码。"""
    key = template_cache_key(template)
    if key is None:
        import pyscreeze
        return pyscreeze._load_cv2(template, grayscale)
    return _match_template(key, grayscale, template).copy()


def locate_first(needle, haystack, *, confidence):
    """已转换数组的逐行首个匹配；不裁剪、不改变候选顺序或严格阈值。"""
    import cv2
    import numpy as np

    confidence = float(confidence)
    height, width = needle.shape[:2]
    if haystack.shape[0] < height or haystack.shape[1] < width:
        raise ValueError("needle dimension(s) exceed the haystack image or region dimensions")
    scores = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
    accepted = scores > confidence
    # 布尔 argmax 取 C 顺序的第一个 True；全 False 时仍需显式拒绝。
    # 仅省去 Pyscreeze 的全屏 int64 索引网格，不能改为最高分位置。
    y, x = np.unravel_index(accepted.argmax(), accepted.shape)
    return (x, y, width, height) if accepted[y, x] else None


class CachedOperatorOCR:
    """执行原宿主 OCR，只对相同模式、尺寸、完整像素缓存引擎输出。

    原宿主保留截图裁剪及舍入、默认灰度、严格置信度比较、诊断保存、
    trace 日志和异常处理；自定义 OCR 实现直接转交，不猜测其语义。
    """

    def __init__(self, operator):
        self._operator = operator
        self._engine = None
        self._pixel_cache = OrderedDict()

    def __getattr__(self, name):
        return getattr(self._operator, name)

    def ocr(self, from_x=None, from_y=None, to_x=None, to_y=None,
            grayscale=True, confidence=None, trace=True):
        from SRACore.operators.ioperator import IOperator

        method = self._operator.ocr
        args = dict(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y,
                    grayscale=grayscale, confidence=confidence, trace=trace)
        if getattr(method, "__func__", None) is not IOperator.ocr:
            return method(**args)
        return IOperator.ocr(self, **args)

    def ocr_engine(self, image, **kwargs):
        engine = self._operator.ocr_engine
        if engine is not self._engine:
            self._pixel_cache.clear()
            self._engine = engine
        key = None
        # 字节本身参与比较，避免摘要碰撞；32 个有界小裁剪不保留整屏图像。
        try:
            if (callable(getattr(image, "tobytes", None))
                    and 0 < image.width * image.height <= 300000):
                key = (image.mode, image.size, tuple(sorted(kwargs.items())), image.tobytes())
                if key in self._pixel_cache:
                    result = deepcopy(self._pixel_cache[key])
                    self._pixel_cache.move_to_end(key)
                    return result
        except Exception:
            # 缓存本身不可用时仍由原引擎执行，不改变宿主的成功/异常边界。
            key = None
        result = engine(image, **kwargs)
        if key is not None:
            try:
                self._pixel_cache[key] = deepcopy(result)
                self._pixel_cache.move_to_end(key)
                while len(self._pixel_cache) > 32:
                    self._pixel_cache.popitem(last=False)
            except Exception:
                self._pixel_cache.clear()
        return result


# ssyb：适配层转交原操作器，中文路径只在图片读取边界处理。
class UnicodeTemplateOperator:
    """共享原操作器的截图、输入和停止事件，只替换扩展图片的读取方式。"""

    def __init__(self, operator):
        self._operator = operator

    def __getattr__(self, name):
        return getattr(self._operator, name)

    def _check_stop(self):
        from SRACore.util.errors import ThreadStoppedError

        event = self.stop_event
        if event is not None and event.is_set():
            raise ThreadStoppedError("图像识别中断", "线程已停止")

    def sleep(self, seconds):
        self._check_stop()
        event = self.stop_event
        if event is None:
            self._operator.sleep(seconds)
        else:
            if seconds < 0:
                raise ValueError("等待时间不能小于零。")
            event.wait(seconds)
        self._check_stop()

    def _box(self, match, template, from_x, from_y):
        from SRACore.operators.model import Box

        left, top, width, height = match
        if from_x is not None and from_y is not None:
            left += int(from_x * self.window_context.width)
            top += int(from_y * self.window_context.height)
        # 页面分派仍依赖原路径字符串；不能把图像对象写进来源字段。
        return Box(left, top, width, height, source=str(template))

    def locate(self, template, *, from_x=None, from_y=None, to_x=None,
               to_y=None, confidence=None, trace=True):
        if _private_template_path(template) is None:
            return self._operator.locate(template, from_x=from_x, from_y=from_y,
                to_x=to_x, to_y=to_y, confidence=confidence, trace=trace)
        import pyscreeze
        from loguru import logger
        from SRACore.util.errors import ThreadStoppedError

        self._check_stop()
        image = load_template(template)
        match_confidence = self.tm_confidence if confidence is None else confidence
        try:
            frame = self.screenshot(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y)
            self._check_stop()
            match = pyscreeze.locate(image, frame, confidence=match_confidence)
            self._check_stop()
            if match is None:
                return None
            box = self._box(match, template, from_x, from_y)
            self.sleep(0.5)
            return box
        except ThreadStoppedError:
            raise
        except Exception as error:
            if trace:
                logger.trace(f"ImageNotFound: {template} -> {error}")
            return None

    def locate_all(self, template, *, from_x=None, from_y=None, to_x=None,
                   to_y=None, confidence=None, trace=True):
        if _private_template_path(template) is None:
            return self._operator.locate_all(template, from_x=from_x, from_y=from_y,
                to_x=to_x, to_y=to_y, confidence=confidence, trace=trace)
        import pyscreeze
        from loguru import logger
        from SRACore.util.errors import ThreadStoppedError

        self._check_stop()
        image = load_template(template)
        match_confidence = self.tm_confidence if confidence is None else confidence
        try:
            frame = self.screenshot(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y)
            self._check_stop()
            matches = pyscreeze.locateAll(image, frame, confidence=match_confidence)
            self.sleep(0.5)
            result = []
            for match in matches:
                self._check_stop()
                result.append(self._box(match, template, from_x, from_y))
            self._check_stop()
            return result
        except ThreadStoppedError:
            raise
        except Exception as error:
            if trace:
                logger.trace(f"ImageNotFound: {template} -> {error}")
            return None

    def locate_any(self, templates, *, from_x=None, from_y=None, to_x=None,
                   to_y=None, confidence=None, trace=True):
        if not any(_private_template_path(template) is not None for template in templates):
            return self._operator.locate_any(templates, from_x=from_x, from_y=from_y,
                to_x=to_x, to_y=to_y, confidence=confidence, trace=trace)
        import pyscreeze
        from loguru import logger
        from SRACore.util.errors import ThreadStoppedError

        self._check_stop()
        match_confidence = self.tm_confidence if confidence is None else confidence
        try:
            frame = self.screenshot(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y)
            self.sleep(0.5)
        except ThreadStoppedError:
            raise
        except Exception as error:
            logger.trace(f"Error taking screenshot: {error}")
            return -1, None
        for index, template in enumerate(templates):
            self._check_stop()
            if not Path(template).exists():
                raise FileNotFoundError(f"无法找到或读取文件 {template}")
            image = load_template(template)
            try:
                match = pyscreeze.locate(image, frame, confidence=match_confidence)
            except (pyscreeze.ImageNotFoundException, ValueError) as error:
                self._check_stop()
                if trace:
                    logger.trace(f"ImageNotFound: {template} -> {error}")
                continue
            self._check_stop()
            if match is not None:
                return index, self._box(match, template, from_x, from_y)
        return -1, None

    def click_img(self, template, x_offset=0, y_offset=0, after_sleep=0):
        from SRACore.operators.ioperator import IOperator

        self._check_stop()
        result = IOperator.click_img(self, template, x_offset, y_offset, after_sleep)
        self._check_stop()
        return result

    def wait_img(self, template, timeout=10, interval=0.5):
        import time
        from loguru import logger

        self._check_stop()
        start_time = time.time()
        logger.debug(f"Waiting for image: {template}")
        while time.time() - start_time < timeout:
            self._check_stop()
            box = self.locate(template)
            if box is not None:
                return box
            self.sleep(interval)
        self._check_stop()
        logger.debug(f"Timeout: {template} -> NotFound in {timeout} seconds")
        return None

    def wait_any_img(self, templates, timeout=10, interval=0.5, trace=True):
        import time
        from loguru import logger

        self._check_stop()
        start_time = time.time()
        while time.time() - start_time < timeout:
            self._check_stop()
            index, box = self.locate_any(templates, trace=trace)
            if index != -1:
                return index, box
            self.sleep(interval)
        self._check_stop()
        logger.debug(f"Timeout: {templates} -> NotFound in {timeout} seconds")
        return -1, None


def adapt_template_operator(operator):
    """仅接管官方默认识图接口，自定义操作器继续使用自己的实现。"""
    from SRACore.operators.ioperator import IOperator

    for name in ("locate", "locate_all", "locate_any"):
        original = getattr(IOperator, name, None)
        if not callable(original) or getattr(type(operator), name, None) is not original:
            return operator
    return UnicodeTemplateOperator(operator)
