import logging
import uuid
from dataclasses import dataclass

from ai_engine.embeddings.base_embedder import EmbeddingError
from ai_engine.generation.base_llm_client import LlmError, LlmRateLimitError
from ai_engine.pipeline.rag_pipeline import RagPipeline
from ai_engine.pipeline.rag_result import RagResult
from app.core.exceptions import AppError
from app.models.chat import ChatMessage, ChatSession
from app.models.model_config import ModelConfiguration
from app.models.retrieved_context import RetrievedContext
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.services.model_config_service import ModelConfigService

logger = logging.getLogger(__name__)

_TITLE_LENGTH = 60


@dataclass(frozen=True)
class ChatTurn:
    chat: ChatSession
    message: ChatMessage
    config: ModelConfiguration
    result: RagResult


class ChatService:
    """Hỏi đáp qua RAG pipeline dùng chung, và lưu mỗi lượt hỏi kèm ngữ cảnh, độ trễ, token, chi phí (M4-T05)."""

    def __init__(self, chats: ChatRepository, configs: ModelConfigService, pipeline: RagPipeline) -> None:
        self._chats = chats
        self._configs = configs
        self._pipeline = pipeline

    def ask(self, user: User, question: str, session_id: uuid.UUID | None, config_id: uuid.UUID | None) -> ChatTurn:
        question = question.strip()
        if not question:
            raise AppError(422, "validation_error", "Câu hỏi rỗng")
        config = self._configs.resolve_for_use(user, config_id)
        if session_id is not None:
            chat = self._chats.get_session_for_user(user.id, session_id)
            if chat is None:
                raise AppError(404, "not_found", "Không tìm thấy cuộc hội thoại")
        else:
            chat = self._chats.create_session(user.id, question[:_TITLE_LENGTH])

        self._chats.add_message(ChatMessage(session_id=chat.id, role="user", content=question))

        try:
            result = self._pipeline.run(
                self._chats.db_session, question=question, user_id=user.id, config=self._configs.to_rag_config(config)
            )
        except LlmRateLimitError as error:
            self._record_failure(chat, config, str(error))
            raise AppError(429, "rate_limited", str(error)) from None
        except (LlmError, EmbeddingError) as error:
            self._record_failure(chat, config, str(error))
            raise AppError(502, "provider_error", str(error)) from None

        message = self._chats.add_message(
            ChatMessage(
                session_id=chat.id,
                role="assistant",
                content=result.answer,
                model_configuration_id=config.id,
                insufficient_context=result.insufficient_context,
                latency_ms=result.latency_ms,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                estimated_cost=result.estimated_cost,
            )
        )
        self._chats.add_contexts(message.id, result.contexts)
        self._chats.commit()
        logger.info(
            "Chat answered: user_id=%s message_id=%s mode=%s contexts=%s latency_ms=%s",
            user.id, message.id, result.mode, len(result.contexts), result.latency_ms,
        )
        return ChatTurn(chat=chat, message=message, config=config, result=result)

    def list_sessions(self, user: User, *, limit: int, offset: int):
        return self._chats.list_sessions(user.id, limit=limit, offset=offset)

    def get_messages(self, user: User, session_id: uuid.UUID) -> list[tuple[ChatMessage, list[RetrievedContext]]]:
        chat = self._require_session(user, session_id)
        messages = self._chats.list_messages(chat)
        contexts = self._chats.contexts_for_messages([m.id for m in messages])
        return [(message, contexts.get(message.id, [])) for message in messages]

    def delete_session(self, user: User, session_id: uuid.UUID) -> None:
        self._chats.delete_session(self._require_session(user, session_id))

    def _require_session(self, user: User, session_id: uuid.UUID) -> ChatSession:
        chat = self._chats.get_session_for_user(user.id, session_id)
        if chat is None:
            raise AppError(404, "not_found", "Không tìm thấy cuộc hội thoại")
        return chat

    def _record_failure(self, chat: ChatSession, config: ModelConfiguration, reason: str) -> None:
        # Giữ lại câu hỏi và lỗi trong lịch sử, để người dùng thấy câu nào đã thất bại.
        self._chats.add_message(
            ChatMessage(session_id=chat.id, role="assistant", content="", model_configuration_id=config.id, error_message=reason)
        )
        self._chats.commit()
