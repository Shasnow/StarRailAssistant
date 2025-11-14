from loguru import logger

from SRACore.util.operator import Executable
from tasks.currency_wars.characters import Character, Positioning, get_character


class CurrencyWars(Executable):
    def __init__(self, run_times):
        super().__init__()
        self.run_times = run_times
        self.force_battle = False
        self.on_field_character: list[Character | None] = [None, None, None, None]  # 场上角色列表
        self.on_field_area: list[tuple[float, float]] = [
            (0.386, 0.365),
            (0.464, 0.365),
            (0.536, 0.365),
            (0.611, 0.365)
        ]
        self.off_field_character: list[Character | None] = [None, None, None, None, None, None]  # 场下角色列表
        self.off_field_area: list[tuple[float, float]] = [
            (0.3156, 0.620),
            (0.3906, 0.620),
            (0.4625, 0.620),
            (0.5364, 0.620),
            (0.6104, 0.620),
            (0.6838, 0.620)
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
        self.faction_tendency = {}  # 阵营倾向字典
        self.school_tendency = {}  # 派系倾向字典
        self.is_running = False

    def run(self):
        if self.run_times == 0:
            return True
        for _ in range(self.run_times):
            self.start_game()
            self.run_game()
        return True

    def page_locate(self) -> int:
        """
        定位到货币战争页面
        :return: int 页面编号，1表示货币战争开始页面，2表示准备阶段页面，-1表示定位失败
        """
        page = self.wait_any_img(["resources/img/enter.png",
                                  "resources/img/currency_wars/currency_wars_start.png",
                                  "resources/img/currency_wars/preparation_stage.png"], interval=0.5)
        if page == 0:
            self.press_key('f4')
            if not self.wait_img("resources/img/f4.png", timeout=20):
                logger.error("检测超时，编号1")
                self.press_key("esc")
            self.click_point(0.3125, 0.20, after_sleep=0.8)  # 旷宇纷争
            self.click_point(0.242, 0.30, after_sleep=0.8)  # 货币战争
            self.click_point(0.7786, 0.8194, after_sleep=1)  # 前往参与
            return 1
        elif page == 1:
            return 1
        elif page == 2:
            return 2
        else:
            logger.error("检测超时")
            return -1

    def start_game(self):
        # 实现游戏开始逻辑
        page = self.page_locate()
        self.is_running=True # 标记任务为运行中
        if page == 1: # 货币战争开始页面
            # 进入对局逻辑
            box = self.wait_img("resources/img/currency_wars/currency_wars_start.png", timeout=30, interval=0.5)
            if not self.click_box(box):
                return False
            box = self.wait_img("resources/img/currency_wars/enter_standard.png", interval=0.5)
            if not self.click_box(box, after_sleep=1.5):
                return False
            while self.click_img("resources/img/currency_wars/down_arrow.png", after_sleep=0.5):
                pass
            if not self.click_img("resources/img/currency_wars/start_game.png", after_sleep=1):
                return False
            box = self.wait_img("resources/img/currency_wars/next_step.png")
            self.sleep(0.5)
            if not self.click_box(box, after_sleep=2):
                return False
            self.click_point(0.5,0.5, after_sleep=0.5)
            box = self.wait_img("resources/img/currency_wars/invest_environment.png")
            if box is None:
                return False
            if not self.click_img("resources/img/collection.png"):
                self.click_point(0.5, 0.5)
            self.click_img("resources/img/ensure2.png", after_sleep=1)
            if self.locate("resources/img/currency_wars/invest_environment.png"):  # 防止出现二连选择
                self.click_point(0.5, 0.5)
                self.click_img("resources/img/ensure2.png", after_sleep=1)
            self.sleep(4)
        elif page == -1:
            return False
        # 已进入对局
        box=self.wait_img('resources/img/currency_wars/strategy.png', timeout=60)
        if not self.click_box(box, after_sleep=1.5):
            return False
        self.click_img('resources/img/currency_wars/apply.png', after_sleep=1)
        self.press_key('esc')
        self.sleep(1)
        for _ in range(3):
            self.click_img('resources/img/currency_wars/trace.png', after_sleep=0.3)
        self.press_key('esc')
        self.get_in_hand_area()  # 更新手牌信息
        return True

    def run_game(self):
        run_times = 0
        while self.is_running:
            self.strategy_event()
            self.update_max_team_size()
            if self.place_character():
                self.sleep(0.5)
                self.special_event()
            self.sell_character()
            if self.battle():
                self.stage_transition()
                if not self.is_running: # 任务已被标记为停止, 需要退出循环
                    break
                self.shopping()
                self.harvest_crystals()
                self.get_in_hand_area(True)  # 更新手牌信息
            else:
                self.refresh_character()
                self.force_battle = True
            run_times += 1
            if run_times % 5 == 0:
                self.refresh_character()

    def refresh_character(self):
        self.get_on_field_area(True)
        self.sleep(0.3)
        self.get_off_field_area(True)
        self.sleep(0.3)
        on_off_field_characters = self.on_field_character + self.off_field_character
        for c in self.in_hand_character:
            if c not in on_off_field_characters:
                c.is_placed = False


    @property
    def coins(self):
        # 实现获取金币逻辑
        logger.info("获取当前金币数量")
        coins = self.ocr(from_x=0.84, from_y=0.81, to_x=0.89, to_y=0.89)
        if coins:
            return int(coins[0][1])
        else:
            return 0

    def _get_character_area(self, areas, target_character_list, force=False, click_delay=0.2):
        """
        通用方法：获取指定区域的角色信息
        :param areas: 区域坐标列表（如 off_field_area）
        :param target_character_list: 目标角色列表（如 off_field_character，将被更新）
        :param force: 强制更新角色信息，默认False（即已有角色则跳过）
        :param click_delay: 点击后等待延迟（秒），默认0.2秒
        :return: 更新后的角色列表
        """
        # 默认OCR区域（如果未指定）
        ocr_from_x, ocr_from_y, ocr_to_x, ocr_to_y = (0.775, 0.175, 0.880, 0.2315)

        for index, area in enumerate(areas):
            try:
                # 点击区域（带延迟，确保界面响应）
                if target_character_list[index] is not None and not force:
                    continue  # 已有角色则跳过
                self.click_point(*area, after_sleep=click_delay)

                # OCR识别角色名称
                character_names = self.ocr(
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
                else:
                    target_character_list[index] = None  # 未识别到角色

                self.click_point(0.5, 0.5)  # 点击空白处关闭信息框

            except Exception as e:
                # 捕获点击或OCR异常（如坐标错误、识别失败）
                logger.error(f"获取区域[{index}]角色失败：{str(e)}")
                target_character_list[index] = None  # 异常时标记为空

        return target_character_list

    def get_off_field_area(self, force=False):
        """获取场下角色信息"""
        self._get_character_area(
            areas=self.off_field_area,
            force=force,
            target_character_list=self.off_field_character
        )
        for char in self.off_field_character:
            if char is not None:
                char.is_placed = True
        logger.info(f"当前场下角色：{self.off_field_character}")

    def get_on_field_area(self, force=False):
        """获取场上角色信息"""
        self._get_character_area(
            areas=self.on_field_area,
            target_character_list=self.on_field_character,
            force=force
        )
        for char in self.on_field_character:
            if char is not None:
                char.is_placed = True
        logger.info(f"当前场上角色：{self.on_field_character}")

    def get_in_hand_area(self, force=False):
        """获取手牌角色信息"""
        target = self.locate('resources/img/currency_wars/open.png')
        while target:
            self.mouse_down(int(target.center[0]), int(target.center[1]))
            self.mouse_up()
            self.sleep(0.5)
            self.click_point(0.35, 0.20, after_sleep=0.5)
            target = self.locate('resources/img/currency_wars/open.png')
        self._get_character_area(
            areas=self.in_hand_area,
            target_character_list=self.in_hand_character,
            force=force
        )
        logger.info(f"当前手牌角色：{self.in_hand_character}")

    def place_character(self) -> bool:
        """
        将手中的角色放置到场上或场下（严格先放前台角色，再放后台角色，确保前台优先占位）
        队伍不满时优先放空位，队伍满时仅替换低cost角色
        :return: 至少有一个角色放置成功返回 True，否则返回 False
        """
        # 第一次遍历：仅处理前台角色（Positioning.OnField / OnOffField），优先占满编队
        logger.info("=== 放置前台角色 ===")
        for i, character in enumerate(self.in_hand_character):
            if character is None or character.is_placed:
                continue
            if character.positioning != Positioning.OffField:
                if self.place_on_field_character(i):
                    self.sleep(0.5)

        # 第二次遍历：仅处理后台角色（Positioning.OffField），填充剩余空位或替换
        logger.info("=== 放置后台角色 ===")
        for i, character in enumerate(self.in_hand_character):
            if character is None or character.is_placed:
                continue
            if character.positioning != Positioning.OnField:
                if self.place_off_field_character(i):
                    self.sleep(0.5)

        logger.info("角色放置完成")
        return True

    def place_on_field_character(self, character_in_hand: int) -> bool:
        """将手中的角色放置到场上（前台角色专用，优先占位）"""
        return self._place_to_target(
            character_in_hand,
            target_characters=self.on_field_character,
            target_areas=self.on_field_area,
            area_type="场上（前台）"
        )

    def place_off_field_character(self, character_in_hand: int) -> bool:
        """将手中的角色放置到场下（后台角色专用）"""
        return self._place_to_target(
            character_in_hand,
            target_characters=self.off_field_character,
            target_areas=self.off_field_area,
            area_type="场下（后台）"
        )

    def _place_to_target(
            self,
            character_in_hand: int,
            target_characters: list[Character],
            target_areas,
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

        # 2. 队伍不满时：优先填充空位（前台角色优先占名额）
        if not full_team:
            for index, existing_char in enumerate(target_characters):
                if existing_char is None:
                    # 执行拖拽放置
                    source = self.in_hand_area[character_in_hand]
                    target = target_areas[index]
                    self.drag(source[0], source[1], target[0], target[1])
                    # 更新角色状态和队伍人数
                    target_characters[index] = character
                    character.is_placed = True
                    self.in_hand_character[character_in_hand] = None
                    logger.info(
                        f"角色 {character.name} 放置到{area_type}索引 {index}（空位）")
                    return True
            logger.info(f"{area_type}无空位可放置")

        # 3. 队伍已满时：仅替换低cost角色（不占用新名额）
        min_cost = character.cost
        min_cost_index = -1
        # 查找目标区域中cost最低的角色
        for index, existing_char in enumerate(target_characters):
            if existing_char is not None and existing_char.cost < min_cost:
                min_cost = existing_char.cost
                min_cost_index = index

        if min_cost_index != -1:
            existing_char = target_characters[min_cost_index]
            # 执行替换
            source = self.in_hand_area[character_in_hand]
            target = target_areas[min_cost_index]
            self.drag(source[0], source[1], target[0], target[1])
            # 更新角色状态（队伍人数不变）
            self.in_hand_character[character_in_hand] = existing_char
            existing_char.is_placed = False
            target_characters[min_cost_index] = character
            character.is_placed = True
            logger.info(
                f"角色 {character.name} 替换{area_type}索引 {min_cost_index} 的 {existing_char.name} "
                f"（cost {existing_char.cost} → {character.cost}）"
            )
            return True

        logger.info(f"{area_type}无低cost角色可替换")
        return False

    def harvest_crystals(self):
        # 实现水晶收集逻辑
        self.drag(0.68, 0.18, 0.82, 0.18)
        self.sleep(0.3)
        self.drag(0.68, 0.25, 0.82, 0.25)
        self.sleep(0.3)
        self.drag(0.68, 0.30, 0.82, 0.30)
        self.sleep(0.3)
        self.drag(0.68, 0.35, 0.82, 0.35)
        self.sleep(0.3)
        self.drag(0.68, 0.40, 0.82, 0.40)
        self.sleep(0.3)

    def sell_character(self):
        # 实现角色出售逻辑
        if self.in_hand_character_count < 9:
            logger.info("手牌未满，跳过出售角色")
            return

        sell_area = (0.05, 0.86)  # 出售区域
        for i, c in enumerate(self.in_hand_character):
            if c is None or c.is_placed:
                continue
            source = self.in_hand_area[i]
            self.drag(source[0], source[1], sell_area[0], sell_area[1])
            self.in_hand_character[i] = None
            logger.info(f"出售角色：{c.name}")
            self.sleep(0.5)

    def battle(self) -> bool:
        self.click_point(0.907, 0.714, after_sleep=1)
        if self.locate('resources/img/ensure.png'):  # 编队未满提醒
            if self.force_battle:
                self.click_img('resources/img/ensure.png')
            else:
                self.press_key('esc')
                self.sleep(0.5)
                return False
        self.force_battle = False
        result = self.wait_any_img(['resources/img/currency_wars/settle.png','resources/img/currency_wars/continue.png'], interval=1,timeout=600)
        if result!=-1:
            logger.info("挑战结束")
            self.sleep(0.5)
            return self.click_point(0.5, 0.824, after_sleep=0.3)  # 点击继续按钮
        else:
            logger.warning("等待挑战结束超时")
            return False

    def stage_transition(self):
        # 实现关卡切换逻辑
        stage = self.wait_any_img([
            'resources/img/currency_wars/replenish_stage.png',
            'resources/img/currency_wars/encounter_node.png',
            'resources/img/currency_wars/fold.png',
            'resources/img/currency_wars/select_invest_strategy.png',
            'resources/img/currency_wars/click_blank.png',
            'resources/img/currency_wars/next_step.png'
        ], timeout=20, interval=1)
        self.sleep(1.5)
        if stage == 0:  # 补给节点
            self.click_point(0.53, 0.52, after_sleep=1)  # 这里应该实现其他选择逻辑, 目前选择固定位置
            self.click_point(0.88, 0.91, after_sleep=1)  # 点击确认按钮
            self.wait_img('resources/img/currency_wars/fold.png', timeout=30)  # 等待刷新界面出现
            return True
        elif stage == 1:  # 遭遇节点
            self.click_point(0.35, 0.50, after_sleep=1)  # 简单难度
            self.click_point(0.50, 0.84, after_sleep=1)  # 点击确认钮
            self.wait_img('resources/img/currency_wars/fold.png', timeout=30)  # 等待刷新界面出现
            return True
        elif stage == 2:  # 刷新界面
            return True
        elif stage == 3:  # 选择投资策略界面
            self.click_point(0.5, 0.68, after_sleep=1)  # 选择中间策略
            self.click_point(0.5, 0.9, after_sleep=1)  # 点击确认按钮
            self.wait_img('resources/img/currency_wars/fold.png', timeout=30)
            return True
        elif stage == 4:  # 点击空白处关闭
            self.click_point(0.5, 0.70, after_sleep=1)
            self.wait_img('resources/img/currency_wars/fold.png', timeout=30)
            return True
        elif stage == 5:  # 挑战结束
            self.click_point(0.5, 0.82, after_sleep=1)
            self.click_point(0.5, 0.82, after_sleep=1)
            self.click_point(0.5, 0.82, after_sleep=1)
            self.is_running = False
            return True
        else:
            logger.error("检测超时")
            raise RuntimeError("关卡切换检测超时")

    def special_event(self):
        event, _ = self.locate_any(
            ['resources/img/currency_wars/ThePlanetOfFestivities.png', 'resources/img/currency_wars/right.png'])
        if event == 0:  # 盛会之星事件
            self.click_point(0.5, 0.25, after_sleep=1)  # 选择第一个选项
            self.click_point(0.77, 0.52, after_sleep=1)  # 点击确认按钮

    def strategy_event(self):
        self.click_img('resources/img/currency_wars/right.png', after_sleep=2)
        self.click_point(0.5, 0.5, after_sleep=0.5)

    def shopping(self):
        def scan_characters_in_store() -> list[Character]:
            results = self.ocr(from_x=0.19, from_y=0.26, to_x=0.88, to_y=0.31)
            chars = []
            for i in range(0, len(results), 2):
                name = results[i][1]
                if '备战席已满' in name:
                    return []
                c = get_character(name)
                if c is not None:
                    chars.append(c)
                    logger.info(f"商店中发现角色：{c.name}，Cost: {c.cost}")
                else:
                    logger.info(f"商店中发现未知角色：{name}")
            return chars

        while self.coins > 40:
            if self.in_hand_character_count == 9:
                break

            if self.level < 7:
                self.press_key('f')
                self.sleep(0.5)
                continue
            cs = scan_characters_in_store()
            if len(cs) != 0:
                for i, c in enumerate(cs):
                    if c in self.on_field_character + self.off_field_character:
                        target = self.store_area[i]
                        self.click_point(*target, after_sleep=0.5)

            primary_selection = self.locate('resources/img/currency_wars/primary_selection.png')
            for _ in range(5):
                if primary_selection:
                    self.click_box(primary_selection, after_sleep=0.5)
                    primary_selection = self.locate('resources/img/currency_wars/primary_selection.png')
                else:
                    break

            self.press_key('d')  # 按d刷新商店
            self.sleep(0.5)
        self.click_point(0.5, 0.55)  # 点击空白处关闭商店

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

    @property
    def level(self):
        logger.info("获取当前等级")
        level = self.ocr(from_x=0.05, from_y=0.815, to_x=0.3, to_y=0.87)
        try:
            if level:
                return int(level[0][1].split('.')[1])
            else:
                return self.max_team_size
        except ValueError:
            return self.max_team_size

    def update_max_team_size(self):
        result = self.ocr(from_x=0.505, from_y=0.18, to_x=0.608, to_y=0.27)
        if result:
            try:
                self.max_team_size = int(result[-1][1])
                logger.info(f"最大队伍人数已更新为 {self.max_team_size}")
            except ValueError:
                logger.warning(f"无法解析最大队伍人数：{result[-1][1]}")

    def get_tendency(self):
        self.faction_tendency.clear()
        self.school_tendency.clear()
        for character in self.on_field_character + self.off_field_character:
            if character is None:
                continue
            if character.faction not in self.faction_tendency:
                self.faction_tendency[character.faction] = 0
            self.faction_tendency[character.faction] += 1
            for school in character.schools:
                if school not in self.school_tendency:
                    self.school_tendency[school] = 0
                self.school_tendency[school] += 1
        self.faction_tendency = {k: v for k, v in
                                 sorted(self.faction_tendency.items(), key=lambda item: item[1], reverse=True)}  # 排序
        self.school_tendency = {k: v for k, v in
                                sorted(self.school_tendency.items(), key=lambda item: item[1], reverse=True)}  # 排序
        logger.info(f"当前阵营倾向：{self.faction_tendency}")
        logger.info(f"当前派系倾向：{self.school_tendency}")
