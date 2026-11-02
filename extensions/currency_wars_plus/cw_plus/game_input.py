"""仅本扩展的本地F/D使用物理扫描码，不修改宿主键表或系统布局。"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

from loguru import logger

from SRACore.util.errors import ThreadStoppedError


class _MouseInput(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _KeyInput(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


class _InputUnion(ctypes.Union):
    _fields_ = [("mi", _MouseInput), ("ki", _KeyInput)]


class _Input(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", wintypes.DWORD), ("data", _InputUnion)]


class GameKeyOperator:
    def __init__(self, operator):
        self._operator = operator

    def __getattr__(self, name):
        return getattr(self._operator, name)

    def _check_stop(self):
        event = getattr(self._operator, "stop_event", None)
        if event is not None and event.is_set():
            raise ThreadStoppedError("按键中断", "线程已停止")

    def press_key(self, key, presses=1, interval=0, wait=0, trace=True):
        if key not in ("f", "d"):
            return self._operator.press_key(key, presses=presses, interval=interval, wait=wait, trace=trace)
        self._check_stop()
        if wait:
            self.sleep(wait)
        scan = 0x21 if key == "f" else 0x20
        for _ in range(presses):
            self._check_stop()
            if not self._operator.is_window_active():
                logger.warning("[商店输入] 游戏窗口未激活，取消F/D，不抢占焦点")
                return False
            down = _Input(type=1, ki=_KeyInput(wVk=0, wScan=scan, dwFlags=0x0008))
            up = _Input(type=1, ki=_KeyInput(wVk=0, wScan=scan, dwFlags=0x0008 | 0x0002))
            accepted = ctypes.windll.user32.SendInput(1, (_Input * 1)(down), ctypes.sizeof(_Input))
            if accepted != 1:
                logger.warning(f"[商店输入] Windows未接受{key.upper()}按下事件")
                return False
            try:
                self._check_stop()
                self.sleep(0.05)  # 保持到游戏下一帧轮询，不能省成无间隔的按下/抬起。
            finally:
                released = ctypes.windll.user32.SendInput(1, (_Input * 1)(up), ctypes.sizeof(_Input))
                if released != 1:
                    # 仅重试安全抬起，绝不重放付费按下事件。
                    ctypes.windll.user32.SendInput(1, (_Input * 1)(up), ctypes.sizeof(_Input))
            self._check_stop()
            if released != 1:
                logger.warning(f"[商店输入] Windows未确认{key.upper()}抬起，停止本次输入")
                return False
            if trace:
                logger.debug(f"[商店输入] 已发送物理{key.upper()}，仍须核实画面结果")
            self._check_stop()
            if interval:
                self.sleep(interval)
        return True


def adapt_game_input(operator):
    if getattr(operator, "type", None) != "Local" or isinstance(operator, GameKeyOperator):
        return operator
    return GameKeyOperator(operator)
