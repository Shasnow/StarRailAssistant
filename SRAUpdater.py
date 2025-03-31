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
import hashlib
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

from SRACore.utils.WindowsProcess import is_process_running, task_kill, Popen

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
    transient=False,
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
    VERSION_FILE = APP_PATH / "version.json"
    HASH_URL = "https://gitee.com/yukikage/sraresource/raw/main/SRA/hash.json"
    HASH_FILE = APP_PATH / "data/hash.json"
    PROXYS = []
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
        self.init_proxy()
        if os.path.exists(self.TEMP_DOWNLOAD_FILE):
            os.remove(self.TEMP_DOWNLOAD_FILE)

    def init_proxy(self):
        with open("version.json","r",encoding="utf-8") as file:
            self.PROXYS=json.load(file)["Proxys"]

    def init_version_file(self):
        if not os.path.exists(self.VERSION_FILE):
            print("初始化版本信息...")
            version_info = {"version": "0.0.0", "resource_version": "0.0.0", "Announcement": ""}
            with open(self.VERSION_FILE, "w", encoding="utf-8") as json_file:
                json.dump(version_info, json_file, indent=4)

    @staticmethod
    def hash_calculate(file_path, hash_algo=hashlib.sha256):
        """计算文件的哈希值"""
        with open(file_path, 'rb') as f:
            data = f.read()
            return hash_algo(data).hexdigest()

    def hash_check(self):
        try:
            response = requests.get(f"{self.HASH_URL}", timeout=10)
            saved_hashes = response.json()
        except RequestException as e:
            print(e)
            raise Exception(f"服务器连接失败")

        # 检查当前文件的哈希值
        inconsistent_files = []
        for file_path, saved_hash in saved_hashes.items():
            if os.path.exists(file_path):  # 检查文件是否存在
                current_hash = self.hash_calculate(file_path)
                if current_hash != saved_hash:
                    inconsistent_files.append(file_path)
            else:
                inconsistent_files.append(file_path)
        return inconsistent_files

    def integrity_check(self):
        print("正在进行资源完整性检查...")
        result = self.hash_check()
        if len(result) != 0:
            print(f"{len(result)}个文件丢失或不是最新的")
            self.download_all(result)
        else:
            print("所有文件均为最新")

    def download_all(self, filelist: list):
        print('下载所需文件...')
        for file in filelist:
            try:
                if os.path.exists(file):
                    os.remove(file)
                self.simple_download(f'https://pub-f5eb43d341f347bb9ab8712e19a5eb51.r2.dev/SRA/{file}', file)
            except Exception as e:
                print("下载失败",e)

    @staticmethod
    def simple_download(url,path):
        try:
            try:
                response = requests.get(url, stream=True)
                file_size = response.headers.get("Content-Length")
            except RequestException:
                print(f"请求超时")
                return
            if file_size is None:
                file_size = 1
            else:
                file_size = int(file_size)
            with download_progress_bar as progress:
                task = progress.add_task(
                    "[bold blue]下载中...",
                    filename=path,
                    start=True,
                    total=file_size,
                    completed=0
                )
                with open(path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        progress.update(task,advance=len(chunk))
                        progress.refresh()

                    progress.remove_task(task)
            print(f"{path}下载完成")
        except Exception as e:
            print(f"下载更新时出错: {e}")
            os.system("pause")

    @lru_cache(maxsize=1)
    def get_current_version(self) -> VersionInfo:
        with open(self.APP_PATH / "version.json", "r", encoding="utf-8") as jsonfile:
            version_info_local = json.load(jsonfile)
            version = version_info_local["version"]
            resource_version = version_info_local["resource_version"]
            announcement = version_info_local["Announcement"]
        return VersionInfo(version, resource_version, announcement, "")

    def announcement_change(self, text):
        with open(self.APP_PATH / "version.json", "r+", encoding="utf-8") as json_file:
            version = json.load(json_file)
            version["Announcement"] = text
        with open(self.APP_PATH / "version.json", "w", encoding="utf-8") as json_file:
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
            raise

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
            self.hash_check()
            return ""
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
                    filename=filepath.name,
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
            return True
        except RequestException as e:
            print(e)
            return False
        finally:
            if session is not None:
                session.close()  # 关闭会话

    def download(self, download_url: str) -> None:
        try:
            print("下载更新文件")
            for proxy in self.PROXYS:
                if self._download(download_url, self.DOWNLOADING_FILE, proxy):
                    self.DOWNLOADING_FILE.rename(self.TEMP_DOWNLOAD_FILE)
                    print("下载完成！")
                    break
                else:
                    continue
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
            Popen(cmd, shell=True)

        except Exception as e:
            print(f"解压更新时出错: {e}")
            os.system("pause")

    @staticmethod
    def version():
        print("SRAUpdater 2.6.0 2025-03-01\nCopyright © <2024> <Shasnow>")


if __name__ == "__main__":
    updater = Updater()
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", help="Download URL of file")
    # parser.add_argument("-d","--directory", help="The directory where the file was downloaded")
    parser.add_argument("-p", "--proxy", help="Proxy URL. If nothing, use default proxys.")
    parser.add_argument("-np", "--no-proxy", action="store_true", help="Do not use proxy.")
    parser.add_argument("-nv", "--no-verify", action="store_true", help="Disable SSL certificate verification.")
    parser.add_argument("-v", "--version", action="store_true", help="")
    parser.add_argument("-f", "--force", action="store_true", help="")
    parser.add_argument("-i", "--integrity-check", action="store_true", help="")
    args = parser.parse_args()

    if args.version:
        updater.version()
        exit(0)
    if args.integrity_check:
        updater.integrity_check()
        exit(0)
    if args.proxy is not None:
        updater.PROXYS = [args.proxy]
    if args.no_proxy:
        updater.PROXYS = [""]
    if args.no_verify:
        updater.VERIFY = False
    # if args.directory is not None:
    #     main.TEMP_DOWNLOAD_FILE=args.directory
    if args.url is not None:
        updater.download(args.url)
        updater.unzip()
    else:
        updater.check_for_updates()
