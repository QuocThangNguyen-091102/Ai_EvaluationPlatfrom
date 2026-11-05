import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.models import Document, DocumentChunk
from app.models.document_chunk import EMBEDDING_DIMENSIONS

pytestmark = pytest.mark.integration

DOCUMENTS = "/api/v1/documents"


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    return tmp_path


def _upload(client, headers, name="tai-lieu.txt", text=None) -> dict:
    content = (text or f"Nội dung {uuid.uuid4()}").encode()
    response = client.post(DOCUMENTS, headers=headers, files={"file": (name, content, "text/plain")})
    assert response.status_code == 202, response.text
    return response.json()


def _created_minutes_ago(db_session, document_id: str, minutes: int) -> None:
    """Trong test mọi bản ghi chung một transaction nên now() giống hệt nhau; đặt giờ tạo rõ ràng để thứ tự có nghĩa."""
    db_session.get(Document, uuid.UUID(document_id)).created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    db_session.flush()


def _add_chunks(db_session, document_id: str, count: int) -> None:
    document = db_session.get(Document, uuid.UUID(document_id))
    for index in range(count):
        db_session.add(
            DocumentChunk(
                document_id=document.id,
                user_id=document.user_id,
                chunk_index=index,
                content=f"chunk {index}",
                page_number=None,
                char_start=0,
                char_end=7,
                embedding=[0.1] * EMBEDDING_DIMENSIONS,
                embedding_model="test-model",
            )
        )
    db_session.flush()


# ------------------------------------------------------------------------------------------------ list
def test_list_returns_only_my_documents_newest_first(api_client, make_authenticated_user, db_session):
    me = make_authenticated_user()
    other = make_authenticated_user()
    first = _upload(api_client, me, "cu.txt")
    second = _upload(api_client, me, "moi.txt")
    _upload(api_client, other, "cua-nguoi-khac.txt")
    _created_minutes_ago(db_session, first["id"], 10)
    _created_minutes_ago(db_session, second["id"], 1)

    response = api_client.get(DOCUMENTS, headers=me)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [item["id"] for item in body["items"]] == [second["id"], first["id"]]
    assert {"limit": body["limit"], "offset": body["offset"]} == {"limit": 20, "offset": 0}


def test_list_is_empty_for_a_new_user(api_client, make_authenticated_user):
    response = api_client.get(DOCUMENTS, headers=make_authenticated_user())

    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_list_paginates(api_client, make_authenticated_user, db_session):
    headers = make_authenticated_user()
    ids = [_upload(api_client, headers)["id"] for _ in range(5)]
    for age, document_id in enumerate(ids):  # ids[0] cũ nhất ... ids[4] mới nhất
        _created_minutes_ago(db_session, document_id, 50 - age)
    newest_first = ids[::-1]

    page = api_client.get(DOCUMENTS, headers=headers, params={"limit": 2, "offset": 2}).json()

    assert page["total"] == 5
    assert [item["id"] for item in page["items"]] == newest_first[2:4]


def test_list_filters_by_status(api_client, make_authenticated_user, db_session):
    headers = make_authenticated_user()
    ready = _upload(api_client, headers)
    _upload(api_client, headers)
    db_session.get(Document, uuid.UUID(ready["id"])).status = "ready"
    db_session.flush()

    body = api_client.get(DOCUMENTS, headers=headers, params={"status": "ready"}).json()

    assert body["total"] == 1
    assert body["items"][0]["id"] == ready["id"]


@pytest.mark.parametrize("params", [{"status": "bogus"}, {"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_list_rejects_invalid_parameters(api_client, make_authenticated_user, params):
    response = api_client.get(DOCUMENTS, headers=make_authenticated_user(), params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_list_reports_the_real_chunk_count(api_client, make_authenticated_user, db_session):
    headers = make_authenticated_user()
    with_chunks = _upload(api_client, headers)
    without_chunks = _upload(api_client, headers)
    _add_chunks(db_session, with_chunks["id"], 3)

    items = {item["id"]: item for item in api_client.get(DOCUMENTS, headers=headers).json()["items"]}

    assert items[with_chunks["id"]]["chunk_count"] == 3
    assert items[without_chunks["id"]]["chunk_count"] == 0


def test_list_requires_authentication(api_client):
    assert api_client.get(DOCUMENTS).status_code == 401


# ---------------------------------------------------------------------------------------------- detail
def test_detail_returns_my_document_with_chunk_count(api_client, make_authenticated_user, db_session):
    headers = make_authenticated_user()
    document = _upload(api_client, headers, "ghi-chu.txt")
    _add_chunks(db_session, document["id"], 2)

    response = api_client.get(f"{DOCUMENTS}/{document['id']}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "ghi-chu.txt"
    assert body["chunk_count"] == 2


def test_detail_of_another_users_document_is_404_not_403(api_client, make_authenticated_user):
    owner = make_authenticated_user()
    stranger = make_authenticated_user()
    document = _upload(api_client, owner)

    response = api_client.get(f"{DOCUMENTS}/{document['id']}", headers=stranger)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_detail_of_unknown_id_is_404_and_same_as_foreign_document(api_client, make_authenticated_user):
    owner = make_authenticated_user()
    stranger = make_authenticated_user()
    foreign = api_client.get(f"{DOCUMENTS}/{_upload(api_client, owner)['id']}", headers=stranger)

    unknown = api_client.get(f"{DOCUMENTS}/{uuid.uuid4()}", headers=stranger)

    assert unknown.status_code == foreign.status_code == 404
    assert unknown.json() == foreign.json()


def test_detail_with_malformed_id_is_422(api_client, make_authenticated_user):
    response = api_client.get(f"{DOCUMENTS}/khong-phai-uuid", headers=make_authenticated_user())

    assert response.status_code == 422


# ---------------------------------------------------------------------------------------------- delete
def test_delete_removes_record_chunks_and_file(api_client, make_authenticated_user, db_session, isolated_upload_dir):
    headers = make_authenticated_user()
    document = _upload(api_client, headers)
    _add_chunks(db_session, document["id"], 2)
    assert len([p for p in isolated_upload_dir.rglob("*") if p.is_file()]) == 1

    response = api_client.delete(f"{DOCUMENTS}/{document['id']}", headers=headers)

    assert response.status_code == 204
    assert api_client.get(f"{DOCUMENTS}/{document['id']}", headers=headers).status_code == 404
    chunks = db_session.scalar(
        select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == uuid.UUID(document["id"]))
    )
    assert chunks == 0
    assert [p for p in isolated_upload_dir.rglob("*") if p.is_file()] == []


def test_delete_of_another_users_document_is_404_and_changes_nothing(
    api_client, make_authenticated_user, isolated_upload_dir
):
    owner = make_authenticated_user()
    stranger = make_authenticated_user()
    document = _upload(api_client, owner)

    response = api_client.delete(f"{DOCUMENTS}/{document['id']}", headers=stranger)

    assert response.status_code == 404
    assert api_client.get(f"{DOCUMENTS}/{document['id']}", headers=owner).status_code == 200
    assert len([p for p in isolated_upload_dir.rglob("*") if p.is_file()]) == 1


def test_delete_succeeds_even_if_the_file_is_already_gone(api_client, make_authenticated_user, isolated_upload_dir):
    headers = make_authenticated_user()
    document = _upload(api_client, headers)
    for stored in isolated_upload_dir.rglob("*"):
        if stored.is_file():
            stored.unlink()

    assert api_client.delete(f"{DOCUMENTS}/{document['id']}", headers=headers).status_code == 204


def test_deleting_twice_returns_404_the_second_time(api_client, make_authenticated_user):
    headers = make_authenticated_user()
    document = _upload(api_client, headers)
    api_client.delete(f"{DOCUMENTS}/{document['id']}", headers=headers)

    assert api_client.delete(f"{DOCUMENTS}/{document['id']}", headers=headers).status_code == 404


def test_same_content_can_be_uploaded_again_after_deletion(api_client, make_authenticated_user):
    headers = make_authenticated_user()
    first = _upload(api_client, headers, text="nội dung cố định để kiểm tra upload lại")
    api_client.delete(f"{DOCUMENTS}/{first['id']}", headers=headers)

    second = api_client.post(
        DOCUMENTS, headers=headers, files={"file": ("lai.txt", "nội dung cố định để kiểm tra upload lại".encode(), "text/plain")}
    )

    assert second.status_code == 202


def test_delete_requires_authentication(api_client):
    assert api_client.delete(f"{DOCUMENTS}/{uuid.uuid4()}").status_code == 401
