# python3.11.x版本不兼容
FROM python:3.10.6
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
# 本地测试的时候用镜像源安装pip包
# RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

ENV LANG="C.UTF-8" \
    TZ="Asia/Shanghai" \
    PGID=0 \
    PUID=0 \
    BDY_APP_NAME="e2bdy" \
    BDY_SECRET_KEY="" \
    BDY_APP_KEY="" \
    USER_PASSKEY="" \
    ENCRYPT_UPLOAD=1 \
    SYNC_INTERVAL="0 21 * * *"

WORKDIR /app

COPY . /app/
COPY ./config /app/config

VOLUME [ "/app/config" ]

CMD [ "python","main.py" ]