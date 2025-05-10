#   <StarRailAssistant:An automated program that helps you complete daily tasks of StarRail.>
#   Copyright © <2024> <Shasnow>

#   This file is part of StarRailAssistant.

#   StarRailAssistant is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the Free Software Foundation,
#   either version 3 of the License, or (at your option) any later version.

#   StarRailAssistant is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#   without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#   See the GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License along with StarRailAssistant.
#   If not, see <https://www.gnu.org/licenses/>.

#   yukikage@qq.com

"""
崩坏：星穹铁道助手
v0.7.0
作者：雪影
配置相关操作
"""
import json
import os
from pathlib import Path

from SRACore.utils import Encryption

config_list_1 = [
    "Mission",
    "StartGame",
    "TrailBlazePower",
    "ReceiveRewards",
    "RedeemCode",
    "Replenish",
    "Support",
    "OrnamentExtraction",
    "CalyxGolden",
    "CalyxCrimson",
    "StagnantShadow",
    "CaverOfCorrosion",
    "EchoOfWar",
    "AfterMission",
    "DivergentUniverse",
]
config_list_2 = {
    "Mission": [
        ["startGame", False],
        ["trailBlazePower", False],
        ["trailBlazerProfile", True],
        ["assignment", True],
        ["mail", True],
        ["dailyTraining", True],
        ["namelessHonor", True],
        ["giftOfOdyssey", False],
        ["redeemCode", False],
        ["afterMission", False],
        ["simulatedUniverse", False]
    ],
    "StartGame": [
        ["autoLogin", False],
        ["launcher", False],
        ["gamePath", ""],
        ["pathType", "StarRail"],
        ["channel", 0],
        ["user", ''],
        ["savePassword", False]
    ],
    "TrailBlazePower": [["taskList", []]],
    "ReceiveRewards": [["enable", False]],
    "RedeemCode": [
        ["codeList", []],
    ],
    "Replenish": [
        ["enable", False],
        ["way", 1],
        ["runTimes", 1],
    ],
    "Support": [
        ["enable", False],
        ["role", ''],
        ["changeLineup", False]
    ],
    "OrnamentExtraction": [
        ["level", 1],
        ["runTimes", 1],
    ],
    "CalyxGolden": [
        ["level", 1],
        ["singleTimes", 1],
        ["runTimes", 1],
    ],
    "CalyxCrimson": [
        ["level", 1],
        ["singleTimes", 1],
        ["runTimes", 1],
    ],
    "StagnantShadow": [
        ["level", 1],
        ["runTimes", 1],
    ],
    "CaverOfCorrosion": [
        ["level", 1],
        ["runTimes", 1],
    ],
    "EchoOfWar": [
        ["runTimes", 1],
        ["level", 1],
    ],
    "AfterMission": [
        ["logout", False],
        ["quitGame", False],
        ["exitSRA", False],
        ["shutdown", False],
        ["sleep", False],
        ["logout", False]
    ],
    "DivergentUniverse": [
        ["enable", False],
        ["mode", 0],
        ["times", 1],
        ["policy", 0],
    ],
}
global_config_list1 = [
    "Config",
    "Settings",
    "Notification",
]
global_config_list2 = {
    "Config": [
        ["currentConfig", 0],
        ["configList", ["Default"]],
        ["next", False],
        ["max",3]
    ],
    "Settings": [
        ["F1", "f1"],
        ["F2", "f2"],
        ["F3", "f3"],
        ["F4", "f4"],
        ["hotkeys",["ctrl+shift+alt+s","ctrl+shift+alt+h"]],
        ["startup", False],
        ["autoUpdate", True],
        ["threadSafety", False],
        ["exitWhenClose",False],
        ["confidence", 0.9],
        ["zoom", 1.5],
        ["mirrorchyanCDK", ""],
        ["uiSize", "1200x800"],
        ["uiLocation", "100x100"],
    ],
    "Notification": [
        ["enable", True],
        ["system", True],
        ["email", False],
        ["SMTP", ""],
        ["port", 465],
        ["sender", ""],
        ["authorizationCode", ""],
        ["receiver", ""],
    ]
        
}


def init() -> None:
    if not any(Path("data").glob("config-*")):
        os.makedirs("data", exist_ok=True)
        addConfig("Default")
    if not os.path.exists("data/globals.json"):
        with open("data/globals.json", "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)

    is_changed = False
    with open("data/globals.json", "r", encoding="utf-8") as f:
        gbl: dict = json.load(f)
        for item in global_config_list1:
            if item not in gbl:
                gbl[item] = {}
                is_changed = True
            for config_list in global_config_list2[item]:
                if not config_list[0] in gbl[item]:
                    gbl[item][config_list[0]] = config_list[1]
                    is_changed = True
        configs = gbl["Config"]["configList"]
    if is_changed:
        with open("data/globals.json", "w", encoding="utf-8") as f:
            json.dump(gbl, f, indent=4, ensure_ascii=False)
        is_changed = False

    for name in configs:
        with open(f"data/config-{name}.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        for index in config_list_1:
            if not index in config:
                config[index] = {}
                is_changed = True
            for config_list in config_list_2[index]:
                if not config_list[0] in config[index]:
                    config[index][config_list[0]] = config_list[1]
                    is_changed = True
        if is_changed:
            with open(f"data/config-{name}.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            is_changed = False


def addConfig(name: str):
    config = {}
    for key in config_list_1:
        config[key] = {}
        for value in config_list_2[key]:
            config[key][value[0]] = value[1]
    config["StartGame"]["user"] = Encryption.new()
    with open(f"data/config-{name}.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def load(path: str) -> dict:
    """
    Load configurations.

    Returns:
        config dict
    """
    with open(path, "r", encoding="utf-8") as json_file:
        config = json.load(json_file)
    return config


def loadConfigByName(name: str) -> dict:
    with open(f"data/config-{name}.json", "r", encoding="utf-8") as json_file:
        config = json.load(json_file)
    return config


def save(config: dict, path: str) -> bool:
    """
    Save configurations.
    """
    try:
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(config, json_file, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


def remove(name: str):
    os.remove(f"data/config-{name}.json")


def rename(old: str, new: str):
    os.rename(f'data/config-{old}.json', f'data/config-{new}.json')
