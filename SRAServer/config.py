"""服务端配置：访问令牌、访客模式、监听地址与 WebUI 开关。

配置来源优先级：命令行参数 > 环境变量 > SRAServer/server.toml（可选）> 默认值。
默认值与既有 C# 服务（appsettings.json）保持一致：空 token（关闭鉴权）、非访客模式。
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PORT = 5073
_TOML_PATH = Path(__file__).with_name("server.toml")


def _read_toml() -> dict:
    try:
        with open(_TOML_PATH, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


@dataclass
class ServerConfig:
    """服务端运行时配置。"""

    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    webui: bool = True
    access_token: str = ""
    visitor_mode: bool = False
    log_level: str = "DEBUG"
    # 覆盖 settings.json 所在的应用数据目录（测试用）
    app_data_dir: str | None = None
    _toml: dict = field(default_factory=dict, repr=False)

    @property
    def auth_enabled(self) -> bool:
        """是否启用访问令牌鉴权（token 为空则全放行）。"""
        return bool(self.access_token.strip())

    @classmethod
    def load(cls, **overrides) -> ServerConfig:
        """从环境变量与可选 server.toml 构建配置，命令行参数通过 overrides 覆盖。

        支持的键（环境变量 / server.toml）：``SRA_HOST``/``host``、``SRA_PORT``/``port``、
        ``SRA_WEBUI``/``webui``、``SRA_ACCESS_TOKEN``/``access_token``、
        ``SRA_VISITOR_MODE``/``visitor_mode``、``SRA_LOG_LEVEL``/``log_level``、
        ``SRA_APP_DATA_DIR``/``app_data_dir``。``overrides`` 中值为 ``None`` 的键不生效，
        以便「未显式指定命令行参数」时保留环境变量/server.toml 的取值。
        """
        toml = _read_toml()

        def pick(env_key: str, toml_key: str, default):
            if env_key in os.environ:
                return os.environ[env_key]
            return toml.get(toml_key, default)

        config = cls(
            host=str(pick("SRA_HOST", "host", "127.0.0.1")),
            port=int(pick("SRA_PORT", "port", DEFAULT_PORT)),
            webui=str(pick("SRA_WEBUI", "webui", "true")).lower() not in ("0", "false", "no"),
            access_token=str(pick("SRA_ACCESS_TOKEN", "access_token", "")),
            visitor_mode=str(pick("SRA_VISITOR_MODE", "visitor_mode", "false")).lower()
            in ("1", "true", "yes"),
            log_level=str(pick("SRA_LOG_LEVEL", "log_level", "DEBUG")),
            app_data_dir=pick("SRA_APP_DATA_DIR", "app_data_dir", None),
            _toml=toml,
        )
        for key, value in overrides.items():
            if value is not None:
                setattr(config, key, value)
        return config