# encrypt2bdy

使用python将文件加密后上传到百度云。

```
docker pull musnows/e2bdy
```

百度网盘对非VIP用户的API上传限制为单文件10GB，超过10G的文件，会在判断后跳过。

由于性能缘故，并不推荐您使用本项目备份大文件，建议用于备份照片、文档等小文件！

经过本地测试，8分钟上传了1.9GB文件，平均速度有4mb/s，对于备份来说够用！

## 配置

1. 申请百度云盘开发者应用

先进行[个人开发者认证](https://pan.baidu.com/union/doc/ml0g2vtvb)（需要实名百度账户和绑定邮箱）然后[创建应用](https://pan.baidu.com/union/doc/fl0hhnulu)

记录下应用的 AppKey 和 Secretkey，分别填入环境变量的 `BDY_APP_KEY` 和 `BDY_SECRET_KEY`

可选环境变量：`BDY_APP_NAME` 应用名字，不填默认为 `e2bdy`

2. 映射路径

需要映射一个 `/app/config` 路径，作为数据库、配置文件、加密密钥的存放路径。

其他路径自由映射为你需要备份的路径。赋予读写权限以避免权限问题的BUG

3. 是否加密

设置环境变量 `ENCRYPT_UPLOAD` 为 1，文件将在加密后被上传。若不需要加密，请设置为0。

应用会在 `/app/config` 路径生成 `encrypt.key` 文件，该文件用于加密和解密文件的操作。

请注意，加密密钥不要发送、拷贝给任何人！同时也需要做好该密钥的备份操作，否则上传到百度云的加密文件将无法被正常解密！

> 后续将提供独立的解密程序，只要 `encrypt.key` 还存在，云端文件没有损坏，就能成功解密备份到百度云盘的文件。

4. 监控间隔

设置环境变量 `SYNC_INTERVAL` 为五位cron表达式。

建议设置为间隔时长大于10分钟的表达式。如果您需要同步的文件非常之多，请适当延长此时间，避免出现上个task还没跑完，下一个就要开始了的情况。如果文件过多，但休眠时长过短，可能会导致硬盘io持续走高，影响其他进程运行。

下面给出几个常用的表达式，可以使用[在线工具](https://tool.lu/crontab/)查看表达式执行时间 

```python
0 21 * * *     # 每天21点执行一次
0 8 * * *      # 每一天的8点执行一次
0 3,5,21 * * * # 每天3点、5点、21点执行一次
0 0-8 * * *    # 每一天0-8点每小时执行一次
0 0-8/2 * * *  # 每一天0-8天每2小时执行一次
*/12 * * * *   # 每12分钟执行一次
```

默认的 cron 设置为 `0 21 * * *`，即每天21点扫描本地，备份新文件到百度云盘

程序将在对应间隔后重新检查本地路径的文件列表，并将新文件上传到百度云。

上传文件的判断基于本地数据库中，对应文件的哈希值是否存在。如果一个文件的哈希已经存在，则认为该文件已经上传。

所以，本程序并**不会**检查你是否已经将云端的文件删除，本地文件删除同样不会同步到云端。

> 后续将提供更多配置项来确定文件是否需要上传

5. 路径配置

将本仓库内 [config-exp.yml](./config/config-exp.yml) 复制并重命名为 `config.yml`，放入一个空文件夹，并将此文件夹映射给docker镜像的 `/app/config` 路径。

配置文件内只需要修改你的备份路径配置，其余token和配置项请以环境变量为准！下面给出备份路径配置示例。

假设我将我的硬盘映射到了docker容器的 `/hdd` 路径，并需要备份该路径中的 `照片` 文件夹。

照片文件夹内有如下文件

```
test/img1.png
img2.png
img3.png
```

在yaml内的配置如下

```yaml
- local: '/hdd/照片'
  remote: '照片1'
```

最终，程序会将文件上传到百度云盘的如下文件夹

```
apps/应用名称/照片1/hdd/照片/test/img1.png
apps/应用名称/照片1/hdd/照片/img2.png
apps/应用名称/照片1/hdd/照片/img3.png
```

* 其中 apps 文件夹在客户端中显示为 `我的应用数据`，百度网盘使用api上传的文件只能上传到此路径。
* 应用名称为第一点中提到的 `BDY_APP_NAME` 环境变量。
* 如果你开启了加密，程序会给文件添加上加密的后缀 `.e2bdy`

请注意，远端文件路径只能指定为文件夹名称，或只能中间带上路径分隔符！

```bash
/test/test   # 不合法
./test/test  # 不合法
test/test/   # 不合法
./test/test/ # 不合法
test/test    # ok
```

请遵循如上配置要求，否则程序会在检测到远端路径配置无效后直接退出。

6. 时区

由于docker配置时区可能会因为不同配置项而出现预期之外的问题，再考虑到百度网盘主要目标用户均为国内用户，本程序中已将时区、获取当前时间函数均固定为了东八区时间。

如果您不在国内，配置 cron 表达式的时候，请以东八区时间为准。

## 解密

参考本仓库wiki文档 -> [WIKI](./wiki)

## 已知错误

### 1.docker退出码137

内存不足时，系统将对应docker容器终止。出现此问题，请确认您要备份的文件中不会出现大于您系统内存或docker容器内存限制的文件。

正如开头所说，本项目适合于备份照片、图片、文档等小文件，并不建议用于备份录像、电影等资源。

## 支持

您的下载使用就是对本人最大的任何可支持！如果能给个star就更好啦！

有任何问题，欢迎提出issue
