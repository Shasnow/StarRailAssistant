class Logger:
    """日志记录器类"""

    def info(self, message=""):
        """记录信息级别日志"""
        print(message)

    def warning(self, message=""):
        """记录警告级别日志"""
        print(message)

    def error(self, message=""):
        """记录错误级别日志"""
        print(message)

    def success(self, message=""):
        """记录成功级别日志"""
        print(message)

    def debug(self, message=""):
        """记录调试级别日志"""
        print(message)

    def trace(self, message=""):
        """记录追踪级别日志"""
        print(message)

    def exception(self, message=""):
        """记录异常级别日志"""
        print(message)


# 实例化日志记录器

logger = Logger()
__all__ = ["logger"]