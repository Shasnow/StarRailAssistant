import os
import sys

# 基础的常量定义
AppPath = os.path.dirname(os.path.realpath(sys.argv[0])).replace(
        "\\", "/"
    )
PLATFORM = "Windows" if sys.platform=="win32" else "Linux"
VERSION = "0.8.2"
CORE = "0.8.2 for " + PLATFORM