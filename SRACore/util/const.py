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
import os
import sys
from pathlib import Path

# 基础的常量定义
AppPath = Path(os.path.dirname(os.path.realpath(sys.argv[0])))
VERSION = "2.7.0"  # 版本号
CORE = f"{VERSION} on {sys.platform}"  # 核心版本信息

AppDataSraDir = Path(os.getenv("APPDATA") if sys.platform == "win32" else os.path.expanduser("~/.config")) / "SRA"