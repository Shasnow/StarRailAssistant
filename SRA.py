#   <StarRailAssistant:An automated program that helps you complete daily tasks of StarRail.>
#   Copyright © <2024> <Shasnow>

#   This file is part of StarRailAssistant.

#   StarRailAssistant is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the Free Software Foundation,
#   either version 3 of the License, or (at your option) any later version.

#   StarRailAssistant is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#   without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#   See the GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License along with StarRailAssistant.
#   If not, see <https://www.gnu.org/licenses/>.

#   yukikage@qq.com

"""
崩坏：星穹铁道助手
作者：雪影
图形化界面及程序主入口
"""

import ctypes
import traceback

import sys
import time
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
)  # 从 PySide6 中导入所需的类

from SRACore.core.SRAssistant import VERSION
from SRACore.utils import Configure
from SRACore.utils.Dialog import (
    ExceptionMessageBox
)
from SRACore.utils.Plugins import PluginManager
from SRACore.utils.SRAWidgets import (
    SystemTray, Hotkey, Main, )

# from ocr import SRAocr

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SRA")  # 修改任务栏图标

class SRA(QMainWindow):
    def __init__(self):
        super().__init__()

        self.system_tray=SystemTray(self)
        self.system_tray.show()
        self.main = Main(self)
        self.setCentralWidget(self.main.ui)
        self.setWindowIcon(QIcon(self.main.AppPath + "/res/SRAicon.ico"))
        self.setWindowTitle(f"SRA v{VERSION} | {PluginManager.getPluginsCount()}个插件已加载")
        size = list(map(int, self.main.globals["Settings"]["uiSize"].split("x")))
        location = list(map(int, self.main.globals["Settings"]["uiLocation"].split("x")))
        self.setGeometry(
            location[0], location[1], size[0], size[1]
        )  # 设置窗口大小与位置
        self.keyboard_listener()

    def keyboard_listener(self):
        self.hotkey=Hotkey(self.main.globals["Settings"]["hotkeys"])
        self.hotkey.start()
        self.hotkey.startOrStop.connect(self.start_status_switch)
        self.hotkey.showOrHide.connect(self.show_or_hide)
        QApplication.instance().aboutToQuit.connect(self.hotkey.stop)

    def start_status_switch(self):
        if self.main.isRunning:
            self.main.kill()
        else:
            self.main.execute()

    def show_or_hide(self):
        self.system_tray.activated.emit(self.system_tray.ActivationReason.Trigger)

    def closeEvent(self, event):
        """Save the window info"""
        # 保存窗口大小与位置
        self.main.globals["Settings"][
            "uiSize"
        ] = f"{self.geometry().width()}x{self.geometry().height()}"
        self.main.globals["Settings"][
            "uiLocation"
        ] = f"{self.geometry().x()}x{self.geometry().y()}"
        Configure.save(self.main.globals, "data/globals.json")
        # 结束残余进程
        event.accept()
        if self.main.globals["Settings"]["exitWhenClose"]:
            QApplication.quit()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def exception_hook(exc_type: type, value):
    """全局异常捕获钩子"""
    try:
        msg_box = ExceptionMessageBox(exc_type.__name__, value, traceback.format_exc())
        msg_box.exec()
    except Exception:
        # 如果连 GUI 都无法启动
        with open("error.log", "w", encoding="utf-8") as file:
            file.write(f"{exc_type}:{value}:{traceback.format_exc()}")


def main():
    if is_admin():
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        start_time = time.time()
        window = SRA()
        window.show()
        end_time = time.time()
        total_time = end_time - start_time
        window.main.update_log(
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) +
            " 程序启动成功，耗时" + f"{total_time:.2f}s")
        version = Configure.load("version.json")
        if not version["Announcement.DoNotShowAgain"]:
            window.main.notice()
        sys.exit(app.exec())

    else:
        # 重新以管理员权限运行脚本
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        # 退出当前进程
        sys.exit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        exception_hook(type(e), e)
