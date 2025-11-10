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


# 角色列表
characters: dict[str, Character] = {
    '貊泽': Character('貊泽', Faction.WolfHunt, [School.FollowUpATK], 1, Positioning.OffField),
    '乱破': Character('乱破', Faction.GalaxyRanger, [School.Break], 1, Positioning.OnField),
    '花火': Character('花火', Faction.ThePlanetOfFestivities, [School.QuantumResonance, School.SkillPoints], 2,
                      Positioning.OffField),
    '遐蝶': Character('遐蝶', Faction.NightDemigod, [School.Bloodflame], 4, Positioning.OnField),
    '银枝': Character('银枝', Faction.GalacticVoyager, [School.AoEATK], 2, Positioning.OnField),
    '丹恒•饮月': Character('丹恒·饮月', Faction.ExpressCohort, [School.SkillPoints], 2, Positioning.OnField),
    '灵砂': Character('灵砂', Faction.WolfHunt, [School.Break], 4, Positioning.OnField),
    '大黑塔': Character('大黑塔', Faction.CosmicScholar, [School.AoEATK], 4, Positioning.OnField),
    '托帕&账账': Character('托帕&账账', Faction.IPC, [School.FollowUpATK], 5, Positioning.OffField),
    '景元': Character('景元', Faction.Xianzhou, [School.AoEATK], 5, Positioning.OnField),
    '云璃': Character('云璃', Faction.WolfHunt, [School.Energy], 5, Positioning.OffField),
    '昔涟': Character('昔涟', Faction.DayDemigod, [School.Other], 5, Positioning.OnField),
    '布洛妮娅': Character('布洛妮娅', Faction.Belobog, [School.Bloodflame], 5, Positioning.OnField),
    '罗刹': Character('罗刹', Faction.GalacticVoyager, [School.Heal], 4, Positioning.OffField),
    '知更鸟': Character('知更鸟', Faction.ThePlanetOfFestivities, [School.FollowUpATK], 4, Positioning.OffField),
    '姬子': Character('姬子', Faction.ExpressCohort, [School.Break], 3, Positioning.OffField),
    '镜流': Character('镜流', Faction.WolfHunt, [School.Bloodflame], 3, Positioning.OffField),
    '真理医生': Character('真理医生', Faction.CosmicScholar, [School.FollowUpATK], 3, Positioning.OnField),
    '那刻夏': Character('那刻夏', Faction.DayDemigod, [School.AoEATK], 3, Positioning.OffField),
    '长夜月': Character('长夜月', Faction.NightDemigod, [School.Bloodflame], 3, Positioning.OnOffField),
    '飞霄': Character('飞霄', Faction.WolfHunt, [School.FollowUpATK], 2, Positioning.OnField),
    '阮•梅': Character('阮·梅', Faction.CosmicScholar, [School.Break], 2, Positioning.OffField),
    '砂金': Character('砂金', Faction.IPC, [School.Shield, School.FollowUpATK], 2, Positioning.OnField),
    '缇宝': Character('缇宝', Faction.DayDemigod, [School.AoEATK], 2, Positioning.OnOffField),
    '万敌': Character('万敌', Faction.NightDemigod, [School.Bloodflame], 2, Positioning.OnOffField),
    '风堇': Character('风堇', Faction.DayDemigod, [School.Heal, School.Bloodflame], 2, Positioning.OnField),
    '丹恒•腾荒': Character('丹恒·腾荒', Faction.NightDemigod, [School.Shield], 2, Positioning.OffField),
    '黑塔': Character('黑塔', Faction.CosmicScholar, [School.AoEATK], 1, Positioning.OnOffField),
    '赛飞儿': Character('赛飞儿', Faction.NightDemigod, [School.FollowUpATK, School.Debuff], 1, Positioning.OnField),
    '青雀': Character('青雀', Faction.Xianzhou, [School.SkillPoints], 1, Positioning.OnField),
    '刃': Character('刃', Faction.StellaronHounters, [School.Bloodflame], 1, Positioning.OffField),
    '翡翠': Character('翡翠', Faction.IPC, [School.AoEATK], 1, Positioning.OffField),
    '瓦尔特': Character('瓦尔特', Faction.ExpressCohort, [School.Debuff], 5, Positioning.OnField),
    'Archer': Character('Archer', Faction.GalacticVoyager, [School.SkillPoints], 5, Positioning.OnField),
    '黑天鹅': Character('黑天鹅', Faction.ThePlanetOfFestivities, [School.DoT], 5, Positioning.OffField),
    '流萤': Character('流萤', Faction.StellaronHounters, [School.Break], 5, Positioning.OnField),
    '银狼': Character('银狼', Faction.StellaronHounters, [School.QuantumResonance], 4, Positioning.OnOffField),
    '杰帕德': Character('杰帕德', Faction.Belobog, [School.Shield], 4, Positioning.OnField),
    '符玄': Character('符玄', Faction.Xianzhou, [School.Heal, School.QuantumResonance], 4, Positioning.OffField),
    '波提欧': Character('波提欧', Faction.GalaxyRanger, [School.Break], 4, Positioning.OnField),
    '彦卿': Character('彦卿', Faction.Xianzhou, [School.Debuff], 3, Positioning.OffField),
    '海瑟音': Character('海瑟音', Faction.DayDemigod, [School.DoT], 4, Positioning.OnField),
    'Saber': Character('Saber', Faction.GalacticVoyager, [School.Energy], 3, Positioning.OnOffField),
    '希儿': Character('希儿', Faction.Belobog, [School.QuantumResonance], 3, Positioning.OnField),
    '娜塔莎': Character('娜塔莎', Faction.Belobog, [School.Heal], 3, Positioning.OffField),
    '忘归人': Character('忘归人', Faction.Xianzhou, [School.Break], 3, Positioning.OffField),
    '黄泉': Character('黄泉', Faction.GalaxyRanger, [School.Debuff], 3, Positioning.OnField),
    '星期日': Character('星期日', Faction.ThePlanetOfFestivities, [School.Energy], 3, Positioning.OnField),
    '白厄': Character('白厄', Faction.Other, [School.Other], 3, Positioning.OnField),
    '刻律德拉': Character('刻律德菈', Faction.NightDemigod, [School.SkillPoints], 2, Positioning.OnOffField),
    '卡芙卡': Character('卡芙卡', Faction.StellaronHounters, [School.DoT], 2, Positioning.OnField),
    '佩拉': Character('佩拉', Faction.Belobog, [School.Debuff], 2, Positioning.OffField),
    '藿藿': Character('藿藿', Faction.Xianzhou, [School.Energy, School.Heal], 2, Positioning.OnOffField),
    '三月七': Character('三月七', Faction.ExpressCohort, [School.Shield], 1, Positioning.OffField),
    '艾丝妲': Character('艾丝妲', Faction.CosmicScholar, [School.DoT], 1, Positioning.OnField),
    '桑博': Character('桑博', Faction.GalacticVoyager, [School.DoT], 1, Positioning.OnOffField),
    '停云': Character('停云', Faction.Xianzhou, [School.Energy], 1, Positioning.OffField),
    '椒丘': Character('椒丘', Faction.WolfHunt, [School.Heal, School.Debuff], 1, Positioning.OnField),
    '加拉赫': Character('加拉赫', Faction.ThePlanetOfFestivities, [School.Break, School.Heal], 1,
                        Positioning.OnOffField),
    '阿格莱雅': Character('阿格莱雅', Faction.DayDemigod, [School.Energy], 1, Positioning.OnField),
}
username = '雪影'
Trailblazer = Character('开拓者', Faction.ExpressCohort, [School.Energy], 4, Positioning.OnField)


def get_character(name: str) -> Character | None:
    """根据名称获取角色信息"""
    name=name.replace('·', '•').replace('傑','杰')
    if name == username:
        return Trailblazer
    return characters.get(name)
