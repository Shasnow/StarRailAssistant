
import enum

class AssistantSignal(enum.Enum):
    """
    信号枚举类
    """
    EXIT_REQUIRE = "exit_require"  # 退出程序请求
    CLEAN_REQUIRE = "clean_require"  # 伴随清理请求
    TASK_COMPLETE = "task_complete"  # 任务完成信号
    TASK_ERROR = "task_error"  # 任务错误信号
    TASK_ABORT = "task_abort"  # 任务中止信号
    RESTART_REQUIRE = "restart_require"  # 重启程序请求
    WAKE_UP_REQUIRE = "wake_up_require"  # 唤醒程序请求