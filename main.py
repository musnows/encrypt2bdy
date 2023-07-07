import os
import time
import hashlib

from utils.myLog import _log

from utils.bdyUpd import BaiDuWangPan
from utils.encrypt import EncryptHanlder,ENCRYPT_FILE
from utils.confLoad import Config,write_config_file,SYNC_INTERVAL
from utils import gtime
from utils.querySql import FilePath,ErrFilePath

DelFileCache = []
"""需要删除的文件路径列表"""
GB_SIZE = 1024 * 1024 * 1024 
FILE_SIZE_LIMITED = 10 * GB_SIZE
"""文件大小限制为10g"""


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
        i,g,e = 0,0,0
        for path_conf in Config['SYNC_PATH']:
            file_list = get_files_list(path_conf['local']) # 获取本地文件列表
            _log.info(f"开始处理路径 '{path_conf['local']}' | 文件数量 {len(file_list)}") # 打印文件列表
            # 遍历文件列表
            for file_path in file_list:
                file_md5_str,e_file_path,file_name = "","",""
                i+=1
                time.sleep(0.05) # 上传了一个文件后休息一会
                try:
                    file_size =  os.path.getsize(file_path) # 文件大小
                    if file_size >= FILE_SIZE_LIMITED:
                        _log.warning(f"[{i}] 文件 '{file_path}' 超出10G限制 | 文件大小：{file_size//GB_SIZE}GB")
                        g+=1
                        continue

                    f = open(file_path,'rb')
                    # 1.计算文件md5，判断文件是否存在于数据中
                    file_name = file_path.partition("/")[-1] # 文件名
                    file_md5_str = hashlib.md5(f.read()).hexdigest()
                    # 找到了
                    if FilePath.select().where(FilePath.file_md5 == file_md5_str).first():
                        _log.debug(f"[{i}] 文件 '{file_path}' 已上传 | 文件哈希：{file_md5_str} | 跳过")
                        g+=1
                        continue
                    # 加密后缀在，不上传（认为是已经处理过的文件）
                    if ENCRYPT_FILE in file_path:
                        _log.info(f"[{i}] 文件 '{file_path}' 是已加密文件，认为其已上传 | 文件哈希：{file_md5_str} | 跳过")
                        g+=1
                        continue
                    # 2.加密
                    # 如果开启了加密，则将文件加密，并将加密后的文件插入缓存
                    e_file_path = file_path
                    if Config['ENCRYPT_UPLOAD']:
                        e_file_path = ept.encrypt_files(file_path,f) 
                    # 3.上传文件
                    fs_id, md5, server_filename, category, rpath, isdir = bdy.finall_upload_file(e_file_path,path_conf['remote'])
                    # 4.入库
                    cur_file = FilePath(file_path=file_path,file_name=file_name,file_md5=file_md5_str,remote_path=rpath)
                    cur_file.save()
                    g+=1
                    # 5.删除临时文件
                    os.remove(e_file_path)
                    _log.info(f"[{i}] 成功上传 '{file_path}' 文件哈希：{md5} 远程路径：{rpath}")
                except Exception as result:
                    _log.exception(f"[{i}] 上传失败 '{file_path}'")
                    e+=1
                    # 入库
                    # md5字符串为空说明问题挺严重，可能是文件不存在！
                    if file_md5_str != "" and file_name !="":
                        cur_file = ErrFilePath(file_path=file_path,file_name=file_name,file_md5=file_md5_str)
                        cur_file.save()
                        _log.info(f"[{i}] 错误记录 '{file_path}' 文件哈希：{file_md5_str}")
                    else:
                        _log.error(f"[{i}] '{file_path}' 严重错误，文件哈希为空！")
                    # 和当前正在处理的文件不同，说明是加密文件
                    if e_file_path != file_path:
                        os.remove(e_file_path)
                    

        # 都处理完毕了，等待下次处理
        next_run_time = gtime.get_time_str_from_stamp(time.time() + SYNC_INTERVAL)
        _log.info(f"本次上传完毕，成功：{g} 错误：{e}，总计：{i}")
        _log.info(f"本次上传完毕，下次处理：{next_run_time} | 开始休眠：{SYNC_INTERVAL}s")
        time.sleep(SYNC_INTERVAL)
    