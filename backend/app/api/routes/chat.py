import uuid

from fastapi import APIRouter, Depends, Query, Response, status

from ai_engine.pipeline.context_builder import cited_numbers
from app.api.dependencies import get_chat_service, get_current_user
from app.models.retrieved_context import RetrievedContext
from app.models.user import User
from app.schemas.chat import (
    AnswerMetrics,
    AskRequest,
    ChatAnswerResponse,
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    CitationResponse,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])

_SNIPPET_CHARS = 400


def _source(number, chunk_id, filename, page_number, score, content) -> CitationResponse:
    return CitationResponse(
        number=number,
        chunk_id=chunk_id,
        filename=filename,
        page_number=page_number,
        score=round(score, 4),
        snippet=content[:_SNIPPET_CHARS],
    )


def _stored_source(context: RetrievedContext) -> CitationResponse:
    return _source(
        context.rank,
        context.chunk_id,
        context.document_filename_snapshot,
        context.page_number,
        context.score,
        context.content_snapshot,
    )


@router.post("/messages", response_model=ChatAnswerResponse)
def ask(
    payload: AskRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatAnswerResponse:
    turn = service.ask(current_user, payload.question, payload.session_id, payload.model_configuration_id)
    result = turn.result
    sources = [_source(c.rank, c.chunk_id, c.filename, c.page_number, c.score, c.content) for c in result.contexts]
    by_number = {source.number: source for source in sources}
    return ChatAnswerResponse(
        session_id=turn.chat.id,
        message_id=turn.message.id,
        answer=result.answer,
        insufficient_context=result.insufficient_context,
        mode=result.mode,
        citations=[by_number[c.number] for c in result.citations],
        sources=sources,
        metrics=AnswerMetrics(
            latency_ms=result.latency_ms,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            estimated_cost=result.estimated_cost,
        ),
        model_configuration_id=turn.config.id,
    )


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatSessionListResponse:
    items, total = service.list_sessions(current_user, limit=limit, offset=offset)
    return ChatSessionListResponse(
        items=[ChatSessionResponse(id=s.id, title=s.title, created_at=s.created_at) for s in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/sessions/{session_id}/messages", response_model=ChatMessageListResponse)
def list_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatMessageListResponse:
    items = []
    for message, contexts in service.get_messages(current_user, session_id):
        sources = [_stored_source(context) for context in contexts]
        by_number = {source.number: source for source in sources}
        cited = [] if message.insufficient_context else cited_numbers(message.content, len(sources))
        items.append(
            ChatMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
                insufficient_context=message.insufficient_context,
                model_configuration_id=message.model_configuration_id,
                error_message=message.error_message,
                citations=[by_number[number] for number in cited],
                sources=sources,
                metrics=AnswerMetrics(
                    latency_ms=message.latency_ms,
                    prompt_tokens=message.prompt_tokens,
                    completion_tokens=message.completion_tokens,
                    estimated_cost=message.estimated_cost,
                ),
            )
        )
    return ChatMessageListResponse(items=items)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> Response:
    service.delete_session(current_user, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
