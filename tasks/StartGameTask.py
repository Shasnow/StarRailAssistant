from pathlib import Path

from SRACore.task import BaseTask
from SRACore.util import sys_util, encryption
from SRACore.util.logger import logger


class StartGameTask(BaseTask):
    def run(self):
        logger.info("启动游戏任务开始")
        self.launch_game()
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
        res,_ = self.wait_any_img(["resources/img/enter.png",
                                 "resources/img/train_supply.png",
                                 "resources/img/task_resources_manage.png"], timeout=120, interval=2)
        if res == 0:
            return True
        elif res == 1:
            # 领取月卡
            self.sleep(1)
            self.click_point(0.5, 0.6, after_sleep=4)
            self.click_point(0.5, 0.8, after_sleep=0.2)
            self.click_point(0.5, 0.5, y_offset=+400)
            return True
        elif res == 2:
            logger.error("未能进入游戏，需要下载过往任务资源。")
            return False
        else:
            logger.error("未能进入游戏，发生未知错误")
            return False

    def launch_game(self):
        """启动游戏"""
        if sys_util.is_process_running("StarRail.exe"):  # 检查游戏是否已在运行
            logger.info("游戏已在运行中")
            return
        if self.config['StartGameChannel'] == 0:
            self.launch_au()  # 启动官服
        else:
            self.launch_bl()  # 启动B站服

    def launch_bl(self):
        self.change_config_ini(14, 0)
        path = Path(self.config['StartGamePath'])
        sys_util.Popen(str(path), shell=True, cwd=path.parent)

    def launch_au(self):
        self.change_config_ini(1, 1)
        sys_util.Popen(self.config['StartGamePath'], shell=True)

    def change_config_ini(self, channel, sub_channel):
        """修改配置文件"""
        path = Path(self.config['StartGamePath'])
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
        if self.config['StartGameChannel'] == 0:
            return self.login_au()  # 登录官服
        else:
            return self.login_bl()  # 登录B站服

    def logout_outside(self):
        logger.info("登出账号")
        if self.wait_img("resources/img/logout.png", timeout=60):
            self.click_img("resources/img/logout.png")
        self.click_img("resources/img/quit2.png")
        return True

    def login_bl(self):
        result,_ = self.wait_any_img(['resources/img/bilibili_login.png', 'resources/img/bilibili_welcome.png',
                                    "resources/img/quit.png", "resources/img/enter.png"],
                                   timeout=60)
        if result == -1:
            logger.error("等待登录界面超时")
            return -1
        if result != 0:
            logger.info(f"登录状态 {result}")
            enable = self.config['StartGameAlwaysLogin']
            if enable and result != 3:  # 是否启用退出账号
                self.logout_outside()  # 执行退出账号后执行下面的登录操作
            else:
                return result  # 直接返回登录状态
        self.click_img("resources/img/bilibili_login_other.png", after_sleep=0.5)

        self.click_point(0.5, 0.69)  # 点击账号密码登录
        if self.config['StartGameAutoLogin']:
            user = encryption.win_decryptor(self.config['StartGameUsername'])
            logger.info(f"登录账号：{user}")
            self.press_key('tab')
            self.sleep(1)
            self.copy(user)
            self.paste()
            self.sleep(1)
            self.press_key("tab")
            self.sleep(0.2)
            self.copy(encryption.win_decryptor(self.config['StartGamePassword']))
            self.paste()
            self.sleep(0.2)
            self.click_point(0.37, 0.53)  # 同意隐私政策
            self.sleep(0.2)
            self.click_point(0.5, 0.6)  # 登录
        else:
            logger.info("未启用自动登录，请手动输入账号密码")
        if self.wait_img("resources/img/bilibili_welcome.png", timeout=60):
            return 1
        else:
            logger.warning("长时间未成功登录，可能密码错误或需要新设备验证")
            return -1

    def login_au(self):
        result, _ = self.wait_any_img(
            ["resources/img/login_page.png", "resources/img/welcome.png",
             "resources/img/quit.png", "resources/img/enter.png"], timeout=60, interval=1)
        if result == -1:
            logger.error("等待登录界面超时")
            return -1
        if result != 0:
            logger.info(f"登录状态 {result}")
            enable = self.config['StartGameAlwaysLogin']
            if enable and result != 3:  # 是否启用退出账号
                self.logout_outside()  # 执行退出账号后执行下面的登录操作
            else:
                return result  # 直接返回登录状态
        target=self.ocr_match("登录其他")
        if target is not None:
            self.click_box(target)

        if not self.click_img("resources/img/login_with_account.png"):
            logger.error("发生错误，错误编号10")
            return -1
        if self.config['StartGameAutoLogin']:
            user = encryption.win_decryptor(self.config['StartGameUsername'])
            if user == "":
                logger.error("未填写账号")
                return -1
            logger.info(f"登录账号：{user}")
            self.sleep(1)
            self.copy(user)
            self.paste()
            self.sleep(1)
            self.press_key("tab")
            self.sleep(0.2)
            self.copy(encryption.win_decryptor(self.config['StartGamePassword']))
            self.paste()
            self.click_img("resources/img/agree.png", x_offset=-158)
            if not self.click_img("resources/img/enter_game.png"):
                logger.error("发生错误，错误编号9")
                return -1
        else:
            logger.info("未启用自动登录，请手动输入账号密码")
        if self.wait_img("resources/img/welcome.png", timeout=60):
            return 1
        else:
            logger.warning("长时间未成功登录，可能密码错误或需要新设备验证")
            return -1

    def start_game_click(self):
        result,_ = self.wait_ocr_any(["开始游戏", "点击进入"], timeout=60, interval=1, from_x=0.44, from_y=0.74, to_x=0.57, to_y=0.97)
        if result == 0:
            self.click_point(0.5, 0.6, after_sleep=1.5)
            self.wait_ocr("点击进入", timeout=20, interval=1, from_x=0.44, from_y=0.74, to_x=0.57, to_y=0.97)
            self.click_point(0.5, 0.5)
            return True
        elif result == 1:
            self.click_point(0.5, 0.5)
            return True
        else:
            return False
