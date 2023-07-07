import os
import time
import traceback

from utils.myLog import _log
from utils.bdyUpd import BaiDuWangPan
from utils.confLoad import Config,write_config_file
from utils import gtime

def is_need_auth():
    """通过config判断是否需要重新授权"""
    if "BDY_USER_TOKEN_OUTDATE" in Config:
        cur_time = time.time()
        if Config["BDY_USER_TOKEN_OUTDATE"] > cur_time:
            time_diff = Config["BDY_USER_TOKEN_OUTDATE"] - cur_time 
            if time_diff <= 3*3600*24: # 小于3天，就需要重新获取token
                return True
            else:
                return False
        else:# 当前时间都比过期时间大了，直接退出
            return True
    else:# 不存在键值，直接退出
        return True
    
def get_files_list(dir: str):
    """
    获取一个目录下所有文件列表，包括子目录
    :param dir: 目录名
    :return: 文件list
    """
    files_list = []
    for root, dirs, files in os.walk(dir, topdown=False):
        for file in files:
            files_list.append(os.path.join(root, file))

    return files_list

def auth_bdy():
    """先进行百度云验证，需要等待用户输入验证码"""
    try:
        if not is_need_auth():
            _log.info("用户token尚未过期，跳过验证阶段")
            return
        
        bdy = BaiDuWangPan(Config['BDY_APP_KEY'],Config['BDY_SECRET_KEY'],Config['BDY_APP_NAME'])
        res = bdy.get_device_code()
        # 出现错误
        if "errno" in res or "error_code" in res:
            _log.critical(f"err get device code: {res}")
            _log.critical("请检查KEY环境变量是否设置正确！进程退出中...")
            os.abort()
        
        # 显示token到控制台，让用户输入。sleep等待
        _log.info(f"请使用浏览器打开 {res['verification_url']} 输入授权码 {res['user_code']}")
        _log.info("请在4分钟内完成此操作，完成后等待进程继续...")
        time.sleep(60*4)

        # 继续，获取token
        res = bdy.get_token_by_device_code(res['device_code'])
        # 出现错误
        if "errno" in res or "error_code" in res:
            _log.critical(f"err get user token: {res}")
            _log.critical("请确认您是否正常进行了应用授权！进程将于60秒后退出...")
            time.sleep(60)
            os.abort()
        
        # 写回配置文件
        Config['BDY_USER_ACCESS_TOKEN'] = res["access_token"] 
        Config['BDY_USER_REFRESH_TOKEN'] = res["refresh_token"]
        Config['BDY_USER_TOKEN_OUTDATE'] = time.time() + res["expires_in"]
        write_config_file(Config)

        _log.info(f"获取token操作结束，已写回配置文件")
        return bdy  # 返回对象
    except Exception as result:
        _log.exception('err in auth init')
        os.abort()

if __name__ == "__main__":
    _log.info(f"[start] start at {gtime.get_time_str()}")
    # 1.鉴权
    bdy = auth_bdy()
    # 2.开始扫描文件
    for path_conf in Config['SYNC_PATH']:
        file_list = get_files_list(path_conf['local']) # 获取本地文件列表
        print(file_list)
        i = 0
        for file_path in file_list:
            fs_id, md5, server_filename, category, path, isdir = bdy.finall_upload_file(file_path)
            print(i,fs_id, md5, server_filename, category, path, isdir)
            i+=1
    
    _log.info(f"[exit] exit at {gtime.get_time_str()}")
    