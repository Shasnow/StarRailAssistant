"""
StarRailAssistant 错误码定义

错误码格式：SRA-XXXX-YYYY
- SRA: StarRailAssistant 缩写
- XXXX: 模块代码（4位数字）
- YYYY: 具体错误代码（4位数字）

错误级别：
- 1XXX: 系统级错误（致命错误，需要立即处理）
- 2XXX: 配置错误（配置文件或参数错误）
- 3XXX: 操作错误（窗口操作、OCR等操作失败）
- 4XXX: 任务错误（任务执行失败）
- 5XXX: 网络错误（网络请求失败）
- 6XXX: 资源错误（文件、图片等资源加载失败）
- 7XXX: 逻辑错误（业务逻辑错误）
- 8XXX: 用户错误（用户操作错误）
- 9XXX: 其他错误（未分类的错误）
"""

from enum import IntEnum
from typing import Any


class ErrorCode(IntEnum):
    """错误码枚举"""

    # ========== 1XXX: 系统级错误 ==========
    # 1000-1099: 系统初始化错误
    SYSTEM_INIT_FAILED = 1001  # 系统初始化失败
    SYSTEM_SHUTDOWN_FAILED = 1002  # 系统关闭失败
    SYSTEM_RESOURCE_EXHAUSTED = 1003  # 系统资源耗尽

    # 1100-1199: 线程和进程错误
    THREAD_STOPPED = 1100  # 线程已停止
    THREAD_CREATE_FAILED = 1101  # 线程创建失败
    THREAD_START_FAILED = 1102  # 线程启动失败
    THREAD_STOP_FAILED = 1103  # 线程停止失败
    PROCESS_CREATE_FAILED = 1104  # 进程创建失败
    PROCESS_KILL_FAILED = 1105  # 进程终止失败

    # 1200-1299: 权限错误
    ADMIN_PRIVILEGES_REQUIRED = 1201  # 需要管理员权限
    FILE_ACCESS_DENIED = 1202  # 文件访问被拒绝
    REGISTRY_ACCESS_DENIED = 1203  # 注册表访问被拒绝

    # ========== 2XXX: 配置错误 ==========
    # 2000-2099: 配置文件错误
    CONFIG_FILE_NOT_FOUND = 2001  # 配置文件未找到
    CONFIG_FILE_CORRUPTED = 2002  # 配置文件损坏
    CONFIG_PARSE_ERROR = 2003  # 配置文件解析错误
    CONFIG_INVALID_FORMAT = 2004  # 配置文件格式无效

    # 2100-2199: 配置项错误
    CONFIG_ITEM_MISSING = 2101  # 配置项缺失
    CONFIG_ITEM_INVALID = 2102  # 配置项无效
    CONFIG_ITEM_OUT_OF_RANGE = 2103  # 配置项超出范围
    CONFIG_ITEM_TYPE_MISMATCH = 2104  # 配置项类型不匹配

    # ========== 3XXX: 操作错误 ==========
    # 3000-3099: 窗口操作错误
    WINDOW_NOT_FOUND = 3001  # 窗口未找到
    WINDOW_INACTIVE = 3002  # 窗口未激活
    WINDOW_ACTIVATE_FAILED = 3003  # 窗口激活失败
    WINDOW_REGION_INVALID = 3004  # 窗口区域无效

    # 3100-3199: OCR识别错误
    OCR_ENGINE_NOT_INITIALIZED = 3101  # OCR引擎未初始化
    OCR_RECOGNITION_FAILED = 3102  # OCR识别失败

    # 3200-3299: 图像识别错误
    IMAGE_NOT_FOUND = 3201  # 图像未找到
    IMAGE_MATCH_FAILED = 3202  # 图像匹配失败
    IMAGE_LOAD_FAILED = 3203  # 图像加载失败
    IMAGE_INVALID_FORMAT = 3204  # 图像格式无效
    SCREENSHOT_FAILED = 3205  # 截图失败

    # 3300-3399: 鼠标键盘操作错误
    MOUSE_MOVE_FAILED = 3301  # 鼠标移动失败
    MOUSE_CLICK_FAILED = 3302  # 鼠标点击失败
    KEYBOARD_INPUT_FAILED = 3303  # 键盘输入失败
    HOTKEY_CONFLICT = 3304  # 热键冲突

    # ========== 4XXX: 任务错误 ==========
    # 4000-4099: 任务管理错误
    TASK_NOT_FOUND = 4001  # 任务未找到
    TASK_LOAD_FAILED = 4002  # 任务加载失败
    TASK_START_FAILED = 4003  # 任务启动失败
    TASK_STOP_FAILED = 4004  # 任务停止失败
    TASK_TIMEOUT = 4005  # 任务超时
    TASK_INTERRUPTED = 4006  # 任务被中断

    # 4100-4199: 启动游戏任务错误
    LOGIN_FAILED = 4101  # 登录失败
    LOGIN_TIMEOUT = 4102  # 登录超时
    UPDATE_REQUIRED = 4103  # 需要更新游戏

    # 4200-4299: 体力任务错误
    NO_POWER = 4201  # 没有体力
    NO_BUILD_TARGET = 4202  # 没有训练目标
    POWER_DETECTION_FAILED = 4203  # 体力检测失败
    NO_SAVE = 4204  # 没有存档
    CLICK_LEVEL_FAILED = 4205  # 点击关卡失败
    WAIT_BATTLE_BOTTON_TIMEOUT = 4206  # 等待挑战按钮超时失败
    CLICK_BATTLE_BUTTON_FAILED = 4207  # 点击挑战按钮失败
    RELICS_LIMIT = 4208  # 背包内遗器数量超过限制
    CLICK_BATTLE_STAR_FAILED = 4209  # 点击开始挑战按钮失败
    CLICK_AGAIN_BUTTON_FAILED = 4210  # 点击再次挑战按钮失败
    QUIT_BATTLE_FAILED = 4211  # 退出战斗失败
    SESSION_NOT_FOUND = 4212  # 副本类别未找到
    REPLENISH_POWER_FAILED = 4213  # 补充体力失败

    # 4300-4399: 领取奖励任务错误

    # 4400-4499: 货币战争任务错误
    CURRENCY_WARS_START_FAILED = 4401  # 货币战争启动失败
    CURRENCY_WARS_GAME_OVER = 4402  # 货币战争游戏结束
    CURRENCY_WARS_CHARACTER_PLACE_FAILED = 4403  # 角色放置失败
    CURRENCY_WARS_INVEST_ENV_INVALID = 4404  # 投资环境无效
    CURRENCY_WARS_INVEST_STRATEGY_INVALID = 4405  # 投资策略无效
    CURRENCY_WARS_BOSS_AFFIX_INVALID = 4406  # Boss词缀无效

    # 4500-4599: 任务结束错误

    # 4600-4999: 其他/通用任务错误
    GO_TO_SURVIVAL_INDEX_FAILED = 4601  # 跳转到生存索引失败
    WAIT_TIMEOUT = 4602  # 等待超时

    # ========== 5XXX: 网络错误 ==========
    # 5000-5099: HTTP请求错误
    HTTP_REQUEST_FAILED = 5001  # HTTP请求失败
    HTTP_TIMEOUT = 5002  # HTTP请求超时
    HTTP_CONNECTION_ERROR = 5003  # HTTP连接错误
    HTTP_RESPONSE_ERROR = 5004  # HTTP响应错误

    # 5100-5199: API错误
    API_NOT_AVAILABLE = 5101  # API不可用
    API_RATE_LIMIT_EXCEEDED = 5102  # API请求频率超限
    API_AUTH_FAILED = 5103  # API认证失败
    API_VERSION_MISMATCH = 5104  # API版本不匹配

    # 5200-5299: 更新错误
    UPDATE_CHECK_FAILED = 5201  # 更新检查失败
    UPDATE_DOWNLOAD_FAILED = 5202  # 更新下载失败
    UPDATE_INSTALL_FAILED = 5203  # 更新安装失败

    # ========== 6XXX: 资源错误 ==========
    # 6000-6099: 文件操作错误
    FILE_NOT_FOUND = 6001  # 文件未找到
    FILE_READ_FAILED = 6002  # 文件读取失败
    FILE_WRITE_FAILED = 6003  # 文件写入失败
    FILE_DELETE_FAILED = 6004  # 文件删除失败
    FILE_COPY_FAILED = 6005  # 文件复制失败

    # 6100-6199: 资源加载错误
    RESOURCE_LOAD_FAILED = 6101  # 资源加载失败
    RESOURCE_MISSING = 6102  # 资源缺失
    RESOURCE_CORRUPTED = 6103  # 资源损坏
    RESOURCE_VERSION_MISMATCH = 6104  # 资源版本不匹配

    # ========== 7XXX: 逻辑错误 ==========
    # 7000-7099: 业务逻辑错误
    INVALID_OPERATION = 7001  # 无效操作
    OPERATION_NOT_SUPPORTED = 7002  # 不支持的操作
    OPERATION_CANCELLED = 7003  # 操作已取消
    OPERATION_IN_PROGRESS = 7004  # 操作正在进行中

    # 7100-7199: 数据验证错误
    DATA_VALIDATION_FAILED = 7101  # 数据验证失败
    DATA_INCONSISTENT = 7102  # 数据不一致
    DATA_OUT_OF_RANGE = 7103  # 数据超出范围
    DATA_TYPE_MISMATCH = 7104  # 数据类型不匹配

    # 7200-7299: 状态错误
    INVALID_STATE = 7201  # 无效状态
    STATE_TRANSITION_FAILED = 7202  # 状态转换失败
    STATE_NOT_READY = 7203  # 状态未就绪

    # ========== 8XXX: 用户错误 ==========
    # 8000-8099: 用户输入错误
    INVALID_INPUT = 8001  # 无效输入
    INPUT_OUT_OF_RANGE = 8002  # 输入超出范围
    INPUT_FORMAT_INVALID = 8003  # 输入格式无效

    # 8100-8199: 用户操作错误
    OPERATION_ABORTED = 8101  # 操作中止
    OPERATION_SKIPPED = 8102  # 操作跳过
    OPERATION_RETRY_EXCEEDED = 8103  # 操作重试次数超限

    # ========== 9XXX: 其他错误 ==========
    UNKNOWN_ERROR = 9001  # 未知错误
    UNEXPECTED_ERROR = 9002  # 意外错误
    DEPRECATED_FEATURE = 9003  # 已弃用的功能


class SRAError(Exception):
    """StarRailAssistant 基础异常类"""

    def __init__(self, error_code: ErrorCode, message: str, details: str | None = None):
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(f"[{error_code.value}] {message}")

    def __str__(self):
        if self.details:
            return f"[{self.error_code.value}] {self.message}: {self.details}"
        return f"[{self.error_code.value}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_code': self.error_code.value,
            'error_name': self.error_code.name,
            'message': self.message,
            'details': self.details
        }


class ThreadStoppedError(SRAError):
    def __init__(self, message: str, details: str | None = None):
        super().__init__(ErrorCode.THREAD_STOPPED, message, details)


def format_error(error: Exception) -> str:
    """格式化错误信息"""
    if isinstance(error, SRAError):
        return str(error)
    else:
        return f"[UNKNOWN_ERROR] {type(error).__name__}: {str(error)}"


__all__ = [
    'ErrorCode',
    'SRAError',
    'ThreadStoppedError',
    'format_error'
]
