import io
from cryptography.fernet import Fernet


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


    def encrypt_files(self,file_data):
        """加密文件"""
        file_content = file_data.read()
        encrypted_content = self.fernet.encrypt(file_content)
        return io.BytesIO(encrypted_content)


    def decrypt_files(self,file_data):
        """解密"""
        file_content = bytearray(self.fernet.decrypt(file_data.read()))
        return io.BytesIO(file_content)