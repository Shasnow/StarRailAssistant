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


def init() -> None:
    if not os.path.exists("data/config.json"):
        config = {}
        os.makedirs("data", exist_ok=True)
        with open("data/config.json", "w") as f:
            json.dump(config, f, indent=4)
    config_list_1 = [
        "Mission",
        "StartGame",
        "ReceiveRewards",
        "RedeemCode",
        "Replenish",
        "OrnamentExtraction",
        "CalyxGolden",
        "CalyxCrimson",
        "StagnantShadow",
        "CaverOfCorrosion",
        "EchoOfWar",
        "QuitGame",
        "DivergentUniverse",
        "Settings",
        "CloudGame",
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
            ["quitGame", False],
            ["simulatedUniverse",False]
        ],
        "StartGame": [
            ["autoLogin", False],
            ["launcher", False],
            ["gamePath", ""],
            ["pathType", "StarRail"],
            ["channel", 0],
        ],
        "ReceiveRewards": [["enable", False]],
        "RedeemCode": [
            ["codeList", []],
        ],
        "Replenish": [
            ["enable", False],
            ["way", 1],
            ["runTimes", 1],
        ],
        "OrnamentExtraction": [
            ["enable", False],
            ["level", 1],
            ["runTimes", 1],
        ],
        "CalyxGolden": [
            ["enable", False],
            ["level", 1],
            ["singleTimes", 1],
            ["runTimes", 1],
        ],
        "CalyxCrimson": [
            ["enable", False],
            ["level", 1],
            ["singleTimes", 1],
            ["runTimes", 1],
        ],
        "StagnantShadow": [
            ["enable", False],
            ["level", 1],
            ["runTimes", 1],
        ],
        "CaverOfCorrosion": [
            ["enable", False],
            ["level", 1],
            ["runTimes", 1],
        ],
        "EchoOfWar": [
            ["enable", False],
            ["runTimes", 1],
            ["level", 1],
        ],
        "QuitGame": [
            ["exitSRA", False],
            ["shutdown", False],
            ["sleep", False],
        ],
        "DivergentUniverse":[
            ["enable", False],
            ["mode", 0],
            ["times",1],
        ],
        "Settings": [
            ["F1", "f1"],
            ["F2", "f2"],
            ["F3", "f3"],
            ["F4", "f4"],
            ["startup", False],
            ["autoUpdate", True],
            ["threadSafety", False],
            ["confidence", 0.9],
            ["uiSize", "1200x800"],
            ["uiLocation", "100x100"],
        ],
        "CloudGame": [["firstly", True]],
    }
    with open("data/config.json", "r") as f:
        config = json.load(f)
    for index in config_list_1:
        if not index in config:
            config[index] = {}
        for config_list in config_list_2[index]:
            if not config_list[0] in config[index]:
                config[index][config_list[0]] = config_list[1]
    with open("data/config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def load() -> dict:
    """
    Load configurations.

    Returns:
        config dict
    """
    with open("data/config.json", "r", encoding="utf-8") as json_file:
        config = json.load(json_file)
    return config


def save(config: dict) -> bool:
    """

    :param config: Configurations dict.
    :return: True if successfully saved, False otherwise.
    """
    try:
        with open("data/config.json", "w", encoding="utf-8") as json_file:
            json.dump(config, json_file, indent=4)
        return True
    except Exception:
        return False


