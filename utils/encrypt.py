import io
from cryptography.fernet import Fernet
from typing import Union

DEFAULT_KEY_PATH = './config/encrypt.key'
"""默认密钥文件路径"""

class EncryptHanlder:

    def __init__(self,key_file_path:str=DEFAULT_KEY_PATH):
        # 生成的秘钥，注意保存,第一次
        key = Fernet.generate_key()
        with open(key_file_path, 'wb') as file:
            file.write(key)
        
        self.encrypt_key = key
        self.fernet = Fernet(key)


    def encrypt_files(self,file_data:Union[bytes,str]):
        """加密文件"""
        if isinstance(file_data,str):
            with open(file_data, 'rb') as f:
                file_content = f.read()
        else:
            file_content = file_data.read()
        encrypted_content = self.fernet.encrypt(file_content)
        temp = io.BytesIO()
        temp.write(encrypted_content)
        return io.BufferedReader(temp)


    def decrypt_files(self,file_data:Union[bytes,str]):
        """解密"""
        if isinstance(file_data,str):
            with open(file_data, 'rb') as f:
                file_content = f.read()
        else:
            file_content = file_data.read()
        # 解密
        file_decrypt_content = bytearray(self.fernet.decrypt(file_content))
        return io.BytesIO(file_decrypt_content)