from loguru import logger

from SRACore.util.operator import Executable
from tasks.currency_wars.img import CWIMG

from .CurrencyWars import CurrencyWars


class BrushOpening(Executable):
    def __init__(self, run_times):
        super().__init__()
        self.run_times = run_times
        self.force_battle = False
        # 持久化 CurrencyWars 实例以复用其辅助流程
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

            # 使用持久化的 CurrencyWars 实例调用页面定位
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

            # 在策略界面 OCR 全屏，查找“叽米”字样
            if self._detect_jimi():
                logger.success("识别到叽米，停止脚本并通知用户")
                try:
                    # 若有统一的通知方式，可改为调用通知模块
                    # from SRACore.util.notify import notify
                    # notify("刷开局命中叽米，已停止脚本")
                    pass
                except Exception:
                    pass
                return True

            # 未识别到叽米：中断探索并重新开始下一轮
            logger.info("未识别到叽米，本轮结束并结算，准备下一轮")
            self._safe_abort_and_return()

    def _detect_jimi(self) -> bool:
        """在当前界面 OCR 文本，检测是否包含“叽米”。"""
        try:
            # 尽可能覆盖更多区域以提升命中概率
            results = []
            # 顶部、中央、底部三段 OCR（坐标按相对比例）
            results += (self.ocr(from_x=0.05, from_y=0.10, to_x=0.95, to_y=0.28) or [])
            results += (self.ocr(from_x=0.05, from_y=0.28, to_x=0.95, to_y=0.70) or [])
            results += (self.ocr(from_x=0.05, from_y=0.70, to_x=0.95, to_y=0.95) or [])
            text = ''.join([r[1] for r in results if isinstance(r, (list, tuple)) and len(r) >= 2])
            if '叽米' in text:
                return True
        except Exception as e:
            logger.warning(f"检测叽米时发生异常：{e}")
        return False

    def _bo_enter_from_start_page(self) -> bool:
        """处理从货币战争开始页面进入对局的完整流程。(刷开局专用)"""
        start_box = self.wait_img(CWIMG.CURRENCY_WARS_START, timeout=30, interval=0.5)
        if start_box is None or not self.click_box(start_box):
            logger.error("未识别到开始按钮")
            return False
        self.click_point(0.5, 0.5, after_sleep=2)

        # 标准进入 or 继续进度（若是继续进度则中断并返回）
        index, box = self.wait_any_img([CWIMG.ENTER_STANDARD, CWIMG.CONTINUE_PROGRESS], timeout=10, interval=0.5)

        if index == 0:
            return self.cw._standard_entry_flow(box)
        elif index == 1:
            logger.info("检测到继续进度，执行结算并返回主界面后再走正常流程")
            if not self._conclude_and_settle_from_continue(box):
                return False
            # 重新点击开始，走标准进入
            start_box = self.wait_img(CWIMG.CURRENCY_WARS_START, timeout=10, interval=0.5)
            if start_box is None or not self.click_box(start_box):
                return False
            self.click_point(0.5, 0.5, after_sleep=1.5)
            enter_box = self.wait_img(CWIMG.ENTER_STANDARD, timeout=10, interval=0.5)
            if enter_box is None:
                return False
            return self.cw._standard_entry_flow(enter_box)

        logger.error("既未识别标准进入，也未识别继续进度入口")
        return False
    
    def _conclude_and_settle_from_continue(self, continue_box) -> bool:
        """从“继续进度”入口中断并结算返回主界面。"""
        if not self.click_box(continue_box, after_sleep=1):
            return False
        # 此处通常会出现“点击空白处”提示，点击以进入结算界面
        click_blank = self.wait_img(CWIMG.CLICK_BLANK, timeout=5, interval=0.5)
        if click_blank is not None:
            self.click_box(click_blank, after_sleep=1)
        return self._safe_abort_and_return()

    def _safe_abort_and_return(self) -> bool:
        """统一的放弃并结算返回到货币战争主界面流程。"""
        try:
            withdraw_and_settle = self.wait_img(CWIMG.WITHDRAW_AND_SETTLE, timeout=8, interval=0.5)
            if withdraw_and_settle is None:
                logger.error("未识别到放弃并结算入口")
                return False
            self.click_box(withdraw_and_settle, after_sleep=3)

            # 结算与返回流程
            next_step = self.wait_img(CWIMG.NEXT_STEP, timeout=8, interval=0.5)
            if next_step is None:
                logger.error("点击放弃并结算后，未识别到下一步")
                return False
            self.click_box(next_step, after_sleep=2)

            next_page = self.wait_img(CWIMG.NEXT_PAGE, timeout=8, interval=0.5)
            if next_page is None:
                logger.error("点击下一步后，未识别到下一页")
                return False
            self.click_box(next_page, after_sleep=2)

            back_currency_wars = self.wait_img(CWIMG.BACK_CURRENCY_WARS, timeout=8, interval=0.5)
            if back_currency_wars is None:
                logger.error("点击下一页后，未识别到返回货币战争")
                return False
            self.click_box(back_currency_wars, after_sleep=2)
            logger.info("已放弃并结算，返回货币战争主界面")
            return True
        except Exception:
            logger.error("放弃并结算流程异常，无法继续")
            return False