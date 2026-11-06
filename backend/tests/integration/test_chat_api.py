import uuid

import pytest
from sqlalchemy import func, select

from ai_engine.generation.base_llm_client import LlmError, LlmRateLimitError
from ai_engine.generation.prompt_templates import INSUFFICIENT_CONTEXT_ANSWER
from app.core.config import settings
from app.models import ChatMessage, RetrievedContext

pytestmark = pytest.mark.integration

ASK = "/api/v1/chat/messages"
CONFIGS = "/api/v1/model-configurations"


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))


@pytest.fixture
def llm_server(monkeypatch):
    """Giả lập máy chủ đã cấu hình một LLM provider (LLM thật được thay bằng ScriptedLlm)."""
    monkeypatch.setattr(settings, "llm_base_url", "https://llm.example/v1")
    monkeypatch.setattr(settings, "llm_model", "model-a")
    monkeypatch.setattr(settings, "llm_provider_name", "test")


def _upload(client, headers, text, name="quy-dinh.txt"):
    response = client.post("/api/v1/documents", headers=headers, files={"file": (name, text.encode(), "text/plain")})
    assert response.status_code == 202, response.text
    return response.json()


def _ask(client, headers, question, **extra):
    return client.post(ASK, headers=headers, json={"question": question, **extra})


# ------------------------------------------------------------------------------------- chế độ không LLM
def test_without_llm_configured_chat_answers_in_extractive_mode(api_client, make_authenticated_user, scripted_llm):
    headers = make_authenticated_user()
    _upload(api_client, headers, "Hồ sơ xin cấp giấy phép phải nộp trong vòng 30 ngày.")

    response = _ask(api_client, headers, "nộp hồ sơ giấy phép trong bao lâu")

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "extractive"
    assert "30 ngày" in body["answer"]
    assert body["citations"][0]["filename"] == "quy-dinh.txt"
    assert scripted_llm.calls == []
    assert body["metrics"]["estimated_cost"] == "0" or float(body["metrics"]["estimated_cost"]) == 0.0


def test_question_without_any_documents_gets_the_refusal(api_client, make_authenticated_user):
    body = _ask(api_client, make_authenticated_user(), "Bất cứ điều gì").json()

    assert body["answer"] == INSUFFICIENT_CONTEXT_ANSWER
    assert body["insufficient_context"] is True
    assert body["citations"] == [] and body["sources"] == []


# ------------------------------------------------------------------------------------- có LLM
def test_with_llm_the_answer_cites_sources_and_metrics_are_recorded(
    api_client, make_authenticated_user, scripted_llm, llm_server, db_session
):
    scripted_llm._respond = lambda messages: "Phải nộp trong 30 ngày [1]."
    headers = make_authenticated_user()
    _upload(api_client, headers, "Hồ sơ xin cấp giấy phép phải nộp trong vòng 30 ngày.")

    body = _ask(api_client, headers, "Hạn nộp hồ sơ giấy phép?").json()

    assert body["mode"] == "llm"
    assert body["answer"] == "Phải nộp trong 30 ngày [1]."
    assert [c["number"] for c in body["citations"]] == [1]
    assert body["metrics"]["prompt_tokens"] == 100 and body["metrics"]["completion_tokens"] == 20
    assert body["metrics"]["estimated_cost"] is None  # model giả không có trong bảng giá: "không biết", không phải 0
    stored = db_session.get(ChatMessage, uuid.UUID(body["message_id"]))
    assert (stored.role, stored.prompt_tokens, stored.latency_ms is not None) == ("assistant", 100, True)
    contexts = db_session.scalars(select(RetrievedContext).where(RetrievedContext.chat_message_id == stored.id)).all()
    assert [c.rank for c in contexts] == [1] and "30 ngày" in contexts[0].content_snapshot


def test_default_configuration_follows_the_server_llm(api_client, make_authenticated_user, llm_server):
    headers = make_authenticated_user()
    _upload(api_client, headers, "nội dung")

    config_id = _ask(api_client, headers, "nội dung").json()["model_configuration_id"]

    config = api_client.get(f"{CONFIGS}/{config_id}", headers=headers).json()
    assert (config["llm_provider"], config["llm_model"]) == ("test", "model-a")


def test_provider_failure_is_502_and_the_failed_turn_stays_in_history(
    api_client, make_authenticated_user, scripted_llm, llm_server
):
    scripted_llm._respond = lambda messages: LlmError("Không kết nối được tới LLM")
    headers = make_authenticated_user()
    _upload(api_client, headers, "nội dung")

    response = _ask(api_client, headers, "nội dung")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "provider_error"
    session_id = api_client.get("/api/v1/chat/sessions", headers=headers).json()["items"][0]["id"]
    messages = api_client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=headers).json()["items"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["error_message"] == "Không kết nối được tới LLM"


def test_rate_limit_is_429(api_client, make_authenticated_user, scripted_llm, llm_server):
    scripted_llm._respond = lambda messages: LlmRateLimitError("LLM từ chối vì vượt hạn mức tần suất")
    headers = make_authenticated_user()
    _upload(api_client, headers, "nội dung")

    response = _ask(api_client, headers, "nội dung")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


def test_llm_configuration_cannot_be_used_when_the_server_has_no_llm(api_client, make_authenticated_user, llm_server, monkeypatch):
    headers = make_authenticated_user()
    config_id = api_client.post(CONFIGS, headers=headers, json={"name": "c", "llm_provider": "test", "llm_model": "model-a"}).json()["id"]
    monkeypatch.setattr(settings, "llm_base_url", None)

    response = _ask(api_client, headers, "x", model_configuration_id=config_id)

    assert response.status_code == 422
    assert "chưa cấu hình LLM" in response.json()["error"]["message"]


# ------------------------------------------------------------------------------------- phiên, lịch sử, cô lập
def test_follow_up_question_goes_into_the_same_session(api_client, make_authenticated_user):
    headers = make_authenticated_user()
    _upload(api_client, headers, "Hồ sơ nộp trong 30 ngày.")
    first = _ask(api_client, headers, "Hồ sơ nộp khi nào?").json()

    second = _ask(api_client, headers, "Còn lệ phí?", session_id=first["session_id"]).json()

    assert second["session_id"] == first["session_id"]
    sessions = api_client.get("/api/v1/chat/sessions", headers=headers).json()
    assert sessions["total"] == 1 and sessions["items"][0]["title"] == "Hồ sơ nộp khi nào?"
    messages = api_client.get(f"/api/v1/chat/sessions/{first['session_id']}/messages", headers=headers).json()["items"]
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    assert messages[1]["sources"][0]["filename"] == "quy-dinh.txt"


def test_another_users_session_is_404_everywhere(api_client, make_authenticated_user):
    owner, stranger = make_authenticated_user(), make_authenticated_user()
    session_id = _ask(api_client, owner, "câu hỏi").json()["session_id"]

    assert _ask(api_client, stranger, "chen vao", session_id=session_id).status_code == 404
    assert api_client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=stranger).status_code == 404
    assert api_client.delete(f"/api/v1/chat/sessions/{session_id}", headers=stranger).status_code == 404
    assert api_client.get("/api/v1/chat/sessions", headers=stranger).json()["total"] == 0


def test_another_users_configuration_cannot_be_used(api_client, make_authenticated_user):
    owner, stranger = make_authenticated_user(), make_authenticated_user()
    config_id = api_client.post(
        CONFIGS, headers=owner, json={"name": "rieng", "llm_provider": "extractive", "llm_model": "top-passages"}
    ).json()["id"]

    assert _ask(api_client, stranger, "x", model_configuration_id=config_id).status_code == 404


def test_answers_never_include_another_users_documents(api_client, make_authenticated_user):
    alice, bob = make_authenticated_user(), make_authenticated_user()
    _upload(api_client, bob, "canary-bi-mat luong giam doc 999 trieu", name="bi-mat.txt")

    body = _ask(api_client, alice, "canary-bi-mat luong giam doc").json()

    assert body["insufficient_context"] is True
    assert "canary" not in str(body)


def test_deleting_a_session_removes_its_messages(api_client, make_authenticated_user, db_session):
    headers = make_authenticated_user()
    session_id = _ask(api_client, headers, "câu hỏi").json()["session_id"]

    assert api_client.delete(f"/api/v1/chat/sessions/{session_id}", headers=headers).status_code == 204
    remaining = db_session.scalar(select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == uuid.UUID(session_id)))
    assert remaining == 0


@pytest.mark.parametrize("payload", [{"question": ""}, {"question": "x" * 2001}, {}])
def test_invalid_questions_are_rejected(api_client, make_authenticated_user, payload):
    assert api_client.post(ASK, headers=make_authenticated_user(), json=payload).status_code == 422


def test_chat_requires_authentication(api_client):
    assert api_client.post(ASK, json={"question": "x"}).status_code == 401


# ------------------------------------------------------------------------------------- cấu hình model
def test_capabilities_report_what_the_server_can_run(api_client, make_authenticated_user):
    body = api_client.get(f"{CONFIGS}/capabilities", headers=make_authenticated_user()).json()

    assert body["llm_configured"] is False
    assert body["embedding_model"] == "intfloat/multilingual-e5-small"
    assert "rag-v1" in body["prompt_versions"]


def test_configuration_defaults_come_from_rag_default_yaml(api_client, make_authenticated_user):
    body = api_client.post(
        CONFIGS, headers=make_authenticated_user(), json={"name": "c", "llm_provider": "extractive", "llm_model": "top-passages"}
    ).json()

    assert (body["top_k"], body["chunk_size"], body["chunk_overlap"], body["prompt_version"]) == (5, 250, 50, "rag-v1")


@pytest.mark.parametrize(
    "payload, fragment",
    [
        ({"llm_provider": "test", "llm_model": "m"}, "chưa cấu hình LLM"),
        ({"llm_provider": "extractive", "llm_model": "khac"}, "top-passages"),
        ({"llm_provider": "extractive", "llm_model": "top-passages", "embedding_model": "khac"}, "embed lại"),
        ({"llm_provider": "extractive", "llm_model": "top-passages", "prompt_version": "rag-v9"}, "rag-v9"),
    ],
)
def test_configurations_the_server_cannot_run_are_rejected(api_client, make_authenticated_user, payload, fragment):
    response = api_client.post(CONFIGS, headers=make_authenticated_user(), json={"name": "c", **payload})

    assert response.status_code == 422
    assert fragment in response.json()["error"]["message"]


def test_configuration_names_are_unique_per_user(api_client, make_authenticated_user):
    headers = make_authenticated_user()
    payload = {"name": "trung", "llm_provider": "extractive", "llm_model": "top-passages"}
    api_client.post(CONFIGS, headers=headers, json=payload)

    assert api_client.post(CONFIGS, headers=headers, json=payload).status_code == 409


def test_configurations_are_private(api_client, make_authenticated_user):
    owner, stranger = make_authenticated_user(), make_authenticated_user()
    config_id = api_client.post(
        CONFIGS, headers=owner, json={"name": "c", "llm_provider": "extractive", "llm_model": "top-passages"}
    ).json()["id"]

    assert api_client.get(f"{CONFIGS}/{config_id}", headers=stranger).status_code == 404
    assert api_client.get(CONFIGS, headers=stranger).json()["total"] == 0
