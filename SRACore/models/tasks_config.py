#!/usr/bin/env python3
"""
自动生成的 Pydantic 模型
源文件: SRAFrontend/SRAFrontend/Models/TasksConfig.cs

SRACore 运行时与 SRAServer 的 OpenAPI 组件共用这一套模型定义，请勿手工编辑：
改动请修改对应的 C# 模型并执行 `npm run modelgen`。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    """生成模型基类：允许按字段名或 JSON 别名构造，并保留未知键。"""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

class StartGameConfig(_Model):
    """启动游戏配置。"""

    isEnabled: bool = Field(True, alias="enabled", description='是否启用启动游戏任务')
    gameChannel: int = Field(0, alias="game.channel", description='游戏渠道，0-国服，1-B服，2-国际服')
    gamePath: str = Field("", alias="game.path", description='游戏启动程序路径')
    gameServer: int = Field(0, alias="game.server", description='国际服服务器，0-亚洲，1-欧洲，2-美洲，3-台港澳，仅国际服有效')
    isUseGlobalGamePath: bool = Field(True, alias="game.useGlobalPath", description='是否使用全局设置中的游戏路径')
    launchDelay: int = Field(5, alias="game.launchDelay", description='启动游戏后的等待延迟（秒）')
    isAutoLogin: bool = Field(True, alias="autologin", description='是否自动登录账号')
    isReLogin: bool = Field(True, alias="relogin", description='是否在登录失败后自动重新登录')
    EncryptedPassword: str = Field("", alias="password", description='加密存储的账号密码')
    EncryptedUsername: str = Field("", alias="username", description='加密存储的账号用户名')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "StartGameConfig":
        """从字典创建对象"""
        return cls.model_validate(data)

class ReceiveRewardsConfig(_Model):
    """领取奖励配置。"""

    isEnabled: bool = Field(False, alias="enabled", description='是否启用领取奖励任务')
    isAssignmentsEnabled: bool = Field(True, alias="rewards.assignments", description='是否领取派遣奖励')
    isDailyTrainingEnabled: bool = Field(True, alias="rewards.dailyTraining", description='是否领取每日实训奖励')
    isGiftOfOdysseyEnabled: bool = Field(True, alias="rewards.giftOfOdyssey", description='是否领取巡星之礼奖励')
    isMailEnabled: bool = Field(True, alias="rewards.mail", description='是否领取邮件奖励')
    isNamelessHonorEnabled: bool = Field(True, alias="rewards.namelessHonor", description='是否领取无名勋礼奖励')
    isRedeemCodeEnabled: bool = Field(False, alias="rewards.redeemCode", description='是否执行兑换码兑换')
    isTrailblazeProfileEnabled: bool = Field(True, alias="rewards.trailblazeProfile", description='是否领取漫游签证奖励')
    redeemCodes: str = Field("", alias="redeemCodes", description='兑换码列表，格式为：兑换码1 兑换码2 兑换码3；任务运行时会自动从官网拉取最新兑换码一并兑换')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "ReceiveRewardsConfig":
        """从字典创建对象"""
        return cls.model_validate(data)

class CosmicStrifeConfig(_Model):
    """旷宇纷争配置。"""

    isEnabled: bool = Field(False, alias="enabled", description='是否启用旷宇纷争任务')
    isCurrencyWarsEnabled: bool = Field(False, alias="currencyWars.enabled", description='货币战争总开关')
    currencyWarsDifficulty: int = Field(0, alias="currencyWars.difficulty", description='货币战争难度，0-最低难度，1-最高难度，2-当前难度')
    currencyWarsMode: int = Field(0, alias="currencyWars.mode", description='货币战争模式，0-标准博弈，1-超频博弈，2-刷开局')
    isCurrencyWarsPointRewardsEnabled: bool = Field(False, alias="currencyWars.pointRewards", description='启用后，若旷宇纷争积分奖励已满则跳过货币战争任务')
    currencyWarsRerollBossAffixes: str = Field("", alias="currencyWars.reroll.bossAffixes", description='货币战争刷开局时的Boss词缀')
    currencyWarsRerollBossNames: str = Field("", alias="currencyWars.reroll.bossNames", description='货币战争刷开局时的Boss名称')
    currencyWarsRerollInvestEnvironments: str = Field("", alias="currencyWars.reroll.investEnvironments", description='货币战争刷开局时的投资环境')
    currencyWarsRerollInvestStrategies: str = Field("", alias="currencyWars.reroll.investStrategies", description='货币战争刷开局时的投资策略')
    currencyWarsRuntimes: int = Field(1, alias="currencyWars.runtimes", description='货币战争刷开局时的运行次数')
    currencyWarsStrategy: str = Field("template", alias="currencyWars.strategy", description='货币战争使用的攻略名称')
    currencyWarsStrategyIndex: int = Field(0, alias="currencyWars.strategyIndex", description='货币战争使用的攻略索引')
    currencyWarsUsername: str = Field("", alias="currencyWars.username", description='货币战争中开拓者的名字')
    isDivergentUniverseEnabled: bool = Field(False, alias="divergentUniverse.enabled", description='差分宇宙总开关')
    divergentUniverseMode: int = Field(0, alias="divergentUniverse.mode", description='差分宇宙模式：0-刷单层，1-完整对局')
    divergentUniverseRuntimes: int = Field(0, alias="divergentUniverse.runtimes", description='差分宇宙运行次数')
    isDivergentUniverseUseTechnique: bool = Field(False, alias="divergentUniverse.useTechnique", description='差分宇宙是否使用秘技速刷')
    isPointRewardsEnabled: bool = Field(False, alias="pointRewards.enabled", description='是否启用积分奖励，启用后当达到周积分上限时跳过此任务')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "CosmicStrifeConfig":
        """从字典创建对象"""
        return cls.model_validate(data)

class MissionAccomplishedConfig(_Model):
    """任务完成后操作。"""

    isEnabled: bool = Field(False, alias="enabled", description='是否启用任务完成后操作')
    isExitApp: bool = Field(False, alias="exitApp", description='完成任务后是否退出应用')
    isExitGame: bool = Field(False, alias="exitGame", description='完成任务后是否退出游戏')
    isLogoff: bool = Field(False, alias="logoff", description='完成任务后是否注销当前用户')
    isLogout: bool = Field(False, alias="logout", description='完成任务后是否登出账号')
    isShutdown: bool = Field(False, alias="shutdown", description='完成任务后是否关机')
    isSleep: bool = Field(False, alias="sleep", description='完成任务后是否睡眠')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "MissionAccomplishedConfig":
        """从字典创建对象"""
        return cls.model_validate(data)

class TrailblazePowerTaskItem(_Model):
    """任务列表。"""

    Name: str = Field("", alias="name", description='任务名称')
    Id: str = Field("", alias="id", description='任务标识ID，如 calyx_golden、echo_of_war')
    Level: int = Field(0, alias="level", description='关卡等级')
    LevelName: str = Field("", alias="levelName", description='关卡名称')
    Count: int = Field(1, alias="count", description='手动模式下单个任务的执行次数')
    RunTimes: int = Field(0, alias="runtimes", description='手动模式下的执行轮数')
    AutoDetect: bool = Field(False, alias="autoDetect", description='是否根据剩余体力自动分配执行次数')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "TrailblazePowerTaskItem":
        """从字典创建对象"""
        return cls.model_validate(data)

class TrailblazePowerConfig(_Model):
    """体力配置。"""

    isEnabled: bool = Field(False, alias="enabled", description='是否启用开拓力任务')
    gardenOfPlentyLevel1: int = Field(0, alias="activity.gardenOfPlenty.level1", description='花藏繁生中拟造花萼（金）的目标关卡')
    gardenOfPlentyLevel2: int = Field(0, alias="activity.gardenOfPlenty.level2", description='花藏繁生中拟造花萼（赤）的目标关卡')
    isUseAssistant: bool = Field(False, alias="useAssistant", description='是否使用支援角色')
    isUseBuildTarget: bool = Field(False, alias="useBuildTarget", description='是否启用培养目标，开启后将优先完成培养目标')
    isMaterialPriority: bool = Field(False, alias="materialPriority", description='培养目标材料优先：识别到材料型副本时跳过饰品提取与侵蚀隧洞，未识别到时仍保留')
    isActivityEnabled: bool = Field(False, alias="activity.enabled", description='是否启用多倍活动检测，启用后将优先刷取花藏繁生/异器盈界/位面分裂副本')
    planarFissureLevel: int = Field(0, alias="activity.planarFissure.level", description='位面分裂的目标关卡')
    realmOfTheStrangeLevel: int = Field(0, alias="activity.realmOfTheStrange.level", description='异器盈界的目标关卡')
    replenishTimes: int = Field(0, alias="replenish.times", description='补充体力的次数')
    isReplenishEnabled: bool = Field(False, alias="replenish.enabled", description='是否补充体力')
    replenishWay: int = Field(0, alias="replenish.way", description='补充体力的方式，0-后备开拓力，1-燃料，2-星琼')
    TaskList: list[TrailblazePowerTaskItem] = Field(default_factory=list, alias="tasklist", description='任务列表')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "TrailblazePowerConfig":
        """从字典创建对象"""
        return cls.model_validate(data)

class TasksConfig(_Model):
    """自动生成的 TasksConfig 类"""

    Name: str = Field("Default", alias="name", description='任务配置名称')
    StartGame: StartGameConfig = Field(default_factory=StartGameConfig, alias="startGame", description='启动游戏配置')
    TrailblazePower: TrailblazePowerConfig = Field(default_factory=TrailblazePowerConfig, alias="trailblazePower", description='体力配置')
    ReceiveRewards: ReceiveRewardsConfig = Field(default_factory=ReceiveRewardsConfig, alias="receiveRewards", description='领取奖励配置')
    CosmicStrife: CosmicStrifeConfig = Field(default_factory=CosmicStrifeConfig, alias="cosmicStrife", description='旷宇纷争配置')
    MissionAccomplished: MissionAccomplishedConfig = Field(default_factory=MissionAccomplishedConfig, alias="missionAccomplished", description='任务完成后操作')
    Version: int = Field(4, alias="version", description='配置文件版本号')

    def to_dict(self) -> dict:
        """转换为字典（键为 C# 侧的 JSON 名称）"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> "TasksConfig":
        """从字典创建对象"""
        return cls.model_validate(data)
