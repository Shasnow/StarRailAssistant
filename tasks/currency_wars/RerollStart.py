import re

from loguru import logger

from SRACore.util.logger import auto_log_methods
from SRACore.util.notify import try_send_notification
from SRACore.task import Executable
from tasks.currency_wars.img import CWIMG, IMG
from .CurrencyWars import CurrencyWars


@auto_log_methods
class RerollStart(Executable):
    # 坐标常量
    STRATEGY_SELECT_X = 0.5
    STRATEGY_SELECT_Y = 0.68
    STRATEGY_CONFIRM_Y = 0.90
    CENTER_X = 0.5  # 未使用的变量
    CENTER_Y = 0.5  # 未使用的变量

    # OCR 区域常量（回退方案）
    OCR_FALLBACK_LEFT = 0.15  # 未使用的变量
    OCR_FALLBACK_TOP = 0.78  # 未使用的变量
    OCR_FALLBACK_RIGHT = 0.95  # 未使用的变量
    OCR_FALLBACK_BOTTOM = 0.92  # 未使用的变量

    # 刷新限制常量
    MAX_REFRESH_CAP = 30  # 未使用的变量
    FALLBACK_REFRESH_ATTEMPTS = 3  # 未使用的变量

    # 页面类型常量
    PAGE_ERROR = -1
    PAGE_START = 1
    PAGE_PREPARATION = 2

    def __init__(self, operator, invest_env:str, invest_strategy:str, invest_strategy_stage:int, max_retry:int):
        super().__init__(operator)
        # 需要的开局
        self.wanted_invest_environment = invest_env.split() if invest_env else []
        self.wanted_invest_strategy = invest_strategy.split() if invest_strategy else []
        self.wanted_invest_strategy_stage = invest_strategy_stage
        self.max_retry = max_retry
        self.cw = CurrencyWars(self.operator, 0)
        # 结算返回后需重启下一轮的标记（避免在同一轮等待策略页）
        self._just_settled = False
        # 标记：进入策略页外部接管阶段后，禁止回到初始策略/进入流程
        self._in_strategy_phase = False
        # 刷到的开局配置，用于检测是否完成刷开局需求
        self.invest_environment = None
        self.invest_strategy = None

    def _reset_cw_flags_after_abort(self, result: bool):
        """统一在结算返回后重置 CW 运行/接管标记。"""
        if result:
            self.cw.strategy_external_control = False
            self.cw.is_running = False
            # 退出策略阶段，允许下一轮重新定位与进入
            self._in_strategy_phase = False
            self.invest_environment = None
            self.invest_strategy = None
        return result

    def run(self):
        """刷开局主流程。
        逻辑：
        - 若识别到 CONTINUE_PROGRESS，则中断当前对局并结算返回，再走正常进入流程；
        - 在开局阶段判断投资环境，没有需要的环境就重开，有需要的环境时，判断是否还需要投资策略；
        - 若还需要刷投资策略，则继续执行到1-2/2-2；否则直接结束任务；
        - 在1-2/2-2用 OCR 检测是否出现需要的策略，出现则停止脚本并通知用户；
        - 未出现则中断探索（结束并结算）并重新开始；
        """
        tries = 0
        while True:
            if tries >= self.max_retry:
                logger.info(f"达到最大尝试次数{self.max_retry}，结束刷开局")
                return True
            # 页面定位
            if not self._in_strategy_phase:
                page = self._handle_page_location()
                if page == self.PAGE_ERROR:
                    return False

                # 进入流程处理
                entry_result = self._handle_entry_phase(page)
                if entry_result == "error":
                    return False
                elif entry_result == "continue":
                    tries += 1
                    logger.info(f"第 {tries} 次尝试开始刷开局")
                    continue
                elif entry_result == "settled":
                    self.operator.sleep(0.8)
                    continue
                else:
                    if self._check_tesk_success():
                        self._stop_on_wanted_opening(f'开局刷到需要的投资环境: {self.invest_environment}')
                        return True

            # 初始策略应用
            if not self._in_strategy_phase:
                tries += 1
                logger.info(f"第 {tries} 次尝试开始刷开局")
                if not self._handle_initial_strategy():
                    self.operator.sleep(1.5)
                    continue

            # 启用外部接管并推进到策略页
            logger.info("启用外部接管并推进到策略页")
            self._enable_strategy_control()
            self.cw.run_game()

            # 等待并处理策略页
            if not self._wait_for_strategy_page():
                logger.debug("未能到达策略页，继续循环")
                continue

            # 检测 1-2/2-2 关卡并处理
            detection_result = self._handle_stage_detection()
            if detection_result == "wanted_opening_reached":
                return True
            elif detection_result == "continue":
                continue

            # 默认策略推进（未进入 1-2/2-2 分支时）
            self._handle_default_strategy_advance()
            continue

    def _handle_page_location(self) -> int:
        """处理页面定位阶段。
        
        Returns:
            int: 页面类型 (PAGE_START=1, PAGE_PREPARATION=2, PAGE_ERROR=-1)
        """
        page = self.cw.page_locate()
        if page == self.PAGE_ERROR:
            logger.error("页面定位失败，无法开始游戏")
        return page

    def _handle_entry_phase(self, page: int) -> str:
        """处理进入流程阶段。
        
        Args:
            page: 页面类型
        
        Returns:
            str: "ok" 正常继续 | "continue" 需重新循环 | "settled" 已结算需重新进入 | "error" 错误终止
        """
        if page == self.PAGE_START:
            # 从开始页进入
            self._just_settled = False
            if not self._rs_enter_from_start_page():
                logger.error("进入对局流程失败，重试下一轮")
                return "continue"
            if self._just_settled:
                logger.info("完成结算返回主页，已重新进入，本轮继续")
                return "settled"
        elif page == self.PAGE_PREPARATION:
            # 准备阶段，执行结算返回
            logger.info("已处于准备阶段，进入结算返回流程")
            if not self._return_to_prep_and_abort():
                logger.error("准备阶段结算返回失败，报错终止脚本")
                return "error"
            self._just_settled = True
            self.operator.sleep(1.0)
            return "continue"
        return "ok"

    def _handle_initial_strategy(self) -> bool:
        """处理初始策略应用阶段。
        
        Returns:
            bool: True 成功 | False 失败
        """
        try:
            if not self.cw.initialize():
                logger.error("初始策略应用失败，结束本轮并重试")
                self._safe_abort_and_return()
                return False
            return True
        except Exception as e:
            logger.error(f"初始策略应用过程异常：{e}")
            self._safe_abort_and_return()
            return False

    def _enable_strategy_control(self):
        """启用策略页外部接管并设置运行状态。"""
        logger.info("启用策略页外部接管并设置运行状态。")
        self.cw.strategy_external_control = True
        self._in_strategy_phase = True
        self.cw.is_running = True

    def _check_tesk_success(self) -> bool:
        """检查任务是否成功。"""
        return (self.wanted_invest_environment == []
                or self.invest_environment in self.wanted_invest_environment) \
            and (self.wanted_invest_strategy == []
                 or self.invest_strategy in self.wanted_invest_strategy)

    def _wait_for_strategy_page(self) -> bool:
        """等待并确认到达选择投资策略界面。
        
        Returns:
            bool: True 成功到达 | False 未能到达
        """
        idx, box = self.operator.wait_any_img(
            [CWIMG.SELECT_INVEST_STRATEGY, CWIMG.CLICK_BLANK],
            timeout=45,
            interval=0.5
        )

        if idx == 1 and box is not None:
            self.operator.click_box(box, after_sleep=1)
            result = self.operator.wait_img(CWIMG.SELECT_INVEST_STRATEGY, timeout=20, interval=0.5)
            return result is not None

        return idx == 0

    def _handle_stage_detection(self) -> str:
        """处理关卡检测阶段（检测是否为对应的策略阶段（1-2/2-2）。

        Returns:
            str: "wanted_opening_reached" 找到目标开局 | "continue" 需继续循环 | "default" 使用默认流程
        """
        ret_box = self.operator.wait_img(CWIMG.RETURN_PREPARATION_PAGE, timeout=10, interval=0.5)
        if ret_box is None:
            return "default"

        self.operator.click_box(ret_box, after_sleep=1.5)
        two_two_box = self.operator.wait_img(CWIMG.TWO_TWO, timeout=6, interval=0.5)
        self.operator.click_img(CWIMG.RETURN_INVESTMENT_STRATEGY, after_sleep=2.0)

        current_stage = 1 if two_two_box is None else 2

        if current_stage < self.wanted_invest_strategy_stage:
            # 未达到目标策略阶段，不结算，继续探索
            self._handle_non_target_strategy_stage()
            return "continue"
        else:
            # 达到目标策略阶段，进入投资策略检测与刷新循环
            if self._handle_target_strategy_stage():
                return "wanted_opening_reached"
            return "continue"

    def _handle_default_strategy_advance(self):
        """处理默认策略推进（未进入 2-2 分支时）。"""
        try:
            self.operator.click_point(self.STRATEGY_SELECT_X, self.STRATEGY_SELECT_Y, after_sleep=0.5)
            self.operator.click_point(self.STRATEGY_SELECT_X, self.STRATEGY_CONFIRM_Y, after_sleep=0.8)
            self.cw.is_running = True
            self.cw.run_game()
        except Exception:
            logger.debug("默认策略推进失败，忽略并继续循环")

    def _detect_strategy(self) -> bool:
        """使用图像匹配或OCR检测是否存在目标投资策略。"""
        try:
            if '叽米金币大使' in self.wanted_invest_strategy:
                return self.operator.locate(CWIMG.JI_MI) is not None
            else:
                index, box = self.operator.wait_ocr_any(self.wanted_invest_strategy, timeout=2, interval=0.5)
                return index != -1
        except Exception as e:
            logger.warning(f"检测投资策略时发生异常：{e}")
            return False

    def _rs_enter_from_start_page(self) -> bool:
        """处理从货币战争开始页面进入对局的完整流程。(刷开局专用)"""
        start_box = self.operator.wait_img(CWIMG.CURRENCY_WARS_START, timeout=30, interval=0.5)
        if start_box is None or not self.operator.click_box(start_box):
            logger.error("未识别到开始按钮")
            return False
        self.operator.click_point(0.5, 0.5, after_sleep=2)

        # 标准进入 or 继续进度（若是继续进度则中断并返回）
        index, box = self.operator.wait_any_img([CWIMG.ENTER_STANDARD, CWIMG.CONCLUDE_AND_SETTLE], timeout=3, interval=0.5)
        if index == 0:
            # 识别到标准进入，直接点击该入口并执行标准进入流程
            if box is None:
                logger.error("未获取到标准进入按钮位置")
                return False
            return self._rs_standard_entry_flow(box)
        elif index == 1:
            # 识别到放弃并结算（继续进度的替代入口），直接点击并执行结算返回
            if box is None or not self.operator.click_box(box, after_sleep=1):
                logger.error("点击放弃并结算入口失败")
                return False
            logger.info("检测到放弃并结算入口，执行结算返回主界面")
            result = self._safe_abort_and_return()
            if result:
                # 标记：该轮仅执行了结算，需回到 while 顶部重新 page_locate
                self._just_settled = True
            return result

        logger.error("既未识别标准进入，也未识别继续进度入口")
        return False

    def _rs_standard_entry_flow(self, enter_standard_box) -> bool:
        """刷开局专用的标准进入流程：
        - 点击标准进入
        - 下拉选择到最低难度（或确保可开始）
        - 点击开始游戏
        - 通过“下一步”进入投资环境
        - 执行一次默认投资确认
        返回 True 表示完成进入并通过投资界面。
        """
        # 点击标准进入
        if not self.operator.click_box(enter_standard_box, after_sleep=1.5):
            logger.error("点击标准进入失败")
            return False
        # 返回最高名望
        self.operator.click_img(CWIMG.RETURN_HIGHEST_RANK, after_sleep=0.8)
        # 点击开始游戏
        if not self.operator.click_img(CWIMG.START_GAME, after_sleep=1):
            logger.error("未识别到开始游戏按钮")
            return False
        # “下一步”
        next_step_box = self.operator.wait_img(CWIMG.NEXT_STEP)
        self.operator.sleep(0.5)
        if next_step_box is None or not self.operator.click_box(next_step_box, after_sleep=2):
            logger.error("进入后未识别到下一步按钮")
            return False
        self.operator.click_point(0.5, 0.5, after_sleep=0.5)
        # 投资环境
        invest_box = self.operator.wait_img(CWIMG.INVEST_ENVIRONMENT)
        if invest_box is None:
            logger.error("未识别到投资环境界面")
            return False
        return self._rs_handle_invest_environment()

    def _rs_handle_invest_environment(self) -> bool:
        """刷开局专用的投资环境处理：
        - 检测需要的投资环境
        - 如果未刷到，则点击刷新
        - 如果刷新后仍未刷到，则点击收集
        - 如果收集后仍未刷到，则返回备战页面并结算返回
        - 如果刷到，则点击投资环境
        """
        if self.wanted_invest_environment == []:
            if not self.operator.click_img(IMG.COLLECTION):
                self.operator.click_point(0.5, 0.5)
            self.operator.click_img(IMG.ENSURE2, after_sleep=1)
            if self.operator.locate(CWIMG.INVEST_ENVIRONMENT):
                self.operator.click_point(0.5, 0.5)
                self.operator.click_img(IMG.ENSURE2, after_sleep=1)
            self.operator.sleep(4)
            return True

        index, box = self.operator.wait_ocr_any(self.wanted_invest_environment, timeout=2, interval=0.5)
        if index == -1:
            box = self.operator.wait_img(CWIMG.REFRESH_ENV, timeout=2, interval=0.5)
            if box is not None and self.operator.click_box(box, after_sleep=1):
                index, box = self.operator.wait_ocr_any(self.wanted_invest_environment, timeout=2, interval=0.5)
        if index == -1:
            logger.info("未刷到需要的投资环境")
            if not self.operator.click_img(IMG.COLLECTION):
                self.operator.click_point(0.5, 0.5)
            self.operator.click_img(IMG.ENSURE2, after_sleep=1)
            if self.operator.locate(CWIMG.INVEST_ENVIRONMENT):
                self.operator.click_point(0.5, 0.5)
                self.operator.click_img(IMG.ENSURE2, after_sleep=1)
            self._return_to_prep_and_abort()
            self.operator.sleep(2)
            return False

        logger.info(f"刷到需要的投资环境: {self.wanted_invest_environment[index]}")
        if self.operator.click_box(box, after_sleep=1):
            self.operator.click_img(IMG.ENSURE2, after_sleep=1)
        self.invest_environment = self.wanted_invest_environment[index]
        self.operator.sleep(4)
        return True

    def _safe_abort_and_return(self) -> bool:
        """兼容旧用法：开始界面直接结算返回到货币战争主界面。"""
        result = self._abort_and_return(in_game=False)
        # 重置CW运行与接管状态，确保下一轮回到page_locate流程
        return self._reset_cw_flags_after_abort(result)

    def _return_to_prep_and_abort(self) -> bool:
        """兼容旧用法：对局中先返回备战再结算返回主页。"""
        result = self._abort_and_return(in_game=True)
        # 重置CW运行与接管状态，确保下一轮回到page_locate流程
        return self._reset_cw_flags_after_abort(result)

    def _abort_and_return(self, in_game: bool) -> bool:
        """统一的结算返回流程。
        - in_game=True：先点击`RETURN_PREPARATION_PAGE`并按`ESC`，再执行结算返回。
        - in_game=False：直接执行结算返回（用于开始界面或无需返回备战的场景）。
        点击顺序（结算部分）：WITHDRAW_AND_SETTLE → NEXT_STEP → NEXT_PAGE → BACK_CURRENCY_WARS
        """
        try:
            if in_game:
                # 返回备战页面
                ret_box = self.operator.wait_img(CWIMG.RETURN_PREPARATION_PAGE, timeout=6, interval=0.5)
                if ret_box is not None:
                    self.operator.click_box(ret_box, after_sleep=1.0)
                # 关闭覆盖层
                self.operator.press_key('esc')
                self.operator.sleep(0.8)

            # 放弃并结算
            withdraw_and_settle = self.operator.wait_img(CWIMG.WITHDRAW_AND_SETTLE, timeout=8, interval=0.5)
            if withdraw_and_settle is None:
                logger.error("未识别到放弃并结算入口")
                return False
            self.operator.click_box(withdraw_and_settle, after_sleep=2.5)

            # 下一步
            next_step = self.operator.wait_img(CWIMG.NEXT_STEP, timeout=8, interval=0.5)
            if next_step is None:
                logger.error("点击放弃并结算后，未识别到下一步")
                return False
            self.operator.click_box(next_step, after_sleep=1.8)

            # 下一页
            next_page = self.operator.wait_img(CWIMG.NEXT_PAGE, timeout=8, interval=0.5)
            if next_page is None:
                logger.error("点击下一步后，未识别到下一页")
                return False
            self.operator.click_box(next_page, after_sleep=1.8)

            # 返回货币战争主页
            back_currency_wars = self.operator.wait_img(CWIMG.BACK_CURRENCY_WARS, timeout=8, interval=0.5)
            if back_currency_wars is None:
                logger.error("点击下一页后，未识别到返回货币战争")
                return False
            self.operator.click_box(back_currency_wars, after_sleep=2)
            logger.info("已结算并返回货币战争主界面")
            return True
        except Exception as e:
            logger.error(f"结算返回流程异常：{e}")
            return False

    def _collect_refresh_counts(self, max_items: int = 3) -> list[int]:
        """基于 REFRESH_COUNT 锚点，OCR 其右侧同一行的刷新次数，返回列表（最多 max_items 个）。

        实际UI：三个刷新次数同处同一行，形如“刷新次数1 刷新次数2 刷新次数3”。
        方案：以锚点为起点，截取其右侧一段“行高”的细长区域，做一次 OCR，按从左到右解析出最多3个数字。
        """
        counts: list[int] = []
        try:
            win = self.operator.get_win_region(active_window=True)
        except Exception:
            return counts
        if win is None:
            return counts

        # 单一锚点
        anchor = self.operator.locate(CWIMG.REFRESH_COUNT)
        if anchor is None:
            logger.debug("未找到刷新次数锚点，改用回退OCR区域尝试识别")
            # 回退方案：在预估的横条区域进行一次OCR（基于常见UI布局），尽量读取数字
            try:
                # 经验区域：界面底部靠上的横条（适配1920x1080及缩放）
                # from_y/to_y 根据日志中点击y≈856（约0.79-0.82）来设定一个稍宽的条带
                results = self.operator.ocr(from_x=0.15, from_y=0.78, to_x=0.95, to_y=0.92, trace=False) or []
                if results:
                    # 左到右排序后拼接
                    items = sorted(results, key=lambda r: r[0][0][0])
                    line = " ".join([str(r[1]) for r in items])
                    logger.debug(f"刷新次数OCR(回退)结果行: '{line}'")
                    pattern = r"刷\s*新\s*次\s*数\s*(\d+)"
                    found = [int(x) for x in re.findall(pattern, line)]
                    if found:
                        return found[:max_items]
                    nums = [int(x) for x in re.findall(r"(\d+)", line)]
                    return nums[:max_items]
            except Exception as e:
                logger.trace(f"回退OCR识别刷新次数失败: {e}")
            return counts

        # 输出锚点坐标用于调试与后续参考
        logger.debug(
            f"刷新次数锚点定位: left={anchor.left}, top={anchor.top}, "
            f"width={anchor.width}, height={anchor.height}"
        )
        logger.debug(f"窗口区域: left={win.left}, top={win.top}, width={win.width}, height={win.height}")

        rel_top = max(0.0, min(1.0, anchor.top / float(win.height)))
        rel_bottom = max(rel_top, min(1.0, (anchor.top + anchor.height) / float(win.height)))
        left = int(win.left)
        top = int(win.top + rel_top * win.height)
        width = int(win.width)
        height = int(max(1.0, (rel_bottom - rel_top) * win.height))

        logger.debug(
            f"OCR区域: rel=(0.0,{rel_top:.6f},1.0,{rel_bottom:.6f}), px=(left={left},top={top},w={width},h={height})"
        )

        if width <= 0 or height <= 0:
            return counts

        results = self.operator.ocr(from_x=0.0, from_y=rel_top, to_x=1.0, to_y=rel_bottom, trace=False) or []
        if not results:
            return counts

        # 左到右排序后拼接成一行文本
        items = sorted(results, key=lambda r: r[0][0][0])
        line = " ".join([str(r[1]) for r in items])
        logger.debug(f"刷新次数OCR结果行: '{line}'")

        # 优先匹配“刷新次数<数字>”模式（OCR 可能分词，允许空白）
        pattern = r"刷\s*新\s*次\s*数\s*(\d+)"
        found = [int(x) for x in re.findall(pattern, line)]
        if found:
            return found[:max_items]

        # 回退：在该行内提取所有数字（可能包含干扰，但区域较窄，通常只有目标数字）
        nums = [int(x) for x in re.findall(r"(\d+)", line)]
        return nums[:max_items]

    def _handle_target_strategy_stage(self) -> bool:
        """处理 2-2 关卡的投资策略检测与刷新循环。

        Returns:
            True: 检测到目标投资策略，脚本应停止
            False: 未检测到目标策略，继续外层流程
        """
        # 首次投资策略检测

        if self._detect_strategy():
            return self._stop_on_wanted_opening(f'找到需要的投资策略: {self.invest_strategy}')

        # 动态 OCR 刷新循环：每轮以最新 OCR 结果为准
        total_clicks = 0
        safe_cap = 30

        while total_clicks < safe_cap:
            counts = self._try_collect_refresh_counts()

            # 有有效 OCR 结果时：全部为 0 则直接结算退出
            if counts:
                nonneg = [x for x in counts if isinstance(x, int) and x >= 0]
                if nonneg and all(x == 0 for x in nonneg):
                    logger.info("动态OCR检测到刷新次数为 0，执行返回备战并结算本轮")
                    self._return_to_prep_and_abort()
                    self.operator.sleep(2.0)
                    return False

            # 按钮不可用/未找到也视为次数用尽
            if not self._click_refresh_button():
                logger.info("刷新按钮不可用或未找到，视为刷新次数已用尽，执行返回备战并结算本轮")
                self._return_to_prep_and_abort()
                self.operator.sleep(2.0)
                return False

            total_clicks += 1
            self.operator.sleep(1.2)

            # 刷新后再次检测投资策略
            if self._detect_strategy():
                return self._stop_on_wanted_opening(f'找到需要的投资策略: {self.invest_strategy}')

        logger.info("达到安全刷新上限，执行返回备战并结算本轮")
        self._return_to_prep_and_abort()
        self.operator.sleep(2.0)
        return False

    def _handle_non_target_strategy_stage(self):
        """处理非2-2关卡：选择默认策略并手动推进到下一个策略页。
        
        执行流程:
        1. 关闭返回备战覆盖层
        2. 选择中间策略并确认
        3. 整理场面(收起商店、收获水晶、放置/出售角色)
        4. 手动推进战斗→关卡切换→商店,直到再次到达策略页
        
        Note:
            不能调用cw.run_game(),因为会执行常规策略事件流程。
            必须手动调用battle→stage_transition→shopping以回到策略页等待。
        """
        logger.info("当前并非 2-2，继续探索本轮")
        try:
            # 关闭返回备战覆盖层
            self.operator.press_key('esc')
            self.operator.sleep(0.8)
            click_blank = self.operator.wait_img(CWIMG.CLICK_BLANK, timeout=3, interval=0.5)
            if click_blank is not None:
                self.operator.click_box(click_blank, after_sleep=0.8)

            # 选择策略并推进
            self.operator.click_point(0.5, 0.68, after_sleep=0.6)
            self.operator.click_point(0.5, 0.90, after_sleep=0.8)
            self.operator.sleep(2.0)

            # 整理场面状态
            fold_box = self.operator.wait_img(CWIMG.FOLD, timeout=2)
            if fold_box is not None:
                self.operator.click_box(fold_box, after_sleep=1)
            self.cw.harvest_crystals()
            self.cw.refresh_character()
            self.cw.get_in_hand_area()
            self.cw.place_character()
            self.cw.sell_character()

            # 手动推进：battle → stage_transition → shopping
            self.cw.is_running = True
            if self.cw.battle():
                self.cw.stage_transition()
                self.cw.shopping()
                self.cw.harvest_crystals()
                self.cw.get_in_hand_area(True)
        except Exception as e:
            logger.debug(f"继续探索推进过程出现异常：{e}，忽略并进入下一轮等待")

    def _determine_max_refresh_attempts(self) -> int:
        """确定本轮最大刷新尝试次数。
        
        Returns:
            max_attempts: 基于OCR或保守策略的最大尝试次数
        """
        safe_cap = 30
        fallback_attempts = 3

        try:
            init_counts = self._collect_refresh_counts(max_items=3)
            if init_counts:
                logger.info(f"刷新次数初始记录: {init_counts}")
                nonneg = [x for x in init_counts if isinstance(x, int) and x >= 0]
                if nonneg:
                    if all(x == 0 for x in nonneg):
                        logger.info("检测到刷新次数为0，执行返回备战并结算本轮")
                        self._return_to_prep_and_abort()
                        self.operator.sleep(2.0)
                        return 0
                    return min(sum(nonneg), safe_cap)

            logger.info("刷新次数OCR不可用，采用保守策略：最多尝试 3 次刷新")
            return fallback_attempts
        except Exception as e:
            logger.trace(f"采集刷新次数异常: {e}")
            return fallback_attempts

    def _try_collect_refresh_counts(self) -> list[int]:
        """尝试采集刷新次数(不阻塞流程)。
        
        Returns:
            list[int]: 刷新次数列表[位置1, 位置2, 位置3]；OCR失败时返回空列表
            
        Note:
            此方法封装了异常处理,确保OCR失败不会中断主流程
        """
        try:
            counts = self._collect_refresh_counts(max_items=3)
            if counts:
                logger.info(f"刷新次数记录: {counts}")
            return counts or []
        except Exception as e:
            logger.trace(f"采集刷新次数异常: {e}")
            return []

    def _stop_on_wanted_opening(self, message: str) -> bool:
        """检测到需要的开局后的统一停止处理。
        
        Args:
            message (str): 日志消息前缀,用于区分不同检测场景
            
        Returns:
            bool: 始终返回True,表示脚本应立即停止
            
        Side Effects:
            - 发送Windows系统通知
            - 设置 self.is_running = False
            - 设置 self.cw.is_running = False
            - 重置 self._in_strategy_phase = False
        """
        logger.success(f"{message}，停止脚本并通知用户")
        # 根据设置开关优先走 SRA 的通知
        try_send_notification("SRA", f"刷到需要的开局，脚本已停止: {message}")
        self.is_running = False
        if hasattr(self, 'cw'):
            self.cw.is_running = False
        self._in_strategy_phase = False
        return True

    def _click_refresh_button(self) -> bool:
        """点击策略刷新按钮(REFRESH_COUNT_BTN)。
        
        Returns:
            bool: 成功点击返回True; 按钮不存在或不可用时返回False
        """
        btn = self.operator.wait_img(CWIMG.REFRESH_COUNT_BTN, timeout=6, interval=0.5)
        if btn is None:
            logger.debug("未找到刷新按钮")
            return False
        return self.operator.click_box(btn, after_sleep=1.0)
