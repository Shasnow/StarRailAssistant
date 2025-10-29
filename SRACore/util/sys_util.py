import psutil


def Popen(arg: str | list[str], shell: bool = False, **kwargs) -> bool:  # NOQA
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


def shutdown(time: int):
    """关机

    Args:
        time (int): 延时关机时间，单位秒
    """
    if time < 0:
        time = 0
    Popen(f"shutdown -s -t {time}", shell=True)


def shutdown_cancel():
    """取消关机"""
    Popen("shutdown -a", shell=True)