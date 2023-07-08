import os
import time
import hashlib
import requests

from utils.myLog import _log

from utils.bdyUpd import BaiDuWangPan
from utils.encrypt import EncryptHanlder,ENCRYPT_FILE
from utils.confLoad import Config,write_config_file,SYNC_INTERVAL,NEED_ENCRYPT
from utils import gtime
from utils.querySql import FilePath,ErrFilePath
from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger


DelFileCache = []
"""需要删除的文件路径列表"""
GB_SIZE = 1024 * 1024 * 1024 
FILE_SIZE_LIMITED = 10 * GB_SIZE
"""文件大小限制为10g"""
UPLOAD_RETRY_TIMES = 3
"""上传文件重试次数"""

def is_need_auth():
    """通过config判断是否需要重新授权百度云"""
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



def upload_task(cron_str:str = SYNC_INTERVAL):
    """单次监看任务，传入corn表达式获取下次执行时间。需要保证传入的表达式合法"""
    # 1.鉴权
    bdy = auth_bdy()
    # 2.判断是否需要加密
    ept = EncryptHanlder() if NEED_ENCRYPT else None
    # 3.开始扫描文件
    _log.info(f"上传任务开始：{gtime.get_time_str()}")
    i,g,e,skip = 0,0,0,0
    for path_conf in Config['SYNC_PATH']:
        try:
            # 4.获取单个配置的文件列表
            file_list = get_files_list(path_conf['local']) # 获取本地文件列表
            _log.info(f"开始处理路径 '{path_conf['local']}' | 文件数量 {len(file_list)}") # 打印文件列表
            # 5.遍历文件列表，将不存在的文件上传
            for file_path in file_list:
                file_md5_str,ept_file_path,file_name = "","",""
                i+=1
                time.sleep(0.05) # 上传了一个文件后休息一会
                try:
                    # 判断文件是否存在（可能有权限问题）
                    if not os.path.exists(file_path):
                        _log.warning(f"[{i}] 文件 '{file_path}' 不存在或无权限访问")
                        e+=1
                        continue
                    # 获取文件大小
                    file_size =  os.path.getsize(file_path) # 文件大小
                    if file_size >= FILE_SIZE_LIMITED:
                        _log.warning(f"[{i}] 文件 '{file_path}' 超出10G限制 | 文件大小：{file_size//GB_SIZE}GB")
                        skip+=1
                        continue
                    # 加密后缀在，不上传（认为是已经处理过的文件）
                    if ENCRYPT_FILE in file_path:
                        _log.info(f"[{i}] 文件 '{file_path}' 是已加密文件，认为其已上传 | 跳过")
                        skip+=1
                        continue
                    # 打开文件
                    f = open(file_path,'rb')
                    # 1.计算文件md5，判断文件是否存在于数据中
                    file_name = file_path.partition("/")[-1] # 文件名
                    file_md5_str = hashlib.md5(f.read()).hexdigest()
                    if file_md5_str == "":
                        _log.warning(f"[{i}] 文件 '{file_path}' 哈希值为空 | 跳过")
                        skip+=1
                        continue
                    # 数据库中找到了，代表已上传
                    if FilePath.select().where(FilePath.file_md5 == file_md5_str).first():
                        _log.debug(f"[{i}] 文件 '{file_path}' 已上传 | 文件哈希：{file_md5_str} | 跳过")
                        skip+=1
                        continue
                    # 2.加密
                    # 如果开启了加密，则将文件加密，并将加密后的文件插入缓存
                    ept_file_path = file_path
                    if NEED_ENCRYPT == 1:
                        ept_file_path = ept.encrypt_files(file_path,f) 
                    # 3.上传文件，重试4次
                    result,is_upload_success = None,False
                    for retry_times in range(UPLOAD_RETRY_TIMES):
                        try:
                            fs_id, md5, server_filename, category, rpath, isdir = bdy.finall_upload_file(ept_file_path,path_conf['remote'])
                            is_upload_success = True
                            break # 成功了直接break
                        except requests.exceptions.ConnectionError as result:
                            # 不是已知网络问题
                            if 'pan.baidu.com' not in str(result):
                                raise result
                            _log.warning(f"[{i}] 处理文件：{file_path} 遇到网络错误，2s后重试 | {retry_times} | {str(result)}")
                            time.sleep(2) # 网络错误需要休眠一会再继续
                            continue
                    # 判断是成功退出，还是超过重试次数退出
                    if not is_upload_success:
                        _log.error(f"[{i}] 处理文件：{file_path} 遇到网络错误，超过重试次数！")
                        raise result  # 依旧抛出异常，跳过这个文件
                        
                    # 4.上传成功，入库
                    cur_file = FilePath(file_path=file_path,file_name=file_name,file_md5=file_md5_str,remote_path=rpath)
                    cur_file.save()
                    g+=1
                    # 5.配置了加密，删除临时加密文件
                    if file_path != ept_file_path and NEED_ENCRYPT == 1:
                        os.remove(ept_file_path) 

                    _log.info(f"[{i}] 成功上传 '{file_path}' 文件哈希：{md5} 远程路径：{rpath}")

                except Exception as result:
                    e+=1
                    if "-7" in str(result):
                        _log.error(f"[{i}] 上传失败 '{file_path}' | 错误码-7，远程路径错误或无权访问，请检查本地路径中是否包含特殊字符")
                    elif "-10" in str(result):
                        _log.error(f"[{i}] 上传失败 '{file_path}' | 错误码-10，云盘空间不足！程序退出...")
                        time.sleep(1)
                        exit(0)  # 这里其实算正常退出
                    else:
                        _log.exception(f"[{i}] 上传失败 '{file_path}'")
                    # 入库
                    # md5字符串为空说明问题挺严重，可能是文件不存在！
                    if file_md5_str != "" and file_name !="":
                        cur_file = ErrFilePath(file_path=file_path,file_name=file_name,file_md5=file_md5_str)
                        cur_file.save()
                        _log.info(f"[{i}] 错误记录 '{file_path}' 文件哈希：{file_md5_str}")
                    else:
                        _log.error(f"[{i}] '{file_path}' 严重错误，文件哈希为空！")
                    # 和当前正在处理的文件不同，说明是加密文件
                    if ept_file_path != "" and ept_file_path != file_path and os.path.exists(ept_file_path):
                        os.remove(ept_file_path) # 删除此文件

        except Exception as result:
            _log.exception(f"err | {path_conf}")

    # 都处理完毕了，等待下次处理
    next_run_time = gtime.get_next_run_time(cron_str)
    _log.info(f"本次上传完毕，上传：{g} 跳过：{skip} 错误：{e} ，总计：{i}")
    _log.info(f"本次上传完毕，下次处理：{next_run_time}")


if __name__ == "__main__":
    _log.info(f"[start] start at {gtime.get_time_str()}")
    try:
        # 1.启动的时候立即运行一次
        upload_task()
        _log.info("[start] 初次运行完毕，准备依据cron表达式启动task")
        time.sleep(4)  # 4秒后启动任务
        # 2.根具cron表达式来构建task
        sch = BlockingScheduler(timezone=Config['TZ'])
        sch.add_job(
            upload_task,trigger=CronTrigger.from_crontab(SYNC_INTERVAL)
        )
        _log.info(f"[start] 根据 cron [{SYNC_INTERVAL}] 启动任务成功，下次运行时间：{gtime.get_next_run_time(SYNC_INTERVAL)}")
        sch.start() # 启动
    except Exception as result:
        _log.exception(f"[start] cron 任务启动失败！请检查 SYNC_INTERVAL 的 cron 表达式是否正确！")
    