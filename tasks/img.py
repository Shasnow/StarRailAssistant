"""
图片常量集中管理

集中管理本模块使用的所有图片路径。

分类：
    SRAIMG  SRA程序资源
    IMG     通用图片
    SGIMG   登录相关
    TPIMG   体力任务
    RRIMG   领取奖励
    CWIMG   货币战争
    DUIMG   差分宇宙
    MAIMG   任务完成
"""
# region SRA专用
class SRAIMG:
    BASE = "resources"
    ROBIN = f"{BASE}/Robin.gif"
    ROBIN2 = f"{BASE}/Robin2.gif"
    SRAICO_PNG = f"{BASE}/SRAico.png"
    SRAICON_ICO = f"{BASE}/SRAicon.ico"
# endregion

# region 通用
class IMG:
    BASE = "resources/img"
    COSMIC_STRIFE = f"{BASE}/cosmic_strife.png"
    DIALOG = f"{BASE}/dialog.png"
    ENTER = f"{BASE}/enter.png"
    ENSURE = f"{BASE}/ensure.png"
    ENSURE2 = f"{BASE}/ensure2.png"
    ENSURE3 = f"{BASE}/ensure3.png"
    F2 = f"{BASE}/f2.png"
    F3 = f"{BASE}/f3.png"
    F4 = f"{BASE}/f4.png"
    M = f"{BASE}/m.png"
    NUMBER_1 = f"{BASE}/1.png"
    NUMBER_2 = f"{BASE}/2.png"
    NUMBER_3 = f"{BASE}/3.png"
    NUMBER_4 = f"{BASE}/4.png"
    NUMBER_5 = f"{BASE}/5.png"
    Q = f"{BASE}/q.png"
    QUIT = f"{BASE}/quit.png"
    QUIT2 = f"{BASE}/quit2.png"
    SURVIVAL_INDEX = f"{BASE}/survival_index.png"
    SURVIVAL_INDEX_ONCLICK = f"{BASE}/survival_index_onclick.png"
# endregion

# region 登录相关专用
class SGIMG:
    BASE = "resources/img/sg"
    AGREE = f"{BASE}/%s/agree.png"
    ENTER_GAME = f"{BASE}/%s/enter_game.png"
    LOGIN_OTHER = f"{BASE}/%s/login_other.png"
    LOGIN_PAGE = f"{BASE}/%s/login_page.png"
    LOGIN_WITH_ACCOUNT = f"{BASE}/%s/login_with_account.png"
    RESTART_FOR_UPDATE = f"{BASE}/restart_for_update.png"
    TASK_RESOURCES_MANAGE = f"{BASE}/task_resources_manage.png"
    TRAIN_SUPPLY = f"{BASE}/train_supply.png"
    USERNAME_INPUT = f"{BASE}/%s/username_input.png"
    WELCOME = f"{BASE}/%s/welcome.png"
    NEW_VERSION = f"{BASE}/new_version.png"
    SETTINGS = f"{BASE}/settings.png"
# endregion

# region 体力任务专用
class TPIMG:
    BASE = "resources/img/tp"
    AGAIN = f"{BASE}/again.png"
    BATTLE = f"{BASE}/battle.png"
    BATTLE_FAILURE = f"{BASE}/battle_failure.png"
    BATTLE_STAR = f"{BASE}/battle_star.png"
    DUPLICATE_REPLACED = f"{BASE}/duplicate_replaced.png"
    ENTER = f"{BASE}/enter.png"
    FUEL = f"{BASE}/fuel.png"
    FUEL_ONCLICK = f"{BASE}/fuel_onclick.png"
    LIGHT_CONE = f"{BASE}/light_cone.png"
    LIMIT = f"{BASE}/limit.png"
    ORNAMENT_EXTRACTION = f"{BASE}/ornament_extraction (%s).png"
    ORNAMENT_EXTRACTION_NO_SAVE = f"{BASE}/ornament_extraction_no_save.png"
    NO_SAVE = f"{BASE}/no_save.png"
    ORNAMENT_EXTRACTION_PAGE = f"{BASE}/ornament_extraction_page.png"
    PLUS = f"{BASE}/plus.png"
    QUIT_BATTLE = f"{BASE}/quit_battle.png"
    REMOVE_SUPPORT = f"{BASE}/remove_support.png"
    REPLENISH = f"{BASE}/replenish.png"
    RESERVED_TRAILBLAZE_POWER = f"{BASE}/reserved_trailblaze_power.png"
    RESERVED_TRAILBLAZE_POWER_ONCLICK = f"{BASE}/reserved_trailblaze_power_onclick.png"
    STELLAR_JADE = f"{BASE}/stellar_jade.png"
    STELLAR_JADE_ONCLICK = f"{BASE}/stellar_jade_onclick.png"
    SUPPORT = f"{BASE}/support.png"
    SUPPORT2 = f"{BASE}/support2.png"
    TRAILBLAZE_POWER = f"{BASE}/trailblaze_power.png"

    # 体力任务的等级图
    @staticmethod
    def level(level_belonging: str, level: int) -> str:
        return f"{TPIMG.BASE}/{level_belonging} ({level}).png"

    # 体力任务的索引图
    @staticmethod
    def session(name: str, onclick: bool = False) -> str:
        suffix = "_onclick" if onclick else ""
        return f"{TPIMG.BASE}/{name}{suffix}.png"
# endregion

# region 领取奖励专用
class RRIMG:
    BASE = "resources/img/receive_rewards"
    ASSIGNMENTS_NONE = f"{BASE}/assignments_none.png"
    ASSIGNMENTS_REWARD = f"{BASE}/assignments_reward.png"
    ASSIGNMENT_PAGE = f"{BASE}/assignment_page.png"
    ASSIGNMENT_PAGE2 = f"{BASE}/assignment_page2.png"
    ASSISTANCE_REWARD = f"{BASE}/assistance_reward.png"
    AUTOMATIC_PLACEMENT = f"{BASE}/automatic_placement.png"
    AUTOMATIC_PLACEMENT2 = f"{BASE}/automatic_placement2.png"
    CLAIM_ALL_MAIL = f"{BASE}/claim_all_mail.png"
    DAILY_REWARD = f"{BASE}/daily_reward.png"
    DAILY_TRAIN_REWARD = f"{BASE}/daily_train_reward.png"
    DAILY_TRAIN_REWARD_NOTREACH = f"{BASE}/daily_train_reward_notreach.png"
    ENHANCE = f"{BASE}/enhance.png"
    FOUR_STAR = f"{BASE}/four_star.png"
    GIFT_RECEIVE = f"{BASE}/gift_receive.png"
    GIFT_RECEIVE2 = f"{BASE}/gift_receive2.png"
    MATERIAL_REPLACEMENT = f"{BASE}/material_replacement.png"
    NAMELESS_HONOR_REWARD = f"{BASE}/nameless_honor_reward.png"
    NAMELESS_HONOR_REWARD_RECEIVE = f"{BASE}/nameless_honor_reward_receive.png"
    NAMELESS_HONOR_TASK = f"{BASE}/nameless_honor_task.png"
    NAMELESS_HONOR_TASK_RECEIVE = f"{BASE}/nameless_honor_task_receive.png"
    NEXT_CODE = f"{BASE}/next_code.png"
    ORDER = f"{BASE}/order.png"
    REDEEM_CODE = f"{BASE}/redeem_code.png"
    RELIC = f"{BASE}/relic.png"
    REVERSE_ORDER = f"{BASE}/reverse_order.png"
    SYNTHESIS = f"{BASE}/synthesis.png"
    SYNTHESIS2 = f"{BASE}/synthesis2.png"
    UPGRADE_MATERIALS = f"{BASE}/upgrade_materials.png"
# endregion

# region 货币战争
class CWIMG:
    BASE = "resources/img/currency_wars"
    APPLY_STRATEGY = f"{BASE}/apply_strategy.png"
    BACK_CURRENCY_WARS = f"{BASE}/back_currency_wars.png"
    BACK_PREPARE_PAGE = f"{BASE}/back_prepare_page.png"
    BATTLE = f"{BASE}/battle.png" #依赖于目前的默认 灰度 CCOEFF 算法
    CANNOT_BE_FIELDED = f"{BASE}/cannot_be_fielded.png"
    CLICK_BLANK = f"{BASE}/click_blank.png"
    COLLECTION = f"{BASE}/collection.png"
    CONTINUE = f"{BASE}/continue.png"
    CONTINUE_PROGRESS = f"{BASE}/continue_progress.png"
    START_CURRENCY_WARS = f"{BASE}/start_currency_wars.png"
    DOWN_ARROW = f"{BASE}/down_arrow.png"
    ENCOUNTER_NODE = f"{BASE}/encounter_node.png"
    ENTER_GAME = f"{BASE}/enter_game.png"
    ENTER_STRATEGY_CODE = f"{BASE}/enter_strategy_code.png"
    EQUIP = f"{BASE}/equip.png"
    EQUIPMENT_RECOMMEND = f"{BASE}/equipment_recommend.png"
    FOLD = f"{BASE}/fold.png"
    FORTUNE_TELLER = f"{BASE}/FortuneTeller.png"
    INVEST_ENVIRONMENT = f"{BASE}/invest_environment.png"
    INVEST_ENV_REFRESH = f"{BASE}/invest_env_refresh.png"
    INVEST_STRATEGY_REFRESH = f"{BASE}/invest_strategy_refresh.png"
    INSTRUCTIONS = f"{BASE}/instructions.png"
    LOGO = f"{BASE}/logo.png"
    NEXT_PAGE = f"{BASE}/next_page.png"
    NEXT_STEP = f"{BASE}/next_step.png"
    OPEN = f"{BASE}/open.png"
    PREPARATION_STAGE = f"{BASE}/preparation_stage.png"
    QUIT = f"{BASE}/quit.png"
    REPLENISH_STAGE = f"{BASE}/replenish_stage.png"
    RETURN_HIGHEST_RANK = f"{BASE}/return_highest_rank.png"
    RIGHT = f"{BASE}/right.png"
    SELECT_INVEST_STRATEGY = f"{BASE}/select_invest_strategy.png"
    SETTLE = f"{BASE}/settle.png"
    STAR = f"{BASE}/star.png"
    START_GAME = f"{BASE}/start_game.png"
    STRATEGY = f"{BASE}/strategy.png"
    SYNTHESIS = f"{BASE}/synthesis.png"
    SILVER_WOLF_LV999 = f"{BASE}/silver_wolf_lv999.png"
    THE_PLANET_OF_FESTIVITIES = f"{BASE}/ThePlanetOfFestivities.png"
    WITHDRAW_AND_SETTLE = f"{BASE}/withdraw_and_settle.png"
# endregion

# region 差分宇宙
class DUIMG:
    BASE = "resources/img/differential_universe"
    BASE_EFFECT_SELECT = f"{BASE}/base_effect_select.png"
    BLESSING_SELECT = f"{BASE}/blessing_select.png"
    MASK_SELECT = f"{BASE}/mask_select.png"
    STATION_SELECT = f"{BASE}/station_select.png"
    BONUS_POINTS = f"{BASE}/bonus_points.png"
    CLOSE = f"{BASE}/close.png"
    COLLECTION = f"{BASE}/collection.png"
    CURIOSITY_SELECT = f"{BASE}/curiosity_select.png"
    DIFFERENTIAL_UNIVERSE_START = f"{BASE}/differential_universe_start.png"
    DIFFERENTIAL_UNIVERSE_QUIT = f"{BASE}/differential_universe_quit.png"
    DIFFERENTIAL_UNIVERSE = f"{BASE}/differential_universe.png"
    END_AND_SETTLE = f"{BASE}/end_and_settle.png"
    EQUATION_EXPANSION = f"{BASE}/equation_expansion.png"
    EQUATION_SELECT = f"{BASE}/equation_select.png"
    LAUNCH_DIFFERENTIAL_UNIVERSE = f"{BASE}/launch_differential_universe.png"
    PERIODIC_CALCULUS = f"{BASE}/periodic_calculus.png"
    RETURN = f"{BASE}/return.png"
    ENSURE = f"{BASE}/ensure.png"
    ENSURE2 = f"{BASE}/ensure2.png"
    SELECT_GRAND_MIRACLE = f"{BASE}/select_grand_miracle.png"
# endregion

# region 任务完成专用
class MAIMG:
    BASE = "resources/img/mission_accomplish"
    LOGOUT = f"{BASE}/logout.png"
    POWER = f"{BASE}/power.png"
# endregion
