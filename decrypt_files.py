# 本文件可以将云端备份的文件解密
from utils.encrypt import EncryptHanlder

# 打开密钥文件
ept = EncryptHanlder('./config/encrypt.key') 
# 解密文件
target_file = './test-py/test.png.e2bdy'
# 解密文件会将加密后缀给删除
ept.decrypt_files(target_file)
# 测试通过