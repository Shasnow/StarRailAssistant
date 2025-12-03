import re

from loguru import logger

from SRACore.util.notify import send_windows_notification
from SRACore.util.operator import Executable
from tasks.currency_wars.img import CWIMG, IMG

from .CurrencyWars import CurrencyWars


class BrushOpening(Executable):
    def __init__(self, run_times):
        super().__init__()
        self.run_times = run_times
        self.force_battle = False
        self.cw = CurrencyWars(run_times)
        # 结算返回后需重启下一轮的标记（避免在同一轮等待策略页）
        self._just_settled = False
        # 轻量通用配置：统一点击后的短暂停顿（不改变原有各处的具体等待）
        self._default_after_click_sleep = 1.0
        # 标记：进入策略页外部接管阶段后，禁止回到初始策略/进入流程
        self._in_strategy_phase = False

    # —— 微型助手方法：仅用于提升可读性与健壮性 ——
    def _wait_then_click_box(self, img, *, timeout=8, interval=0.5, after_sleep=None):
        """等待图像并点击其区域。保持与原有 wait_img + click_box 组合一致的行为。

        不改变业务顺序与时间参数的默认值；仅封装以减少重复代码。
        """
        box = self.wait_img(img, timeout=timeout, interval=interval)
        if box is None:
            return None
        self.click_box(box, after_sleep=(self._default_after_click_sleep if after_sleep is None else after_sleep))
        return box

    def _reset_cw_flags_after_abort(self, result: bool):
        """统一在结算返回后重置 CW 运行/接管标记。"""
        if result:
            self.cw.strategy_external_control = False
            self.cw.is_running = False
            # 退出策略阶段，允许下一轮重新定位与进入
            self._in_strategy_phase = False
        return result
        
    def openning(self):
        """刷开局主流程。
        需求：
        - 若识别到 CONTINUE_PROGRESS，则中断当前对局并结算返回，再走正常进入流程；
        - 循环直到首次识别到“选择投资策略”界面；
        - 在该界面 OCR 检测是否出现“叽米”，出现则停止脚本并通知用户；
        - 未出现则中断探索（结束并结算）并重新开始；
        """
        tries = 0
        while True:
            # 在策略阶段外才进行页面定位与进入流程；策略阶段内直接进行策略页等待与判定
            if not self._in_strategy_phase:
                page = self.cw.page_locate()
                if page == -1:
                    logger.error("页面定位失败，无法开始游戏")
                    return False

            # 进入流程：从开始页进入；准备阶段直接继续
            if not self._in_strategy_phase and page == 1:
                # 先清除上轮残留的结算标记，仅在本轮确实进行“继续进度→结算返回”时再置位。
                self._just_settled = False
                if not self._bo_enter_from_start_page():
                    logger.error("进入对局流程失败，重试下一轮")
                    continue
                # 若本轮识别到了“继续进度”并已结算返回，则回到顶部重新定位与进入。
                if self._just_settled:
                    logger.info("完成结算返回主页，已重新进入，本轮继续")
                    self.sleep(0.8)
                    continue
            elif not self._in_strategy_phase and page == 2:
                logger.info("已处于准备阶段，进入结算返回流程")
                if not self._return_to_prep_and_abort():
                    logger.error("准备阶段结算返回失败，报错终止脚本")
                    return False
                # 结算成功后已回到货币战争主页，下一轮应重新定位并进入
                self._just_settled = True
                self.sleep(1.0)
                continue

            # 到这里才算正式开始一次刷开局尝试（为了排除仅“继续进度→结算返回”的前置流程）
            # 若当前处于策略页外部接管，则不应计为一次新的尝试（避免二次触发策略页时误增尝试次数）
            if not self._in_strategy_phase:
                tries += 1
                logger.info(f"开始刷开局，第 {tries} 次尝试")
            # 进入后应用一次初始策略，与 CW 正常流程一致
            if not self._in_strategy_phase:
                try:
                    if not self.cw._apply_initial_strategy():
                        logger.error("初始策略应用失败，结束本轮并重试")
                        self._safe_abort_and_return()
                        self.sleep(1.5)
                        continue
                except Exception as e:
                    logger.error(f"初始策略应用过程异常：{e}")
                    self._safe_abort_and_return()
                    self.sleep(1.5)
                    continue
            # 启用策略页外部接管：在识别到“选择投资策略”页时，CW停止推进，由本流程处理2-2与叽米判断
            self.cw.strategy_external_control = True
            self._in_strategy_phase = True
            # 确保 CW 进入运行状态，否则 run_game() 循环不会执行
            self.cw.is_running = True
            # 运行一次 CW 的战斗与关卡推进，直到到达策略页被外部接管为止
            self.cw.run_game()
            
            # 等待到“选择投资策略”界面
            idx, box = self.wait_any_img([CWIMG.SELECT_INVEST_STRATEGY, CWIMG.CLICK_BLANK], timeout=45, interval=0.5)

            if idx == 1 and box is not None:
                self.click_box(box, after_sleep=1)
                _ = self.wait_img(CWIMG.SELECT_INVEST_STRATEGY, timeout=20, interval=0.5)

            # 下方逻辑为  在策略页面后，识别是否为 2-2。不是 2-2 则继续探索，是 2-2 则进入叽米判定逻辑。
            ret_box = self.wait_img(CWIMG.RETURN_PREPARATION_PAGE, timeout=10, interval=0.5)
            if ret_box is not None:
                self.click_box(ret_box, after_sleep=1.5)
                # 识别是否为 2-2 关卡
                two_two_box = self.wait_img(CWIMG.TWO_TWO, timeout=6, interval=0.5)
                # 点击返回投资策略界面
                self.click_img(CWIMG.RETURN_INVESTMENT_STRATEGY, after_sleep=2.0)
                if two_two_box is not None:
                    # 命中 2-2：进入叽米判定逻辑
                    if self._detect_jimi():
                        logger.success("2-2 关卡识别到叽米，停止脚本并通知用户")
                        try:
                            send_windows_notification("SRA", "刷开局命中叽米，脚本已停止")
                        except Exception:
                            logger.warning("通知模块调用失败")
                        self.is_running = False
                        if hasattr(self, 'cw'):
                            self.cw.is_running = False
                        self._in_strategy_phase = False
                        return True

                    # 未命中叽米：消耗刷新次数逐次检测，直到刷新用尽或命中为止
                    # 动态上限：优先由OCR决定；不可用时使用安全兜底（3 次）
                    refresh_attempts = 0  # 已尝试刷新次数
                    safe_cap = 30  # 兜底上限（用于读取成功时的最大保护）
                    fallback_attempts = 3  # OCR 不可用时，默认尝试 3 次
                    consecutive_ocr_fail = 0  # 连续 OCR 失败计数
                    max_attempts = safe_cap  # 本轮最大尝试刷新次数
                    # 先尝试读取一次作为初始上限依据
                    try:
                        init_counts = self._collect_refresh_counts(max_items=3)
                        if init_counts:
                            logger.info(f"刷新次数初始记录: {init_counts}")
                            # 若能读到非零，取其总和或最大值作为本轮可刷新上限
                            nonneg = [x for x in init_counts if isinstance(x, int) and x >= 0]
                            if nonneg:
                                # 三个位置取总和；如OCR拆分异常也不超过safe_cap
                                max_attempts = min(sum(nonneg), 30) or safe_cap
                                if all(x == 0 for x in nonneg):
                                    logger.info("检测到刷新次数为0，执行返回备战并结算本轮")
                                    self._return_to_prep_and_abort()
                                    self.sleep(2.0)
                                    continue
                        else:
                            # 初次读取失败：采用保守策略，最多尝试 3 次刷新
                            consecutive_ocr_fail += 1
                            max_attempts = fallback_attempts
                            logger.info("刷新次数OCR不可用，采用保守策略：最多尝试 3 次刷新")
                    except Exception as e:
                        logger.trace(f"采集刷新次数异常: {e}")

                    while refresh_attempts < max_attempts:
                        try:
                            counts = self._collect_refresh_counts(max_items=3)
                            if counts:
                                consecutive_ocr_fail = 0
                                logger.info(f"刷新次数记录: {counts}")
                                # 如果检测到全部为0，则认为刷新次数已用尽
                                if all(isinstance(x, int) and x == 0 for x in counts):
                                    logger.info("检测到刷新次数已用尽，执行返回备战并结算本轮")
                                    self._return_to_prep_and_abort()
                                    self.sleep(2.0)
                                    break
                            else:
                                # OCR 未读到数字时，不再提前退出；继续走“尝试点击刷新按钮”策略
                                consecutive_ocr_fail += 1
                                if consecutive_ocr_fail == 1 and max_attempts == safe_cap:
                                    # 中途 OCR 开始失败但此前读过次数：保持之前推导的 max_attempts，不做调整
                                    logger.debug("OCR未读到次数，沿用先前上限并继续尝试刷新")
                        except Exception as e:
                            logger.trace(f"采集刷新次数异常: {e}")

                        # 尝试点击刷新按钮；若按钮不可用/不存在，视为已用尽
                        if not self._click_refresh_button():
                            logger.info("刷新按钮不可用或未找到，可能已用尽刷新次数，执行返回备战并结算本轮")
                            self._return_to_prep_and_abort()
                            self.sleep(2.0)
                            break

                        refresh_attempts += 1
                        self.sleep(1.2)
                        if self._detect_jimi():
                            logger.success("刷新后识别到叽米，停止脚本并通知用户")
                            try:
                                send_windows_notification("SRA", "刷新后命中叽米，脚本已停止")
                            except Exception:
                                logger.warning("通知模块调用失败")
                            self.is_running = False
                            if hasattr(self, 'cw'):
                                self.cw.is_running = False
                            return True
                    # 如果循环自然结束且未命中叽米，继续外层流程
                    continue
                else:
                    # 非 2-2：不结算，继续探索（尽量回到策略界面并按默认策略继续）
                    logger.info("当前并非 2-2，继续探索本轮")
                    try:
                        # 关闭返回备战覆盖层
                        self.press_key('esc')
                        self.sleep(0.8)
                        # 若仍有“点击空白处关闭”，点击一次
                        click_blank = self.wait_img(CWIMG.CLICK_BLANK, timeout=3, interval=0.5)
                        if click_blank is not None:
                            self.click_box(click_blank, after_sleep=0.8)
                        # 模拟CW的默认策略选择：点中间策略并确认，以推进进程
                        self.click_point(0.5, 0.68, after_sleep=0.6)
                        self.click_point(0.5, 0.90, after_sleep=0.8)
                        self.sleep(2.0)
                        
                        #若无下方操作，会导致交还CW后直接进入battle逻辑，卡死
                        fold_box = self.wait_img(CWIMG.FOLD, timeout=2) # 判断商店是否为未收起状态
                        if fold_box is not None:
                            self.click_box(fold_box, after_sleep=1)
                        self.cw.harvest_crystals()  # 收获水晶
                        self.cw.refresh_character()  # 更新角色信息
                        self.cw.get_in_hand_area()  # 更新手牌信息
                        self.cw.place_character()  # 放置角色
                        self.cw.sell_character()  # 出售多余角色
                        
                        # 策略处理完成后，需推进战斗与节点切换直到下一个策略页
                        # 不能直接调用 run_game()，因为它会先执行 strategy_event 等常规流程
                        # 应手动推进：battle → stage_transition，直到再次到达策略页
                        self.cw.is_running = True
                        if self.cw.battle():
                            self.cw.stage_transition()
                            # stage_transition 会在遇到策略页时设置 is_running=False 并退出
                            # 此时回到 BrushOpening 的 while 顶部，重新等待策略页
                            self.cw.shopping()
                            self.cw.harvest_crystals()
                            self.cw.get_in_hand_area(True)
                    except Exception as e:
                        logger.debug(f"继续探索推进过程出现异常：{e}，忽略并进入下一轮等待")
                    # 回到等待下一个策略页/节点的循环
                    continue

            # 走到此处表示：未进入 2-2 分支或未触发返回备战逻辑。
            # 使用默认操作推进一次策略选择，继续等待下一次策略页。
            try:
                self.click_point(0.5, 0.68, after_sleep=0.5)
                self.click_point(0.5, 0.90, after_sleep=0.8)
                # 默认策略推进后，交还给 CW 继续战斗与推进
                self.cw.is_running = True
                self.cw.run_game()
            except Exception:
                logger.debug("默认策略推进失败，忽略并继续循环")
            continue

    def _detect_jimi(self) -> bool:
        """使用图像匹配检测是否存在叽米图片。"""
        try:
            return self.locate(CWIMG.JI_MI) is not None
        except Exception as e:
            logger.warning(f"检测叽米图片时发生异常：{e}")
            return False

    def _bo_enter_from_start_page(self) -> bool:
        """处理从货币战争开始页面进入对局的完整流程。(刷开局专用)"""
        start_box = self.wait_img(CWIMG.CURRENCY_WARS_START, timeout=30, interval=0.5)
        if start_box is None or not self.click_box(start_box):
            logger.error("未识别到开始按钮")
            return False
        self.click_point(0.5, 0.5, after_sleep=2)

        # 标准进入 or 继续进度（若是继续进度则中断并返回）
        index, box = self.wait_any_img([CWIMG.ENTER_STANDARD, CWIMG.CONCLUDE_AND_SETTLE], timeout=3, interval=0.5)
        if index == 0:
            # 识别到标准进入，直接点击该入口并执行标准进入流程
            if box is None:
                logger.error("未获取到标准进入按钮位置")
                return False
            return self._bo_standard_entry_flow(box)
        elif index == 1:
            # 识别到放弃并结算（继续进度的替代入口），直接点击并执行结算返回
            if box is None or not self.click_box(box, after_sleep=1):
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

    def _bo_standard_entry_flow(self, enter_standard_box) -> bool:
        """刷开局专用的标准进入流程：
        - 点击标准进入
        - 下拉选择到最低难度（或确保可开始）
        - 点击开始游戏
        - 通过“下一步”进入投资环境
        - 执行一次默认投资确认
        返回 True 表示完成进入并通过投资界面。
        """
        # 点击标准进入
        if not self.click_box(enter_standard_box, after_sleep=1.5):
            logger.error("点击标准进入失败")
            return False
        # 返回最高名望
        try:
            highest_rank = self.wait_img(CWIMG.RETURN_HIGHEST_RANK, timeout=5, interval=0.5)
            if highest_rank is not None:
                self.click_box(highest_rank, after_sleep=0.8)
            else:
                logger.info("未识别到返回最高名望按钮，继续后续流程")
        except Exception:
            logger.trace("返回最高名望步骤跳过")
        # 点击开始游戏
        if not self.click_img(CWIMG.START_GAME, after_sleep=1):
            logger.error("未识别到开始游戏按钮")
            return False
        # “下一步”
        next_step_box = self.wait_img(CWIMG.NEXT_STEP)
        self.sleep(0.5)
        if next_step_box is None or not self.click_box(next_step_box, after_sleep=2):
            logger.error("进入后未识别到下一步按钮")
            return False
        self.click_point(0.5, 0.5, after_sleep=0.5)
        # 投资环境
        invest_box = self.wait_img(CWIMG.INVEST_ENVIRONMENT)
        if invest_box is None:
            logger.error("未识别到投资环境界面")
            return False
        # 投资操作（与CW一致逻辑）
        if not self.click_img(IMG.COLLECTION):
            self.click_point(0.5, 0.5)
        self.click_img(IMG.ENSURE2, after_sleep=1)
        if self.locate(CWIMG.INVEST_ENVIRONMENT):
            self.click_point(0.5, 0.5)
            self.click_img(IMG.ENSURE2, after_sleep=1)
        self.sleep(4)
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
                ret_box = self.wait_img(CWIMG.RETURN_PREPARATION_PAGE, timeout=6, interval=0.5)
                if ret_box is not None:
                    self.click_box(ret_box, after_sleep=1.0)
                # 关闭覆盖层
                self.press_key('esc')
                self.sleep(0.8)

            # 放弃并结算
            withdraw_and_settle = self.wait_img(CWIMG.WITHDRAW_AND_SETTLE, timeout=8, interval=0.5)
            if withdraw_and_settle is None:
                logger.error("未识别到放弃并结算入口")
                return False
            self.click_box(withdraw_and_settle, after_sleep=2.5)

            # 下一步
            next_step = self.wait_img(CWIMG.NEXT_STEP, timeout=8, interval=0.5)
            if next_step is None:
                logger.error("点击放弃并结算后，未识别到下一步")
                return False
            self.click_box(next_step, after_sleep=1.8)

            # 下一页
            next_page = self.wait_img(CWIMG.NEXT_PAGE, timeout=8, interval=0.5)
            if next_page is None:
                logger.error("点击下一步后，未识别到下一页")
                return False
            self.click_box(next_page, after_sleep=1.8)

            # 返回货币战争主页
            back_currency_wars = self.wait_img(CWIMG.BACK_CURRENCY_WARS, timeout=8, interval=0.5)
            if back_currency_wars is None:
                logger.error("点击下一页后，未识别到返回货币战争")
                return False
            self.click_box(back_currency_wars, after_sleep=2)
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
            win = self.get_win_region(active_window=True)
        except Exception:
            return counts
        if win is None:
            return counts

        # 单一锚点
        anchor = self.locate(CWIMG.REFRESH_COUNT)
        if anchor is None:
            logger.debug("未找到刷新次数锚点，改用回退OCR区域尝试识别")
            # 回退方案：在预估的横条区域进行一次OCR（基于常见UI布局），尽量读取数字
            try:
                # 经验区域：界面底部靠上的横条（适配1920x1080及缩放）
                # from_y/to_y 根据日志中点击y≈856（约0.79-0.82）来设定一个稍宽的条带
                results = self.ocr_in_tuple(0.15, 0.78, 0.95, 0.92, trace=False) or []
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
        height = int(max(1, (rel_bottom - rel_top) * win.height))

        logger.debug(
            f"OCR区域: rel=(0.0,{rel_top:.6f},1.0,{rel_bottom:.6f}), px=(left={left},top={top},w={width},h={height})"
        )
        
        if width <= 0 or height <= 0:
            return counts

        results = self.ocr_in_tuple(0.0, rel_top, 1.0, rel_bottom, trace=False) or []
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

    def _click_refresh_button(self) -> bool:
        """点击刷新按钮（REFRESH_COUNT_BTN）。"""
        btn = self.wait_img(CWIMG.REFRESH_COUNT_BTN, timeout=6, interval=0.5)
        if btn is None:
            logger.debug("未找到刷新按钮")
            return False
        return self.click_box(btn, after_sleep=1.0)
    