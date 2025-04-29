# Базовый образ
FROM python:3.11-slim

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Запуск сервера
CMD ["gunicorn", "--bind --timeout 120 --workers 25", "0.0.0.0:8000", "config.wsgi:application"]