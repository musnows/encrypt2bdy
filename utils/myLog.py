import os
import logging

from datetime import datetime,timezone,timedelta
from logging.handlers import TimedRotatingFileHandler

LOGGER_NAME = "e2bdylog"
LOGGER_FILE = "./config/log/run.log" # 如果想修改log文件的名字和路径，修改此变量

def beijing(sec, what):
    """获取北京时间"""
    utc_dt = datetime.now(timezone.utc) # 获取当前时间
    beijing_time = utc_dt.astimezone(timezone(timedelta(hours=8))) # 转换为北京时间
    return beijing_time.timetuple()

def mkdir_log(path="./config/log/"):
    """创建存日志文件的路径"""
    if not os.path.exists(path):
        os.mkdir(path)

# 日志时间改为北京时间
logging.Formatter.converter = beijing # type: ignore

# 只打印info以上的日志（debug低于info）
logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname)s:%(filename)s:%(funcName)s:%(lineno)d | %(message)s",
                    datefmt="%y-%m-%d %H:%M:%S")
# 获取一个logger对象
mkdir_log() # 先创建对应路径
_log = logging.getLogger(LOGGER_NAME)
"""自定义的logger对象"""
# 1.实例化控制台handler和文件handler，同时输出到控制台和文件
file_handler = logging.FileHandler(LOGGER_FILE, mode="a", encoding="utf-8")
fmt = logging.Formatter(fmt="[%(asctime)s] %(levelname)s:%(filename)s:%(funcName)s:%(lineno)d | %(message)s",
                    datefmt="%y-%m-%d %H:%M:%S")
file_handler.setFormatter(fmt)
# 2.按每天来自动生成日志文件的备份
log_handler = TimedRotatingFileHandler(LOGGER_FILE, when='D')
log_handler.setFormatter(fmt)
# 3.添加个日志处理器
_log.addHandler(log_handler)