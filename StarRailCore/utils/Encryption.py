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
数据加密
"""
import os

from cryptography.fernet import Fernet


def generate_key(key_file="data/frperg.sra"):
    key = Fernet.generate_key()
    with open(key_file, "wb") as key_file:
        key_file.write(key)
    return key


def load_key(key_file="data/frperg.sra"):
    return open(key_file, "rb").read()


def encrypt_word(pwd, key_file="data/frperg.sra"):
    key = load_key(key_file)
    cipher_suite = Fernet(key)
    encrypted_password = cipher_suite.encrypt(pwd.encode())
    return encrypted_password


def decrypt_word(encrypted_password, key_file="data/frperg.sra"):
    key = load_key(key_file)
    cipher_suite = Fernet(key)
    decrypted_pwd = cipher_suite.decrypt(encrypted_password).decode()
    return decrypted_pwd


def init():
    if not os.path.exists("data/frperg.sra"):
        generate_key()
    if not os.path.exists("data/privacy.sra"):
        with open("data/privacy.sra", "wb") as sra_file:
            sra_file.write(encrypt_word(""))


def load():
    with open("data/privacy.sra", "rb") as sra_file:
        privacy = sra_file.read()
        try:
            acc = privacy
            account_text = decrypt_word(acc)
        except IndexError:
            account_text = ""
    return account_text


def save(account_text):
    acc = encrypt_word(account_text)
    with open("data/privacy.sra", "wb") as sra_file:
        sra_file.write(acc)
