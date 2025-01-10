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
v2.1
作者：雪影
"""

import json
import os
from dataclasses import dataclass
from time import sleep
import requests
from pathlib import Path
from requests import RequestException
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, DownloadColumn, TransferSpeedColumn
from functools import lru_cache
from StarRailAssistant.utils import WindowsProcess

# 下载进度条
download_progress_bar = Progress(
    TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    DownloadColumn(),
    "•",
    TransferSpeedColumn(),
    "•",
    TimeRemainingColumn(),
    transient=True,
)

@dataclass
class VersionInfo:
    version: str
    resource_version: str
    announcement: str
    resource_announcement: str

class Updater:
    GITHUB_URL = "https://github.com/Shasnow/StarRailAssistant/releases/download/v{version}/StarRailAssistant_v{version}.zip"
    RESOURCE_URL = "https://github.com/Shasnow/SRAresource/releases/download/resource/resource.zip"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    }
    APP_PATH = Path(__file__).parent.parent.absolute()
    VERSION_INFO_URL = (
        "https://github.com/Shasnow/StarRailAssistant/blob/main/version.json"
    )
    PROXY = [
        "https://gitproxy.click/",
        "https://cdn.moran233.xyz/",
        "https://gh.llkk.cc/",
        "https://github.akams.cn/",
        "https://www.ghproxy.cn/",
        "",
    ]
    PROXY_LIST_LEN = len(PROXY)
    # 临时下载文件的路径
    TEMP_DOWNLOAD_PATH = APP_PATH / "SRAUpdate.zip"
    DOWNLOAD_FAT = Path(APP_PATH / "SRAUpdate.zip.downloaded")

    # 更新提取后的目录（与安装目录相同）
    UPDATE_EXTRACT_DIR = APP_PATH

    def __init__(self):
        print("欢迎使用SRA更新器>_<")
        self.init_version_file()
        if os.path.exists(self.TEMP_DOWNLOAD_PATH):
            os.remove(self.TEMP_DOWNLOAD_PATH)

    def init_version_file(self):
        if not os.path.exists(self.APP_PATH / "version.json"):
            print("初始化版本信息...")
            version_info = {"version": "0.0.0", "resource_version": "0.0.0"}
            with open(
                    self.APP_PATH / "version.json", "w", encoding="utf-8"
            ) as json_file:
                json.dump(version_info, json_file, indent=4)

    @lru_cache(maxsize=1)
    def get_current_version(self) -> VersionInfo:
        with open(self.APP_PATH / "version.json", "r", encoding="utf-8") as jsonfile:
            version_info_local = json.load(jsonfile)
            version = version_info_local["version"]
            resource_version = version_info_local["resource_version"]
        return VersionInfo(version, resource_version, "", "")

    def check_for_updates(self):
        print("检查版本信息...")
        version = self.get_current_version()
        try:
            url = self.version_check(version)
            if url == "":
                return
            self.download(url)
            self.unzip()
        except Exception as e:
            print(f"检查更新时出错: {e}")
            os.system("pause")

    def version_check(self, v: VersionInfo) -> str:
        # 从远程服务器获取版本信息
        i = 0
        while i < self.PROXY_LIST_LEN:
            try:
                response = requests.get(self.PROXY[i] + self.VERSION_INFO_URL)
                version_info = response.json()
                break
            except RequestException:
                i += 1
                print(f"请求超时，重新尝试...({i}/{self.PROXY_LIST_LEN})")
        else:
            raise Exception(
                f"服务器连接失败，已尝试 ({self.PROXY_LIST_LEN}/{self.PROXY_LIST_LEN})"
            )
        # 获取远程最新版本号
        remote_version = version_info["version"]
        remote_resource_version = version_info["resource_version"]
        # 比较当前版本和远程版本
        if remote_version > v.version:
            print(f"发现新版本：{remote_version}")
            print(f"更新说明：\n{version_info['announcement']}")
            return self.GITHUB_URL.format(version=remote_version)
        if remote_resource_version > v.resource_version:
            print(f"发现资源更新：{remote_resource_version}")
            print(f"更新说明：\n{version_info['resource_announcement']}")
            return self.RESOURCE_URL
        print("已经是最新版本")
        return ""
    
    def can_direct(self, url: str) -> bool:
        """
        判断是否可以直连
        :param url: 链接
        :return: 是否可以直连
        """
        try:
            response = requests.head(url, headers=self.HEADERS, timeout=5)
            if response.status_code == 200:
                print("代理直连成功")
                return True
        except Exception:
            pass
        return False
    
    def proxy_avaliable(self, proxy_url: str) -> bool:
        """ 判断代理是否可用 """
        result = self.can_direct(f"{proxy_url}/https://github.com/Shasnow/StarRailAssistant/releases/download/v{self.get_current_version().version}/StarRailAssistant_v{self.get_current_version().version}.zip")
        if result:
            print(f"代理: {proxy_url}, 确认可用, 将使用此代理")
        else:
            print(f"代理{proxy_url}, 不可用, 跳过.")
        return result
    
    def _download(self, url: str, filepath: Path, proxy_url: str = "") -> None:
        """
        下载文件
        :param url: 下载链接
        :param filename: 保存文件名
        :param proxy_url: 代理链接前缀
        """
        filename = filepath.stem
        if not self.can_direct(url):
            url = f"{proxy_url}{url}"
        
        start_byte = 0
        resume_header = {}

        # 检查文件是否存在
        if filepath.exists():
            start_byte = filepath.stat().st_size
            if start_byte > 0:
                resume_header = {"Range": f"bytes={start_byte}-"}
                self.HEADERS.update(resume_header)
                print("服务器支持断点续传，开始继续下载...")

        with download_progress_bar as progress:
            resp = requests.get(url, headers=self.HEADERS, stream=True)
            total_size = int(resp.headers.get("Content-Length", 0))

            if start_byte > 0 and resp.status_code != 206:
                print("服务器不支持断点续传，重新下载整个文件")
                start_byte = 0
                resume_header = {}
                self.HEADERS.update(resume_header)
                resp = requests.get(url, headers=self.HEADERS, stream=True)
                total_size = int(resp.headers.get("Content-Length", 0))

            task = progress.add_task(
                f"[bold blue]下载 {filename}", 
                filename=filename,
                start=False,
                total=total_size + start_byte,
                completed=start_byte
            )

            mode = 'ab' if start_byte > 0 else 'wb'
            with open(filepath, mode) as file:
                for data in resp.iter_content(chunk_size=8192):
                    file.write(data)
                    progress.update(task, advance=len(data))
                    progress.refresh()

            progress.remove_task(task)

    def download(self, download_url: str) -> None:
        try:
            print("下载更新文件")
            i = 0
            while i < self.PROXY_LIST_LEN:
                proxy_url = self.PROXY[i]
                if self.proxy_avaliable(proxy_url):
                    self._download(download_url, self.DOWNLOAD_FAT, proxy_url)
                    break
                else:
                    i += 1
                    continue
        except Exception as e:
            print(f"下载更新时出错: {e}")
            os.system("pause")
        except KeyboardInterrupt:
            print("下载更新已取消")
            os.remove(self.DOWNLOAD_FAT)
            os.system("pause")
            exit(1)

    def unzip(self):
        if WindowsProcess.is_process_running("SRA.exe"):
            WindowsProcess.task_kill("SRA.exe")
            sleep(2)
        try:
            # 去掉 .downloaded的后缀
            self.DOWNLOAD_FAT.rename(self.TEMP_DOWNLOAD_PATH)
            print("解压更新文件")
            if not os.path.exists(self.APP_PATH / "tools/7z.exe"):
                print(f"解压工具丢失，请手动解压{self.TEMP_DOWNLOAD_PATH}到当前文件夹")
                os.system("pause")
                return
            command = f"{self.APP_PATH}/tools/7z x {self.TEMP_DOWNLOAD_PATH} -y"
            cmd = 'cmd.exe /c start "" ' + command
            WindowsProcess.Popen(cmd, shell=True)

        except Exception as e:
            print(f"解压更新时出错: {e}")
            os.system("pause")


if __name__ == "__main__":
    main = Updater()
    main.check_for_updates()