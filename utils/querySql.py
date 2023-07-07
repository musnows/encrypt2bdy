import peewee
from playhouse.pool import SqliteDatabase
from playhouse.shortcuts import model_to_dict

from .gtime import get_datetime_now
from .myLog import _log

sqliteDB = SqliteDatabase("./config/e2bdy.db")
"""sqlite3数据库连接"""

class BaseTable(peewee.Model):
    """生成基类 所有表构建的类都是基类之上的 继承这个基类"""

    class Meta:
        database = sqliteDB

    def __str__(self):
        """打印的时候转成dict再返回"""
        return str(model_to_dict(self))

class FilePath(BaseTable):
    """已上传文件缓存"""
    class Meta:
        db_table = 'file_upd'  # 表名

    file_path = peewee.TextField(
        null=False,
        help_text='文件路径'
    )
    remote_path = peewee.TextField(
        null=False,
        help_text='远程文件路径'
    )
    file_md5 = peewee.TextField(
        null=False,
        unique=True,
        help_text='文件md5'
    )
    insert_time = peewee.TimestampField(null=False,
                                    default=get_datetime_now().now,
                                    help_text='插入时间')
    
class ErrFilePath(BaseTable):
    """错误文件"""
    class Meta:
        db_table = 'file_err'

    file_path = peewee.TextField(
        null=False,
        help_text='文件路径'
    )
    file_md5 = peewee.TextField(
        null=False,
        unique=True,
        help_text='文件md5'
    )
    insert_time = peewee.TimestampField(null=False,
                                    default=get_datetime_now().now,
                                    help_text='插入时间')
    

sqliteDB.create_tables([
    FilePath,ErrFilePath
])
sqliteDB.close()
_log.info(f"[sqlite3] create all tables")