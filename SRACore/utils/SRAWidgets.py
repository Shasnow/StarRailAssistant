from PySide6.QtCore import Signal, QPropertyAnimation, QEasingCurve, Property, QRect
from PySide6.QtGui import QColor, Qt, QPainter
from PySide6.QtWidgets import QWidget


class ToggleSwitch(QWidget):
    stateChanged = Signal(bool)  # 定义自定义信号用于状态变化

    def __init__(self, parent=None, on_color="#2196F3", off_color="#9E9E9E", bg_color="#e0e0e0"):
        super().__init__(parent)
        self.setFixedSize(48, 24)  # 设置固定大小
        self.is_on = False
        self.on_color = QColor(on_color)  # 开启状态颜色
        self.off_color = QColor(off_color)  # 关闭状态颜色
        self.bg_color = QColor(bg_color)  # 背景颜色
        self.knob_size = 18  # 滑块大小
        self.setCursor(Qt.CursorShape.PointingHandCursor)  # 鼠标悬停时显示手型光标

        # 初始化动画
        self._knob_x = 5 if not self.is_on else self.width() - self.knob_size - 5
        self.animation = QPropertyAnimation(self, b"knob_x", self)
        self.animation.setDuration(200)  # 动画持续时间 200 毫秒
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)  # 使用缓入缓出曲线

    def getKnobX(self):
        """获取滑块 X 坐标"""
        return self._knob_x

    def setKnobX(self, value):
        """设置滑块 X 坐标并触发更新"""
        self._knob_x = value
        self.update()

    knob_x = Property(int, fget=getKnobX, fset=setKnobX)  # 定义可动画化的属性

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # 启用抗锯齿

        # 绘制背景
        bg_rect = QRect(0, 0, self.width(), self.height())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.bg_color)
        painter.drawRoundedRect(bg_rect, self.height() // 2, self.height() // 2)  # 圆角背景

        # 绘制滑块
        knob_rect = QRect(self._knob_x, (self.height() - self.knob_size) // 2, self.knob_size, self.knob_size)
        painter.setBrush(self.on_color if self.is_on else self.off_color)
        painter.drawRoundedRect(knob_rect, self.knob_size // 2, self.knob_size // 2)  # 圆角滑块

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_on = not self.is_on
            self.stateChanged.emit(self.is_on)  # 发出状态变化信号
            self.animateSwitch()  # 启动动画

    def animateSwitch(self):
        """启动动画以平滑过渡滑块位置"""
        target_x = self.width() - self.knob_size - 5 if self.is_on else 5
        self.animation.setStartValue(self._knob_x)
        self.animation.setEndValue(target_x)
        self.animation.start()  # 开始动画

    def isOn(self):
        return self.is_on

    def setOn(self, state):
        self.is_on = state
        self.animateSwitch()  # 设置状态时也启动动画
        self.stateChanged.emit(self.is_on)  # 发出状态变化信号

    def sizeHint(self):
        return self.size()  # 返回固定大小