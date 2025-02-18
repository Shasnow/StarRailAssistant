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
作者：雪影
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from time import sleep

import requests
from requests import RequestException
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, DownloadColumn, TransferSpeedColumn

from StarRailAssistant.utils.WindowsProcess import is_process_running, task_kill, Popen
from subprocess import DEVNULL  # 丢弃垃圾输出, 未遂. 想彻底解决还得再引入一个更新器,解决更新器自更新的覆盖问题

FROZEN = getattr(sys, "frozen", False)
""" 是否被打包成了可执行文件 """

if FROZEN:
    from sys import exit

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
    APP_PATH = Path(sys.executable).parent.absolute() if FROZEN else Path(__file__).parent.absolute()
    print(f"当前路径：{APP_PATH}")
    VERSION_INFO_URL = (
        "https://gitee.com/yukikage/StarRailAssistant/releases/download/release/version.json"
    )
    PROXYS = [
        "https://gh.llkk.cc/",
        "https://github.akams.cn/",
        "https://www.ghproxy.cn/",
        "https://ghproxy.cc/",
        "https://cdn.moran233.xyz/",
        "",
    ]
    VERIFY = True
    # 临时下载文件的路径
    TEMP_DOWNLOAD_DIR = APP_PATH
    TEMP_DOWNLOAD_FILE = TEMP_DOWNLOAD_DIR / "SRAUpdate.zip"
    DOWNLOADING_FILE = TEMP_DOWNLOAD_DIR / "SRAUpdate.zip.downloaded"

    # 更新提取后的目录（与安装目录相同）
    UPDATE_EXTRACT_DIR = APP_PATH

    def __init__(self):
        print("欢迎使用SRA更新器>_<")
        self.init_version_file()
        if os.path.exists(self.TEMP_DOWNLOAD_FILE):
            os.remove(self.TEMP_DOWNLOAD_FILE)

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
            version = version_info_local.get("version", "0.0.0")
            resource_version = version_info_local.get("resource_version", "0.0.0")
            announcement = version_info_local.get("Announcement", "<hr><p>噔噔——新的公告界面～(∠・ω&lt; )⌒☆</p><hr>")
        return VersionInfo(version, resource_version, announcement, "")

    def announcement_change(self, text):
        with open(self.APP_PATH / "version.json", "r+", encoding="utf-8") as json_file:
            version = json.load(json_file)
            version["Announcement"] = text
            json_file.seek(0)
            json.dump(version, json_file, indent=4, ensure_ascii=False)

    def check_for_updates(self):
        """ 检查并更新 """
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
        try:
            response = requests.get(f"{self.VERSION_INFO_URL}", timeout=10)
            version_info = response.json()
        except RequestException as e:
            print(e)
            raise Exception(f"服务器连接失败")

        # 获取远程最新版本号
        remote_version = version_info["version"]
        remote_resource_version = version_info["resource_version"]
        new_announcement = version_info["Announcement"]
        # 比较当前版本和远程版本
        print(f"当前版本：{v.version}")
        print(f"当前资源版本：{v.resource_version}")
        print(f"远程版本：{remote_version}")
        print(f"远程资源版本：{remote_resource_version}")
        if remote_version > v.version:
            print(f"发现新版本：{remote_version}")
            print(f"更新说明：\n{version_info['announcement']}")
            return self.GITHUB_URL.format(version=remote_version)
        if remote_resource_version > v.resource_version:
            print(f"发现资源更新：{remote_resource_version}")
            print(f"更新说明：\n{version_info['resource_announcement']}")
            return self.RESOURCE_URL
        if new_announcement != v.announcement:
            self.announcement_change(new_announcement)
        print("已经是最新版本")
        return ""

    def get_download_session(self, url: str, proxy_url: str = "") -> tuple[requests.Session, str]:
        _url = f"{proxy_url}{url}"
        session = requests.session()
        session.headers.update(self.HEADERS)
        # head confirm
        resp = session.head(_url, allow_redirects=True, verify=self.VERIFY)
        if resp.status_code != 200:
            raise RequestException(f"请求{_url}失败，状态码：{resp.status_code}")
        return session, _url

    def _download(self, url: str, filepath: Path, proxy_url: str = "") -> bool:
        """
        下载文件
        :param url: 下载链接
        :param filepath: 保存文件路径
        :param proxy_url: 代理链接前缀
        """
        session = None
        try:
            session, download_url = self.get_download_session(url, proxy_url)

            # 获取文件总大小
            resp = session.head(download_url, allow_redirects=True, verify=self.VERIFY)
            total_size = int(resp.headers.get("Content-Length", 0))
            start_byte = 0

            # 设置断点续传头
            if start_byte > 0:
                resume_header = {"Range": f"bytes={start_byte}-"}
                self.HEADERS.update(resume_header)
                print("服务器支持断点续传，开始继续下载...")

            # 发起请求
            resp = session.get(download_url, headers=self.HEADERS, stream=True, verify=self.VERIFY)

            # 检查服务器是否支持断点续传
            if start_byte > 0 and resp.status_code != 206:
                print("服务器不支持断点续传，重新下载整个文件")
                start_byte = 0
                self.HEADERS.pop("Range", None)  # 删除断点续传的header
                resp = session.get(download_url, headers=self.HEADERS, stream=True, verify=self.VERIFY)

            # 初始化进度条
            with download_progress_bar as progress:
                task = progress.add_task(
                    "[bold blue]下载中...",
                    filename=filepath.name.strip(".downloaded"),
                    start=True,
                    total=total_size,
                    completed=start_byte
                )

                # 打开文件，追加或写入模式
                mode = 'ab' if start_byte > 0 else 'wb'
                with open(filepath, mode) as file:
                    for data in resp.iter_content(chunk_size=8192):
                        file.write(data)
                        progress.update(task, advance=len(data))
                        progress.refresh()

                progress.remove_task(task)
                # 去掉 .downloaded的后缀
                self.DOWNLOADING_FILE.rename(self.TEMP_DOWNLOAD_FILE)
                print("下载完成！")
                return True
        except RequestException as e:
            print(f"\n拉取出了点小问题, 不过无伤大雅\t({e})")
            return False
        finally:
            if session is not None:
                session.close()  # 关闭会话

    def download(self, download_url: str) -> None:
        try:
            print("下载更新文件")
            for i, proxy in enumerate(self.PROXYS):
                print(f"正在尝试从第 {i + 1} 个下载线路下载, 请稍后...(剩余 {len(self.PROXYS)-i-1} 个备用线路待尝试)")
                if self._download(download_url, self.DOWNLOADING_FILE, proxy):
                    break
            else:
                raise Exception("服务器连接失败")
        except Exception as e:
            print(f"下载更新时出错: {e}")
            os.system("pause")
            exit(1)
        except KeyboardInterrupt:
            print("下载更新已取消")
            if os.path.exists(self.DOWNLOADING_FILE):
                need_remove = input("是否删除下载的部分? (删除后，需要重新下载) (y/n)").strip().lower()
                os.remove(self.DOWNLOADING_FILE) if need_remove == "y" else None
            os.system("pause")
            exit(0)

    def unzip(self):
        if is_process_running("SRA.exe"):
            task_kill("SRA.exe")
            sleep(2)
        try:
            print("解压更新文件")
            if not os.path.exists(self.APP_PATH / "tools/7z.exe"):
                print(f"解压工具丢失，请手动解压{self.TEMP_DOWNLOAD_FILE}到当前文件夹")
                os.system("pause")
                return
            command = f"{self.APP_PATH}/tools/7z x {self.TEMP_DOWNLOAD_FILE} -y"
            cmd = 'cmd.exe /c start "" ' + command
            Popen(cmd, shell=True, stdout=DEVNULL, stderr=DEVNULL)

        except Exception as e:
            print(f"解压更新时出错: {e}")
            os.system("pause")


if __name__ == "__main__":
    main = Updater()
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", help="Download URL of file")
    # parser.add_argument("-d","--directory", help="The directory where the file was downloaded")
    parser.add_argument("-p", "--proxy", help="Proxy URL. If nothing, use default proxys.")
    parser.add_argument("-np", "--no-proxy", action="store_true", help="Do not use proxy.")
    parser.add_argument("-v", "--verify", help="Whether to enable SSL certificate verification. Default: True")
    args = parser.parse_args()

    if args.proxy is not None:
        main.PROXYS = [args.proxy]
    if args.no_proxy:
        main.PROXYS = [""]
    if args.verify == "False":
        main.VERIFY = False
    # if args.directory is not None:
    #     main.TEMP_DOWNLOAD_FILE=args.directory
    if args.url is not None:
        main.download(args.url)
        main.unzip()
    else:
        main.check_for_updates()
    print("完美运行!")
    os.system("pause")
