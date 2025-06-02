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
import time

import cv2
import pyautogui
import pygetwindow
import pyscreeze
from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtWidgets import QApplication

from SRACore.utils.Logger import logger


def exist(img_path, wait_time=2):
    """Determine if a situation exists.

    Args:
        img_path (str): Img path of the situation.
        wait_time (int): Waiting time before run_flag.
    Returns:
        True if existed, False otherwise.
    """
    time.sleep(wait_time)
    try:
        img = cv2.imread(img_path)
        if img is None:
            raise FileNotFoundError("无法找到或读取文件 " + img_path + ".png")
        pyautogui.locateOnWindow(img, "崩坏：星穹铁道", confidence=0.90)
        return True
    except pyautogui.ImageNotFoundException:
        return False
    except FileNotFoundError as e:
        logger.exception(e)
        return False
    except ValueError:
        logger.exception("窗口未激活")
        return False


class PlotListener(QThread):
    plot_start = Signal()
    plot_end = Signal()
    interrupted = Signal()
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
                if exist("res/img/dialog.png", wait_time=self.wait_time):
                    self.in_plot_flag = True
                    self.plot_start.emit()
                else:
                    if self.in_plot_flag:
                        self.in_plot_flag = False
                        self.plot_end.emit()
            except pygetwindow.PyGetWindowException:
                logger.error("窗口未激活")
                self.stop()
            except pyscreeze.PyScreezeException:
                logger.error("未能找到窗口")
                self.stop()
                self.interrupted.emit()
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
                if exist("res/img/continue.png", wait_time=1):
                    pyautogui.press("space")
                for i in range(4,0,-1):
                    if exist(f"res/img/{i}.png", wait_time=0):
                        pyautogui.press(str(i))
                        break
            except pygetwindow.PyGetWindowException:
                logger.error("窗口未激活")
                self.event_stop()
            except pyscreeze.PyScreezeException:
                logger.error("未能找到窗口")
                self.event_stop()


class Main(QObject):
    interrupted = Signal()
    def __init__(self):
        super().__init__()
        try:
            self.listener_thread = PlotListener()
            self.play_thread = AutoPlot()
            self.listener_thread.plot_start.connect(self.play_thread_start)
            self.listener_thread.plot_end.connect(self.play_thread_stop)
            self.listener_thread.interrupted.connect(lambda : self.interrupted.emit())
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
