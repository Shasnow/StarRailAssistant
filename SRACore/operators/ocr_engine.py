"""可选 OCR execution provider；不改变模型、预处理或识别阈值。"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from loguru import logger
from rapidocr import RapidOCR
from rapidocr.inference_engine.base import FileInfo
from rapidocr.utils.typings import EngineType


class DirectMLOCR(RapidOCR):
    """保留原有 CPU 会话；仅将检测和识别交给 DirectML。"""

    def __init__(self, config_path, params):
        super().__init__(config_path=config_path, params=params)
        self._run_lock = threading.Lock()
        self._cpu_sessions = []
        self._enable_directml()

    def _enable_directml(self):
        import onnxruntime as ort

        pending = []
        try:
            for section, model in (("Det", self.text_det), ("Rec", self.text_rec)):
                cfg = self.cfg[section]
                if cfg.engine_type != EngineType.ONNXRUNTIME:
                    raise ValueError(f"{section}: only the ONNX Runtime backend supports DirectML")
                path = cfg.model_path
                if path is None:
                    info = model.session.get_model_url(FileInfo(
                        cfg.engine_type, cfg.ocr_version, cfg.task_type, cfg.lang_type, cfg.model_type))
                    path = Path(cfg.model_root_dir) / Path(info["model_dir"]).name
                # 使用独立 options，避免与 CPU 会话共享可变配置。
                cpu_options = model.session.session.get_session_options()
                options = ort.SessionOptions()
                for key in ("log_severity_level", "graph_optimization_level", "enable_cpu_mem_arena",
                            "intra_op_num_threads", "inter_op_num_threads"):
                    setattr(options, key, getattr(cpu_options, key))
                options.enable_mem_pattern = False
                options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                session = ort.InferenceSession(str(path), sess_options=options,
                                               providers=[("DmlExecutionProvider", {"device_id": 0}), "CPUExecutionProvider"])
                session.disable_fallback()
                if session.get_providers()[0] != "DmlExecutionProvider":
                    raise RuntimeError(f"{section}: selected {session.get_providers()}")
                pending.append((model, session, model.session.session))
        except Exception as exc:
            logger.warning("OCR: DirectML 初始化失败，保留 CPUExecutionProvider: {}", exc)
            return
        for model, session, cpu in pending:
            self._cpu_sessions.append((model, cpu))
            model.session.session = session
        logger.info("OCR: Det/Rec 使用 DmlExecutionProvider + CPUExecutionProvider；Cls 保持 CPU（常规 OCR 不调用分类器）。")

    def __call__(self, *args, **kwargs):
        from onnxruntime.capi.onnxruntime_pybind11_state import EPFail, Fail, RuntimeException
        from rapidocr.inference_engine.onnxruntime.main import ONNXRuntimeError

        # DirectML 禁止同一会话并发 Run；RapidOCR 的逐次参数也在此锁内。
        with self._run_lock:
            try:
                return super().__call__(*args, **kwargs)
            except ONNXRuntimeError as exc:
                if not self._cpu_sessions or not isinstance(exc.__cause__, (EPFail, Fail, RuntimeException)):
                    raise
                # 设备失败后停止整个 GPU pipeline，不继续使用另一模型的 DirectML 会话。
                for model, cpu in self._cpu_sessions:
                    model.session.session = cpu
                self._cpu_sessions.clear()
                logger.warning("OCR: DirectML 执行失败，使用 CPU 重试同一图像，此进程不再尝试 GPU: {}", exc.__cause__)
                return super().__call__(*args, **kwargs)


def create_ocr(config_path: Path | None) -> RapidOCR:
    provider = os.environ.get("SRA_OCR_PROVIDER", "").strip().lower()
    params = {"Global.log_level": "error"}
    if provider in {"cpu", "directml"}:
        for name in ("cuda", "dml", "cann", "coreml"):
            params[f"EngineConfig.onnxruntime.use_{name}"] = False
    if provider == "directml":
        import onnxruntime

        if sys.platform != "win32" or sys.maxsize <= 2**32 or sys.getwindowsversion().build < 18362:
            logger.warning("OCR: DirectML 需要 Windows x64 10 1903 或更新版本，使用 CPUExecutionProvider。")
        elif onnxruntime.__version__ != onnxruntime.get_version_string():
            logger.warning("OCR: ONNX Runtime Python/native 版本不一致（{} / {}），不启用 DirectML，使用 CPU。",
                           onnxruntime.__version__, onnxruntime.get_version_string())
        elif "DmlExecutionProvider" not in onnxruntime.get_available_providers():
            logger.warning("OCR: DirectML 不可用，使用 CPUExecutionProvider。")
        else:
            return DirectMLOCR(config_path, params)
    elif provider and provider != "cpu":
        logger.warning("OCR: 未知 SRA_OCR_PROVIDER={!r}，保留原有配置。", provider)
    return RapidOCR(config_path=config_path, params=params)
