import json
from typing import Any

from loguru import logger

import tasks.currency_wars.characters as cw_chars
from SRACore.task import Executable
from tasks.currency_wars.characters import Character, Positioning, get_character
from tasks.currency_wars.img import CWIMG, IMG


class CurrencyWars(Executable):
    def __init__(self, operator, run_times: int):
        super().__init__(operator)
        self.run_times = run_times
        self.is_continue = False  # 是否是继续挑战
        self.strategy_external_control: bool = False  # 当外部（如刷开局流程）希望在“选择投资策略”页接管逻辑时，置为 True
        self.difficulty_mode: int = 0  # 难度模式：0=最低难度，1=最高难度（默认最低）
        self.on_field_character: list[Character | None] = [None, None, None, None]  # 场上角色列表
        self.on_field_area: list[tuple[float, float]] = [
            (0.386, 0.365),
            (0.464, 0.365),
            (0.536, 0.365),
            (0.611, 0.365)
        ]
        self.off_field_character: list[Character | None] = [None, None, None, None, None, None]  # 场下角色列表
        self.off_field_area: list[tuple[float, float]] = [
            (0.3056, 0.620),
            (0.3806, 0.620),
            (0.4525, 0.620),
            (0.5264, 0.620),
            (0.6004, 0.620),
            (0.6738, 0.620)
        ]
        self.in_hand_character: list[Character | None] = [None, None, None, None, None, None, None, None,
                                                          None]  # 手牌角色列表
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
        ]  # 手牌区域
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
        self.strategy_characters: dict[str, int] = dict()  # 在攻略中的角色及其预期购买数量
        self.is_overclock = False  # 超频博弈

    def reset_character(self):
        """ 重置所有角色信息 """
        for i, c in enumerate(self.on_field_character):
            if c is not None:
                c.is_placed = False  # 重置放置状态
            self.on_field_character[i] = None  # 重置角色信息
        for i, c in enumerate(self.off_field_character):
            if c is not None:
                c.is_placed = False
            self.off_field_character[i] = None
        for i, c in enumerate(self.in_hand_character):
            if c is not None:
                c.is_placed = False
            self.in_hand_character[i] = None

    @staticmethod
    def set_username(username: str):
        # 调用处已经确保 username 非空
        cw_chars.username = username.strip()

    def set_overclock(self, overclock: bool):
        self.is_overclock = overclock

    def run(self):
        if self.run_times == 0:
            return True
        for _ in range(self.run_times):
            if not self.start_game():
                return False
            self.run_game()
        return True

    def page_locate(self) -> int:
        """
        定位到货币战争页面
        :return: int 页面编号，1表示货币战争开始页面，2表示准备阶段页面，-1表示定位失败
        """
        page, _ = self.operator.wait_any_img([IMG.ENTER,
                                              CWIMG.CURRENCY_WARS_START,
                                              CWIMG.PREPARATION_STAGE], interval=0.5)
        if page == 0:
            guide_hotkey = ((self.settings or {}).get('GuideHotkey', 'f4') or 'f4')
            self.operator.press_key(str(guide_hotkey).lower())
            if not self.operator.wait_img(IMG.F4, timeout=20):
                logger.error("检测超时，编号1")
                self.operator.press_key("esc")
            self.operator.click_img("resources/img/cosmic_strife.png", after_sleep=1)  # 旷宇纷争
            self.operator.click_point(0.242, 0.30, after_sleep=0.8)  # 货币战争
            self.operator.click_point(0.7786, 0.8194, after_sleep=1)  # 前往参与
            return 1
        elif page == 1:
            return 1
        elif page == 2:
            return 2
        else:
            logger.error("检测超时")
            return -1

    def start_game(self):
        """开始一局货币战争。
        拆分原复杂流程为多个独立步骤，提升可读性与可维护性。
        返回 True 表示进入对局并完成初始策略与手牌识别
            False 表示流程中断或失败。
        """
        page = self.page_locate()
        if page == -1:
            logger.error("页面定位失败，无法开始游戏")
            return False
        self.is_running = True  # 标记任务运行中
        # 仅在开始页面需要进入流程；准备阶段直接跳过进入逻辑
        if page == 1:
            if not self._enter_from_start_page():
                logger.error("进入对局流程失败")
                return False
        elif page == 2:
            self.is_continue = True
            logger.info("已处于准备阶段，跳过进入流程")

        # 进入对局后的初始策略与手牌更新
        if self.is_continue:
            logger.info("继续进度进入，跳过初始策略应用")
            self.operator.sleep(2)
            self.refresh_character()
            self.get_in_hand_area(True)
            return True
        if not self.initialize():
            logger.error("对局初始化失败")
            return False
        return True

    # ==================== 进入流程辅助方法 ====================
    def _enter_from_start_page(self) -> bool:
        """处理从货币战争开始页面进入对局的完整流程。"""
        start_box = self.operator.wait_img(CWIMG.CURRENCY_WARS_START, timeout=30, interval=0.5)
        if start_box is None:
            logger.error("未识别到开始按钮")
            return False
        self.operator.do_while(lambda: self.operator.click_box(start_box, after_sleep=0.5),
                      lambda: self.operator.locate(CWIMG.LOGO) is None,
                      interval=0.5, max_iterations=10)

        # 标准进入 or 继续进度
        index, box = self.operator.wait_any_img([CWIMG.ENTER_STANDARD, CWIMG.CONTINUE_PROGRESS], timeout=10,
                                                interval=0.5)

        if index == 0:
            if self.is_overclock:
                self.operator.click_point(0.1526, 0.4139, after_sleep=1, tag="超频博弈按钮")  # 超频博弈
            return self._standard_entry_flow(box)
        elif index == 1:
            return self._continue_progress_flow(box)

        logger.error("既未识别标准进入，也未识别继续进度入口")
        return False

    def _standard_entry_flow(self, enter_standard_box) -> bool:
        """标准进入：选择难度、开始游戏、投资环境。"""
        if not self.operator.click_box(enter_standard_box, after_sleep=1.5):
            return False
        # 难度选择：根据前端配置选择最低或最高
        if self.difficulty_mode == 1:
            # 最高难度：若识别到“返回最高职级”则点击，否则直接开始
            self.operator.click_img(CWIMG.RETURN_HIGHEST_RANK, after_sleep=0.8)
        else:
            # 最低难度：尝试点击下拉至最低项
            while self.operator.click_img(CWIMG.DOWN_ARROW, after_sleep=0.5):
                pass

        if not self.operator.click_img(CWIMG.START_GAME, after_sleep=1):
            return False
        next_step_box = self.operator.wait_img(CWIMG.NEXT_STEP)
        self.operator.sleep(0.5)
        if next_step_box is None or not self.operator.click_box(next_step_box, after_sleep=2):
            return False
        self.operator.click_point(0.5, 0.5, after_sleep=0.5)
        invest_box = self.operator.wait_img(CWIMG.INVEST_ENVIRONMENT)
        if invest_box is None:
            logger.error("未识别到投资环境界面")
            return False
        # 投资操作
        if not self.operator.click_img(CWIMG.COLLECTION):
            self.operator.click_point(0.5, 0.5)
        self.operator.click_img(IMG.ENSURE2, after_sleep=1)
        if self.operator.locate(CWIMG.INVEST_ENVIRONMENT):
            self.operator.click_point(0.5, 0.5)
            self.operator.click_img(IMG.ENSURE2, after_sleep=1)
        self.operator.sleep(4)
        return True

    # =============== 配置注入 ===============
    def set_difficulty(self, mode: int):
        """设置难度模式：0=最低难度，1=最高难度"""
        self.difficulty_mode = mode

    def _continue_progress_flow(self, continue_progress_box) -> bool:
        """继续已有进度进入对局。"""
        self.is_continue = True
        if not self.operator.click_box(continue_progress_box, after_sleep=1):
            return False
        try:
            self.operator.sleep(2)
            click_blank = self.operator.wait_img(CWIMG.CLICK_BLANK, timeout=5, interval=0.5)
            if click_blank is None:
                logger.error("继续进度后未识别到点击空白提示")
                return False
            self.operator.click_box(click_blank, after_sleep=1)
            return True
        except Exception as e:
            logger.error(f"继续进度流程异常，无法进入对局: {e}")
            return False

    # ==================== 进入后的初始策略 ====================
    def initialize(self) -> bool:
        """进入对局后的攻略应用与手牌识别。"""
        self.operator.sleep(1)
        # strategy_box = self.operators.wait_img(CWIMG.STRATEGY, timeout=60, interval=0.5)
        # if strategy_box is None or not self.operators.click_box(strategy_box, after_sleep=1.5):
        #     logger.error("未识别到攻略按钮")
        #     return False
        # cancel_apply_box = self.operators.wait_img(CWIMG.CANCEL_APPLY, timeout=2)
        # if cancel_apply_box is None:  # 未应用攻略则应用
        #     if self.operators.click_img(CWIMG.APPLY, after_sleep=1):
        #         self.operators.press_key('esc')
        #         self.operators.sleep(1)
        #         for _ in range(3):
        #             self.operators.click_img(CWIMG.TRACE, after_sleep=0.3)
        # self.operators.press_key('esc')
        # 不考虑中途加入、接管情况

        self.get_in_hand_area()  # 更新手牌信息（若无接管情况，则仅有此行有用）
        self.place_character()  # 放置角色
        return True

    def run_game(self):
        run_times = 0
        while self.is_running:
            # self.strategy_event()
            self.update_max_team_size()
            self.place_character()
            self.sell_character()
            if not self.battle():
                break
            if not self.stage_transition():
                break
            if not self.is_running:  # 任务已被标记为停止, 需要退出循环
                break
            self.shopping()
            self.harvest_crystals()
            self.get_in_hand_area(True)  # 更新手牌信息

            run_times += 1
            if run_times % 3 == 0:  # 每3轮更新一次场上角色，顺便穿戴装备
                self.refresh_character()
                self.sort_all_areas_by_priority()  # 优先级排序
        # 任务结束，重置角色状态
        self.reset_character()

    def refresh_character(self):
        """ 刷新角色信息，确保手牌中未放置的角色状态正确。 """
        self.get_on_field_area(True)
        self.operator.sleep(0.3)
        self.get_off_field_area(True)
        self.operator.sleep(0.3)
        on_off_field_characters = self.on_field_character + self.off_field_character
        for c in self.in_hand_character:
            if c is not None and c not in on_off_field_characters:
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

    def _get_character_in_area(self, areas, target_character_list, force=False, equip=False):
        """
        通用方法：获取指定区域的角色信息
        :param areas: 区域坐标列表（如 off_field_area）
        :param target_character_list: 目标角色列表（如 off_field_character，将被更新）
        :param force: 强制更新角色信息，默认False（即已有角色则跳过）
        :param equip: 是否顺便穿戴装备
        :return: 更新后的角色列表
        """
        # 默认OCR区域（如果未指定）
        ocr_from_x, ocr_from_y, ocr_to_x, ocr_to_y = (0.775, 0.175, 0.880, 0.2315)

        for index, area in enumerate(areas):
            try:
                # 点击区域（带延迟，确保界面响应）
                if target_character_list[index] is not None and not force:
                    continue  # 已有角色则跳过
                self.operator.click_point(*area, after_sleep=0.2)

                # OCR识别角色名称
                character_names = self.operator.ocr(
                    from_x=ocr_from_x,
                    from_y=ocr_from_y,
                    to_x=ocr_to_x,
                    to_y=ocr_to_y
                )

                # 更新角色列表
                if character_names and len(character_names) > 0:
                    name = ''
                    for char_name in character_names:
                        name += char_name[1]
                    target_character_list[index] = get_character(name)
                    if equip:
                        self.operator.click_img(CWIMG.EQUIPMENT_RECOMMEND, after_sleep=1)
                        _, box = self.operator.locate_any([CWIMG.EQUIP, CWIMG.SYNTHESIS], confidence=0.8)
                        if box:
                            self.operator.click_box(box, after_sleep=0.5)
                else:
                    target_character_list[index] = None  # 未识别到角色

                self.operator.click_point(0.5, 0.5)  # 点击空白处关闭信息框

            except Exception as e:
                # 捕获点击或OCR异常（如坐标错误、识别失败）
                logger.error(f"获取区域[{index}]角色失败：{str(e)}")
                target_character_list[index] = None  # 异常时标记为空

        return target_character_list

    def get_off_field_area(self, force=False):
        """获取场下角色信息"""
        self._get_character_in_area(areas=self.off_field_area, target_character_list=self.off_field_character,
                                    equip=True,
                                    force=force)
        for char in self.off_field_character:
            if char is not None:
                char.is_placed = True
        logger.info(f"当前场下角色：{self.off_field_character}")

    def get_on_field_area(self, force=False):
        """获取场上角色信息"""
        self._get_character_in_area(areas=self.on_field_area, target_character_list=self.on_field_character,
                                    equip=True,
                                    force=force)
        for char in self.on_field_character:
            if char is not None:
                char.is_placed = True
        logger.info(f"当前场上角色：{self.on_field_character}")

    def get_in_hand_area(self, force=False):
        """获取手牌角色信息"""
        target = self.operator.locate(CWIMG.OPEN)
        while target:
            self.operator.mouse_down(target.center[0], target.center[1])
            self.operator.mouse_up()
            self.operator.sleep(0.5)
            self.operator.click_point(0.35, 0.20, after_sleep=0.5)
            target = self.operator.locate(CWIMG.OPEN)
        self._get_character_in_area(areas=self.in_hand_area, target_character_list=self.in_hand_character, force=force)
        logger.info(f"当前手牌角色：{self.in_hand_character}")

    def place_character(self) -> bool:
        """
        将手中的角色放置到场上或场下（严格先放前台角色，再放后台角色，确保前台优先占位）
        队伍不满时优先放空位，队伍满时仅替换低priority角色
        :return: 至少有一个角色放置成功返回 True，否则返回 False
        """
        # 第一次遍历：仅处理前台角色（Positioning.OnField / OnOffField），优先占满编队
        logger.info("=== 放置前台角色 ===")
        for i, character in enumerate(self.in_hand_character):
            if character is None or character.is_placed:
                continue
            if character.position != Positioning.OffField:
                if self.place_on_field_character(i):
                    self.operator.sleep(1)
                    self.handle_special_event()

        # 第二次遍历：仅处理后台角色（Positioning.OffField），填充剩余空位或替换
        logger.info("=== 放置后台角色 ===")
        for i, character in enumerate(self.in_hand_character):
            if character is None or character.is_placed:
                continue
            if character.position != Positioning.OnField:
                if self.place_off_field_character(i):
                    self.operator.sleep(1)
                    self.handle_special_event()

        logger.info("角色放置完成")
        return True

    def place_on_field_character(self, character_in_hand: int) -> bool:
        """将手中的角色放置到场上（前台角色专用，优先占位）"""
        return self._place_to_target(
            character_in_hand,
            target_characters=self.on_field_character,
            area_type="前台"
        )

    def place_off_field_character(self, character_in_hand: int) -> bool:
        """将手中的角色放置到场下（后台角色专用）"""
        return self._place_to_target(
            character_in_hand,
            target_characters=self.off_field_character,
            area_type="后台"
        )

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
            logger.error(f"无效的手牌索引：{character_in_hand}（范围：0~{len(self.in_hand_character) - 1}）")
            return False

        character = self.in_hand_character[character_in_hand]
        if not character or character.is_placed:
            logger.warning(f"手牌索引 {character_in_hand} 无有效角色或角色已放置")
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
        min_priority = character.priority
        min_priority_index = -1
        # 查找目标区域中priority最低的角色
        for index, existing_char in enumerate(target_characters):
            if existing_char is not None and existing_char.priority < min_priority:
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

    def harvest_crystals(self):
        # 实现水晶收集逻辑
        self.operator.drag_to(0.68, 0.18, 0.82, 0.18)
        self.operator.sleep(0.3)
        self.operator.drag_to(0.68, 0.25, 0.82, 0.25)
        self.operator.sleep(0.3)
        self.operator.drag_to(0.68, 0.30, 0.83, 0.30)
        self.operator.sleep(0.3)
        self.operator.drag_to(0.68, 0.35, 0.84, 0.35)
        self.operator.sleep(0.3)
        self.operator.drag_to(0.68, 0.40, 0.83, 0.40)
        self.operator.sleep(0.3)

    def sell_character(self):
        """
        实现角色出售逻辑，确保手牌不超过8个角色
        :return: bool - 出售操作是否成功
        """
        max_attempts = 5
        attempt = 0

        while attempt < max_attempts:
            if self.in_hand_character_count < 8:
                logger.info("手牌未满，跳过出售角色")
                return True
            logger.info("手牌已满，尝试出售角色")
            self.handle_sell_character()
            self.get_in_hand_area()  # 检测空位，确保没有新插入的角色
            attempt += 1

        # 超过最大尝试次数仍未成功出售时的逻辑
        logger.warning(f"已尝试{max_attempts}次出售角色，手牌仍为满状态，将强制执行出售")
        self.handle_sell_character(force=True)
        self.get_in_hand_area()  # 最后更新手牌状态

        if self.in_hand_character_count < 8:
            logger.info("强制出售角色成功")
            return True
        else:
            logger.error("强制出售角色失败，手牌仍为满状态")
            return False

    def handle_sell_character(self, force=False):
        """
        角色出售逻辑
        :param force: bool - 是否强制出售所有角色（包括已放置的角色）
        """
        # 创建需要出售的角色索引列表
        characters_to_sell = []
        for i, character in enumerate(self.in_hand_character):
            if character is None:
                continue
            if force:
                characters_to_sell.append((i, character))
            elif not character.is_placed:
                characters_to_sell.append((i, character))
        
        # 执行出售操作 - 使用通用对换方法（商店区域没有角色列表）
        for i, character in characters_to_sell:
            # 由于商店区域没有角色列表，直接执行拖拽
            sell_area = (0.05, 0.86)  # 出售区域
            source = self.in_hand_area[i]
            self.operator.drag_to(source[0], source[1], sell_area[0], sell_area[1])
            # 更新手牌状态
            self.in_hand_character[i] = None
            if character:
                character.is_placed = False
            logger.info(f"已出售角色：{character.name}")
            self.operator.sleep(0.5)
        logger.info("出售操作完成")

    def battle(self) -> bool:
        # self.operators.click_point(0.907, 0.714, after_sleep=1)
        battle_box = self.operator.wait_img(CWIMG.BATTLE, timeout=3, interval=0.5)
        if battle_box is None or not self.operator.click_box(battle_box, after_sleep=1.5):
            logger.error("未识别到战斗按钮")
            return False
        if self.operator.locate(IMG.ENSURE):  # 编队未满提醒
            self.operator.click_img(IMG.ENSURE)
        result, _ = self.operator.wait_any_img([CWIMG.SETTLE, CWIMG.CONTINUE], timeout=600, interval=1)
        if result != -1:
            logger.info("挑战结束")
            self.operator.sleep(0.5)
            return self.operator.click_point(0.5, 0.824, after_sleep=1)  # 点击继续按钮
        else:
            logger.warning("等待挑战结束超时")
            return False

    def stage_transition(self):
        """实现关卡切换逻辑，通过识别图片状态执行对应操作"""
        # 定义状态配置：(图片路径, 状态名称, 处理函数, 是否为终止状态)
        stage_config = [
            (
                CWIMG.FORTUNE_TELLER,
                '命运卜者',
                lambda: [
                    self.operator.click_point(0.8, 0.3, after_sleep=1),  # 选择第三个选项
                    self.operator.click_point(0.77, 0.521, after_sleep=1),  # 点击确认按钮
                    self.operator.click_point(0.8438, 0.8481, after_sleep=1)  # 打开商店界面
                ],
                False  # 非终止状态
            ),
            (
                CWIMG.REPLENISH_STAGE,
                '补给节点',
                lambda: [
                    self.operator.click_point(0.53, 0.52, after_sleep=1),  # 选择固定位置
                    self.operator.click_point(0.88, 0.91, after_sleep=1)  # 点击确认按钮
                ],
                False  # 非终止状态
            ),
            (
                CWIMG.ENCOUNTER_NODE,
                '遭遇节点',
                lambda: [
                    self.operator.click_point(0.35, 0.50, after_sleep=1),  # 简单难度
                    self.operator.click_point(0.50, 0.84, after_sleep=1)  # 点击确认钮
                ],
                False
            ),
            (
                CWIMG.FOLD,
                '无',
                None,  # 目标状态，无需处理
                True  # 正常终止状态
            ),
            (
                CWIMG.SELECT_INVEST_STRATEGY,
                '选择投资策略',
                lambda: [
                    # 当外部接管策略页时，停止 CW 循环并不进行点击，由外层流程处理。
                    setattr(self, 'is_running', False)
                ] if self.strategy_external_control else [
                    self.operator.click_point(0.5, 0.68, after_sleep=1),  # 选择中间策略
                    self.operator.click_point(0.5, 0.9, after_sleep=1)  # 点击确认按钮
                ],
                False
            ),
            (
                CWIMG.CLICK_BLANK,
                '强敌来袭',
                lambda: [self.operator.click_point(0.5, 0.70, after_sleep=1)],
                False
            ),
            (
                CWIMG.NEXT_STEP,
                '游戏结束',
                lambda: [
                    self.operator.click_img(CWIMG.NEXT_STEP, after_sleep=1),
                    self.operator.click_point(0.5, 0.82, after_sleep=1),
                    self.operator.click_point(0.5, 0.82, after_sleep=1),
                    setattr(self, 'is_running', False)  # 停止运行标志
                ],
                True  # 挑战结束，终止状态
            )
        ]

        img_list = [cfg[0] for cfg in stage_config]

        # 等待初始状态
        stage_index, _ = self.operator.wait_any_img(img_list, timeout=30, interval=1)
        self.operator.sleep(1.5)

        while True:  # 用无限循环 + 内部break控制退出
            # 若被外部标记停止（例如策略页外部接管），立刻退出切换流程
            if not self.is_running:
                logger.info("检测到 is_running=False，退出关卡切换流程")
                return True
            # 检查是否超时（未识别到任何状态）
            if stage_index == -1:
                logger.error("关卡状态检测超时，未识别到任何图片")
                raise RuntimeError("关卡切换检测超时")

            # 获取当前状态配置
            img_path, stage_name, handle_func, is_terminal = stage_config[stage_index]
            logger.info(f"检测到状态：{stage_name}({img_path})")

            # 执行状态处理函数
            if handle_func is not None:
                try:
                    actions = handle_func()
                    if actions:
                        for _ in actions:
                            pass  # 操作已在lambda中执行
                    logger.info(f"状态 {stage_name} 处理完成")
                except Exception as e:
                    logger.error(f"处理状态 {stage_name} 时出错: {e}")
                    raise

            # 若当前为策略页且启用了外部接管，则立即退出切换流程
            if img_path == CWIMG.SELECT_INVEST_STRATEGY and self.strategy_external_control:
                logger.info("策略页外部接管生效，退出关卡切换流程")
                return True

            # 若当前是终止状态，直接退出循环
            if is_terminal:
                logger.info(f"达到终止状态：{stage_name}，退出关卡切换流程")
                return True

            # 非终止状态，继续等待下一个状态
            stage_index, _ = self.operator.wait_any_img(img_list, timeout=30, interval=1)
            self.operator.sleep(1.5)

    def handle_special_event(self):
        event, _ = self.operator.locate_any([
            CWIMG.THE_PLANET_OF_FESTIVITIES,
            CWIMG.FORTUNE_TELLER,
        ])
        if event == 0:  # 盛会之星事件
            self.operator.click_point(0.5, 0.25, after_sleep=1)  # 选择第一个选项
            self.operator.click_point(0.77, 0.521, after_sleep=1)  # 点击确认按钮
            return self.handle_special_event()  # 可能连续触发事件，递归处理
        elif event == 1:  # 命运卜者事件
            logger.info("触发命运卜者事件")
            self.operator.click_point(0.8, 0.3, after_sleep=1)  # 选择第三个选项
            self.operator.click_point(0.77, 0.521, after_sleep=1)  # 点击确认按钮
            return self.handle_special_event()  # 可能连续触发事件，递归处理
        else:
            # 未检测到特殊事件，正常返回
            return True

    def strategy_event(self):
        """处理攻略事件"""
        self.operator.click_img(CWIMG.RIGHT, after_sleep=2)  # 装备合成
        self.operator.click_point(0.5, 0.5, after_sleep=0.5)

    def shopping(self):
        def scan_characters_in_store() -> list[Character]:
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
                if name.isdecimal(): # 跳过价格识别结果
                    continue
                if '备' in name:  # 备战席已满
                    return []
                char = get_character(name)
                if char is not None:
                    chars.append(char)
                    logger.info(f"商店中发现角色：{char.name}，P: {char.priority}")
                else:
                    logger.info(f"商店中发现未知角色：{name}")
            return chars

        while True:
            purchased = False
            coins = self.get_coins()
            if coins < 4:
                break
            level = self.get_level()

            if not self.is_overclock and coins < self.min_coins:
                logger.info(f"当前金币 {coins} 小于最低保留数量 {self.min_coins}")
                break
            if level < self.min_level:
                # 当等级小于最低等级要求时，持续按f提升等级，跳过购买
                self.operator.press_key('f')
                self.operator.sleep(0.5)
                continue
            cs = scan_characters_in_store()
            if len(cs) != 0:
                for i, c in enumerate(cs):
                    if c.name in self.strategy_characters.keys():  # 如果角色在攻略中出现
                        if self.strategy_characters[c.name] <= 0:
                            continue  # 如果该角色已达购买上限则跳过
                        target = self.store_area[i]
                        self.operator.click_point(*target, after_sleep=0.5)
                        purchased = True # 标记购买了角色
                        self.strategy_characters[c.name] -= 1  # 购买次数减一
                        self.operator.move_to(0.5, 0.5)  # 移动鼠标避免遮挡

            self.operator.press_key('d')  # 按d刷新商店
            self.operator.sleep(0.5)
            if level < self.mid_level and not purchased:
                # 当等级小于中级等级要求且未购买任何角色时，按f提升等级
                self.operator.press_key('f')
                self.operator.sleep(0.5)
        self.operator.click_point(0.5, 0.55, after_sleep=1.5)  # 点击空白处关闭商店

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
        """获取当前手牌角色数量"""
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
        if ".json" in name:
            path = name
        else:
            path = f"tasks/currency_wars/strategies/{name}.json"
        with open(path, "r", encoding="utf-8") as f:
            strategy_data: dict[str, Any] = json.load(f)
        strategy_name = strategy_data.get("name")
        description = strategy_data.get("description")
        self.min_coins = strategy_data.get("min_coins", 40)
        self.min_level = strategy_data.get("min_level", 7)
        self.mid_level = strategy_data.get("mid_level", 7)
        # 在攻略中的角色设置成最高优先级
        strategy_on_field: dict[str,int] = strategy_data.get("on_field", {})
        strategy_off_field: dict[str,int] = strategy_data.get("off_field", {})
        for i, cn in enumerate(strategy_on_field.keys()):
            c = get_character(cn)
            if c is None:
                logger.warning(f"攻略角色不存在，跳过：{cn}")
                continue
            c.priority = 99 - i  # 确保攻略中的前台角色优先级都大于其他角色，同时有所差别
            c.position = Positioning.OnField
            self.strategy_characters[cn] = strategy_on_field[cn]
        for i, cn in enumerate(strategy_off_field):
            c = get_character(cn)
            if c is None:
                logger.warning(f"攻略角色不存在，跳过：{cn}")
                continue
            c.priority = 99 - i  # 确保攻略中的后台角色优先级都大于其他角色
            c.position = Positioning.OffField
            self.strategy_characters[cn] = strategy_off_field[cn]
        logger.info(f"已加载攻略: {strategy_name}: {description}")

    def unload_strategy(self):
        """卸载当前攻略，重置角色"""
        for c in cw_chars.characters.values():
            c.reset()
        self.min_coins = 40
        self.min_level = 7
        self.mid_level = 7
        self.strategy_characters.clear()
        logger.info("已卸载当前攻略，角色优先级已重置")

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
            'on_field': (self.on_field_character, self.on_field_area, "场上"),
            'off_field': (self.off_field_character, self.off_field_area, "场下"),
            'in_hand': (self.in_hand_character, self.in_hand_area, "手牌")
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
            logger.error(f"源区域索引超出范围: {source_index} (0~{len(source_coords)-1})")
            return False
        if not (0 <= target_index < len(target_coords)):
            logger.error(f"目标区域索引超出范围: {target_index} (0~{len(target_coords)-1})")
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
        self.operator.drag_to(source_coord[0], source_coord[1], target_coord[0], target_coord[1])
        self.operator.sleep(0.5)  # 等待操作完成
        
        # 交换角色列表中的内容
        source_chars[source_index], target_chars[target_index] = target_chars[target_index], source_chars[source_index]
        
        # 更新角色的放置状态
        if source_char:
            source_char.is_placed = (target_area_type != 'in_hand')
        if target_char:
            target_char.is_placed = (source_area_type != 'in_hand')
        
        logger.info(f"对换操作完成: {source_name}[{source_index}] <-> {target_name}[{target_index}]")
        return True

    def swap_field_and_hand_character(self, field_index: int, hand_index: int) -> bool:
        """
        示例方法：交换场上和手牌区的角色
        
        :param field_index: 场上角色的索引 (0-3)
        :param hand_index: 手牌角色的索引 (0-8)
        :return: 交换是否成功
        """
        return self.swap_character_between_areas(
            source_area_type='on_field',
            source_index=field_index,
            target_area_type='in_hand',
            target_index=hand_index
        )

    def swap_field_and_offfield_character(self, field_index: int, offfield_index: int) -> bool:
        """
        示例方法：交换场上和场下区的角色
        
        :param field_index: 场上角色的索引 (0-3)
        :param offfield_index: 场下角色的索引 (0-5)
        :return: 交换是否成功
        """
        return self.swap_character_between_areas(
            source_area_type='on_field',
            source_index=field_index,
            target_area_type='off_field',
            target_index=offfield_index
        )

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
            area_name = "场上"
        else:  # off_field
            characters = self.off_field_character
            area_name = "场下"
        
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
            target_current_info = None
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
