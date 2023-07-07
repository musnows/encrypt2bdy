import os
import yaml
from .myLog import _log

CONF_FILE_PATH = '../config/config.yml'
"""配置文件路径"""

# 读取配置文件yaml
with open(CONF_FILE_PATH, 'r', encoding='utf-8') as f:
    Config:dict = yaml.load(f.read(), Loader=yaml.FullLoader)
    """配置文件"""

def env_checker(key:str,default,is_critical = False):
    """传入key，检查对应env是否存在，不存则返回default。
    - 如果is_critical为True，不存在时程序退出！
    """
    temp = os.getenv(key)
    # 环境变量不存在或者为空
    if not temp or temp =="":
        if not is_critical: return default  # 不重要，返回默认值
        else:
            _log.critical(f"env '{key}' not exists or empty!")
            os.abort()
    return temp

def write_file(path: str, value):
    """写入文件,仅支持yaml格式的dict"""
    with open(path, 'w+', encoding='utf-8') as fw:
        yaml.dump(value, fw)

def write_config_file():
    """写入配置文件"""
    with open(CONF_FILE_PATH, 'w+', encoding='utf-8') as fw:
        yaml.dump(Config, fw)


Config['BDY_SECRET_KEY'] = env_checker('BDY_SECRET_KEY',None,True)
Config['BDY_APP_KEY'] = env_checker('BDY_APP_KEY',None,True)
Config['BDY_APP_NAME'] = env_checker('BDY_APP_KEY',"e2bdys")
Config['SYNC_INTERVAL'] = env_checker('SYNC_INTERVAL',600)
Config['ENCRYPT_UPLOAD'] = env_checker('ENCRYPT_UPLOAD',1)


_log.info(f"loaded config from '{CONF_FILE_PATH}'")