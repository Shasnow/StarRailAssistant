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
    MAIMG   使命完成
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
    NUMBER_1 = f"{BASE}/1.png"
    NUMBER_2 = f"{BASE}/2.png"
    NUMBER_3 = f"{BASE}/3.png"
    NUMBER_4 = f"{BASE}/4.png"
    NUMBER_5 = f"{BASE}/5.png"
    ENTER = f"{BASE}/enter.png"
    F2 = f"{BASE}/f2.png"
    F3 = f"{BASE}/f3.png"
    F4 = f"{BASE}/f4.png"
    DIALOG = f"{BASE}/dialog.png"
    M = f"{BASE}/m.png"
    ENSURE = f"{BASE}/ensure.png"
    ENSURE2 = f"{BASE}/ensure2.png"
    ENSURE3 = f"{BASE}/ensure3.png"
    Q = f"{BASE}/q.png"
    QUIT = f"{BASE}/quit.png"
    QUIT2 = f"{BASE}/quit2.png"
    SURVIVAL_INDEX = f"{BASE}/survival_index.png"
    SURVIVAL_INDEX_ONCLICK = f"{BASE}/survival_index_onclick.png"
    COSMIC_STRIFE = f"{BASE}/cosmic_strife.png"
# endregion

# region 登录相关专用
class SGIMG:
    BASE = "resources/img/sg"
    TRAIN_SUPPLY = f"{BASE}/train_supply.png"
    TASK_RESOURCES_MANAGE = f"{BASE}/task_resources_manage.png"
    RESTART_FOR_UPDATE = f"{BASE}/restart_for_update.png"
    LOGIN_PAGE = f"{BASE}/%s/login_page.png"
    WELCOME = f"{BASE}/%s/welcome.png"
    LOGIN_OTHER = f"{BASE}/%s/login_other.png"
    LOGIN_WITH_ACCOUNT = f"{BASE}/%s/login_with_account.png"
    USERNAME_INPUT = f"{BASE}/%s/username_input.png"
    AGREE = f"{BASE}/%s/agree.png"
    ENTER_GAME = f"{BASE}/%s/enter_game.png"
# endregion

# region 体力任务专用
class TPIMG:
    BASE = "resources/img/tp"
    ENTER= f"{BASE}/enter.png"
    TRAILBLAZE_POWER = f"{BASE}/trailblaze_power.png"
    ORNAMENT_EXTRACTION = f"{BASE}/ornament_extraction (%s).png"
    ORNAMENT_EXTRACTION_NO_SAVE = f"{BASE}/ornament_extraction_no_save.png"
    ORNAMENT_EXTRACTION_PAGE = f"{BASE}/ornament_extraction_page.png"
    PLUS = f"{BASE}/plus.png"
    BATTLE_STAR = f"{BASE}/battle_star.png"
    LIMIT = f"{BASE}/limit.png"
    REPLENISH = f"{BASE}/replenish.png"
    BATTLE = f"{BASE}/battle.png"
    AGAIN = f"{BASE}/again.png"
    QUIT_BATTLE = f"{BASE}/quit_battle.png"
    BATTLE_FAILURE = f"{BASE}/battle_failure.png"
    LIGHT_CONE = f"{BASE}/light_cone.png"
    REMOVE_SUPPORT = f"{BASE}/remove_support.png"
    SUPPORT = f"{BASE}/support.png"
    SUPPORT2 = f"{BASE}/support2.png"
    DUPLICATE_REPLACED = f"{BASE}/duplicate_replaced.png"
    RESERVED_TRAILBLAZE_POWER = f"{BASE}/reserved_trailblaze_power.png"
    RESERVED_TRAILBLAZE_POWER_ONCLICK = f"{BASE}/reserved_trailblaze_power_onclick.png"
    FUEL = f"{BASE}/fuel.png"
    FUEL_ONCLICK = f"{BASE}/fuel_onclick.png"
    STELLAR_JADE = f"{BASE}/stellar_jade.png"
    STELLAR_JADE_ONCLICK = f"{BASE}/stellar_jade_onclick.png"

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
    ASSISTANCE_REWARD = f"{BASE}/assistance_reward.png"
    REDEEM_CODE = f"{BASE}/redeem_code.png"
    CLAIM_ALL_MAIL = f"{BASE}/claim_all_mail.png"
    GIFT_RECEIVE = f"{BASE}/gift_receive.png"
    GIFT_RECEIVE2 = f"{BASE}/gift_receive2.png"
    ASSIGNMENTS_NONE = f"{BASE}/assignments_none.png"
    ASSIGNMENT_PAGE = f"{BASE}/assignment_page.png"
    ASSIGNMENT_PAGE2 = f"{BASE}/assignment_page2.png"
    ASSIGNMENTS_REWARD = f"{BASE}/assignments_reward.png"
    DAILY_REWARD = f"{BASE}/daily_reward.png"
    DAILY_TRAIN_REWARD = f"{BASE}/daily_train_reward.png"
    DAILY_TRAIN_REWARD_NOTREACH = f"{BASE}/daily_train_reward_notreach.png"
    NAMELESS_HONOR_REWARD_RECEIVE = f"{BASE}/nameless_honor_reward_receive.png"
    NAMELESS_HONOR_TASK = f"{BASE}/nameless_honor_task.png"
    NAMELESS_HONOR_TASK_RECEIVE = f"{BASE}/nameless_honor_task_receive.png"
    NAMELESS_HONOR_REWARD = f"{BASE}/nameless_honor_reward.png"
    SYNTHESIS = f"{BASE}/synthesis.png"
    MATERIAL_REPLACEMENT = f"{BASE}/material_replacement.png"
    AUTOMATIC_PLACEMENT = f"{BASE}/automatic_placement.png"
    SYNTHESIS2 = f"{BASE}/synthesis2.png"
    RELIC = f"{BASE}/relic.png"
    REVERSE_ORDER = f"{BASE}/reverse_order.png"
    ENHANCE = f"{BASE}/enhance.png"
    ORDER = f"{BASE}/order.png"
    UPGRADE_MATERIALS = f"{BASE}/upgrade_materials.png"
    AUTOMATIC_PLACEMENT2 = f"{BASE}/automatic_placement2.png"
    FOUR_STAR = f"{BASE}/four_star.png"
    NEXT_CODE = f"{BASE}/next_code.png"
# endregion

# region 货币战争
class CWIMG:
    BASE = "resources/img/currency_wars"
    COLLECTION = f"{BASE}/collection.png"
    CURRENCY_WARS_START = f"{BASE}/currency_wars_start.png"
    EQUIP = f"{BASE}/equip.png"
    EQUIPMENT_RECOMMEND = f"{BASE}/equipment_recommend.png"
    SYNTHESIS = f"{BASE}/synthesis.png"
    PREPARATION_STAGE = f"{BASE}/preparation_stage.png"
    ENTER_STANDARD = f"{BASE}/enter_standard.png"
    CONTINUE_PROGRESS = f"{BASE}/continue_progress.png"
    DOWN_ARROW = f"{BASE}/down_arrow.png"
    START_GAME = f"{BASE}/start_game.png"
    NEXT_STEP = f"{BASE}/next_step.png"
    INVEST_ENVIRONMENT = f"{BASE}/invest_environment.png"
    CLICK_BLANK = f"{BASE}/click_blank.png"
    OPEN = f"{BASE}/open.png"
    SETTLE = f"{BASE}/settle.png"
    CONTINUE = f"{BASE}/continue.png"
    REPLENISH_STAGE = f"{BASE}/replenish_stage.png"
    ENCOUNTER_NODE = f"{BASE}/encounter_node.png"
    FOLD = f"{BASE}/fold.png"
    SELECT_INVEST_STRATEGY = f"{BASE}/select_invest_strategy.png"
    THE_PLANET_OF_FESTIVITIES = f"{BASE}/ThePlanetOfFestivities.png"
    RIGHT = f"{BASE}/right.png"
    FORTUNE_TELLER = f"{BASE}/FortuneTeller.png"
    RETURN_HIGHEST_RANK = f"{BASE}/return_highest_rank.png"
    WITHDRAW_AND_SETTLE = f"{BASE}/withdraw_and_settle.png"
    NEXT_PAGE = f"{BASE}/next_page.png"
    BACK_CURRENCY_WARS = f"{BASE}/back_currency_wars.png"
    BATTLE = f"{BASE}/battle.png" #依赖于目前的默认 灰度 CCOEFF 算法
    LOGO = f"{BASE}/logo.png"
    QUIT = f"{BASE}/quit.png"
    CANNOT_BE_FIELDED = f"{BASE}/cannot_be_fielded.png"
    INVEST_STRATEGY_REFRESH = f"{BASE}/invest_strategy_refresh.png"
    INVEST_ENV_REFRESH = f"{BASE}/invest_env_refresh.png"
# endregion

# region 差分宇宙
class DUIMG:
    BASE = "resources/img/differential_universe"
    DIFFERENTIAL_UNIVERSE_START=f"{BASE}/differential_universe_start.png"
    PERIODIC_CALCULUS = f"{BASE}/periodic_calculus.png"
    LAUNCH_DIFFERENTIAL_UNIVERSE = f"{BASE}/launch_differential_universe.png"
    BLESSING_SELECT = f"{BASE}/blessing_select.png"
    BASE_EFFECT_SELECT = f"{BASE}/base_effect_select.png"
    EQUATION_SELECT = f"{BASE}/equation_select.png"
    CURIOSITY_SELECT = f"{BASE}/curiosity_select.png"
    EQUATION_EXPANSION = f"{BASE}/equation_expansion.png"
    CLOSE = f"{BASE}/close.png"
    DIVERGENT_UNIVERSE_QUIT = f"{BASE}/differential_universe_quit.png"
    COLLECTION = f"{BASE}/collection.png"
    END_AND_SETTLE = f"{BASE}/end_and_settle.png"
    RETURN = f"{BASE}/return.png"
    BONUS_POINTS = f"{BASE}/bonus_points.png"
# endregion

# region 使命完成专用
class MAIMG:
    BASE = "resources/img/mission_accomplish"
    POWER = f"{BASE}/power.png"
    LOGOUT = f"{BASE}/logout.png"
# endregion