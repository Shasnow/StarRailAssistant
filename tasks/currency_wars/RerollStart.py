from SRACore.util.logger import logger
from .CurrencyWars import CurrencyWars
from .img import IMG, CWIMG


class RerollStart(CurrencyWars):
    # Boss词条OCR区域（基于1920x1080截图坐标: 30,930-1200,1030）
    BOSS_AFFIX_FROM_X = 0.016
    BOSS_AFFIX_FROM_Y = 0.861
    BOSS_AFFIX_TO_X = 0.625
    BOSS_AFFIX_TO_Y = 0.954

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
        self.wanted_invest_strategy = None  # 必须出现的投资策略
        self.wanted_boss_affix = None  # 必须出现的boss词缀
        self.hate_boss_affix = None  # 讨厌的boss词缀，出现就重开
        self.invest_strategy_stage = 0  # 投资策略阶段
        self.invest_strategy_stage_limit = 2  # 投资策略阶段上限，超过后不再检测投资策略
        self.invest_strategy_satisfied = False  # 满意标志

    def set_invest_env(self, invest_env: str):
        """设置投资环境"""
        invest_env = invest_env.split()
        self.wanted_invest_env = list()
        self.optional_invest_env = list()
        for item in invest_env:
            if item.startswith("?"):
                self.optional_invest_env.append(item[1:])
            else:
                self.wanted_invest_env.append(item)

    def set_invest_strategy(self, invest_strategy: str, invest_strategy_stage_limit: int = 2):
        """设置投资策略"""
        def clean_strategy(s):
            return s.strip().replace("·", "").replace("•", "")
        self.wanted_invest_strategy = list(map(clean_strategy, invest_strategy.split()))
        self.invest_strategy_stage_limit = invest_strategy_stage_limit

    def set_boss_affix(self, boss_affix: str):
        """设置boss词缀"""
        boss_affix = boss_affix.split() if boss_affix else []
        self.wanted_boss_affix = list()
        self.hate_boss_affix = list()
        for item in boss_affix:
            if item.startswith("!"):
                self.hate_boss_affix.append(item[1:])
            else:
                self.wanted_boss_affix.append(item)

    def handle_boss_info(self) -> None:
        if self.wanted_boss_affix or self.hate_boss_affix:
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
        if not self.wanted_invest_strategy:
            # 如果不需要重开，且没有投资策略要求，可中止刷开局
            logger.info("已刷到满足要求的开局，停止刷开局")
            self.is_running = False
            return False
        return True

    def handle_invest_strategy(self):
        def default_invest_strategy_handler():
            if not self.operator.click_img(CWIMG.COLLECTION):  # 优先点击带有收集图标的策略
                self.operator.click_point(0.5, 0.27)  # 无法点击时，点击中心点
            self.operator.click_img(IMG.ENSURE2, after_sleep=1)  # 确认选择
        self.invest_strategy_stage += 1

        for _ in range(3):
            logger.info("正在识别投资策略...")
            result = self._detect_invest_strategy()
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
                self.invest_strategy_satisfied = True
                return

        default_invest_strategy_handler()

        if self.invest_strategy_stage >= self.invest_strategy_stage_limit:
            logger.info(f"已达到投资策略阶段 {self.invest_strategy_stage_limit}, 准备重开...")
            self.reroll = True
            return

    def handle_stage_transitioned(self) -> bool:
        if self.reroll:
            self.abort_and_return()
            self.reroll = False
            return False
        if self.invest_strategy_satisfied:
            # 如果已经满足投资策略要求，则中止刷开局
            logger.info("已刷到满足要求的开局，停止刷开局")
            self.is_running = False
            return False
        return True

    def _detect_invest_strategy(self):
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
            affix_text = str(item[1]).strip().replace("·", "").replace("•", "")
            detected_invest_strategy.append(affix_text)

        # 日志输出识别到的词缀，便于调试
        logger.info(f"识别到投资策略：{detected_invest_strategy}")

        for i, invest_strategy in enumerate(detected_invest_strategy):
            if invest_strategy in self.wanted_invest_strategy:
                logger.info(f"检测到需要的投资策略 {invest_strategy}")
                return i
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
            affix_text = str(item[1]).strip()
            if not affix_text:  # 过滤空字符串
                continue
            detected_affixes.append(affix_text)

        # 日志输出识别到的词缀，便于调试
        logger.info(f"识别到Boss词缀：{detected_affixes}")

        # 筛选规则校验（优先级：仇恨词缀 → 需要词缀 → 可选词缀）
        # 规则1：检测仇恨词缀（只要包含任意一个，直接返回False）
        if self.hate_boss_affix:
            for hate_affix in self.hate_boss_affix:
                if hate_affix in detected_affixes:
                    logger.warning(f"检测到词缀【{hate_affix}】，不符合要求")
                    return False

        # 规则2：检测需要词缀（必须包含所有需要词缀，否则返回False）
        if self.wanted_boss_affix:
            for wanted_affix in self.wanted_boss_affix:
                if wanted_affix not in detected_affixes:
                    logger.warning(f"缺少需要词缀【{wanted_affix}】，不符合要求")
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
            affix_text = str(item[1]).strip()
            detected_invest_env.append(affix_text)

        # 日志输出识别到的词缀，便于调试
        logger.info(f"识别到投资环境：{detected_invest_env}")
        
        # 优先检测必须的投资环境
        for i, env in enumerate(detected_invest_env):
            if env in self.wanted_invest_env:
                logger.info(f"检测到必须的投资环境【{env}】")
                return i
        
        # 如果没有必须的投资环境，检测可选的投资环境
        if self.optional_invest_env:
            for i, env in enumerate(detected_invest_env):
                if env in self.optional_invest_env:
                    logger.info(f"检测到可选的投资环境【{env}】")
                    return i
        
        # 既没有必须的投资环境，也没有可选的投资环境
        return -1

