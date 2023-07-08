# -*- coding: utf-8 -*-
import time
import regex
import json, os, hashlib, requests
from urllib.parse import urlencode
from .myLog import _log


def has_emoji(text:str):
    """判断文件路径中是否含有emoji（无法上传到bdy）"""
    emoji_pattern = regex.compile("[\p{So}\p{Sk}]")
    return bool(emoji_pattern.search(text))

def remove_emoji(text:str):
    """从字符串中删除emoji"""
    ret = ""
    for c in text:
        if not has_emoji(c):
            ret += c
    return ret


class BaiDuWangPan():
    def __init__(self,app_key:str,secret_key:str,app_name:str,access_token="",refresh_token="",outdate_time=0):
        """传入token，初始化成员"""
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_outdate_time = outdate_time  # token过期的时间戳
        self.app_name = app_name
        self.app_key = app_key  # Appkey
        self.secret_key = secret_key  # Secretkey
        self.precreate_api = 'https://pan.baidu.com/rest/2.0/xpan/file?'  # 预上传
        self.upload_api = 'https://d.pcs.baidu.com/rest/2.0/pcs/superfile2?'  # 分片上传
        self.create_api = 'https://pan.baidu.com/rest/2.0/xpan/file?'  # 创建文件、文件夹
        self.query_file_url = 'http://pan.baidu.com/rest/2.0/xpan/multimedia?'  # 查询文件信息
        self.get_token_url = 'https://openapi.baidu.com/oauth/2.0/token?'  # 获取token

    def get_refresh_token(self):
        """
        使用Refresh Token刷新以获得新的Access Token
        :param refresh_token: 必须参数，用于刷新Access Token用的Refresh Token。注意一个Refresh Token只能被用来刷新一次；
        :return:
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.app_key,
            "client_secret": self.secret_key
        }
        response = requests.post(self.get_token_url, data)
        res_data = json.loads(response.text)
        return res_data
    

    def get_device_code(self):
        """获取token之前，先调用本函数获取设备码。
        
        响应示例如下
        res_json = {
            "device_code": "设备code，用于调用api",
            "user_code": "用户设备code，需要展示给用户",
            "verification_url": "https://openapi.baidu.com/device",
            "qrcode_url": "二维码图片url",
            "expires_in": 300,
            "interval": 5,
        }
        """
        url = f"https://openapi.baidu.com/oauth/2.0/device/code?response_type=device_code&client_id={self.app_key}&scope=basic,netdisk"

        payload = {}
        headers = {"User-Agent": "pan.baidu.com"}

        response = requests.request("GET", url, headers=headers, data=payload)
        res_text = response.text.encode("utf8")
        res_json = json.loads(res_text)
        _log.debug(f'device: {res_json}')
        return res_json


    def get_token_by_device_code(self,device_code:str):
        """用device_code获取token
        - 有效期到了，就需要refresh（有效期一个月，那就可以设置定时任务，29天刷新一次！）
        - 结果示例如下
        res = {
            "expires_in": 2592000,
            "refresh_token": "删了",
            "access_token": "删了",
            "session_secret": "本来就是空的",
            "session_key": "本来就是空的",
            "scope": "basic netdisk",
        }
        """
        url = f"https://openapi.baidu.com/oauth/2.0/token?grant_type=device_token&code={device_code}&client_id={self.app_key}&client_secret={self.secret_key}"

        payload = {}
        headers = {"User-Agent": "pan.baidu.com"}

        response = requests.request("GET", url, headers=headers, data=payload)
        res_token_json = json.loads(response.text.encode("utf8"))
        _log.debug(f'token: {res_token_json}')
        # 设置成员变量
        if "refresh_token" in res_token_json:
            self.refresh_token = res_token_json["refresh_token"]
            self.access_token = res_token_json["access_token"]
            self.token_outdate_time = time.time() + res_token_json["expires_in"]
            _log.info(f"获取用户token成功，过期时间：{self.token_outdate_time}")

        return res_token_json
    

    def precreate(self, file_path:str,remote_base:str):
        """预上传 https://pan.baidu.com/union/doc/3ksg0s9r7
        
        说明
        - rtype参数尝试无效！不管如何都会上传文件！230707
        - 请求参数rtype=0时，如果云端存在同名文件，此次调用会失败。
        - 云端文件重命名策略：假设云端已有文件为test.txt，新的名称为test(1).txt1, 当发现已有目录 /dir 时, 新创建的目录命名为：/dir(1) 。
        - content-md5和slice-md5都不为空时，接口会判断云端是否已存在相同文件，如果存在，返回的return_type=2，代表直接上传成功，无需请求后面的分片上传和创建文件接口。
        - 如果return_type=1，代表需要上传文件
        """
        remote_path = '/apps/' + self.app_name + '/' + remote_base  # 基础路径
        # 拼接远程路径名
        arr = file_path.split('/')
        for item in arr[1::]:
            remote_path = os.path.join(remote_path, item)
        # 判断文件路径中是否包含emoji，如果有，将emoji字符串删除
        if has_emoji(remote_path):
            remote_path = remove_emoji(remote_path)
            _log.info(f"[预上传] 远程路径中剔除原有emoji：{remote_path}")
        # 文件大小
        size = os.path.getsize(file_path)
        # 文件块的md5 list
        block_list = []
        # 文件数据
        with open(file_path, 'rb') as f:
            i = 0
            # 分片计算文件的md5
            while True:
                data = f.read(1024 * 1024 * 4)
                if not data:
                    _log.debug(f"{i} break in prev")
                    break
                block_file_md5 = hashlib.md5(data).hexdigest()
                block_list.append(block_file_md5)
                i+=1
            # 计算整个文件md5
            # file_md5_str = hashlib.md5(f.read()).hexdigest()
        # 调用api
        params = {
            'method': 'precreate',
            'access_token': self.access_token,
        }
        data = {
            'path': remote_path,
            'size': size,
            'isdir': 0,
            'autoinit': 1,
            'block_list': json.dumps(block_list)
        }
        _log.debug(f'ps-req {data}')
        api = self.precreate_api + urlencode(params)
        response = requests.post(api, data=data)
        res_data = json.loads(response.content)
        _log.debug(f'pc-res {res_data}')
        
        errno = 0
        if 'errno' in res_data:
            errno = res_data['errno']
        elif 'error_code' in res_data:
            errno = res_data['error_code']
        if errno:
            raise Exception(f"err! {res_data}")
        return res_data.get('uploadid'),res_data.get('return_type'), remote_path, size, block_list

    def upload(self, remote_path, uploadid, partseq, file_data):
        """
        分片上传功能函数
        普通用户单个分片大小固定为4MB（文件大小如果小于4MB，无需切片，直接上传即可），单文件总大小上限为4G。
        普通会员用户单个分片大小上限为16MB，单文件总大小上限为10G。
        超级会员用户单个分片大小上限为32MB，单文件总大小上限为20G。
        :param remote_path: 上传后使用的文件绝对路径
        :param uploadid: precreate接口下发的uploadid
        :param partseq: 文件分片的位置序号，从0开始，参考precreate接口返回的block_list
        :param file_data: 上传的文件内容
        :return: 文件的md5字符串
        """
        data = {}
        files = [
            ('file', file_data)
        ]
        params = {
            'method': 'upload',
            'access_token': self.access_token,
            'path': remote_path,
            'type': 'tmpfile',
            'uploadid': uploadid,
            'partseq': partseq
        }
        api = self.upload_api + urlencode(params)
        response = requests.post(api, data=data, files=files)
        res_data = json.loads(response.content)
        _log.debug(f'upd-res {res_data}')
        errno = 0
        if 'errno' in res_data:
            errno = res_data['errno']
        elif 'error_code' in res_data:
            errno = res_data['error_code']

        if errno:
            raise Exception(f"err! {res_data}")
        md5 = res_data.get('md5', '')
        return md5

    def create(self, remote_path, size, block_list, uploadid):
        """
        创建文件
        :param remote_path: 上传后使用的文件绝对路径
        :param size: 文件大小B
        :param block_list: 文件各分片MD5的json串，MD5对应superfile2返回的md5，且要按照序号顺序排列
        :param uploadid: uploadid
        :return:
        """
        params = {
            'method': 'create',
            'access_token': self.access_token,
        }
        api = self.create_api + urlencode(params)
        data = {
            'path': remote_path,
            'size': size,
            'isdir': 0,
            'uploadid': uploadid,
            'block_list': json.dumps(block_list)
        }
        response = requests.post(api, data=data)
        res_data = json.loads(response.content)
        _log.debug(f"文件创建成功！{res_data}")
        errno = res_data.get('errno', 0)
        if errno:
            raise Exception(f"err! {res_data}")
        else:
            fs_id = res_data.get("fs_id", '')
            md5 = res_data.get("md5", '')
            server_filename = res_data.get("server_filename", '')
            category = res_data.get("category", 0)
            path = res_data.get("path", '')
            ctime = res_data.get("ctime", '')
            isdir = res_data.get("isdir", '')
            return fs_id, md5, server_filename, category, path, isdir
    
    def create_dir(self,path:str):
        """创建文件夹"""
        params = {
            'method': 'create',
            'access_token': self.access_token,
        }
        api = self.create_api + urlencode(params)
        remote_path = '/apps/' + self.app_name  # 基础路径
        # 拼接远程路径名
        arr = path.split('/')
        for item in arr[1::]:
            remote_path = os.path.join(remote_path, item)
        # 远程路径
        data = {
            'path': remote_path,
            'isdir': 1,
        }
        response = requests.request("POST", api, data = data)
        res_data = json.loads(response.content)
        errno = res_data.get('errno', 0)
        _log.debug(f'dir {res_data}')
        if errno:
            raise Exception(f"err! {res_data}")
        else:
            return res_data


    def finall_upload_file(self, file_path:str,remote_base_path:str):
        """最终上传函数，只需要传入文件路径就行
        - 上传完毕了之后，需要进行create
        - remoete_base_path：上传到远程的文件夹路径
        """
        uploadid,return_type ,remote_path, size, block_list = self.precreate(file_path,remote_base_path)
        _log.debug(f"upd:{uploadid} return:{return_type} remote:{remote_path} size:{size} block:{block_list}")
        if return_type == 2:
            return None  # 不需要上传
        # 打开文件
        with open(file_path, 'rb') as f:
            # 开始分片上传
            i = 0
            while True:
                data = f.read(1024 * 1024 * 4)
                if not data:
                    _log.debug(f'{i} break in upload')
                    break
                md5 = self.upload(remote_path, uploadid, i, data)
                i += 1
        # 汇总文件
        return self.create(remote_path, size, block_list, uploadid)

    def download_file(self, fs_id):
        """
        查询文件并下载
        先查询文件是否存在，若存在则返回文件下载地址(dlink)
        下载文件需要在下载地址拼上access_token
        :param fs_id: 文件id数组，数组中元素是uint64类型，数组大小上限是：100
        :return: 文件下载地址
        """
        dlink = ''
        params = {
            "method": "filemetas",
            "access_token": self.access_token,
            "fsids": json.dumps([int(fs_id)]),
            "dlink": 1
        }
        api_url = self.query_file_url + urlencode(params)
        response = requests.get(api_url)
        res_data = json.loads(response.text)
        _log.debug(res_data)
        errmsg = res_data.get("errmsg", None)
        if errmsg == 'succ':
            res_list = res_data.get("list", [])
            if res_list:
                dlink = res_list[0].get('dlink', '')
            if dlink:
                return dlink + '&' + 'access_token={}'.format(self.access_token)
        else:
            raise


def test_upd(p:str):
    t = BaiDuWangPan()
    t.create_dir(p)

# 测试
if __name__ == "__main__":
    _log.debug('start')
    # # test_upd_myself('./test2.png')
    test_upd('./dir/test/')
