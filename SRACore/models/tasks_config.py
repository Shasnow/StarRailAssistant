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
    replenishMode: int = 0
    replenishTimes: int = 0
    replenishWay: int = 0
    isUseAssistant: bool = False
    isUseBuildTarget: bool = False
    TaskList: list[TrailblazePowerTaskItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "enabled": self.isEnabled,
            "replenish.enabled": self.isReplenishEnabled,
            "replenish.mode": self.replenishMode,
            "replenish.times": self.replenishTimes,
            "replenish.way": self.replenishWay,
            "useAssistant": self.isUseAssistant,
            "useBuildTarget": self.isUseBuildTarget,
            "tasklist": self.TaskList
        }

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        return cls(**{
            "isEnabled": data.get("enabled", False),
            "isReplenishEnabled": data.get("replenish.enabled", False),
            "replenishMode": data.get("replenish.mode", 0),
            "replenishTimes": data.get("replenish.times", 0),
            "replenishWay": data.get("replenish.way", 0),
            "isUseAssistant": data.get("useAssistant", False),
            "isUseBuildTarget": data.get("useBuildTarget", False),
            "TaskList": data.get("tasklist", list())
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
    isDifferentialUniverseEnabled: bool = False
    differentialUniverseMode: int = 0
    differentialUniverseRuntimes: int = 0
    isDifferentialUniverseUseTechnique: bool = False
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
            "differentialUniverse.enabled": self.isDifferentialUniverseEnabled,
            "differentialUniverse.mode": self.differentialUniverseMode,
            "differentialUniverse.runtimes": self.differentialUniverseRuntimes,
            "differentialUniverse.useTechnique": self.isDifferentialUniverseUseTechnique,
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
            "isDifferentialUniverseEnabled": data.get("differentialUniverse.enabled", False),
            "differentialUniverseMode": data.get("differentialUniverse.mode", 0),
            "differentialUniverseRuntimes": data.get("differentialUniverse.runtimes", 0),
            "isDifferentialUniverseUseTechnique": data.get("differentialUniverse.useTechnique", False),
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
