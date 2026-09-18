import re
from collections.abc import Callable
from typing import Any

from loguru import logger

from SRACore.operators.model import Box
from SRACore.task import Executable
from SRACore.util.errors import SRAError, ErrorCode
from SRACore.util.strutil import ContainsMatcher
from tasks.img import DUIMG, IMG


class DivergentUniverse(Executable):
    # 随意门 HSV 范围（OpenCV 约定）
    HSV_LOWER = (146, 64, 154)
    HSV_UPPER = (175, 146, 222)
    # 随意门最小检测面积
    MIN_DOOR_AREA = 2500
    # 视角旋转最大尝试次数
    MAX_ROTATE_ATTEMPTS = 8
    # 前进超时时间（秒）
    FORWARD_TIMEOUT = 20
    # 前进时分段持键时长（秒）
    FORWARD_HOLD_INTERVAL = 0.5
    # 对齐阈值（像素），小于此值视为已居中
    ALIGN_THRESHOLD = 10
    # 对齐最大重试次数
    MAX_ALIGN_ATTEMPTS = 10
    # 站点刷新最大次数
    MAX_REROLL_ATTEMPTS = 3
    # 事件扫描：一周内转动+识别的步数
    SCAN_STEPS = 10
    # 事件扫描：轮数上限（每轮 = 旋转一周识别 + 前进识别）
    MAX_SCAN_ROUNDS = 4
    # 事件扫描：每轮前进时长（秒）
    SCAN_FORWARD_DURATION = 1.0

    def __init__(self,
                 operator,
                 run_times: int = 1,
                 use_technique: bool = False,
                 point_rewards: bool = False,
                 mode: int = 0):
        super().__init__(operator)
        self.run_times = run_times
        self.use_technique = use_technique
        self.point_rewards = point_rewards
        self.station_priority = ["战斗", "精英", "商店"]
        self.selections: list[tuple[str, str, Callable[[], Any] | None, bool]] = [
            ("选择面具", DUIMG.MASK_SELECT, self.handle_mask_select, False),
            ("选择祝福", DUIMG.BLESSING_SELECT, self.handle_blessing_select, False),
            ("选择方程", DUIMG.EQUATION_SELECT, self.handle_equation_select, False),
            ("选择奇物", DUIMG.CURIOSITY_SELECT, self.handle_curiosity_select, False),
            ("方程展开", DUIMG.EQUATION_EXPANSION, self.handle_equation_expand, False),
            ("祝福强化", DUIMG.BLESSING_ENHANCEMENT, self.handle_close, False),
            ("选择站点卡", DUIMG.STATION_SELECT, self.handle_station_select, False),
            ("选择下一个站点", DUIMG.SELECT_NEXT_STATION, self.handle_next_station_select, False),
            ("选择惊世奇迹", DUIMG.SELECT_GRAND_MIRACLE, self.handle_miracle_select, False),
            ("选择奇迹", DUIMG.SELECT_YOUR_MIRACLE, self.handle_miracle_select, False),
            ("选择区域", DUIMG.SELECT_AREA, self.handle_area_select, False),
            ("点击空白处关闭", DUIMG.CLOSE, self.handle_close, False),
            ("丢弃", DUIMG.DISCARD_DISABLE, self.handle_disc_curiosity, False),
            # ("奇物损毁", DUIMG.DESTROY_CURIOSITY, self.handle_disc_curiosity, False),
            ("事件", DUIMG.EVENT, self.handle_event, False),
            ("探索成功", DUIMG.SUCCESS, self.handle_success, True),
            ('处理完成', DUIMG.DIVERGENT_UNIVERSE_QUIT, None, True),
        ]
        self.stations: list[tuple[str, Callable[[], bool]]] = [
            ("战斗", self.handle_fight_station),
            ("精英", self.handle_elite_station),
            ("首领", self.handle_fight_station),
            ("转化", self.handle_fight_station),
            ("商店", self.handle_shop_station),
            ("事件", self.handle_event_station),
            ("铸造", self.handle_forge_station),
            ("奖励", self.handle_event_station),
            ("休整", self.handle_shop_station),
            ("异常", self.handle_event_station),
            ("财富", self.handle_wealth_station),
        ]

        self.selection_template_list = [s[1] for s in self.selections]
        self.in_game = False
        self.is_running = False
        self.mode = mode
        self.current_station = "战斗"
        

    def run(self):
        """主任务执行函数"""
        logger.info("执行任务：差分宇宙-周期演算")

        for exe_time in range(self.run_times):
            if not self.page_locate():
                return False
            if not self.in_game:
                if self.point_rewards and self.check_point_rewards():
                    break
                if not self._start_divergent_universe(exe_time):
                    return False
            if not self.game_loop():
                return False
            
        if self.point_rewards:
            self.receive_point_rewards()
        self._return_to_main_menu()
        logger.info("Mission accomplished")
        return True

    def game_loop(self):
        """游戏循环"""
        logger.info("开始游戏循环")
        self.is_running = True
        while True:
            if not self.select():
                return False
            if not self.is_running:
                break
            if not self.station():
                return False
            if not self.select():
                return False
            if self.mode == 0:
                self._quit_game()
                break
            if not self.navigate_to_next_station():
                return False
        return True

    def _start_divergent_universe(self, exe_time):
        """开始差分宇宙任务"""
        logger.info(f"第{exe_time + 1}次进入差分宇宙，少女祈祷中…")
        index, box = self.operator.wait_any_img([DUIMG.DIVERGENT_UNIVERSE, DUIMG.DIVERGENT_UNIVERSE_START])
        if index == -1:
            logger.error(SRAError(ErrorCode.IMAGE_NOT_FOUND, "未找到差分宇宙入口"))
            return False
        if index == 0:  # 差分宇宙门口
            self.operator.press_key("f")
            box = self.operator.wait_img(DUIMG.DIVERGENT_UNIVERSE_START)
        # index=1, 已经在差分宇宙界面，box为开始按钮
        # 点击开始按钮直到进入
        self.operator.do_while(lambda: self.operator.click_box(box),
                               lambda: self.operator.locate(DUIMG.PERIODIC_CALCULUS) is None,
                               interval=1, max_iterations=10)
        self.operator.click_img(DUIMG.PERIODIC_CALCULUS)

        _, launch_button_box = self.operator.wait_any_img([DUIMG.LAUNCH_DIVERGENT_UNIVERSE, DUIMG.CONTINUE_PROGRESS])
        # 启动差分宇宙
        if launch_button_box is None:
            logger.error("未找到差分宇宙启动按钮")
            return False
        if not self.operator.click_box(launch_button_box):
            logger.error("点击差分宇宙启动按钮失败")
            return False

        return True

    def handle_fight_station(self):
        """战斗站点处理"""
        def _move_and_attack():
            self.operator.hold_key("w", duration=0.2)
            self.operator.click_point(0.5, 0.5, after_sleep=0.1)

        self.operator.hold_key("w", duration=1.5)
        logger.info("移动")

        logger.info("尝试进入战斗")
        if self.use_technique:
            self.operator.press_key("e")
            self.operator.sleep(0.5)
        # 在战斗进行中循环执行：点击屏幕中心攻击 + 按 W 前进
        # 直到检测不到"退出差分宇宙"按钮（进入战斗）或达到最大尝试次数
        self.operator.do_while(
            _move_and_attack,
            lambda: self.operator.locate(DUIMG.DIVERGENT_UNIVERSE_QUIT) is not None,
            interval=1, max_iterations=10
        )
        logger.info("战斗开始")

        self.operator.sleep(5)

        logger.info("等待战斗结束")

        return True

    def handle_elite_station(self):
        """精英站点处理"""
        return self.handle_fight_station()

    def handle_shop_station(self):
        """商店站点处理"""
        # 暂不处理，直接返回True
        return True

    def handle_event_station(self):
        """事件站点处理"""
        self.operator.sleep(1)
        for _ in range(4):
            event = self._scan_for_event()
            if event is None:
                logger.info("扫描未找到事件，结束事件站点处理")
                break
            matcher = ContainsMatcher(event.source)
            self._align_horizontal(event, lambda: self.operator.ocr_match(text=matcher, from_x=0.24, from_y=0.0, to_x=0.77, to_y=0.5))
            self._move_forward_until_found("事件")
            self.operator.press_key("f")
            self.select()
        return True

    def _detect_event(self) -> Box | None:
        """识别视野内的事件名称，过滤以数字开头的干扰文本"""
        events = self.operator.ocr_boxes(from_x=0.24, from_y=0.0, to_x=0.77, to_y=0.5, confidence=0.8)
        for box in events or []:
            if len(box.source) < 2 or box.source.isascii() or box.source == "造物调试台":  # 事件不可能为纯ASCII文本
                continue
            logger.info(f"识别到事件: {box.source}")
            return box
        return None

    def _scan_for_event(self) -> Box | None:
        """扫描寻找事件：重置视角 → 向右旋转一周并穿插识别 → 未找到则前进后重新扫描，循环直到找到或达到轮数上限"""
        step = int(self.operator.window_context.width * 0.5)
        for round_ in range(1, self.MAX_SCAN_ROUNDS + 1):
            self.operator.press_key("capslock")  # 视角重置到角色面向方向
            self.operator.sleep(0.5)
            # 向右旋转一周，每步转动后识别
            for _ in range(self.SCAN_STEPS):
                self.operator.move_rel(step, 0)
                self.operator.sleep(0.3)
                event = self._detect_event()
                if event is not None:
                    return event
            logger.info(f"{round_}/{self.MAX_SCAN_ROUNDS} 未找到事件，前进后重试")
            # 前进一段距离后识别，再进入下一轮
            self.operator.hold_key("w", self.SCAN_FORWARD_DURATION)
            self.operator.sleep(0.3)
            event = self._detect_event()
            if event is not None:
                return event
        logger.warning("扫描完成仍未找到事件")
        return None

    def handle_event(self):
        """事件处理"""
        for _ in range(10):
            state, box = self.operator.locate_any([DUIMG.EVENT_SELECT, DUIMG.EVENT_NEXT, DUIMG.EVENT_SELECTION])
            if state == -1:
                break
            if state == 1:
                self.operator.click_point(0.8, 0.8, after_sleep=0.1, tag="点击事件对话")
            if state == 0:
                self.operator.click_box(box, after_sleep=1)
            if state == 2:
                all_selections = self.operator.locate_all(DUIMG.EVENT_SELECTION)
                if not all_selections:
                    raise RuntimeError("未找到事件选择项")
                for s in all_selections:
                    self.operator.click_box(s, after_sleep=0.5)
                    if not self.operator.click_img(DUIMG.ENSURE4):
                        continue
                    break
        
        return True

    def handle_forge_station(self):
        """铸造站点处理"""
        return self.handle_event_station()

    def navigate_to_next_station(self):
        """导航到下一个站点：定位随意门 → 水平对齐 → 前进 → 交互"""
        if not self._find_door_and_align():
            self._quit_game(temporary=True)
            self._start_divergent_universe(0)
            self.page_locate()
            self.operator.hold_key("d", duration=1)
            if not self._find_door_and_align():
                return False
        if not self._move_forward_until_found("随意门"):
            logger.warning("前进超时未检测到交互提示，尝试直接交互")
        self.operator.press_key('f')
        return True

    def _find_door(self):
        """检测随意门，未找到则旋转视角重试"""
        self.operator.active_window()
        self.operator.press_key("capslock", presses=2, interval=0.2)  # 重置视角
        for attempt in range(1, self.MAX_ROTATE_ATTEMPTS + 1):
            boxes = self.operator.detect_color(
                self.HSV_LOWER, self.HSV_UPPER,
                min_area=self.MIN_DOOR_AREA, trace=True,
            )
            if boxes:
                logger.info("已找到随意门")
                return boxes[0]

            logger.debug(f"第 {attempt} 次检测：未找到，旋转视角")
            # 向右移动半个窗口宽度以旋转视角
            move_distance = int(self.operator.window_context.width * 0.5)
            self.operator.move_rel(move_distance, 0)
            self.operator.sleep(0.5)

        logger.warning(f"已尝试 {self.MAX_ROTATE_ATTEMPTS} 次，仍未找到随意门")
        return None

    def _align_horizontal(self, box, detect: Callable[[], Box | list[Box] | None]):
        """循环旋转视角直到目标中心与屏幕中心水平偏差小于阈值

        Args:
            box: 初始检测到的目标框
            detect: 重新检测目标位置的回调，返回 Box 列表
        """
        screen_center_x = self.operator.window_context.width // 2
        for attempt in range(1, self.MAX_ALIGN_ATTEMPTS + 1):
            delta = box.center[0] - screen_center_x

            if abs(delta) < self.ALIGN_THRESHOLD:
                logger.debug(f"第 {attempt} 次对齐：偏差 {delta}px，已居中")
                return

            logger.debug(f"第 {attempt} 次对齐：偏差 {delta}px，旋转视角")
            self.operator.move_rel(delta, 0)
            self.operator.sleep(0.5)

            # 重新检测目标位置
            boxes = detect()
            if not boxes:
                logger.warning(f"第 {attempt} 次对齐：旋转后丢失目标，终止对齐")
                return
            box = boxes[0] if isinstance(boxes, list) else boxes

        logger.warning(f"已尝试 {self.MAX_ALIGN_ATTEMPTS} 次仍未对齐，继续执行")

    def _find_door_and_align(self):
        """检测随意门，未找到则旋转视角重试，对齐到屏幕中心"""
        box = self._find_door()
        if box is None:
            logger.error("未找到随意门，无法导航到下一个站点")
            return False
        self._align_horizontal(
            box,
            lambda: self.operator.detect_color(
                self.HSV_LOWER, self.HSV_UPPER,
                min_area=self.MIN_DOOR_AREA, trace=False))
        return True

    def _move_forward_until_found(self, text: str = "", forward_hold_interval: float | None = None):
        """分段按住 w 前进，检测到 IMG.F 或超时后停止"""
        logger.info(f"开始前进，超时 {self.FORWARD_TIMEOUT}s，等待检测交互提示")
        if forward_hold_interval is None:
            forward_hold_interval = self.FORWARD_HOLD_INTERVAL
        # do_while: 条件满足（未检测到 F）时重复前进；达到 max_iterations（即超时）返回 False
        found = self.operator.do_while(
            lambda: self.operator.hold_key("w", forward_hold_interval, trace=False),
            lambda: not self.operator.locate(IMG.F, trace=False),
            interval=0.1,
            max_iterations=int(self.FORWARD_TIMEOUT / (forward_hold_interval + 0.1)) + 1,
        )
        if found:
            logger.info("检测到交互提示，停止前进")
            if text == "":
                return True
            boxes = self.operator.ocr_boxes(from_x=0.62, from_y=0.54, to_x=0.72, to_y=0.6)
            if boxes:
                box = boxes[0]
                if text in box.text:
                    return True
                else:
                    self._move_forward_until_found(text, forward_hold_interval) # 递归调用，继续前进
        else:
            logger.warning(f"前进超时（{self.FORWARD_TIMEOUT}s），停止前进")
        return found

    def select(self):
        """选择操作"""
        selection_index, _ = self.operator.wait_any_img(self.selection_template_list, timeout=600)
        while True:
            if selection_index == -1:
                raise RuntimeError("未匹配到任何选择界面")

            selection_name, _, handler, is_terminal = self.selections[selection_index]
            logger.info(f"检测到选择界面: {selection_name}")
            if handler:
                try:
                    handler()
                except Exception as e:
                    logger.error(SRAError(ErrorCode.UNKNOWN_ERROR, f"处理{selection_name}时发生错误: {e}"))
                    return False
            if is_terminal:
                break
            self.operator.sleep(0.5)
            selection_index, _ = self.operator.wait_any_img(self.selection_template_list, timeout=30)

        return True

    def station(self):
        """站点操作"""
        for station_name, handler in self.stations:
            if self.current_station in station_name:
                return handler()
        raise RuntimeError(f"无法处理站点 {self.current_station}")

    def handle_mask_select(self):
        self.operator.click_point(0.1713, 0.80, tag="选择下面的面具")
        confirm_btn = self.operator.wait_img(DUIMG.ENSURE)
        if confirm_btn is not None:
            self.operator.click_box(confirm_btn)
        else:
            raise RuntimeError("选择面具后未找到确认按钮")

    def handle_blessing_select(self):
        if not self.operator.click_img(DUIMG.COLLECTION):
            if not self.operator.click_img(DUIMG.RECOMMENDED_BLESSING):
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

    def handle_disc_curiosity(self):
        self.operator.click_point(0.45, 0.4, tag="选择丢弃奇物")
        self.operator.click_img(DUIMG.DISCARD, after_sleep=0.5)
        self.operator.click_img(IMG.ENSURE, after_sleep=0.5)

    def handle_station_select(self):
        """选择站点"""
        # 默认选中第一个站点，直接点击确认
        self.operator.click_img(DUIMG.ENSURE2, after_sleep=0.5)

    def handle_miracle_select(self):
        self.handle_blessing_select()

    def handle_next_station_select(self):
        """选择下一个站点：优先选择 station_priority 中的站点，未刷出则点击刷新重试"""
        self.operator.click_point(0.5, 0.5)  # 点击中心，确保选择到下一个站点，防止只有单个站点时未识别到
        boxes = self.operator.ocr_boxes(from_x=0.1, from_y=0.675, to_x=0.9, to_y=0.76)  # 识别选项
        if not boxes:
            raise RuntimeError("未找到下一个站点")
        logger.info(f"识别到 {len(boxes)} 个选项")
        target = self._match_priority_station(boxes)
        for reroll in range(1, self.MAX_REROLL_ATTEMPTS + 1):
            if target is not None:
                break
            logger.info(f"未找到目标站点，第 {reroll}/{self.MAX_REROLL_ATTEMPTS} 次刷新站点")
            if not self.operator.click_img(DUIMG.REROLL, after_sleep=1):
                logger.warning("未找到刷新按钮，停止刷新")
                break
            boxes = self.operator.ocr_boxes(from_x=0.1, from_y=0.675, to_x=0.9, to_y=0.75)  # 刷新后重新识别
            if not boxes:
                raise RuntimeError("刷新后未找到站点选项")
            target = self._match_priority_station(boxes)
        if target is None:
            logger.info("未刷出目标站点，选择第一个选项")
            target = boxes[0]
        logger.info(f"选择站点: {target.text}")
        self.operator.click_box(target)
        self.current_station = target.text
        self.operator.sleep(0.5)
        self.operator.click_img(DUIMG.ENSURE, after_sleep=0.5)
        return True

    def _match_priority_station(self, boxes):
        """返回第一个匹配 station_priority 的选项，没有则返回 None"""
        return next(
            (box for box in boxes if any(station in box.text for station in self.station_priority)),
            None,
        )

    def handle_area_select(self):
        self.operator.click_point(0.5, 0.4, x_offset=-140, tag="选择区域")
        self.operator.click_img(DUIMG.ENSURE3, after_sleep=0.5)

    def handle_success(self):
        """处理探索成功"""
        boxes = self.operator.ocr_match(text="返回", from_x=0.3, from_y=0.88, to_x=0.7, to_y=0.93)
        if not boxes:
            raise RuntimeError("未找到探索成功按钮")
        self.operator.click_box(boxes, after_sleep=0.5)
        self.operator.click_img(IMG.ENSURE)

    def handle_wealth_station(self):
        """处理财富站点"""
        self._find_door_and_align()
        self._move_forward_until_found("战利品")
        self.operator.press_key("f")
        self.select()
        return True

    def _quit_game(self, temporary=False):
        """退出游戏"""
        logger.info("退出差分宇宙")
        for _ in range(30):
            if not self.operator.locate(DUIMG.END_AND_SETTLE):
                self.operator.press_key("esc")
                self.operator.sleep(1)
            else:
                break
        else:
            logger.error("等待结算退出入口超时")
            return False
        
        if temporary:  # 暂离
            self.operator.click_point(0.8, 0.83, after_sleep=0.5, tag="暂离")
            return True
        else:
            self.operator.click_point(0.8, 0.9, after_sleep=0.5, tag="退出并结算")
        box = self.operator.wait_img(IMG.ENSURE2)
        if box is None:
            logger.warning("未找到结算确认按钮")
            return False

        self.operator.click_box(box)

        logger.info("返回主界面")
        if self.operator.wait_img(DUIMG.RETURN):
            self.operator.click_img(DUIMG.RETURN, after_sleep=0.5)

        return self.operator.wait_any_img(
            [DUIMG.DIVERGENT_UNIVERSE_START, IMG.ENTER], timeout=30)

    def _return_to_main_menu(self):
        """返回主菜单"""
        self.operator.do_while(
            lambda : self.operator.press_key("esc"),
            lambda : self.operator.locate(IMG.ENTER) is None,
            interval=1, max_iterations=10
        )

    def page_locate(self, depth = 0):
        """
        定位到差分宇宙页面。
        :return: None
        """
        if depth >=10:
            logger.error("差分宇宙页面定位超时")
            return False
        page, _ = self.operator.wait_any_img([
            IMG.ENTER,
            DUIMG.DIVERGENT_UNIVERSE_START,
            DUIMG.BONUS_POINTS,
            DUIMG.DIVERGENT_UNIVERSE_QUIT
        ], interval=1)
        if page == 0:
            if self.operator.locate(DUIMG.DIVERGENT_UNIVERSE): # 差分宇宙门口
                self.operator.press_key("f")
            else:
                self.operator.press_key(self.settings.General.hotkeyF4)
                if not self.operator.wait_img(IMG.F4, timeout=20):
                    logger.error(SRAError(ErrorCode.WAIT_TIMEOUT, "等待指南界面超时"))
                    self.operator.press_key("esc")
                self.operator.click_img(IMG.COSMIC_STRIFE, after_sleep=1)  # 旷宇纷争
                self.operator.click_point(0.242, 0.441, after_sleep=0.5)  # 差分宇宙
                self.operator.click_point(0.7786, 0.8194, after_sleep=1)  # 前往参与
            return self.page_locate(depth + 1)
        elif page == 1:
            return True
        elif page == 2:
            self.operator.press_key("esc")
            return self.page_locate(depth + 1)
        elif page == 3:
            # 已在差分宇宙局内
            self.in_game = True
            return True
        else:
            logger.error("检测超时")
            return False

    def check_point_rewards(self):
        result = self.operator.ocr(from_x=0.1, from_y=0.89, to_x=0.21, to_y=0.96)
        # 格式 x/18000，OCR可能将结果切断成多个部分或产生噪声，用正则匹配开头和结尾都是18000
        if result:
            current = "".join(item[1] for item in result)
            logger.info(f"当前积分奖励: {current}")
            if re.match(r'^18000.*18000$', current):
                return True
        return False

    def receive_point_rewards(self):
        if self.operator.locate(IMG.ENTER):
            self.operator.press_key("f")
        self.operator.click_point(0.15, 0.93, tag="领取积分奖励", after_sleep=1)
        if self.operator.click_img(DUIMG.RECEIVE, after_sleep=1):
            self.operator.press_key("esc")