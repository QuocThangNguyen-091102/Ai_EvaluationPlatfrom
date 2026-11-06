import hashlib
import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from ai_engine.ingestion.ingestion_pipeline import IngestionResult
from ai_engine.retrieval.vector_retriever import RetrievedChunk
from app.models.document import Document
from app.models.retrieved_context import RetrievedContext
from app.models.security_test import SecurityTestCase, SecurityTestResult, SecurityTestRun
from app.models.user import SANDBOX_EMAIL_DOMAIN, User
from app.repositories.chunk_repository import ChunkRepository
from security.test_case_loader import SecurityCase

_UNUSABLE_PASSWORD_HASH = "!sandbox-account-cannot-log-in"


def sandbox_email(run_id: uuid.UUID, role: str) -> str:
    return f"security-{run_id}-{role}@{SANDBOX_EMAIL_DOMAIN}"


class SecurityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def db_session(self) -> Session:
        return self._session

    # -------------------------------------------------------------------------- test case snapshot
    def snapshot_case(self, case: SecurityCase) -> SecurityTestCase:
        existing = self._session.scalar(
            select(SecurityTestCase).where(SecurityTestCase.case_key == case.key, SecurityTestCase.content_hash == case.content_hash)
        )
        if existing is not None:
            return existing
        raw = case.raw
        row = SecurityTestCase(
            case_key=case.key,
            case_version=case.version,
            content_hash=case.content_hash,
            category=case.category,
            title=case.title,
            description=case.description,
            input_payload=raw["input"],
            setup=raw.get("setup") or {},
            expected_behavior=case.expected_behavior,
            evaluation_criteria={"rules": raw["rules"], "judge": raw.get("judge")},
            default_severity=case.severity,
            requires_llm=case.requires_llm,
            mitigation=case.mitigation,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def cases_by_ids(self, ids: Sequence[uuid.UUID]) -> list[SecurityTestCase]:
        rows = {row.id: row for row in self._session.scalars(select(SecurityTestCase).where(SecurityTestCase.id.in_(ids)))}
        return [rows[i] for i in ids if i in rows]

    # -------------------------------------------------------------------------- run
    def add_run(self, run: SecurityTestRun) -> SecurityTestRun:
        self._session.add(run)
        self._session.flush()
        return run

    def get_run_for_user(self, user_id: uuid.UUID, run_id: uuid.UUID) -> SecurityTestRun | None:
        return self._session.scalar(select(SecurityTestRun).where(SecurityTestRun.id == run_id, SecurityTestRun.user_id == user_id))

    def get_run(self, run_id: uuid.UUID) -> SecurityTestRun | None:
        """Chỉ cho tác vụ nền (id do hệ thống tạo)."""
        return self._session.get(SecurityTestRun, run_id, populate_existing=True)

    def list_runs(self, user_id: uuid.UUID, *, limit: int, offset: int):
        condition = SecurityTestRun.user_id == user_id
        total = self._session.scalar(select(func.count()).select_from(SecurityTestRun).where(condition))
        items = self._session.scalars(
            select(SecurityTestRun).where(condition).order_by(SecurityTestRun.created_at.desc(), SecurityTestRun.id).limit(limit).offset(offset)
        ).all()
        return list(items), total

    def mark_unfinished_runs_failed(self, message: str) -> int:
        result = self._session.execute(
            update(SecurityTestRun)
            .where(SecurityTestRun.status.in_(("pending", "running")))
            .values(status="failed", error_message=message, finished_at=func.now())
        )
        return result.rowcount

    # -------------------------------------------------------------------------- result
    def add_result(self, result: SecurityTestResult, contexts: Sequence[RetrievedChunk]) -> None:
        self._session.add(result)
        self._session.flush()
        self._session.add_all(
            RetrievedContext(
                security_test_result_id=result.id,
                chunk_id=chunk.chunk_id,
                rank=chunk.rank,
                score=chunk.score,
                content_snapshot=chunk.content,
                document_filename_snapshot=chunk.filename,
                page_number=chunk.page_number,
            )
            for chunk in contexts
        )
        self._session.flush()

    def list_results(self, run_id: uuid.UUID, *, status=None, severity=None, category=None, limit=None, offset=0):
        conditions = [SecurityTestResult.run_id == run_id]
        if status:
            conditions.append(SecurityTestResult.status == status)
        if severity:
            conditions.append(SecurityTestResult.severity == severity)
        if category:
            conditions.append(SecurityTestCase.category == category)
        base = select(SecurityTestResult, SecurityTestCase).join(SecurityTestCase, SecurityTestResult.test_case_id == SecurityTestCase.id)
        total = self._session.scalar(select(func.count()).select_from(base.where(*conditions).subquery()))
        query = base.where(*conditions).order_by(SecurityTestCase.case_key)
        if limit is not None:
            query = query.limit(limit).offset(offset)
        return [tuple(row) for row in self._session.execute(query).all()], total

    def contexts_for_results(self, result_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, list[RetrievedContext]]:
        grouped: dict[uuid.UUID, list[RetrievedContext]] = {i: [] for i in result_ids}
        if not result_ids:
            return grouped
        rows = self._session.scalars(
            select(RetrievedContext)
            .where(RetrievedContext.security_test_result_id.in_(result_ids))
            .order_by(RetrievedContext.security_test_result_id, RetrievedContext.rank)
        )
        for row in rows:
            grouped[row.security_test_result_id].append(row)
        return grouped

    # -------------------------------------------------------------------------- sandbox
    def create_sandbox_user(self, run_id: uuid.UUID, role: str) -> User:
        user = User(email=sandbox_email(run_id, role), password_hash=_UNUSABLE_PASSWORD_HASH, is_active=False)
        self._session.add(user)
        self._session.flush()
        return user

    def add_sandbox_document(self, user_id: uuid.UUID, filename: str, content: bytes, ingested: IngestionResult) -> Document:
        document = Document(
            user_id=user_id,
            filename=filename,
            content_type="text/plain",
            size_bytes=len(content),
            content_hash=hashlib.sha256(content).hexdigest(),
            storage_path=f"sandbox://{filename}",
            status="ready",
            processing_config=ingested.processing_config,
        )
        self._session.add(document)
        self._session.flush()
        ChunkRepository(self._session).replace_chunks(
            user_id=user_id, document_id=document.id, chunks=ingested.chunks, embedding_model=ingested.embedding_model
        )
        return document

    def delete_sandbox_users(self, run_id: uuid.UUID | None = None) -> int:
        """Xóa user sandbox (tài liệu và chunk xóa theo). Bản chụp đoạn lấy về trong kết quả vẫn được giữ."""
        pattern = f"security-{run_id}-%@{SANDBOX_EMAIL_DOMAIN}" if run_id else f"security-%@{SANDBOX_EMAIL_DOMAIN}"
        return self._session.execute(delete(User).where(User.email.like(pattern))).rowcount

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
