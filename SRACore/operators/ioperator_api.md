# SRACore 核心模块 API 文档

本文档涵盖 SRACore 的核心模块，包括屏幕操作、数据模型和任务框架。

---

## 目录

- [模块概述](#模块概述)
- [模块列表](#模块列表)
- [`operators.ioperator` 模块](#operatorsioperator-模块)
- [`operators.model` 模块](#operatorsmodel-模块)
- [`task` 模块](#task-模块)

---

## 模块概述

```
SRACore/
├── operators/
│   ├── ioperator.py      # 抽象操作器基类
│   ├── model.py          # 数据模型定义
│   ├── operator.py       # 操作器实现
│   └── browser_operator.py  # 浏览器操作器
└── task/
    └── __init__.py       # 任务框架
```

### 导入方式

```python
from SRACore.operators.ioperator import IOperator
from SRACore.operators.model import Box, Region
from SRACore.task import BaseTask, task, get_tasks
```

---

## 模块列表

| 模块名 | 说明 |
|--------|------|
| `operators.ioperator` | 屏幕操作模块的抽象基类，定义标准接口 |
| `operators.model` | 数据模型定义，包含 `Box` 和 `Region` 数据类 |
| `task` | 任务框架，提供任务基类和注册机制 |

---

## `operators.ioperator` 模块

`ioperator` 是屏幕操作模块的抽象基类，提供了图像识别、OCR文字识别、鼠标点击、按键操作等自动化控制功能。

### 类概述

```python
class IOperator(ABC)
```

`IOperator` 是一个抽象基类，定义了屏幕自动化操作的标准接口。开发者需要实现其抽象方法以适配不同的窗口平台（如 Windows、Mac 等）。

#### 初始化参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `stop_event` | `threading.Event \| None` | 停止线程事件，用于中断操作 |

#### 类属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `ocr_engine` | `RapidOCR \| None` | OCR 引擎单例实例 |

---

### IOperator 属性列表

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `type` | `str` | 操作器类型，默认值为 `"Local"` |
| `tm_confidence` | `float` | 模板匹配置信度阈值 |
| `ocr_confidence` | `float` | OCR 识别置信度阈值 |
| `top` | `int` | 窗口顶部坐标 |
| `left` | `int` | 窗口左侧坐标 |
| `width` | `int` | 窗口宽度 |
| `height` | `int` | 窗口高度 |
| `is_developer_mode` | `bool` | 是否启用开发者模式 |
| `is_save_ocr_image` | `bool` | 是否保存 OCR 图像（仅在开发者模式下有效） |
| `stop_event` | `threading.Event \| None` | 停止事件 |

---

### IOperator 抽象方法

#### `is_window_active() -> bool`

检查目标窗口是否为当前活动窗口。

#### `screenshot() -> Image`

截取屏幕截图。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `from_x` | `float \| None` | `None` | 起始点 X 坐标比例 (0-1) |
| `from_y` | `float \| None` | `None` | 起始点 Y 坐标比例 (0-1) |
| `to_x` | `float \| None` | `None` | 结束点 X 坐标比例 (0-1) |
| `to_y` | `float \| None` | `None` | 结束点 Y 坐标比例 (0-1) |

#### `click_point() -> bool`

点击指定坐标位置。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `x` | `int \| float` | - | X 坐标 |
| `y` | `int \| float` | - | Y 坐标 |
| `x_offset` | `int \| float` | `0` | X 偏移量 |
| `y_offset` | `int \| float` | `0` | Y 偏移量 |
| `after_sleep` | `float` | `0` | 点击后等待时间（秒） |
| `tag` | `str` | `""` | 日志标记 |
| `trace` | `bool` | `False` | 是否打印日志 |

#### `press_key() -> bool`

按下按键。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `key` | `str` | - | 按键名称 |
| `presses` | `int` | `1` | 按下次数 |
| `interval` | `float` | `0` | 按键间隔时间（秒） |
| `wait` | `float` | `0` | 首次按下前的等待时间（秒） |
| `trace` | `bool` | `True` | 是否打印调试信息 |

#### `hold_key() -> bool`

按住按键一段时间。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `key` | `str` | - | 按键名称 |
| `duration` | `float` | `0` | 按住时间（秒） |

#### `copy() -> None`

将文本复制到剪贴板。

#### `paste() -> None`

从剪贴板粘贴文本。

#### `move_rel() -> bool`

相对当前位置移动光标。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `x_offset` | `int` | X 轴偏移量 |
| `y_offset` | `int` | Y 轴偏移量 |

#### `move_to() -> bool`

将鼠标移动到指定位置。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `x` | `int \| float` | - | X 坐标 |
| `y` | `int \| float` | - | Y 坐标 |
| `duration` | `float` | `0.0` | 移动持续时间（秒） |
| `trace` | `bool` | `True` | 是否打印调试信息 |

#### `mouse_down() -> bool`

按下鼠标按钮。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `x` | `int \| float` | - | X 坐标 |
| `y` | `int \| float` | - | Y 坐标 |
| `trace` | `bool` | `True` | 是否打印调试信息 |

#### `mouse_up() -> bool`

释放鼠标按钮。

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `x` | `int \| float \| None` | `None` | X 坐标 |
| `y` | `int \| float \| None` | `None` | Y 坐标 |
| `trace` | `bool` | `True` | 是否打印调试信息 |

#### `scroll() -> bool`

滚动鼠标滚轮。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `distance` | `int` | 滚动距离 |

---

### IOperator 图像识别方法

#### `locate() -> Box | None`

在窗口内查找模板图片位置。

```python
def locate(self,
           template: str,
           *,
           from_x: float | None = None,
           from_y: float | None = None,
           to_x: float | None = None,
           to_y: float | None = None,
           confidence: float | None = None,
           trace: bool = True) -> Box | None
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `template` | `str` | - | 模板图片路径 |
| `from_x` | `float \| None` | `None` | 起始点 X 坐标比例 (0-1) |
| `from_y` | `float \| None` | `None` | 起始点 Y 坐标比例 (0-1) |
| `to_x` | `float \| None` | `None` | 结束点 X 坐标比例 (0-1) |
| `to_y` | `float \| None` | `None` | 结束点 Y 坐标比例 (0-1) |
| `confidence` | `float \| None` | `None` | 匹配置信度阈值 (0-1) |
| `trace` | `bool` | `True` | 是否打印调试信息 |

**返回：** 找到的 `Box` 对象或 `None`

---

#### `locate_all() -> list[Box] | None`

在窗口内查找所有匹配的图片位置。

```python
def locate_all(self,
               template: str,
               *,
               from_x: float | None = None,
               from_y: float | None = None,
               to_x: float | None = None,
               to_y: float | None = None,
               confidence: float | None = None,
               trace: bool = True) -> list[Box] | None
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `template` | `str` | - | 模板图片路径 |
| `from_x` | `float \| None` | `None` | 起始点 X 坐标比例 (0-1) |
| `from_y` | `float \| None` | `None` | 起始点 Y 坐标比例 (0-1) |
| `to_x` | `float \| None` | `None` | 结束点 X 坐标比例 (0-1) |
| `to_y` | `float \| None` | `None` | 结束点 Y 坐标比例 (0-1) |
| `confidence` | `float \| None` | `None` | 匹配置信度阈值 (0-1) |
| `trace` | `bool` | `True` | 是否打印调试信息 |

**返回：** 所有匹配的 `Box` 对象列表或 `None`

---

#### `locate_any() -> tuple[int, Box | None]`

在窗口内查找任意一张图片位置。

```python
def locate_any(self,
               templates: list[str],
               *,
               from_x: float | None = None,
               from_y: float | None = None,
               to_x: float | None = None,
               to_y: float | None = None,
               confidence: float | None = None,
               trace: bool = True) -> tuple[int, Box | None]
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `templates` | `list[str]` | - | 模板图片路径列表 |
| `from_x` | `float \| None` | `None` | 起始点 X 坐标比例 (0-1) |
| `from_y` | `float \| None` | `None` | 起始点 Y 坐标比例 (0-1) |
| `to_x` | `float \| None` | `None` | 结束点 X 坐标比例 (0-1) |
| `to_y` | `float \| None` | `None` | 结束点 Y 坐标比例 (0-1) |
| `confidence` | `float \| None` | `None` | 匹配置信度阈值 (0-1) |
| `trace` | `bool` | `True` | 是否打印调试信息 |

**返回：** 元组 `(图片索引, Box对象)`，未找到返回 `(−1, None)`

---

### IOperator OCR 识别方法

#### `ocr() -> list[Any] | None`

执行 OCR 文字识别。

```python
def ocr(self,
        *,
        from_x: float | None = None,
        from_y: float | None = None,
        to_x: float | None = None,
        to_y: float | None = None,
        trace: bool = True) -> list[Any] | None
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `from_x` | `float \| None` | `None` | 起始点 X 坐标比例 (0-1) |
| `from_y` | `float \| None` | `None` | 起始点 Y 坐标比例 (0-1) |
| `to_x` | `float \| None` | `None` | 结束点 X 坐标比例 (0-1) |
| `to_y` | `float \| None` | `None` | 结束点 Y 坐标比例 (0-1) |
| `trace` | `bool` | `True` | 是否打印调试信息 |

**返回：** OCR 引擎返回的原始结果列表或 `None`

---

#### `ocr_match() -> Box | None`

OCR 识别并匹配指定文本，返回文本位置。

```python
def ocr_match(self,
              text: str,
              confidence: float | None = None,
              *,
              from_x: float | None = None,
              from_y: float | None = None,
              to_x: float | None = None,
              to_y: float | None = None,
              trace: bool = True) -> Box | None
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text` | `str` | - | 要识别的文本 |
| `confidence` | `float \| None` | `None` | 识别置信度，默认使用 `ocr_confidence` |
| `from_x` | `float \| None` | `None` | 识别区域起始 X 坐标比例 (0-1) |
| `from_y` | `float \| None` | `None` | 识别区域起始 Y 坐标比例 (0-1) |
| `to_x` | `float \| None` | `None` | 识别区域结束 X 坐标比例 (0-1) |
| `to_y` | `float \| None` | `None` | 识别区域结束 Y 坐标比例 (0-1) |
| `trace` | `bool` | `True` | 是否打印调试信息 |

**返回：** 匹配的 `Box` 对象或 `None`

---

#### `ocr_match_any() -> tuple[int, Box | None]`

OCR 识别并匹配任意指定文本，返回文本索引和位置。

```python
def ocr_match_any(self,
                  texts: list[str],
                  confidence: float | None = None,
                  *,
                  from_x: float | None = None,
                  from_y: float | None = None,
                  to_x: float | None = None,
                  to_y: float | None = None,
                  trace: bool = True) -> tuple[int, Box | None]
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `texts` | `list[str]` | - | 要识别的文本列表 |
| `confidence` | `float \| None` | `None` | 识别置信度，默认使用 `ocr_confidence` |
| `from_x` | `float \| None` | `None` | 识别区域起始 X 坐标比例 (0-1) |
| `from_y` | `float \| None` | `None` | 识别区域起始 Y 坐标比例 (0-1) |
| `to_x` | `float \| None` | `None` | 识别区域结束 X 坐标比例 (0-1) |
| `to_y` | `float \| None` | `None` | 识别区域结束 Y 坐标比例 (0-1) |
| `trace` | `bool` | `True` | 是否打印调试信息 |

**返回：** 元组 `(文本索引, Box对象)`，未找到返回 `(−1, None)`

---

### IOperator 等待方法

#### `wait_img() -> Box | None`

等待模板图片出现。

```python
def wait_img(self,
             template: str,
             timeout: int = 10,
             interval: float = 0.5) -> Box | None
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `template` | `str` | - | 模板图片路径 |
| `timeout` | `int` | `10` | 超时时间（秒） |
| `interval` | `float` | `0.5` | 检查间隔时间（秒） |

**返回：** 找到的 `Box` 对象或 `None`

---

#### `wait_any_img() -> tuple[int, Box | None]`

等待任意一张图片出现。

```python
def wait_any_img(self,
                 templates: list[str],
                 timeout: int = 10,
                 interval: float = 0.5,
                 trace: bool = True) -> tuple[int, Box | None]
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `templates` | `list[str]` | - | 模板图片路径列表 |
| `timeout` | `int` | `10` | 超时时间（秒） |
| `interval` | `float` | `0.5` | 检查间隔时间（秒） |
| `trace` | `bool` | `True` | 是否打印调试信息 |

**返回：** 元组 `(图片索引, Box对象)`，未找到返回 `(−1, None)`

---

#### `wait_ocr() -> Box | None`

等待 OCR 识别到指定文本。

```python
def wait_ocr(self,
             text: str,
             confidence: float | None = None,
             interval: float = 0.2,
             timeout: float = 10,
             *args: Any,
             **kwargs: Any) -> Box | None
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text` | `str` | - | 要识别的文本 |
| `confidence` | `float \| None` | `None` | 识别置信度 |
| `interval` | `float` | `0.2` | 检查间隔时间（秒） |
| `timeout` | `float` | `10` | 超时时间（秒） |

**返回：** 找到的 `Box` 对象或 `None`

---

#### `wait_ocr_any() -> tuple[int, Box | None]`

等待 OCR 识别到任意指定文本。

```python
def wait_ocr_any(self,
                 texts: list[str],
                 confidence: float | None = None,
                 interval: float = 0.2,
                 timeout: float = 10,
                 *args: Any,
                 **kwargs: Any) -> tuple[int, Box | None]
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `texts` | `list[str]` | - | 要识别的文本列表 |
| `confidence` | `float \| None` | `None` | 识别置信度 |
| `interval` | `float` | `0.2` | 检查间隔时间（秒） |
| `timeout` | `float` | `10` | 超时时间（秒） |

**返回：** 元组 `(文本索引, Box对象)`，未找到返回 `(−1, None)`

---

#### `wait_any() -> tuple[int, Box | None]` *(静态方法)*

等待任意条件满足。

```python
@staticmethod
def wait_any(conditions: list[Waitable],
             timeout: int = 10,
             interval: float = 0.5) -> tuple[int, Box | None]
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `conditions` | `list[Waitable]` | - | 条件函数列表，每个函数返回 `Box \| None` |
| `timeout` | `int` | `10` | 超时时间（秒） |
| `interval` | `float` | `0.5` | 检查间隔时间（秒） |

**返回：** 元组 `(条件索引, Box对象)`，未找到返回 `(−1, None)`

---

### IOperator 点击与输入方法

#### `click_box() -> bool`

点击 Box 区域中心。

```python
def click_box(self,
              box: Box,
              x_offset: int | float = 0,
              y_offset: int | float = 0,
              after_sleep: float = 0) -> bool
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `box` | `Box` | - | Box 对象 |
| `x_offset` | `int \| float` | `0` | X 偏移量 |
| `y_offset` | `int \| float` | `0` | Y 偏移量 |
| `after_sleep` | `float` | `0` | 点击后等待时间（秒） |

**返回：** 点击成功返回 `True`，否则返回 `False`

---

#### `click_img() -> bool`

查找图片并点击其中心位置。

```python
def click_img(self,
              template: str,
              x_offset: int | float = 0,
              y_offset: int | float = 0,
              after_sleep: float = 0) -> bool
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `template` | `str` | - | 模板图片路径 |
| `x_offset` | `int \| float` | `0` | X 偏移量 |
| `y_offset` | `int \| float` | `0` | Y 偏移量 |
| `after_sleep` | `float` | `0` | 点击后等待时间（秒） |

**返回：** 点击成功返回 `True`，否则返回 `False`

---

### IOperator 鼠标操作方法

#### `drag_to() -> bool`

拖动鼠标到指定位置。

```python
def drag_to(self,
            from_x: int | float,
            from_y: int | float,
            to_x: int | float,
            to_y: int | float,
            duration: float = 0.5,
            trace: bool = True) -> bool
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `from_x` | `int \| float` | - | 起始 X 坐标 |
| `from_y` | `int \| float` | - | 起始 Y 坐标 |
| `to_x` | `int \| float` | - | 目标 X 坐标 |
| `to_y` | `int \| float` | - | 目标 Y 坐标 |
| `duration` | `float` | `0.5` | 拖动持续时间（秒） |
| `trace` | `bool` | `True` | 是否打印调试信息 |

**返回：** 拖动成功返回 `True`

---

### IOperator 工具方法

#### `sleep() -> None` *(静态方法)*

线程休眠。

```python
@staticmethod
def sleep(seconds: float) -> None
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `seconds` | `float` | 休眠时间（秒） |

---

#### `do_while() -> bool` *(静态方法)*

在满足条件时重复执行操作。

```python
@staticmethod
def do_while(action: Callable[[], Any],
             condition: Callable[[], bool],
             interval: float = 0.1,
             max_iterations: int = 50) -> bool
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `action` | `Callable[[], Any]` | - | 操作函数 |
| `condition` | `Callable[[], bool]` | - | 条件函数 |
| `interval` | `float` | `0.1` | 检查条件前的等待时间（秒） |
| `max_iterations` | `int` | `50` | 最大迭代次数 |

**返回：** 因不再满足条件而退出返回 `True`，达到最大迭代次数返回 `False`

---

## `operators.model` 模块

`model` 模块定义了屏幕自动化操作中使用的数据模型，包括 `Region` 和 `Box` 数据类。

### Region

表示屏幕上的一个矩形区域。

**定义：**

```python
@dataclasses.dataclass
class Region:
    left: int
    top: int
    width: int
    height: int
    parent: 'Region | None' = None
```

**属性：**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `left` | `int` | - | 左侧坐标 |
| `top` | `int` | - | 顶部坐标 |
| `width` | `int` | - | 宽度 |
| `height` | `int` | - | 高度 |
| `parent` | `Region \| None` | `None` | 父区域引用 |

#### `tuple` (属性)

将 Region 转换为元组。

```python
@property
def tuple(self) -> tuple[int, int, int, int]
```

**返回：** `(left, top, width, height)`

#### `sub_region()`

获取当前 Region 内的子区域。

```python
def sub_region(self, from_x: float, from_y: float, to_x: float, to_y: float) -> 'Region'
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `from_x` | `float` | 子区域起始 X 坐标比例 (0-1) |
| `from_y` | `float` | 子区域起始 Y 坐标比例 (0-1) |
| `to_x` | `float` | 子区域结束 X 坐标比例 (0-1) |
| `to_y` | `float` | 子区域结束 Y 坐标比例 (0-1) |

**返回：** 新的 `Region` 对象，其 `parent` 属性指向当前区域

---

### Box

表示窗口内的一个矩形区域。

**定义：**

```python
@dataclasses.dataclass
class Box:
    left: int
    top: int
    width: int
    height: int
    source: str | None = None
```

**属性：**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `left` | `int` | - | 左侧坐标 |
| `top` | `int` | - | 顶部坐标 |
| `width` | `int` | - | 宽度 |
| `height` | `int` | - | 高度 |
| `source` | `str \| None` | `None` | 来源（模板路径或文本） |

#### `center` (属性)

获取 Box 的中心点坐标。

```python
@property
def center(self) -> tuple[int, int]
```

**返回：** 中心点坐标 `(center_x, center_y)`

#### `distance()`

计算两个 Box 中心点之间的欧几里得距离。

```python
def distance(self, other: 'Box') -> float
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `other` | `Box` | 另一个 Box 对象 |

**返回：** 两点之间的欧几里得距离

---

### `Waitable` 类型别名

条件函数类型别名：

```python
type Waitable = Callable[[], Box | None]
```

---

## `task` 模块

`task` 模块定义了任务框架，提供了任务的基类、注册机制和生命周期管理。

### Executable

可执行对象的基类，提供停止功能。

**定义：**

```python
class Executable:
    def __init__(self, operator: IOperator):
        self.operator = operator
        self.settings = operator.settings
        self.stop_event = self.operator.stop_event
```

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `operator` | `IOperator` | 操作器实例 |
| `settings` | `Settings` | 设置对象 |
| `stop_event` | `threading.Event \| None` | 停止事件 |

**方法：**

#### `stop()`

停止执行。

```python
def stop(self) -> None
```

---

### BaseTask

基础任务类，所有任务类都应继承自此类。继承自 `Executable`。

**定义：**

```python
class BaseTask(Executable, ABC):
    def __init__(self, operator: IOperator, config: TasksConfig):
        super().__init__(operator)
        self.config = config
        self._post_init()
```

**初始化参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `operator` | `IOperator` | 操作器实例 |
| `config` | `TasksConfig` | 任务配置 |

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `config` | `TasksConfig` | 任务配置 |

**方法：**

#### `_post_init()`

子类可重写此方法以进行额外初始化。

```python
def _post_init(self) -> None
```

#### `start()` *(final)*

启动任务，调用 `on_start()`。

```python
@final
def start(self) -> None
```

#### `run()` *(abstract)*

任务的主要执行逻辑，子类必须实现。

```python
@abstractmethod
def run(self) -> bool
```

**返回：** 执行成功返回 `True`，失败返回 `False`

#### `finish()` *(final)*

完成任务，调用 `on_finish()`。

```python
@final
def finish(self) -> None
```

#### `fail()` *(final)*

任务失败，调用 `on_failure()`。

```python
@final
def fail(self) -> None
```

#### `send_notification()`

发送通知。

```python
def send_notification(self, message: str, result: str) -> None
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `message` | `str` | 通知消息 |
| `result` | `str` | 结果类型（`"success"` 或 `"error"`） |

#### `on_start()`

任务开始时的回调方法。

```python
def on_start(self) -> None
```

#### `on_finish()`

任务完成时的回调方法。

```python
def on_finish(self) -> None
```

#### `on_failure()`

任务失败时的回调方法。

```python
def on_failure(self) -> None
```

---

### 任务注册机制

#### `registry`

全局任务注册表，存储已注册的任务类及其执行顺序。

```python
registry: list[tuple[int, type[BaseTask]]] = list()
```

#### `task()` 装饰器

任务注册装饰器，用于将任务类注册到全局任务列表中，并指定执行顺序。

```python
def task(_cls: type[BaseTask] | None = None, *, order: int | None = None)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `_cls` | `type[BaseTask] \| None` | `None` | 被装饰的任务类 |
| `order` | `int \| None` | `None` | 执行顺序，默认追加到列表末尾 |

**使用示例：**

```python
from SRACore.task import BaseTask, task

@task(order=1)
class MyTask(BaseTask):
    def run(self) -> bool:
        # 任务逻辑
        return True
```

#### `get_tasks()`

获取已注册的任务类列表，按执行顺序排序。

```python
def get_tasks() -> list[type[BaseTask]]
```

**返回：** 已排序的任务类列表

---

## 使用示例

```python
from SRACore.operators.ioperator import IOperator
from SRACore.operators.model import Box

class MyOperator(IOperator):
    # 实现抽象方法...
    pass

op = MyOperator()

# 等待图片出现
box = op.wait_img("button.png", timeout=10)

# 如果找到则点击
if box:
    op.click_box(box)

# OCR 识别并匹配文本
result = op.ocr_match("Hello World")

# 等待 OCR 文本
box = op.wait_ocr("Loading...")
```
