import csv
import io

import pytest

from app.core.config import settings

pytestmark = pytest.mark.integration

DOC_TEXT = (
    "Quy định nộp hồ sơ. Hồ sơ xin cấp giấy phép phải được nộp trong vòng 30 ngày kể từ ngày nhận thông báo. "
    "Phí và lệ phí: người nộp hồ sơ không phải đóng lệ phí trong năm đầu tiên."
)
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


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))


@pytest.fixture
def llm_server(monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url", "https://llm.example/v1")
    monkeypatch.setattr(settings, "llm_model", "model-a")
    monkeypatch.setattr(settings, "llm_provider_name", "test")


@pytest.fixture
def owner(api_client, make_authenticated_user):
    headers = make_authenticated_user()
    response = api_client.post(
        "/api/v1/documents", headers=headers, files={"file": ("quy-dinh.txt", DOC_TEXT.encode(), "text/plain")}
    )
    assert response.status_code == 202
    return headers


def _version(client, headers, cases=(ANSWER_CASE, UNANSWERABLE_CASE), *, review=True):
    dataset = client.post("/api/v1/datasets", headers=headers, json={"name": "Bộ đánh giá"}).json()
    version = client.get(f"/api/v1/datasets/{dataset['id']}/versions", headers=headers).json()["items"][0]
    for case in cases:
        assert client.post(f"/api/v1/dataset-versions/{version['id']}/test-cases", headers=headers, json=case).status_code == 201
    if review:
        assert client.post(f"/api/v1/dataset-versions/{version['id']}/review", headers=headers).status_code == 200
    return version


def _metric(items, name):
    return next(m for m in items if m["metric_name"] == name)


def test_draft_version_cannot_be_evaluated(api_client, owner):
    version = _version(api_client, owner, review=False)

    response = api_client.post("/api/v1/evaluations", headers=owner, json={"dataset_version_id": version["id"]})

    assert response.status_code == 409


def test_judge_requires_a_configured_llm(api_client, owner):
    version = _version(api_client, owner)

    response = api_client.post(
        "/api/v1/evaluations", headers=owner, json={"dataset_version_id": version["id"], "judge_model": "judge-a"}
    )

    assert response.status_code == 422


def test_extractive_run_scores_retrieval_but_has_no_generation_metrics(api_client, owner):
    version = _version(api_client, owner)

    created = api_client.post("/api/v1/evaluations", headers=owner, json={"dataset_version_id": version["id"]})

    assert created.status_code == 202
    run = api_client.get(f"/api/v1/evaluations/{created.json()['id']}", headers=owner).json()
    assert run["status"] == "completed"
    assert (run["total_cases"], run["completed_cases"], run["failed_cases"]) == (2, 2, 0)
    assert run["environment"]["model_configuration"]["llm_provider"] == "extractive"
    assert run["environment"]["dataset_version"]["cases"] == 2
    aggregates = run["aggregate_metrics"]
    assert _metric(aggregates, "recall_at_k")["value"] == 1.0
    assert _metric(aggregates, "mrr")["value"] == 1.0
    # Extractive không có câu trả lời do LLM viết, nên không có gì để judge chấm.
    assert all(m["metric_name"] not in ("faithfulness", "answer_relevancy") for m in aggregates)

    results = api_client.get(f"/api/v1/evaluations/{run['id']}/results", headers=owner).json()
    assert results["total"] == 2
    answered = next(r for r in results["items"] if r["expected_behavior"] == "answer")
    assert answered["contexts"][0]["relevant"] is True
    assert _metric(answered["metrics"], "precision_at_k")["k"] == 5


def test_llm_run_uses_judge_and_exports_csv(api_client, owner, llm_server):
    version = _version(api_client, owner)
    config = api_client.post(
        "/api/v1/model-configurations", headers=owner, json={"name": "llm", "llm_provider": "test", "llm_model": "model-a"}
    )
    assert config.status_code == 201

    created = api_client.post(
        "/api/v1/evaluations",
        headers=owner,
        json={"dataset_version_id": version["id"], "model_configuration_id": config.json()["id"], "judge_model": "judge-a"},
    ).json()

    run = api_client.get(f"/api/v1/evaluations/{created['id']}", headers=owner).json()
    assert run["status"] == "completed"
    assert run["judge_prompt_version"] == "judge-strict-json"
    assert _metric(run["aggregate_metrics"], "faithfulness")["status"] == "computed"

    report = api_client.get(f"/api/v1/evaluations/{run['id']}/report?format=csv", headers=owner)
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("text/csv")
    text = report.content.decode("utf-8-sig")
    assert "judge-a" in text
    rows = list(csv.reader(io.StringIO(text)))
    header = next(row for row in rows if row and row[0] == "test_case_id")
    assert "faithfulness" in header and "recall_at_k" in header


def test_llm_run_without_judge_reports_judge_metrics_as_skipped(api_client, owner, llm_server):
    version = _version(api_client, owner, cases=(ANSWER_CASE,))
    config = api_client.post(
        "/api/v1/model-configurations", headers=owner, json={"name": "llm", "llm_provider": "test", "llm_model": "model-a"}
    ).json()

    created = api_client.post(
        "/api/v1/evaluations", headers=owner, json={"dataset_version_id": version["id"], "model_configuration_id": config["id"]}
    ).json()

    run = api_client.get(f"/api/v1/evaluations/{created['id']}", headers=owner).json()
    faithfulness = _metric(run["aggregate_metrics"], "faithfulness")
    assert (faithfulness["status"], faithfulness["value"]) == ("skipped", None)


def test_failed_case_is_recorded_without_stopping_the_run(api_client, owner, llm_server, scripted_llm):
    from ai_engine.generation.base_llm_client import LlmError

    version = _version(api_client, owner, cases=(ANSWER_CASE,))
    config = api_client.post(
        "/api/v1/model-configurations", headers=owner, json={"name": "llm", "llm_provider": "test", "llm_model": "model-a"}
    ).json()
    scripted_llm._respond = lambda messages: LlmError("provider down")

    created = api_client.post(
        "/api/v1/evaluations", headers=owner, json={"dataset_version_id": version["id"], "model_configuration_id": config["id"]}
    ).json()

    run = api_client.get(f"/api/v1/evaluations/{created['id']}", headers=owner).json()
    assert run["status"] == "completed"
    assert run["failed_cases"] == 1
    result = api_client.get(f"/api/v1/evaluations/{run['id']}/results?status=error", headers=owner).json()["items"][0]
    assert result["category"] == "error"
    assert result["error_message"]


def test_runs_are_private_to_their_owner(api_client, owner, make_authenticated_user):
    version = _version(api_client, owner)
    run = api_client.post("/api/v1/evaluations", headers=owner, json={"dataset_version_id": version["id"]}).json()
    stranger = make_authenticated_user()

    assert api_client.get(f"/api/v1/evaluations/{run['id']}", headers=stranger).status_code == 404
    assert api_client.get(f"/api/v1/evaluations/{run['id']}/results", headers=stranger).status_code == 404
    assert api_client.get("/api/v1/evaluations", headers=stranger).json()["total"] == 0
    assert api_client.post("/api/v1/evaluations", headers=stranger, json={"dataset_version_id": version["id"]}).status_code == 404


def test_report_requires_a_completed_run(api_client, owner, db_session):
    from app.models.evaluation import EvaluationRun

    version = _version(api_client, owner)
    run_id = api_client.post("/api/v1/evaluations", headers=owner, json={"dataset_version_id": version["id"]}).json()["id"]
    db_session.get(EvaluationRun, run_id).status = "running"
    db_session.flush()

    assert api_client.get(f"/api/v1/evaluations/{run_id}/report", headers=owner).status_code == 409


def test_startup_recovery_fails_unfinished_runs(api_client, owner, db_session, evaluation_run_service):
    from app.models.evaluation import EvaluationRun

    version = _version(api_client, owner)
    run_id = api_client.post("/api/v1/evaluations", headers=owner, json={"dataset_version_id": version["id"]}).json()["id"]
    db_session.get(EvaluationRun, run_id).status = "running"
    db_session.flush()

    assert evaluation_run_service.recover_interrupted() == 1
    run = api_client.get(f"/api/v1/evaluations/{run_id}", headers=owner).json()
    assert run["status"] == "failed"
    assert run["error_message"]
