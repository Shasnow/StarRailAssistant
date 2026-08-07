import enum
import threading

from rapidocr import RapidOCR

from SRACore.models.app_settings import AppSettings
from SRACore.operators.ioperator import IOperator
from SRACore.util.const import AppRootDir


class OperatorType(enum.StrEnum):
    Local = "Local"
    Browser = "Browser"


class OperatorFactory:
    __ocr_instance: RapidOCR = None  # pyright: ignore[reportAssignmentType]

    @classmethod
    def get_operator(cls, optype: str | OperatorType, settings: AppSettings,
                     stop_event: threading.Event | None = None) -> IOperator:
        if optype == OperatorType.Local:
            from SRACore.operators.operator import Operator
            __instance = Operator(ocr_engine=cls.get_ocr_instance(), settings=settings,
                                  stop_event=stop_event)
        elif optype == OperatorType.Browser:
            from SRACore.operators.browser_operator import BrowserOperator
            __instance = BrowserOperator(ocr_engine=cls.get_ocr_instance(), settings=settings,
                                         stop_event=stop_event)
        else:
            raise ValueError(f"Unknown operator type: {optype}")
        return __instance

    @classmethod
    def get_ocr_instance(cls) -> RapidOCR:
        if cls.__ocr_instance is None:
            config_path = AppRootDir / 'rapidocr' / 'config.yaml'
            if not config_path.exists():
                config_path = None
            cls.__ocr_instance = RapidOCR(config_path=config_path, params={"Global.log_level": "error"})  # pyright: ignore[reportArgumentType]
        # noinspection bad-return
        return cls.__ocr_instance
