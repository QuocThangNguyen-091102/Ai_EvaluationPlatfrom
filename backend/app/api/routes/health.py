from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    """Cho biết backend đang chạy. Trạng thái kết nối DB được thêm ở M2-T05."""
    return {"status": "ok"}
