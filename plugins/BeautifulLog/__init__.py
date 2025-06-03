from PySide6.QtWidgets import QApplication, QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget, QFrame, QTextBrowser
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import QRegularExpression
import sys
from dataclasses import dataclass

from SRACore.utils.Dialog import MessageBox
from SRACore.utils.Plugins import PluginManager

import winreg


def is_dark_mode():
    try:
        # 打开注册表键
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        # 读取AppsUseLightTheme值
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        # 如果值为0，则表示深色模式
        return value == 0
    except WindowsError:
        return False


@dataclass
class LogTheme:
    """ 日志主题 """
    time_format: str
    time_color: QColor
    time_font: QFont
    log_colors: dict[str, QColor]
    log_fonts: dict[str, QFont]
    all_log_levels: list[str]


class LogHighlighter(QSyntaxHighlighter):
    def __init__(self, parent, theme: LogTheme):
        super().__init__(parent)
        self.theme = theme
        self.formats = self._create_formats()

    def _create_formats(self):
        """
        根据主题创建高亮格式
        """
        formats = {}
        for level in self.theme.all_log_levels:
            fmt = QTextCharFormat()
            fmt.setForeground(self.theme.log_colors.get(level, QColor("white")))
            fmt.setFont(self.theme.log_fonts.get(level, QFont()))
            formats[level] = fmt

        time_format = QTextCharFormat()
        time_format.setForeground(self.theme.time_color)
        time_format.setFont(self.theme.time_font)
        formats['TIME'] = time_format

        return formats

    def highlightBlock(self, text: str):
        # Highlight log levels
        for level in self.theme.all_log_levels:
            expression = QRegularExpression(rf"\b{level}\b")
            i = expression.globalMatch(text)
            while i.hasNext():
                match = i.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), self.formats[level])

        # Highlight timestamps
        time_regex = QRegularExpression(self.theme.time_format)
        i = time_regex.globalMatch(text)
        while i.hasNext():
            match = i.next()
            self.setFormat(match.capturedStart(), match.capturedLength(), self.formats['TIME'])


class LogViewer(QPlainTextEdit):
    def __init__(self, theme: LogTheme, styleSheet: str = None):
        super().__init__()
        self.setReadOnly(True)
        # self.setStyleSheet(styleSheet)
        self.highlighter = LogHighlighter(self.document(), theme)

    def append_log(self, text: str):
        self.appendPlainText(text)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


if is_dark_mode():
    theme = LogTheme(
        time_format=r"\b\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\b",
        time_color=QColor("#BD93F9"),
        time_font=QFont("Consolas", 14, QFont.Weight.Bold),
        log_colors={
            "ERROR": QColor("#FF5555"),
            "FATAL": QColor("#AA0000"),
            "WARNING": QColor("#F1FA8C"),
            "WARN": QColor("#F1FA8C"),
            "INFO": QColor("#8BE9FD"),
            "DEBUG": QColor("#50FA7B")
        },
        log_fonts={
            "ERROR": QFont("Consolas", 14, QFont.Weight.Bold),
            "FATAL": QFont("Consolas", 14, QFont.Weight.Bold),
            "WARNING": QFont("Consolas", 14, QFont.Weight.Bold),
            "WARN": QFont("Consolas", 14, QFont.Weight.Bold),
            "INFO": QFont("Consolas", 14),
            "DEBUG": QFont("Consolas", 14)
        },
        all_log_levels=["ERROR", "FATAL", "WARNING", "WARN", "INFO", "DEBUG"]
    )
    style_sheet = """
            QPlainTextEdit {
                background: #282A36;
                color: #F8F8F2;
                font-family: Consolas, 'Fira Mono', 'Courier New', monospace;
                font-size: 16px;
                border: none;
            }
        """
else:
    theme = LogTheme(
        time_format=r"\b\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\b",
        time_color=QColor("#6BCC62"),
        time_font=QFont("Consolas", 14, QFont.Weight.Bold),
        log_colors={
            "ERROR": QColor("#CC0000"),
            "FATAL": QColor("#AA0000"),
            "WARNING": QColor("#FF9900"),
            "WARN": QColor("#FF9900"),
            "INFO": QColor("#0066CC"),
            "DEBUG": QColor("#009933")
        },
        log_fonts={
            "ERROR": QFont("Consolas", 14, QFont.Weight.Bold),
            "FATAL": QFont("Consolas", 14, QFont.Weight.Bold),
            "WARNING": QFont("Consolas", 14, QFont.Weight.Bold),
            "WARN": QFont("Consolas", 14, QFont.Weight.Bold),
            "INFO": QFont("Consolas", 14),
            "DEBUG": QFont("Consolas", 14)
        },
        all_log_levels=["ERROR", "FATAL", "WARNING", "WARN", "INFO", "DEBUG"]
    )

    style_sheet = """
        QPlainTextEdit {
            background: #F3F3F3;
            color: #000000;
            font-family: Consolas, 'Fira Mono', 'Courier New', monospace;
            font-size: 16px;
            font-weight: bold;
        }
    """


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("现代终端日志显示")
        self.resize(800, 500)
        self.viewer = LogViewer(theme, style_sheet)
        layout = QVBoxLayout()
        layout.addWidget(self.viewer)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 示例日志
        self.viewer.append_log("2024-06-01 12:34:56 INFO 启动应用程序")
        self.viewer.append_log("2024-06-01 12:35:00 WARN 配置文件缺失，使用默认值")
        self.viewer.append_log("2024-06-01 12:35:05 ERROR 无法连接到数据库")
        self.viewer.append_log("2024-06-01 12:35:10 DEBUG 进入调试模式")
        self.viewer.append_log("2024-06-01 12:35:10 FATAL 致命错误，无法继续运行程序...")

if __name__ != "__main__":
    NAME = "更漂亮的日志"
    VERSION = "1.0.0"
    DESCRIPTION = "这个插件提供了一个现代化的终端日志显示，支持多种日志级别的高亮显示。"
    AUTHOR = "雪影、幽幽子"
    UI = PluginManager.public_ui
    ins = PluginManager.public_instance
    ins.log.setParent(None)
    ins.log.deleteLater()
    ins.log = LogViewer(theme,style_sheet)
    UI.findChild(QFrame, "frame3").layout().addWidget(ins.log)
    ins.update_log = ins.log.append_log
    ins.log.append = ins.log.append_log


def run():
    MessageBox.info(UI,"插件信息",f"{NAME} {VERSION}\n{DESCRIPTION}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
