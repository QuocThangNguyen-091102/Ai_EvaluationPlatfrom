import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from ai_engine.embeddings.base_embedder import InputTooLongError
from app.core.config import settings
from app.models import Document, DocumentChunk
from app.services.ingestion_service import INTERRUPTED_MESSAGE, UNEXPECTED_MESSAGE

pytestmark = pytest.mark.integration

DOCUMENTS = "/api/v1/documents"
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    return tmp_path


def _upload(client, headers, name: str, content: bytes, content_type="application/octet-stream") -> dict:
    response = client.post(DOCUMENTS, headers=headers, files={"file": (name, content, content_type)})
    assert response.status_code == 202, response.text
    return response.json()


def _detail(client, headers, document_id) -> dict:
    return client.get(f"{DOCUMENTS}/{document_id}", headers=headers).json()


def _chunks(db_session, document_id) -> list[DocumentChunk]:
    return list(
        db_session.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == uuid.UUID(document_id)).order_by(DocumentChunk.chunk_index)
        )
    )


def _words(n: int) -> str:
    return " ".join(f"từ{i}" for i in range(n))


# ------------------------------------------------------------------------------------------- xử lý thành công
def test_uploaded_txt_is_processed_to_ready_with_chunks_and_vectors(api_client, make_authenticated_user, db_session):
    headers = make_authenticated_user()
    uploaded = _upload(api_client, headers, "ghi-chu.txt", _words(600).encode())
    assert uploaded["status"] == "uploaded"  # phản hồi trả trước khi xử lý nền

    detail = _detail(api_client, headers, uploaded["id"])

    assert detail["status"] == "ready"
    assert detail["error_message"] is None
    assert detail["chunk_count"] == 3
    assert detail["processing_config"] == {
        "chunk_size": 250,
        "chunk_overlap": 50,
        "chunk_unit": "words",
        "embedding_model": "test-hash-embedder",
    }
    chunks = _chunks(db_session, uploaded["id"])
    assert [c.chunk_index for c in chunks] == [0, 1, 2]
    assert all(len(c.embedding) == 384 and c.embedding_model == "test-hash-embedder" for c in chunks)


def test_chunks_belong_to_the_uploader(api_client, make_authenticated_user, db_session):
    headers = make_authenticated_user()
    uploaded = _upload(api_client, headers, "a.txt", "nội dung riêng".encode())
    owner = db_session.get(Document, uuid.UUID(uploaded["id"])).user_id

    assert {c.user_id for c in _chunks(db_session, uploaded["id"])} == {owner}


def test_real_vietnamese_pdf_is_processed_with_page_numbers(api_client, make_authenticated_user, db_session):
    headers = make_authenticated_user()
    uploaded = _upload(api_client, headers, "quy-dinh.pdf", (FIXTURES / "vi_two_pages.pdf").read_bytes())

    assert _detail(api_client, headers, uploaded["id"])["status"] == "ready"
    chunks = _chunks(db_session, uploaded["id"])
    assert chunks[0].page_number == 1
    assert "giấy phép" in " ".join(c.content for c in chunks)


def test_embedder_receives_the_chunk_texts(api_client, make_authenticated_user, test_embedder):
    headers = make_authenticated_user()
    _upload(api_client, headers, "a.txt", "Hồ sơ phải nộp trong 30 ngày.".encode())

    assert test_embedder.passage_calls == [["Hồ sơ phải nộp trong 30 ngày."]]


# ------------------------------------------------------------------------------------------- lỗi
def test_corrupt_pdf_ends_as_failed_with_a_clear_reason(api_client, make_authenticated_user, db_session):
    headers = make_authenticated_user()
    uploaded = _upload(api_client, headers, "hong.pdf", b"%PDF-1.7\nnoi dung hong, khong phai pdf that\n")

    detail = _detail(api_client, headers, uploaded["id"])

    assert detail["status"] == "failed"
    assert "PDF" in detail["error_message"]
    assert _chunks(db_session, uploaded["id"]) == []


def test_text_too_long_for_the_model_ends_as_failed_with_advice(api_client, make_authenticated_user, test_embedder):
    test_embedder._fail_with = InputTooLongError("Đoạn thứ 1 dài 900 token, vượt giới hạn 512 token của model; hãy giảm kích thước chunk")
    headers = make_authenticated_user()
    uploaded = _upload(api_client, headers, "a.txt", "nội dung".encode())

    detail = _detail(api_client, headers, uploaded["id"])

    assert detail["status"] == "failed"
    assert "giảm kích thước chunk" in detail["error_message"]


def test_unexpected_error_is_reported_without_internal_detail(api_client, make_authenticated_user, test_embedder):
    test_embedder._fail_with = RuntimeError("chi tiết nội bộ bí mật")
    headers = make_authenticated_user()
    uploaded = _upload(api_client, headers, "a.txt", "nội dung".encode())

    detail = _detail(api_client, headers, uploaded["id"])

    assert detail["status"] == "failed"
    assert detail["error_message"] == UNEXPECTED_MESSAGE
    assert "bí mật" not in detail["error_message"]


def test_missing_original_file_ends_as_failed(api_client, make_authenticated_user, ingestion_service, isolated_upload_dir):
    headers = make_authenticated_user()
    uploaded = _upload(api_client, headers, "a.txt", "nội dung".encode())
    for stored in isolated_upload_dir.rglob("*"):
        if stored.is_file():
            stored.unlink()

    ingestion_service.process(uuid.UUID(uploaded["id"]))

    detail = _detail(api_client, headers, uploaded["id"])
    assert detail["status"] == "failed"
    assert "file gốc" in detail["error_message"]


def test_processing_a_deleted_document_does_nothing(ingestion_service):
    ingestion_service.process(uuid.uuid4())  # không ném lỗi


# ------------------------------------------------------------------------------------------- reprocess
def test_reprocess_with_smaller_chunks_replaces_chunks_without_duplicates(api_client, make_authenticated_user, db_session):
    headers = make_authenticated_user()
    uploaded = _upload(api_client, headers, "a.txt", _words(600).encode())
    assert _detail(api_client, headers, uploaded["id"])["chunk_count"] == 3

    response = api_client.post(
        f"{DOCUMENTS}/{uploaded['id']}/reprocess", headers=headers, json={"chunk_size": 100, "chunk_overlap": 0}
    )

    assert response.status_code == 202
    assert response.json()["status"] == "processing"
    detail = _detail(api_client, headers, uploaded["id"])
    assert detail["status"] == "ready"
    assert detail["chunk_count"] == 6
    assert detail["processing_config"]["chunk_size"] == 100
    assert [c.chunk_index for c in _chunks(db_session, uploaded["id"])] == list(range(6))


def test_reprocess_without_body_uses_defaults(api_client, make_authenticated_user):
    headers = make_authenticated_user()
    uploaded = _upload(api_client, headers, "a.txt", _words(600).encode())

    response = api_client.post(f"{DOCUMENTS}/{uploaded['id']}/reprocess", headers=headers)

    assert response.status_code == 202
    assert _detail(api_client, headers, uploaded["id"])["processing_config"]["chunk_size"] == 250


def test_reprocess_fixes_a_previously_failed_document(api_client, make_authenticated_user, test_embedder):
    test_embedder._fail_with = RuntimeError("lỗi tạm")
    headers = make_authenticated_user()
    uploaded = _upload(api_client, headers, "a.txt", "nội dung".encode())
    assert _detail(api_client, headers, uploaded["id"])["status"] == "failed"
    test_embedder._fail_with = None

    api_client.post(f"{DOCUMENTS}/{uploaded['id']}/reprocess", headers=headers)

    detail = _detail(api_client, headers, uploaded["id"])
    assert (detail["status"], detail["error_message"]) == ("ready", None)


def test_reprocess_while_processing_is_409(api_client, make_authenticated_user, db_session):
    headers = make_authenticated_user()
    uploaded = _upload(api_client, headers, "a.txt", "nội dung".encode())
    db_session.get(Document, uuid.UUID(uploaded["id"])).status = "processing"
    db_session.flush()

    response = api_client.post(f"{DOCUMENTS}/{uploaded['id']}/reprocess", headers=headers)

    assert response.status_code == 409


def test_reprocess_of_another_users_document_is_404(api_client, make_authenticated_user):
    owner, stranger = make_authenticated_user(), make_authenticated_user()
    uploaded = _upload(api_client, owner, "a.txt", "nội dung".encode())

    assert api_client.post(f"{DOCUMENTS}/{uploaded['id']}/reprocess", headers=stranger).status_code == 404


@pytest.mark.parametrize(
    "body",
    [{"chunk_size": 10}, {"chunk_size": 1000}, {"chunk_size": 100, "chunk_overlap": 100}, {"chunk_overlap": -1}],
)
def test_reprocess_rejects_invalid_chunking(api_client, make_authenticated_user, body):
    headers = make_authenticated_user()
    uploaded = _upload(api_client, headers, "a.txt", "nội dung".encode())

    response = api_client.post(f"{DOCUMENTS}/{uploaded['id']}/reprocess", headers=headers, json=body)

    assert response.status_code == 422


# ------------------------------------------------------------------------------------------- khởi động lại
def test_recovery_marks_unfinished_documents_as_failed_but_leaves_finished_ones(
    api_client, make_authenticated_user, db_session, ingestion_service
):
    headers = make_authenticated_user()
    finished = _upload(api_client, headers, "xong.txt", "đã xong".encode())
    stuck = _upload(api_client, headers, "ket.txt", "đang dở".encode())
    db_session.get(Document, uuid.UUID(stuck["id"])).status = "processing"
    db_session.flush()

    ingestion_service.recover_interrupted()

    assert _detail(api_client, headers, finished["id"])["status"] == "ready"
    stuck_detail = _detail(api_client, headers, stuck["id"])
    assert (stuck_detail["status"], stuck_detail["error_message"]) == ("failed", INTERRUPTED_MESSAGE)
