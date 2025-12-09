from SRACore.util.logger import logger

from SRACore.util.const import AppDataSraDir
from SRACore.util.i18n import t
import json


def load_config(name:str):
    try:
        with open(AppDataSraDir / f'configs/{name}.json', 'r') as f:
           return json.load(f)
    except FileNotFoundError as e:
        logger.error(t('config.file_not_found', name=name, error=e))
        return {}
    except json.JSONDecodeError as e:
        logger.error(t('config.parse_error', name=name, error=e))
        return {}
    except Exception as e:
        logger.error(t('config.load_error', name=name, error=e))
        return {}

def load_settings():
    try:
        with open(AppDataSraDir / 'settings.json', 'r') as f:
           return json.load(f)
    except FileNotFoundError as e:
        logger.error(t('config.settings_not_found', error=e))
        return {}
    except json.JSONDecodeError as e:
        logger.error(t('config.settings_parse_error', error=e))
        return {}
    except Exception as e:
        logger.error(t('config.settings_load_error', error=e))
        return {}

def load_cache():
    try:
        with open(AppDataSraDir / 'cache.json', 'r') as f:
           return json.load(f)
    except FileNotFoundError as e:
        logger.error(t('config.cache_not_found', error=e))
        return {}
    except json.JSONDecodeError as e:
        logger.error(t('config.cache_parse_error', error=e))
        return {}
    except Exception as e:
        logger.error(t('config.cache_load_error', error=e))
        return {}