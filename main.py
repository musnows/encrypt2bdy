import os
import time

from utils.myLog import _log

from utils.bdyUpd import BaiDuWangPan
from utils.encrypt import EncryptHanlder
from utils.confLoad import Config,write_config_file,SYNC_INTERVAL
from utils import gtime

DelFileCache = []
"""需要删除的文件路径列表"""
UpdFileCache = []
"""上传成功的文件列表"""
ErrFileCache = []
"""上传失败的文件列表"""

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
            return BaiDuWangPan(Config['BDY_APP_KEY'],Config['BDY_SECRET_KEY'],Config['BDY_APP_NAME'],
                                Config['BDY_USER_ACCESS_TOKEN'],Config['BDY_USER_REFRESH_TOKEN'],Config['BDY_USER_TOKEN_OUTDATE'])
        
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
    # 2.判断是否需要加密
    ept = EncryptHanlder() if Config['ENCRYPT_UPLOAD'] else None
    # 3.开始扫描文件
    while True:
        _log.info(f"上传任务开始：{gtime.get_time_str()}")
        i = 0
        for path_conf in Config['SYNC_PATH']:
            file_list = get_files_list(path_conf['local']) # 获取本地文件列表
            _log.info(f"开始处理路径 '{path_conf['local']}' | 文件数量 {len(file_list)}") # 打印文件列表
            # 遍历文件列表
            for file_path in file_list:
                try:
                    # 如果开启了加密，则将文件加密，并将加密后的文件插入缓存
                    e_file_path = file_path
                    if Config['ENCRYPT_UPLOAD']:
                        e_file_path = ept.encrypt_files(file_path) # can't work 
                        DelFileCache.append(e_file_path) # 插入到删除缓存中

                    fs_id, md5, server_filename, category, path, isdir = bdy.finall_upload_file(e_file_path,path_conf['remote'])
                    _log.info(f"[{i}] 成功上传 '{file_path}' 文件哈希：{md5} 远程路径：{path}")
                    i+=1
                    # 上传了一个文件后休息一会
                    time.sleep(0.05)
                except Exception as result:
                    _log.exception(f"[{i}] 上传失败 '{file_path}'")
                    ErrFileCache.append(file_path)
                    i+=1

        # 都处理完毕了，等待下次处理
        next_run_time = gtime.get_time_str_from_stamp(time.time() + SYNC_INTERVAL)
        _log.info(f"本次上传完毕，下次处理：{gtime.get_time_str_from_stamp(time.time() + SYNC_INTERVAL)} | 开始休眠：{SYNC_INTERVAL}s")

    