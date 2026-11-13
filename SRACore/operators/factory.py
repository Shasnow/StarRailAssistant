import enum
import os
import platform
import sys
import threading
from pathlib import Path

from loguru import logger
from rapidocr import RapidOCR

from SRACore.models.app_settings import AppSettings
from SRACore.operators.ioperator import IOperator
from SRACore.operators.model import WindowContext
from SRACore.util.const import AppRootDir

# onnxruntime 依赖的 VC++ 运行库 DLL
VC_RUNTIME_DLLS = ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll")


def _missing_vc_runtime_dlls() -> list[str]:
    """检查 onnxruntime 依赖的 VC++ 运行库 DLL 是否缺失"""
    search_dirs = [
        Path(sys.base_prefix),
        AppRootDir / 'python',
        Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32',
    ]
    return [dll for dll in VC_RUNTIME_DLLS if not any((folder / dll).exists() for folder in search_dirs)]


class OperatorType(enum.StrEnum):
    Local = "Local"
    Browser = "Browser"


class OperatorFactory:
    # noinspection bad-assignment
    __ocr_instance: RapidOCR = None  # pyright: ignore[reportAssignmentType]
    __window_context = WindowContext()

    @classmethod
    def get_operator(cls, optype: str | OperatorType = OperatorType.Local, settings: AppSettings | None = None,
                     stop_event: threading.Event | None = None) -> IOperator:
        if optype == OperatorType.Local:
            from SRACore.operators.operator import Operator
            __instance = Operator(ocr_engine=cls.get_ocr_instance(), settings=settings or AppSettings.from_dict({}),
                                  stop_event=stop_event, window_context=cls.__window_context)
        elif optype == OperatorType.Browser:
            from SRACore.operators.browser_operator import BrowserOperator
            __instance = BrowserOperator(ocr_engine=cls.get_ocr_instance(), settings=settings or AppSettings.from_dict({}),
                                         stop_event=stop_event, window_context=cls.__window_context)
        else:
            raise ValueError(f"Unknown operator type: {optype}")
        return __instance

    @classmethod
    def get_ocr_instance(cls) -> RapidOCR:
        if cls.__ocr_instance is None:
            config_path = AppRootDir / 'rapidocr' / 'config.yaml'
            if not config_path.exists():
                config_path = None
            try:
                cls.__ocr_instance = RapidOCR(config_path=config_path, params={"Global.log_level": "error"})  # pyright: ignore[reportArgumentType]
            except (ImportError, OSError) as error:
                # onnxruntime 是二进制依赖，加载失败基本是运行环境问题，给出可自查的提示而不是原始堆栈
                logger.error(f"OCR 引擎初始化失败：{error}")
                logger.error(f"运行环境：Python {platform.python_version()} ({platform.machine()})，{sys.executable}")
                missing = _missing_vc_runtime_dlls()
                if missing:
                    logger.error(f"缺少 VC++ 运行库 DLL：{', '.join(missing)}")
                else:
                    logger.error("VC++ 运行库 DLL 齐全，常见原因是杀毒软件拦截 DLL 注入或系统运行库版本过旧")
                raise RuntimeError("OCR 引擎初始化失败",
                               "请安装或修复 Microsoft Visual C++ 2015-2022 运行库（x64），"
                               "并关闭杀毒软件的注入/沙箱功能后重启程序") from error
        # noinspection bad-return
        return cls.__ocr_instance
