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
import faulthandler
import os
import sys
import time
import traceback

from PySide6.QtWidgets import QApplication

from SRACore.utils import Configure

if not os.path.exists("log"):
    os.mkdir("log")
faulthandler.enable(open("log/crash.log","w",encoding="utf-8"))

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SRA")  # 修改任务栏图标


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def exception_hook(exc_type: type, value):
    """全局异常捕获钩子"""
    try:
        from SRACore.utils.Dialog import ExceptionMessageBox
        if QApplication.instance() is None:
            QApplication(sys.argv)
        msg_box = ExceptionMessageBox(exc_type.__name__, value, traceback.format_exc())
        msg_box.exec()
    except Exception as e:
        # 如果连 GUI 都无法启动
        with open("log/error.log", "w", encoding="utf-8") as file:
            file.write(f"{exc_type}:{value}:{traceback.format_exc()}\n"
                       f"During handle the exception, another exception occurred: {e}")


def main():
    if not is_admin():
        if len(sys.argv) > 1:
            print("必须以管理员身份运行终端，才能使用SRA命令行。")
            sys.exit()
        else:
            print("即将以管理员权限重新运行，请允许 UAC 提示。")
            # 重新以管理员权限运行脚本
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            # 退出当前进程
            sys.exit()

    if len(sys.argv) > 1:
        from SRACore.core.SRACommandLine import CommandLine
        if sys.argv[1] == "--cli":
            CommandLine().cmdloop()
        elif sys.argv[1] == "--run":
            CommandLine().do_run(" ".join(sys.argv[2:]))
        else:
            CommandLine().default(sys.argv[1])
    else:
        from SRACore.utils.SRAComponents import SRA
        from SRACore.utils.Plugins import PluginManager
        PluginManager.scan_plugins()
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
        PluginManager.load_plugins("late")
        sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        exception_hook(type(e), e)
