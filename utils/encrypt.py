import os
from cryptography.fernet import Fernet
from .myLog import _log

DEFAULT_KEY_PATH = './config/encrypt.key'
"""默认密钥文件路径"""
ENCRYPT_FILE = '.ept'
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


    def encrypt_files(self,file_path:str):
        """加密文件，返回加密后的文件路径"""
        with open(file_path, 'rb') as f:
            file_content = f.read()
        # 加密
        encrypted_content = self.fernet.encrypt(file_content)
        # file_exten = file_path.split(".")[-1]  # 文件后缀
        temp_file_path = file_path + ENCRYPT_FILE
        # 写入临时文件
        with open(temp_file_path , 'wb') as f:
            f.write(encrypted_content)
        # temp = io.BytesIO(encrypted_content)
        # temp.write(encrypted_content)
        return temp_file_path


    def decrypt_files(self,file_path:str):
        """解密,直接写入原文件"""
        with open(file_path, 'rb') as f:
            file_content = f.read()
        # 解密，直接写入源文件
        file_content = bytearray(self.fernet.decrypt(file_content))
        file_path = file_path.replace(ENCRYPT_FILE,'') # 删除后缀
        with open(file_path , 'wb') as f:
            f.write(file_content)
        
        return file_path