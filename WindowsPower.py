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
v0.6.4 beta
作者：雪影
Windows电源操作
"""

import subprocess
import sys

from StarRailAssistant.utils.Logger import logger

def hibernate():
    command = ["shutdown", "/h"]
    try:
        subprocess.run(command, check=True)
        logger.info("计算机进入休眠")
    except subprocess.CalledProcessError:
        logger.exception()


def schedule_shutdown(delay_in_seconds):
    """
    设置Windows延时关机。

    :param delay_in_seconds: 延时多少秒关机（必须大于0）。
    """
    if delay_in_seconds <= 0:
        logger.debug("延时必须大于0秒。")
        sys.exit(1)
    command = ["shutdown", "/s", "/t", str(delay_in_seconds)]
    try:
        subprocess.run(command, check=True)
        logger.info(f"计算机将在{delay_in_seconds}秒后关机。")
    except subprocess.CalledProcessError as e:
        logger.exception(f"设置关机时出错：{e}",is_fatal=True)

def shutdown_cancel():
    """
    取消关机
    """
    command=["shutdown","/a"]
    try:
        subprocess.run(command,check=True)
        logger.info("关机已取消")
    except subprocess.CalledProcessError as e:
        logger.exception()


if __name__ == "__main__":
    delay = int(input("请输入延时关机的秒数（大于0）: "))
    schedule_shutdown(delay)
    ans=input()
    if ans=='0':
        shutdown_cancel()