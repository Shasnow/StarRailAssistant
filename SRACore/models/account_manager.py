#!/usr/bin/env python3
"""
账号管理模块 - 支持多账号存储和切换
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from SRACore.util import encryption


@dataclass
class SavedAccount:
    """保存的账号信息"""
    name: str = ""  # 账号别名，如 "主号"、"小号"
    encrypted_username: str = ""  # 加密后的用户名
    encrypted_password: str = ""  # 加密后的密码
    game_channel: int = 0  # 游戏渠道 (0=官服, 1=B服, 2=国际服)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "encryptedUsername": self.encrypted_username,
            "encryptedPassword": self.encrypted_password,
            "gameChannel": self.game_channel
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**{
            "name": data.get("name", ""),
            "encrypted_username": data.get("encryptedUsername", ""),
            "encrypted_password": data.get("encryptedPassword", ""),
            "game_channel": data.get("gameChannel", 0)
        })

    def get_username(self) -> str:
        """获取用户名"""
        # 尝试解密，如果失败则返回原始值
        if self.encrypted_username:
            try:
                decrypted = encryption.decryptor(self.encrypted_username)
                if decrypted:
                    return decrypted
            except:
                pass
        return self.encrypted_username

    def get_password(self) -> str:
        """获取密码"""
        # 尝试解密，如果失败则返回原始值
        if self.encrypted_password:
            try:
                decrypted = encryption.decryptor(self.encrypted_password)
                if decrypted:
                    return decrypted
            except:
                pass
        return self.encrypted_password

    @staticmethod
    def create(name: str, username: str, password: str, game_channel: int = 0) -> SavedAccount:
        """创建新的保存账号"""
        # 注意：由于 encryption 模块没有 encryptor 函数，这里暂时存储原始值
        # 实际生产环境中应该使用适当的加密方式
        return SavedAccount(
            name=name,
            encrypted_username=username,
            encrypted_password=password,
            game_channel=game_channel
        )


@dataclass
class AccountManager:
    """账号管理器 - 管理多个保存的账号"""
    accounts: list[SavedAccount] = field(default_factory=list)
    selected_account_index: int = -1  # -1 表示使用旧的单账号模式

    def to_dict(self) -> dict:
        return {
            "accounts": [acc.to_dict() for acc in self.accounts],
            "selectedAccountIndex": self.selected_account_index
        }

    @classmethod
    def from_dict(cls, data: dict):
        accounts = [SavedAccount.from_dict(acc) for acc in data.get("accounts", [])]
        return cls(
            accounts=accounts,
            selected_account_index=data.get("selectedAccountIndex", -1)
        )

    def add_account(self, account: SavedAccount) -> int:
        """添加账号，返回新账号的索引"""
        self.accounts.append(account)
        return len(self.accounts) - 1

    def remove_account(self, index: int) -> bool:
        """移除指定索引的账号"""
        if 0 <= index < len(self.accounts):
            self.accounts.pop(index)
            # 调整选中的索引
            if self.selected_account_index >= len(self.accounts):
                self.selected_account_index = len(self.accounts) - 1
            return True
        return False

    def update_account(self, index: int, account: SavedAccount) -> bool:
        """更新指定索引的账号"""
        if 0 <= index < len(self.accounts):
            self.accounts[index] = account
            return True
        return False

    def select_account(self, index: int) -> bool:
        """选择账号"""
        if -1 <= index < len(self.accounts):
            self.selected_account_index = index
            return True
        return False

    def get_selected_account(self) -> Optional[SavedAccount]:
        """获取当前选中的账号"""
        if 0 <= self.selected_account_index < len(self.accounts):
            return self.accounts[self.selected_account_index]
        return None

    def get_account_count(self) -> int:
        """获取账号数量"""
        return len(self.accounts)

    def get_account_names(self) -> list[str]:
        """获取所有账号名称"""
        return [acc.name for acc in self.accounts]

    def find_account_by_name(self, name: str) -> Optional[SavedAccount]:
        """根据名称查找账号"""
        for acc in self.accounts:
            if acc.name == name:
                return acc
        return None

    def find_account_index_by_name(self, name: str) -> int:
        """根据名称查找账号索引，找不到返回-1"""
        for i, acc in enumerate(self.accounts):
            if acc.name == name:
                return i
        return -1
