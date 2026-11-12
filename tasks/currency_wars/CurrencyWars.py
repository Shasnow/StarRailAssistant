import enum
import json
import re
import time
from collections.abc import Callable
from typing import Any

from loguru import logger

from SRACore.operators.model import Box
from SRACore.task import Executable
from SRACore.util.errors import ErrorCode, SRAError
from tasks.currency_wars.characters import Character, Characters, Positioning
from tasks.img import CWIMG, IMG, DUIMG


class Difficulty(enum.IntEnum):
    """难度模式枚举"""
    LOWEST = 0
    HIGHEST = 1
    CURRENT = 2


class CurrencyWarsPage(enum.IntEnum):
    """货币战争页面枚举"""
    START = 1
    PREPARATION = 2
    UNKNOWN = -1


class StageName(enum.StrEnum):
    """关卡阶段名称枚举"""
    REPLENISH_STAGE = '补给阶段'
    ENCOUNTER_NODE = '遭遇节点'
    FOLD = '无'
    SELECT_INVEST_STRATEGY = '选择投资策略'
    CLICK_BLANK = '点击空白处关闭'
    GAME_OVER = '游戏结束'
    MAIN_MENU = '主界面'
    SELECT_EQUIPMENT = '选择装备'



def _merge_ocr_lines(fragments: list[tuple[list[tuple[int, int]], str, float]]) -> list[str]:
    """按文本框坐标把 OCR 片段拼成文本行，去掉检测框重叠处被重复识别的字。

    RapidOCR 有时会把同一行文本切成多个互相重叠的文本框（例如“知更鸟·晴歌”被切成
    “知更鸟”和“鸟·晴歌”），直接按顺序拼接会多出重叠的字。这里按片段的横向重叠范围
    估算可重复字数上限，再比对文本实际重复的前缀（检测框边界不精确，且“·”等窄字符
    会拉偏平均字宽，所以只按几何估算会误删有效字符）；纵向不重叠的片段视为新的一行。
    """
    ordered = sorted(fragments, key=lambda item: (min(p[1] for p in item[0]), min(p[0] for p in item[0])))
    lines: list[str] = []
    line_right = line_top = line_bottom = 0
    for points, fragment, _ in ordered:
        left = min(point[0] for point in points)
        right = max(point[0] for point in points)
        top = min(point[1] for point in points)
        bottom = max(point[1] for point in points)
        same_line = bool(lines) and top < line_bottom and bottom > line_top
        if same_line:
            text = lines[-1]
            if left < line_right:
                char_width = (right - left) / len(fragment) if fragment else 0
                if char_width > 0:
                    # 几何重叠字数只作为上限（再多容一个字符），实际去掉多少由重复文本决定
                    limit = min(int(round((line_right - left) / char_width)) + 1, len(fragment), len(text))
                    for k in range(limit, 0, -1):
                        if fragment[:k] == text[-k:]:
                            fragment = fragment[k:]
                            break
            lines[-1] = text + fragment
            line_right = max(line_right, right)
            line_top = min(line_top, top)
            line_bottom = max(line_bottom, bottom)
        else:
            lines.append(fragment)
            line_right, line_top, line_bottom = right, top, bottom
    return lines


def _merge_ocr_text(fragments: list[tuple[list[tuple[int, int]], str, float]]) -> str:
    """按文本框坐标拼接 OCR 片段（多行直接相连），去掉重叠处被重复识别的字。"""
    return ''.join(_merge_ocr_lines(fragments))


class CurrencyWars(Executable):
    def __init__(self, operator, runtimes, isPointRewardsEnabled: bool = False):
        super().__init__(operator)
        self.runtimes = runtimes
        self.isPointRewardsEnabled = isPointRewardsEnabled
        self.special_events: dict[str, tuple[str, Callable[[], bool]]] = {
            "领航员": ("选择伙伴", self.handle_choose_partner),
            "盛会之星": ("盛会之星", self.handle_the_planet_of_festivities),
            "命运圣杯": ("祈愿试炼", self.handle_wish_trial),
            "头号玩家": ("我来当策划", self.handle_silver_wolf_lv999),
            "开拓银轨": ("开拓商店", self.handle_trailblaze_store),
            "奇兽花园": ("奇兽花园", self.handle_beast_garden),
            "梦境交织": ("梦境交织", self.handle_dream_interference)
        }
        self.is_continue = False  # 是否是继续挑战
        self.is_game_over = False
        self.skip_current_round = False  # 前台无角色时跳过本轮剩余流程，直接刷新角色并开始新一轮
        self.difficulty: int = Difficulty.LOWEST
        self.on_field_character: list[Character | None] = [None, None, None, None]  # 前台角色列表
        self.on_field_area: list[tuple[float, float]] = [
            (0.386, 0.365),
            (0.464, 0.365),
            (0.536, 0.365),
            (0.611, 0.365)
        ]
        self.off_field_character: list[Character | None] = [None, None, None, None, None, None]  # 后台角色列表
        self.off_field_area: list[tuple[float, float]] = [
            (0.3056, 0.620),
            (0.3806, 0.620),
            (0.4525, 0.620),
            (0.5264, 0.620),
            (0.6004, 0.620),
            (0.6738, 0.620)
        ]
        self.in_hand_character: list[Character | None] = [None, None, None, None, None, None, None, None,
                                                          None]  # 备战席角色列表
        self.in_hand_area: list[tuple[float, float]] = [
            (0.229, 0.844),
            (0.297, 0.844),
            (0.358, 0.844),
            (0.426, 0.844),
            (0.488, 0.844),
            (0.556, 0.844),
            (0.618, 0.844),
            (0.684, 0.844),
            (0.749, 0.844)
        ]  # 备战席区域
        self.store_area: list[tuple[float, float]] = [
            (0.25, 0.18),
            (0.40, 0.18),
            (0.55, 0.18),
            (0.68, 0.18),
            (0.80, 0.18)
        ]
        self.max_team_size = 3  # 最大队伍人数
        self.is_running = False
        self.min_coins = 40  # 最小金币数
        self.min_level = 7  # 商店等级
        self.mid_level = 7  # 商店等级
        self.strategy_characters: dict[str, int] = dict()  # 在攻略中的角色及其预期星级
        self.strategy_code = ""  # 当前使用的攻略代码
        self.strategy_special_events: dict[str, str] = dict()  # 攻略中的特殊事件处理
        self.is_overclock = False  # 超频博弈
        self.is_complex_invest_strategy_selection_enabled = False  # 是否启用复杂投资策略选择逻辑

    def run(self):
        self.is_running = True
        if self.runtimes == 0:
            logger.warning("货币战争运行次数为 0 ，本次将跳过运行。")
            return True
        if self.isPointRewardsEnabled:
            page = self.page_locate()
            if page == CurrencyWarsPage.START and self.check_point_rewards():
                logger.info("旷宇纷争积分奖励已满，跳过货币战争任务")
                return True
        for i in range(self.runtimes):
            if not self.is_running:
                break
            logger.info(f"第{i + 1}次进入货币战争，剩余{self.runtimes - i - 1}次")
            try:
                if self.start_game():
                    self.game_loop()
            except Exception as e:
                logger.error(e)
                return False
        self.handle_ending()
        return True

    def handle_ending(self):
        """ 处理游戏结束逻辑，默认退出货币战争页面 """
        self.operator.wait_img(CWIMG.START_CURRENCY_WARS, timeout=30)
        self.operator.press_key("esc")

    def check_point_rewards(self) -> bool:
        """检查旷宇纷争积分奖励是否已满（需处于货币战争开始页面）"""
        result = self.operator.ocr(from_x=0.1, from_y=0.89, to_x=0.21, to_y=0.96)
        # 格式 x/18000，OCR可能将结果切断成多个部分或产生噪声，用正则匹配开头和结尾都是18000
        if result:
            current = "".join(item[1] for item in result)
            logger.info(f"当前积分奖励: {current}")
            if re.match(r'^18000.*18000$', current):
                return True
        return False

    def reset_character(self):
        """ 重置所有角色信息 """
        for i, c in enumerate(self.on_field_character):
            if c is not None:
                c.is_placed = False  # 重置放置状态
                c.stars = 1  # 重置星级
            self.on_field_character[i] = None  # 重置角色信息
        for i, c in enumerate(self.off_field_character):
            if c is not None:
                c.is_placed = False
                c.stars = 1
            self.off_field_character[i] = None
        for i, c in enumerate(self.in_hand_character):
            if c is not None:
                c.is_placed = False
                c.stars = 1
            self.in_hand_character[i] = None

    def set_difficulty(self, mode: int):
        """设置难度模式：0=最低难度，1=最高难度，2=当前难度（不切换）"""
        self.difficulty = mode

    def set_overclock(self, overclock: bool):
        self.is_overclock = overclock

    def page_locate(self, depth = 0) -> CurrencyWarsPage:
        """
        定位到货币战争页面

        :return: CurrencyWarsPage 枚举值，表示当前所在页面；如果未识别到任何目标页面，则返回 CurrencyWarsPage.UNKNOWN
        """
        if depth>5:
            raise RuntimeError("页面定位递归过深，可能存在无限循环")
        page, _ = self.operator.wait_any_img([IMG.ENTER,
                                              CWIMG.START_CURRENCY_WARS,
                                              CWIMG.PREPARATION_STAGE,
                                              DUIMG.BONUS_POINTS], interval=0.5)
        if page == 0:
            if self.operator.locate(CWIMG.CURRENCY_WARS): # 货币战争门口
                self.operator.press_key("f")
            else:
                logger.info("[页面定位] 正在定位到货币战争开始页面")
                guide_hotkey = self.settings.General.hotkeyF4
                self.operator.press_key(str(guide_hotkey).lower())
                if not self.operator.wait_img(IMG.F4, timeout=20):
                    logger.error(SRAError(ErrorCode.WAIT_TIMEOUT, "等待指南界面超时"))
                    self.operator.press_key("esc")
                box = self.operator.wait_img(IMG.COSMIC_STRIFE, timeout=10)
                self.operator.click_box(box, after_sleep=1)  # 旷宇纷争
                self.operator.click_point(0.242, 0.30, after_sleep=0.8)  # 货币战争
                self.operator.click_point(0.7786, 0.8194, after_sleep=1)  # 前往参与
            return self.page_locate(depth + 1)
        elif page == 1:
            logger.info("[页面定位] 已定位到货币战争开始页面")
            return CurrencyWarsPage.START
        elif page == 2:
            logger.info("[页面定位] 已定位到货币战争准备阶段")
            return CurrencyWarsPage.PREPARATION
        elif page == 3:
            self.operator.press_key("esc")
            return CurrencyWarsPage.START
        else:
            logger.error("[页面定位] 检测超时，未识别到任何目标页面")
            return CurrencyWarsPage.UNKNOWN

    def start_game(self):
        """开始一局货币战争。
        拆分原复杂流程为多个独立步骤，提升可读性与可维护性。
        返回 True 表示进入对局并完成初始策略与备战席识别
            False 表示流程中断或失败。
        """
        page = self.page_locate()
        if page == CurrencyWarsPage.UNKNOWN:
            logger.error("[启动流程] 页面定位失败，无法开始游戏")
            return False
        self.is_running = True  # 标记任务运行中
        if not self._handle_page_enter(page):
            logger.error("[启动流程] 进入对局流程失败")
            self.is_running = False
            return False

        if not self.handle_game_entered():
            return False
        # 对局初始化
        init_success = self._initialize_game()
        if not init_success:
            logger.error("[启动流程] 对局初始化失败")
            self.is_running = False
            return False
        if not self.handle_game_initialized():
            return False
        logger.info("[启动流程] 对局启动成功")
        self.is_game_over = False
        return True

    def _handle_page_enter(self, page: CurrencyWarsPage) -> bool:
        """
        根据页面类型处理进入逻辑
        :param page: 页面枚举值
        :return: True-进入成功，False-进入失败
        """
        if page == CurrencyWarsPage.START:
            # 开始页面 → 执行进入流程
            return self._enter_from_start_page()
        elif page == CurrencyWarsPage.PREPARATION:
            # 准备阶段 → 跳过进入流程
            self.is_continue = True
            logger.info("[进入流程] 已处于准备阶段，跳过进入流程")
            return True
        else:
            return False

    # ==================== 进入流程辅助方法 ====================
    def _enter_from_start_page(self) -> bool:
        """
        从开始页面进入对局
        :return: True-进入成功，False-进入失败
        """
        # 等待开始按钮
        index, box = self.operator.wait_any_img(
            [CWIMG.START_CURRENCY_WARS, CWIMG.INSTRUCTIONS],
            timeout=30,
            interval=0.5
        )
        if index == -1:
            logger.error("[进入流程] 未识别到开始按钮")
            return False
        if index == 1:
            self.operator.press_key("esc")  # 赛季扩充说明
            box = self.operator.wait_img(CWIMG.START_CURRENCY_WARS, timeout=30)  # 重新获取开始游戏按钮
        # 重试点击开始按钮直到LOGO消失
        self.operator.do_while(
            lambda: self.operator.click_box(box),  # NOQA  # pyright: ignore[reportArgumentType]
            lambda: self.operator.locate(CWIMG.LOGO) is None,
            interval=2,
            max_iterations=10
        )
        self.operator.sleep(1)  # 等待界面响应
        if self.is_overclock:
            self.operator.click_point(0.15625, 0.4167, after_sleep=1, tag="点击超频博弈")
        else:
            self.operator.click_point(0.15625, 0.2315, after_sleep=1, tag="点击标准博弈")

        # 选择进入方式（标准进入/继续进度）
        enter_type, enter_box = self.operator.wait_any_img(
            [CWIMG.ENTER_GAME, CWIMG.CONTINUE_PROGRESS],
            timeout=10
        )
        if enter_box is None:
            logger.error("[进入流程] 未识别到任何进入方式（标准/继续）")
            return False

        # 执行对应进入逻辑
        if enter_type == 0:  # 标准进入
            return self._enter_new_game(enter_box)
        elif enter_type == 1:  # 继续进度
            return self._enter_continue_game(enter_box)

        return False

    def _enter_new_game(self, enter_button_box) -> bool:
        """
        新游戏进入流程
        :param enter_button_box: 进入按钮坐标框
        :return: True-成功，False-失败
        """
        # 1. 点击进入按钮
        if not self.operator.click_box(enter_button_box, after_sleep=1.5):
            logger.error("[新游戏] 点击进入按钮失败")
            return False

        # 2. 难度选择
        self._select_difficulty()

        # 3. 点击开始对局
        if not self.operator.click_img(CWIMG.START_GAME, after_sleep=1):
            logger.error("[新游戏] 点击开始对局按钮失败")
            return False

        # 4. 处理Boss信息
        if not self._handle_boss_info_flow():
            return False

        # 5. 处理投资环境
        self._handle_invest_environment_flow()
        self.operator.sleep(8)  # 等待开局补给
        return True

    def _select_difficulty(self) -> None:
        """难度选择逻辑（抽离后更易维护）"""
        if self.difficulty == Difficulty.HIGHEST:
            # 最高难度：点击返回最高职级
            logger.info("[难度选择] 选择最高难度")
            self.operator.click_img(CWIMG.RETURN_HIGHEST_RANK, after_sleep=0.8)
        elif self.difficulty == Difficulty.LOWEST:
            # 最低难度：循环点击下拉箭头
            logger.info("[难度选择] 选择最低难度")
            while self.operator.click_img(CWIMG.DOWN_ARROW, after_sleep=0.5):
                pass
        elif self.difficulty == Difficulty.CURRENT:
            # 当前难度：不操作
            logger.info("[难度选择] 保持当前难度")
        else:
            logger.warning(f"[难度选择] 未知难度模式：{self.difficulty}，使用当前难度")

    def _handle_boss_info_flow(self) -> bool:
        """处理Boss信息流程（抽离独立方法）"""
        # 等待下一步提示
        next_step_box = self.operator.wait_img(
            CWIMG.NEXT_STEP,
            timeout=10
        )
        if not next_step_box:
            logger.error("[Boss信息] 未识别到下一步提示")
            return False

        # 处理Boss信息 + 点击下一步
        self.operator.sleep(0.5)
        self.handle_boss_info()
        if not self.operator.do_while(
            lambda: self.operator.click_box(next_step_box, after_sleep=1),
            lambda: self.operator.locate(CWIMG.NEXT_STEP) is not None,
            interval=1,
            max_iterations=10
        ):
            logger.error("[Boss信息] 点击下一步按钮失败")
            return False
        # 点击空白处
        self.operator.click_point(0.6, 0.5, after_sleep=0.5, tag="点击空白处")
        return True

    def _handle_invest_environment_flow(self) -> bool:
        # 检查投资环境界面
        if not self.operator.wait_img(CWIMG.INVEST_ENVIRONMENT):
            logger.error("[投资环境] 未识别到投资环境界面")
            return False
        self.operator.sleep(1)  # 等待界面稳定
        self.handle_invest_environment()
        # 有些情况下点击投资环境界面后会再次弹出投资环境界面，需要再次处理
        if self.operator.locate(CWIMG.INVEST_ENVIRONMENT):
            self.handle_invest_environment()
        return True

    # ==================== 继续进度进入逻辑（重构后） ====================
    def _enter_continue_game(self, continue_button_box) -> bool:
        """
        继续进度进入流程（重构后，异常处理更规范）
        :param continue_button_box: 继续按钮坐标框
        :return: True-成功，False-失败
        """
        self.is_continue = True
        # 点击继续按钮
        if not self.operator.click_box(continue_button_box, after_sleep=1):
            logger.error("[继续进度] 点击继续按钮失败")
            return False

        try:
            # 等待空白提示并点击
            self.operator.sleep(2)
            click_blank_box = self.operator.wait_img(
                CWIMG.CLICK_BLANK,
                timeout=10
            )
            if not click_blank_box:
                logger.error("[继续进度] 未识别到点击空白提示")
                return False
            self.operator.click_box(click_blank_box, after_sleep=2)
            logger.info("[继续进度] 进入对局成功")
            return True
        except Exception as e:
            logger.error(f"[继续进度] 流程异常：{str(e)}", exc_info=True)
            return False

    # ==================== 对局初始化（重构后） ====================
    def _initialize_game(self) -> bool:
        """
        对局初始化（重构后，区分继续进度和新游戏）
        :return: True-初始化成功，False-初始化失败
        """
        self.operator.sleep(1)
        if self.is_continue:
            # 继续进度：获取前台角色信息
            logger.info("[初始化] 继续进度")
            self.refresh_character()
        # 新游戏：没有初始化逻辑
        return True

    def handle_boss_info(self) -> None:
        """处理进入对局后可能出现的Boss信息提示框。

        如果需要额外的操作（如记录Boss信息、调整策略等），可以在此方法中实现。"""
        ...

    def handle_invest_environment(self) -> None:
        """处理投资环境界面

        标准模式下，简单地选择中间的投资环境或选择尚未收集的投资环境，点击确定即可。
        """
        if not self.operator.click_img(CWIMG.COLLECTION):
            self.operator.click_point(0.5, 0.5, tag="选择中间的投资环境")
        self.operator.click_img(IMG.ENSURE2, after_sleep=1)
        if self.operator.locate(CWIMG.INVEST_ENVIRONMENT):
            self.operator.click_point(0.5, 0.5, after_sleep=1)
            self.operator.click_img(IMG.ENSURE2, after_sleep=1)

    def handle_game_entered(self) -> bool:  # NOQA
        """进入游戏的后续处理逻辑（如有）。默认实现为无操作，子类可重写此方法以添加额外逻辑。

        调用时机：在完成进入流程并进入对局后、初始化角色信息前调用
        Returns:
            True-继续执行后续初始化和游戏循环；False-中止进入流程
        """
        if self.is_continue or not self.strategy_code:
            return True
        self.operator.click_img(CWIMG.STRATEGY, after_sleep=1)
        self.operator.click_img(CWIMG.HOT_STRATEGIES, after_sleep=0.5)
        self.operator.move_to(0.5, 0.5)
        self.operator.sleep(0.5)
        self.operator.click_img(CWIMG.ENTER_STRATEGY_CODE, after_sleep=1)
        self.operator.click_point(0.5, 0.5, after_sleep=1, tag="攻略码输入框")
        self.operator.copy(self.strategy_code)
        self.operator.paste()
        self.operator.sleep(1)
        self.operator.click_img(IMG.ENSURE2, after_sleep=1)
        box = self.operator.wait_img(CWIMG.APPLY_STRATEGY)
        if box:
            self.operator.click_box(box, after_sleep=1)
        else:
            logger.warning("[应用策略] 未识别到应用策略按钮")
        
        # 恢复到主界面
        self.operator.do_while(
            lambda: self.operator.press_key('esc'),
            lambda: self.operator.locate(CWIMG.QUIT) is None,
            interval=0.5,            max_iterations=5)
        return True

    def handle_game_initialized(self) -> bool:  # NOQA
        """对局初始化完成后的处理逻辑（如有）。默认实现为无操作，子类可重写此方法以添加额外逻辑。

        调用时机：在完成角色放置和备战席识别后、正式进入游戏循环前调用
        Returns:
            True-继续执行游戏循环；False-中止进入流程
        """
        return True

    def abort_and_return(self) -> bool:
        """中止当前对局并返回开始页面"""
        logger.info("中止当前对局并返回开始页面")
        index, box = self.operator.wait_any_img([CWIMG.QUIT, CWIMG.WITHDRAW_AND_SETTLE])
        if index<0:
            return False
        if index == 0:
            self.operator.click_box(box, after_sleep=1)
            self.operator.click_img(CWIMG.WITHDRAW_AND_SETTLE)
        elif index == 1:
            self.operator.click_box(box)
        b = self.operator.wait_img(CWIMG.NEXT_STEP)
        if b is None:
            return False
        self.handle_game_over(None)
        return True

    def game_loop(self):
        run_times = 0
        while self.is_running:
            self.harvest_crystals()
            self.get_in_hand_area(True)  # 更新备战席信息
            self.handle_characters_updated()
            self.update_max_team_size()
            self.place_character()
            self.sell_character()
            if not self.battle():
                if self.skip_current_round:  # 前台无角色，跳过本轮剩余流程
                    self.skip_current_round = False
                    self.refresh_character()
                    self.sort_all_areas_by_priority()  # 优先级排序
                    continue
                break
            self.handle_special_event()
            if not self.stage_transition():
                break
            if self.is_game_over:  # 任务已被标记为停止, 需要退出循环
                break
            self.shopping()

            run_times += 1
            if run_times % 2 == 0:  # 每2轮更新一次前台角色，顺便穿戴装备
                self.refresh_character()
                self.sort_all_areas_by_priority()  # 优先级排序
        # 游戏循环结束，重置角色状态
        self.reset_character()
        return True

    def refresh_character(self):
        """ 刷新角色信息，确保备战席中未放置的角色状态正确。 """
        self.get_on_field_area(True)
        self.operator.sleep(0.3)
        boxes = self.operator.rectangle_detect(120, 150, 130, 150,
                                               from_x=0.1, from_y=0.52, to_x=0.86, to_y=0.7,
                                               trace=True)
        if boxes:
            # 去重：中心距离小于 100 的矩形视为同一个位置
            unique_boxes: list[Box] = []
            for b in sorted(boxes, key=lambda b: b.left):
                if all(b.distance(u) >= 100 for u in unique_boxes):
                    unique_boxes.append(b)
            self.off_field_area = [
                (b.center[0] / self.operator.window_context.width, b.center[1] / self.operator.window_context.height)
                for b in unique_boxes
            ]
            # 同步调整角色列表长度
            if len(self.off_field_area) > len(self.off_field_character):
                self.off_field_character.extend(
                    [None] * (len(self.off_field_area) - len(self.off_field_character))
                )
            logger.info(f"当前后台共有 {len(self.off_field_area)} 个位置")
        self.get_off_field_area(True)
        self.operator.sleep(0.3)
        field_characters = self.on_field_character + self.off_field_character
        for c in self.in_hand_character:
            if c is not None and c not in field_characters:
                c.is_placed = False

    def get_coins(self):
        # 实现获取金币逻辑
        logger.info("获取当前金币数量")
        coins = self.operator.ocr(from_x=0.84, from_y=0.81, to_x=0.89, to_y=0.89)
        if coins:
            try:
                return int(coins[0][1])
            except (IndexError, ValueError):
                return 0
        else:
            return 0

    def _get_character_in_area(self,
                               areas,
                               target_character_list,
                               force=False,
                               equip=False,
                               count_stars=False,
                               use_backup_ocr=False):
        """
        通用方法：获取指定区域的角色信息
        :param areas: 区域坐标列表（如 off_field_area）
        :param target_character_list: 目标角色列表（如 off_field_character，将被更新）
        :param force: 强制更新角色信息，默认False（即已有角色则跳过）
        :param equip: 是否顺便穿戴装备
        :param count_stars: 是否获取角色星级
        :return: 更新后的角色列表
        """

        def get_stars(merge: int) -> int:
            # 获取角色星级 merge: 当 box 之间的距离小于此值时，将它们视为同一个box
            boxes = self.operator.locate_all(CWIMG.STAR, from_x=0.83, from_y=0.15, to_x=0.87, to_y=0.17)
            if not boxes:
                return 0
            valid_boxes: list[Box] = []
            for b in boxes:
                for vb in valid_boxes:
                    if vb.distance(b) < merge:
                        break
                else:
                    valid_boxes.append(b)
            return len(valid_boxes)

        # 角色名称OCR区域
        ocr_from_x, ocr_from_y, ocr_to_x, ocr_to_y = (0.775, 0.185, 0.880, 0.258)

        for index, area in enumerate(areas):
            try:
                # 点击区域（带延迟，确保界面响应）
                if target_character_list[index] is not None and not force:
                    continue  # 已有角色则跳过
                self.operator.mouse_down(*area, trace=False)
                self.operator.sleep(0.2)
                self.operator.mouse_up(*area, trace=False)

                # OCR识别角色名称
                character_names = self.operator.ocr(
                    from_x=ocr_from_x,
                    from_y=ocr_from_y,
                    to_x=ocr_to_x,
                    to_y=ocr_to_y
                )

                if not character_names and use_backup_ocr:
                    # 狸猫/佩佩等可能需要在另一个位置识别
                    ocr_from_x2, ocr_from_y2, ocr_to_x2, ocr_to_y2 = (0.775, 0.445, 0.880, 0.486)
                    # 尝试在备用区域识别角色名称
                    character_names = self.operator.ocr(
                        from_x=ocr_from_x2,
                        from_y=ocr_from_y2,
                        to_x=ocr_to_x2,
                        to_y=ocr_to_y2
                    )

                # 更新角色列表
                # 空位背景常被误识别为“1”等数字/符号，只保留包含文字的片段
                fragments = [item for item in character_names or () if re.search(r"[^\W\d_]", item[1])]
                if fragments:
                    # OCR 可能把名字切成多个重叠的文本框，也可能把下方标签一起识别进来：
                    # 逐行累加，优先采用能匹配角色表的组合（如“银狼LV.999”而不是“银狼LV.999前台”）
                    lines = _merge_ocr_lines(fragments)
                    name, char = '', None
                    for i in range(len(lines)):
                        candidate = ''.join(lines[:i + 1])
                        char = Characters.get_character(candidate)
                        if char is not None:
                            name = candidate
                            break
                    if char is None:
                        name = ''.join(lines)
                        logger.warning(f"OCR识别到角色名称：{name}，但未在角色列表中找到匹配项")
                        target_character_list[index] = Characters.new_character(name)  # 新增临时角色
                        continue
                    if count_stars and not char.is_npc:
                        char.stars = get_stars(merge=3)
                    target_character_list[index] = char
                    if equip and not char.is_npc:
                        if char.name in self.strategy_characters.keys():
                            self.operator.click_point(0.77, 0.75, after_sleep=0.5, trace=False)  # 点击装备推荐按钮
                            _, box = self.operator.locate_any([CWIMG.EQUIP, CWIMG.SYNTHESIS], confidence=0.8)
                            if box:
                                self.operator.click_box(box, after_sleep=0.5)
                    self.operator.click_point(0.3, 0.5, trace=True)  # 点击空白处关闭信息框
                else:
                    target_character_list[index] = None  # 未识别到角色

            except Exception as e:
                # 捕获点击或OCR异常（如坐标错误、识别失败）
                logger.error(f"获取区域[{index}]角色失败：{str(e)}")

        return target_character_list

    def get_off_field_area(self, force=False):
        """获取后台角色信息"""
        self._get_character_in_area(areas=self.off_field_area, target_character_list=self.off_field_character,
                                    equip=True,
                                    force=force,
                                    count_stars=True,
                                    use_backup_ocr=True)
        for char in self.off_field_character:
            if char is not None:
                char.is_placed = True
        logger.info(f"当前后台角色：{self.off_field_character}")

    def get_on_field_area(self, force=False):
        """获取前台角色信息"""
        self._get_character_in_area(areas=self.on_field_area, target_character_list=self.on_field_character,
                                    equip=True,
                                    force=force,
                                    count_stars=True)
        for char in self.on_field_character:
            if char is not None:
                char.is_placed = True
        logger.info(f"当前前台角色：{self.on_field_character}")

    def get_in_hand_area(self, force=False):
        """获取备战席角色信息"""
        # 打开武器箱或专家邀请函
        target = self.operator.locate(CWIMG.OPEN)
        while target:
            self.operator.mouse_down(target.center[0], target.center[1])
            self.operator.mouse_up()
            self.operator.sleep(1)
            self.operator.click_point(0.8, 0.25, after_sleep=1)
            target = self.operator.locate(CWIMG.OPEN)
        self._get_character_in_area(areas=self.in_hand_area, target_character_list=self.in_hand_character, force=force)
        logger.info(f"当前备战席角色：{self.in_hand_character}")

    def harvest_crystals(self):
        # 实现水晶收集逻辑
        logger.info("收集水晶")
        if self.operator.type == "Local":
            self.operator.drag_to(0.68, 0.20, 0.82, 0.18, trace=False)
            self.operator.sleep(0.3)
            self.operator.drag_to(0.68, 0.25, 0.82, 0.25, trace=False)
            self.operator.sleep(0.3)
            self.operator.drag_to(0.68, 0.30, 0.83, 0.30, trace=False)
            self.operator.sleep(0.3)
            self.operator.drag_to(0.68, 0.35, 0.84, 0.35, trace=False)
            self.operator.sleep(0.3)
            self.operator.drag_to(0.68, 0.40, 0.83, 0.40, trace=False)
            self.operator.sleep(0.3)
        else:
            # 浏览器不支持滑动，拖动可能无法正确触发收集
            for x in range(66, 85, 2):
                for y in range(20, 41, 5):
                    self.operator.click_point(x / 100, y / 100, trace=False)

        self.detect_silver_wolf_lv999()  # 也许开出银狼了

    def sell_character(self):
        """
        实现角色出售逻辑，确保备战席不超过8个角色
        :return: bool - 出售操作是否成功
        """
        max_attempts = 5
        attempt = 0

        while attempt < max_attempts:
            if self.in_hand_character_count < 8:
                logger.info("备战席未满，跳过出售角色")
                return True
            logger.info("备战席已满，尝试出售角色")
            self._handle_sell_character()
            self.get_in_hand_area()  # 检测空位，确保没有新插入的角色
            attempt += 1

        # 超过最大尝试次数仍未成功出售时的逻辑
        logger.warning(f"已尝试{max_attempts}次出售角色，备战席仍为满状态，将强制执行出售")
        self._handle_sell_character(force=True)
        self.get_in_hand_area()  # 最后更新备战席状态

        if self.in_hand_character_count < 8:
            logger.info("强制出售角色成功")
            return True
        else:
            logger.error("强制出售角色失败，备战席仍为满状态")
            return False

    def _handle_sell_character(self, force=False):
        """
        角色出售逻辑
        :param force: bool - 是否强制出售所有角色（包括已放置的角色）
        """
        # 创建需要出售的角色索引列表
        characters_to_sell: list[tuple[int, Character]] = []
        for i, character in enumerate(self.in_hand_character):
            if character is None:
                continue
            if force:
                # 强制出售
                logger.info(f"强制出售角色：{character.name}")
                characters_to_sell.append((i, character))
            elif character.name not in self.strategy_characters.keys():
                # 不在攻略中的角色
                logger.info(f"出售非攻略角色：{character.name}")
                characters_to_sell.append((i, character))
            elif character.stars >= self.strategy_characters[character.name] and character.is_placed:
                # 已满足攻略要求的角色
                logger.info(f"出售满足攻略要求的角色：{character.name}")
                characters_to_sell.append((i, character))

        # 执行出售操作
        for i, character in characters_to_sell:
            # 由于商店区域没有角色列表，直接执行拖拽
            sell_area = (0.05, 0.86)  # 出售区域
            source = self.in_hand_area[i]
            self.operator.drag_to(source[0], source[1], sell_area[0], sell_area[1])
            # 更新备战席状态
            self.in_hand_character[i] = None
            if character:
                character.is_placed = False
            logger.info(f"已出售角色：{character.name}")
            self.operator.sleep(0.5)
        logger.info("出售操作完成")

    def battle(self) -> bool:
        # 按钮偶现点击不生效：点击后需确认按钮消失，未消失则重试
        button_labels = ["出战", "跳过", "幕后茶歇", "选择主角"]
        button_region = {"from_x": 0.9, "from_y": 0.65, "to_x": 0.98, "to_y": 0.75}
        # 限制处理次数，避免识别异常时无限递归
        max_protagonist_selections = 3
        for _ in range(max_protagonist_selections + 1):
            index, box = self.operator.wait_ocr_any(button_labels, **button_region)
            if index == -1:
                # 没有识别到任何已知按钮
                raise RuntimeError("未识别到战斗按钮或跳过按钮")
            for _ in range(3):
                self.operator.click_box(box, after_sleep=1.5)
                retry_box = self.operator.ocr_match(button_labels[index], **button_region)  # pyright: ignore[reportArgumentType]
                if retry_box is None:  # 按钮已消失，点击生效
                    break
                box = retry_box  # 用重新定位的位置重试
            else:
                logger.warning(f"点击「{button_labels[index]}」后按钮未消失，点击可能未生效")
            if index != 3:  # 不是选择主角，继续后续战斗流程
                break
            self.handle_protagonist_selection()  # 选择完主角后重新进入战斗流程
        else:
            raise RuntimeError("战斗流程异常")
        if index == 2:  # 幕后茶歇
            self.handle_tea_break()
            return True
        if index == 0:  # 出战：确认前台角色后等待战斗结束
            ocr_i, _ = self.operator.ocr_match_any(["无角色", "未达上限"], from_x=0.36, from_y=0.44, to_x=0.64, to_y=0.5)
            # 检查前台区域是否有角色
            if ocr_i == 0:
                logger.error("前台区域无角色，无法出战，跳过本轮剩余流程")
                self.skip_current_round = True
                self.operator.click_img(IMG.ENSURE)
                return False
            elif ocr_i == 1:
                logger.info("前台区域未达上限，继续战斗")
                self.operator.click_img(IMG.ENSURE)
            logger.info("战斗开始，等待挑战结束")
            # 战斗中持续检测“未开启自动战斗”图标（Q），出现即按 V 开启；
            # IMG.Q 放在结算/继续之后，保证战斗结束时优先判定为结束
            waiting_templates = [CWIMG.SETTLE, CWIMG.CONTINUE, IMG.Q]
        else:  # 跳过战斗：对局已结束，直接等待结算界面
            logger.info("跳过战斗")
            waiting_templates = [CWIMG.SETTLE, CWIMG.CONTINUE]
        deadline = time.time() + 600
        while True:
            result, _ = self.operator.wait_any_img(waiting_templates, timeout=max(deadline - time.time(), 0),
                                                   interval=1, trace=False)
            if result != 2:  # 结算/继续按钮或超时（跳过战斗时没有索引 2）
                break
            self.operator.press_key("v")  # 按 V 开启自动战斗，继续等待
            self.operator.sleep(1)
        if result == -1:
            logger.warning("等待挑战结束超时")
            for _ in range(5):
                self.operator.press_key('esc')
                self.operator.sleep(1)
                if self.operator.click_img(CWIMG.RETREAT):
                    break
            else:
                raise RuntimeError("挑战结束超时，未能成功中止对局")
            self.abort_and_return() # 挑战结束超时，尝试中止并返回开始页面
            return False
        logger.info("挑战结束")
        self.operator.sleep(0.5)
        self.operator.click_point(0.5, 0.824, tag="点击继续按钮")
        self.operator.sleep(3)
        return True

    def stage_transition(self):
        """实现关卡切换逻辑，通过识别图片状态执行对应操作"""
        # 定义状态配置：(图片路径, 状态名称, 处理函数, 是否为终止状态)
        stage_config = [
            (
                CWIMG.REPLENISH_STAGE,
                StageName.REPLENISH_STAGE,
                self.handle_replenish_stage
            ),
            (
                CWIMG.ENCOUNTER_NODE,
                StageName.ENCOUNTER_NODE,
                self.handle_encounter_node
            ),
            (
                CWIMG.FOLD,
                StageName.FOLD,
                lambda prev_stage: True,  # 目标状态，无需处理
            ),
            (
                CWIMG.SELECT_INVEST_STRATEGY,
                StageName.SELECT_INVEST_STRATEGY,
                self.handle_invest_strategy
            ),
            (
                CWIMG.CLICK_BLANK,
                StageName.CLICK_BLANK,
                self.handle_click_blank
            ),
            (
                CWIMG.NEXT_STEP,
                StageName.GAME_OVER,
                self.handle_game_over
            ),
            (
                CWIMG.START_CURRENCY_WARS,
                StageName.MAIN_MENU,
                self.handle_main_menu
            ),
            (
                CWIMG.SELECT_EQUIPMENT,
                StageName.SELECT_EQUIPMENT,
                lambda prev_stage: self.operator.click_point(0.5, 0.2, after_sleep=0.5, tag="选择装备")
            ),
        ]

        img_list = [cfg[0] for cfg in stage_config]

        while True:  # 用无限循环 + 内部break控制退出
            stage_index, _ = self.operator.wait_any_img(img_list, timeout=15, interval=1)
            self.operator.sleep(1.5)
            prev_stage_name: StageName | None = None
            # 检查是否超时（未识别到任何状态）
            if stage_index == -1:
                if self.operator.click_img(CWIMG.STORE):
                    continue
                raise RuntimeError("关卡状态检测超时，未识别到任何图片")

            # 获取当前状态配置
            img_path, stage_name, handle_func = stage_config[stage_index]
            logger.info(f"检测到状态：{stage_name}({img_path})")

            # 执行状态处理函数
            try:
                is_terminal = handle_func(prev_stage_name)
                logger.info(f"状态 {stage_name} 处理完成")
            except Exception as e:
                raise RuntimeError(f"处理状态 {stage_name} 时发生异常: {str(e)}") from e

            # 更新上一阶段名称
            prev_stage_name = stage_name

            # 若当前是终止状态，直接退出循环
            if is_terminal:
                logger.info(f"达到终止状态：{stage_name}，退出关卡切换流程")
                return self.handle_stage_transitioned()

    def handle_main_menu(self, _: StageName | None) -> bool:
        """处理主菜单界面的逻辑"""
        self.is_game_over = True
        return True

    def handle_stage_transitioned(self) -> bool:  # NOQA
        """关卡切换完成后的处理逻辑（如有）。默认实现为无操作，子类可重写此方法以添加额外逻辑。
        调用时机：在完成关卡切换流程后、正式进入下一轮游戏循环前调用
        Returns:
            True-继续执行游戏循环；False-中止任务
        """
        return True

    def handle_characters_updated(self):
        """角色信息更新后的处理逻辑（如有）。默认实现为无操作，可重写此方法以添加额外逻辑。"""
        if all(c is None for c in self.on_field_character + self.off_field_character + self.in_hand_character):
            # 如果所有角色信息均为None，打开商店界面购买角色
            self.operator.click_point(0.8438, 0.8481, after_sleep=1, tag="打开商店界面")
            self.shopping()
            # 重新获取备战席信息
            self.get_in_hand_area()

    def handle_game_over(self, _: StageName | None) -> bool:
        """处理游戏结束后的逻辑，如点击继续、返回主界面等"""
        self.operator.click_img(CWIMG.NEXT_STEP)
        self.operator.move_to(0.5, 0.5)  # 移动鼠标避免遮挡
        next_page_box = self.operator.wait_img(CWIMG.NEXT_PAGE)
        if next_page_box is None:
            logger.warning("未识别到下一页按钮，无法继续")
            self.operator.click_point(0.5, 0.82, after_sleep=1, tag="点击下一页")  # 兜底方案
        else:
            self.operator.click_box(next_page_box, after_sleep=1)
        self.operator.click_point(0.5, 0.82, after_sleep=1, tag="点击返回货币战争")
        self.is_game_over = True  # 标记游戏结束
        return True

    def handle_click_blank(self, _: StageName | None) -> bool:
        """处理Boss预览界面的逻辑"""
        self.operator.click_point(0.5, 0.70, after_sleep=1)
        return False

    def handle_invest_strategy(self, prev_stage: StageName | None) -> bool:
        """处理投资策略选择界面的逻辑"""
        if not self.operator.click_img(CWIMG.COLLECTION):
            self.operator.click_point(0.5, 0.3, after_sleep=0.5, tag="选择中间的投资策略")
        self.operator.click_img(IMG.ENSURE2, after_sleep=1)
        self.post_invest_strategy()
        return False

    def post_invest_strategy(self, strategy_name: str | None = None):
        """投资策略选择后的后续处理逻辑"""
        if strategy_name == "阿哈大悦" or self.operator.locate(CWIMG.SELECT_SIMPLE_EQUIPMENT):
            self.operator.click_point(0.8, 0.25, after_sleep=1, tag="阿哈大悦选择装备4")

    def handle_replenish_stage(self, _: StageName | None):
        """处理补给阶段的逻辑"""
        self.operator.click_point(0.53, 0.52, after_sleep=1)  # 选择固定位置
        self.operator.click_point(0.88, 0.91, after_sleep=1)  # 点击确认按钮
        self.detect_silver_wolf_lv999()  # 也许选到银狼了
        return False

    def handle_encounter_node(self, _: StageName | None) -> bool:
        """处理遭遇节点的逻辑"""
        self.operator.click_point(0.35, 0.50, after_sleep=1)  # 简单难度
        self.operator.click_point(0.50, 0.84, after_sleep=1)  # 点击确认钮
        return False

    def _handle_selection_event(self, ocr_region: tuple[float, float, float, float],
                                keyword: str, count: int = 1):
        """
        通用事件选择处理
        :param ocr_region: OCR识别区域 (from_x, from_y, to_x, to_y)
        :param keyword: 目标关键词（空格分隔的多个关键词按顺序各匹配一个选项）
        :param count: 需要同时选中的选项数量（如“梦境交织”需要选择两个）
        """
        boxes = self.operator.ocr_boxes(from_x=ocr_region[0], from_y=ocr_region[1],
                                        to_x=ocr_region[2], to_y=ocr_region[3])
        if not boxes:
            return False
        # 每个关键词各匹配一个尚未选中的选项
        chosen: list[int] = []
        for candidate in keyword.split() or [""]:
            for index, box in enumerate(boxes):
                if index not in chosen and candidate in box.source.strip():
                    chosen.append(index)
                    break
        if not chosen:
            # 如果没有匹配的关键词，则默认选择最后一个选项
            chosen = [len(boxes) - 1]
        if len(chosen) < count:
            # 需要多选时，按 OCR 顺序补齐未选中的选项
            chosen += [index for index in range(len(boxes)) if index not in chosen][:count - len(chosen)]
        if len(chosen) < count:
            logger.warning(f"事件选项不足：需要选择 {count} 个，仅识别到 {len(chosen)} 个")
        for index in chosen:
            self.operator.click_box(boxes[index], after_sleep=1)
        # 确认按钮偶现点击不生效：点击后按钮应消失，仍在则重试
        for _ in range(3):
            self.operator.click_img(IMG.ENSURE2, after_sleep=1)
            if not self.operator.locate(IMG.ENSURE2):
                break
        else:
            raise RuntimeError("确认事件选择失败")
        return True

    def handle_the_planet_of_festivities(self):
        """处理盛会之星事件的逻辑"""
        return self._handle_selection_event((0.22, 0.29, 0.85, 0.35),
                                            self.strategy_special_events.get("盛会之星", ""))

    def handle_choose_partner(self):
        """处理领航员选择事件的逻辑"""
        return self._handle_selection_event((0.25, 0.32, 0.85, 0.39),
                                            self.strategy_special_events.get("领航员", ""))

    def handle_wish_trial(self):
        """处理命运圣杯事件的逻辑"""
        return self._handle_selection_event((0.22, 0.42, 0.85, 0.465), self.strategy_special_events.get("命运圣杯", ""))

    def handle_trailblaze_store(self):
        """处理开拓银轨事件的逻辑"""
        self.operator.click_point(0.5, 0.2)
        self.operator.click_point(0.5, 0.5)
        return True

    def handle_beast_garden(self):
        """处理奇兽花园事件的逻辑"""
        return self._handle_selection_event((0.22, 0.34, 0.85, 0.4),
                                            self.strategy_special_events.get("奇兽花园", ""))

    def handle_dream_interference(self):
        """处理梦境交织事件的逻辑（该事件需要同时选择两个选项）"""
        return self._handle_selection_event((0.22, 0.3, 0.85, 0.36),
                                            self.strategy_special_events.get("梦境交织", ""),
                                            count=2)

    def detect_special_event(self) -> str:
        """检测当前是否有特殊事件发生，并返回事件名称"""
        result = self.operator.ocr(from_x=0.49, from_y=0.038, to_x=0.60, to_y=0.11)
        if not result:
            return ""
        # OCR 可能把标题切成多个片段，括号等符号也容易被识别成噪声（如“我来当(?策划”），
        # 因此先按坐标拼接，再只保留汉字匹配标题
        text = re.sub(r"[^\u4e00-\u9fff]", "", _merge_ocr_text(result))
        # 遍历特殊事件列表，匹配标题
        for event, (title, handler) in self.special_events.items():
            if title in text:
                return event
        return ""

    def detect_silver_wolf_lv999(self):
        """处理银狼LV.999 2星事件的逻辑"""
        if self.operator.locate(CWIMG.SILVER_WOLF_LV999):
            self.handle_silver_wolf_lv999()

    def handle_silver_wolf_lv999(self):
        return self._handle_selection_event((0.22, 0.34, 0.85, 0.4),
                                            self.strategy_special_events.get("头号玩家", ""))

    def handle_special_event(self):
        """处理特殊事件的逻辑"""
        event = self.detect_special_event()

        if event:
            logger.info(f"检测到特殊事件：{event}")
            handler = self.special_events[event][1]
            if not handler():
                raise RuntimeError("特殊事件处理失败")
            self.handle_special_event()  # 递归处理
        # 未检测到事件，退出

    # ==================== 幕后茶歇节点 ====================
    def handle_tea_break(self) -> bool:
        """处理「幕后茶歇」奇遇节点。

        该节点出现时界面右侧不会显示出战按钮，而是显示「幕后茶歇」按钮。
        点击后在「与奇遇伙伴对话（触发特殊事件）」与「享用茶歇（回复 20 点小队生命值）」中二选一，
        并推进后续对话、奖励选择与开箱流程，直到回到备战界面。

        :return: True-已处理完茶歇事件并回到备战界面；False-当前不是茶歇节点或处理失败
        """

        def _is_tea_break_health_low() -> bool:
            """读取茶歇界面顶部的生命值，判断是否需要优先回复生命"""
            result = self.operator.ocr(from_x=0.49, from_y=0.03, to_x=0.57, to_y=0.12)
            for item in result or []:
                text = str(item[1]).strip()
                if text.isdigit():
                    health = int(text)
                    logger.info(f"[幕后茶歇] 当前生命值：{health}")
                    return health <= 40
            return False

        def _drive_tea_break(_option: tuple[float, float]) -> bool:
            """推进茶歇事件：处理对话、特殊事件奖励与开箱，直到回到备战界面"""
            self.operator.click_point(*_option, after_sleep=1)
            self.operator.do_while(
                lambda : self.operator.locate(CWIMG.TEA_BREAK, from_x=0.65, from_y=0.8, to_x=0.9, to_y=0.9) is not None,
                lambda : self.operator.click_point(0.5, 0.5, after_sleep=1),
                max_iterations=5
            )
            return_box = self.operator.wait_ocr("返回", from_x=0.58, from_y=0.38, to_x=0.96, to_y=0.8, timeout=3)
            if return_box is None:
                logger.error("[幕后茶歇] 未识别到返回按钮，茶歇事件推进失败")
                return False
            self.operator.click_box(return_box, y_offset=-0.1, after_sleep=0.5)  # 点击返回选项的上一个选项
            ensure_box = self.operator.wait_ocr("确认", from_x=0.58, from_y=0.38, to_x=0.96, to_y=0.8, timeout=3)
            if ensure_box is None:
                logger.error("[幕后茶歇] 未识别到确认按钮，茶歇事件推进失败")
                return False
            self.operator.click_box(ensure_box, after_sleep=0.5)
            self.operator.do_while(
                lambda: self.operator.locate(CWIMG.CLICK_BLANK, from_x=0.65, from_y=0.8, to_x=0.9, to_y=0.9) is None,
                lambda: self.operator.click_point(0.5, 0.9, after_sleep=1),
                max_iterations=5
            )  # 点击空白处推进对话，直到出现「点击空白处继续」提示
            return True

        if self.operator.ocr_match("享用茶歇", from_x=0.70, from_y=0.56, to_x=0.90, to_y=0.62) is None:
            logger.error("[幕后茶歇] 未识别到茶歇事件界面")
            return False
        # 生命值偏低时优先享用茶歇回复生命，否则与奇遇伙伴对话获取特殊奖励
        option = (0.8, 0.5) if _is_tea_break_health_low() else (0.2, 0.5)
        return _drive_tea_break(option)

    def handle_protagonist_selection(self) -> bool:
        """处理「选择主角」奇遇节点。"""
        logger.info("选择主角")
        self.operator.click_point(0.2, 0.3, after_sleep=1, tag="选择左侧效果")
        target = (0.5, 0.4)
        # 从前台角色中按优先级从高到低依次尝试
        candidates = sorted(((i, c) for i, c in enumerate(self.on_field_character) if c is not None),
                            key=lambda item: item[1].priority or 0, reverse=True)
        if not candidates:
            raise RuntimeError("未检测到前台角色，无法选择主角")
        for index, character in candidates:
            logger.info(f"选择主角：{character.name}（优先级 {character.priority}）")
            origin = (0.42+index*0.05, 0.56)
            self.operator.drag_to(origin[0], origin[1], target[0], target[1])  # 拖动角色到主角位置
            self.operator.sleep(0.5)
            self.operator.click_point(0.5, 0.888, after_sleep=1, tag="点击确认选择主角")
            # 该角色已有主角效果时会弹出替换光环提示，只识别提示文字所在的小块区域
            if self.operator.ocr_match("替换", from_x=0.38, from_y=0.43, to_x=0.65, to_y=0.53):
                # 该角色已有主角效果：关闭替换提示，换下一个角色重试
                logger.warning(f"角色 {character.name} 已有主角效果，换下一个角色重试")
                self.operator.press_key("esc")
                self.operator.sleep(1)
                continue
            return True
        raise RuntimeError("未能选择主角：所有前台角色都已有主角效果")

    def shopping(self):
        def scan_characters_in_store() -> list[Character] | None:
            """扫描商店中的角色"""
            results = self.operator.ocr(from_x=0.19, from_y=0.26, to_x=0.88, to_y=0.31)
            chars = []
            if not results:
                return []
            for item in results:
                name_raw = item[1]
                if not isinstance(name_raw, str):
                    continue
                name: str = name_raw.strip()
                if not name:
                    continue
                if name.isdecimal():  # 跳过价格识别结果
                    continue
                if '备' in name:  # 备战席已满
                    return None
                char = Characters.get_character(name)
                if char is not None:
                    chars.append(char)
                    logger.info(f"商店中发现角色：{char.name}，P: {char.priority}")
                else:
                    logger.info(f"商店中发现未知角色：{name}")
            return chars

        def purchase_target_character(characters: list[Character]) -> bool:
            """
            尝试购买目标角色（策略内的角色）
            :param characters: 商店中扫描到的角色列表
            :return: True-购买成功，False-无目标角色可买
            """
            for i, c in enumerate(characters):
                if c.name in self.strategy_characters.keys():  # 角色在攻略列表中
                    if c.stars >= self.strategy_characters[c.name]:
                        continue  # 已达目标星级
                    # 执行购买操作
                    target = self.store_area[i]
                    self.operator.click_point(*target, after_sleep=0.5)
                    logger.info(f"购买角色：{c.name}")
                    # 特殊处理
                    if c.name == Characters.SilverWolfLV999.name:
                        self.detect_silver_wolf_lv999()
                    self.operator.move_to(0.5, 0.5)  # 移动鼠标避免遮挡

            logger.info("当前商店无目标角色可购买")
            return False

        cs = scan_characters_in_store()
        if cs:
            purchase_target_character(cs)
        prev_coins = -1
        while True:
            purchased = False

            level = self.get_level()
            coins = self.get_coins()

            # 前后两次循环识别到的金币数量相同则结束循环
            if coins == prev_coins:
                logger.info(f"当前金币{coins}与上一轮相同，退出购物循环")
                break
            prev_coins = coins

            # 基础退出条件：金币不足4
            if coins < 4:
                logger.info(f"金币不足4（当前{coins}），退出购物循环")
                break
            # 等级大于3且小于最低等级：升级
            if 3 < level < self.min_level:
                logger.info(f"等级{level}大于3且小于最低等级{self.min_level}，执行升级操作")
                self.operator.press_key('f')
                self.operator.sleep(0.5)
                continue

            # 扫描商店角色并尝试购买
            cs = scan_characters_in_store()
            if cs:
                purchased = purchase_target_character(cs)

            # 非超频模式：检查金币是否满足保留要求（预判刷新后结果）
            if not self.is_overclock:
                # 最小保留数校验：当前金币 < 最小保留数 → 直接退出
                if coins < self.min_coins:
                    logger.info(f"当前金币 {coins} 小于最低保留数量 {self.min_coins}，退出购物循环")
                    break

            # 执行刷新（仅当预判后金币足够时才会走到这里）
            self.operator.press_key('d')
            self.operator.sleep(0.5)

            # 6. 等级<中级等级且未购买：升级（原有逻辑）
            if level < self.mid_level and not purchased:
                logger.info(f"等级{level}<中级等级{self.mid_level}且未购买角色，执行升级操作")
                self.operator.press_key('f')
                self.operator.sleep(0.5)

        # 关闭商店
        self.operator.click_point(0.5, 0.55, after_sleep=1.5)
        logger.info("购物流程结束，关闭商店")

    @property
    def current_team_size(self) -> int:
        """获取当前队伍人数"""
        size = 0
        for character in self.on_field_character + self.off_field_character:
            if character is not None:
                size += 1
        return size

    @property
    def in_hand_character_count(self) -> int:
        """获取当前备战席角色数量"""
        count = 0
        for character in self.in_hand_character:
            if character is not None:
                count += 1
        return count

    def get_level(self):
        logger.info("获取当前等级")
        level = self.operator.ocr(from_x=0.05, from_y=0.815, to_x=0.3, to_y=0.87)
        try:
            if level:
                return int(level[0][1].split('.')[1])
            else:
                return self.max_team_size
        except (ValueError, IndexError):
            return self.max_team_size

    def update_max_team_size(self):
        result = self.operator.ocr(from_x=0.505, from_y=0.18, to_x=0.608, to_y=0.27)
        if result:
            try:
                self.max_team_size = int(str(result[-1][1]).strip())
                logger.info(f"最大队伍人数已更新为 {self.max_team_size}")
            except ValueError:
                logger.warning(f"无法解析最大队伍人数：{result[-1][1]}")

    def load_strategy(self, name: str):
        """加载攻略文件"""
        if not name.strip():
            logger.warning("未指定攻略文件名，将使用默认策略")
            name = "template"
        if ".json" in name:
            path = name
        else:
            path = f"tasks/currency_wars/strategies/{name}.json"
        with open(path, "r", encoding="utf-8") as f:
            strategy_data: dict[str, Any] = json.load(f)
        strategy_title = strategy_data.get("title", "")
        description = strategy_data.get("description", "")
        self.min_coins = strategy_data.get("min_coins", 40)
        self.min_level = strategy_data.get("min_level", 7)
        self.mid_level = strategy_data.get("mid_level", 7)
        self.strategy_code = strategy_data.get("share_code", "")
        self.strategy_special_events = strategy_data.get("special_events", {})
        # 在攻略中的角色设置成最高优先级
        strategy_on_field: dict[str, int] = strategy_data.get("on_field", {})
        strategy_off_field: dict[str, int] = strategy_data.get("off_field", {})
        # 攻略里的角色名可能带 OCR 无法输入的字符（如“知更鸟•晴歌”），统一按角色表的标准名称记录
        on_field_names: set[str] = set()
        for i, cn in enumerate(strategy_on_field.keys()):
            c = Characters.get_character(cn)
            if c is None:
                logger.warning(f"攻略角色不存在，跳过：{cn}")
                continue
            c.priority = 99 - i  # 确保攻略中的前台角色优先级都大于其他角色，同时有所差别
            c.position = Positioning.OnField
            on_field_names.add(c.name)
            self.strategy_characters[c.name] = strategy_on_field[cn]
        for i, cn in enumerate(strategy_off_field):
            c = Characters.get_character(cn)
            if c is None:
                logger.warning(f"攻略角色不存在，跳过：{cn}")
                continue
            c.priority = 99 - i  # 确保攻略中的后台角色优先级都大于其他角色
            if c.name in on_field_names:
                c.position = Positioning.OnOffField
            else:
                c.position = Positioning.OffField
                self.strategy_characters[c.name] = strategy_off_field[cn]
        # 兼容旧配置: 1 -> 1星，3 -> 2星，9 -> 3星
        for sc in self.strategy_characters.keys():
            if 3 < self.strategy_characters[sc] < 9:
                self.strategy_characters[sc] = 2
            elif self.strategy_characters[sc] >= 9:
                self.strategy_characters[sc] = 3
        logger.info(f"已加载攻略: {strategy_title}: {description}")

    def unload_strategy(self):
        """卸载当前攻略，重置角色"""
        for c in Characters.characters.values():
            c.reset()
        self.min_coins = 40
        self.min_level = 7
        self.mid_level = 7
        self.strategy_characters.clear()
        self.strategy_code = ""
        logger.info("已卸载当前攻略，角色优先级已重置")

    def place_character(self) -> bool:
        """
        将手中的角色放置到前台或后台（严格先放前台角色，再放后台角色，确保前台优先占位）
        队伍不满时优先放空位，队伍满时仅替换低priority角色
        :return: 至少有一个角色放置成功返回 True，否则返回 False
        """
        # 第一次遍历：仅处理前台角色（Positioning.OnField / OnOffField），优先占满编队
        logger.info("=== 放置前台角色 ===")
        for i, character in enumerate(self.in_hand_character):
            if character is None or character.is_placed:
                continue
            if character.position == Positioning.OffField:
                continue
            if self.place_on_field_character(i):
                self.operator.sleep(2)
                self.handle_special_event()

        # 第二次遍历：仅处理后台角色（Positioning.OffField），填充剩余空位或替换
        logger.info("=== 放置后台角色 ===")
        for i, character in enumerate(self.in_hand_character):
            if character is None or character.is_placed:
                continue
            if character.position == Positioning.OnField:
                continue
            if self.place_off_field_character(i):
                self.operator.sleep(2)
                self.handle_special_event()

        # 若前台为空，则从后台提升一个角色到前台第一个位置，避免出现前台全空的情况
        self.ensure_on_field_not_empty()

        logger.info("角色放置完成")
        return True

    def place_on_field_character(self, character_in_hand: int) -> bool:
        """将手中的角色放置到前台（前台角色专用，优先占位）"""
        return self._place_to_target(
            character_in_hand,
            target_characters=self.on_field_character,
            area_type="前台"
        )

    def place_off_field_character(self, character_in_hand: int) -> bool:
        """将手中的角色放置到后台（后台角色专用）"""
        return self._place_to_target(
            character_in_hand,
            target_characters=self.off_field_character,
            area_type="后台"
        )

    def ensure_on_field_not_empty(self) -> bool:
        """校验前台角色列表是否为空。

        若前台（on_field_character）全部为空，则从后台（off_field_character）中按顺序取第一个非空角色，
        将其移动到前台第一个位置（索引 0）。

        :return: 若无需处理或移动成功返回 True；若前台为空且后台也无角色可移动则返回 False。
        """
        if any(c is not None for c in self.on_field_character):
            return True

        for off_index, char in enumerate(self.off_field_character):
            if char is None:
                continue
            logger.info(f"前台为空，提升后台角色 {char.name} (off_field[{off_index}]) 到前台 on_field[0]")
            return self.swap_character_between_areas(
                source_area_type='off_field',
                source_index=off_index,
                target_area_type='on_field',
                target_index=0,
            )

        logger.warning("前台为空且后台无角色可提升")
        return False

    def _place_to_target(
            self,
            character_in_hand: int,
            target_characters: list[Character | None],
            area_type: str
    ) -> bool:
        """通用放置逻辑：适配前台/后台角色，处理空位放置和满员替换"""
        full_team = self.current_team_size >= self.max_team_size

        # 1. 基础有效性检查
        if not (0 <= character_in_hand < len(self.in_hand_character)):
            logger.error(f"无效的备战席索引：{character_in_hand}（范围：0~{len(self.in_hand_character) - 1}）")
            return False

        character = self.in_hand_character[character_in_hand]
        if not character or character.is_placed:
            logger.warning(f"备战席索引 {character_in_hand} 无有效角色或角色已放置")
            return False

        # 确定目标区域类型
        target_area_type = 'on_field' if area_type == "前台" else 'off_field'

        # 2. 队伍不满时：优先填充空位（前台角色优先占名额）
        if not full_team:
            for index, existing_char in enumerate(target_characters):
                if existing_char is None:
                    # 使用通用对换方法实现放置
                    success = self.swap_character_between_areas(
                        source_area_type='in_hand',
                        source_index=character_in_hand,
                        target_area_type=target_area_type,
                        target_index=index
                    )
                    if success:
                        logger.info(
                            f"角色 {character.name} 放置到{area_type}索引 {index}（空位）")
                    return success
            logger.info(f"{area_type}无空位可放置")

        # 3. 队伍已满时：仅替换低priority角色（不占用新名额）
        min_priority = character.priority if character.priority is not None else -1
        min_priority_index = -1
        # 查找目标区域中priority最低的角色
        for index, existing_char in enumerate(target_characters):
            # if existing_char is None:
            if existing_char is None or existing_char.priority is None:
                continue
            # existing_priority = existing_char.priority if existing_char.priority is not None else -1
            # if existing_priority < min_priority:
            if existing_char.priority < min_priority:
                # min_priority = existing_priority
                min_priority = existing_char.priority
                min_priority_index = index

        if min_priority_index != -1:
            existing_char = target_characters[min_priority_index]
            if existing_char is None:  # 类型保护
                return False
            # 使用通用对换方法实现替换
            success = self.swap_character_between_areas(
                source_area_type='in_hand',
                source_index=character_in_hand,
                target_area_type=target_area_type,
                target_index=min_priority_index
            )
            if success:
                logger.info(
                    f"角色 {character.name} 替换{area_type}索引 {min_priority_index} 的 {existing_char.name} "
                    f"(priority {existing_char.priority} → {character.priority})"
                )
            return success

        logger.info(f"{character.name}无低priority角色可替换")
        return False

    def swap_character_between_areas(
            self,
            source_area_type: str,
            source_index: int,
            target_area_type: str,
            target_index: int
    ) -> bool:
        """
        通用方法：将两个任意区域的任意位置的内容进行对换

        :param source_area_type: 源区域类型 ('on_field', 'off_field', 'in_hand')
        :param source_index: 源区域中的位置索引
        :param target_area_type: 目标区域类型 ('on_field', 'off_field', 'in_hand')
        :param target_index: 目标区域中的位置索引
        :return: 对换操作是否成功
        """
        # 区域映射：区域类型 -> (角色列表, 坐标列表, 区域名称)
        area_mapping = {
            'on_field': (self.on_field_character, self.on_field_area, "前台"),
            'off_field': (self.off_field_character, self.off_field_area, "后台"),
            'in_hand': (self.in_hand_character, self.in_hand_area, "备战席")
        }

        # 验证区域类型
        if source_area_type not in area_mapping or target_area_type not in area_mapping:
            logger.error(f"无效的区域类型: source={source_area_type}, target={target_area_type}")
            return False

        # 获取源区域信息
        source_chars, source_coords, source_name = area_mapping[source_area_type]
        # 获取目标区域信息
        target_chars, target_coords, target_name = area_mapping[target_area_type]

        # 验证索引范围
        if not (0 <= source_index < len(source_coords)):
            logger.error(f"源区域索引超出范围: {source_index} (0~{len(source_coords) - 1})")
            return False
        if not (0 <= target_index < len(target_coords)):
            logger.error(f"目标区域索引超出范围: {target_index} (0~{len(target_coords) - 1})")
            return False

        # 获取源和目标角色
        source_char = source_chars[source_index]
        target_char = target_chars[target_index]

        # 记录操作前的状态
        logger.info(f"开始对换操作: {source_name}[{source_index}] <-> {target_name}[{target_index}]")
        logger.info(f"源角色: {source_char.name if source_char else 'None'}")
        logger.info(f"目标角色: {target_char.name if target_char else 'None'}")

        # 执行拖拽对换操作
        source_coord = source_coords[source_index]
        target_coord = target_coords[target_index]

        # 执行拖拽
        self.operator.drag_to(source_coord[0], source_coord[1], target_coord[0], target_coord[1], trace=False)
        self.operator.sleep(0.5)  # 等待操作完成
        if self.operator.locate(CWIMG.CANNOT_BE_FIELDED, from_x=0.25, from_y=0.25, to_x=0.75, to_y=0.75):
            logger.warning("对换操作失败：目标位置无法放置该角色")
            self.operator.sleep(1)
            self.operator.click_point(0.5, 0.5, after_sleep=1)  # 点击空白处关闭提示.
            return False

        # 交换角色列表中的内容
        source_chars[source_index], target_chars[target_index] = target_chars[target_index], source_chars[source_index]

        # 更新角色的放置状态
        if source_char:
            source_char.is_placed = (target_area_type != 'in_hand')
        if target_char:
            target_char.is_placed = (source_area_type != 'in_hand')

        logger.info(f"对换操作完成: {source_name}[{source_index}] <-> {target_name}[{target_index}]")
        return True

    def sort_characters_by_priority(self, area_type: str) -> bool:
        """
        对指定区域的角色按优先级进行排序，高优先级角色靠前

        :param area_type: 区域类型 ('on_field', 'off_field')
        :return: 排序操作是否成功
        """
        # 验证区域类型
        if area_type not in ['on_field', 'off_field']:
            logger.error(f"无效的区域类型: {area_type}，只支持 'on_field' 或 'off_field'")
            return False

        # 获取区域信息
        if area_type == 'on_field':
            characters = self.on_field_character
            area_name = "前台"
        else:  # off_field
            characters = self.off_field_character
            area_name = "后台"

        logger.info(f"开始对{area_name}区域角色按优先级排序")

        # 创建包含角色、索引和优先级的列表
        char_info_list = []
        for i, char in enumerate(characters):
            if char is not None:
                char_info_list.append({
                    'character': char,
                    'index': i,
                    'priority': char.priority
                })
            else:
                char_info_list.append({
                    'character': None,
                    'index': i,
                    'priority': -1  # 空位置优先级设为-1，排在最后
                })

        # 按优先级降序排序（高优先级在前）
        sorted_char_info = sorted(char_info_list, key=lambda x: x['priority'], reverse=True)

        # 执行排序交换
        success_count = 0
        for target_pos, target_info in enumerate(sorted_char_info):
            current_pos = target_info['index']

            # 如果已经在正确位置，跳过
            if current_pos == target_pos:
                continue

            # 找到目标位置当前的角色信息
            target_current_info: dict[str, Any] | None = None
            for info in char_info_list:
                if info['index'] == target_pos:
                    target_current_info = info
                    break

            # 如果目标位置为空或优先级较低，执行交换
            if (target_current_info is None or
                    target_current_info['character'] is None or
                    target_current_info['priority'] <= target_info['priority']):

                # 执行交换
                if self.swap_character_between_areas(
                        source_area_type=area_type,
                        source_index=current_pos,
                        target_area_type=area_type,
                        target_index=target_pos
                ):
                    success_count += 1
                    logger.info(f"{area_name}区域位置交换: [{current_pos}] <-> [{target_pos}]")

                    # 更新char_info_list中的索引信息
                    for info in char_info_list:
                        if info['index'] == current_pos:
                            info['index'] = target_pos
                        elif info['index'] == target_pos:
                            info['index'] = current_pos

        logger.info(f"{area_name}区域优先级排序完成，成功交换 {success_count} 次")
        return success_count > 0

    def sort_all_areas_by_priority(self) -> bool:
        """
        对所有区域（前台和后台）的角色按优先级进行排序

        :return: 排序操作是否成功
        """
        logger.info("开始对所有区域进行优先级排序")

        field_success = self.sort_characters_by_priority('on_field')
        offfield_success = self.sort_characters_by_priority('off_field')

        overall_success = field_success or offfield_success

        if overall_success:
            logger.info("所有区域优先级排序完成")
        else:
            logger.info("无需进行排序操作")

        return overall_success
