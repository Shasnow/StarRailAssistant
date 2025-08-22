from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication


class SystemTray(QSystemTrayIcon):
    """系统托盘图标组件，提供快速访问主界面和退出应用的功能。"""

    def __init__(self, parent):
        super().__init__(QIcon("resources/SRAico.png"), parent)
        self.parent_object = parent
        self.setToolTip("SRA")
        right_click_menu = QMenu()  # 右键菜单
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        # 将action加入右键菜单
        right_click_menu.addAction("显示主界面", self.parent().show)
        right_click_menu.addAction(quit_action)
        self.setContextMenu(right_click_menu)  # 设置右键菜单
        self.activated.connect(self.active_handle)  # 激活事件处理

    @Slot(QSystemTrayIcon.ActivationReason)
    def active_handle(self, reason):
        """处理系统托盘图标的激活事件。"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.parent_object.isVisible():
                if self.parent_object.isMinimized():
                    self.parent_object.showNormal()
                else:
                    self.parent_object.showMinimized()
            else:
                self.parent_object.show()
