import enum
import time
import typing
import re

from SRACore.util.strutil import EqualsMatcher, RegexMatcher, StrMatcher

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

    # 登出确认弹窗的标题/说明文案，用于判断弹窗是否已关闭
    LOGOUT_CONFIRM_TITLE = RegexMatcher(r"退出登录|退出并保留登录记录|确定要退出")
    # 弹窗确认按钮
    LOGOUT_CONFIRM_BUTTON = EqualsMatcher("退出")
    # 滑块验证码文案，出现时只能人工处理
    SLIDER_CAPTCHA_TEXT = "请拖动滑块完成拼图"

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
                self.operator.change_auto_battle(True)  # 云游戏需要在进入游戏后切换自动战斗模式  # pyright: ignore[reportAttributeAccessIssue]
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
                # 登出失败时沿用当前登录状态，避免在残留弹窗遮挡的界面上继续走账号登录
                if not self.logout():  # 登出后走账号密码登录
                    logger.warning("登出失败，沿用当前登录状态继续")
                    return status
            else:
                return status
        if self._try_history_account_login():  # 密码留空时的免密码历史账号切号
            return 1
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
        # 顺序即优先级：滑块验证码需最先识别，避免被同屏的「登录」按钮抢先命中
        login_texts: list[str | StrMatcher] = [
            self.SLIDER_CAPTCHA_TEXT,
            "登录",
            "欢迎",
            EqualsMatcher("同意"),
            "开始游戏"]
        for _ in range(3):
            index, result = self.operator.wait_any([
                lambda: self.operator.locate_any(login_pages),
                lambda: self.operator.ocr_match_any(login_texts)],
                timeout=60, interval=1)
            match index:
                case -1:
                    logger.error("等待登录界面超时，请检查游戏状态")
                    return None
                case 0:  # 特征图片定位
                    page_index: int = typing.cast(int, result[0])  # pyright: ignore[reportOptionalSubscript, reportIndexIssue]
                    return (LoginStatus.ENTER_GAME_PAGE, LoginStatus.IN_GAME_PAGE, LoginStatus.NEW_VERSION_PAGE)[page_index]
                case 1:  # OCR 匹配
                    ocr_index, box = typing.cast(tuple, result)
                    match ocr_index:
                        case 0:  # 滑块验证码 - 只能人工完成，完成后重新检测
                            if not self._wait_slider_captcha():
                                return None
                        case 1:  # "登录"
                            return LoginStatus.LOGIN_PAGE
                        case 2:  # "欢迎"
                            return LoginStatus.WELCOME_PAGE
                        case 3:  # "同意" - 隐私协议界面，点击后重新检测
                            self.operator.click_box(typing.cast('Box', box), after_sleep=1)
                        case 4:  # "开始游戏" - 已保存登录记录，可直接进入
                            return LoginStatus.ENTER_GAME_PAGE
        return LoginStatus.UNKNOWN_PAGE

    def _wait_slider_captcha(self, timeout: float = 180) -> bool:
        """等待人工完成滑块验证码

        Args:
            timeout: 最长等待秒数

        Returns:
            bool: 验证码是否已完成
        """
        logger.warning("检测到滑块验证码，请在游戏窗口中手动拖动滑块完成验证")
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.operator.sleep(2)
            if self.operator.ocr_match(self.SLIDER_CAPTCHA_TEXT) is None:
                logger.info("滑块验证码已完成")
                return True
        logger.error("等待滑块验证码超时，请检查游戏状态")
        return False

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
        if self.operator.wait_ocr_any(["欢迎", "开始游戏", "点击进入"], from_x=0.44, from_y=0.07, to_x=0.6, to_y=0.9, timeout=180):
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

    def logout(self) -> bool:
        """登出当前账号

        Returns:
            bool: 是否已处于登录界面（登出成功或本身无需登出）
        """
        logger.info("登出账号")
        idx, box = self.operator.wait_ocr_any(["登出", "登入"], interval=1, timeout=60, from_x=0.9375, from_y=0.1204,
                                              to_x=0.96875, to_y=0.3935)
        if idx == 1:
            # 已经在登录界面，无需登出
            return True
        if box is None:
            logger.warning("未找到登出按钮")
            return False
        self.operator.click_box(box, after_sleep=1)
        # 先尝试模板点击确认按钮；失败则由 _confirm_logout_dialog 用 OCR 兜底
        self.operator.click_img(IMG.QUIT2, after_sleep=1)
        if self._confirm_logout_dialog():
            return True
        logger.warning("登出确认弹窗未能关闭，登录界面可能被遮挡")
        return False

    def _confirm_logout_dialog(self) -> bool:
        """点击登出确认弹窗的确认按钮，并校验弹窗已关闭

        Returns:
            bool: 弹窗是否已关闭
        """
        for _ in range(3):
            box = self.operator.ocr_match(self.LOGOUT_CONFIRM_BUTTON, from_x=0.325,from_y=0.3, to_x=0.675, to_y=0.7)
            if box is None:
                return True
            self.operator.click_box(box, after_sleep=1)
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
    def _try_history_account_login(self) -> bool:
        """免密码历史账号切号：密码留空且账号非空时，账号字段作为切号提示词。

        在登录页点击账号信息框触发客户端历史账号下拉，选中目标账号后由客户端
        回填其记住的密码完成登录，SRA 侧零密码存储。失败时回退原有登录流程。

        Returns:
            bool: 是否已通过历史账号完成登录
        """
        user = encryption.decryptor(self.config.StartGame.EncryptedUsername)
        passwd = encryption.decryptor(self.config.StartGame.EncryptedPassword)
        if user == "" or passwd != "":
            return False  # 密码已配置或账号为空，走原有账号密码流程
        if self._game_channel() == 'gb':
            # 国际服登录页布局与国服不同（账号输入框直接暴露、文案为英文），
            # 未经实测，暂不支持；后续可在此分支单独实现
            logger.info("历史账号切号暂不支持国际服，走原有登录流程")
            return False
        logger.info(f"密码未配置，尝试历史账号切号（提示词: {user}）")
        try:
            ok = self._switch_by_history(user)
        except RuntimeError as e:
            logger.error(f"历史账号切号失败: {e}")
            return False
        if not ok:
            return False
        if self.operator.wait_ocr_any(
            ["欢迎", "开始游戏", "点击进入"],
            from_x=0.44, from_y=0.07, to_x=0.6, to_y=0.9, timeout=180,
        ):
            return True
        logger.warning("切号后等待欢迎界面超时，请检查游戏状态")
        return False

    @staticmethod
    def _norm_acct(s: str) -> str:
        """去除星号等非字母数字字符，用于账号比对"""
        return re.sub(r"[^0-9A-Za-z]", "", s or "")

    def _acct_match(self, hint: str, raw: str) -> bool:
        """提示词与界面显示文本的归一化比对。

        完整手机号/邮箱对掩码显示（如 123****21）按「前缀+后缀+总长度」匹配，
        避免单纯去星号让两个首尾相同的账号撞在一起。
        """
        h, t = self._norm_acct(hint), self._norm_acct(raw)
        if not h or not t:
            return False
        if h in t or t in h:
            return True
        m = re.search(r"(\d{2,4})\*{2,}(\d{2,4})", (raw or "").strip())
        if m and h.isdigit():
            pre, suf = m.group(1), m.group(2)
            if len(h) >= len(pre) + len(suf) and h.startswith(pre) and h.endswith(suf):
                return True
        return False

    def _switch_by_history(self, hint: str) -> bool:
        """点击账号信息框触发历史账号下拉 → 选中目标账号 → 确认登录。

        下拉候选只取账号框下方、水平位置邻近的文本，避免「账号密码」
        「忘记密码」等同屏文本混入；未命中时把候选写入日志便于排查。
        Returns:
            bool: 是否选中了目标账号并点击了登录
        """
        boxes = self.operator.ocr_boxes()
        if boxes is None:
            raise RuntimeError("未检测到登录界面")
        acct = login = None
        for box in boxes:
            src = box.source or ""
            if ("登录" in src or "进入游戏" in src) and "其他账号" not in src:
                login = box  # 「登录其他账号」是入口按钮，不是确认键
            if acct is None and (re.search(r"\d{2,4}\*{2,}\d{2,4}", src) or "邮箱" in src):
                acct = box  # 快速登录页的脱敏账号框 / 账密页的邮箱输入框
        if acct is None or login is None:
            raise RuntimeError("未检测到账号信息框或登录按钮，请检查游戏画面")

        self.operator.click_box(acct, after_sleep=1)  # 触发历史账号下拉
        acct_cx = acct.left + acct.width // 2
        span = max(acct.width * 3, 200)
        target, seen = None, []
        deadline = time.time() + 8
        while time.time() < deadline and target is None:
            for box in self.operator.ocr_boxes() or []:
                cx = box.left + box.width // 2
                if box.top < acct.top or abs(cx - acct_cx) > span:
                    continue  # 只认账号框下方、水平邻近的条目（下拉列表区域）
                txt = box.source or ""
                if txt and txt not in seen:
                    seen.append(txt)
                if txt != (acct.source or "") and self._acct_match(hint, txt):
                    target = box
                    break
            if target is None:
                self.operator.sleep(0.5)
        if target is None:
            logger.error(f"下拉列表中未找到账号「{hint}」，识别到的候选: {seen[:10]}")
            return False
        logger.info(f"选中历史账号: {target.source}")
        self.operator.click_box(target, after_sleep=2)  # 客户端自动回填记住的密码

        confirm = None  # 下拉可能遮挡原坐标，重新定位确认按钮
        for box in self.operator.ocr_boxes() or []:
            src = box.source or ""
            if ("登录" in src or "进入游戏" in src) and "其他账号" not in src:
                confirm = box
                break
        if confirm is not None:
            self.operator.click_box(confirm, after_sleep=1)
        for box in self.operator.ocr_boxes() or []:  # 同意隐私政策弹窗兜底
            if box.source in ("同意", "同意并继续"):
                self.operator.click_box(box, after_sleep=1)
                break
        return True
