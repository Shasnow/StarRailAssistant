from loguru import logger

from SRACore.task import Executable


class DifferentialUniverse(Executable):
    def __init__(self, operator, run_times: int, use_technique: bool):
        super().__init__(operator)
        self.run_times = run_times
        self.use_technique = use_technique

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
                return False
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
        box = self.operator.wait_img("resources/img/differential_universe_start.png")
        # 点击开始按钮
        if box is None:
            logger.error("发生错误，错误编号18")
            return False
        self.operator.do_while(lambda : self.operator.click_box(box),
                      lambda : self.operator.locate("resources/img/periodic_calculus.png") is None,
                      interval=0.5, max_iterations=10)
        self.operator.click_img("resources/img/periodic_calculus.png")

        launch_button_box = self.operator.wait_img("resources/img/launch_differential_universe.png")
        # 启动差分宇宙
        if not self.operator.click_box(launch_button_box):
            logger.error("发生错误，错误编号20")
            return False

        return True

    def _navigate_and_fight(self):
        """导航和战斗处理"""
        logger.info("移动")
        self.operator.hold_key("w", duration=2.5)

        logger.info("进入战斗")
        if self.use_technique:
            self.operator.press_key("e")
            self.operator.sleep(0.5)
        self.operator.click_point(0.5, 0.5, after_sleep=0.1)
        self.operator.click_point(0.5, 0.5, after_sleep=0.1)

        # 检查是否需要使用技能
        if self.operator.wait_img("resources/img/q.png", timeout=10):
            self.operator.press_key("v")

        logger.info("等待战斗结束")
        if not self.operator.wait_img("resources/img/blessing_select.png", timeout=120, interval=1):
            logger.error("失败/超时")
            return False

        return True

    def _select(self):
        """选择祝福"""
        var = ["选择基础效果", "选择祝福", "选择方程", "选择奇物"]

        while True:
            index, _ = self.operator.wait_any_img([
                "resources/img/base_effect_select.png",
                "resources/img/blessing_select.png",
                "resources/img/equation_select.png",
                "resources/img/curiosity_select.png",
                "resources/img/equation_expansion.png",
                "resources/img/close.png",
                "resources/img/divergent_universe_quit.png"
            ], interval=0.5)

            if index==0 or index == 1 or index == 2 or index==3:  # 祝福选择或方程式选择或奇物选择
                logger.info(var[index])
                self.operator.sleep(0.5)
                if not self.operator.click_img("resources/img/collection.png"):
                    self.operator.click_point(0.5, 0.5, x_offset=-150)
                self.operator.click_img("resources/img/ensure2.png", after_sleep=1)
            elif index == 4 or index == 5:  # 方程式扩展或关闭
                self.operator.press_key('esc')
                self.operator.sleep(0.5)
            else:  # 退出
                break

        return True

    def _complete_mission(self):
        """完成任务结算"""
        logger.info("退出并结算")
        for i in range(30):
            if not self.operator.locate("resources/img/end_and_settle.png"):
                self.operator.press_key("esc")
                self.operator.sleep(1)
            else:
                break
        else:
            logger.error("无法退出，错误编号21")
            return False

        self.operator.click_point(0.8, 0.9, after_sleep=0.5)
        self.operator.click_img("resources/img/ensure2.png", after_sleep=0.5)

        logger.info("返回主界面")
        if self.operator.wait_img("resources/img/return.png"):
            self.operator.click_img("resources/img/return.png", after_sleep=0.5)

        return True

    def _return_to_main_menu(self):
        """返回主菜单"""
        self.operator.press_key("esc", presses=2, interval=1)

    def page_locate(self):
        """
        定位到差分宇宙页面。
        :return: None
        """
        page, _ = self.operator.wait_any_img([
            "resources/img/enter.png",
            "resources/img/differential_universe_start.png",
            "resources/img/bonus points.png"
        ], interval=0.5)
        if page == 0:
            self.operator.press_key(self.settings.get('GuideHotkey', 'f4').lower())
            if not self.operator.wait_img("resources/img/f4.png", timeout=20):
                logger.error("检测超时，编号1")
                self.operator.press_key("esc")
            self.operator.click_point(0.3125, 0.20, after_sleep=0.5)  # 旷宇纷争
            self.operator.click_point(0.242, 0.441, after_sleep=0.5)  # 差分宇宙
            self.operator.click_point(0.7786, 0.8194, after_sleep=1)  # 前往参与
            return True
        elif page == 1:
            return True
        elif page == 2:
            # 积分奖励页面
            self.operator.sleep(4)
            self.operator.press_key('esc')
            return True
        else:
            logger.error("检测超时")
            return False
