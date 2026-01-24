from pathlib import Path

from SRACore.task import BaseTask
from SRACore.util import sys_util, encryption
from SRACore.util.logger import logger


class StartGameTask(BaseTask):
    def run(self):
        logger.info("启动游戏任务开始")
        self.launch_game()
        return self.login_and_enter_game()

    def login_and_enter_game(self):
        match self.login():
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
            "resources/img/enter.png",
            "resources/img/train_supply.png",
            "resources/img/task_resources_manage.png",
            "resources/img/restart_for_update.png"
        ], timeout=120, interval=2)
        if res == 0:
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
            self.operator.click_img("resources/img/ensure2.png")
            return self.login_and_enter_game()  # 递归调用重新登录进入游戏
        else:
            logger.error("未能进入游戏，发生未知错误")
            return False

    def launch_game(self):
        """启动游戏"""
        if sys_util.is_process_running("StarRail.exe"):  # 检查游戏是否已在运行
            logger.info("游戏已在运行中")
            return
        path = Path(self.settings.get('GamePath')) if self.config.get("StartGameUseGlobalPath", True) else Path(
            self.config.get('StartGamePath'))
        logger.debug(f"游戏启动路径: {path}")
        # 根据配置选择游戏路径
        match self.config.get('StartGameChannel'):
            case 0:
                logger.info("正在启动官服游戏客户端...")
                self.change_config_ini(path, 1, 1)
            case 1:
                logger.info("正在启动B站服游戏客户端...")
                self.change_config_ini(path, 14, 0)
            case 2:
                logger.info("正在启动国际服游戏客户端...")
            case _:
                logger.error("未知的游戏渠道配置")
                raise RuntimeError("未知的游戏渠道配置")

        if not path or path == "":
            logger.error("未设置游戏启动路径")
            raise RuntimeError("未设置游戏启动路径")

        # 构建启动参数
        launch_args = []
        if self.settings.get('LaunchArgumentsPopupWindow', False):
            launch_args.append('-popupwindow')

        # 添加高级参数
        advanced_args = self.settings.get('LaunchArgumentsAdvanced', '').strip()
        if advanced_args:
            launch_args.extend(advanced_args.split())

        # 根据配置选择启动方式
        use_cmd = self.settings.get('LaunchWithCmd', False)
        if use_cmd:
            logger.info("使用 CMD 启动游戏")
            import subprocess
            cmd = f'start "" "{path}" {" ".join(launch_args)}'
            subprocess.Popen(cmd, shell=True)
        else:
            sys_util.Popen([str(path)] + launch_args)

    @staticmethod
    def change_config_ini(path: Path, channel, sub_channel):
        """修改配置文件"""
        root_path = path.parent
        config_file = root_path / 'config.ini'
        with open(config_file, 'r') as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith('channel='):
                lines[lines.index(line)] = f'channel={channel}\n'
            elif line.startswith('sub_channel='):
                lines[lines.index(line)] = f'sub_channel={sub_channel}\n'
        with open(config_file, 'w') as f:
            f.writelines(lines)

    def login(self):
        channel = None
        match self.config['StartGameChannel']:
            case 0:
                channel = 'cn'
            case 1:
                channel = 'bl'
            case 2:
                channel = 'gb'
            case _:
                logger.error("未知的游戏渠道配置")
                raise RuntimeError("未知的游戏渠道配置")

        result, _ = self.operator.wait_any_img([
            f'resources/img/sg/{channel}/login_page.png',
            f'resources/img/sg/{channel}/welcome.png',
            "resources/img/quit.png",
            "resources/img/enter.png"
        ], timeout=60, interval=1)

        if result == -1:
            logger.error("等待登录界面超时")
            return -1
        if result != 0:
            logger.info(f"登录状态 {result}")
            enable = self.config['StartGameAlwaysLogin']
            if enable and result != 3:  # 是否启用退出账号
                self.logout()  # 执行退出账号后执行下面的登录操作
            else:
                return result  # 直接返回登录状态

        self.operator.click_img(f'resources/img/sg/{channel}/login_other.png', after_sleep=1)
        self.operator.click_img(f"resources/img/sg/{channel}/login_with_account.png", after_sleep=1)
        if self.config['StartGameAutoLogin']:
            user = encryption.win_decryptor(self.config['StartGameUsername'])
            passwd = encryption.win_decryptor(self.config['StartGamePassword'])
            if user == "" or passwd == "":
                logger.error("未设置自动登录账号或密码")
                return -1
            logger.info(f"登录账号：{user}")
            self.operator.click_img(f"resources/img/sg/{channel}/username_input.png", after_sleep=1)
            self.operator.copy(user)
            self.operator.paste()
            self.operator.sleep(1)
            self.operator.press_key("tab")
            self.operator.sleep(0.2)
            self.operator.copy(passwd)
            self.operator.paste()
            self.operator.click_img(f"resources/img/sg/{channel}/agree.png", x_offset=-35, after_sleep=1)
            if not self.operator.click_img(f"resources/img/sg/{channel}/enter_game.png"):
                logger.error("发生错误，错误编号9")
                return -1
        else:
            logger.info("未启用自动登录，请手动完成登录")
        if self.operator.wait_img(f"resources/img/sg/{channel}/welcome.png", timeout=120):
            return 1
        else:
            logger.warning("长时间未成功登录，可能密码错误或需要验证")
            return -1

    def logout(self):
        logger.info("登出账号")
        box = self.operator.wait_ocr("登出", timeout=60, interval=1, from_x=0.9375, from_y=0.1204, to_x=0.96875, to_y=0.3935)
        if box:
            self.operator.click_box(box, after_sleep=1)
            if not self.operator.click_img("resources/img/quit2.png", after_sleep=1):
                self.operator.click_img("resources/img/ensure3.png", after_sleep=1)
            return True
        return False

    def start_game_click(self):
        result, _ = self.operator.wait_ocr_any(["开始游戏", "点击进入"], timeout=60, interval=1, from_x=0.44,
                                               from_y=0.74, to_x=0.57, to_y=0.97)
        if result == 0:
            self.operator.click_point(0.5, 0.6, after_sleep=1.5)
            self.operator.wait_ocr("点击进入", timeout=20, interval=1, from_x=0.44, from_y=0.74, to_x=0.57, to_y=0.97)
            self.operator.click_point(0.5, 0.5)
            return True
        elif result == 1:
            self.operator.click_point(0.5, 0.5)
            return True
        else:
            return False
