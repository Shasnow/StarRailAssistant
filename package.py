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

import os
import sys
import json
import shutil
from pathlib import Path


def version_text(version_numb: list) -> str:
    """将版本号列表转为可读的文本信息"""

    while len(version_numb) < 4:
        version_numb.append(0)

    if version_numb[3] == 0:
        version = f"v{'.'.join(str(_) for _ in version_numb[0:3])}"
    else:
        version = (
            f"v{'.'.join(str(_) for _ in version_numb[0:3])}-beta.{version_numb[3]}"
        )
    return version


if __name__ == "__main__":

    root_path = Path(sys.argv[0]).resolve().parent

    with (root_path / "version.json").open(mode="r", encoding="utf-8") as f:
        version = json.load(f)

    main_version_numb = list(map(int, version["version"].split(".")))

    print("Packaging SRA main program ...")

    os.system(
        "powershell -Command python -m nuitka --standalone --mingw64"
        " --enable-plugins=pyside6 --windows-console-mode=disable"
        " --windows-icon-from-ico=res\\SRAicon.ico"
        " --company-name='StarRailAssistant Team' --product-name=StarRailAssistant"
        f" --file-version={version['version']}"
        f" --product-version={version['version']}"
        " --file-description='StarRailAssistant Component'"
        " --copyright='Copyright © 2024 Shasnow'"
        " --assume-yes-for-downloads --output-filename=SRA"
        " --remove-output SRA.py"
    )

    print("Start to copy rescourses ...")

    shutil.copytree(root_path / "res", root_path / "SRA.dist/res")
    shutil.copytree(root_path / "tools", root_path / "SRA.dist/tools")
    shutil.copy(root_path / "HELP.md", root_path / "SRA.dist/HELP.md")
    shutil.copy(root_path / "LICENSE", root_path / "SRA.dist/LICENSE")
    shutil.copy(root_path / "README.md", root_path / "SRA.dist/README.md")
    shutil.copy(root_path / "version.json", root_path / "SRA.dist/version.json")

    print("Start to compress ...")

    shutil.make_archive(
        base_name=root_path / f"StarRailAssistant_{version_text(main_version_numb)}",
        format="zip",
        root_dir=root_path / "SRA.dist",
        base_dir=".",
    )
    shutil.rmtree(root_path / "SRA.dist")

    print("SRA main program packaging completed !")

    (root_path / "version_info.txt").write_text(
        f"{version_text(main_version_numb)}\n\n{version['announcement']}",
        encoding="utf-8",
    )
