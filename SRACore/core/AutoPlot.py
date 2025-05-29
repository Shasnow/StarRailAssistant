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
v0.7.0
作者：雪影
自动剧情
"""

import sys

import pyautogui
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication

from SRACore.utils.Logger import logger
from SRACore.utils.SRAOperator import SRAOperator


class PlotListener(QThread):
    plot_start = Signal()
    plot_end = Signal()
    wait_time=1

    def __init__(self):
        super().__init__()
        self.running_flag = True
        self.in_plot_flag = False

    def stop(self):
        self.running_flag = False

    def run(self):
        self.running_flag = True
        logger.info("监听，启动！")
        while self.running_flag:
            try:
                if SRAOperator.exist("res/img/dialog.png", wait_time=self.wait_time):
                    self.in_plot_flag = True
                    self.plot_start.emit()
                else:
                    if self.in_plot_flag:
                        self.in_plot_flag = False
                        self.plot_end.emit()
            except Exception as e:
                logger.exception(f"发生异常{e}")
                self.stop()
        logger.info("自动剧情已关闭")


class AutoPlot(QThread):
    def __init__(self):
        super().__init__()
        self.running_flag = False

    def event_stop(self):
        self.running_flag = False

    def event_start(self):
        self.running_flag = True
        self.start()

    def run(self):
        logger.info("自动播放运行中")
        while self.running_flag:
            try:
                if SRAOperator.exist("res/img/continue.png", wait_time=1):
                    pyautogui.press("space")
                for i in range(4,0,-1):
                    if SRAOperator.exist(f"res/img/{i}.png", wait_time=0):
                        pyautogui.press(str(i))
                        break
            except Exception as e:
                logger.exception(f"发生异常{e}")
                self.event_stop()


class Main:
    def __init__(self):
        try:
            self.listener_thread = PlotListener()
            self.play_thread = AutoPlot()
            self.listener_thread.plot_start.connect(self.play_thread_start)
            self.listener_thread.plot_end.connect(self.play_thread_stop)
        except Exception as e:
            logger.exception(e)

    def run_application(self):
        self.listener_thread.start()

    def quit_application(self):
        self.listener_thread.stop()
        self.play_thread.event_stop()

    def play_thread_start(self):
        self.listener_thread.wait_time=4
        self.play_thread.event_start()

    def play_thread_stop(self):
        logger.info("自动剧情停止")
        self.listener_thread.wait_time=1
        self.play_thread.event_stop()

if __name__ == "__main__":
    app=QApplication(sys.argv)
    main=Main()
    main.run_application()
    app.exec()
