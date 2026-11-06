"""Kiểm thử bảo mật (M7) trên chính hệ thống này, qua RAG pipeline dùng chung.

Mỗi lượt chạy trong một sandbox riêng: hai user tạm (attacker, victim) không đăng nhập được, tài liệu thử lấy từ YAML,
xử lý bằng đúng chunker và embedder của luồng thật. Câu hỏi được gửi với quyền của attacker. Hết lượt thì xóa sandbox;
bản chụp các đoạn lấy về vẫn nằm trong kết quả làm bằng chứng. Tài liệu thật của user không bị dùng hay thay đổi.
"""

import logging
import time
import uuid
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from datetime import datetime, timezone

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from ai_engine.embeddings.base_embedder import Embedder
from ai_engine.generation.base_llm_client import LlmClient
from ai_engine.generation.prompt_templates import INSUFFICIENT_CONTEXT_ANSWER, build_answer_messages
from ai_engine.ingestion.ingestion_pipeline import ingest
from ai_engine.pipeline.rag_pipeline import RagPipeline
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.run_environment import snapshot
from app.models.model_config import ModelConfiguration
from app.models.security_test import SecurityTestCase, SecurityTestResult, SecurityTestRun
from app.models.user import User
from app.repositories.security_repository import SecurityRepository
from app.schemas.security_test import SecurityRunCreate
from app.services.model_config_service import ModelConfigService, llm_configured
from evaluation.evaluators.judge_prompts import DEFAULT_JUDGE_PROMPT_VERSION
from evaluation.evaluators.llm_judge import LlmJudge
from evaluation.reports.report_builder import build_csv
from security.evaluators.security_result_evaluator import protected_fragments
from security.reports.security_report_builder import coverage_notes
from security.runners.security_runner import SecurityOutcome, SecurityRunner
from security.test_case_loader import Canary, SecurityCase, load_cases, materialize, parse_case

logger = logging.getLogger(__name__)

INTERRUPTED_MESSAGE = "Lượt kiểm thử bị gián đoạn vì máy chủ khởi động lại; hãy tạo lượt mới"
UNEXPECTED_MESSAGE = "Lỗi hệ thống khi chạy kiểm thử bảo mật"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def server_secrets() -> dict[str, str]:
    """Giá trị secret thật của máy chủ, chỉ dùng trong bộ nhớ để dò rò rỉ; không bao giờ ghi ra DB hay log."""
    values = {"JWT_SECRET": settings.jwt_secret, "LLM_API_KEY": settings.llm_api_key or ""}
    try:
        values["DATABASE_PASSWORD"] = make_url(settings.database_url).password or ""
    except Exception:
        values["DATABASE_PASSWORD"] = ""
    # Chuỗi quá ngắn dễ khớp nhầm; bỏ qua.
    return {name: value for name, value in values.items() if len(value) >= 8}


def case_from_snapshot(row: SecurityTestCase) -> SecurityCase:
    item = {
        "key": row.case_key,
        "version": row.case_version,
        "title": row.title,
        "description": row.description,
        "severity": row.default_severity,
        "requires_llm": row.requires_llm,
        "input": row.input_payload,
        "expected_behavior": row.expected_behavior,
        "rules": row.evaluation_criteria["rules"],
        "mitigation": row.mitigation,
    }
    if row.setup:
        item["setup"] = row.setup
    if row.evaluation_criteria.get("judge") is not None:
        item["judge"] = row.evaluation_criteria["judge"]
    case = parse_case(row.category, item, source=f"snapshot {row.case_key}")
    if case.content_hash != row.content_hash:
        raise ValueError(f"Bản chụp test case {row.case_key} không khớp content_hash")
    return case


class SecurityService:
    def __init__(self, repository: SecurityRepository, configs: ModelConfigService) -> None:
        self._repository = repository
        self._configs = configs

    @staticmethod
    def list_test_cases(category: str | None = None) -> list[SecurityCase]:
        return load_cases(categories=(category,) if category else None)

    def create_run(self, user: User, payload: SecurityRunCreate) -> SecurityTestRun:
        config = self._configs.resolve_for_use(user, payload.model_configuration_id)
        if payload.judge_model and not llm_configured():
            raise AppError(422, "validation_error", "Máy chủ chưa cấu hình LLM nên không có judge; để trống judge_model")
        categories = sorted(set(payload.categories)) if payload.categories else []
        cases = load_cases(categories=tuple(categories) or None)
        if not cases:
            raise AppError(422, "validation_error", "Không có test case nào cho các nhóm đã chọn")
        snapshots = [self._repository.snapshot_case(case) for case in cases]
        llm_available = ModelConfigService.to_rag_config(config).uses_llm
        run = self._repository.add_run(
            SecurityTestRun(
                user_id=user.id,
                model_configuration_id=config.id,
                status="pending",
                categories=categories,
                total_cases=len(cases),
                judge_model=payload.judge_model,
                judge_prompt_version=(payload.judge_prompt_version or DEFAULT_JUDGE_PROMPT_VERSION) if payload.judge_model else None,
                coverage_notes=coverage_notes(
                    cases, requested_categories=categories or None, llm_available=llm_available, judge_used=bool(payload.judge_model)
                ),
                environment=snapshot(
                    model_configuration={
                        "id": str(config.id),
                        "name": config.name,
                        "llm_provider": config.llm_provider,
                        "llm_model": config.llm_model,
                        "embedding_model": config.embedding_model,
                        "prompt_version": config.prompt_version,
                        "top_k": config.top_k,
                        "temperature": config.temperature,
                        "chunk_size": config.chunk_size,
                        "chunk_overlap": config.chunk_overlap,
                    },
                    llm_available=llm_available,
                    cases=[{"id": str(row.id), "key": row.case_key, "content_hash": row.content_hash} for row in snapshots],
                ),
            )
        )
        self._repository.commit()
        return run

    def list_runs(self, user: User, *, limit: int, offset: int):
        return self._repository.list_runs(user.id, limit=limit, offset=offset)

    def get_run(self, user: User, run_id: uuid.UUID) -> SecurityTestRun:
        run = self._repository.get_run_for_user(user.id, run_id)
        if run is None:
            raise AppError(404, "not_found", "Không tìm thấy lượt kiểm thử bảo mật")
        return run

    def results(self, user: User, run_id: uuid.UUID, *, status=None, severity=None, category=None, limit=None, offset=0):
        run = self.get_run(user, run_id)
        rows, total = self._repository.list_results(run.id, status=status, severity=severity, category=category, limit=limit, offset=offset)
        return rows, total, self._repository.contexts_for_results([result.id for result, _ in rows])

    def report_csv(self, user: User, run_id: uuid.UUID) -> tuple[SecurityTestRun, str]:
        run = self.get_run(user, run_id)
        if run.status != "completed":
            raise AppError(409, "conflict", "Chỉ xuất báo cáo khi lượt kiểm thử đã hoàn tất")
        rows, _, _ = self.results(user, run_id)
        config = (run.environment or {}).get("model_configuration", {})
        summary = run.summary or {}
        metadata = [
            ("run_id", run.id),
            ("LLM", f"{config.get('llm_provider')}/{config.get('llm_model')}"),
            ("prompt", config.get("prompt_version")),
            ("top_k", config.get("top_k")),
            ("judge", run.judge_model or "không dùng"),
            ("nhóm", ", ".join(run.categories) or "cả 5 nhóm"),
            ("số test", run.total_cases),
            *[(f"số {status}", count) for status, count in sorted((summary.get("by_status") or {}).items())],
            *[(f"fail mức {severity}", count) for severity, count in sorted((summary.get("failed_by_severity") or {}).items())],
            ("bắt đầu", run.started_at),
            ("kết thúc", run.finished_at),
            *[(f"giới hạn {i}", note) for i, note in enumerate(run.coverage_notes or [], start=1)],
        ]
        columns = ["case_key", "category", "title", "severity", "status", "evaluator", "violations", "judge", "actual_response", "mitigation", "error_message"]
        table = []
        for result, case in rows:
            evidence = result.evidence or {}
            judge = evidence.get("judge") or {}
            table.append(
                {
                    "case_key": case.case_key,
                    "category": case.category,
                    "title": case.title,
                    "severity": result.severity,
                    "status": result.status,
                    "evaluator": result.evaluator,
                    "violations": "; ".join(v["detail"] for v in evidence.get("violations", [])) or evidence.get("reason"),
                    "judge": f"{judge.get('status')}: {judge.get('reason', '')}" if judge else None,
                    "actual_response": result.actual_response,
                    "mitigation": result.mitigation,
                    "error_message": result.error_message,
                }
            )
        return run, build_csv(metadata, columns, table)


class SecurityRunService:
    def __init__(
        self,
        *,
        session_factory: Callable[[], AbstractContextManager[Session]],
        pipeline_provider: Callable[[], RagPipeline],
        embedder_provider: Callable[[], Embedder],
        judge_client_for: Callable[[str], LlmClient],
        secrets_provider: Callable[[], Mapping[str, str]] = server_secrets,
    ) -> None:
        self._session_factory = session_factory
        self._pipeline_provider = pipeline_provider
        self._embedder_provider = embedder_provider
        self._judge_client_for = judge_client_for
        self._secrets_provider = secrets_provider

    def execute(self, run_id: uuid.UUID) -> None:
        with self._session_factory() as session:
            repository = SecurityRepository(session)
            run = repository.get_run(run_id)
            if run is None:
                return
            run.status, run.started_at = "running", _now()
            repository.commit()
            try:
                self._execute(session, repository, run)
            except Exception:
                logger.exception("Security run failed: run_id=%s", run_id)
                repository.rollback()
                run = repository.get_run(run_id)
                if run is not None:
                    run.status, run.error_message, run.finished_at = "failed", UNEXPECTED_MESSAGE, _now()
                    repository.commit()
            finally:
                repository.delete_sandbox_users(run_id)
                repository.commit()

    def _execute(self, session: Session, repository: SecurityRepository, run: SecurityTestRun) -> None:
        config = session.get(ModelConfiguration, run.model_configuration_id)
        rag_config = ModelConfigService.to_rag_config(config)
        rows = repository.cases_by_ids([uuid.UUID(item["id"]) for item in run.environment["cases"]])
        canary = Canary.generate()
        cases = [materialize(case_from_snapshot(row), canary) for row in rows]
        row_ids = {row.case_key: row.id for row in rows}
        run_id = run.id
        run.environment = {**run.environment, "canary": canary.value}

        attacker = repository.create_sandbox_user(run_id, "attacker")
        victim = repository.create_sandbox_user(run_id, "victim")
        owners = {"attacker": attacker.id, "victim": victim.id}
        documents = self._prepare_documents(repository, cases, owners, config.chunk_size, config.chunk_overlap)
        repository.commit()

        pipeline = self._pipeline_provider()
        judge = LlmJudge(self._judge_client_for(run.judge_model), run.judge_prompt_version) if run.judge_model else None
        system_prompt = build_answer_messages(rag_config.prompt_version, "", [])[0].content
        attacker_id = attacker.id

        def ask(case: SecurityCase):
            if case.scope == "all_own_documents":
                document_ids = None
            elif case.scope == "victim_documents":
                document_ids = documents[case.key]["victim"]
            else:
                document_ids = documents[case.key]["attacker"]
            return pipeline.run(session, question=case.question, user_id=attacker_id, config=rag_config, document_ids=document_ids)

        def on_case(outcome: SecurityOutcome) -> None:
            result = outcome.result
            repository.add_result(
                SecurityTestResult(
                    run_id=run_id,
                    test_case_id=row_ids[outcome.case.key],
                    status=outcome.status,
                    severity=outcome.case.severity,
                    actual_response=result.answer if result else None,
                    evidence=outcome.evidence,
                    evaluator=outcome.evaluator,
                    mitigation=outcome.case.mitigation,
                    error_message=outcome.error_message,
                    latency_ms=result.latency_ms if result else None,
                ),
                result.contexts if result else [],
            )
            repository.get_run(run_id).completed_cases += 1
            repository.commit()

        started = time.monotonic()
        summary = SecurityRunner(
            ask=ask,
            llm_available=rag_config.uses_llm,
            protected=protected_fragments(system_prompt, allowed=[INSUFFICIENT_CONTEXT_ANSWER]),
            secrets=self._secrets_provider(),
            judge=judge,
            on_case=on_case,
        ).run(cases)
        run = repository.get_run(run_id)
        run.summary = {
            "by_status": summary.by_status,
            "failed_by_severity": summary.failed_by_severity,
            "by_category": summary.by_category,
        }
        run.status, run.finished_at = "completed", _now()
        repository.commit()
        logger.info("Security run completed: run_id=%s cases=%s seconds=%.1f", run_id, summary.total, time.monotonic() - started)

    def _prepare_documents(self, repository, cases, owners, chunk_size, chunk_overlap) -> dict[str, dict[str, list[uuid.UUID]]]:
        embedder = self._embedder_provider()
        created: dict[tuple[str, str], uuid.UUID] = {}
        per_case: dict[str, dict[str, list[uuid.UUID]]] = {}
        for case in cases:
            ids: dict[str, list[uuid.UUID]] = {"attacker": [], "victim": []}
            for document in case.documents:
                key = (document.owner, document.text)
                if key not in created:
                    content = document.text.encode("utf-8")
                    ingested = ingest(content, "text/plain", chunk_size=chunk_size, chunk_overlap=chunk_overlap, embedder=embedder)
                    created[key] = repository.add_sandbox_document(owners[document.owner], document.filename, content, ingested).id
                ids[document.owner].append(created[key])
            per_case[case.key] = ids
        return per_case

    def recover_interrupted(self) -> int:
        with self._session_factory() as session:
            repository = SecurityRepository(session)
            count = repository.mark_unfinished_runs_failed(INTERRUPTED_MESSAGE)
            repository.delete_sandbox_users()
            repository.commit()
        return count
