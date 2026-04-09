"""
脚本仓库管理器
负责：仓库管理、脚本列表获取、脚本下载/更新、本地脚本扫描
"""
import json
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests

from SRACore.util.const import AppDataSraDir
from SRACore.util.logger import logger

# 已安装脚本目录
ScriptsDir = AppDataSraDir / "scripts"
# 仓库配置文件
ReposConfigPath = AppDataSraDir / "script_repos.json"


@dataclass
class ScriptTaskDef:
    """脚本内的单个任务定义"""
    name: str = ""
    entry: str = ""      # Python 文件名，如 task_a.py
    class_name: str = "" # 类名，如 TaskA


@dataclass
class ScriptManifest:
    """本地脚本的 manifest.json"""
    id: str = ""
    name: str = ""
    version: str = ""
    description: str = ""
    author: str = ""
    tasks: list[ScriptTaskDef] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> "ScriptManifest":
        m = ScriptManifest(
            id=d.get("id", ""),
            name=d.get("name", ""),
            version=d.get("version", "0.0.0"),
            description=d.get("description", ""),
            author=d.get("author", ""),
        )
        for t in d.get("tasks", []):
            m.tasks.append(ScriptTaskDef(
                name=t.get("name", ""),
                entry=t.get("entry", ""),
                class_name=t.get("class", ""),
            ))
        return m

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "tasks": [{"name": t.name, "entry": t.entry, "class": t.class_name} for t in self.tasks],
        }


@dataclass
class RepoScriptInfo:
    """仓库索引中的脚本信息"""
    id: str = ""
    name: str = ""
    version: str = ""
    description: str = ""
    author: str = ""
    download_url: str = ""
    # 对比本地版本后设置
    installed_version: Optional[str] = None
    has_update: bool = False

    @property
    def is_installed(self) -> bool:
        return self.installed_version is not None


@dataclass
class ScriptRepo:
    """脚本仓库配置"""
    name: str = ""
    url: str = ""        # repo.json 的 URL
    enabled: bool = True


class ScriptManager:
    """脚本管理器（单例）"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        ScriptsDir.mkdir(parents=True, exist_ok=True)

    # ===== 仓库管理 =====

    def load_repos(self) -> list[ScriptRepo]:
        """加载已配置的仓库列表"""
        if not ReposConfigPath.exists():
            return []
        try:
            with open(ReposConfigPath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [ScriptRepo(**r) for r in data.get("repos", [])]
        except Exception as e:
            logger.error(f"加载仓库配置失败: {e}")
            return []

    def save_repos(self, repos: list[ScriptRepo]):
        """保存仓库列表"""
        try:
            with open(ReposConfigPath, "w", encoding="utf-8") as f:
                json.dump({"repos": [r.__dict__ for r in repos]}, f,
                          ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存仓库配置失败: {e}")

    def add_repo(self, name: str, url: str) -> bool:
        """添加仓库"""
        repos = self.load_repos()
        if any(r.url == url for r in repos):
            logger.warning(f"仓库已存在: {url}")
            return False
        repos.append(ScriptRepo(name=name, url=url))
        self.save_repos(repos)
        return True

    def remove_repo(self, url: str):
        """删除仓库"""
        repos = [r for r in self.load_repos() if r.url != url]
        self.save_repos(repos)

    # ===== 仓库脚本列表 =====

    def fetch_repo_scripts(self, repo: ScriptRepo) -> list[RepoScriptInfo]:
        """从仓库拉取脚本列表，并与本地版本对比"""
        try:
            resp = requests.get(repo.url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"拉取仓库 {repo.url} 失败: {e}")
            return []

        installed = self.get_installed_scripts()
        installed_map = {s.id: s.version for s in installed}

        result = []
        for item in data.get("scripts", []):
            info = RepoScriptInfo(
                id=item.get("id", ""),
                name=item.get("name", ""),
                version=item.get("version", "0.0.0"),
                description=item.get("description", ""),
                author=item.get("author", ""),
                download_url=item.get("download_url", ""),
            )
            if info.id in installed_map:
                info.installed_version = installed_map[info.id]
                info.has_update = info.version != info.installed_version
            result.append(info)
        return result

    # ===== 本地脚本管理 =====

    def get_installed_scripts(self) -> list[ScriptManifest]:
        """扫描本地已安装的脚本"""
        scripts = []
        if not ScriptsDir.exists():
            return scripts
        for d in ScriptsDir.iterdir():
            if not d.is_dir():
                continue
            manifest_path = d / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                scripts.append(ScriptManifest.from_dict(data))
            except Exception as e:
                logger.warning(f"读取脚本 manifest 失败: {d}, {e}")
        return scripts

    def get_script_dir(self, script_id: str) -> Path:
        return ScriptsDir / script_id

    # ===== 下载/安装 =====

    def download_and_install(self, info: RepoScriptInfo,
                              on_progress=None) -> bool:
        """下载并安装脚本（zip 格式）"""
        if not info.download_url:
            logger.error(f"脚本 {info.id} 没有下载地址")
            return False

        script_dir = self.get_script_dir(info.id)
        tmp_zip = AppDataSraDir / f"_tmp_{info.id}.zip"

        try:
            if on_progress:
                on_progress(0, f"正在下载 {info.name}...")

            resp = requests.get(info.download_url, timeout=60, stream=True)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(tmp_zip, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if on_progress and total > 0:
                        on_progress(int(downloaded / total * 80),
                                    f"下载中 {downloaded // 1024}KB / {total // 1024}KB")

            if on_progress:
                on_progress(80, "正在解压...")

            if script_dir.exists():
                shutil.rmtree(script_dir)
            script_dir.mkdir(parents=True)

            with zipfile.ZipFile(tmp_zip, "r") as z:
                # 解压，自动去掉顶层文件夹
                members = z.namelist()
                top = members[0].split("/")[0] if members else ""
                for member in members:
                    stripped = member[len(top)+1:] if member.startswith(top+"/") else member
                    if not stripped:
                        continue
                    target = script_dir / stripped
                    if member.endswith("/"):
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(member) as src, open(target, "wb") as dst:
                            dst.write(src.read())

            if on_progress:
                on_progress(100, "安装完成")

            logger.info(f"脚本 {info.id} 安装成功")
            return True

        except Exception as e:
            logger.error(f"安装脚本 {info.id} 失败: {e}")
            if script_dir.exists():
                shutil.rmtree(script_dir, ignore_errors=True)
            return False
        finally:
            if tmp_zip.exists():
                tmp_zip.unlink(missing_ok=True)

    def uninstall(self, script_id: str) -> bool:
        """卸载脚本"""
        script_dir = self.get_script_dir(script_id)
        if script_dir.exists():
            shutil.rmtree(script_dir)
            logger.info(f"脚本 {script_id} 已卸载")
            return True
        return False

    def check_updates(self) -> list[RepoScriptInfo]:
        """检查所有仓库中已安装脚本的更新"""
        updates = []
        for repo in self.load_repos():
            if not repo.enabled:
                continue
            scripts = self.fetch_repo_scripts(repo)
            updates.extend([s for s in scripts if s.has_update])
        return updates


# 全局单例
script_manager = ScriptManager()
