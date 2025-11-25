from loguru import logger

from SRACore.util.operator import Executable


class DifferentialUniverse(Executable):
    def __init__(self, run_times):
        super().__init__()
        self.run_times = run_times

    def run(self):
        """主任务执行函数"""
        logger.info("执行任务：差分宇宙-周期演算")

        for exe_time in range(self.run_times):
            if not self.page_locate():
                return False
            if not self._start_differential_universe(exe_time):
                return False
            if not self._select():
                return False
            if not self._navigate_and_fight():
                return False+65

            if not self._select():
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

    def _select(self):
        """选择祝福"""
        var = ["选择基础效果", "选择祝福", "选择方程", "选择奇物"]

        while True:
            index, _ = self.wait_any_img([
                "resources/img/base_effect_select.png",
                "resources/img/blessing_select.png",
                "resources/img/equation_select.png",
                "resources/img/curiosity_select.png",
                "resources/img/equation_expansion.png",
                "resources/img/close.png",
                "resources/img/divergent_universe_quit.png"
            ],interval=0.5)

            if index==0 or index == 1 or index == 2 or index==3:  # 祝福选择或方程式选择或奇物选择
                logger.info(var[index])
                self.sleep(0.5)
                if not self.click_img("resources/img/collection.png"):
                    self.click_point(0.5, 0.5, x_offset=-150)
                self.click_img("resources/img/ensure2.png", after_sleep=1)
            elif index == 4 or index == 5:  # 方程式扩展或关闭
                self.press_key('esc')
                self.sleep(0.5)
            else:  # 退出
                break

        return True

    def _complete_mission(self):
        """完成任务结算"""
        logger.info("退出并结算")
        for i in range(30):
            if not self.locate("resources/img/end_and_settle.png"):
                self.press_key("esc")
                self.sleep(1)
            else:
                break
        else:
            logger.error("无法退出，错误编号21")
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
        page, _ = self.wait_any_img([
            "resources/img/enter.png",
            "resources/img/differential_universe_start.png",
            "resources/img/bonus points.png"
        ],interval=0.5)
        if page == 0:
            self.press_key(self.settings.get('GuideHotkey', 'f4').lower())
            if not self.wait_img("resources/img/f4.png", timeout=20):
                logger.error("检测超时，编号1")
                self.press_key("esc")
            self.click_point(0.3125, 0.20, after_sleep=0.5)  # 旷宇纷争
            self.click_point(0.242, 0.441, after_sleep=0.5)  # 差分宇宙
            self.click_point(0.7786, 0.8194, after_sleep=1)  # 前往参与
            return True
        elif page == 1:
            return True
        elif page == 2:
            self.sleep(4)
            self.press_key('esc')
            return True
        else:
            logger.error("检测超时")
            return False
