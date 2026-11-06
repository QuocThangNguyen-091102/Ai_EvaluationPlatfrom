import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status

from app.api.dependencies import get_current_user, get_security_run_service, get_security_service
from app.models.security_test import SecurityTestRun
from app.models.user import User
from app.schemas.security_test import (
    SecurityCategory,
    SecurityContextResponse,
    SecurityResultListResponse,
    SecurityResultResponse,
    SecurityRunCreate,
    SecurityRunListResponse,
    SecurityRunResponse,
    SecurityTestCaseListResponse,
    SecurityTestCaseResponse,
)
from app.services.security_service import SecurityRunService, SecurityService

router = APIRouter(prefix="/security", tags=["security"])

_SNIPPET = 300


def _run(run: SecurityTestRun) -> SecurityRunResponse:
    return SecurityRunResponse(
        id=run.id,
        status=run.status,
        model_configuration_id=run.model_configuration_id,
        categories=run.categories or [],
        total_cases=run.total_cases,
        completed_cases=run.completed_cases,
        judge_model=run.judge_model,
        judge_prompt_version=run.judge_prompt_version,
        summary=run.summary or {},
        coverage_notes=run.coverage_notes or [],
        environment=run.environment or {},
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
    )


@router.get("/test-cases", response_model=SecurityTestCaseListResponse)
def list_test_cases(category: SecurityCategory | None = None, user: User = Depends(get_current_user)) -> SecurityTestCaseListResponse:
    return SecurityTestCaseListResponse(
        items=[
            SecurityTestCaseResponse(
                key=case.key,
                version=case.version,
                category=case.category,
                title=case.title,
                description=case.description,
                severity=case.severity,
                requires_llm=case.requires_llm,
                expected_behavior=case.expected_behavior,
                mitigation=case.mitigation,
                uses_judge=case.judge_criterion is not None,
            )
            for case in SecurityService.list_test_cases(category)
        ]
    )


@router.post("/runs", response_model=SecurityRunResponse, status_code=status.HTTP_202_ACCEPTED)
def create_run(
    payload: SecurityRunCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service),
    runner: SecurityRunService = Depends(get_security_run_service),
) -> SecurityRunResponse:
    run = service.create_run(user, payload)
    background_tasks.add_task(runner.execute, run.id)
    return _run(run)


@router.get("/runs", response_model=SecurityRunListResponse)
def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service),
) -> SecurityRunListResponse:
    runs, total = service.list_runs(user, limit=limit, offset=offset)
    return SecurityRunListResponse(items=[_run(r) for r in runs], total=total, limit=limit, offset=offset)


@router.get("/runs/{run_id}", response_model=SecurityRunResponse)
def get_run(run_id: uuid.UUID, user: User = Depends(get_current_user), service: SecurityService = Depends(get_security_service)):
    return _run(service.get_run(user, run_id))


@router.get("/runs/{run_id}/results", response_model=SecurityResultListResponse)
def list_results(
    run_id: uuid.UUID,
    status_filter: Literal["pass", "fail", "error", "skipped"] | None = Query(default=None, alias="status"),
    severity: Literal["critical", "high", "medium", "low"] | None = None,
    category: SecurityCategory | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service),
) -> SecurityResultListResponse:
    rows, total, contexts = service.results(user, run_id, status=status_filter, severity=severity, category=category, limit=limit, offset=offset)
    return SecurityResultListResponse(
        items=[
            SecurityResultResponse(
                id=result.id,
                test_case_id=case.id,
                case_key=case.case_key,
                category=case.category,
                title=case.title,
                description=case.description,
                expected_behavior=case.expected_behavior,
                status=result.status,
                severity=result.severity,
                actual_response=result.actual_response,
                evidence=result.evidence or {},
                evaluator=result.evaluator,
                mitigation=result.mitigation,
                error_message=result.error_message,
                latency_ms=result.latency_ms,
                contexts=[
                    SecurityContextResponse(rank=c.rank, filename=c.document_filename_snapshot, score=round(c.score, 4), snippet=c.content_snapshot[:_SNIPPET])
                    for c in contexts.get(result.id, [])
                ],
            )
            for result, case in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/runs/{run_id}/report")
def report(
    run_id: uuid.UUID,
    format: Literal["csv"] = "csv",
    user: User = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service),
) -> Response:
    run, content = service.report_csv(user, run_id)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="security-{run.id}.csv"'},
    )
