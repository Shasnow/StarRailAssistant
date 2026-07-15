from SRACore.task import BaseTask, task
from SRACore.util import encryption
from SRACore.util.errors import SRAError, ErrorCode
from SRACore.util.logger import logger
from tasks.img import IMG, SGIMG

@task(order=0)
class StartGameTask(BaseTask):
    def run(self):
        logger.info("启动游戏任务开始")
        self.launch_game()
        return self.login_and_enter_game()

    def login_and_enter_game(self):
        self.operator.screenshot_background = False  # 暂时关闭后台截图
        login_result = self.login()
        self.operator.screenshot_background = True
        match login_result:
            case -1 | 0:
                logger.warning("登录失败")
                return False
            case 1 | 2:
                logger.info("登录成功")
            case 3:
                logger.info("已进入游戏")
                return True
            case _:
                logger.error("未知登录状态")
                return False
        self.start_game_click()
        res, _ = self.operator.wait_any_img([
            IMG.ENTER,
            SGIMG.TRAIN_SUPPLY,
            SGIMG.TASK_RESOURCES_MANAGE,
            SGIMG.RESTART_FOR_UPDATE
        ], timeout=120, interval=2)
        if res == 0:
            if self.operator.type == "Browser":
                self.operator.change_auto_battle(True)  # 云游戏需要在进入游戏后切换自动战斗模式
            return True
        elif res == 1:
            # 领取月卡
            self.operator.sleep(1)
            self.operator.click_point(0.5, 0.6, after_sleep=4)
            self.operator.click_point(0.5, 0.8, after_sleep=0.2)
            self.operator.click_point(0.5, 0.5, y_offset=+400)
            return True
        elif res == 2:
            logger.error("未能进入游戏，需要下载过往任务资源。")
            return False
        elif res == 3:
            logger.info("需要重启游戏以完成更新，正在重启游戏...")
            self.operator.click_img(IMG.ENSURE2)
            return self.login_and_enter_game()  # 递归调用重新登录进入游戏
        else:
            logger.error(SRAError(ErrorCode.INVALID_STATE, "未知游戏状态", f"当前状态码: {res}，预期状态码: 0~3"))
            return False

    def launch_game(self):
        """启动游戏"""
        if self.operator.type == "Browser":
            self.operator.launch(0,"")
            return
        if self.config.StartGame.isUseGlobalGamePath:
            game_path_index = self.settings.General.gamePathIndex
            game_paths:list[str] = self.settings.General.gamePaths
            raw_path = game_paths[game_path_index] if game_path_index < len(game_paths) else None
        else:
            raw_path = self.config.StartGame.gamePath
        if not raw_path:
            logger.error("未设置游戏启动路径")
            raise SRAError(ErrorCode.INVALID_INPUT, "未设置游戏启动路径")
        self.operator.launch(channel=self.config.StartGame.gameChannel, path=raw_path)

    def login(self):
        if hasattr(self.operator, 'driver'):
            user = encryption.decryptor(self.config.StartGame.EncryptedUsername)
            passwd = encryption.decryptor(self.config.StartGame.EncryptedPassword)
            return self.operator.login(user, passwd)
        channel = None
        match self.config.StartGame.gameChannel:
            case 0:
                channel = 'cn'
            case 1:
                channel = 'bl'
            case 2:
                channel = 'gb'
            case _:
                raise SRAError(ErrorCode.INVALID_INPUT, "未知的游戏渠道配置", f"当前配置值 {self.config.StartGame.gameChannel}")

        result, _ = self.operator.wait_any_img([
            SGIMG.LOGIN_PAGE % channel,
            SGIMG.WELCOME % channel,
            SGIMG.SETTINGS,
            IMG.ENTER,
            SGIMG.NEW_VERSION,
            SGIMG.AGREE1
        ], timeout=60, interval=1)

        if result == -1:
            logger.error(SRAError(ErrorCode.LOGIN_TIMEOUT, "等待登录界面超时", "请检查游戏状态"))
            return -1
        if result == 5:
            self.operator.click_box(_, after_sleep=1)
            result = 0
        if result != 0:
            logger.info(f"登录状态 {result}")
            enable = self.config.StartGame.isReLogin
            if result == 4:
                # 游戏需要更新
                logger.error(SRAError(ErrorCode.UPDATE_REQUIRED, "游戏需要更新", "请手动更新游戏后重试"))
                return -1
            if enable and result != 3:  # 是否启用退出账号
                self.logout()  # 执行退出账号后执行下面的登录操作
            else:
                return result  # 直接返回登录状态

        self.operator.click_img(SGIMG.LOGIN_OTHER % channel, after_sleep=1)
        self.operator.click_img(SGIMG.LOGIN_WITH_ACCOUNT % channel, after_sleep=1)
        if self.config.StartGame.isAutoLogin:
            user = encryption.decryptor(self.config.StartGame.EncryptedUsername)
            passwd = encryption.decryptor(self.config.StartGame.EncryptedPassword)
            if user == "" or passwd == "":
                logger.error(SRAError(ErrorCode.INVALID_INPUT, "自动登录账号或密码未设置", "请检查配置中的自动登录账号和密码"))
                return -1
            logger.info(f"登录账号：{user}")
            self.operator.click_img(SGIMG.USERNAME_INPUT % channel, after_sleep=1)
            self.operator.copy(user)
            self.operator.paste()
            self.operator.sleep(1)
            self.operator.press_key("tab")
            self.operator.sleep(0.2)
            self.operator.copy(passwd)
            self.operator.paste()
            self.operator.click_img(SGIMG.AGREE % channel, x_offset=-35, after_sleep=1)
            self.operator.click_img(SGIMG.ENTER_GAME % channel)
        else:
            logger.info("未启用自动登录，请手动完成登录")

        if self.operator.wait_img(SGIMG.WELCOME % channel, timeout=120):
            return 1
        else:
            logger.warning(SRAError(ErrorCode.LOGIN_FAILED, "登录后等待欢迎界面超时", "请检查游戏状态"))
            return -1

    def logout(self):
        logger.info("登出账号")
        idx, box = self.operator.wait_ocr_any(["登出", "登入"], interval=1, timeout=60, from_x=0.9375, from_y=0.1204,
                                              to_x=0.96875, to_y=0.3935)
        if idx==1:
            # 已经在登录界面，无需登出
            return True
        if box:
            self.operator.click_box(box, after_sleep=1)
            if not self.operator.click_img(IMG.QUIT2, after_sleep=1):
                self.operator.click_img(IMG.ENSURE3, after_sleep=1)
            return True
        return False

    def start_game_click(self):
        result, _ = self.operator.wait_ocr_any(["开始游戏", "点击进入"], interval=1, timeout=60, from_x=0.44,
                                               from_y=0.74, to_x=0.57, to_y=0.97)
        if result == 0:
            self.operator.click_point(0.5, 0.6, after_sleep=1.5)
            self.operator.wait_ocr("点击进入", interval=1, timeout=20, from_x=0.44, from_y=0.74, to_x=0.57, to_y=0.97)
            self.operator.click_point(0.5, 0.5)
            return True
        elif result == 1:
            self.operator.click_point(0.5, 0.5)
            return True
        else:
            return False
