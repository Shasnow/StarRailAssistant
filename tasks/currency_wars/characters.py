import dataclasses
import enum


class Faction(enum.IntEnum):
    Xianzhou = 1  # 仙舟
    WolfHunt = 2  # 狼狩
    NightDemigod = 3  # 夜之半神
    DayDemigod = 4  # 昼之半神
    Belobog = 5  # 贝洛伯格
    ExpressCohort = 6  # 列车同行
    CosmicScholar = 7  # 银河学者
    GalacticVoyager = 8  # 星间旅人
    ThePlanetOfFestivities = 9  # 盛会之星
    StellaronHounters = 10  # 星核猎手
    GalaxyRanger = 11  # 巡海游侠
    IPC = 12  # 公司
    Other = 13  # 其他


class School(enum.IntEnum):
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
    OnField = 1  # 前台
    OffField = 2  # 后台
    OnOffField = 3  # 前后兼备


@dataclasses.dataclass
class Character:
    name: str  # 名称
    faction: Faction  # 阵营
    schools: list[School]  # 派系
    cost: int  # 费用
    positioning: Positioning  # 站位
    select_will: int = 0  # 抓取意愿
    is_placed: bool = False  # 是否已放置

    def __str__(self):
        return f'{self.name}'

    def __repr__(self):
        return f'{self.name}'


class Characters:
    Cyrene = Character('昔涟', Faction.DayDemigod, [School.Other], 5, Positioning.OnField)
    DanHeng_PermansorTerrae = Character('丹恒·腾荒', Faction.NightDemigod, [School.Shield], 2, Positioning.OffField)
    Evernight = Character('长夜月', Faction.NightDemigod, [School.Bloodflame], 3, Positioning.OnOffField)
    Cerydra = Character('刻律德菈', Faction.NightDemigod, [School.SkillPoints], 3, Positioning.OnOffField)
    Hysilens = Character('海瑟音', Faction.DayDemigod, [School.DoT], 4, Positioning.OnField)
    Archer = Character('Archer', Faction.GalacticVoyager, [School.SkillPoints], 5, Positioning.OnField)
    Saber = Character('Saber', Faction.GalacticVoyager, [School.Energy], 3, Positioning.OnOffField)
    Phainon = Character('白厄', Faction.Other, [School.Other], 3, Positioning.OnField)
    Cipher = Character('赛飞儿', Faction.NightDemigod, [School.FollowUpATK, School.Debuff], 1, Positioning.OnField)
    Hyacine = Character('风堇', Faction.DayDemigod, [School.Heal, School.Bloodflame], 2, Positioning.OnField)
    Anaxa = Character('那刻夏', Faction.DayDemigod, [School.AoEATK], 3, Positioning.OffField)
    Castorice = Character('遐蝶', Faction.NightDemigod, [School.Bloodflame], 4, Positioning.OnField)
    Mydei = Character('万敌', Faction.NightDemigod, [School.Bloodflame], 2, Positioning.OnOffField)
    Tribbie = Character('缇宝', Faction.DayDemigod, [School.AoEATK], 2, Positioning.OnOffField)
    Aglaea = Character('阿格莱雅', Faction.DayDemigod, [School.Energy], 1, Positioning.OnField)
    TheHerta = Character('大黑塔', Faction.CosmicScholar, [School.AoEATK], 4, Positioning.OnField)
    Sunday = Character('星期日', Faction.ThePlanetOfFestivities, [School.Energy], 3, Positioning.OnField)
    Fugue = Character('忘归人', Faction.Xianzhou, [School.Break], 3, Positioning.OffField)
    Rappa = Character('乱破', Faction.GalaxyRanger, [School.Break], 1, Positioning.OnField)
    Lingsha = Character('灵砂', Faction.WolfHunt, [School.Break], 4, Positioning.OnField)
    Feixiao = Character('飞霄', Faction.WolfHunt, [School.FollowUpATK], 2, Positioning.OnField)
    Moze = Character('貊泽', Faction.WolfHunt, [School.FollowUpATK], 1, Positioning.OffField)
    Jiaoqiu = Character('椒丘', Faction.WolfHunt, [School.Heal, School.Debuff], 1, Positioning.OnField)
    Yunli = Character('云璃', Faction.WolfHunt, [School.Energy], 5, Positioning.OffField)
    Jade = Character('翡翠', Faction.IPC, [School.AoEATK], 1, Positioning.OffField)
    Firefly = Character('流萤', Faction.StellaronHounters, [School.Break], 5, Positioning.OnField)
    Boothill = Character('波提欧', Faction.GalaxyRanger, [School.Break], 4, Positioning.OnField)
    Robin = Character('知更鸟', Faction.ThePlanetOfFestivities, [School.FollowUpATK], 4, Positioning.OffField)
    Aventurine = Character('砂金', Faction.IPC, [School.Shield, School.FollowUpATK], 2, Positioning.OnField)
    Acheron = Character('黄泉', Faction.GalaxyRanger, [School.Debuff], 3, Positioning.OnField)
    Gallagher = Character('加拉赫', Faction.ThePlanetOfFestivities, [School.Break, School.Heal], 1,
                          Positioning.OnOffField)
    Sparkle = Character('花火', Faction.ThePlanetOfFestivities, [School.QuantumResonance, School.SkillPoints], 2,
                        Positioning.OffField)
    BlackSwan = Character('黑天鹅', Faction.ThePlanetOfFestivities, [School.DoT], 5, Positioning.OffField)
    DrRatio = Character('真理医生', Faction.CosmicScholar, [School.FollowUpATK], 3, Positioning.OnField)
    RuanMei = Character('阮·梅', Faction.CosmicScholar, [School.Break], 2, Positioning.OffField)
    Argenti = Character('银枝', Faction.GalacticVoyager, [School.AoEATK], 2, Positioning.OnField)
    Huohuo = Character('藿藿', Faction.Xianzhou, [School.Energy, School.Heal], 2, Positioning.OnOffField)
    TopazAndNumby = Character('托帕&账账', Faction.IPC, [School.FollowUpATK], 5, Positioning.OffField)
    Jingliu = Character('镜流', Faction.WolfHunt, [School.Bloodflame], 3, Positioning.OffField)
    FuXuan = Character('符玄', Faction.Xianzhou, [School.Heal, School.QuantumResonance], 4, Positioning.OffField)
    DanHeng_ImbibitorLunae = Character('丹恒·饮月', Faction.ExpressCohort, [School.SkillPoints], 2, Positioning.OnField)
    Kafka = Character('卡芙卡', Faction.StellaronHounters, [School.DoT], 2, Positioning.OnField)
    Blade = Character('刃', Faction.StellaronHounters, [School.Bloodflame], 1, Positioning.OffField)
    Luocha = Character('罗刹', Faction.GalacticVoyager, [School.Heal], 4, Positioning.OffField)
    SilverWolf = Character('银狼', Faction.StellaronHounters, [School.QuantumResonance], 4, Positioning.OnOffField)
    JingYuan = Character('景元', Faction.Xianzhou, [School.AoEATK], 5, Positioning.OnField)
    Seele = Character('希儿', Faction.Belobog, [School.QuantumResonance], 3, Positioning.OnField)
    Gepard = Character('杰帕德', Faction.Belobog, [School.Shield], 4, Positioning.OnField)
    Natasha = Character('娜塔莎', Faction.Belobog, [School.Heal], 3, Positioning.OffField)
    Bronya = Character('布洛妮娅', Faction.Belobog, [School.Bloodflame], 5, Positioning.OnField)
    Welt = Character('瓦尔特', Faction.ExpressCohort, [School.Debuff], 5, Positioning.OnField)
    Himeko = Character('姬子', Faction.ExpressCohort, [School.Break], 3, Positioning.OffField)
    Yanqing = Character('彦卿', Faction.Xianzhou, [School.Debuff], 3, Positioning.OffField)
    Asta = Character('艾丝妲', Faction.CosmicScholar, [School.DoT], 1, Positioning.OnField)
    Sampo = Character('桑博', Faction.GalacticVoyager, [School.DoT], 1, Positioning.OnOffField)
    March7th = Character('三月七', Faction.ExpressCohort, [School.Shield], 1, Positioning.OffField)
    Tingyun = Character('停云', Faction.Xianzhou, [School.Energy], 1, Positioning.OffField)
    Qingque = Character('青雀', Faction.Xianzhou, [School.SkillPoints], 1, Positioning.OnField)
    Pela = Character('佩拉', Faction.Belobog, [School.Debuff], 2, Positioning.OffField)
    Herta = Character('黑塔', Faction.CosmicScholar, [School.AoEATK], 1, Positioning.OnOffField)
    Trailblazer = Character('开拓者', Faction.ExpressCohort, [School.Energy], 4, Positioning.OnField)


# 角色列表
characters: dict[str, Character] = {
    '貊泽': Characters.Moze,
    '乱破': Characters.Rappa,
    '花火': Characters.Sparkle,
    '遐蝶': Characters.Castorice,
    '银枝': Characters.Argenti,
    '丹恒•饮月': Characters.DanHeng_ImbibitorLunae,
    '灵砂': Characters.Lingsha,
    '大黑塔': Characters.TheHerta,
    '托帕&账账': Characters.TopazAndNumby,
    '景元': Characters.JingYuan,
    '云璃': Characters.Yunli,
    '昔涟': Characters.Cyrene,
    '布洛妮娅': Characters.Bronya,
    '罗刹': Characters.Luocha,
    '知更鸟': Characters.Robin,
    '姬子': Characters.Himeko,
    '镜流': Characters.Jingliu,
    '真理医生': Characters.DrRatio,
    '那刻夏': Characters.Anaxa,
    '长夜月': Characters.Evernight,
    '飞霄': Characters.Feixiao,
    '阮•梅': Characters.RuanMei,
    '砂金': Characters.Aventurine,
    '缇宝': Characters.Tribbie,
    '万敌': Characters.Mydei,
    '风堇': Characters.Hyacine,
    '丹恒•腾荒': Characters.DanHeng_PermansorTerrae,
    '黑塔': Characters.Herta,
    '赛飞儿': Characters.Cipher,
    '青雀': Characters.Qingque,
    '刃': Characters.Blade,
    '翡翠': Characters.Jade,
    '瓦尔特': Characters.Welt,
    'Archer': Characters.Archer,
    '黑天鹅': Characters.BlackSwan,
    '流萤': Characters.Firefly,
    '银狼': Characters.SilverWolf,
    '杰帕德': Characters.Gepard,
    '符玄': Characters.FuXuan,
    '波提欧': Characters.Boothill,
    '彦卿': Characters.Yanqing,
    '海瑟音': Characters.Hysilens,
    'Saber': Characters.Saber,
    '希儿': Characters.Seele,
    '娜塔莎': Characters.Natasha,
    '忘归人': Characters.Fugue,
    '黄泉': Characters.Acheron,
    '星期日': Characters.Sunday,
    '白厄': Characters.Phainon,
    '刻律德拉': Characters.Cerydra,
    '刻律德': Characters.Cerydra,
    '卡芙卡': Characters.Kafka,
    '佩拉': Characters.Pela,
    '藿藿': Characters.Huohuo,
    '三月七': Characters.March7th,
    '艾丝妲': Characters.Asta,
    '桑博': Characters.Sampo,
    '停云': Characters.Tingyun,
    '椒丘': Characters.Jiaoqiu,
    '加拉赫': Characters.Gallagher,
    '阿格莱雅': Characters.Aglaea,
}
username = '开拓者'  # 请将此处改为你的角色名称


def get_character(name: str) -> Character | None:
    """根据名称获取角色信息"""
    name = name.replace('·', '•').replace('傑', '杰').replace('姐', '妲')
    if name == username:
        return Characters.Trailblazer
    return characters.get(name)
