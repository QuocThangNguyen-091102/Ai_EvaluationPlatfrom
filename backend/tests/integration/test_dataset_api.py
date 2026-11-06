import json

import pytest

from app.core.config import settings

pytestmark = pytest.mark.integration

DOC_TEXT = (
    "Quy định nộp hồ sơ. Hồ sơ xin cấp giấy phép phải được nộp trong vòng 30 ngày kể từ ngày nhận thông báo. "
    "Phí và lệ phí: người nộp hồ sơ không phải đóng lệ phí trong năm đầu tiên."
)


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))


@pytest.fixture
def owner(api_client, make_authenticated_user):
    headers = make_authenticated_user()
    response = api_client.post(
        "/api/v1/documents", headers=headers, files={"file": ("quy-dinh.txt", DOC_TEXT.encode(), "text/plain")}
    )
    assert response.status_code == 202
    return headers


def _dataset(client, headers, name="Bộ câu hỏi quy định"):
    dataset = client.post("/api/v1/datasets", headers=headers, json={"name": name}).json()
    version = client.get(f"/api/v1/datasets/{dataset['id']}/versions", headers=headers).json()["items"][0]
    return dataset, version


ANSWER_CASE = {
    "question": "Hồ sơ xin giấy phép phải nộp trong bao lâu?",
    "ground_truth_answer": "Trong vòng 30 ngày kể từ ngày nhận thông báo.",
    "reference_contexts": [{"filename": "quy-dinh.txt", "quote": "phải được nộp trong vòng 30 ngày"}],
    "question_type": "fact",
    "difficulty": "easy",
    "expected_behavior": "answer",
}
UNANSWERABLE_CASE = {
    "question": "Lương giám đốc là bao nhiêu?",
    "question_type": "unanswerable",
    "difficulty": "medium",
    "expected_behavior": "insufficient_context",
}


def _add(client, headers, version_id, case):
    return client.post(f"/api/v1/dataset-versions/{version_id}/test-cases", headers=headers, json=case)


# ---------------------------------------------------------------------------------- dataset, version
def test_new_dataset_starts_with_an_empty_draft_version(api_client, owner):
    dataset, version = _dataset(api_client, owner)

    assert dataset["name"] == "Bộ câu hỏi quy định"
    assert (version["version_number"], version["status"], version["test_case_count"]) == (1, "draft", 0)


def test_dataset_names_are_unique_per_user(api_client, owner):
    _dataset(api_client, owner, "trung")

    assert api_client.post("/api/v1/datasets", headers=owner, json={"name": "trung"}).status_code == 409


# ---------------------------------------------------------------------------------- reference contexts
def test_reference_quote_is_located_and_stored_with_exact_offsets(api_client, owner):
    _, version = _dataset(api_client, owner)

    response = _add(api_client, owner, version["id"], ANSWER_CASE)

    assert response.status_code == 201
    reference = response.json()["reference_contexts"][0]
    assert reference["filename"] == "quy-dinh.txt"
    assert reference["text"] == "phải được nộp trong vòng 30 ngày"
    assert DOC_TEXT[reference["char_start"] : reference["char_end"]] == reference["text"]
    assert len(reference["document_content_hash"]) == 64


@pytest.mark.parametrize(
    "quote, fragment",
    [("câu này không có trong tài liệu", "Không tìm thấy"), ("nộp", "nhiều lần")],
)
def test_unverifiable_quotes_are_rejected(api_client, owner, quote, fragment):
    _, version = _dataset(api_client, owner)
    case = {**ANSWER_CASE, "reference_contexts": [{"filename": "quy-dinh.txt", "quote": quote}]}

    response = _add(api_client, owner, version["id"], case)

    assert response.status_code == 422
    assert fragment in response.json()["error"]["message"]


def test_reference_to_someone_elses_document_is_rejected(api_client, owner, make_authenticated_user):
    stranger = make_authenticated_user()
    _, version = _dataset(api_client, stranger)

    response = _add(api_client, stranger, version["id"], ANSWER_CASE)

    assert response.status_code == 422
    assert "Không có tài liệu" in response.json()["error"]["message"]


@pytest.mark.parametrize(
    "change",
    [
        {"ground_truth_answer": None},
        {"reference_contexts": []},
        {"question_type": "unanswerable"},
    ],
)
def test_inconsistent_cases_are_rejected(api_client, owner, change):
    _, version = _dataset(api_client, owner)

    assert _add(api_client, owner, version["id"], {**ANSWER_CASE, **change}).status_code == 422


def test_unanswerable_case_needs_no_reference(api_client, owner):
    _, version = _dataset(api_client, owner)

    assert _add(api_client, owner, version["id"], UNANSWERABLE_CASE).status_code == 201


# ---------------------------------------------------------------------------------- import
def _import(client, headers, version_id, filename, content: bytes):
    return client.post(
        f"/api/v1/dataset-versions/{version_id}/test-cases/import", headers=headers, files={"file": (filename, content, "application/octet-stream")}
    )


def _count(client, headers, version_id):
    return client.get(f"/api/v1/dataset-versions/{version_id}/test-cases", headers=headers).json()["total"]


def test_import_json_writes_all_valid_cases(api_client, owner):
    _, version = _dataset(api_client, owner)
    content = json.dumps([ANSWER_CASE, UNANSWERABLE_CASE], ensure_ascii=False).encode()

    response = _import(api_client, owner, version["id"], "cases.json", content)

    assert response.json() == {"imported": 2}
    assert _count(api_client, owner, version["id"]) == 2


def test_import_with_any_bad_row_writes_nothing_and_reports_rows(api_client, owner):
    _, version = _dataset(api_client, owner)
    bad_quote = {**ANSWER_CASE, "reference_contexts": [{"filename": "quy-dinh.txt", "quote": "không có trong tài liệu"}]}
    content = json.dumps([ANSWER_CASE, bad_quote, {**UNANSWERABLE_CASE, "difficulty": "x"}], ensure_ascii=False).encode()

    response = _import(api_client, owner, version["id"], "cases.json", content)

    assert response.status_code == 422
    rows = {item["row"] for item in response.json()["error"]["details"]}
    assert rows == {2, 3}
    assert _count(api_client, owner, version["id"]) == 0


def test_import_csv(api_client, owner):
    _, version = _dataset(api_client, owner)
    csv_text = (
        "question,ground_truth_answer,question_type,difficulty,expected_behavior,source_note,reference_documents,reference_quotes\n"
        "Năm đầu có thu lệ phí không?,Không,fact,easy,answer,,quy-dinh.txt,không phải đóng lệ phí trong năm đầu tiên\n"
    )

    assert _import(api_client, owner, version["id"], "cases.csv", csv_text.encode()).json() == {"imported": 1}


# ---------------------------------------------------------------------------------- duyệt, bất biến, version mới
def test_empty_version_cannot_be_reviewed(api_client, owner):
    _, version = _dataset(api_client, owner)

    assert api_client.post(f"/api/v1/dataset-versions/{version['id']}/review", headers=owner).status_code == 422


def test_reviewed_version_is_frozen(api_client, owner):
    _, version = _dataset(api_client, owner)
    case_id = _add(api_client, owner, version["id"], ANSWER_CASE).json()["id"]

    reviewed = api_client.post(f"/api/v1/dataset-versions/{version['id']}/review", headers=owner).json()
    assert (reviewed["status"], reviewed["test_case_count"]) == ("reviewed", 1)
    assert reviewed["reviewed_at"] is not None

    assert api_client.post(f"/api/v1/dataset-versions/{version['id']}/review", headers=owner).status_code == 409
    assert _add(api_client, owner, version["id"], UNANSWERABLE_CASE).status_code == 409
    assert api_client.put(f"/api/v1/test-cases/{case_id}", headers=owner, json=UNANSWERABLE_CASE).status_code == 409
    assert api_client.delete(f"/api/v1/test-cases/{case_id}", headers=owner).status_code == 409
    imported = _import(api_client, owner, version["id"], "a.json", json.dumps([UNANSWERABLE_CASE]).encode())
    assert imported.status_code == 409
    assert _count(api_client, owner, version["id"]) == 1


def test_new_version_copied_from_a_reviewed_one_is_editable_and_leaves_the_original_untouched(api_client, owner):
    dataset, v1 = _dataset(api_client, owner)
    _add(api_client, owner, v1["id"], ANSWER_CASE)
    api_client.post(f"/api/v1/dataset-versions/{v1['id']}/review", headers=owner)

    v2 = api_client.post(f"/api/v1/datasets/{dataset['id']}/versions", headers=owner, json={"copy_from_version_id": v1["id"]}).json()

    assert (v2["version_number"], v2["status"], v2["test_case_count"]) == (2, "draft", 1)
    assert _add(api_client, owner, v2["id"], UNANSWERABLE_CASE).status_code == 201
    assert _count(api_client, owner, v2["id"]) == 2
    assert _count(api_client, owner, v1["id"]) == 1
    versions = api_client.get(f"/api/v1/datasets/{dataset['id']}/versions", headers=owner).json()["items"]
    assert [v["version_number"] for v in versions] == [2, 1]


# ---------------------------------------------------------------------------------- sửa, xóa, lọc
def test_update_and_delete_a_case_in_a_draft(api_client, owner):
    _, version = _dataset(api_client, owner)
    case_id = _add(api_client, owner, version["id"], ANSWER_CASE).json()["id"]

    updated = api_client.put(f"/api/v1/test-cases/{case_id}", headers=owner, json={**ANSWER_CASE, "difficulty": "hard"})
    assert updated.json()["difficulty"] == "hard"
    assert api_client.delete(f"/api/v1/test-cases/{case_id}", headers=owner).status_code == 204
    assert _count(api_client, owner, version["id"]) == 0


def test_cases_can_be_filtered_by_type_and_difficulty(api_client, owner):
    _, version = _dataset(api_client, owner)
    _add(api_client, owner, version["id"], ANSWER_CASE)
    _add(api_client, owner, version["id"], UNANSWERABLE_CASE)

    by_type = api_client.get(f"/api/v1/dataset-versions/{version['id']}/test-cases", headers=owner, params={"question_type": "unanswerable"}).json()
    by_difficulty = api_client.get(f"/api/v1/dataset-versions/{version['id']}/test-cases", headers=owner, params={"difficulty": "easy"}).json()

    assert [c["question_type"] for c in by_type["items"]] == ["unanswerable"]
    assert [c["difficulty"] for c in by_difficulty["items"]] == ["easy"]


# ---------------------------------------------------------------------------------- cô lập
def test_datasets_are_private(api_client, owner, make_authenticated_user):
    stranger = make_authenticated_user()
    dataset, version = _dataset(api_client, owner)
    case_id = _add(api_client, owner, version["id"], ANSWER_CASE).json()["id"]

    assert api_client.get(f"/api/v1/datasets/{dataset['id']}", headers=stranger).status_code == 404
    assert api_client.get(f"/api/v1/datasets/{dataset['id']}/versions", headers=stranger).status_code == 404
    assert api_client.get(f"/api/v1/dataset-versions/{version['id']}/test-cases", headers=stranger).status_code == 404
    assert _add(api_client, stranger, version["id"], UNANSWERABLE_CASE).status_code == 404
    assert api_client.put(f"/api/v1/test-cases/{case_id}", headers=stranger, json=UNANSWERABLE_CASE).status_code == 404
    assert api_client.post(f"/api/v1/dataset-versions/{version['id']}/review", headers=stranger).status_code == 404
    assert api_client.get("/api/v1/datasets", headers=stranger).json()["total"] == 0
