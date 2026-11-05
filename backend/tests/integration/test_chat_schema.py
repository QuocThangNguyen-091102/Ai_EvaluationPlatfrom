import uuid

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.models import (
    ChatMessage,
    ChatSession,
    Document,
    DocumentChunk,
    ModelConfiguration,
    RetrievedContext,
    User,
)
from app.models.document_chunk import EMBEDDING_DIMENSIONS

pytestmark = pytest.mark.integration


def _user(session) -> User:
    user = User(email=f"{uuid.uuid4()}@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


def _config(session, user, **overrides) -> ModelConfiguration:
    values = dict(
        user_id=user.id,
        name=f"cau-hinh-{uuid.uuid4().hex[:8]}",
        llm_provider="test",
        llm_model="model-a",
        embedding_provider="local",
        embedding_model="intfloat/multilingual-e5-small",
        prompt_version="v1",
        top_k=5,
        temperature=0.0,
        chunk_size=200,
        chunk_overlap=40,
    )
    values.update(overrides)
    config = ModelConfiguration(**values)
    session.add(config)
    session.flush()
    return config


def _chat_session(session, user) -> ChatSession:
    chat = ChatSession(user_id=user.id, title="Hội thoại thử")
    session.add(chat)
    session.flush()
    return chat


def _message(session, chat, role="assistant", config=None) -> ChatMessage:
    message = ChatMessage(
        session_id=chat.id,
        role=role,
        content="nội dung",
        model_configuration_id=config.id if config else None,
    )
    session.add(message)
    session.flush()
    return message


def _chunk(session, user) -> DocumentChunk:
    document = Document(
        user_id=user.id,
        filename="a.txt",
        content_type="text/plain",
        size_bytes=1,
        content_hash=uuid.uuid4().hex + uuid.uuid4().hex[:32],
        storage_path="x",
    )
    session.add(document)
    session.flush()
    chunk = DocumentChunk(
        document_id=document.id,
        user_id=user.id,
        chunk_index=0,
        content="nội dung chunk",
        char_start=0,
        char_end=14,
        embedding=[0.1] * EMBEDDING_DIMENSIONS,
        embedding_model="test",
    )
    session.add(chunk)
    session.flush()
    return chunk


def _context(session, message, chunk=None) -> RetrievedContext:
    context = RetrievedContext(
        chat_message_id=message.id,
        chunk_id=chunk.id if chunk else None,
        rank=1,
        score=0.9,
        content_snapshot="bản chụp nội dung chunk",
        document_filename_snapshot="a.txt",
        page_number=1,
    )
    session.add(context)
    session.flush()
    return context


# ------------------------------------------------------------------------------ model_configurations
def test_model_configuration_can_be_created(db_session):
    config = _config(db_session, _user(db_session))

    assert config.id is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"top_k": 0},
        {"temperature": -0.1},
        {"temperature": 2.5},
        {"chunk_size": 0},
        {"chunk_overlap": -1},
        {"chunk_size": 100, "chunk_overlap": 100},
    ],
)
def test_model_configuration_rejects_invalid_numbers(db_session, overrides):
    with pytest.raises(IntegrityError):
        _config(db_session, _user(db_session), **overrides)


def test_model_configuration_name_is_unique_per_user_only(db_session):
    first, second = _user(db_session), _user(db_session)
    _config(db_session, first, name="mac-dinh")

    _config(db_session, second, name="mac-dinh")
    with pytest.raises(IntegrityError):
        _config(db_session, first, name="mac-dinh")


# ------------------------------------------------------------------------------ chat
def test_message_role_must_be_user_or_assistant(db_session):
    chat = _chat_session(db_session, _user(db_session))

    with pytest.raises(IntegrityError):
        _message(db_session, chat, role="system")


def test_deleting_a_session_removes_messages_and_contexts(db_session):
    user = _user(db_session)
    chat = _chat_session(db_session, user)
    message = _message(db_session, chat)
    _context(db_session, message)

    db_session.execute(delete(ChatSession).where(ChatSession.id == chat.id))

    assert db_session.scalar(select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == chat.id)) == 0
    assert (
        db_session.scalar(select(func.count()).select_from(RetrievedContext).where(RetrievedContext.chat_message_id == message.id))
        == 0
    )


def test_deleting_a_user_removes_everything_under_them(db_session):
    user = _user(db_session)
    chat = _chat_session(db_session, user)
    _message(db_session, chat)
    _config(db_session, user)

    db_session.execute(delete(User).where(User.id == user.id))

    assert db_session.scalar(select(func.count()).select_from(ChatSession).where(ChatSession.user_id == user.id)) == 0
    assert db_session.scalar(select(func.count()).select_from(ModelConfiguration).where(ModelConfiguration.user_id == user.id)) == 0


def test_configuration_in_use_by_a_message_cannot_be_deleted(db_session):
    user = _user(db_session)
    config = _config(db_session, user)
    _message(db_session, _chat_session(db_session, user), config=config)

    with pytest.raises(IntegrityError):
        db_session.execute(delete(ModelConfiguration).where(ModelConfiguration.id == config.id))


def test_unused_configuration_can_be_deleted(db_session):
    config = _config(db_session, _user(db_session))

    db_session.execute(delete(ModelConfiguration).where(ModelConfiguration.id == config.id))


# ------------------------------------------------------------------------------ retrieved_contexts
def test_deleting_a_chunk_keeps_the_context_and_its_snapshot(db_session):
    user = _user(db_session)
    chunk = _chunk(db_session, user)
    context = _context(db_session, _message(db_session, _chat_session(db_session, user)), chunk)

    db_session.execute(delete(DocumentChunk).where(DocumentChunk.id == chunk.id))
    db_session.refresh(context)

    assert context.chunk_id is None
    assert context.content_snapshot == "bản chụp nội dung chunk"


def test_deleting_the_document_keeps_the_context_snapshot(db_session):
    user = _user(db_session)
    chunk = _chunk(db_session, user)
    context = _context(db_session, _message(db_session, _chat_session(db_session, user)), chunk)

    db_session.execute(delete(Document).where(Document.id == chunk.document_id))
    db_session.refresh(context)

    assert context.chunk_id is None
    assert context.document_filename_snapshot == "a.txt"


def test_context_must_belong_to_exactly_one_owner(db_session):
    with pytest.raises(IntegrityError):
        db_session.add(
            RetrievedContext(
                chat_message_id=None,
                rank=1,
                score=0.5,
                content_snapshot="x",
                document_filename_snapshot="a.txt",
            )
        )
        db_session.flush()
