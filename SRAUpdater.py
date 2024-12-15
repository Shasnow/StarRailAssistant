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
SRA更新器
v2.0.0
作者：雪影
"""

import json
import os
import sys
from time import sleep

import requests

from StarRailAssistant.utils import WindowsProcess


class Updater:
    APP_PATH = os.path.dirname(os.path.realpath(sys.argv[0])).replace(
        "\\", "/"
    )  # 获取软件自身的路径
    # 远程版本信息文件的URL
    VERSION_INFO_URL = "https://ghp.ci/https://github.com/Shasnow/StarRailAssistant/blob/main/version.json"

    # 临时下载文件的路径
    TEMP_DOWNLOAD_PATH = os.path.join(APP_PATH, "SRAUpdate.zip")

    # 更新提取后的目录（通常与安装目录相同）
    UPDATE_EXTRACT_DIR = APP_PATH

    def __init__(self):
        print("欢迎使用SRA更新器")
        self.init_version_file()
        if os.path.exists(self.TEMP_DOWNLOAD_PATH):
            os.remove(self.TEMP_DOWNLOAD_PATH)

    def init_version_file(self):
        if not os.path.exists(self.APP_PATH + "/version.json"):
            print("初始化版本信息")
            version_info = {
                "version": "0.0.0",
                "updater": "0.0.0",
                "resource_version": "0.0.0"
            }
            with open(self.APP_PATH + "/version.json", "w", encoding="utf-8") as json_file:
                json.dump(version_info, json_file, indent=4)

    def get_current_version(self):
        with open(self.APP_PATH + '/version.json', 'r', encoding="utf-8") as jsonfile:
            version_info = json.load(jsonfile)
            version = version_info["version"]
            updater_version = version_info["updater"]
            resource_version = version_info["resource_version"] if "resource_version" in version_info else "0.0.0"
        return version, updater_version, resource_version

    def check_for_updates(self):
        print("检查版本信息")
        current_version, current_updater_version, current_resource_version = self.get_current_version()
        try:
            url, updater_update = self.version_check(current_version, current_updater_version, current_resource_version)
            if url == "":
                return
            self.download(url)
            self.unzip()
        except Exception as e:
            print(f"检查更新时出错: {e}")
            os.system("pause")

    def version_check(self, current_version, current_updater_version, current_resource_version):
        # 从远程服务器获取版本信息
        response = requests.get(self.VERSION_INFO_URL)
        version_info = response.json()
        # 获取远程最新版本号
        remote_version = version_info["version"]
        remote_updater_version = version_info["updater"]
        remote_resource_version = version_info["resource_version"]
        updater_update = False
        if remote_updater_version > current_updater_version:
            updater_update = True
        # 比较当前版本和远程版本
        if remote_version > current_version:
            print(f"发现新版本：{remote_version}")
            print(f"更新说明：\n{version_info['announcement']}")
            return version_info["download_url"], updater_update
        if remote_resource_version > current_resource_version:
            print(f"发现资源更新：{remote_resource_version}")
            print(f"更新说明：\n{version_info['resource_announcement']}")
            return version_info["resource_download_url"], updater_update
        print("已经是最新版本")
        return "", updater_update

    def download(self, download_url):
        try:
            print("下载更新文件")
            response = requests.get(download_url, stream=True)
            file_size = response.headers.get('Content-Length')
            if file_size is None:
                file_size = 1
            else:
                file_size = int(file_size)
            with open(self.TEMP_DOWNLOAD_PATH, 'wb') as f:
                downloaded_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    print(
                        f"\r已下载: {downloaded_size / 1000000:.2f}/{file_size / 1000000:.2f} MB ({downloaded_size / file_size * 100:.2f}%)",
                        end="")
            print()
        except Exception as e:
            print(f"下载更新时出错: {e}")
            os.system("pause")

    def unzip(self):
        if WindowsProcess.is_process_running("SRA.exe"):
            WindowsProcess.task_kill("SRA.exe")
            sleep(2)
        try:
            print("解压更新文件")
            command=self.APP_PATH+"/tools/7z x "+self.TEMP_DOWNLOAD_PATH+" -y"
            cmd = 'cmd.exe /c start "" '+command
            WindowsProcess.popen(cmd, shell=True)

        except Exception as e:
            print(f"解压更新时出错: {e}")
            os.system("pause")


if __name__ == "__main__":
    main = Updater()
    main.check_for_updates()
