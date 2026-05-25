#!/usr/bin/env python3
"""
自动生成的Python类
源文件: TasksConfig.cs
"""

from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class TasksConfig:
    """自动生成的 TasksConfig 类"""

    Name: str = "Default"
    StartGame: StartGameConfig = None
    TrailblazePower: TrailblazePowerConfig = None
    ReceiveRewards: ReceiveRewardsConfig = None
    CosmicStrife: CosmicStrifeConfig = None
    MissionAccomplished: MissionAccomplishedConfig = None
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

@dataclass
class StartGameConfig:
    """自动生成的 StartGameConfig 类"""

    isEnabled: bool = True
    gameChannel: int = 0
    gamePath: str = ""
    isUseGlobalGamePath: bool = True
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
            "game.useGlobalPath": self.isUseGlobalGamePath,
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
            "isUseGlobalGamePath": data.get("game.useGlobalPath", True),
            "isAutoLogin": data.get("autologin", True),
            "isReLogin": data.get("relogin", True),
            "EncryptedPassword": data.get("password", ""),
            "EncryptedUsername": data.get("username", "")
        })

@dataclass
class TrailblazePowerConfig:
    """自动生成的 TrailblazePowerConfig 类"""

    isEnabled: bool = False
    isReplenishEnabled: bool = False
    replenishTimes: int = 0
    replenishWay: int = 0
    isUseAssistant: bool = False
    isUseBuildTarget: bool = False
    TaskList: list[TrailblazePowerTaskItem] = field(default_factory=list)
    isActivityEnabled: bool = False
    gardenOfPlentyLevel1: int = 0
    gardenOfPlentyLevel2: int = 0
    planarFissureLevel: int = 0
    realmOfTheStrangeLevel: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "enabled": self.isEnabled,
            "replenish.enabled": self.isReplenishEnabled,
            "replenish.times": self.replenishTimes,
            "replenish.way": self.replenishWay,
            "useAssistant": self.isUseAssistant,
            "useBuildTarget": self.isUseBuildTarget,
            "tasklist": self.TaskList,
            "activity.enabled": self.isActivityEnabled,
            "activity.gardenOfPlenty.level1": self.gardenOfPlentyLevel1,
            "activity.gardenOfPlenty.level2": self.gardenOfPlentyLevel2,
            "activity.planarFissure.level": self.planarFissureLevel,
            "activity.realmOfTheStrange.level": self.realmOfTheStrangeLevel
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "isEnabled": data.get("enabled", False),
            "isReplenishEnabled": data.get("replenish.enabled", False),
            "replenishTimes": data.get("replenish.times", 0),
            "replenishWay": data.get("replenish.way", 0),
            "isUseAssistant": data.get("useAssistant", False),
            "isUseBuildTarget": data.get("useBuildTarget", False),
            "TaskList": [TrailblazePowerTaskItem.from_dict(item) for item in data.get("tasklist", list())],
            "isActivityEnabled": data.get("activity.enabled", False),
            "gardenOfPlentyLevel1": data.get("activity.gardenOfPlenty.level1", 0),
            "gardenOfPlentyLevel2": data.get("activity.gardenOfPlenty.level2", 0),
            "planarFissureLevel": data.get("activity.planarFissure.level", 0),
            "realmOfTheStrangeLevel": data.get("activity.realmOfTheStrange.level", 0)
        })

@dataclass
class ReceiveRewardsConfig:
    """自动生成的 ReceiveRewardsConfig 类"""

    isEnabled: bool = False
    redeemCodes: str = ""
    Rewards: list[bool] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "enabled": self.isEnabled,
            "redeemCodes": self.redeemCodes,
            "rewards": self.Rewards
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "isEnabled": data.get("enabled", False),
            "redeemCodes": data.get("redeemCodes", ""),
            "Rewards": data.get("rewards", list())
        })

@dataclass
class CosmicStrifeConfig:
    """自动生成的 CosmicStrifeConfig 类"""

    isEnabled: bool = False
    isPointRewardsEnabled: bool = False
    isDivergentUniverseEnabled: bool = False
    divergentUniverseMode: int = 0
    divergentUniverseRuntimes: int = 0
    isDivergentUniverseUseTechnique: bool = False
    isCurrencyWarsEnabled: bool = False
    currencyWarsMode: int = 0
    currencyWarsDifficulty: int = 0
    currencyWarsPolicy: int = 0
    currencyWarsRerollBossAffixes: str = ""
    currencyWarsRerollBossNames: str = ""
    currencyWarsRerollInvestEnvironments: str = ""
    currencyWarsRerollInvestStrategies: str = ""
    currencyWarsRuntimes: int = 0
    currencyWarsStrategy: str = "template"
    currencyWarsStrategyIndex: int = 0
    currencyWarsUsername: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "enabled": self.isEnabled,
            "pointRewards.enabled": self.isPointRewardsEnabled,
            "divergentUniverse.enabled": self.isDivergentUniverseEnabled,
            "divergentUniverse.mode": self.divergentUniverseMode,
            "divergentUniverse.runtimes": self.divergentUniverseRuntimes,
            "divergentUniverse.useTechnique": self.isDivergentUniverseUseTechnique,
            "currencyWars.enabled": self.isCurrencyWarsEnabled,
            "currencyWars.mode": self.currencyWarsMode,
            "currencyWars.difficulty": self.currencyWarsDifficulty,
            "currencyWars.policy": self.currencyWarsPolicy,
            "currencyWars.reroll.bossAffixes": self.currencyWarsRerollBossAffixes,
            "currencyWars.reroll.bossNames": self.currencyWarsRerollBossNames,
            "currencyWars.reroll.investEnvironments": self.currencyWarsRerollInvestEnvironments,
            "currencyWars.reroll.investStrategies": self.currencyWarsRerollInvestStrategies,
            "currencyWars.runtimes": self.currencyWarsRuntimes,
            "currencyWars.strategy": self.currencyWarsStrategy,
            "currencyWars.strategyIndex": self.currencyWarsStrategyIndex,
            "currencyWars.username": self.currencyWarsUsername
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "isEnabled": data.get("enabled", False),
            "isPointRewardsEnabled": data.get("pointRewards.enabled", False),
            "isDivergentUniverseEnabled": data.get("divergentUniverse.enabled", False),
            "divergentUniverseMode": data.get("divergentUniverse.mode", 0),
            "divergentUniverseRuntimes": data.get("divergentUniverse.runtimes", 0),
            "isDivergentUniverseUseTechnique": data.get("divergentUniverse.useTechnique", False),
            "isCurrencyWarsEnabled": data.get("currencyWars.enabled", False),
            "currencyWarsMode": data.get("currencyWars.mode", 0),
            "currencyWarsDifficulty": data.get("currencyWars.difficulty", 0),
            "currencyWarsPolicy": data.get("currencyWars.policy", 0),
            "currencyWarsRerollBossAffixes": data.get("currencyWars.reroll.bossAffixes", ""),
            "currencyWarsRerollBossNames": data.get("currencyWars.reroll.bossNames", ""),
            "currencyWarsRerollInvestEnvironments": data.get("currencyWars.reroll.investEnvironments", ""),
            "currencyWarsRerollInvestStrategies": data.get("currencyWars.reroll.investStrategies", ""),
            "currencyWarsRuntimes": data.get("currencyWars.runtimes", 0),
            "currencyWarsStrategy": data.get("currencyWars.strategy", "template"),
            "currencyWarsStrategyIndex": data.get("currencyWars.strategyIndex", 0),
            "currencyWarsUsername": data.get("currencyWars.username", "")
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
