FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY app ./app

# Chạy bằng user thường, không dùng root. Thư mục upload phải thuộc user này để volume `uploads` ghi được.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/uploads \
    && chown appuser /app/uploads
USER appuser

EXPOSE 8000

# Áp dụng migration rồi mới khởi động API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
