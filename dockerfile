FROM python:3.11.2
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

ENV LANG="C.UTF-8" \
    TZ="Asia/Shanghai" \
    PGID=0 \
    PUID=0 \
    BDY_SECRET_KEY="" \
    BDY_APP_KEY="" \
    BDY_APP_NAME="e2bdy" \
    ENCRYPT_UPLOAD=1 \
    SYNC_INTERVAL="0 21 * * *"

WORKDIR /app

COPY . /app/
COPY ./config /app/config

VOLUME [ "/app/config" ]

CMD [ "python","main.py" ]