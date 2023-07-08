from croniter import croniter
from datetime import datetime,timezone,timedelta

def get_time_str(format_str='%y-%m-%d %H:%M:%S'):
    """获取当前时间，格式为 `23-01-01 00:00:00`"""    
    utc_dt = datetime.now(timezone.utc) # 获取当前时间
    bj_dt = utc_dt.astimezone(timezone(timedelta(hours=8))) # 转换为北京时间
    return bj_dt.strftime(format_str)
    # use time.loacltime if you aren't using BeiJing Time
    # return time.strftime("%y-%m-%d %H:%M:%S", time.localtime())

def get_timestamp():
    """获取当前时间戳（北京时间）"""    
    utc_dt = datetime.now(timezone.utc) # 获取当前时间
    bj_dt = utc_dt.astimezone(timezone(timedelta(hours=8))) # 转换为北京时间
    return bj_dt.timestamp()

def get_time_str_from_stamp(timestamp,format_str='%y-%m-%d %H:%M:%S'):
    """从时间戳获取字符串时间"""
    utc_dt =  datetime.fromtimestamp(timestamp,tz=timezone(timedelta(hours=8)))
    return utc_dt.strftime(format_str)

def get_timestamp_from_str(time_str:str,format_str='%y-%m-%d %H:%M:%S'):
    """从可读时间转为时间戳,格式 23-01-01 00:00:00
    - 如果传入的只有日期，如23-01-01，则会自动获取当日0点的时间戳
    """
    if len(time_str) == 8:
        time_str+=" 00:00:00"
    dt = datetime.strptime(time_str, format_str)
    tz = timezone(timedelta(hours=8))
    dt = dt.astimezone(tz)
    return dt.timestamp()

def get_datetime_now():
    """获取东八区的datetime_now"""
    utc_dt = datetime.now(timezone.utc) # 获取当前时间
    bj_dt = utc_dt.astimezone(timezone(timedelta(hours=8))) # 转换为北京时间
    return bj_dt


def get_next_run_time(cron_str:str):
    """通过cron表达式获取下次运行时间"""
    utc_dt = datetime.now(timezone.utc) # 获取当前时间
    bj_dt = utc_dt.astimezone(timezone(timedelta(hours=8)))
    cron = croniter(cron_str, bj_dt.now())
    next_run_time = cron.get_next(datetime)
    return next_run_time