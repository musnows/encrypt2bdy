import os
import io
from hashlib import md5
from cryptography.fernet import Fernet
from .myLog import _log

DEFAULT_KEY_PATH = './config/encrypt.key'
"""默认密钥文件路径"""
ENCRYPT_FILE = '.e2bdy'
"""加密文件后缀"""

class EncryptHanlder:

    def __init__(self,key_file_path:str=DEFAULT_KEY_PATH):
        # 只有key不存在采需要新建
        if not os.path.exists(key_file_path):
            key = Fernet.generate_key()
            with open(key_file_path, 'wb') as file:
                file.write(key)
            _log.info(f"init key file in '{key_file_path}'")
        else:
            with open(key_file_path,'rb') as file:
                key = file.read()
            _log.info(f"load key file from '{key_file_path}'")
            
        # 成员变量赋值
        self.encrypt_key = key
        self.fernet = Fernet(key)


    def encrypt_files(self,file_path:str,file_data=None):
        """加密文件，返回加密后的文件路径; file_data 是 f.read之后的值"""
        file_bytes = file_data
        if not isinstance(file_data,io.BufferedReader):
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
        # 计算文件md5
        _log.debug(f"{file_path} | {md5(file_bytes).hexdigest()}")
        # 加密
        encrypted_content = self.fernet.encrypt(file_bytes)
        # file_exten = file_path.split(".")[-1]  # 文件后缀
        temp_file_path = file_path + ENCRYPT_FILE
        # 写入临时文件
        with open(temp_file_path , 'wb') as f:
            f.write(encrypted_content)
        # temp = io.BytesIO(encrypted_content)
        # temp.write(encrypted_content)
        return temp_file_path


    def decrypt_files(self,file_path:str,file_data=None):
        """解密,直接写入原文件"""
        file_bytes = file_data
        if not isinstance(file_data,io.BufferedReader):
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
        # 解密，直接写入源文件
        file_bytes = bytearray(self.fernet.decrypt(file_bytes))
        file_path = file_path.replace(ENCRYPT_FILE,'') # 删除后缀
        with open(file_path , 'wb') as f:
            f.write(file_bytes)
        
        return file_path