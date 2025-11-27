#   <StarRailAssistant:An automated program that helps you complete daily task of StarRail.>
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

    print("Packaging Python program...")

    os.system(
        "powershell -Command python -m nuitka --standalone --mingw64"
        " --windows-console-mode=force --windows-uac-admin"
        " --windows-icon-from-ico=resources\\SRAicon.ico"
        " --company-name='StarRailAssistant Team' --product-name=StarRailAssistant"
        f" --file-version={version['version'].split('-')[0]}"
        f" --product-version={version['version'].split('-')[0]}"
        " --file-description='StarRailAssistant Component'"
        " --copyright='Copyright © 2024 Shasnow'"
        " --assume-yes-for-downloads --output-filename=SRA-cli"
        " --remove-output main.py"
    )
    print("Python program packaging completed !")

    print("Start to copy resources ...")

    shutil.copytree(root_path / "SRAFrontend/bin/Release/net8.0/win-x64/publish", root_path / "main.dist/", dirs_exist_ok=True)
    shutil.copytree(root_path / "resources", root_path / "main.dist/resources")
    shutil.copytree(root_path / "rapidocr_onnxruntime", root_path / "main.dist/rapidocr_onnxruntime")
    shutil.copytree(root_path / "task", root_path / "main.dist/task")
    os.makedirs(root_path / "main.dist/SRACore", exist_ok=True)
    shutil.copy(root_path / "SRACore/config.toml", root_path / "main.dist/SRACore/config.toml")
    shutil.copy(root_path / "LICENSE", root_path / "main.dist/LICENSE")
    shutil.copy(root_path / "README.md", root_path / "main.dist/README.md")
    shutil.copy(root_path / "version.json", root_path / "main.dist/version.json")

    print("Start to compress ...")

    shutil.make_archive(
        base_name=str(root_path / f"StarRailAssistant_v{version['version']}"),
        format="zip",
        root_dir=root_path / "main.dist",
        base_dir=".",
    )
    shutil.rmtree(root_path / "main.dist")

    print("SRA program packaging completed !")

    (root_path / "version_info.txt").write_text(
        f"v{version['version']}\n\n{version['Announcement'][0]['content']}", encoding="utf-8"
    )
