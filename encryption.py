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
beta v0.6
作者：雪影
加密
"""
from cryptography.fernet import Fernet
import os


# 生成密钥
def generate_key(key_file='frperg.sra'):
    key = Fernet.generate_key()
    with open(key_file, 'wb') as key_file:
        key_file.write(key)
    return key


# 从文件加载密钥
def load_key(key_file='frperg.sra'):
    return open(key_file, 'rb').read()


# 加密密码
def encrypt_word(pwd, key_file='frperg.sra'):
    key = load_key(key_file)
    cipher_suite = Fernet(key)
    encrypted_password = cipher_suite.encrypt(pwd.encode())
    return encrypted_password


# 解密密码
def decrypt_word(encrypted_password, key_file='frperg.sra'):
    key = load_key(key_file)
    cipher_suite = Fernet(key)
    decrypted_pwd = cipher_suite.decrypt(encrypted_password).decode()
    return decrypted_pwd

def init():
    if not os.path.exists('frperg.sra'):
        generate_key()
    if not os.path.exists('privacy.sra'):
        with open("privacy.sra",'wb') as sra_file:
            sra_file.write(b'')


if __name__ == "__main__":
    if not os.path.exists('frperg.sra'):
        generate_key()
    password = input("请输入密码: ")
    password=encrypt_word(password)
    print(password)
    decrypted_password = decrypt_word(password)
    print("解密后的密码是:", decrypted_password)
