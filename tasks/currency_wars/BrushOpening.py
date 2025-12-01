import re
import time
from pathlib import Path

from loguru import logger

from SRACore.util.notify import send_windows_notification
from SRACore.util.operator import Executable, Region
from tasks.currency_wars.img import CWIMG

from .CurrencyWars import CurrencyWars


class BrushOpening(Executable):
    def __init__(self, run_times):
        super().__init__()
        self.run_times = run_times
        self.force_battle = False
        self.cw = CurrencyWars(run_times)
        
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
            tries += 1
            logger.info(f"开始刷开局，第 {tries} 次尝试")

            page = self.cw.page_locate()
            if page == -1:
                logger.error("页面定位失败，无法开始游戏")
                return False

            # 进入流程：从开始页进入；准备阶段直接继续
            if page == 1:
                if not self._bo_enter_from_start_page():
                    logger.error("进入对局流程失败，重试下一轮")
                    continue
            elif page == 2:
                logger.info("已处于准备阶段，跳过进入流程")

            # 等待到首次“选择投资策略”界面
            idx, box = self.wait_any_img([CWIMG.SELECT_INVEST_STRATEGY, CWIMG.CLICK_BLANK], timeout=30, interval=0.5)
            if idx == -1:
                logger.warning("未在限定时间内到达选择投资策略界面，结束本轮并重试")
                self._safe_abort_and_return()
                continue

            # 保证在策略界面停留，避免误关
            if idx == 1 and box is not None:
                # 如果出现“点击空白处关闭”，先点击以继续弹出策略
                self.click_box(box, after_sleep=1)
                _ = self.wait_img(CWIMG.SELECT_INVEST_STRATEGY, timeout=8, interval=0.5)

            # 需求：在策略页面后，识别“返回备战页面”，点击后识别关卡是否为2-2，然后识别是否存在叽米图片
            ret_box = self.wait_img(CWIMG.RETURN_PREPARATION_PAGE, timeout=10, interval=0.5)
            if ret_box is not None:
                self.click_box(ret_box, after_sleep=1.5)
                # 识别是否为 2-2 关卡
                two_two_box = self.wait_img(CWIMG.TWO_TWO, timeout=6, interval=0.5)
                if two_two_box is not None:
                    # 识别是否存在叽米（使用图片匹配，而非 OCR）
                    if self._detect_jimi():
                        logger.success("2-2 关卡识别到叽米，停止脚本并通知用户")
                        try:
                            send_windows_notification("SRA", "刷开局命中叽米，脚本已停止")
                        except Exception:
                            logger.warning("通知模块调用失败")
                        # 标记运行状态为停止
                        self.is_running = False
                        if hasattr(self, 'cw'):
                            self.cw.is_running = False
                        return True

                    # 未命中叽米：记录刷新次数并尝试刷新一次后再检测
                    try:
                        counts = self._collect_refresh_counts(max_items=3)
                        if counts:
                            logger.info(f"刷新次数记录: {counts}")
                    except Exception as e:
                        logger.trace(f"采集刷新次数异常: {e}")

                    if self._click_refresh_button():
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
                        # 刷新后仍未识别到叽米：执行返回备战并结算的完整流程
                        logger.info("刷新后仍未识别到叽米，返回备战并结算本轮")
                        self._return_to_prep_and_abort()
                        continue

            # 未识别到叽米：中断探索并重新开始下一轮
            logger.info("未识别到叽米，返回备战并结算，准备下一轮")
            self._return_to_prep_and_abort()

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
            if box is None or not self.click_box(box, after_sleep=1):
                logger.error("点击标准进入失败")
                return False
            return self.cw._standard_entry_flow(box)
        elif index == 1:
            # 识别到放弃并结算（继续进度的替代入口），直接点击并执行结算返回
            if box is None or not self.click_box(box, after_sleep=1):
                logger.error("点击放弃并结算入口失败")
                return False
            logger.info("检测到放弃并结算入口，执行结算返回主界面")
            return self._safe_abort_and_return()

        logger.error("既未识别标准进入，也未识别继续进度入口")
        return False
    
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