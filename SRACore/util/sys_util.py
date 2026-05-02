import sys
from typing import Any

import psutil
from pathlib import Path

def Popen(arg: str | Path | list[str], shell: bool = False, **kwargs: Any) -> bool:  # NOQA
    """
    Launches a process using the specified path.

    Args:
        arg (str | list[str]): The path to the executable or a list of arguments to execute.
        shell (bool): Whether to execute the command through the shell. Default is False.

    Returns:
        bool: True if the process is successfully launched, False otherwise.
    """
    try:
        psutil.Popen(arg, shell=shell, **kwargs)
        return True
    except FileNotFoundError:
        # Raised when the specified file or executable is not found.
        return False
    except OSError:
        # Raised for other OS-related errors during process creation.
        return False


def is_process_running(process_name: str) -> bool:
    """
    Check if there is any running process that contains the given name string.

    Args:
        process_name (str): Name of the process to be searched.
    Returns:
        True if the process is running, otherwise False.
    """
    # Iterate over all running processes
    for proc in psutil.process_iter(['name', 'status']):
        try:
            if process_name.lower() in proc.info['name'].lower():
                if proc.info['status'] == psutil.STATUS_ZOMBIE:
                    continue
                if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
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


def shutdown(time: int):
    """关机

    Args:
        time (int): 延时关机时间，单位秒
    """
    if time < 0:
        time = 0
    if sys.platform == "win32":
        Popen(f"shutdown -s -t {time}", shell=True)
    elif sys.platform == "linux":
        Popen(f"shutdown -h +{time // 60 if time >= 60 else 0}", shell=True)
    else:
        Popen("shutdown -h now", shell=True)


def shutdown_cancel():
    """取消关机"""
    if sys.platform == "win32":
        Popen("shutdown -a", shell=True)
    elif sys.platform == "linux":
        Popen("shutdown -c", shell=True)


def sleep_system():
    """将系统置于睡眠状态"""
    if sys.platform == "win32":
        Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
    elif sys.platform == "linux":
        Popen("systemctl suspend", shell=True)
    else:
        Popen("pm-suspend", shell=True)