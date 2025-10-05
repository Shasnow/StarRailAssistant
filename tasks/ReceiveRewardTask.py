from SRACore.tasks.BaseTask import BaseTask
from SRACore.util.logger import logger


class ReceiveRewardTask(BaseTask):
    def __init__(self, config: dict):
        super().__init__("receive_reward", config)
        self.config_name=config.get('name', 'unknown')

    def run(self):
        # 初始化任务
        tasks, tasks2 = self._init_tasks()

        # 校验界面状态
        if not self._prepare_ui():
            return False

        # 执行任务组1（带参数）
        if tasks and not self._execute_tasks_with_args(tasks):
            return False

        # 执行任务组2（无参数）
        if tasks2 and not self._execute_tasks_without_args(tasks2):
            return False

        return True

    def _init_tasks(self):
        """根据配置初始化任务列表"""
        tasks = []
        item_select = self.config['item_select']

        # 主任务列表（需要传参的任务）esc界面完成的
        if item_select[0]:
            tasks.append((self.trailblazer_profile, ()))
        if item_select[1]:
            tasks.append((self.assignments_reward, ()))
        if item_select[6]:
            tasks.append((self.redeem_code, (self.config["redeem_code_list"],)))
        if item_select[2]:
            tasks.append((self.mail, ()))

        # 次要任务列表（无参数任务）
        tasks2 = []
        if item_select[3]:
            tasks2.append(self.daily_training_reward)
        if item_select[4]:
            tasks2.append(self.nameless_honor)
        if item_select[5]:
            tasks2.append(self.gift_of_odyssey)

        return tasks, tasks2

    def _prepare_ui(self):
        """等待进入主界面并打开菜单"""
        logger.info("领取奖励")
        if not self.wait_img("resources/img/enter.png", timeout=30):
            logger.error("检测超时，编号2")
            return False
        return True

    def _execute_tasks_with_args(self, tasks):
        """执行需要传参的任务列表"""
        # 打开ESC菜单
        self.press_key("esc")
        if not self.wait_ocr("开拓", timeout=20, from_x=0.656,from_y=0.222, to_x=0.740, to_y=0.278):
            return False

        for task, args in tasks:
            if self.stop_flag:
                break
            task(*args)
        else:
            self.sleep(2)  # 所有任务完成后等待2秒
            self.press_key("esc")  # 关闭菜单
            return True
        return False

    def _execute_tasks_without_args(self, tasks):
        """执行无参数的任务列表"""
        for task in tasks:
            if self.stop_flag:
                break
            task()
        else:
            return True
        return False

    def trailblazer_profile(self):
        """Mission trailblaze profile"""
        logger.info("执行任务：签证奖励")
        if self.click_point(0.92,0.10, after_sleep=1):
            if self.click_point(0.82,0.13, after_sleep=1):
                if self.click_img("resources/img/assistance_reward.png"):
                    self.sleep(1)
                    self.press_key("esc", presses=2, interval=1.2)
                else:
                    logger.info("没有可领取的奖励1")
                    self.press_key("esc")
            else:
                logger.info("没有可领取的奖励2")
        else:
            logger.info("没有可领取的奖励3")
        logger.info("任务完成：签证奖励")

    def redeem_code(self, redeem_code_list):
        """Fills in redeem code and redeems them.

        Note:
            Do not include the `self` parameter in the ``Args`` section.
        Args:
            redeem_code_list (list): The list thar stored redeem codes.
        Returns:
            None
        """
        logger.info("执行任务：领取兑换码")
        if len(redeem_code_list) == 0:
            logger.warning("未填写兑换码")
        for code in redeem_code_list:
            self.sleep(1)
            if self.click_point(0.92, 0.10):
                if self.click_img("resources/img/redeem_code.png"):
                    self.sleep(2)
                    self.copy(code)
                    self.click_point(0.5, 0.5)
                    self.paste()
                    self.click_img("resources/img/ensure.png")
                    self.sleep(2)
                    self.press_key("esc")
                else:
                    logger.error("发生错误，错误编号16")
            else:
                logger.error("发生错误，错误编号17")
        logger.info("任务完成：领取兑换码")

    def mail(self):
        """Open mailbox and pick up mails."""
        logger.info("执行任务：领取邮件")
        if self.click_point(0.97,0.25, after_sleep=1.5):
            if self.click_img("resources/img/claim_all_mail.png"):
                self.sleep(2)
                self.press_key("esc", presses=2, interval=1)
            else:
                logger.info("没有可以领取的邮件")
                self.press_key("esc")
        else:
            logger.info("没有可以领取的邮件")
        logger.info("任务完成：领取邮件")

    def gift_of_odyssey(self):
        """Open the activity screen to receive gift_of_odyssey.

        Remember to update the gift_of_odyssey.png in each game version.
        """
        logger.info("执行任务：巡星之礼")
        if not self.wait_img("resources/img/enter.png", timeout=30):
            logger.error("检测超时，编号2")
            return
        self.press_key(self.config.get('key_f1', 'f1'))
        self.sleep(0.2)
        target=self.ocr_match("巡星之礼")
        if target is None:
            logger.info("没有巡星之礼活动")
            self.press_key("esc")
            return
        if self.click_img("resources/img/gift_receive.png") or self.click_img("resources/img/gift_receive2.png"):
            logger.info("领取成功")
            self.sleep(2)
            self.press_key("esc", presses=2, interval=2)
        else:
            logger.info("没有可以领取的巡星之礼")
            self.press_key("esc")
        logger.info("任务完成：巡星之礼")

    def assignments_reward(self):
        """Receive assignment reward"""
        logger.info("执行任务：领取派遣奖励")
        if not self.click_img("resources/img/assignments_none.png"):
            logger.info("没有可领取的奖励")
            return
        match self.wait_any_img(["resources/img/assignment_page.png", "resources/img/assignment_page2.png"],
                                timeout=10):
            case 0:
                pass
            case 1:
                self.click_point(0.34, 0.22)
            case _:
                logger.error("发生错误，错误编号7")
                self.press_key("esc")
                return

        if self.click_img("resources/img/assignments_reward.png", after_sleep=2):
            if self.click_img("resources/img/assign_again.png"):
                logger.info("再次派遣")
                while not self.ocr_match("开拓", from_x=0.656,from_y=0.222, to_x=0.740, to_y=0.278):
                    self.press_key("esc")
                    self.sleep(1)
            else:
                logger.error("发生错误，错误编号6")
                self.press_key("esc")
        else:
            logger.info("没有可以领取的派遣奖励")
            self.press_key("esc")
            self.sleep(2)
        logger.info("任务完成：领取派遣奖励")

    def daily_training_reward(self):
        """Receive daily training reward"""
        logger.info("执行任务：领取每日实训奖励")
        if not self.wait_img("resources/img/enter.png"):
            logger.error("检测超时，编号2")
            return
        self.press_key(self.config.get('key_f4', 'f4'))
        if not self.wait_img("resources/img/f4.png", timeout=20):
            logger.error("检测超时，编号1")
            self.press_key("esc")
            return
        if self.locate("resources/img/survival_index_onclick.png"):
            logger.info("没有可领取的奖励")
        else:
            while self.click_img("resources/img/daily_reward.png", after_sleep=0.5):
                self.move_rel(0, 50)

            if self.click_img("resources/img/daily_train_reward.png", after_sleep=1.5):
                self.press_key("esc")
                self.sleep(0.5)
                if self.locate("resources/img/daily_train_reward_notreach.png"):  # NOQA
                    logger.info("存在每日实训未达到要求")
            else:
                logger.info("没有可领取的奖励")
        self.screenshot().save(f"log/daily_training_reward-{self.config_name}.png")
        self.press_key("esc")
        logger.info("任务完成：领取每日实训奖励")

    def nameless_honor(self):
        """Receive nameless honor reward"""
        logger.info("执行任务：领取无名勋礼奖励")
        if not self.wait_img("resources/img/enter.png"):
            logger.error("检测超时，编号2")
            return
        self.press_key(self.config.get('key_f2', 'f2'))
        if not self.wait_img("resources/img/f2.png", timeout=20):
            logger.error("检测超时，编号1")
            self.press_key("esc")
            return
        if self.click_img("resources/img/nameless_honor_reward_receive.png", after_sleep=2):
            logger.info("领取了无名勋礼奖励")
            self.press_key("esc")
        if not self.click_img("resources/img/nameless_honor_task.png"):
            logger.info("没有可领取的奖励")
            self.press_key("esc")
            return
        if not self.click_img("resources/img/nameless_honor_task_receive.png"):
            logger.info("没有已完成的无名勋礼任务")
            self.press_key("esc")
            return
        logger.info("成功领取无名勋礼任务奖励")
        self.sleep(1)
        self.press_key("esc")
        if not self.click_img("resources/img/nameless_honor_reward.png"):
            logger.info("没有可领取的奖励")
            return
        if self.click_img("resources/img/nameless_honor_reward_receive.png", after_sleep=2):
            logger.info("领取了无名勋礼奖励")
            self.press_key("esc", presses=2, interval=2)
        else:
            logger.info("没有可领取的奖励")
        logger.info("完成任务：领取无名勋礼奖励")
