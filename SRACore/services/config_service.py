"""配置服务：配置名列表、读写、以及敏感字段（账号/密码）的加解密下发。

- 磁盘格式：DPAPI 加密（SRACore.util.encryption），与 C# 端一致；
- 下发格式：用 AccessToken 派生密钥的 AES-256-GCM 加密，格式 base64(IV[12]+密文+tag[16])。
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from pydantic import ValidationError

from SRACore.models.tasks_config import TasksConfig
from SRACore.util import encryption
from SRACore.util.const import ConfigsDir
from SRACore.util.data_persister import load_config

from SRACore.services.cache_service import CacheService

INVALID_NAME_CHARS = set('\\/:*?"<>|')
STATIC_VERSION = 4


def _aes_key(access_token: str) -> bytes:
    return hashlib.sha256(access_token.encode("utf-8")).digest()


def encrypt_with_access_token(plaintext: str, access_token: str) -> str:
    """使用 AccessToken 派生密钥的 AES-256-GCM 加密（对齐 C# EncryptWithAccessToken）。"""
    if not plaintext:
        return ""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    iv = os.urandom(12)
    ciphertext = AESGCM(_aes_key(access_token)).encrypt(iv, plaintext.encode("utf-8"), None)
    return base64.b64encode(iv + ciphertext).decode("utf-8")


def decrypt_with_access_token(ciphertext: str, access_token: str) -> str:
    """解密 encrypt_with_access_token 生成的负载，失败返回空字符串。"""
    if not ciphertext or not access_token:
        return ""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        raw = base64.b64decode(ciphertext)
        return AESGCM(_aes_key(access_token)).decrypt(raw[:12], raw[12:], None).decode("utf-8")
    except Exception:
        return ""


class ConfigService:
    """配置的读取/写入与下发脱敏。"""

    def __init__(self, cache: CacheService) -> None:
        self._cache = cache

    # ── 列表 ──

    def names(self) -> list[str]:
        return self._cache.config_names()

    def exists(self, name: str) -> bool:
        return name in self.names()

    def create(self, name: str) -> str:
        self._cache.add_config_name(name)
        return name

    def delete(self, name: str) -> bool:
        return self._cache.remove_config_name(name)

    @staticmethod
    def is_valid_name(name: str) -> bool:
        return not any(ch in INVALID_NAME_CHARS for ch in name)

    # ── 读取 ──

    def load_dict(self, name: str) -> dict[str, Any]:
        """加载配置文件为点号键字典（敏感字段为磁盘密文），不存在或版本过旧时返回默认配置。"""
        config = load_config(name)
        if config is None or config.Version < STATIC_VERSION:
            return TasksConfig(Name=name, Version=STATIC_VERSION).to_dict()
        config.Name = name
        return config.to_dict()

    def safe_payload(self, name: str, data: dict[str, Any], *, access_token: str) -> dict[str, Any]:
        """生成下发给客户端的配置：账号/密码用 AccessToken 加密（未配置 token 时置空）。"""
        start_game = data.get("startGame")
        if isinstance(start_game, dict):
            if access_token:
                username = encryption.decryptor(start_game.get("username", ""))
                password = encryption.decryptor(start_game.get("password", ""))
                start_game["username"] = encrypt_with_access_token(username, access_token)
                start_game["password"] = encrypt_with_access_token(password, access_token)
            else:
                start_game["username"] = ""
                start_game["password"] = ""
        return data

    def masked_dict(self, name: str) -> dict[str, Any]:
        """返回下发/展示用配置：账号密码非空时以 ``******`` 掩码（对齐 MCP sra_config_get）。"""
        data = self.load_dict(name)
        start_game = data.get("startGame")
        if isinstance(start_game, dict):
            start_game["username"] = "******" if start_game.get("username") else ""
            start_game["password"] = "******" if start_game.get("password") else ""
        return data

    # ── 写入 ──

    def patch(self, name: str, patch: dict[str, Any]) -> list[str]:
        """按「section + 点号字段名」部分更新配置，返回被更新字段名列表。

        仅接受已存在的字段；``startGame.username/password`` 的明文会加密后落盘，
        未提供的字段保持原值（对齐 MCP sra_config_update）。
        """
        current = self.load_dict(name)
        updated: list[str] = []
        for section, fields in patch.items():
            target = current.get(section)
            if not isinstance(target, dict) or not isinstance(fields, dict):
                continue
            for key, value in fields.items():
                if section == "startGame" and key in ("username", "password"):
                    target[key] = encryption.encryptor(value if isinstance(value, str) else "")
                    updated.append(f"{section}.{key}")
                    continue
                if key in target:
                    target[key] = value
                    updated.append(f"{section}.{key}")
        if updated:
            self.save_dict(name, current)
        return updated

    def save_dict(self, name: str, data: dict[str, Any]) -> None:
        ConfigsDir.mkdir(parents=True, exist_ok=True)
        path = ConfigsDir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def update(self, name: str, body: dict[str, Any], *, access_token: str) -> str | None:
        """按 C# ConfigsController.UpdateConfig 语义更新配置并落盘。

        请求体中的账号/密码为 AccessToken 密文；缺省时保留磁盘上的原值（保持明文不变）。

        落盘前用 :class:`TasksConfig` 校验并归一化（补全缺失 section、版本号提升到当前
        ``STATIC_VERSION``），结构非法时**不写盘**并返回错误信息（由控制器转成 400），
        避免任意 JSON 污染 ``configs/*.json``。
        """
        current = self.load_dict(name)
        current_start_game = current.get("startGame") if isinstance(current.get("startGame"), dict) else {}

        body = dict(body)
        body["name"] = name
        incoming = body.get("startGame")
        if not isinstance(incoming, dict):
            incoming = {}
        for field in ("username", "password"):
            if field in incoming:
                incoming[field] = self._to_stored(incoming.get(field), access_token)
            else:
                incoming[field] = current_start_game.get(field, "")
        body["startGame"] = incoming

        try:
            config = TasksConfig.from_dict(body)
        except ValidationError as e:
            details = e.errors()
            first = details[0] if details else {}
            location = ".".join(str(part) for part in first.get("loc", ())) or "body"
            return f"配置结构非法（{location}）: {first.get('msg', 'validation error')}"
        config.Name = name
        config.Version = STATIC_VERSION
        self.save_dict(name, config.to_dict())
        return None

    @staticmethod
    def _to_stored(wire_value: Any, access_token: str) -> str:
        """把下发的（AccessToken 加密的）凭据转为磁盘存储值（DPAPI 加密）。"""
        wire = wire_value if isinstance(wire_value, str) else ""
        if not wire:
            return ""
        plaintext = decrypt_with_access_token(wire, access_token) if access_token else wire
        return encryption.encryptor(plaintext)