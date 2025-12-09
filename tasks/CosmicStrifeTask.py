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
        # 互斥：货币战争常规 vs 刷开局
        cw_enable = self.config.get("CurrencyWarsEnable", False)
        cw_opening_enable = self.config.get("CurrencyWarsBrushOpeningEnable", False)
        if cw_enable and cw_opening_enable:
            logger.error("配置冲突：同时启用了'货币战争'与'货币战争刷开局'，请仅选择其一")
            return False

        if cw_opening_enable:
            logger.info("执行任务：旷宇纷争-货币战争刷开局")
            from tasks.currency_wars import BrushOpening
            bo_config = self.config.get("CurrencyWarsBrushOpening", {})
            bo_task = BrushOpening(bo_config)
            if not bo_task.openning():
                logger.error("旷宇纷争-货币战争刷开局任务失败")
                return False

        if cw_enable:
            logger.info("执行任务：旷宇纷争-货币战争")
            from tasks.currency_wars import CurrencyWars
            cw_task = CurrencyWars(self.config.get("CurrencyWarsRunTimes", 0))
            username = self.config.get("CurrencyWarsUsername","")
            if username is None or username.strip() == "":
                logger.error("货币战争开拓者名称为空，请在前端配置中填写。")
                return False
            cw_task.set_username(username)
            # 前端难度选择：0=最低难度，1=最高难度
            difficulty = int(self.config.get("CurrencyWarsDifficulty", 0))
            try:
                cw_task.set_difficulty(difficulty)
            except Exception:
                pass
            if not cw_task.run():
                logger.error("旷宇纷争-货币战争任务失败")
                return False
        logger.info("旷宇纷争任务全部完成")
        return True
