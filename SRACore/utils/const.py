import os
import sys

# 基础的常量定义
AppPath = os.path.dirname(os.path.realpath(sys.argv[0])).replace(
    "\\", "/"
)
PLATFORM = "Windows" if sys.platform == "win32" else "Linux"
VERSION = "0.8.3"
CORE = "0.8.3 for " + PLATFORM

RANDOM_TITLE = [
    "--cli !",
    "坐和放宽",
    "not 'Sequence Read Archive'",
    "--run !",
    "启动器启动启动器"
]
