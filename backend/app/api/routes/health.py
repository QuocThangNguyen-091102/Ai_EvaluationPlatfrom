from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health(session: Session = Depends(get_session)) -> JSONResponse:
    """Cho biết backend chạy và kết nối được tới DB. Trả 503 khi DB không phản hồi."""
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "degraded", "database": "error"})
    return JSONResponse(content={"status": "ok", "database": "ok"})
