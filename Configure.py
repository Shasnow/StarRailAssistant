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
beta v0.6.3
作者：雪影
配置
"""
import json
import os


def init():
    if not os.path.exists("data/config.json"):
        config = {
            "Mission": {
                "startGame": False,
                "trailBlazerProfile": False,
                "redeemCode": False,
                "assignment": False,
                "giftOfOdyssey": False,
                "mail": False,
                "trailBlazePower": False,
                "dailyTraining": False,
                "namelessHonor": False,
                "quitGame": False
            },
            "StartGame": {
                "autoLogin": False,
                "launcher": False,
                "gamePath": "",
                "pathType":"StarRail",
                "channel": 0
            },
            "RedeemCode": {
                "codeList": []
            },
            "Replenish": {
                "enable": False,
                "way": 1,
                "runTimes": 1
            },
            "OrnamentExtraction": {
                "enable": False,
                "level": 1,
                "runTimes": 1
            },
            "CalyxGolden": {
                "enable": False,
                "level": 1,
                "singleTimes": 1,
                "runTimes": 1
            },
            "CalyxCrimson": {
                "enable": False,
                "level": 1,
                "singleTimes": 1,
                "runTimes": 1
            },
            "StagnantShadow": {
                "enable": False,
                "level": 1,
                "runTimes": 1
            },
            "CaverOfCorrosion": {
                "enable": False,
                "level": 1,
                "runTimes": 1
            },
            "EchoOfWar": {
                "enable": False,
                "runTimes": 1,
                "level": 1
            }
        }
        with open("data/config.json", "w", encoding="utf-8") as json_file:
            json.dump(config, json_file, indent=4)


def load() -> dict:
    """
    Load configurations.
    :return: config
    :rtype: dict
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


if __name__ == "__main__":
    init()
