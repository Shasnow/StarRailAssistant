# type: ignore
import json
from typing import Any

from SRACore.localization import Resource
from SRACore.models.app_settings import AppSettings
from SRACore.models.tasks_config import TasksConfig
from SRACore.util.const import AppDataDir, ConfigsDir
from SRACore.util.logger import logger


def _migrate_legacy_rewards(data: dict) -> dict:
    """旧版配置兼容：将旧 rewards 列表迁移为新版独立开关字段"""
    rewards = data.get("receiveRewards", {}).get("rewards")
    if not isinstance(rewards, list):
        return data
    rw = data["receiveRewards"]
    # 旧版 rewards 列表索引对应的字段名及默认值
    legacy_map = [
        ("rewards.trailblazeProfile", True),
        ("rewards.assignments", True),
        ("rewards.mail", True),
        ("rewards.dailyTraining", True),
        ("rewards.namelessHonor", True),
        ("rewards.giftOfOdyssey", True),
        ("rewards.redeemCode", False),
    ]
    for index, (key, default) in enumerate(legacy_map):
        if key not in rw:  # 仅在新版字段缺失时回退读取旧列表
            rw[key] = rewards[index] if len(rewards) > index else default
    return data


def load_config(name: str) -> TasksConfig | None:
    path = ''
    try:
        if ".json" in name:
            path = name.replace('\"', '')
        else:
            path = ConfigsDir / f'{name}.json'
        with open(path, 'r') as f:
            data = json.load(f)
        data = _migrate_legacy_rewards(data)
        return TasksConfig.from_dict(data)
    except FileNotFoundError:
        logger.error(Resource.config_fileNotFound(path))
        return None
    except json.JSONDecodeError as e:
        logger.error(Resource.config_parseError(path, str(e)))
        return None
    except Exception as e:
        logger.error(Resource.config_exception(path, str(e)))
        return None

def load_data(typ: str) -> dict[Any, Any]:
    path = ''
    match typ:
        case 'settings':
            path = AppDataDir / 'settings.json'
        case 'cache':
            path = AppDataDir / 'cache.json'
        case _:
            return {}

    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(Resource.config_fileNotFound(path))
        return {}
    except json.JSONDecodeError as e:
        logger.error(Resource.config_parseError(path, str(e)))
        return {}
    except Exception as e:
        logger.error(Resource.config_exception(path, str(e)))
        return {}


def load_cache():
    return load_data('cache')
