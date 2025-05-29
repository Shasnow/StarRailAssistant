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
import sys
from dataclasses import dataclass
import time
if sys.platform=="win32":
    import win32crypt
    from .SRAFileType import SRAFileType
elif sys.platform=="linux":
    from cryptography.fernet import Fernet
    class SRAFileType:
        @staticmethod
        def save(data, path):
            with open(path, 'wb') as f:
                f.write(data.account.encode('utf-8') + b'\n' + data.password.encode('utf-8'))
        @staticmethod
        def load(path):
            with open(path, 'rb') as f:
                content = f.read().split(b'\n')
                return User(content[0].decode('utf-8'), content[1].decode('utf-8'))



@dataclass
class User:
    account: str
    password: str


def generate_key():
    """生成一个密钥，用于加密和解密"""
    return Fernet.generate_key()


def linux_encryptor(note: str, key: bytes=None) -> str:
    """使用Fernet加密数据"""
    if note == "":
        return ""
    if key is None:
        if not os.path.exists('data/key'):
            with open('data/key', 'wb') as f:
                key = generate_key()
                f.write(key)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(note.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def linux_decryptor(note: str, key: bytes=None) -> str:
    """使用Fernet解密数据"""
    if note == "":
        return ""
    if key is None:
        if not os.path.exists('data/key'):
            raise ValueError("A key is required for decryption on Linux.")
        with open('data/key', 'rb') as f:
            key = f.read()
    fernet = Fernet(key)
    decrypted = fernet.decrypt(base64.b64decode(note))
    return decrypted.decode("utf-8")


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


def encryptor(note: str, key: bytes = None) -> str:
    """根据平台选择加密方法"""
    if sys.platform=='win32':
        return win_encryptor(note)
    elif sys.platform=='linux':
        return linux_encryptor(note, key)
    else:
        raise RuntimeError("Unsupported platform for encryption.")


def decryptor(note: str, key: bytes = None) -> str:
    """根据平台选择解密方法"""
    if sys.platform=='win32':
        return win_decryptor(note)
    elif sys.platform=='linux':
        return linux_decryptor(note, key)
    else:
        raise RuntimeError("Unsupported platform for decryption.")


def save(account, password, path: str, key: bytes = None):
    user = User(encryptor(account, key), encryptor(password, key))
    SRAFileType.save(user, path)


def load(path: str, key: bytes = None) -> User:
    if os.path.exists(path):
        user = SRAFileType.load(path)
        return User(decryptor(user.account, key), decryptor(user.password, key))
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