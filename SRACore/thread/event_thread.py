import dataclasses
import threading
import time
from loguru import logger
from threading import Lock
from typing import Callable, Optional, Any
import pynput


@dataclasses.dataclass
class KeyDownEvent:
    key: str
    callback: Callable
    args: Any = None
    is_triggered: bool = False  # 防抖标记

class EventListener:
    # 退出信号：控制监听器线程退出
    exit_event = threading.Event()
    # 按键回调列表：(按键字符串, 回调函数, 是否已触发防抖)
    _key_down_events: dict[str, KeyDownEvent] = {}
    # 线程锁：保证多线程操作_key_down_events的安全性
    _lock = Lock()
    # 监听器线程实例
    _listener_thread: Optional[threading.Thread] = None

    def register_key_event(self, key: str, callback: Callable, args) -> None:
        """
        注册按键按下事件（线程安全）
        :param key: 按键字符串（如 'a'、'enter'、'ctrl'）
        :param callback: 按键按下时的回调函数（无参数）
        :param args: 回调函数的参数
        """
        with self._lock:
            # 先移除同名按键，避免重复注册
            self._key_down_events[key] = KeyDownEvent(key=key, callback=callback, args=args)

    def unregister_key_event(self, key: str) -> None:
        """注销指定按键的事件（线程安全）"""
        with self._lock:
            if key in self._key_down_events:
                del self._key_down_events[key]

    def _listener_loop(self) -> None:
        """监听器核心循环（内部方法，不直接调用）"""

        # 映射pynput的按键名称到字符串（适配原keyboard库的命名习惯）
        def _key_to_str(key) -> str:
            try:
                return key.char  # 普通按键（a、1、空格等）
            except AttributeError:
                return str(key).split('.')[-1]  # 特殊按键（enter、ctrl等）

        # 监听按键按下事件
        def on_press(key):
            if self.exit_event.is_set():
                return  # 退出监听
            key_str = _key_to_str(key)

            with self._lock:
                event = self._key_down_events.get(key_str)
                if event is None or event.is_triggered:
                    return
                # 标记为已触发，防止重复触发
                event.is_triggered = True
                # 调用回调函数
                try:
                    event.callback(event.args)
                except Exception as e:
                    logger.error(f"回调执行失败 (按键={key_str}): {e}")

        # 监听按键释放事件（重置防抖标记）
        def on_release(key):
            if self.exit_event.is_set():
                return
            key_str = _key_to_str(key)

            with self._lock:
                event = self._key_down_events.get(key_str)
                if event:
                    event.is_triggered = False

        # 启动pynput监听（阻塞式，直到exit_event被设置）
        with pynput.keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            while not self.exit_event.is_set():
                if not listener.is_alive():
                    break
                time.sleep(0.1)  # 降低CPU占用

    def start(self) -> None:
        """启动事件监听器（独立子线程，不阻塞主线程）"""
        if self._listener_thread and self._listener_thread.is_alive():
            logger.info("event listener is already running")
            return

        # 重置退出事件
        self.exit_event.clear()
        # 启动独立子线程
        self._listener_thread = threading.Thread(
            target=self._listener_loop,
            daemon=True  # 守护线程，主线程退出时自动终止
        )
        self._listener_thread.start()
        logger.debug("event listener started")

    def stop(self) -> None:
        """停止事件监听器"""
        self.exit_event.set()
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1)
            self._listener_thread = None
        logger.debug("event listener stopped")