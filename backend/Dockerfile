FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/model-cache

WORKDIR /app

# Build context là thư mục gốc repo (để copy được cả ai_engine/).
COPY backend/requirements.txt .
# PyTorch bản CPU: bản mặc định trên Linux kéo theo CUDA (vài GB), không dùng được trên máy chủ miễn phí.
RUN pip install --no-cache-dir torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY backend/alembic.ini .
COPY backend/app ./app
COPY ai_engine ./ai_engine
COPY evaluation ./evaluation
COPY configs ./configs

# Chạy bằng user thường, không dùng root. Thư mục upload và cache model phải thuộc user này để volume ghi được.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/uploads /app/model-cache \
    && chown appuser /app/uploads /app/model-cache
USER appuser

EXPOSE 8000

# Áp dụng migration rồi mới khởi động API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
