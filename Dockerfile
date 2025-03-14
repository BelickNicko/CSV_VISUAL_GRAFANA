# Базовый образ
FROM python:3.9-slim

RUN apt-get update && \
    apt-get install -y wget && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем скрипт и другие файлы
COPY data_loader.py /app/data_loader.py
COPY all_schemas.yaml /app/all_schemas.yaml

VOLUME /csv_data