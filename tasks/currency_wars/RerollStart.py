from SRACore.util.logger import logger
from tasks.img import CWIMG, IMG

from .CurrencyWars import CurrencyWars


class RerollStart(CurrencyWars):
    # Boss词条OCR区域（基于1920x1080截图坐标: 30,930-1200,1030）
    BOSS_AFFIX_FROM_X = 0.016
    BOSS_AFFIX_FROM_Y = 0.861
    BOSS_AFFIX_TO_X = 0.625
    BOSS_AFFIX_TO_Y = 0.954

    # Boss名称OCR区域（基于1920x1080截图坐标: 125,700-990,740）
    BOSS_NAME_FROM_X = 0.065
    BOSS_NAME_FROM_Y = 0.648
    BOSS_NAME_TO_X = 0.516
    BOSS_NAME_TO_Y = 0.685

    # 投资策略OCR区域（基于1920x1080截图坐标: 270,455-1650,510）
    INVEST_STRATEGY_OCR_FROM_X = 0.141
    INVEST_STRATEGY_OCR_FROM_Y = 0.421
    INVEST_STRATEGY_OCR_TO_X = 0.859
    INVEST_STRATEGY_OCR_TO_Y = 0.472

    # 投资环境OCR区域（基于1920x1080截图坐标: 235,360-1700,410）
    INVEST_ENV_OCR_FROM_X = 0.122
    INVEST_ENV_OCR_FROM_Y = 0.333
    INVEST_ENV_OCR_TO_X = 0.885
    INVEST_ENV_OCR_TO_Y = 0.380

    def __init__(self, operator, runtimes):
        super().__init__(operator, runtimes)
        self.reroll = False  # 重开标志
        self.wanted_invest_env = None  # 需要的投资环境
        self.optional_invest_env = None  # 可选的投资环境
        self.wanted_invest_strategies = None  # 各阶段需要的投资策略（列表，按阶段顺序）
        self.wanted_boss_names = None  # 需要的Boss名称
        self.wanted_boss_affixes = None  # 必须出现的boss词缀
        self.hate_boss_affixes = None  # 讨厌的boss词缀，出现就重开
        self.invest_strategy_stage = 0  # 投资策略阶段
        self.invest_strategy_satisfied = False  # 满意标志

    def handle_ending(self):
        # 刷开局不需要结束游戏
        pass

    @staticmethod
    def _normalize_ocr_text(text: str) -> str:
        return text.strip().replace("·", "").replace("•", "").replace("?", "").replace(" ", "")

    @staticmethod
    def _is_substring(a: str, b: str) -> bool:
        """Return True if `a` is a substring of `b`."""
        if not a or not b:
            return False
        return a in b

    def set_invest_env(self, invest_env: str):
        """设置投资环境"""
        invest_env_tokens = invest_env.split()
        self.wanted_invest_env = list()
        self.optional_invest_env = list()
        for item in invest_env_tokens:
            if item.startswith("?"):
                self.optional_invest_env.append(item[1:])
            else:
                self.wanted_invest_env.append(item)

    def set_invest_strategy(self, invest_strategy: str):
        """设置投资策略
        
        投资策略使用分号分隔，按照顺序分别对应阶段1、阶段2...
        留空表示该阶段无要求。
        例如：
        - "策略1;策略2"：阶段1需要策略1，阶段2需要策略2
        - ";策略2"：阶段1无要求，阶段2需要策略2
        - "策略1;"：阶段1需要策略1，阶段2无要求，阶段1满足后立即结束
        """
        if not invest_strategy:
            return
        # 使用分号分隔各阶段的投资策略要求
        stages = invest_strategy.replace("；", ";").split(";")
        # 去除末尾空字符串（如"策略1;"会分割为["策略1", ""]）
        while stages and stages[-1] == "":
            stages.pop()
        self.wanted_invest_strategies = [self._normalize_ocr_text(s) for s in stages]

    def set_boss_name(self, boss_names: str):
        """
        设置boss名称
        格式：第一位面;第二位面;第三位面
        """
        if not boss_names:
            return
        boss_name_tokens = boss_names.replace("；", ";").split(";") if boss_names else []
        normalized_boss_names = [self._normalize_ocr_text(item) for item in boss_name_tokens[:3]]
        while len(normalized_boss_names) < 3:
            normalized_boss_names.append("")
        self.wanted_boss_names = normalized_boss_names if any(normalized_boss_names) else None

    def set_boss_affix(self, boss_affix: str):
        """设置boss词缀"""
        if not boss_affix:
            return
        boss_affix_tokens = boss_affix.split() if boss_affix else []
        self.wanted_boss_affixes = list()
        self.hate_boss_affixes = list()
        for item in boss_affix_tokens:
            if item.startswith("!"):
                self.hate_boss_affixes.append(self._normalize_ocr_text(item[1:]))
            else:
                self.wanted_boss_affixes.append(self._normalize_ocr_text(item))

    def handle_boss_info(self) -> None:
        if self.wanted_boss_names:
            logger.info("检测到开局，正在识别Boss名称...")
            if not self._detect_boss_name():
                logger.info("Boss名称不符合要求，准备重开...")
                self.reroll = True

        if not self.reroll and (self.wanted_boss_affixes or self.hate_boss_affixes):
            logger.info("检测到开局，正在识别Boss词缀...")
            if not self._detect_boss_affix():
                logger.info("Boss词缀不符合要求，准备重开...")
                self.reroll = True
            else:
                logger.info("Boss词缀符合要求，继续游戏...")

    def handle_invest_environment(self) -> None:
        if not (self.wanted_invest_env or self.optional_invest_env):
            super().handle_invest_environment()
            return
        
        for _ in range(2):
            logger.info("正在识别投资环境...")
            result = self._detect_invest_env()
            if result != -1:
                self.operator.click_point(0.25 * (result + 1), 0.27, tag="投资环境")  # 根据投资环境的位置计算点击坐标，每个环境占屏幕宽度的25%
                self.operator.click_img(IMG.ENSURE2, after_sleep=1)
                logger.info("投资环境符合要求，继续游戏...")
                break
            
            logger.info("投资环境不符合要求，尝试刷新...")
            refresh_box = self.operator.locate(CWIMG.INVEST_ENV_REFRESH)
            if refresh_box is not None:
                self.operator.click_box(refresh_box, after_sleep=1)
            else:
                if self.wanted_invest_env:
                    logger.info("无法刷新，准备重开...")
                    self.reroll = True
                super().handle_invest_environment()

    def handle_game_entered(self) -> bool:
        if self.reroll:
            self.abort_and_return()
            self.reroll = False
            return False
        if not self.wanted_invest_strategies:
            # 如果不需要重开，且没有投资策略要求，可中止刷开局
            logger.info("已刷到满足要求的开局，停止刷开局")
            self.is_running = False
            return False
        # 检查当前阶段是否有投资策略要求，无要求则立即结束
        if self.invest_strategy_stage >= len(self.wanted_invest_strategies):
            logger.info("所有阶段投资策略已满足，停止刷开局")
            self.is_running = False
            return False
        return True

    def handle_invest_strategy(self):
        def default_invest_strategy_handler():
            if self.invest_strategy_stage >= len(self.wanted_invest_strategies):
                # 未匹配到投资策略需要重开时，直接重开，不进行选择和确定。
                logger.info(f"已达到投资策略阶段, 准备重开...")
                self.operator.click_img(CWIMG.BACK_PREPARE_PAGE, after_sleep=0.5)
                self.abort_and_return()
                self.invest_strategy_stage = 0  # 重置投资策略阶段计数器
                return
            if not self.operator.click_img(CWIMG.COLLECTION):  # 优先点击带有收集图标的策略
                self.operator.click_point(0.5, 0.27)  # 无法点击时，点击中心点
            self.operator.click_img(IMG.ENSURE2, after_sleep=1)  # 确认选择

        current_stage_index = self.invest_strategy_stage
        self.invest_strategy_stage += 1

        # 检查当前阶段是否有投资策略要求
        if not self.wanted_invest_strategies or current_stage_index >= len(self.wanted_invest_strategies):
            # 没有更多要求，直接结束刷开局
            logger.info(f"阶段{self.invest_strategy_stage}无投资策略要求，所有阶段已满足，停止刷开局")
            self.is_running = False
            return
        
        wanted_strategy = self.wanted_invest_strategies[current_stage_index]
        if not wanted_strategy:
            # 当前阶段无要求，直接继续下一阶段
            logger.info(f"阶段{self.invest_strategy_stage}无投资策略要求，继续游戏...")
            self.operator.click_point(0.5, 0.27)  # 点击中心点选择任意策略
            self.operator.click_img(IMG.ENSURE2, after_sleep=1)
            # 检查下一阶段是否还有要求，若无则结束
            if current_stage_index + 1 >= len(self.wanted_invest_strategies):
                logger.info("所有阶段投资策略已满足，停止刷开局")
                self.is_running = False
            return

        for _ in range(3):
            logger.info(f"阶段{self.invest_strategy_stage}正在识别投资策略...")
            result = self._detect_invest_strategy(wanted_strategy)
            if result == -1:
                logger.info("投资策略不符合要求，正在刷新...")
                boxs = self.operator.locate_all(CWIMG.INVEST_STRATEGY_REFRESH)
                if boxs is None:
                    logger.info("已无刷新次数")
                    break
                for box in boxs:
                    self.operator.click_box(box, after_sleep=1)
            else:
                logger.info("投资策略符合要求，继续游戏...")
                self.operator.click_point(0.25 * (result + 1), 0.27, tag="投资策略")  # 根据投资策略的位置计算点击坐标，每个策略占屏幕宽度的25%
                self.operator.click_img(IMG.ENSURE2, after_sleep=1)
                # 检查下一阶段是否还有要求，若无则结束
                if current_stage_index + 1 >= len(self.wanted_invest_strategies):
                    logger.info("当前阶段满足且无后续要求，停止刷开局")
                    self.is_running = False
                return

        default_invest_strategy_handler()

    def handle_stage_transitioned(self) -> bool:
        if self.reroll:
            self.abort_and_return()
            self.reroll = False
            return False
        return self.is_running

    def _detect_invest_strategy(self, wanted_strategy: str = None):
        """
        检测投资策略是否符合要求
        
        :param wanted_strategy: 当前阶段需要的投资策略，如果为None则使用全部期望策略
        :return: 匹配的投资策略索引，-1表示未匹配
        """
        detected_invest_strategy = list()
        raw_results = self.operator.ocr(
            from_x=self.INVEST_STRATEGY_OCR_FROM_X,
            from_y=self.INVEST_STRATEGY_OCR_FROM_Y,
            to_x=self.INVEST_STRATEGY_OCR_TO_X,
            to_y=self.INVEST_STRATEGY_OCR_TO_Y,
        )
        # 边界处理：OCR识别失败/无结果
        if not raw_results:  # 覆盖None和空列表两种情况
            logger.warning("投资策略OCR识别失败：无识别结果")
            return -1

        # 解析OCR结果：过滤空字符串，仅保留有效词缀
        for item in raw_results:
            # 提取并清洗词缀文本
            affix_text = self._normalize_ocr_text(str(item[1]))  # 去除常见的干扰字符
            detected_invest_strategy.append(affix_text)

        # 日志输出识别到的词缀，便于调试
        logger.info(f"识别到投资策略：{detected_invest_strategy}")

        # 使用指定的当前阶段策略进行匹配
        if wanted_strategy:
            for i, invest_strategy in enumerate(detected_invest_strategy):
                if self._is_substring(wanted_strategy, invest_strategy):
                    logger.info(f"检测到需要的投资策略 {invest_strategy} (匹配: {wanted_strategy})")
                    return i
            return -1
        return -1

    def _detect_boss_affix(self) -> bool:
        """
        检测Boss词缀是否符合筛选规则（仇恨词缀/需要词缀/可选词缀）
        筛选规则优先级：仇恨词缀 > 需要词缀 > 可选词缀
        :return: True-词缀符合要求，False-词缀不符合要求
        """
        detected_affixes = []
        # 执行OCR识别Boss词缀
        raw_results = self.operator.ocr(
            from_x=self.BOSS_AFFIX_FROM_X,
            from_y=self.BOSS_AFFIX_FROM_Y,
            to_x=self.BOSS_AFFIX_TO_X,
            to_y=self.BOSS_AFFIX_TO_Y
        )
        # 边界处理：OCR识别失败/无结果
        if not raw_results:  # 覆盖None和空列表两种情况
            logger.warning("Boss词缀OCR识别失败：无识别结果")
            return False

        # 解析OCR结果：过滤空字符串+去重，仅保留有效词缀
        for item in raw_results:
            # 提取并清洗词缀文本
            affix_text = self._normalize_ocr_text(str(item[1]))
            if not affix_text:  # 过滤空字符串
                continue
            detected_affixes.append(affix_text)

        # 日志输出识别到的词缀，便于调试
        logger.info(f"识别到Boss词缀：{detected_affixes}")

        # 筛选规则校验（优先级：仇恨词缀 → 需要词缀 → 可选词缀）
        # 规则1：检测仇恨词缀（只要包含任意一个，直接返回False）
        if self.hate_boss_affixes:
            for hate_affix in self.hate_boss_affixes:
                # 仇恨词缀采用子字符串匹配，只要识别到的任一词缀与仇恨词缀存在子串关系即判定为不符合
                for aff in detected_affixes:
                    if self._is_substring(hate_affix, aff):
                        logger.warning(f"检测到词缀【{hate_affix}】(识别:{aff})，不符合要求")
                        return False

        # 规则2：检测需要词缀（必须包含所有需要词缀，否则返回False）
        if self.wanted_boss_affixes:
            # 必需词缀也采用子字符串匹配：每个需要词缀必须在识别结果中找到至少一个存在子串关系的项
            for wanted_affix in self.wanted_boss_affixes:
                found = False
                for aff in detected_affixes:
                    if self._is_substring(wanted_affix, aff):
                        found = True
                        break
                if not found:
                    logger.warning(f"缺少需要词缀【{wanted_affix}】，不符合要求")
                    return False
        return True

    def _detect_boss_name(self) -> bool:
        """检测Boss名称是否符合筛选规则，顺序依次对应第一、二、三位面。"""
        raw_results = self.operator.ocr(
            from_x=self.BOSS_NAME_FROM_X,
            from_y=self.BOSS_NAME_FROM_Y,
            to_x=self.BOSS_NAME_TO_X,
            to_y=self.BOSS_NAME_TO_Y
        )
        if not raw_results:
            logger.warning("Boss名称OCR识别失败：无识别结果")
            return False

        sorted_results = sorted(raw_results, key=lambda _item: _item[0][0][0])
        detected_boss_names = []
        for item in sorted_results:
            boss_name = self._normalize_ocr_text(str(item[1]))
            if not boss_name:
                continue
            detected_boss_names.append(boss_name)

        detected_boss_names = detected_boss_names[:3]
        logger.info(f"识别到Boss名称：{detected_boss_names}")

        if not self.wanted_boss_names:
            return True

        for i, wanted_boss_name in enumerate(self.wanted_boss_names):
            if not wanted_boss_name:
                continue
            if i >= len(detected_boss_names):
                logger.warning(f"第{i + 1}位面Boss名称缺失，期望【{wanted_boss_name}】")
                return False
            # 使用子字符串匹配判断名称是否符合要求
            detected_name = detected_boss_names[i]
            if not self._is_substring(wanted_boss_name, detected_name):
                logger.warning(
                    f"第{i + 1}位面Boss名称不符合要求，识别到【{detected_name}】，期望包含【{wanted_boss_name}】"
                )
                return False

        return True

    def _detect_invest_env(self):
        detected_invest_env = []

        raw_results = self.operator.ocr(
            from_x=self.INVEST_ENV_OCR_FROM_X,
            from_y=self.INVEST_ENV_OCR_FROM_Y,
            to_x=self.INVEST_ENV_OCR_TO_X,
            to_y=self.INVEST_ENV_OCR_TO_Y,
        )
        # 边界处理：OCR识别失败/无结果
        if not raw_results:  # 覆盖None和空列表两种情况
            logger.warning("投资环境OCR识别失败：无识别结果")
            return -1

        # 解析OCR结果：过滤空字符串+去重，仅保留有效词缀
        for item in raw_results:
            # 提取并清洗词缀文本
            affix_text = self._normalize_ocr_text(str(item[1]))
            detected_invest_env.append(affix_text)

        # 日志输出识别到的词缀，便于调试
        logger.info(f"识别到投资环境：{detected_invest_env}")
        
        # 优先检测必须的投资环境
        for i, env in enumerate(detected_invest_env):
            # 使用子字符串匹配：将期望值规范化后，与识别到的env做子串比较
            for want in (self.wanted_invest_env or []):
                if self._is_substring(self._normalize_ocr_text(want), env):
                    logger.info(f"检测到必须的投资环境【{env}】(匹配: {want})")
                    return i

        # 如果没有必须的投资环境，检测可选的投资环境
        if self.optional_invest_env:
            for i, env in enumerate(detected_invest_env):
                for opt in self.optional_invest_env:
                    if self._is_substring(self._normalize_ocr_text(opt), env):
                        logger.info(f"检测到可选的投资环境【{env}】(匹配: {opt})")
                        return i

        # 既没有必须的投资环境，也没有可选的投资环境
        return -1



