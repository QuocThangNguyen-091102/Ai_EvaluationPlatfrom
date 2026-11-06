import csv
import io
from decimal import Decimal

import pytest

from app.core.config import settings

pytestmark = pytest.mark.integration

DOC_TEXT = (
    "Quy định nộp hồ sơ. Hồ sơ xin cấp giấy phép phải được nộp trong vòng 30 ngày kể từ ngày nhận thông báo. "
    "Phí và lệ phí: người nộp hồ sơ không phải đóng lệ phí trong năm đầu tiên."
)
CASE = {
    "question": "Hồ sơ xin giấy phép phải nộp trong bao lâu?",
    "ground_truth_answer": "Trong vòng 30 ngày kể từ ngày nhận thông báo.",
    "reference_contexts": [{"filename": "quy-dinh.txt", "quote": "phải được nộp trong vòng 30 ngày"}],
    "question_type": "fact",
    "difficulty": "easy",
    "expected_behavior": "answer",
}
CONFIGS = "/api/v1/model-configurations"


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))


@pytest.fixture
def owner(api_client, make_authenticated_user):
    headers = make_authenticated_user()
    response = api_client.post("/api/v1/documents", headers=headers, files={"file": ("quy-dinh.txt", DOC_TEXT.encode(), "text/plain")})
    assert response.status_code == 202
    return headers


def _version(client, headers, review=True):
    dataset = client.post("/api/v1/datasets", headers=headers, json={"name": "Bộ benchmark"}).json()
    version = client.get(f"/api/v1/datasets/{dataset['id']}/versions", headers=headers).json()["items"][0]
    assert client.post(f"/api/v1/dataset-versions/{version['id']}/test-cases", headers=headers, json=CASE).status_code == 201
    if review:
        client.post(f"/api/v1/dataset-versions/{version['id']}/review", headers=headers)
    return version["id"]


def _config(client, headers, name, **extra):
    body = {"name": name, "llm_provider": "extractive", "llm_model": "top-passages", **extra}
    response = client.post(CONFIGS, headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create(client, headers, version_id, config_ids, variable="top_k"):
    return client.post(
        "/api/v1/benchmarks",
        headers=headers,
        json={"name": "top_k 1 và 5", "dataset_version_id": version_id, "varied_variable": variable, "model_configuration_ids": config_ids},
    )


def test_benchmark_runs_one_evaluation_per_config_and_compares(api_client, owner):
    version_id = _version(api_client, owner)
    configs = [_config(api_client, owner, "k1", top_k=1), _config(api_client, owner, "k5", top_k=5)]

    created = _create(api_client, owner, version_id, configs)

    assert created.status_code == 202
    detail = api_client.get(f"/api/v1/benchmarks/{created.json()['id']}", headers=owner).json()
    assert detail["status"] == "completed"
    assert [v["varied_value"] for v in detail["variants"]] == [1, 5]
    for variant in detail["variants"]:
        assert variant["status"] == "completed"
        assert any(m["metric_name"] == "recall_at_k" for m in variant["aggregate_metrics"])
        assert variant["usage"]["cases"] == 1 and variant["usage"]["latency_p50_ms"] is not None
        assert Decimal(variant["usage"]["total_cost"]) == 0
    assert detail["notes"] == []

    # Lượt con là lượt đánh giá bình thường: thấy được ở trang Đánh giá.
    assert api_client.get("/api/v1/evaluations", headers=owner).json()["total"] == 2

    report = api_client.get(f"/api/v1/benchmarks/{detail['id']}/report?format=csv", headers=owner)
    rows = list(csv.reader(io.StringIO(report.content.decode("utf-8-sig"))))
    header_index = next(i for i, row in enumerate(rows) if row and row[0] == "top_k")
    assert [row[0] for row in rows[header_index + 1 :] if row] == ["1", "5"]
    assert "latency_p95_ms" in rows[header_index]


def test_configs_must_differ_on_the_declared_variable(api_client, owner):
    version_id = _version(api_client, owner)
    configs = [_config(api_client, owner, "a", top_k=5), _config(api_client, owner, "b", top_k=5, temperature=0.5)]

    response = _create(api_client, owner, version_id, configs)

    assert response.status_code == 422
    assert api_client.get("/api/v1/benchmarks", headers=owner).json()["total"] == 0


def test_extra_differences_are_recorded_as_notes(api_client, owner):
    version_id = _version(api_client, owner)
    configs = [_config(api_client, owner, "a", top_k=3), _config(api_client, owner, "b", top_k=5, temperature=0.5)]

    detail = _create(api_client, owner, version_id, configs).json()

    assert "temperature" in detail["notes"][0]


def test_draft_version_rejected_and_nothing_left_behind(api_client, owner):
    version_id = _version(api_client, owner, review=False)
    configs = [_config(api_client, owner, "a", top_k=3), _config(api_client, owner, "b", top_k=5)]

    assert _create(api_client, owner, version_id, configs).status_code == 409
    assert api_client.get("/api/v1/benchmarks", headers=owner).json()["total"] == 0
    assert api_client.get("/api/v1/evaluations", headers=owner).json()["total"] == 0


def test_validation_of_request(api_client, owner):
    version_id = _version(api_client, owner)
    config = _config(api_client, owner, "a")

    assert _create(api_client, owner, version_id, [config]).status_code == 422
    assert _create(api_client, owner, version_id, [config, config]).status_code == 422
    assert _create(api_client, owner, version_id, [config, config], variable="temperature").status_code == 422


def test_benchmarks_are_private(api_client, owner, make_authenticated_user):
    version_id = _version(api_client, owner)
    configs = [_config(api_client, owner, "k1", top_k=1), _config(api_client, owner, "k5", top_k=5)]
    benchmark_id = _create(api_client, owner, version_id, configs).json()["id"]
    stranger = make_authenticated_user()

    assert api_client.get(f"/api/v1/benchmarks/{benchmark_id}", headers=stranger).status_code == 404
    assert api_client.get(f"/api/v1/benchmarks/{benchmark_id}/report", headers=stranger).status_code == 404
    # Người lạ không dùng được cấu hình của người khác.
    assert _create(api_client, stranger, version_id, configs).status_code == 404
