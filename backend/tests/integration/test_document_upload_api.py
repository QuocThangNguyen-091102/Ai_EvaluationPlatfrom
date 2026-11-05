import io
import uuid
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core import file_storage
from app.core.config import settings
from app.models import Document

pytestmark = pytest.mark.integration

UPLOAD = "/api/v1/documents"


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path, monkeypatch) -> Path:
    """Mỗi test ghi file vào thư mục tạm riêng, pytest tự dọn."""
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    return tmp_path


def _pdf(tag: str = "") -> bytes:
    return b"%PDF-1.7\n" + tag.encode() + uuid.uuid4().bytes


def _docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", f"<document>{uuid.uuid4()}</document>")
    return buffer.getvalue()


def _upload(client, headers, content: bytes, filename: str, content_type: str = "application/octet-stream"):
    return client.post(UPLOAD, headers=headers, files={"file": (filename, content, content_type)})


def _document_count(db_session) -> int:
    return db_session.scalar(select(func.count()).select_from(Document))


def test_upload_pdf_returns_202_and_stores_metadata_and_file(api_client, make_authenticated_user, isolated_upload_dir):
    headers = make_authenticated_user()
    content = _pdf()

    response = _upload(api_client, headers, content, "báo cáo.pdf")

    assert response.status_code == 202
    body = response.json()
    assert body["filename"] == "báo cáo.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == len(content)
    assert body["status"] == "uploaded"
    assert body["chunk_count"] == 0
    assert body["error_message"] is None
    stored = list(isolated_upload_dir.rglob("*.pdf"))
    assert len(stored) == 1
    assert stored[0].read_bytes() == content


def test_stored_file_name_is_generated_by_the_server_not_taken_from_the_client(
    api_client, make_authenticated_user, isolated_upload_dir
):
    headers = make_authenticated_user()

    response = _upload(api_client, headers, _pdf(), "../../etc/passwd.pdf")

    assert response.status_code == 202
    assert response.json()["filename"] == "passwd.pdf"
    stored = [p for p in isolated_upload_dir.rglob("*") if p.is_file()]
    assert len(stored) == 1
    assert stored[0].name != "passwd.pdf"
    assert isolated_upload_dir in stored[0].parents


def test_upload_docx_and_txt_are_accepted(api_client, make_authenticated_user):
    headers = make_authenticated_user()

    docx = _upload(api_client, headers, _docx(), "mau.docx")
    txt = _upload(api_client, headers, "Nội dung văn bản tiếng Việt".encode(), "ghi-chu.txt")

    assert docx.status_code == txt.status_code == 202
    assert txt.json()["content_type"] == "text/plain"


def test_upload_does_not_trust_the_content_type_sent_by_the_client(api_client, make_authenticated_user):
    headers = make_authenticated_user()

    response = _upload(api_client, headers, _pdf(), "file.pdf", content_type="text/html")

    assert response.status_code == 202
    assert response.json()["content_type"] == "application/pdf"


@pytest.mark.parametrize("filename", ["virus.exe", "cu.doc", "bang.xlsx", "khongduoi"])
def test_unsupported_extension_is_rejected_with_415(api_client, make_authenticated_user, db_session, filename):
    headers = make_authenticated_user()
    before = _document_count(db_session)

    response = _upload(api_client, headers, _pdf(), filename)

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"
    assert _document_count(db_session) == before


def test_pdf_extension_with_other_content_is_rejected(api_client, make_authenticated_user):
    headers = make_authenticated_user()

    response = _upload(api_client, headers, b"MZ\x90\x00 executable", "fake.pdf")

    assert response.status_code == 415


def test_file_over_the_size_limit_is_rejected_with_413_and_nothing_is_stored(
    api_client, make_authenticated_user, db_session, isolated_upload_dir, monkeypatch
):
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)
    headers = make_authenticated_user()
    too_big = b"%PDF-1.7\n" + b"x" * (1024 * 1024)
    before = _document_count(db_session)

    response = _upload(api_client, headers, too_big, "lon.pdf")

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"
    assert "1 MB" in response.json()["error"]["message"]
    assert _document_count(db_session) == before
    assert [p for p in isolated_upload_dir.rglob("*") if p.is_file()] == []


def test_file_exactly_at_the_limit_is_accepted(api_client, make_authenticated_user, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)
    headers = make_authenticated_user()
    exactly = b"%PDF-1.7\n" + b"x" * (1024 * 1024 - len(b"%PDF-1.7\n"))

    response = _upload(api_client, headers, exactly, "vua-du.pdf")

    assert response.status_code == 202


def test_empty_file_is_rejected_with_422(api_client, make_authenticated_user):
    headers = make_authenticated_user()

    response = _upload(api_client, headers, b"", "rong.txt")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_missing_file_field_is_rejected_with_422(api_client, make_authenticated_user):
    headers = make_authenticated_user()

    response = api_client.post(UPLOAD, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_uploading_the_same_content_twice_returns_409_with_the_existing_id(
    api_client, make_authenticated_user, db_session, isolated_upload_dir
):
    headers = make_authenticated_user()
    content = _pdf()
    first = _upload(api_client, headers, content, "ban-dau.pdf")

    second = _upload(api_client, headers, content, "doi-ten.pdf")

    assert second.status_code == 409
    error = second.json()["error"]
    assert error["code"] == "conflict"
    assert error["details"]["existing_document_id"] == first.json()["id"]
    assert len([p for p in isolated_upload_dir.rglob("*") if p.is_file()]) == 1


def test_different_users_may_upload_the_same_content_and_keep_separate_copies(
    api_client, make_authenticated_user, isolated_upload_dir
):
    content = _pdf()
    first_user = make_authenticated_user()
    second_user = make_authenticated_user()

    first = _upload(api_client, first_user, content, "a.pdf")
    second = _upload(api_client, second_user, content, "a.pdf")

    assert first.status_code == second.status_code == 202
    assert first.json()["id"] != second.json()["id"]
    assert len([p for p in isolated_upload_dir.rglob("*.pdf")]) == 2


def test_upload_requires_authentication(api_client, db_session):
    before = _document_count(db_session)

    response = api_client.post(UPLOAD, files={"file": ("a.pdf", _pdf(), "application/pdf")})

    assert response.status_code == 401
    assert _document_count(db_session) == before


def test_failed_file_write_leaves_no_database_row(
    api_client, make_authenticated_user, db_session, isolated_upload_dir, monkeypatch
):
    headers = make_authenticated_user()
    before = _document_count(db_session)

    def broken_save(*_args, **_kwargs):
        raise OSError("đĩa đầy")

    monkeypatch.setattr("app.services.document_service.save_file", broken_save)

    response = _upload(api_client, headers, _pdf(), "that-bai.pdf")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "đĩa đầy" not in response.text
    assert _document_count(db_session) == before


def test_storage_refuses_paths_outside_the_upload_directory(isolated_upload_dir):
    with pytest.raises(ValueError):
        file_storage.save_file("../ngoai-thu-muc.txt", b"x")
