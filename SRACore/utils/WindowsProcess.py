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
Windows进程操作
"""
import subprocess
import winreg

import psutil
import win32con
import win32gui


def find_window(title) -> int | None:
    """Find window handles based on the window title

    Args:
        title (str): Window title.
    Returns:
        The first found window handle, None otherwise.
    """

    def enum_callback(hwnd, result):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) == title:
            result.append(hwnd)

    windows = []
    win32gui.EnumWindows(enum_callback, windows)
    return windows[0] if windows else None


def is_window_active(window_title) -> bool:
    """Check if the specified window is active.

    Args:
        window_title (str): The title of the window to check.
    Returns:
        True if the window is active, False otherwise.
    """
    hwnd = find_window(window_title)
    if hwnd:
        return win32gui.GetForegroundWindow() == hwnd
    return False

def check_window(window_title) -> bool:
    """Check that the game is running by window title.

    Returns:
        True if game is running, False if not.
    """

    hwnd = find_window(window_title)
    if hwnd:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)  # 确保窗口不是最小化状态
        win32gui.SetForegroundWindow(hwnd)
        return True
    else:
        return False


def is_process_running(process_name) -> bool:
    """
    Check if there is any running process that contains the given name string.

    Args:
        process_name (str): Name of the process to be searched.
    Returns:
        True if the process is running, otherwise False.
    """
    # Iterate over all running processes
    for proc in psutil.process_iter(['name']):
        try:
            # Check if the process name contains the given name string
            if process_name.lower() in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def task_kill(process: str) -> bool:
    """关闭指定进程

    Args:
        process (str): 进程名
    Returns:
        bool
    """
    for proc in psutil.process_iter(['name']):
        try:
            if process.lower() in proc.info['name'].lower():
                proc.kill()
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def open_normal(path: str) -> bool:
    """运行指定exe程序并等待

        Args:
            path: 程序路径

        Returns:
            True if opened successfully, False otherwise.
        """
    try:
        subprocess.run(path)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def Popen(path: str|list[str], shell=False) -> bool:
    """运行指定exe程序

    Args:
        shell: 通过shell运行
        path: 程序路径

    Returns:
        True if opened successfully, False otherwise.
    """
    try:
        psutil.Popen(path, shell=shell)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_startup_item(program_name, program_path) -> bool:
    """设置进程的开机启动

    Args:
        program_name (str): 启动项名称
        program_path (str): 启动项路径

    Returns:
        True if successfully set, False otherwise.
    """
    try:
        key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, program_name, 0, winreg.REG_SZ, program_path)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def delete_startup_item(item_name: str) -> bool:
    """
    删除开机启动项
    Args:
        item_name: 启动项名称

    Returns:
        True if successfully delete, False otherwise.
    """
    try:
        startup_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                                     winreg.KEY_SET_VALUE | winreg.KEY_WOW64_32KEY)
        winreg.DeleteValue(startup_key, item_name)
        winreg.CloseKey(startup_key)
        return True
    except Exception:
        return False
