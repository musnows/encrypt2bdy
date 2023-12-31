# 本文件可以将云端备份的文件解密
from utils.encrypt import EncryptHanlder
from utils.myLog import _log
from main import get_files_list

if __name__ == "__main__":
    # 打开密钥文件，将docker生成的密钥文件放入此文件夹
    ept = EncryptHanlder('./test-dir/encrypt.key') 
    # 解密文件的目标文件夹，将下载的加密文件放入此文件夹
    target_file_folder = './test-dir/dcp'
    file_list = get_files_list(target_file_folder)
    _log.info(f"开始解密路径 '{target_file_folder}' 中的文件 | 文件数量：{len(file_list)}")

    i,g,e = 0,0,0
    for file_path in file_list:
        i+=1
        try:
            # 解密文件会将加密后缀给删除
            ept.decrypt_files(file_path)
            g+=1
            _log.info(f"[{i}] 文件解密：{file_path}")
        except:
            _log.exception(f"[{i}] 解密出错！ {file_path}")
            e+=1