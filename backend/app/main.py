from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import get_ingestion_service
from app.api.routes import auth, chat, datasets, documents, health, model_configs
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Tác vụ nền của lần chạy trước đã mất khi tiến trình dừng: đánh dấu để người dùng xử lý lại (R9).
    get_ingestion_service().recover_interrupted()
    yield


app = FastAPI(title="AI Evaluation Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(model_configs.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")
