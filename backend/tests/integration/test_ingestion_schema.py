import uuid

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import DataError, IntegrityError

from app.models import Document, DocumentChunk, User
from app.models.document_chunk import EMBEDDING_DIMENSIONS

pytestmark = pytest.mark.integration


def _make_user(session, email=None) -> User:
    user = User(email=email or f"{uuid.uuid4()}@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


def _make_document(session, user, content_hash=None, **overrides) -> Document:
    document = Document(
        user_id=user.id,
        filename="policy.pdf",
        content_type="application/pdf",
        size_bytes=1234,
        content_hash=content_hash or uuid.uuid4().hex + uuid.uuid4().hex[:32],
        storage_path="uploads/policy.pdf",
        **overrides,
    )
    session.add(document)
    session.flush()
    return document


def _make_chunk(session, document, chunk_index=0, user_id=None, embedding=None) -> DocumentChunk:
    chunk = DocumentChunk(
        document_id=document.id,
        user_id=user_id or document.user_id,
        chunk_index=chunk_index,
        content="nội dung chunk",
        page_number=1,
        char_start=0,
        char_end=14,
        embedding=embedding or [0.1] * EMBEDDING_DIMENSIONS,
        embedding_model="test-model",
    )
    session.add(chunk)
    session.flush()
    return chunk


def test_tables_exist(db_session):
    tables = {
        row.table_name
        for row in db_session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_name IN ('users','documents','document_chunks')")
        )
    }
    assert tables == {"users", "documents", "document_chunks"}


def test_embedding_column_has_the_configured_dimension(db_session):
    column_type = db_session.execute(
        text(
            "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
            "WHERE attrelid = 'document_chunks'::regclass AND attname = 'embedding'"
        )
    ).scalar_one()
    assert column_type == f"vector({EMBEDDING_DIMENSIONS})"


def test_expected_indexes_exist(db_session):
    names = {
        row[0]
        for row in db_session.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename IN ('users','documents','document_chunks')")
        )
    }
    assert {
        "uq_users_email",
        "uq_documents_user_id_content_hash",
        "uq_documents_id_user_id",
        "ix_documents_user_id_created_at",
        "ix_documents_status",
        "uq_document_chunks_document_id_chunk_index",
        "ix_document_chunks_user_id",
    } <= names


def test_vector_with_wrong_dimension_is_rejected(db_session):
    document = _make_document(db_session, _make_user(db_session))

    with pytest.raises((DataError, IntegrityError)):
        _make_chunk(db_session, document, embedding=[0.1] * (EMBEDDING_DIMENSIONS - 1))


def test_chunk_cannot_claim_a_different_owner_than_its_document(db_session):
    owner = _make_user(db_session)
    other_user = _make_user(db_session)
    document = _make_document(db_session, owner)

    with pytest.raises(IntegrityError):
        _make_chunk(db_session, document, user_id=other_user.id)


def test_same_content_cannot_be_uploaded_twice_by_the_same_user(db_session):
    user = _make_user(db_session)
    _make_document(db_session, user, content_hash="a" * 64)

    with pytest.raises(IntegrityError):
        _make_document(db_session, user, content_hash="a" * 64)


def test_different_users_may_hold_the_same_content(db_session):
    first = _make_user(db_session)
    second = _make_user(db_session)

    _make_document(db_session, first, content_hash="b" * 64)
    _make_document(db_session, second, content_hash="b" * 64)


def test_email_must_be_unique(db_session):
    _make_user(db_session, email="same@example.com")

    with pytest.raises(IntegrityError):
        _make_user(db_session, email="same@example.com")


def test_document_status_defaults_to_uploaded_and_rejects_unknown_values(db_session):
    user = _make_user(db_session)
    document = _make_document(db_session, user)
    db_session.refresh(document)
    assert document.status == "uploaded"

    with pytest.raises(IntegrityError):
        _make_document(db_session, user, status="finished")


def test_deleting_a_document_removes_its_chunks(db_session):
    document = _make_document(db_session, _make_user(db_session))
    _make_chunk(db_session, document, chunk_index=0)
    _make_chunk(db_session, document, chunk_index=1)

    db_session.execute(delete(Document).where(Document.id == document.id))

    remaining = db_session.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document.id))
    assert remaining == 0


def test_deleting_a_user_removes_documents_and_chunks(db_session):
    user = _make_user(db_session)
    document = _make_document(db_session, user)
    _make_chunk(db_session, document)

    db_session.execute(delete(User).where(User.id == user.id))

    assert db_session.scalar(select(func.count()).select_from(Document).where(Document.user_id == user.id)) == 0
    assert db_session.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.user_id == user.id)) == 0


def test_chunk_order_within_a_document_is_unique(db_session):
    document = _make_document(db_session, _make_user(db_session))
    _make_chunk(db_session, document, chunk_index=0)

    with pytest.raises(IntegrityError):
        _make_chunk(db_session, document, chunk_index=0)


def test_vector_distance_query_returns_nearest_chunk_first(db_session):
    user = _make_user(db_session)
    document = _make_document(db_session, user)
    near = _make_chunk(db_session, document, chunk_index=0, embedding=[1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1))
    _make_chunk(db_session, document, chunk_index=1, embedding=[0.0, 1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 2))

    query_vector = [0.9] + [0.1] + [0.0] * (EMBEDDING_DIMENSIONS - 2)
    nearest = db_session.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.user_id == user.id)
        .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
        .limit(1)
    ).one()

    assert nearest.id == near.id
