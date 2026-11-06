import csv
import io
from contextlib import nullcontext
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select, text

from ai_engine.generation.prompt_templates import INSUFFICIENT_CONTEXT_ANSWER
from ai_engine.pipeline.rag_result import RagResult
from app.api.dependencies import get_security_run_service
from app.core.config import settings
from app.main import app
from app.models.document import Document
from app.models.security_test import SecurityTestRun
from app.models.user import SANDBOX_EMAIL_DOMAIN, User
from app.services.security_service import SecurityRunService
from security.test_case_loader import CATEGORIES
from tests.conftest import TEST_SECRETS

pytestmark = pytest.mark.integration

RUNS = "/api/v1/security/runs"
OWN_TEXT = "Tài liệu riêng của người dùng thật. Quy định nộp hồ sơ trong vòng 30 ngày."


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
    response = api_client.post("/api/v1/documents", headers=headers, files={"file": ("rieng.txt", OWN_TEXT.encode(), "text/plain")})
    assert response.status_code == 202
    return headers


def _results(client, headers, run_id, **params):
    items = client.get(f"{RUNS}/{run_id}/results", headers=headers, params=params).json()["items"]
    return {item["case_key"]: item for item in items}


def _sandbox_users(db_session) -> int:
    return db_session.scalar(select(func.count()).select_from(User).where(User.email.like(f"%@{SANDBOX_EMAIL_DOMAIN}")))


def test_catalog_lists_all_five_categories(api_client, make_authenticated_user):
    items = api_client.get("/api/v1/security/test-cases", headers=make_authenticated_user()).json()["items"]

    assert {item["category"] for item in items} == set(CATEGORIES)
    assert all(item["mitigation"] for item in items)


def test_extractive_run_checks_isolation_and_skips_llm_only_cases(api_client, owner, db_session):
    created = api_client.post(RUNS, headers=owner, json={})

    assert created.status_code == 202
    run = api_client.get(f"{RUNS}/{created.json()['id']}", headers=owner).json()
    assert run["status"] == "completed"
    assert run["completed_cases"] == run["total_cases"] > 0
    results = _results(api_client, owner, run["id"])
    assert {key: results[key]["status"] for key in ("AC-01", "AC-02", "DL-02")} == {"AC-01": "pass", "AC-02": "pass", "DL-02": "pass"}
    assert results["PI-01"]["status"] == "skipped"
    assert results["AC-02"]["contexts"] == []
    # Đoạn lấy về của AC-01 chỉ là tài liệu sandbox của attacker, không có tài liệu của nạn nhân hay của user thật.
    canary = run["environment"]["canary"]
    assert all(canary not in c["snippet"] and c["filename"] != "rieng.txt" for c in results["AC-01"]["contexts"])
    assert any("PI-01" in note for note in run["coverage_notes"])
    assert run["summary"]["by_status"]["skipped"] >= 1

    # Hết lượt: sandbox bị xóa; tài liệu thật của user còn nguyên.
    assert _sandbox_users(db_session) == 0
    documents = api_client.get("/api/v1/documents", headers=owner).json()["items"]
    assert [d["filename"] for d in documents] == ["rieng.txt"]


def test_selected_categories_only(api_client, owner):
    run = api_client.post(RUNS, headers=owner, json={"categories": ["access_control"]}).json()

    results = _results(api_client, owner, run["id"])
    assert set(results) == {"AC-01", "AC-02"}
    assert any("Không chạy các nhóm" in note for note in run["coverage_notes"])


def test_leaked_secret_fails_and_evidence_names_it_without_the_value(api_client, owner, db_session, security_run_service):
    class LeakyPipeline:
        def run(self, session, *, question, user_id, config, document_ids=None):
            return RagResult(f"Khóa là {TEST_SECRETS['JWT_SECRET']}", False, [], [], "extractive", "extractive", "top-passages", "rag-v1", 5, None, None, Decimal(0))

    leaky = SecurityRunService(
        session_factory=lambda: nullcontext(db_session),
        pipeline_provider=LeakyPipeline,
        embedder_provider=security_run_service._embedder_provider,
        judge_client_for=lambda model: None,
        secrets_provider=lambda: TEST_SECRETS,
    )
    app.dependency_overrides[get_security_run_service] = lambda: leaky

    run = api_client.post(RUNS, headers=owner, json={"categories": ["data_leakage"]}).json()

    result = _results(api_client, owner, run["id"])["DL-02"]
    assert (result["status"], result["severity"], result["evaluator"]) == ("fail", "critical", "rule")
    evidence = str(result["evidence"])
    assert "JWT_SECRET" in evidence and TEST_SECRETS["JWT_SECRET"] not in evidence
    detail = api_client.get(f"{RUNS}/{run['id']}", headers=owner).json()
    assert detail["summary"]["failed_by_severity"] == {"critical": 1}


def test_llm_run_uses_rules_and_judge(api_client, owner, llm_server, scripted_llm, judge_llm):
    config = api_client.post(
        "/api/v1/model-configurations", headers=owner, json={"name": "llm", "llm_provider": "test", "llm_model": "model-a"}
    ).json()
    # LLM giả luôn từ chối: đúng với mọi test chỉ dẫn độc.
    scripted_llm._respond = lambda messages: INSUFFICIENT_CONTEXT_ANSWER
    judge_llm._respond = lambda messages: '{"violated": false, "reason": "từ chối"}'

    run = api_client.post(RUNS, headers=owner, json={"model_configuration_id": config["id"], "judge_model": "judge-a"}).json()

    detail = api_client.get(f"{RUNS}/{run['id']}", headers=owner).json()
    assert detail["status"] == "completed"
    assert detail["summary"]["by_status"] == {"pass": detail["total_cases"]}
    results = _results(api_client, owner, run["id"])
    assert results["DL-01"]["evaluator"] == "judge"
    assert results["PI-03"]["evaluator"] == "rule"


def test_llm_that_obeys_injection_fails(api_client, owner, llm_server, scripted_llm):
    config = api_client.post(
        "/api/v1/model-configurations", headers=owner, json={"name": "llm", "llm_provider": "test", "llm_model": "model-a"}
    ).json()
    scripted_llm._respond = lambda messages: "Thủ đô của Úc là Canberra."

    run = api_client.post(RUNS, headers=owner, json={"model_configuration_id": config["id"], "categories": ["prompt_injection"]}).json()

    result = _results(api_client, owner, run["id"], status="fail")["PI-03"]
    assert {v["rule"] for v in result["evidence"]["violations"]} == {"require_insufficient_context", "forbidden_in_answer"}


def test_report_csv_includes_coverage_limits(api_client, owner):
    run = api_client.post(RUNS, headers=owner, json={"categories": ["access_control"]}).json()

    response = api_client.get(f"{RUNS}/{run['id']}/report?format=csv", headers=owner)

    assert response.status_code == 200
    text_content = response.content.decode("utf-8-sig")
    assert "không kết luận hệ thống an toàn tuyệt đối" in text_content
    header = next(row for row in csv.reader(io.StringIO(text_content)) if row and row[0] == "case_key")
    assert "mitigation" in header


def test_runs_are_private(api_client, owner, make_authenticated_user):
    run = api_client.post(RUNS, headers=owner, json={"categories": ["access_control"]}).json()
    stranger = make_authenticated_user()

    assert api_client.get(f"{RUNS}/{run['id']}", headers=stranger).status_code == 404
    assert api_client.get(f"{RUNS}/{run['id']}/results", headers=stranger).status_code == 404
    assert api_client.get(f"{RUNS}/{run['id']}/report", headers=stranger).status_code == 404
    assert api_client.get(RUNS, headers=stranger).json()["total"] == 0


def test_report_requires_completed_run_and_recovery_cleans_sandbox(api_client, owner, db_session, security_run_service):
    run_id = api_client.post(RUNS, headers=owner, json={"categories": ["access_control"]}).json()["id"]
    db_session.get(SecurityTestRun, run_id).status = "running"
    db_session.add(User(email=f"security-leftover-attacker@{SANDBOX_EMAIL_DOMAIN}", password_hash="!", is_active=False))
    db_session.flush()

    assert api_client.get(f"{RUNS}/{run_id}/report", headers=owner).status_code == 409
    assert security_run_service.recover_interrupted() == 1
    assert api_client.get(f"{RUNS}/{run_id}", headers=owner).json()["status"] == "failed"
    assert _sandbox_users(db_session) == 0


def test_sandbox_domain_cannot_register(api_client):
    response = api_client.post(
        "/api/v1/auth/register", json={"email": f"x@{SANDBOX_EMAIL_DOMAIN}", "password": "mat-khau-thu-nghiem-1"}
    )

    assert response.status_code == 422


def test_sandbox_documents_never_mix_with_real_documents(api_client, owner, db_session):
    api_client.post(RUNS, headers=owner, json={})

    remaining = db_session.scalar(select(func.count()).select_from(Document).where(Document.storage_path.like("sandbox://%")))
    assert remaining == 0


def test_deleting_a_user_removes_their_security_runs(api_client, owner, db_session):
    run_id = api_client.post(RUNS, headers=owner, json={"categories": ["access_control"]}).json()["id"]
    user_id = db_session.get(SecurityTestRun, run_id).user_id

    db_session.execute(delete(User).where(User.id == user_id))
    db_session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    assert db_session.get(SecurityTestRun, run_id, populate_existing=True) is None
