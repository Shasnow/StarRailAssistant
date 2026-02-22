from SRACore.task import BaseTask
from SRACore.util.logger import logger


class CosmicStrifeTask(BaseTask):
    def run(self):
        """主任务执行函数"""
        if self.config.get("DUEnable", False):
            logger.info("执行任务：旷宇纷争-模拟宇宙")
            from tasks.differential_universe import DifferentialUniverse
            du_task = DifferentialUniverse(
                self.operator,
                self.config.get("DURunTimes", 0),
                self.config.get("DUUseTechnique", False))
            if not du_task.run():
                logger.error("旷宇纷争-模拟宇宙任务失败")
                return False
        # 互斥：货币战争常规 vs 刷开局
        cw_enable = self.config.get("CurrencyWarsEnable", False)
        if not cw_enable:
            logger.info("旷宇纷争任务全部完成")
            return True
        cw_mode = self.config.get("CurrencyWarsMode", 0)
        username = self.config.get("CurrencyWarsUsername", "")

        if username is None or username.strip() == "":
            logger.error("货币战争开拓者名称为空，请在前端配置中填写。")
            return False

        if cw_mode==2:
            logger.info("执行任务：旷宇纷争-货币战争 刷开局")
            from tasks.currency_wars import RerollStart
            rs_task = RerollStart(operator=self.operator,
                                  invest_env=self.config.get("CwRsInvestEnvironments"),
                                  invest_strategy=self.config.get("CwRsInvestStrategies"),
                                  invest_strategy_stage= self.config.get("CwRsInvestStrategyStage", 1),
                                  max_retry=self.config.get("CwRsMaxRetry", 0),
                                  boss_affix=self.config.get("CwRsBossAffixes", ""))
            # 刷开局难度选择：0=最高难度(默认)，1=当前难度（不切换难度，直接开始）
            rs_difficulty = self.config.get("CwRsDifficulty", 0)
            rs_task.cw.set_difficulty(1 if rs_difficulty == 0 else 2)
            rs_task.cw.set_username(username)
            rs_task.cw.load_strategy("template")
            if not rs_task.run():
                logger.error("旷宇纷争-货币战争刷开局任务失败")
                return False

        elif cw_mode==1 or cw_mode==0:
            logger.info("执行任务：旷宇纷争-货币战争")
            from tasks.currency_wars import CurrencyWars
            cw_task = CurrencyWars(self.operator, self.config.get("CurrencyWarsRunTimes", 0))
            cw_task.set_username(username)
            cw_task.load_strategy("template")
            # 前端难度选择：0=最低难度，1=最高难度
            difficulty = self.config.get("CurrencyWarsDifficulty", 0)
            cw_task.set_difficulty(difficulty)
            if cw_mode == 1:  # 超频博弈
                cw_task.set_overclock(True)

            if not cw_task.run():
                logger.error("旷宇纷争-货币战争任务失败")
                return False
        logger.info("旷宇纷争任务全部完成")
        return True
