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
作者：雪影
打包
"""

import json
import os
import shutil
import sys
from pathlib import Path

if __name__ == "__main__":

    root_path = Path(sys.argv[0]).resolve().parent

    with (root_path / "version.json").open(mode="r", encoding="utf-8") as f:
        version = json.load(f)

    print("Start to copy resources ...")

    os.makedirs(root_path / "main.dist/SRA", exist_ok=True)
    shutil.copytree(root_path / "SRAFrontend/bin/Release/net8.0/win-x64/publish", root_path / "main.dist", dirs_exist_ok=True)
    shutil.copytree(root_path / "resources", root_path / "main.dist/SRA/resources")
    shutil.copytree(root_path / "tasks", root_path / "main.dist/SRA/tasks")
    shutil.copytree(root_path / "SRACore", root_path / "main.dist/SRA/SRACore")
    shutil.copy(root_path / "version.json", root_path / "main.dist/SRA/version.json")
    shutil.copy(root_path / "LICENSE", root_path / "main.dist/SRA/LICENSE")
    shutil.copy(root_path / "README.md", root_path / "main.dist/SRA/README.md")
    shutil.copy(root_path / "main.py", root_path / "main.dist/SRA/main.py")
    shutil.copy(root_path / "requirements.txt", root_path / "main.dist/SRA/requirements.txt")
    shutil.copy(root_path / "SRA-cli.exe", root_path / "main.dist/SRA-cli.exe")

    print("Start to compress full package...")

    shutil.make_archive(
        base_name=str(root_path / f"StarRailAssistant_v{version['version']}"),
        format="zip",
        root_dir=root_path / "main.dist",
        base_dir=".",
    )
    

    print("SRA program packaging completed !")
    print("Start to compress source code...")
    shutil.make_archive(
        base_name=str(root_path / f"StarRailAssistant_Core_v{version['version']}"),
        format="zip",
        root_dir=root_path / "main.dist/SRA",
        base_dir=".",
    )
    print("SRA source code packaging completed !")
    shutil.rmtree(root_path / "main.dist")
    (root_path / "version_info.txt").write_text(
        f"v{version['version']}\n\n{version['Announcement'][0]['content']}", encoding="utf-8"
    )
