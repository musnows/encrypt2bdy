import os
import ruamel.yaml
from .myLog import _log

CONF_FILE_PATH = './config/config.yml'
"""配置文件路径"""
CONF_EXP_FILE_PATH = './config/config-exp.yml'
"""示例配置文件路径"""
Config = {}
"""配置文件"""


class YamlLoader:

    def __init__(self, file_path: str):
        self.file = file_path

    def file_load(self):
        """加载yml文件"""
        with open(self.file, 'r', encoding='utf-8') as f:
            return ruamel.yaml.round_trip_load(f)

    def file_dump(self, data):
        """写入yml文件到路径"""
        with open(self.file, 'w', encoding='utf-8') as f:
            ruamel.yaml.YAML().dump(data, f)  # 导出的时候保留注释


def env_checker(key: str, default, is_critical=False):
    """
    传入key，检查对应env是否存在，不存在则返回default。
    - 如果is_critical为True，不存在env配置时程序退出！
    """
    temp = os.getenv(key)
    # 环境变量不存在或者为空
    if not temp or temp == "":
        if not is_critical: return default  # 不重要，返回默认值
        else:
            _log.critical(f"[config] env '{key}' not exists or empty!")
            os.abort()
    return temp


def is_valid_remote_path(path: str):
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


def config_remote_path_checker(sync_path_list: list):
    """检查remote path是否正确填写"""
    for path_conf in sync_path_list:
        remote_path = path_conf['remote']
        if not is_valid_remote_path(remote_path):
            _log.warning(f"[config] 远端文件路径不能以/开头或结尾！错误路径：'{remote_path}'")
            os.abort()


def write_config_file(value=Config):
    """写入配置文件"""
    YamlLoader(CONF_FILE_PATH).file_dump(value)


##########################读取并检测配置是否合法#################################

if os.path.exists(CONF_FILE_PATH):
    Config = YamlLoader(CONF_FILE_PATH).file_load()
    _log.info(f"[config] loaded config from '{CONF_FILE_PATH}'")
else:
    Config = YamlLoader(CONF_EXP_FILE_PATH).file_load()
    YamlLoader(CONF_FILE_PATH).file_dump(Config)  # 加载默认的配置文件
    _log.info(f"[config] init config from '{CONF_EXP_FILE_PATH}'")

# 检测环境变量是否存在
Config['BDY_SECRET_KEY'] = env_checker('BDY_SECRET_KEY', None, True)
Config['BDY_APP_KEY'] = env_checker('BDY_APP_KEY', None, True)
Config['BDY_APP_NAME'] = env_checker('BDY_APP_NAME', "e2bdys")
Config['SYNC_INTERVAL'] = env_checker('SYNC_INTERVAL', "0 21 * * *")
Config['ENCRYPT_UPLOAD'] = int(env_checker('ENCRYPT_UPLOAD', 0))
# 获取到环境变量后，写回一次配置文件
write_config_file(Config)

SYNC_INTERVAL = Config['SYNC_INTERVAL']
"""监看间隔时长的cron表达式"""

# 如果配置了加密，则一定要配置密钥
NEED_ENCRYPT = Config['ENCRYPT_UPLOAD']
"""是否需要加密？1为是"""
USER_PASSKEY = env_checker("USER_PASSKEY", "test", (NEED_ENCRYPT == 1))
"""用户密钥配置"""
# 检查用户密钥是否真的配置好了
if NEED_ENCRYPT == 1:
    assert (USER_PASSKEY != "")

# 加载完毕
_log.info("[config] loaded config success")
