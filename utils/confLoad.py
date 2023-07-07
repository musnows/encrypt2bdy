import os,re
from ruamel import yaml
from .myLog import _log

CONF_FILE_PATH = './config/config.yml'
"""配置文件路径"""
CONF_EXP_FILE_PATH = './config/config-exp.yml'
"""示例配置文件路径"""
Config = {}
"""配置文件"""

class YamlLoader:
    def __init__(self, file):
        self.file = file
 
    def file_load(self):
        with open(self.file, 'r', encoding='utf-8') as f:
            return yaml.round_trip_load(f)
 
    def file_dump(self, data):
        with open(self.file, 'w',encoding='utf-8') as f:
            yaml.round_trip_dump(data, f, default_flow_style=False)

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

  
def is_valid_remote_path(path:str):  
    """检查远端路径是否符合要求"""
    # 判断路径是否以斜杠开头或者结尾，也不能以.开头
    if path[0] == '/' or path[0] == '.':
        return False
    if path[-1:] == '/':
        return False
    # 不能有如下字符
    if './' in path:  
        return False  
    if '//' in path:
        return False
    return True  

def config_remote_path_checker(sync_path_list:list):
    """检查remote path是否正确填写"""
    for path_conf in sync_path_list:
        remote_path = path_conf['remote']
        if not is_valid_remote_path(remote_path):        
            _log.warning(f"远端文件路径不能以/开头或结尾！错误路径：'{remote_path}'")
            os.abort()

def write_config_file(value=Config):
    """写入配置文件"""
    YamlLoader(CONF_FILE_PATH).file_dump(value)

if os.path.exists(CONF_FILE_PATH):
    Config = YamlLoader(CONF_FILE_PATH).file_load()
    _log.info(f"loaded config from '{CONF_FILE_PATH}'")
else:
    Config = YamlLoader(CONF_EXP_FILE_PATH).file_load()
    YamlLoader(CONF_FILE_PATH).file_dump(Config)
    _log.info(f"init config from '{CONF_EXP_FILE_PATH}'")
    

Config['BDY_SECRET_KEY'] = env_checker('BDY_SECRET_KEY',None,True)
Config['BDY_APP_KEY'] = env_checker('BDY_APP_KEY',None,True)
Config['BDY_APP_NAME'] = env_checker('BDY_APP_NAME',"e2bdys")
Config['SYNC_INTERVAL'] = int(env_checker('SYNC_INTERVAL',600))
Config['ENCRYPT_UPLOAD'] = int(env_checker('ENCRYPT_UPLOAD',1))

SYNC_INTERVAL = Config['SYNC_INTERVAL']
"""监看间隔时长s"""

# 加载完毕
_log.info(f"loaded config success")