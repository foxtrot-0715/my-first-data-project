# Берем легкий, но полнофункциональный Python 3.11
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Ставим системные библиотеки для компиляции C-расширений и сразу чистим кэш apt
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# КРИТИЧЕСКИЙ ШАГ: Ставим PyTorch строго в CPU-версии! Образ похудеет на 600 мегабайт!
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Копируем весь наш код внутрь
COPY . .

# Прописываем Питону, где корень проекта
ENV PYTHONPATH=/app