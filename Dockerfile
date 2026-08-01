FROM python:3.11-slim

# Build tools (asyncpg C extension uchun kerak)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pip yangilash va dependencies o'rnatish
COPY bot/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Bot kodini ko'chirish
COPY bot/ ./bot/

# Unbuffered output (loglar tezroq ko'rinsin)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Ishga tushirish
CMD ["python3", "-u", "bot/main.py"]
