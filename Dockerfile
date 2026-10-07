# サーバと同じ Python 3.8 で動かす(エンジンが 3.8 前提のため)
FROM python:3.8-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# エンジンは同時に1件しか処理できない(モジュール変数を共有している)ため 1プロセス・1スレッド
CMD exec gunicorn -b :$PORT -w 1 --threads 1 -t 900 main:app
