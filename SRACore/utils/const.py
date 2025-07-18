import os
import sys
from pathlib import Path

# 基础的常量定义
AppPath = Path(os.path.dirname(os.path.realpath(sys.argv[0])))
PLATFORM = "Windows" if sys.platform == "win32" else "Linux"
VERSION = "0.8.4"
CORE = f"{VERSION} for {PLATFORM}"

RANDOM_TITLE = [
    "--cli !",
    "坐和放宽",
    "not 'Sequence Read Archive'",
    "--run !",
    "启动器启动启动器",
    "你知道吗：定时执行需要重启SRA后生效",
    "-1073741819",
    "因为太阳将要毁伤",
    "跨越寰宇终抵黯淡星外"
]
