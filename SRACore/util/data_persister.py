# type: ignore
import json
from typing import Any

from SRACore.localization import Resource
from SRACore.models.app_settings import AppSettings
from SRACore.util.const import AppDataDir, ConfigsDir
from SRACore.util.logger import logger


def load_config(name: str) -> dict[str, Any] | None:
    path = ''
    try:
        if ".json" in name:
            path = name.replace('\"', '')
        else:
            path = ConfigsDir / f'{name}.json'
        with open(path, 'r') as f:
            return json.load(f)
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


def load_settings(group: str | None = None) -> dict[str, Any]:
    data = load_data("settings")
    if group:
        return data.get(group, {})
    else:
        return data


def load_app_settings() -> AppSettings:
    data = load_settings()
    return AppSettings.from_dict(data)


def load_cache():
    return load_data('cache')


def load_app_config():
    path = 'SRACore/config.toml'
    try:
        import tomllib
        with open(path, 'rb') as f:
            return tomllib.load(f)
    except FileNotFoundError:
        logger.error(Resource.config_fileNotFound(path))
        return None
    except Exception as e:
        logger.error(Resource.config_exception(path, str(e)))
        return None
