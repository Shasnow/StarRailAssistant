from collections.abc import Callable

from loguru import logger

from SRACore.task import Executable
from SRACore.util.errors import SRAError, ErrorCode
from tasks.img import DUIMG, IMG


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
            if not self.select():
                return False
            if not self._navigate_and_fight():
                return False
            if not self.select():
                return False
            if not self._complete_mission():
                return False

        self._return_to_main_menu()
        logger.info("Mission accomplished")
        return True

    def _start_differential_universe(self, exe_time):
        """开始差分宇宙任务"""
        logger.info(f"第{exe_time + 1}次进入差分宇宙，少女祈祷中…")
        index, box = self.operator.wait_any_img([DUIMG.DIFFERENTIAL_UNIVERSE, DUIMG.DIFFERENTIAL_UNIVERSE_START])
        if index == -1:
            logger.error(SRAError(ErrorCode.IMAGE_NOT_FOUND, "未找到差分宇宙入口"))
            return False
        if index == 0:  # 差分宇宙门口
            self.operator.press_key("f")
            box = self.operator.wait_img(DUIMG.DIFFERENTIAL_UNIVERSE_START)
        # index=1, 已经在差分宇宙界面，box为开始按钮
        # 点击开始按钮直到进入
        self.operator.do_while(lambda: self.operator.click_box(box),  # NOQA
                               lambda: self.operator.locate(DUIMG.PERIODIC_CALCULUS) is None,
                               interval=1, max_iterations=10)
        self.operator.click_img(DUIMG.PERIODIC_CALCULUS)

        launch_button_box = self.operator.wait_img(DUIMG.LAUNCH_DIFFERENTIAL_UNIVERSE)
        # 启动差分宇宙
        if launch_button_box is None:
            logger.error(SRAError(ErrorCode.IMAGE_NOT_FOUND, "未找到差分宇宙启动按钮"))
            return False
        if not self.operator.click_box(launch_button_box):
            logger.error(SRAError(ErrorCode.MOUSE_CLICK_FAILED, "点击差分宇宙启动按钮失败"))
            return False

        return True

    def _navigate_and_fight(self):
        """导航和战斗处理"""
        logger.info("移动")
        self.operator.hold_key("w", duration=1.5)

        logger.info("进入战斗")
        if self.use_technique:
            self.operator.press_key("e")
            self.operator.sleep(0.5)
        self.operator.click_point(0.5, 0.5, after_sleep=0.1)
        self.operator.click_point(0.5, 0.5, after_sleep=0.1)

        self.operator.sleep(3)

        logger.info("等待战斗结束")

        return True

    def select(self):
        """选择祝福"""
        selections: list[tuple[str, str, Callable[[], None] | None, bool]] = [
            ("选择面具", DUIMG.MASK_SELECT, self.handle_mask_select, False),
            ("选择祝福", DUIMG.BLESSING_SELECT, self.handle_blessing_select, False),
            ("选择方程", DUIMG.EQUATION_SELECT, self.handle_equation_select, False),
            ("选择奇物", DUIMG.CURIOSITY_SELECT, self.handle_curiosity_select, False),
            ("方程展开", DUIMG.EQUATION_EXPANSION, self.handle_equation_expand, False),
            ("选择站点卡", DUIMG.STATION_SELECT, self.handle_station_select, False),
            ("选择惊世奇迹", DUIMG.SELECT_GRAND_MIRACLE, self.handle_miracle_select, False),
            ("点击空白处关闭", DUIMG.CLOSE, self.handle_close, False),
            ('', DUIMG.DIFFERENTIAL_UNIVERSE_QUIT, None, True),
        ]

        template_list = [s[1] for s in selections]
        selection_index, _ = self.operator.wait_any_img(template_list, timeout=60)
        while True:
            if selection_index == -1:
                raise RuntimeError("未匹配到任何选择界面")

            selection_name, _, handler, is_terminal = selections[selection_index]
            logger.info(f"检测到选择界面: {selection_name}")
            if handler:
                try:
                    handler()
                except Exception as e:
                    logger.error(SRAError(ErrorCode.UNKNOWN_ERROR, f"处理{selection_name}时发生错误: {e}"))
                    return False
            if is_terminal:
                break
            self.operator.sleep(1)
            selection_index, _ = self.operator.wait_any_img(template_list, timeout=30)

        return True

    def handle_mask_select(self):
        self.operator.click_point(0.1713, 0.82, tag="选择下面的面具")
        confirm_btn = self.operator.wait_img(DUIMG.ENSURE)
        if confirm_btn is not None:
            self.operator.click_box(confirm_btn)

    def handle_blessing_select(self):
        if not self.operator.click_img(DUIMG.COLLECTION):
            self.operator.click_point(0.5, 0.4, x_offset=-140)
        self.operator.click_img(IMG.ENSURE2, after_sleep=1)

    def handle_equation_select(self):
        self.handle_blessing_select()

    def handle_curiosity_select(self):
        self.handle_blessing_select()

    def handle_close(self):
        self.operator.press_key('esc')

    def handle_equation_expand(self):
        self.handle_close()

    def handle_station_select(self):
        self.operator.click_img(DUIMG.ENSURE2, after_sleep=0.5)

    def handle_miracle_select(self):
        self.handle_blessing_select()

    def _complete_mission(self):
        """完成任务结算"""
        logger.info("退出并结算")
        for _ in range(30):
            if not self.operator.locate(DUIMG.END_AND_SETTLE):
                self.operator.press_key("esc")
                self.operator.sleep(1)
            else:
                break
        else:
            logger.error(SRAError(ErrorCode.WAIT_TIMEOUT, "等待结算退出入口超时"))
            return False

        self.operator.click_point(0.8, 0.9, after_sleep=0.5, tag="退出并结算")
        box = self.operator.wait_img(IMG.ENSURE2)
        if box is None:
            logger.warning(SRAError(ErrorCode.IMAGE_NOT_FOUND, "未找到结算确认按钮"))
            return False

        self.operator.click_box(box)

        logger.info("返回主界面")
        if self.operator.wait_img(DUIMG.RETURN):
            self.operator.click_img(DUIMG.RETURN, after_sleep=0.5)

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
            IMG.ENTER,
            DUIMG.DIFFERENTIAL_UNIVERSE_START,
        ], interval=1)
        if page == 0:
            self.operator.press_key(self.settings.General.hotkeyF4)
            if not self.operator.wait_img(IMG.F4, timeout=20):
                logger.error(SRAError(ErrorCode.WAIT_TIMEOUT, "等待指南界面超时"))
                self.operator.press_key("esc")
            self.operator.click_img(IMG.COSMIC_STRIFE, after_sleep=1)  # 旷宇纷争
            self.operator.click_point(0.242, 0.441, after_sleep=0.5)  # 差分宇宙
            self.operator.click_point(0.7786, 0.8194, after_sleep=1)  # 前往参与
            return True
        elif page == 1:
            return True
        else:
            logger.error("检测超时")
            return False
