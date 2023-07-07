import os
import time
import traceback

from utils.myLog import _log
from utils.bdyUpd import BaiDuWangPan
from utils.confLoad import Config,write_config_file
from utils import gtime


def auth_bdy():
    """先进行百度云验证，需要等待用户输入验证码"""
    try:
        bdy = BaiDuWangPan(Config['APP_KEY'],Config['BDY_SECRET_KEY'],Config['BDY_APP_NAME'])
        res = bdy.get_device_code()
        # 出现错误
        if "errno" in res or "error_code" in res:
            _log.critical(f"err get device code: {res}")
            _log.critical("请检查KEY环境变量是否设置正确！进程退出中...")
            os.abort()
        
        # 显示token到控制台，让用户输入。sleep等待
        _log.info(f"浏览器打开 {res['verification_url']} 输入验证码 {res['user_code']}")
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
        global Config
        Config['BDY_USER_ACCESS_TOKEN'] = res["access_token"] 
        Config['BDY_USER_REFRESH_TOKEN'] = res["refresh_token"]
        Config['BDY_USER_TOKEN_OUTDATE'] = time.time() + res["expires_in"]
        write_config_file(Config)

        _log.info(f"获取token操作结束，已写回配置文件")

    except Exception as result:
        _log.exception('err in auth init')
        os.abort()

if __name__ == "__main__":
    _log.info(f"[start] start at {gtime.get_time_str()}")