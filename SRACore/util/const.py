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
VERSION = "2.13.0"  # 版本号
CORE = f"{VERSION} on {sys.platform}"  # 核心版本信息

AppRootDir = Path(__file__).parent.parent.parent.absolute()
if sys.platform == "win32":
    AppDataDir = Path(os.getenv("APPDATA", "")) / "SRA"
else:
    AppDataDir = Path.home() / ".config" / "SRA"
ConfigsDir = AppDataDir / "configs"
CacheDir = AppDataDir / "cache"
