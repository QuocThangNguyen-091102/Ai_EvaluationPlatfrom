import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ai_engine.retrieval.vector_retriever import RetrievedChunk
from app.models.chat import ChatMessage, ChatSession
from app.models.retrieved_context import RetrievedContext


class ChatRepository:
    """Truy cập chat_sessions, chat_messages và retrieved_contexts. Mọi truy vấn của user đều lọc theo user_id."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def db_session(self) -> Session:
        """Session dùng chung cho pipeline (truy xuất vector chạy trong cùng transaction)."""
        return self._session

    def get_session_for_user(self, user_id: uuid.UUID, session_id: uuid.UUID) -> ChatSession | None:
        return self._session.scalar(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id))

    def create_session(self, user_id: uuid.UUID, title: str) -> ChatSession:
        chat = ChatSession(user_id=user_id, title=title)
        self._session.add(chat)
        self._session.flush()
        return chat

    def list_sessions(self, user_id: uuid.UUID, *, limit: int, offset: int) -> tuple[list[ChatSession], int]:
        total = self._session.scalar(select(func.count()).select_from(ChatSession).where(ChatSession.user_id == user_id))
        items = self._session.scalars(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc(), ChatSession.id)
            .limit(limit)
            .offset(offset)
        ).all()
        return list(items), total

    def delete_session(self, chat: ChatSession) -> None:
        self._session.execute(delete(ChatSession).where(ChatSession.id == chat.id, ChatSession.user_id == chat.user_id))
        self._session.commit()

    def add_message(self, message: ChatMessage) -> ChatMessage:
        self._session.add(message)
        self._session.flush()
        return message

    def add_contexts(self, message_id: uuid.UUID, chunks: Sequence[RetrievedChunk]) -> None:
        self._session.add_all(
            RetrievedContext(
                chat_message_id=message_id,
                chunk_id=chunk.chunk_id,
                rank=chunk.rank,
                score=chunk.score,
                content_snapshot=chunk.content,
                document_filename_snapshot=chunk.filename,
                page_number=chunk.page_number,
            )
            for chunk in chunks
        )
        self._session.flush()

    def list_messages(self, chat: ChatSession) -> list[ChatMessage]:
        return list(
            self._session.scalars(
                select(ChatMessage)
                .where(ChatMessage.session_id == chat.id)
                .order_by(ChatMessage.created_at, ChatMessage.id)
            )
        )

    def contexts_for_messages(self, message_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, list[RetrievedContext]]:
        if not message_ids:
            return {}
        rows = self._session.scalars(
            select(RetrievedContext)
            .where(RetrievedContext.chat_message_id.in_(message_ids))
            .order_by(RetrievedContext.chat_message_id, RetrievedContext.rank)
        ).all()
        grouped: dict[uuid.UUID, list[RetrievedContext]] = {}
        for row in rows:
            grouped.setdefault(row.chat_message_id, []).append(row)
        return grouped

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
