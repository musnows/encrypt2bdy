import os
import pyAesCrypt
from .myLog import _log

DEFAULT_KEY_PATH = './config/encrypt.key'
"""默认密钥文件路径"""
ENCRYPT_FILE_EXTENSION = '.e2bdy'
"""加密文件后缀"""
CHUNK_SIZE = 64 * 1024  # 设置分块大小
"""加密操作分片大小"""


class EncryptHanlder:
    """文件加密解密处理机制"""

    def __init__(self, passwd: str):
        """传入用户自定义的密钥"""
        # 成员变量赋值
        self.passwd = passwd

    def encrypt_file(self, input_file: str):
        """
        加密文件，采用分片读取
        :param input_file： 需要加密的源文件
        :return 加密后的文件路径
        """
        encrypt_file_path = input_file + ENCRYPT_FILE_EXTENSION
        with open(input_file, 'rb') as file_in, open(encrypt_file_path,
                                                     'wb') as file_out:
            pyAesCrypt.encryptStream(file_in, file_out, self.passwd,
                                     CHUNK_SIZE)
        return encrypt_file_path

    def decrypt_file(self, encrypted_file: str):
        """
        解密文件，采用分片读取
        :param encrypted_file：需要解密的文件
        :return 解密后的文件路径
        """
        temp_file_path = encrypted_file.replace(ENCRYPT_FILE_EXTENSION, "")
        # 如果源文件存在，则添加一个文件后缀来区别名字
        # 避免覆盖一个可能就是加密前的文件
        if os.path.exists(temp_file_path):
            _log.warning(
                f"add '.decrypt' to file path because '{temp_file_path}' already exists!"
            )
            temp_file_path += f"{ENCRYPT_FILE_EXTENSION}.decrypt"
            # 这不是一个常用后缀，如果这个文件还存在，则删除它
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                _log.warning(f"remove {temp_file_path} before decrypt")
        # 解密操作
        with open(encrypted_file,
                  'rb') as file_in, open(temp_file_path, 'wb+') as file_out:
            pyAesCrypt.decryptStream(file_in, file_out, self.passwd,
                                     CHUNK_SIZE)
        return temp_file_path
