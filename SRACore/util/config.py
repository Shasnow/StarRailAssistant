import json
from typing import Any

from SRACore.localization import Resource
from SRACore.util.const import AppDataSraDir
from SRACore.util.logger import logger


def load_config(name:str) -> dict[str, Any] | None:
    path = ''
    try:
        if ".json" in name:
            path = name.replace('\"', '')
        else:
            path = AppDataSraDir / f'configs/{name}.json'
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

def load_settings():
    path = AppDataSraDir / 'settings.json'
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
    path = AppDataSraDir / 'cache.json'
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