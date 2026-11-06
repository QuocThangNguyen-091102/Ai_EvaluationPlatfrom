import uuid
from decimal import Decimal

import pytest

from ai_engine.generation.base_llm_client import LlmError
from ai_engine.generation.cost_estimator import ModelPrice, PriceTable
from ai_engine.generation.prompt_templates import INSUFFICIENT_CONTEXT_ANSWER
from ai_engine.ingestion.ingestion_pipeline import ingest
from ai_engine.pipeline.rag_config import EXTRACTIVE_MODEL, EXTRACTIVE_PROVIDER, RAGConfig
from ai_engine.pipeline.rag_pipeline import EXTRACTIVE_INTRO, RagPipeline
from app.models import Document, User
from app.repositories.chunk_repository import ChunkRepository
from tests.fakes import HashEmbedder, ScriptedLlm

pytestmark = pytest.mark.integration

EMBEDDER = HashEmbedder()
PRICES = PriceTable([ModelPrice("test", "scripted", Decimal("1"), Decimal("2"), "USD", "2026-11-06")])
LLM_CONFIG = RAGConfig(top_k=3, temperature=0.0, prompt_version="rag-v1", llm_provider="test", llm_model="scripted")
EXTRACTIVE_CONFIG = RAGConfig(
    top_k=3, temperature=0.0, prompt_version="rag-v1", llm_provider=EXTRACTIVE_PROVIDER, llm_model=EXTRACTIVE_MODEL
)


def _user(session) -> User:
    user = User(email=f"{uuid.uuid4()}@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


def _document(session, user, text, filename="quy-dinh.txt") -> Document:
    document = Document(
        user_id=user.id, filename=filename, content_type="text/plain", size_bytes=len(text),
        content_hash=uuid.uuid4().hex + uuid.uuid4().hex[:32], storage_path="x", status="ready",
    )
    session.add(document)
    session.flush()
    result = ingest(text.encode(), "text/plain", chunk_size=50, chunk_overlap=0, embedder=EMBEDDER)
    ChunkRepository(session).replace_chunks(user_id=user.id, document_id=document.id, chunks=result.chunks, embedding_model="t")
    return document


def _pipeline(llm=None, clock=None):
    llm = llm or ScriptedLlm()
    kwargs = {"clock": clock} if clock else {}
    return RagPipeline(embedder=EMBEDDER, llm_for=lambda config: llm, price_table=PRICES, **kwargs), llm


def test_answer_uses_retrieved_context_and_reports_cited_sources(db_session):
    user = _user(db_session)
    _document(db_session, user, "Hồ sơ xin cấp giấy phép phải nộp trong vòng 30 ngày.")
    pipeline, llm = _pipeline(ScriptedLlm(lambda m: "Phải nộp trong 30 ngày [1]."))

    result = pipeline.run(db_session, question="Hạn nộp hồ sơ giấy phép?", user_id=user.id, config=LLM_CONFIG)

    assert result.answer == "Phải nộp trong 30 ngày [1]."
    assert result.mode == "llm" and not result.insufficient_context
    assert [c.number for c in result.citations] == [1]
    assert result.citations[0].chunk.filename == "quy-dinh.txt"
    prompt = llm.calls[0][1].content
    assert "30 ngày" in prompt and "Câu hỏi: Hạn nộp hồ sơ giấy phép?" in prompt


def test_no_documents_means_refusal_without_calling_the_llm(db_session):
    user = _user(db_session)
    pipeline, llm = _pipeline()

    result = pipeline.run(db_session, question="Bất kỳ?", user_id=user.id, config=LLM_CONFIG)

    assert result.answer == INSUFFICIENT_CONTEXT_ANSWER
    assert result.insufficient_context and result.contexts == [] and result.citations == []
    assert llm.calls == []
    assert result.estimated_cost == Decimal(0)


def test_llm_refusal_is_recognized_as_insufficient_context(db_session):
    user = _user(db_session)
    _document(db_session, user, "Món phở bò nấu từ xương ống.")
    pipeline, _ = _pipeline(ScriptedLlm(lambda m: INSUFFICIENT_CONTEXT_ANSWER))

    result = pipeline.run(db_session, question="Lương giám đốc bao nhiêu?", user_id=user.id, config=LLM_CONFIG)

    assert result.insufficient_context
    assert result.citations == []
    assert result.contexts, "ngữ cảnh đã đưa cho LLM vẫn được ghi lại để phân tích lỗi"


def test_citations_outside_the_context_range_are_ignored(db_session):
    user = _user(db_session)
    _document(db_session, user, "Hồ sơ nộp trong 30 ngày.")
    pipeline, _ = _pipeline(ScriptedLlm(lambda m: "Theo [1] và [7] và [1] lần nữa."))

    result = pipeline.run(db_session, question="hồ sơ", user_id=user.id, config=LLM_CONFIG)

    assert [c.number for c in result.citations] == [1]


def test_extractive_mode_answers_without_any_llm(db_session):
    user = _user(db_session)
    _document(db_session, user, "Hồ sơ xin cấp giấy phép phải nộp trong vòng 30 ngày.")
    pipeline, llm = _pipeline()

    result = pipeline.run(db_session, question="nộp hồ sơ giấy phép", user_id=user.id, config=EXTRACTIVE_CONFIG)

    assert result.mode == "extractive"
    assert result.answer.startswith(EXTRACTIVE_INTRO)
    assert "[1] Hồ sơ xin cấp giấy phép" in result.answer
    assert llm.calls == []
    assert (result.prompt_tokens, result.estimated_cost) == (None, Decimal(0))


def test_pipeline_never_uses_another_users_documents(db_session):
    alice, bob = _user(db_session), _user(db_session)
    _document(db_session, bob, "canary-bi-mat luong giam doc 999 trieu", filename="bi-mat.txt")
    pipeline, llm = _pipeline()

    result = pipeline.run(db_session, question="canary-bi-mat luong giam doc", user_id=alice.id, config=LLM_CONFIG)

    assert result.insufficient_context and result.contexts == []
    assert llm.calls == [], "LLM không bao giờ được thấy nội dung của người khác"


def test_document_filter_is_applied(db_session):
    user = _user(db_session)
    keep = _document(db_session, user, "giấy phép loại A", filename="a.txt")
    _document(db_session, user, "giấy phép loại B", filename="b.txt")
    pipeline, _ = _pipeline()

    result = pipeline.run(db_session, question="giấy phép", user_id=user.id, config=LLM_CONFIG, document_ids=[keep.id])

    assert {c.filename for c in result.contexts} == {"a.txt"}


def test_tokens_cost_and_latency_are_recorded(db_session):
    user = _user(db_session)
    _document(db_session, user, "Hồ sơ nộp trong 30 ngày.")
    ticks = iter([10.0, 10.25])
    pipeline, _ = _pipeline(ScriptedLlm(prompt_tokens=1000, completion_tokens=500), clock=lambda: next(ticks))

    result = pipeline.run(db_session, question="hồ sơ", user_id=user.id, config=LLM_CONFIG)

    assert (result.prompt_tokens, result.completion_tokens) == (1000, 500)
    assert result.estimated_cost == Decimal("0.002000")  # 1000*1 + 500*2 trên 1 triệu
    assert result.latency_ms == 250
    assert (result.llm_provider, result.llm_model, result.prompt_version) == ("test", "scripted", "rag-v1")


def test_unknown_price_gives_unknown_cost(db_session):
    user = _user(db_session)
    _document(db_session, user, "Hồ sơ nộp trong 30 ngày.")
    pipeline, _ = _pipeline()
    config = RAGConfig(top_k=3, temperature=0, prompt_version="rag-v1", llm_provider="test", llm_model="khong-co-gia")

    assert pipeline.run(db_session, question="hồ sơ", user_id=user.id, config=config).estimated_cost is None


def test_llm_errors_propagate_to_the_caller(db_session):
    user = _user(db_session)
    _document(db_session, user, "Hồ sơ nộp trong 30 ngày.")
    pipeline, _ = _pipeline(ScriptedLlm(lambda m: LlmError("LLM lỗi")))

    with pytest.raises(LlmError):
        pipeline.run(db_session, question="hồ sơ", user_id=user.id, config=LLM_CONFIG)


def test_empty_question_is_rejected(db_session):
    pipeline, _ = _pipeline()

    with pytest.raises(ValueError):
        pipeline.run(db_session, question="   ", user_id=uuid.uuid4(), config=LLM_CONFIG)


def test_config_validation():
    with pytest.raises(ValueError):
        RAGConfig(top_k=0, temperature=0, prompt_version="rag-v1", llm_provider="x", llm_model="y")
    with pytest.raises(ValueError):
        RAGConfig(top_k=1, temperature=3, prompt_version="rag-v1", llm_provider="x", llm_model="y")
