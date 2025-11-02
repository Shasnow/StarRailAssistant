from SRACore.util.logger import logger

from SRACore.util.const import ApplicationDataPath
import json


def load_config(name:str):
    try:
        with open(ApplicationDataPath / f'configs/{name}.json','r') as f:
           return json.load(f)
    except FileNotFoundError as e:
        logger.error(f"配置文件 {name}.json 未找到: {e}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"配置文件 {name}.json 解析错误: {e}")
        return {}
    except Exception as e:
        logger.error(f"加载配置文件 {name}.json 时发生错误: {e}")
        return {}

def load_settings():
    try:
        with open(ApplicationDataPath / 'settings.json','r') as f:
           return json.load(f)
    except FileNotFoundError as e:
        logger.error(f"设置文件 settings.json 未找到: {e}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"设置文件 settings.json 解析错误: {e}")
        return {}
    except Exception as e:
        logger.error(f"加载设置文件 settings.json 时发生错误: {e}")
        return {}

def load_cache():
    try:
        with open(ApplicationDataPath / 'cache.json','r') as f:
           return json.load(f)
    except FileNotFoundError as e:
        logger.error(f"缓存文件 cache.json 未找到: {e}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"缓存文件 cache.json 解析错误: {e}")
        return {}
    except Exception as e:
        logger.error(f"加载缓存文件 cache.json 时发生错误: {e}")
        return {}