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

import base64
import os.path
from dataclasses import dataclass

import time
import win32crypt

from .SRAFileType import SRAFileType


@dataclass
class User:
    account: str
    password: str


def win_encryptor(note: str, description: str = None, entropy: bytes = None) -> str:
    """使用Windows DPAPI加密数据"""

    if note == "":
        return ""

    encrypted = win32crypt.CryptProtectData(
        note.encode("utf-8"), description, entropy, None, None, 0
    )
    return base64.b64encode(encrypted).decode("utf-8")


def win_decryptor(note: str, entropy: bytes = None) -> str:
    """使用Windows DPAPI解密数据"""

    if note == "":
        return ""

    decrypted = win32crypt.CryptUnprotectData(
        base64.b64decode(note), entropy, None, None, 0
    )
    return decrypted[1].decode("utf-8")


def save(account, password, path: str):
    user = User(win_encryptor(account), win_encryptor(password))
    SRAFileType.save(user, path)


def load(path: str) -> User:
    if os.path.exists(path):
        user = SRAFileType.load(path)
        return User(win_decryptor(user.account), win_decryptor(user.password))
    else:
        return User('', '')


def new():
    integer_timestamp = int(time.time())
    os.makedirs("data/user", exist_ok=True)
    path = f"data/user/{integer_timestamp}.sra"
    SRAFileType.save(User('', ''), path)
    return path


def remove(path: str):
    os.remove(path)
