import re
import time
from pathlib import Path

from loguru import logger

from SRACore.util.notify import send_windows_notification
from SRACore.util.operator import Executable, Region
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

            page = self.cw.page_locate()
            if page == -1:
                logger.error("页面定位失败，无法开始游戏")
                return False

            # 进入流程：从开始页进入；准备阶段直接继续
            if page == 1:
                if not self._bo_enter_from_start_page():
                    logger.error("进入对局流程失败，重试下一轮")
                    continue
                # 如果刚刚进行了“放弃并结算”，本轮应直接重启进入流程
                if self._just_settled:
                    logger.info("完成结算返回主页，开启下一轮刷开局")
                    self._just_settled = False
                    self.sleep(1.0)
                    continue
            elif page == 2:
                logger.info("已处于准备阶段，进入结算返回流程")
                if not self._return_to_prep_and_abort():
                    logger.error("准备阶段结算返回失败，报错终止脚本")
                    return False

            # 到这里才算正式开始一次刷开局尝试（排除仅“继续进度→结算返回”的前置流程）
            tries += 1
            logger.info(f"开始刷开局，第 {tries} 次尝试")
            # 进入后应用一次初始策略，保持与 CW 正常流程一致
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
            # 确保 CW 进入运行状态，否则 run_game() 循环不会执行
            self.cw.is_running = True
            # 运行一次 CW 的战斗与关卡推进，直到到达策略页被外部接管为止
            
            self.cw.run_game()
            

            # 等待到首次“选择投资策略”界面（提高超时阈值，增强稳定性）
            idx, box = self.wait_any_img([CWIMG.SELECT_INVEST_STRATEGY, CWIMG.CLICK_BLANK], timeout=45, interval=0.5)
            if idx == -1:
                logger.warning("未在限定时间内到达选择投资策略界面，结束本轮并重试")
                # 结算返回后增加短暂稳定等待，避免下一轮立即识图失败
                self._safe_abort_and_return()
                self.sleep(2.0)
                continue

            # 保证在策略界面停留，避免误关
            if idx == 1 and box is not None:
                # 如果出现“点击空白处关闭”，先点击以继续弹出策略
                self.click_box(box, after_sleep=1)
                # 再次等待策略页面，适当延长一次以兼容加载/动画遮罩
                _ = self.wait_img(CWIMG.SELECT_INVEST_STRATEGY, timeout=20, interval=0.5)

            # 需求：在策略页面后，识别是否为 2-2。不是 2-2 则继续探索，是 2-2 则进入叽米判定逻辑。
            ret_box = self.wait_img(CWIMG.RETURN_PREPARATION_PAGE, timeout=10, interval=0.5)
            if ret_box is not None:
                self.click_box(ret_box, after_sleep=1.5)
                # 识别是否为 2-2 关卡
                two_two_box = self.wait_img(CWIMG.TWO_TWO, timeout=6, interval=0.5)
                # 点击返回投资策略界面
                self.click_img(CWIMG.RETURN_INVESTMENT_STRATEGY, after_sleep=1.0)
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
                        return True

                    # 未命中叽米：消耗刷新次数逐次检测，直到刷新用尽或命中为止
                    refresh_attempts = 0
                    max_safe_attempts = 6  # 安全上限，避免异常导致死循环
                    while refresh_attempts < max_safe_attempts:
                        try:
                            counts = self._collect_refresh_counts(max_items=3)
                            if counts:
                                logger.info(f"刷新次数记录: {counts}")
                                # 如果检测到全部为0，则认为刷新次数已用尽
                                if all(isinstance(x, int) and x == 0 for x in counts):
                                    logger.info("检测到刷新次数已用尽，执行返回备战并结算本轮")
                                    self._return_to_prep_and_abort()
                                    self.sleep(2.0)
                                    break
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
                    # 如果循环自然结束且未命中叽米，继续外层流程（已在用尽时结算并continue）
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
                        # 策略处理完成后，交还给 CW 继续战斗与推进
                        self.cw.strategy_external_control = False
                        self.cw.is_running = True
                        self.cw.run_game()
                    except Exception:
                        logger.debug("继续探索推进过程出现异常，忽略并进入下一轮等待")
                    # 回到等待下一个策略页/节点的循环
                    continue

            # 走到此处表示：未进入 2-2 分支或未触发返回备战逻辑。
            # 使用默认操作推进一次策略选择，继续等待下一次策略页。
            try:
                self.click_point(0.5, 0.68, after_sleep=0.5)
                self.click_point(0.5, 0.90, after_sleep=0.8)
                # 默认策略推进后，交还给 CW 继续战斗与推进
                self.cw.strategy_external_control = False
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
        index, box = self.wait_any_img([CWIMG.ENTER_STANDARD, CWIMG.CONCLUDE_AND_SETTLE], timeout=10, interval=0.5)
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
        # 返回最高名望（替代下拉选择难度）
        try:
            highest_rank = self.wait_img(CWIMG.RETURN_HIGHEST_RANK, timeout=5, interval=0.5)
            if highest_rank is not None:
                self.click_box(highest_rank, after_sleep=0.8)
            else:
                logger.debug("未识别到返回最高名望按钮，继续后续流程")
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
        return self._abort_and_return(in_game=False)

    def _return_to_prep_and_abort(self) -> bool:
        """兼容旧用法：对局中先返回备战再结算返回主页。"""
        return self._abort_and_return(in_game=True)

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
            logger.debug("未找到刷新次数锚点")
            return counts

        # 构造“同一行右侧”OCR区域（细长条）
        pad_x = 6
        pad_y = 2
        left = min(win.left + win.width - 10, anchor.left + anchor.width + pad_x)
        top = max(win.top, anchor.top - pad_y)
        # 宽度尽可能覆盖到右侧边界，高度与锚点行高相近
        width = max(40, min(600, win.left + win.width - left - 6))
        height = max(16, min(anchor.height + 2 * pad_y, win.top + win.height - top - 4))
        if width <= 0 or height <= 0:
            return counts

        region = Region(left, top, width, height)
        # 调试：输出用于识别的区域截图
        try:
            debug_dir = Path("log") / "currency_wars"
            debug_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            img_path = debug_dir / f"refresh_counts_region_{ts}.png"
            self.screenshot(region).save(img_path)
            logger.debug(f"刷新次数OCR区域: {region.tuple}, 截图: {img_path}")
        except Exception as e:
            logger.trace(f"保存刷新次数OCR区域截图失败: {e}")
        results = self.ocr_in_region(region, trace=False) or []
        if not results:
            return counts

        # 左到右排序后拼接成一行文本
        items = sorted(results, key=lambda r: r[0][0][0])
        line = " ".join([str(r[1]) for r in items])

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
    