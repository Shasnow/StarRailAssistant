import enum
import typing
if typing.TYPE_CHECKING:
    from SRACore.operators.model import Box

from SRACore.operators.factory import OperatorType
from SRACore.task import BaseTask, task
from SRACore.util import encryption
from SRACore.util.logger import logger
from tasks.img import IMG, SGIMG

class LoginStatus(enum.IntEnum):
    """登录状态枚举"""
    UNKNOWN_PAGE = -1
    LOGIN_PAGE = 0
    WELCOME_PAGE = 1
    ENTER_GAME_PAGE = 2
    IN_GAME_PAGE = 3
    NEW_VERSION_PAGE = 4

@task(order=0)
class StartGameTask(BaseTask):
    """启动游戏任务"""

    def run(self):
        logger.info("启动游戏任务开始")
        self.launch_game()
        delay = self.config.StartGame.launchDelay
        logger.info(f"游戏已启动, {delay}秒后开始自动化操作")
        self.operator.sleep(delay)
        return self.login_and_enter_game()

    def login_and_enter_game(self, _retry_count: int = 0):
        max_retries = 3
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
            # 月卡界面可能因网络波动或设备性能延迟弹出，等待确认
            if self.operator.wait_img(SGIMG.TRAIN_SUPPLY, timeout=3, interval=1):
                self._collect_monthly_card()
                return True
            if self.operator.type == "Browser":
                self.operator.change_auto_battle(True)  # 云游戏需要在进入游戏后切换自动战斗模式
            return True
        elif res == 1:
            self._collect_monthly_card()
            return True
        elif res == 2:
            logger.error("未能进入游戏，需要下载过往任务资源。")
            return False
        elif res == 3:
            if _retry_count >= max_retries:
                logger.error(f"重启游戏更新后仍无法进入，已尝试 {max_retries} 次")
                return False
            logger.info("需要重启游戏以完成更新，正在重启游戏...")
            self.operator.click_img(IMG.ENSURE2)
            return self.login_and_enter_game(_retry_count=_retry_count + 1)  # 递归调用重新登录进入游戏
        else:
            logger.error(f"未知游戏状态，当前状态码: {res}，预期状态码: 0~3")
            return False

    def _collect_monthly_card(self):
        """领取月卡奖励"""
        self.operator.sleep(1)
        self.operator.click_point(0.5, 0.6, after_sleep=4)
        self.operator.click_point(0.5, 0.8, after_sleep=0.2)
        self.operator.click_point(0.5, 0.5, y_offset=+400)

    def launch_game(self):
        """启动游戏"""
        if self.operator.type == "Browser":
            self.operator.launch(0, "")
            return
        if self.config.StartGame.isUseGlobalGamePath:
            game_path_index = self.settings.General.gamePathIndex
            game_paths: list[str] = self.settings.General.gamePaths
            raw_path = game_paths[game_path_index] if game_path_index < len(game_paths) else None
        else:
            raw_path = self.config.StartGame.gamePath
        if not raw_path:
            logger.error("未设置游戏启动路径")
            raise ValueError("未设置游戏启动路径")
        self.operator.launch(channel=self.config.StartGame.gameChannel, path=raw_path)

    def login(self) -> int:
        """登录游戏

        Returns:
            int: -1 登录失败，1 登录成功，2 欢迎界面，3 已在游戏中
        """
        if self.operator.type == OperatorType.Browser:
            return self._browser_login()
        status = self._detect_login_state()
        if status is None:  # 等待登录界面超时
            return -1
        if status != LoginStatus.LOGIN_PAGE:  # 不在登录界面，说明已经登录过
            logger.info(f"登录状态 {status}")
            if status == LoginStatus.NEW_VERSION_PAGE:
                logger.error("游戏需要更新，请手动更新游戏后重试")
                return -1
            if self.config.StartGame.isReLogin and status != LoginStatus.IN_GAME_PAGE:
                self.logout()  # 登出后走账号密码登录
            else:
                return status
        return self._account_login()

    def _browser_login(self) -> int:
        """云游戏登录，由浏览器 Operator 处理"""
        user = encryption.decryptor(self.config.StartGame.EncryptedUsername)
        passwd = encryption.decryptor(self.config.StartGame.EncryptedPassword)
        return self.operator.login(user, passwd, relogin=self.config.StartGame.isReLogin)

    def _detect_login_state(self) -> LoginStatus | None:
        """检测当前登录状态，遇到隐私协议界面自动点击同意并重新检测（最多 3 次）

        Returns:
            LoginStatus | None: 当前登录状态；等待登录界面超时返回 None
        """
        login_pages = [
                SGIMG.SETTINGS,
                IMG.ENTER,
                SGIMG.NEW_VERSION]
        for _ in range(3):
            index, result = self.operator.wait_any([
                lambda: self.operator.locate_any(login_pages),
                lambda: self.operator.ocr_match("同意"),
                lambda: self.operator.ocr_match_any(["登录", "欢迎"])],
                timeout=60, interval=1)
            match index:
                case -1:
                    logger.error("等待登录界面超时，请检查游戏状态")
                    return None
                case 0:  # 特征图片定位
                    page_index:int = typing.cast(int, result[0])
                    return (LoginStatus.ENTER_GAME_PAGE, LoginStatus.IN_GAME_PAGE, LoginStatus.NEW_VERSION_PAGE)[page_index]
                case 1:  # 隐私协议界面，点击同意后重新检测
                    self.operator.click_box(typing.cast('Box', result), after_sleep=1)
                case 2:  # OCR 匹配到"登录"/"欢迎"
                    ocr_index, _ = typing.cast(tuple, result)
                    return LoginStatus.LOGIN_PAGE if ocr_index == 0 else LoginStatus.WELCOME_PAGE
        return LoginStatus.UNKNOWN_PAGE

    def _account_login(self) -> int:
        """进入账号密码界面完成登录，并等待欢迎界面出现"""
        self.operator.click_box(self.operator.ocr_match("其他账号"))
        self.operator.move_to(0.5, 0.5)  # 移动到中心位置, 防止按钮提示文本干扰
        self.operator.sleep(1)
        if self._game_channel() != 'gb':  # 国际服客户端此页面直接暴露账号输入框
            self.operator.click_box(self.operator.ocr_match("密码"))
            self.operator.move_to(0.5, 0.5)  # 移动到中心位置, 防止按钮提示文本干扰
            self.operator.sleep(1)
        if self.config.StartGame.isAutoLogin:
            if not self._fill_credentials():
                return -1
        else:
            logger.info("未启用自动登录，请手动完成登录")
        if self.operator.wait_ocr("欢迎", from_x=0.5, from_y=0.07, to_x=0.6, to_y=0.2, timeout=180):
            return 1
        logger.warning("登录后等待欢迎界面超时，请检查游戏状态")
        return -1

    def _fill_credentials(self) -> bool:
        """自动填写账号密码并点击登录

        Returns:
            bool: 是否配置了账号密码并完成登录点击
        """
        user = encryption.decryptor(self.config.StartGame.EncryptedUsername)
        passwd = encryption.decryptor(self.config.StartGame.EncryptedPassword)
        if user == "" or passwd == "":
            logger.error("自动登录账号或密码未设置，请检查配置中的自动登录账号和密码")
            return False
        logger.info(f"登录账号：{user[:3]}*****{user[-3:]}")
        boxes = self.operator.ocr_boxes()
        if boxes is None:
            raise RuntimeError("未检测到登录界面")
        email_box = login_box = None
        for box in boxes:
            if "邮箱" in box.source:
                email_box = box
            if "登录" in box.source or "进入游戏" in box.source:
                login_box = box
        if email_box is None or login_box is None:
            raise RuntimeError("未检测到登录界面输入框，请检查游戏状态")
        self.operator.click_box(email_box, after_sleep=1)
        self.operator.copy(user)
        self.operator.paste()
        self.operator.sleep(1)
        self.operator.press_key("tab")
        self.operator.sleep(0.2)
        self.operator.copy(passwd)
        self.operator.paste()
        self.operator.click_box(login_box, after_sleep=1)
        boxes = self.operator.ocr_boxes()
        if boxes is None:
            raise RuntimeError("未检测到同意隐私政策界面，请检查游戏状态")
        for box in boxes:
            if box.source == "同意" or box.source == "同意并继续":
                self.operator.click_box(box, after_sleep=1)
                break
        return True

    def _game_channel(self) -> str:
        """将游戏渠道配置转换为渠道标识"""
        match self.config.StartGame.gameChannel:
            case 0:
                return 'cn'
            case 1:
                return 'bl'
            case 2:
                return 'gb'
            case _:
                raise ValueError(f"未知的游戏渠道配置，当前配置值 {self.config.StartGame.gameChannel}")

    def select_global_server(self):
        """Select and confirm the configured global server before login."""
        labels = ["Asia", "Europe", "America", "TW,HK,MO"]
        server_index = max(0, min(int(getattr(self.config.StartGame, "gameServer", 0)), len(labels) - 1))
        target = labels[server_index]
        # All four bounds are required for cropped OCR so the returned box is
        # offset back into window coordinates correctly before click_box().
        index, box = self.operator.wait_ocr_any(
            labels,
            timeout=15,
            from_x=0,
            from_y=0.55,
            to_x=1,
            to_y=0.95,
        )
        if index < 0 or box is None:
            logger.warning("未检测到国际服区服选择器，跳过区服切换")
            return False
        logger.info(f"打开国际服区服选择器，当前区服: {labels[index]}，目标区服: {target}")
        self.operator.click_box(box, after_sleep=1)
        index, _ = self.operator.wait_ocr_any(["服务器列表", "Server List"], timeout=10)
        if index < 0:
            logger.warning("未检测到国际服区服选择弹窗")
            return False
        index, box = self.operator.wait_ocr_any([target], timeout=10)
        if index < 0 or box is None:
            logger.warning(f"未检测到国际服目标区服: {target}")
            return False
        self.operator.click_box(box, after_sleep=0.5)
        index, box = self.operator.wait_ocr_any(["确认", "Confirm"], timeout=5)
        if index >= 0 and box is not None:
            self.operator.click_box(box, after_sleep=1)
            logger.info(f"已选择国际服区服: {target}")
            return True
        logger.warning(f"国际服区服选择未找到确认按钮: {target}")
        return False

    def logout(self):
        logger.info("登出账号")
        idx, box = self.operator.wait_ocr_any(["登出", "登入"], interval=1, timeout=60, from_x=0.9375, from_y=0.1204,
                                              to_x=0.96875, to_y=0.3935)
        if idx == 1:
            # 已经在登录界面，无需登出
            return True
        if box:
            self.operator.click_box(box, after_sleep=1)
            if not self.operator.click_img(IMG.QUIT2, after_sleep=1):
                self.operator.click_img(IMG.ENSURE3, after_sleep=1)
            return True
        return False

    def start_game_click(self):
        if self.config.StartGame.gameChannel == 2:
            self.select_global_server()
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
