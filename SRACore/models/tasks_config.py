#!/usr/bin/env python3
"""
自动生成的Python类
源文件: TasksConfig.cs
"""

from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class StartGameConfig:
    """自动生成的 StartGameConfig 类"""

    isEnabled: bool = True
    gameChannel: int = 0
    gamePath: str = ""
    gameServer: int = 0
    isUseGlobalGamePath: bool = True
    launchDelay: int = 5
    isAutoLogin: bool = True
    isReLogin: bool = True
    EncryptedPassword: str = ""
    EncryptedUsername: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "enabled": self.isEnabled,
            "game.channel": self.gameChannel,
            "game.path": self.gamePath,
            "game.server": self.gameServer,
            "game.useGlobalPath": self.isUseGlobalGamePath,
            "game.launchDelay": self.launchDelay,
            "autologin": self.isAutoLogin,
            "relogin": self.isReLogin,
            "password": self.EncryptedPassword,
            "username": self.EncryptedUsername
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "isEnabled": data.get("enabled", True),
            "gameChannel": data.get("game.channel", 0),
            "gamePath": data.get("game.path", ""),
            "gameServer": data.get("game.server", 0),
            "isUseGlobalGamePath": data.get("game.useGlobalPath", True),
            "launchDelay": data.get("game.launchDelay", 5),
            "isAutoLogin": data.get("autologin", True),
            "isReLogin": data.get("relogin", True),
            "EncryptedPassword": data.get("password", ""),
            "EncryptedUsername": data.get("username", "")
        })

@dataclass
class TrailblazePowerConfig:
    """自动生成的 TrailblazePowerConfig 类"""

    isEnabled: bool = False
    gardenOfPlentyLevel1: int = 0
    gardenOfPlentyLevel2: int = 0
    isUseAssistant: bool = False
    isUseBuildTarget: bool = False
    isActivityEnabled: bool = False
    planarFissureLevel: int = 0
    realmOfTheStrangeLevel: int = 0
    replenishTimes: int = 0
    isReplenishEnabled: bool = False
    replenishWay: int = 0
    TaskList: list[TrailblazePowerTaskItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "enabled": self.isEnabled,
            "activity.gardenOfPlenty.level1": self.gardenOfPlentyLevel1,
            "activity.gardenOfPlenty.level2": self.gardenOfPlentyLevel2,
            "useAssistant": self.isUseAssistant,
            "useBuildTarget": self.isUseBuildTarget,
            "activity.enabled": self.isActivityEnabled,
            "activity.planarFissure.level": self.planarFissureLevel,
            "activity.realmOfTheStrange.level": self.realmOfTheStrangeLevel,
            "replenish.times": self.replenishTimes,
            "replenish.enabled": self.isReplenishEnabled,
            "replenish.way": self.replenishWay,
            "tasklist": self.TaskList
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "isEnabled": data.get("enabled", False),
            "gardenOfPlentyLevel1": data.get("activity.gardenOfPlenty.level1", 0),
            "gardenOfPlentyLevel2": data.get("activity.gardenOfPlenty.level2", 0),
            "isUseAssistant": data.get("useAssistant", False),
            "isUseBuildTarget": data.get("useBuildTarget", False),
            "isActivityEnabled": data.get("activity.enabled", False),
            "planarFissureLevel": data.get("activity.planarFissure.level", 0),
            "realmOfTheStrangeLevel": data.get("activity.realmOfTheStrange.level", 0),
            "replenishTimes": data.get("replenish.times", 0),
            "isReplenishEnabled": data.get("replenish.enabled", False),
            "replenishWay": data.get("replenish.way", 0),
            "TaskList": [TrailblazePowerTaskItem.from_dict(item) for item in data.get("tasklist", list())]
        })

@dataclass
class ReceiveRewardsConfig:
    """自动生成的 ReceiveRewardsConfig 类"""

    isEnabled: bool = False
    isAssignmentsEnabled: bool = True
    isDailyTrainingEnabled: bool = True
    isGiftOfOdysseyEnabled: bool = True
    isMailEnabled: bool = True
    isNamelessHonorEnabled: bool = True
    isRedeemCodeEnabled: bool = False
    isTrailblazeProfileEnabled: bool = True
    redeemCodes: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "enabled": self.isEnabled,
            "rewards.assignments": self.isAssignmentsEnabled,
            "rewards.dailyTraining": self.isDailyTrainingEnabled,
            "rewards.giftOfOdyssey": self.isGiftOfOdysseyEnabled,
            "rewards.mail": self.isMailEnabled,
            "rewards.namelessHonor": self.isNamelessHonorEnabled,
            "rewards.redeemCode": self.isRedeemCodeEnabled,
            "rewards.trailblazeProfile": self.isTrailblazeProfileEnabled,
            "redeemCodes": self.redeemCodes
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "isEnabled": data.get("enabled", False),
            "isAssignmentsEnabled": data.get("rewards.assignments", True),
            "isDailyTrainingEnabled": data.get("rewards.dailyTraining", True),
            "isGiftOfOdysseyEnabled": data.get("rewards.giftOfOdyssey", True),
            "isMailEnabled": data.get("rewards.mail", True),
            "isNamelessHonorEnabled": data.get("rewards.namelessHonor", True),
            "isRedeemCodeEnabled": data.get("rewards.redeemCode", False),
            "isTrailblazeProfileEnabled": data.get("rewards.trailblazeProfile", True),
            "redeemCodes": data.get("redeemCodes", "")
        })

@dataclass
class CosmicStrifeConfig:
    """自动生成的 CosmicStrifeConfig 类"""

    isEnabled: bool = False
    isCurrencyWarsEnabled: bool = False
    currencyWarsDifficulty: int = 0
    currencyWarsMode: int = 0
    currencyWarsRerollBossAffixes: str = ""
    currencyWarsRerollBossNames: str = ""
    currencyWarsRerollInvestEnvironments: str = ""
    currencyWarsRerollInvestStrategies: str = ""
    currencyWarsRuntimes: int = 0
    currencyWarsStrategy: str = "template"
    currencyWarsStrategyIndex: int = 0
    currencyWarsUsername: str = ""
    isDivergentUniverseEnabled: bool = False
    divergentUniverseMode: int = 0
    divergentUniverseRuntimes: int = 0
    isDivergentUniverseUseTechnique: bool = False
    isPointRewardsEnabled: bool = False

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "enabled": self.isEnabled,
            "currencyWars.enabled": self.isCurrencyWarsEnabled,
            "currencyWars.difficulty": self.currencyWarsDifficulty,
            "currencyWars.mode": self.currencyWarsMode,
            "currencyWars.reroll.bossAffixes": self.currencyWarsRerollBossAffixes,
            "currencyWars.reroll.bossNames": self.currencyWarsRerollBossNames,
            "currencyWars.reroll.investEnvironments": self.currencyWarsRerollInvestEnvironments,
            "currencyWars.reroll.investStrategies": self.currencyWarsRerollInvestStrategies,
            "currencyWars.runtimes": self.currencyWarsRuntimes,
            "currencyWars.strategy": self.currencyWarsStrategy,
            "currencyWars.strategyIndex": self.currencyWarsStrategyIndex,
            "currencyWars.username": self.currencyWarsUsername,
            "divergentUniverse.enabled": self.isDivergentUniverseEnabled,
            "divergentUniverse.mode": self.divergentUniverseMode,
            "divergentUniverse.runtimes": self.divergentUniverseRuntimes,
            "divergentUniverse.useTechnique": self.isDivergentUniverseUseTechnique,
            "pointRewards.enabled": self.isPointRewardsEnabled
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "isEnabled": data.get("enabled", False),
            "isCurrencyWarsEnabled": data.get("currencyWars.enabled", False),
            "currencyWarsDifficulty": data.get("currencyWars.difficulty", 0),
            "currencyWarsMode": data.get("currencyWars.mode", 0),
            "currencyWarsRerollBossAffixes": data.get("currencyWars.reroll.bossAffixes", ""),
            "currencyWarsRerollBossNames": data.get("currencyWars.reroll.bossNames", ""),
            "currencyWarsRerollInvestEnvironments": data.get("currencyWars.reroll.investEnvironments", ""),
            "currencyWarsRerollInvestStrategies": data.get("currencyWars.reroll.investStrategies", ""),
            "currencyWarsRuntimes": data.get("currencyWars.runtimes", 0),
            "currencyWarsStrategy": data.get("currencyWars.strategy", "template"),
            "currencyWarsStrategyIndex": data.get("currencyWars.strategyIndex", 0),
            "currencyWarsUsername": data.get("currencyWars.username", ""),
            "isDivergentUniverseEnabled": data.get("divergentUniverse.enabled", False),
            "divergentUniverseMode": data.get("divergentUniverse.mode", 0),
            "divergentUniverseRuntimes": data.get("divergentUniverse.runtimes", 0),
            "isDivergentUniverseUseTechnique": data.get("divergentUniverse.useTechnique", False),
            "isPointRewardsEnabled": data.get("pointRewards.enabled", False)
        })

@dataclass
class MissionAccomplishedConfig:
    """自动生成的 MissionAccomplishedConfig 类"""

    isEnabled: bool = False
    isExitApp: bool = False
    isExitGame: bool = False
    isLogout: bool = False
    isShutdown: bool = False
    isSleep: bool = False

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "enabled": self.isEnabled,
            "exitApp": self.isExitApp,
            "exitGame": self.isExitGame,
            "logout": self.isLogout,
            "shutdown": self.isShutdown,
            "sleep": self.isSleep
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "isEnabled": data.get("enabled", False),
            "isExitApp": data.get("exitApp", False),
            "isExitGame": data.get("exitGame", False),
            "isLogout": data.get("logout", False),
            "isShutdown": data.get("shutdown", False),
            "isSleep": data.get("sleep", False)
        })

@dataclass
class TrailblazePowerTaskItem:
    """自动生成的 TrailblazePowerTaskItem 类"""

    Name: str = ""
    Id: str = ""
    Level: int = 0
    LevelName: str = ""
    Count: int = 1
    RunTimes: int = 0
    AutoDetect: bool = False

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.Name,
            "id": self.Id,
            "level": self.Level,
            "levelName": self.LevelName,
            "count": self.Count,
            "runtimes": self.RunTimes,
            "autoDetect": self.AutoDetect
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "Name": data.get("name", ""),
            "Id": data.get("id", ""),
            "Level": data.get("level", 0),
            "LevelName": data.get("levelName", ""),
            "Count": data.get("count", 1),
            "RunTimes": data.get("runtimes", 0),
            "AutoDetect": data.get("autoDetect", False)
        })

@dataclass
class TasksConfig:
    """自动生成的 TasksConfig 类"""

    Name: str = "Default"
    StartGame: StartGameConfig = field(default_factory=StartGameConfig)
    TrailblazePower: TrailblazePowerConfig = field(default_factory=TrailblazePowerConfig)
    ReceiveRewards: ReceiveRewardsConfig = field(default_factory=ReceiveRewardsConfig)
    CosmicStrife: CosmicStrifeConfig = field(default_factory=CosmicStrifeConfig)
    MissionAccomplished: MissionAccomplishedConfig = field(default_factory=MissionAccomplishedConfig)
    Version: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.Name,
            "startGame": self.StartGame.to_dict(),
            "trailblazePower": self.TrailblazePower.to_dict(),
            "receiveRewards": self.ReceiveRewards.to_dict(),
            "cosmicStrife": self.CosmicStrife.to_dict(),
            "missionAccomplished": self.MissionAccomplished.to_dict(),
            "version": self.Version
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "Name": data.get("name", "Default"),
            "StartGame": StartGameConfig.from_dict(data.get("startGame", {})),
            "TrailblazePower": TrailblazePowerConfig.from_dict(data.get("trailblazePower", {})),
            "ReceiveRewards": ReceiveRewardsConfig.from_dict(data.get("receiveRewards", {})),
            "CosmicStrife": CosmicStrifeConfig.from_dict(data.get("cosmicStrife", {})),
            "MissionAccomplished": MissionAccomplishedConfig.from_dict(data.get("missionAccomplished", {})),
            "Version": data.get("version", 0)
        })
