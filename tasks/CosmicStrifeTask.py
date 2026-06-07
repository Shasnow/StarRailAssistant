from SRACore.task import BaseTask, task
from SRACore.util.errors import ErrorCode, SRAError
from SRACore.util.logger import logger
from tasks.currency_wars.characters import Characters
from tasks.img import DUIMG, IMG

@task(order=3)
class CosmicStrifeTask(BaseTask):
    def run(self):
        """主任务执行函数"""
        if self.config.CosmicStrife.isDivergentUniverseEnabled:
            logger.info("执行任务：旷宇纷争-模拟宇宙")
            from tasks.divergent_universe import DivergentUniverse
            du_task = DivergentUniverse(
                self.operator,
                self.config.CosmicStrife.divergentUniverseRuntimes,
                self.config.CosmicStrife.isDivergentUniverseUseTechnique,
                self.config.CosmicStrife.isPointRewardsEnabled)
            if not du_task.run():
                logger.error("旷宇纷争-模拟宇宙任务失败")
                return False
        # 互斥：货币战争常规 vs 刷开局
        cw_enable = self.config.CosmicStrife.isCurrencyWarsEnabled
        if not cw_enable:
            logger.info("旷宇纷争任务全部完成")
            return True
        cw_mode = self.config.CosmicStrife.currencyWarsMode
        username = self.config.CosmicStrife.currencyWarsUsername
        strategy = self.config.CosmicStrife.currencyWarsStrategy
        runtimes = self.config.CosmicStrife.currencyWarsRuntimes
        difficulty = self.config.CosmicStrife.currencyWarsDifficulty

        if username is None or username.strip() == "":
            logger.error("货币战争开拓者名称为空，请在前端配置中填写。")
            return False
        Characters.set_username(username)

        if cw_mode==2:
            logger.info("执行任务：旷宇纷争-货币战争 刷开局")
            from tasks.currency_wars import RerollStart
            rs_task = RerollStart(operator=self.operator, runtimes=runtimes)
            # 刷开局难度选择：和标准模式使用同一个难度配置项
            rs_task.set_difficulty(difficulty)
            rs_task.load_strategy(strategy)
            rs_task.set_boss_name(self.config.CosmicStrife.currencyWarsRerollBossNames)
            rs_task.set_boss_affix(self.config.CosmicStrife.currencyWarsRerollBossAffixes)
            rs_task.set_invest_env(self.config.CosmicStrife.currencyWarsRerollInvestEnvironments)
            rs_task.set_invest_strategy(self.config.CosmicStrife.currencyWarsRerollInvestStrategies)
            if not rs_task.run():
                logger.error("旷宇纷争-货币战争刷开局任务失败")
                return False

        elif cw_mode==1 or cw_mode==0:
            logger.info("执行任务：旷宇纷争-货币战争 常规")
            from tasks.currency_wars import CurrencyWars
            cw_task = CurrencyWars(operator=self.operator, runtimes=runtimes)
            cw_task.load_strategy(strategy)
            # 前端难度选择：0=最低难度，1=最高难度
            cw_task.set_difficulty(difficulty)
            if cw_mode == 1:  # 超频博弈
                cw_task.set_overclock(True)
            if not cw_task.run():
                logger.error("旷宇纷争-货币战争任务失败")
                return False
        logger.info("旷宇纷争任务全部完成")
        return True

    def on_completed(self) -> None:
        on_complete = self.settings.Notification.onCompleted
        if self.__class__.__name__ in on_complete:
            guide_hotkey = self.settings.General.hotkeyF4
            self.operator.press_key(str(guide_hotkey).lower())
            if not self.operator.wait_img(IMG.F4, timeout=20):
                logger.error(SRAError(ErrorCode.WAIT_TIMEOUT, "等待指南界面超时"))
                self.operator.press_key("esc")
            self.operator.sleep(2)
            self.operator.click_img(IMG.COSMIC_STRIFE, after_sleep=1)  # 旷宇纷争
            self.operator.click_point(0.235, 0.81, after_sleep=1)  # 打开积分奖励面板
            self.operator.wait_img(DUIMG.BONUS_POINTS, timeout=5)
            self.send_notification(f"任务 {self.__class__.__name__} 执行完成。", "success")
            self.operator.press_key('esc', presses=2, interval=1)
