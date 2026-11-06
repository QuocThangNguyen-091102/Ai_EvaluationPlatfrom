"""Truy xuất có kiểm soát quyền: test quan trọng nhất về cô lập dữ liệu (gate M4)."""

import uuid

import pytest

from ai_engine.ingestion.ingestion_pipeline import ingest
from ai_engine.retrieval.metadata_filters import RetrievalScope
from ai_engine.retrieval.vector_retriever import retrieve
from app.models import Document, User
from app.repositories.chunk_repository import ChunkRepository
from tests.fakes import HashEmbedder

pytestmark = pytest.mark.integration

EMBEDDER = HashEmbedder()


def _user(session) -> User:
    user = User(email=f"{uuid.uuid4()}@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


def _document(session, user, text: str, *, filename="tai-lieu.txt", status="ready", chunk_size=50) -> Document:
    document = Document(
        user_id=user.id,
        filename=filename,
        content_type="text/plain",
        size_bytes=len(text),
        content_hash=uuid.uuid4().hex + uuid.uuid4().hex[:32],
        storage_path="x",
        status=status,
    )
    session.add(document)
    session.flush()
    result = ingest(text.encode(), "text/plain", chunk_size=chunk_size, chunk_overlap=0, embedder=EMBEDDER)
    ChunkRepository(session).replace_chunks(
        user_id=user.id, document_id=document.id, chunks=result.chunks, embedding_model=EMBEDDER.model_name
    )
    return document


def _search(session, user, question, top_k=5, document_ids=None):
    return retrieve(session, EMBEDDER.embed_query(question), RetrievalScope(user.id, document_ids), top_k=top_k)


SECRET = "canary-bi-mat-cua-nguoi-khac luong thuong nam 2026 cua giam doc"


def test_user_never_receives_another_users_chunks_even_when_asking_for_them(db_session):
    alice, bob = _user(db_session), _user(db_session)
    _document(db_session, alice, "Quy định nộp hồ sơ trong 30 ngày.")
    _document(db_session, bob, SECRET, filename="bi-mat.txt")

    results = _search(db_session, alice, SECRET, top_k=50)

    assert results, "alice vẫn phải nhận kết quả từ tài liệu của chính mình"
    assert all("canary" not in r.content for r in results)
    assert all(r.filename != "bi-mat.txt" for r in results)


def test_user_with_no_documents_gets_nothing_even_if_others_have_matches(db_session):
    newcomer, bob = _user(db_session), _user(db_session)
    _document(db_session, bob, SECRET)

    assert _search(db_session, newcomer, SECRET, top_k=50) == []


def test_document_filter_cannot_reach_another_users_document(db_session):
    alice, bob = _user(db_session), _user(db_session)
    _document(db_session, alice, "tài liệu của alice")
    bobs = _document(db_session, bob, SECRET)

    assert _search(db_session, alice, SECRET, document_ids=[bobs.id]) == []


def test_most_similar_chunk_is_ranked_first(db_session):
    user = _user(db_session)
    _document(db_session, user, "Món phở bò nấu từ xương ống hầm nhiều giờ.", filename="pho.txt")
    _document(db_session, user, "Hồ sơ xin cấp giấy phép phải nộp trong 30 ngày.", filename="giay-phep.txt")

    results = _search(db_session, user, "nộp hồ sơ giấy phép trong bao nhiêu ngày")

    assert results[0].filename == "giay-phep.txt"
    assert [r.rank for r in results] == list(range(1, len(results) + 1))
    assert results[0].score >= results[-1].score


def test_top_k_limits_the_number_of_results(db_session):
    user = _user(db_session)
    _document(db_session, user, " ".join(f"từ{i}" for i in range(500)), chunk_size=20)

    assert len(_search(db_session, user, "từ1", top_k=3)) == 3


def test_document_filter_restricts_to_selected_documents(db_session):
    user = _user(db_session)
    keep = _document(db_session, user, "giấy phép kinh doanh", filename="keep.txt")
    _document(db_session, user, "giấy phép kinh doanh bản khác", filename="other.txt")

    results = _search(db_session, user, "giấy phép", document_ids=[keep.id])

    assert {r.filename for r in results} == {"keep.txt"}


@pytest.mark.parametrize("status", ["uploaded", "processing", "failed"])
def test_only_ready_documents_are_searched(db_session, status):
    user = _user(db_session)
    _document(db_session, user, "giấy phép đang xử lý", status=status)

    assert _search(db_session, user, "giấy phép") == []


def test_result_carries_location_for_citations(db_session):
    user = _user(db_session)
    document = _document(db_session, user, "Hồ sơ phải nộp trong 30 ngày.", filename="quy-dinh.txt")

    top = _search(db_session, user, "hồ sơ nộp")[0]

    assert (top.document_id, top.filename, top.chunk_index) == (document.id, "quy-dinh.txt", 0)
    assert top.content == "Hồ sơ phải nộp trong 30 ngày."
    assert -1.0 <= top.score <= 1.0001


def test_invalid_scope_and_top_k_are_rejected(db_session):
    user = _user(db_session)
    with pytest.raises(ValueError):
        RetrievalScope(user_id="khong-phai-uuid")
    with pytest.raises(ValueError):
        RetrievalScope(user_id=user.id, document_ids=[])
    with pytest.raises(ValueError):
        _search(db_session, user, "x", top_k=0)
