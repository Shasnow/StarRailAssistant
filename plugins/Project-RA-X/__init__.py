# MIT License
# Copyright (c) 2025 EveGlow
from ctypes import windll

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget

from SRACore.util.logger import log_emitter
from SRACore.util.operator import Operator


class TransparentLogWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.operator = Operator()
        self.setWindowTitle("透明日志")
        self.setGeometry(100, 100, 500, 200)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 设置窗口背景透明
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)  # 无边框窗口，保持最前显示，隐藏任务栏图标
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # 设置鼠标事件穿透
        # self.move(QApplication.primaryScreen().geometry().bottomLeft() - self.rect().bottomLeft() + QPoint(0, -300))  # 定位窗口到屏幕底部任务栏上方
        # 设置窗口无边框样式
        self.setStyleSheet("background-color: transparent; border: none;")

        # 初始化日志显示文本框
        self.log_view = QTextEdit(self)
        self.log_view.setStyleSheet("background-color: transparent; color: white;")  # 透明背景，白色文字
        self.log_view.setReadOnly(True)  # 只读模式
        self.log_view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  # 按窗口宽度自动换行
        self.log_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 禁用水平滚动条
        self.log_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 禁用垂直滚动条
        self.log_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 禁止文本框获取焦点
        self.log_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)  # 禁用右键菜单

        # 初始化自动定位定时器
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_location)
        self.timer.start()

        layout = QVBoxLayout(self)
        layout.addWidget(self.log_view)

        # 设置窗口不能进行点击操作
        hwnd = int(self.winId())
        ex_style = windll.user32.GetWindowLongW(hwnd, -20)
        windll.user32.SetWindowLongW(hwnd, -20, ex_style | 0x80000 | 0x20)

    def scroll_to_bottom(self):
        """自动滚动到文本框底部"""
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def update_log(self, msg):
        """
        更新日志显示内容

        参数:
            msg: 日志消息对象，包含level和message等信息
        """
        color_map = {
            "INFO": "#90EE90",
            "WARNING": "yellow",
            "ERROR": "red",
            "SUCCESS": "green",
            # "DEBUG": "lightblue" 测试可用
        }
        _, time, level, *message = msg.split(" ")
        if level.upper() not in ["INFO", "WARNING", "ERROR", "SUCCESS"]:
            return

        color = color_map.get(level.upper(), "white")
        # 构建带有阴影效果和颜色的HTML格式日志文本
        font_family = "Microsoft YaHei Mono, Consolas, monospace"
        html_text = (
            f'<div style="font-size:14px; font-weight:bold; font-family:\'{font_family}\'; '
            f'padding: 2px 6px;">'
            f'<span style="color:#D8BFD8">{time}</span> <span style="color:{color}">[{level}] </span> <span style="color:#7B68EE"> {"".join(message)}</span>'
            f'</div>'
        )
        self.log_view.append(html_text)
        self.scroll_to_bottom()

    def update_location(self):
        self.setVisible(self.operator.is_window_active)  # 检查游戏窗口是否激活
        self.operator.get_win_region(active_window=False, raise_exception=False)
        top = self.operator.top / self.operator.zoom
        left = self.operator.left / self.operator.zoom
        self.setGeometry(int(left), int(top + 450), 500, 200)

    def closeEvent(self, event):
        """
        窗口关闭事件处理

        参数:
            event: 关闭事件对象
        """
        print("窗口关闭，退出程序")
        event.accept()  # 接受关闭事件


if __name__ != "__main__":
    """作为插件运行时注册插件"""
    log_window = TransparentLogWindow()
    log_window.show()
    log_emitter.log_signal.connect(log_window.update_log)


def run():
    """空运行函数，保留接口"""
    pass


if __name__ == "__main__":
    """直接运行时的提示信息"""
    input("还没想好如何实现主窗口，但你可以键入'Enter'退出程序喵~")
