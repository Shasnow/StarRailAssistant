from SRACore.task import BaseTask
from SRACore.util.logger import logger


class CosmicStrifeTask(BaseTask):
    def __init__(self, config: dict):
        super().__init__(config)

    def run(self):
        """主任务执行函数"""
        if self.config.get("SimulatedUniverseEnable", False):
            logger.info("执行任务：旷宇纷争-模拟宇宙")
            from tasks.differential_universe import DifferentialUniverse
            du_task = DifferentialUniverse(self.config.get("SimulatedUniverseRunTimes", 0))
            if not du_task.run():
                logger.error("旷宇纷争-模拟宇宙任务失败")
                return False
        if self.config.get("CurrencyWarsEnable", False):
            logger.info("执行任务：旷宇纷争-货币战争")
            from tasks.currency_wars import CurrencyWars
            cw_task = CurrencyWars(self.config.get("CurrencyWarsRunTimes", 0))
            username = self.config.get("CurrencyWarsUsername","")
            if username is None or username.strip() == "":
                logger.error("货币战争开拓者名称为空，请在前端配置中填写。")
                return False
            cw_task.set_username(username)
            if not cw_task.run():
                logger.error("旷宇纷争-货币战争任务失败")
                return False
        logger.info("旷宇纷争任务全部完成")
        return True
