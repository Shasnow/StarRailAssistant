from SRACore.tasks.BaseTask import BaseTask
from SRACore.util.logger import logger


class SimulateUniverseTask(BaseTask):
    def __init__(self,config: dict):
        super().__init__("simulated_universe",config)
        self.times = self.config.get("times", 1)

    def run(self):
        """主任务执行函数"""
        logger.info("执行任务：差分宇宙-周期演算")

        for exe_time in range(self.times):
            self.page_locate()
            if not self._start_differential_universe(exe_time):
                return False
            if not self._select_base_effect():
                return False
            if not self._select_blessings():
                return False
            if not self._navigate_and_fight():
                return False
            if not self._select_blessings():
                return False
            if not self._complete_mission():
                return False

        self._return_to_main_menu()
        logger.info("Mission accomplished")
        return True

    def _start_differential_universe(self, exe_time):
        """开始差分宇宙任务"""
        logger.info(f"第{exe_time + 1}次进入差分宇宙，少女祈祷中…")
        box = self.wait_img("resources/img/differential_universe_start.png")
        # 点击开始按钮
        if not self.click_box(box):
            logger.error("发生错误，错误编号18")
            return False

        # 等待并点击周期演算
        if not self.wait_img("resources/img/periodic_calculus.png"):
            logger.error("发生错误，错误编号19")
            return False
        self.click_img("resources/img/periodic_calculus.png")

        # 处理队伍选择
        if self.click_img("resources/img/nobody.png"):
            self.click_img("resources/img/preset_formation.png")
            self.click_img("resources/img/team1.png")

        # 启动差分宇宙
        if not self.click_img("resources/img/launch_differential_universe.png"):
            logger.error("发生错误，错误编号20")
            return False

        return True

    def _select_base_effect(self):
        """选择基础效果"""
        if not self.wait_img("resources/img/base_effect_select.png", timeout=25):
            logger.error("超时")
            return False

        logger.info("选择基础效果")
        self.sleep(1)

        # 尝试点击收集按钮，否则点击中心点
        if not self.click_img("resources/img/collection.png"):
            self.click_point(0.5, 0.5, x_offset=-250, after_sleep=0.5)
            if not self.locate("resources/img/ensure2.png"):
                self.click_point(0.5, 0.5)

        self.sleep(0.5)
        return self.click_img("resources/img/ensure2.png")

    def _navigate_and_fight(self):
        """导航和战斗处理"""
        logger.info("移动")
        self.hold_key("w", duration=2.6)

        logger.info("进入战斗")
        self.click_point(0.5, 0.5)

        # 检查是否需要使用技能
        if self.wait_img("resources/img/q.png", timeout=10):
            self.press_key("v")

        logger.info("等待战斗结束")
        if not self.wait_img("resources/img/blessing_select.png", timeout=120, interval=1):
            logger.error("失败/超时")
            return False

        return True

    def _select_blessings(self):
        """选择祝福"""
        logger.info("选择祝福")

        while True:
            index = self.wait_any_img([
                "resources/img/blessing_select.png",
                "resources/img/equation_select.png",
                "resources/img/curiosity_select.png",
                "resources/img/equation_expansion.png",
                "resources/img/close.png",
                "resources/img/divergent_universe_quit.png"
            ],interval=0)

            if index == 0 or index == 1 or index==2:  # 祝福选择或方程式选择或奇物选择
                if not self.click_img("resources/img/collection.png"):
                    self.click_point(0.5, 0.5, x_offset=-100)
                self.click_img("resources/img/ensure2.png", after_sleep=1)
            elif index == 3 or index == 4:  # 方程式扩展或关闭
                self.press_key('esc')
            else:  # 退出
                break

        return True

    def _complete_mission(self):
        """完成任务结算"""
        logger.info("退出并结算")
        self.press_key("esc")

        if not self.wait_img("resources/img/end_and_settle.png"):
            return False

        self.click_point(0.8, 0.9, after_sleep=0.5)
        self.click_img("resources/img/ensure2.png", after_sleep=0.5)

        logger.info("返回主界面")
        if self.wait_img("resources/img/return.png"):
            self.click_img("resources/img/return.png", after_sleep=0.5)

        return True

    def _return_to_main_menu(self):
        """返回主菜单"""
        self.press_key("esc", presses=2, interval=1)

    def page_locate(self):
        """
        定位到差分宇宙页面。
        :return: None
        """
        page = self.wait_any_img(["resources/img/enter.png", "resources/img/differential_universe_start.png","resources/img/bonus points.png"])
        if page == 0:
            self.press_key(self.gcm.get('key_f4', 'f4'))
            if not self.wait_img("resources/img/f4.png", timeout=20):
                logger.error("检测超时，编号1")
                self.press_key("esc")
            self.click_point(0.3125, 0.20, after_sleep=0.5)  # 差分宇宙
            self.click_point(0.7786, 0.8194, after_sleep=1)  # 周期演算
            return True
        elif page == 1:
            return True
        elif page == 2:
            self.press_key('esc')
            return True
        else:
            logger.error("检测超时")
            return False
