from ..utils.Logger import logger
from ..Exceptions import NotImplementException
from ..utils.ComputerOperator import ComputerOperator
from ..utils.ImgLocater import ImageLocater
from ..utils.WindowLocater import WindowLocater
from ..utils._types import Config
from ..utils._const import GAME_IMG
import subprocess

class StarRail:
    """
    和游戏核心的操作都在这里,这里就主要写游戏的一些启动，关闭，日志记录等逻辑，其他的游戏逻辑有额外的实现
    """
    def __init__(self, config: Config, resouce_path: str) -> None:
        self.logger = logger
        self.window_locater = WindowLocater("崩坏：星穹铁道")
        self.config = config
        self.resouce_path = resouce_path
        self.computer = ComputerOperator()
        self.image_locater = ImageLocater()
        try:
            self.initilaize()
        except NotImplementException:
            self.logger.warning("没有自定义的初始化,跳过自定义初始化")
            pass
        self.logger.info("默认初始化完成")

    def initilaize(self):
        """
        自定义初始化方法, 子类可以重写该方法
        """
        raise NotImplementException("请在子类中实现该方法")
    
    def isRunning(self) -> bool:
        """
        判断游戏是否在运行
        """
        self.logger.info("检测游戏状态")
        hwnd = self.window_locater.find_window()
        if hwnd:
            self.logger.info("游戏仍在运行")
            return True
        else:
            self.logger.warning("游戏可能被最小化或者关闭")
            return False
        
    def launchGame(self):
        """
        启动游戏
        """
        self.logger.info("崩坏：星穹铁道, 启动！")
        try:
            if not self.isRunning():
                path = self.config['gamePath']
                subprocess.Popen(path)
                self.logger.info("游戏已启动")
            else:
                self.logger.warning("游戏已在运行, 请勿重复启动")
        except Exception:
            self.logger.exception("启动游戏失败,详情请看堆栈信息", is_fatal=True)
        
    def closeGame(self):
        """
        退出游戏
        """
        self.logger.info("退出游戏")
        cmd = "taskkill /f /im StarRail.exe"
        subprocess.run(cmd, shell=True, check=True)
        self.logger.info("游戏已退出")


    def isNotStarRailPath(self, path: str) -> bool:
        if path:
            if path.split('/')[-1].split('.')[0] != 'StarRail':
                self.logger.warning(fr"路径{path}不是星穹铁道的, 请检查")
                return False
            else:
                return True
        else:
            self.logger.warning("路径为空, 请检查")
            return False
    
    def login(self, account: str = '', password: str = '') -> None:
        """
        登录游戏
        """
        try:
            if self.image_locater.checkOnWindow(fr"{self.resouce_path}/{GAME_IMG['welcome']}", 2):
                self.logger.debug("用户已登录")
            elif self.image_locater.checkOnWindow(fr"{self.resouce_path}/{GAME_IMG['not_logged_in']}", 2, 4):
                 self.logger.debug("用户未登录")
                 if self.computer.click_screen(fr"{self.resouce_path}/{GAME_IMG['login_with_account']}"):
                    self.logger.debug("开始登录")
                    self.computer.write_on_screen(account,watting_time=1)
                    self.computer.press_key('tab',interval=0.1)
                    self.computer.write_on_screen(password, watting_time=1)
                    self.computer.click_screen(fr"{self.resouce_path}/{GAME_IMG['agree']}", -158)
            else:
                self.logger.warning("未知的登录状态, 请检查")
        except Exception:
            self.logger.exception("登录失败, 请检查账号密码是否正确", is_fatal=True)

