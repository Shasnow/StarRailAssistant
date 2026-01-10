import dataclasses


@dataclasses.dataclass
class Region:
    """表示屏幕上的一个矩形区域

    例如，Region(0,0,0,0) 表示屏幕左上角的一个点
    """
    left: int
    top: int
    width: int
    height: int
    parent: 'Region | None' = None

    def __repr__(self):
        return f'Region(left={self.left}, top={self.top}, width={self.width}, height={self.height})'

    @property
    def tuple(self):
        """将Region转换为元组"""
        return self.left, self.top, self.width, self.height

    def sub_region(self, from_x: float, from_y: float, to_x: float, to_y: float) -> 'Region':
        """获取当前Region内的子区域"""
        new_left = self.left + int(self.width * from_x)
        new_top = self.top + int(self.height * from_y)
        new_width = int(self.width * (to_x - from_x))
        new_height = int(self.height * (to_y - from_y))
        return Region(new_left, new_top, new_width, new_height, parent=self)

@dataclasses.dataclass
class Box:
    """表示窗口内的一个矩形区域

    例如，Box(0,0,0,0) 表示窗口左上角的一个点
    """
    left: int
    top: int
    width: int
    height: int
    source: str | None = None

    @property
    def center(self):
        """获取Box的中心点坐标"""
        center_x = self.left + self.width // 2
        center_y = self.top + self.height // 2
        return center_x, center_y