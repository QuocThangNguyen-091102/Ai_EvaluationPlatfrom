# Import mọi model để Base.metadata biết đầy đủ các bảng (Alembic dựa vào đó).
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User

__all__ = ["Document", "DocumentChunk", "User"]
