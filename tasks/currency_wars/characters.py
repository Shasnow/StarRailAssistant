import dataclasses
import enum


class Faction(enum.IntEnum):
    """
    角色阵营枚举类
    表示角色所属的游戏阵营
    """
    Xianzhou = 1  # 仙舟
    WolfHunt = 2  # 狼狩
    NightDemigod = 3  # 夜之半神
    DayDemigod = 4  # 昼之半神
    Belobog = 5  # 贝洛伯格
    ExpressCohort = 6  # 列车同行
    CosmicScholar = 7  # 银河学者
    GalacticVoyager = 8  # 星间旅人
    ThePlanetOfFestivities = 9  # 盛会之星
    StellaronHunters = 10  # 星核猎手
    GalaxyRanger = 11  # 巡海游侠
    IPC = 12  # 公司
    Other = 13  # 其他


class School(enum.IntEnum):
    """
    角色派系枚举类
    表示角色所属的游戏派系
    """
    Break = 1  # 击破
    FollowUpATK = 2  # 追加攻击
    Energy = 3  # 能量
    AoEATK = 4  # 群攻
    Bloodflame = 5  # 燃血
    Debuff = 6  # 减益
    DoT = 7  # 持续伤害
    SkillPoints = 8  # 战技点
    QuantumResonance = 9  # 量子同频
    Heal = 10  # 治疗
    Shield = 11  # 护盾
    Other = 12  # 其他


class Positioning(enum.IntEnum):
    """
    角色站位枚举类
    表示角色在游戏中的默认站位
    """
    OnField = 1  # 前台
    OffField = 2  # 后台
    OnOffField = 3  # 前后兼备

    def __add__(self, other) -> 'Positioning':
        if not isinstance(other, Positioning):
            return NotImplemented

        # 相同 → 返回自己
        if self == other:
            return self

        # 不同 → 合并为前后台兼备
        return Positioning.OnOffField


@dataclasses.dataclass
class Character:
    """
    角色类
    包含角色的基本信息和状态
    """
    name: str  # 名称
    # faction: list[Faction] | Faction  # 阵营
    # schools: list[School]  # 派系
    cost: int  # 费用
    positioning: Positioning  # 默认站位
    position: Positioning | None = None  # 实际站位（适配攻略的特殊情况）
    priority: int | None = None  # 优先级
    is_placed: bool = False  # 是否已放置
    stars: int = 0  # 角色星级

    def __post_init__(self):
        if self.priority is None:
            self.priority = self.cost
        if self.position is None:
            self.position = self.positioning

    def __str__(self):
        return f'{self.name}'

    def __repr__(self):
        return f'{self.name}'

    def reset(self):
        self.priority = self.cost
        self.position = self.positioning


class Characters:
    """
    角色工具类
    提供角色信息查询、设置开拓者名称等功能
    """
    Cyrene = Character('昔涟', 5, Positioning.OnField)
    DanHeng_PermansorTerrae = Character('丹恒·腾荒', 2, Positioning.OffField)
    Evernight = Character('长夜月', 4, Positioning.OnOffField)
    Cerydra = Character('刻律德菈', 3, Positioning.OnOffField)
    Hysilens = Character('海瑟音', 4, Positioning.OnField)
    Archer = Character('Archer', 5, Positioning.OnField)
    Saber = Character('Saber', 3, Positioning.OnOffField)
    Phainon = Character('白厄', 3, Positioning.OnField)
    Cipher = Character('赛飞儿', 1, Positioning.OnField)
    Hyacine = Character('风堇', 2, Positioning.OnField)
    Anaxa = Character('那刻夏', 3, Positioning.OffField)
    Castorice = Character('遐蝶', 4, Positioning.OnField)
    Mydei = Character('万敌', 2, Positioning.OnOffField)
    Tribbie = Character('缇宝', 2, Positioning.OnOffField)
    Aglaea = Character('阿格莱雅', 1, Positioning.OnField)
    TheHerta = Character('大黑塔', 4, Positioning.OnField)
    Sunday = Character('星期日', 3, Positioning.OnField)
    Fugue = Character('忘归人', 3, Positioning.OffField)
    Rappa = Character('乱破', 1, Positioning.OnField)
    Lingsha = Character('灵砂', 2, Positioning.OnField)
    Feixiao = Character('飞霄', 1, Positioning.OnField)
    Moze = Character('貊泽', 1, Positioning.OffField)
    Jiaoqiu = Character('椒丘', 1, Positioning.OnField)
    Yunli = Character('云璃', 5, Positioning.OffField)
    Jade = Character('翡翠', 1, Positioning.OffField)
    Firefly = Character('流萤', 5, Positioning.OnField)
    Boothill = Character('波提欧', 4, Positioning.OnField)
    Robin = Character('知更鸟', 4, Positioning.OffField)
    Aventurine = Character('砂金', 2, Positioning.OnField)
    Acheron = Character('黄泉', 3, Positioning.OnField)
    Gallagher = Character('加拉赫', 1, Positioning.OnOffField)
    Sparkle = Character('花火', 2, Positioning.OffField)
    BlackSwan = Character('黑天鹅', 5, Positioning.OffField)
    DrRatio = Character('真理医生', 3, Positioning.OnField)
    RuanMei = Character('阮·梅', 2, Positioning.OffField)
    Argenti = Character('银枝', 2, Positioning.OnField)
    Huohuo = Character('藿藿', 2, Positioning.OnOffField)
    TopazAndNumby = Character('托帕&账账', 5, Positioning.OffField)
    Jingliu = Character('镜流', 3, Positioning.OffField)
    FuXuan = Character('符玄', 4, Positioning.OffField)
    DanHeng_ImbibitorLunae = Character('丹恒·饮月', 2, Positioning.OnField)
    Kafka = Character('卡芙卡', 2, Positioning.OnField)
    Blade = Character('刃', 1, Positioning.OffField)
    Luocha = Character('罗刹', 4, Positioning.OffField)
    SilverWolf = Character('银狼', 4, Positioning.OnOffField)
    JingYuan = Character('景元', 5, Positioning.OnField)
    Seele = Character('希儿', 3, Positioning.OnField)
    Gepard = Character('杰帕德', 4, Positioning.OnField)
    Natasha = Character('娜塔莎', 3, Positioning.OffField)
    Bronya = Character('布洛妮娅', 5, Positioning.OnField)
    Welt = Character('瓦尔特', 5, Positioning.OnField)
    Himeko = Character('姬子', 3, Positioning.OffField)
    Yanqing = Character('彦卿', 3, Positioning.OffField)
    Asta = Character('艾丝妲', 1, Positioning.OnField)
    Sampo = Character('桑博', 1, Positioning.OnOffField)
    March7th = Character('三月七', 1, Positioning.OffField)
    Tingyun = Character('停云', 1, Positioning.OffField)
    Qingque = Character('青雀', 1, Positioning.OnField)
    Pela = Character('佩拉', 2, Positioning.OffField)
    Herta = Character('黑塔', 1, Positioning.OnOffField)
    Trailblazer = Character('开拓者', 4, Positioning.OnField)
    TheDahlia = Character('大丽花', 1, Positioning.OnOffField)
    YaoGuang = Character('爻光', 1, Positioning.OnOffField)
    Sparxie = Character('火花', 4, Positioning.OnField)
    Ashveil = Character('不死途', 2, Positioning.OnOffField)
    SilverWolfLV999 = Character('银狼LV.999', 5, Positioning.OnOffField)
    Evanescia = Character('绯英', 2, Positioning.OnOffField)

    # 角色列表
    characters: dict[str, Character] = {
        '貊泽': Moze,
        '乱破': Rappa,
        '花火': Sparkle,
        '遐蝶': Castorice,
        '银枝': Argenti,
        '丹恒•饮月': DanHeng_ImbibitorLunae,
        '灵砂': Lingsha,
        '大黑塔': TheHerta,
        '托帕&账账': TopazAndNumby,
        '景元': JingYuan,
        '云璃': Yunli,
        '昔涟': Cyrene,
        '布洛妮娅': Bronya,
        '罗刹': Luocha,
        '知更鸟': Robin,
        '姬子': Himeko,
        '镜流': Jingliu,
        '真理医生': DrRatio,
        '那刻夏': Anaxa,
        '长夜月': Evernight,
        '飞霄': Feixiao,
        '阮•梅': RuanMei,
        '砂金': Aventurine,
        '缇宝': Tribbie,
        '万敌': Mydei,
        '风堇': Hyacine,
        '丹恒•腾荒': DanHeng_PermansorTerrae,
        '黑塔': Herta,
        '赛飞儿': Cipher,
        '青雀': Qingque,
        '刃': Blade,
        '翡翠': Jade,
        '瓦尔特': Welt,
        'Archer': Archer,
        '黑天鹅': BlackSwan,
        '流萤': Firefly,
        '银狼': SilverWolf,
        '杰帕德': Gepard,
        '符玄': FuXuan,
        '波提欧': Boothill,
        '彦卿': Yanqing,
        '海瑟音': Hysilens,
        'Saber': Saber,
        '希儿': Seele,
        '娜塔莎': Natasha,
        '忘归人': Fugue,
        '黄泉': Acheron,
        '星期日': Sunday,
        '白厄': Phainon,
        '刻律德拉': Cerydra,
        '刻律德菈': Cerydra,
        '刻律德': Cerydra,
        '卡芙卡': Kafka,
        '佩拉': Pela,
        '藿藿': Huohuo,
        '三月七': March7th,
        '艾丝妲': Asta,
        '桑博': Sampo,
        '停云': Tingyun,
        '椒丘': Jiaoqiu,
        '加拉赫': Gallagher,
        '阿格莱雅': Aglaea,
        '开拓者': Trailblazer,
        '大丽花': TheDahlia,
        '光': YaoGuang,
        '爻光': YaoGuang,
        '火花': Sparxie,
        '不死途': Ashveil,
        '银狼LV.999': SilverWolfLV999,
        '绯英': Evanescia,
    }
    username = '开拓者'  # 角色名称

    @classmethod
    def get_character(cls, name: str) -> Character | None:
        """根据名称获取角色信息"""
        name = name.replace('·', '•').replace('傑', '杰').replace('姐', '妲').replace("交", "")
        if name == cls.username:
            return cls.Trailblazer
        return cls.characters.get(name)

    @classmethod
    def set_username(cls, username: str):
        """设置开拓者名称"""
        cls.username = username
