import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status

from app.api.dependencies import get_current_user, get_evaluation_run_service, get_evaluation_service
from app.models.evaluation import EvaluationRun, MetricResult
from app.models.user import User
from app.schemas.evaluation import (
    EvaluationCreate,
    EvaluationResultListResponse,
    EvaluationResultResponse,
    EvaluationRunListResponse,
    EvaluationRunResponse,
    MetricResponse,
    ResultContextResponse,
)
from app.services.evaluation_service import EvaluationRunService, EvaluationService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

RunStatus = Literal["pending", "running", "completed", "failed"]
_SNIPPET = 300


def _metric(metric: MetricResult) -> MetricResponse:
    return MetricResponse(
        metric_name=metric.metric_name, k=metric.k, value=metric.value, method=metric.method, status=metric.status, details=metric.details
    )


def _run(run: EvaluationRun, aggregates: list[MetricResult]) -> EvaluationRunResponse:
    return EvaluationRunResponse(
        id=run.id,
        status=run.status,
        dataset_version_id=run.dataset_version_id,
        model_configuration_id=run.model_configuration_id,
        judge_model=run.judge_model,
        judge_prompt_version=run.judge_prompt_version,
        total_cases=run.total_cases,
        completed_cases=run.completed_cases,
        failed_cases=run.failed_cases,
        categories=run.categories or {},
        aggregate_metrics=[_metric(m) for m in aggregates],
        environment=run.environment or {},
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
    )


@router.post("", response_model=EvaluationRunResponse, status_code=status.HTTP_202_ACCEPTED)
def create_evaluation(
    payload: EvaluationCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    service: EvaluationService = Depends(get_evaluation_service),
    runner: EvaluationRunService = Depends(get_evaluation_run_service),
) -> EvaluationRunResponse:
    run = service.create_run(user, payload)
    background_tasks.add_task(runner.execute, run.id)
    return _run(run, [])


@router.get("", response_model=EvaluationRunListResponse)
def list_evaluations(
    status_filter: RunStatus | None = Query(default=None, alias="status"),
    dataset_version_id: uuid.UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRunListResponse:
    runs, total = service.list_runs(user, status=status_filter, dataset_version_id=dataset_version_id, limit=limit, offset=offset)
    return EvaluationRunListResponse(items=[_run(r, service.aggregates(r)) for r in runs], total=total, limit=limit, offset=offset)


@router.get("/{run_id}", response_model=EvaluationRunResponse)
def get_evaluation(run_id: uuid.UUID, user: User = Depends(get_current_user), service: EvaluationService = Depends(get_evaluation_service)):
    run = service.get_run(user, run_id)
    return _run(run, service.aggregates(run))


@router.get("/{run_id}/results", response_model=EvaluationResultListResponse)
def list_results(
    run_id: uuid.UUID,
    status_filter: Literal["ok", "error"] | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationResultListResponse:
    rows, total, metrics, contexts = service.results(user, run_id, status=status_filter, category=category, limit=limit, offset=offset)
    items = []
    for result, case in rows:
        result_metrics = metrics.get(result.id, [])
        precision = next((m for m in result_metrics if m.metric_name == "precision_at_k"), None)
        relevant_ranks = set(precision.details.get("relevant_ranks", [])) if precision else None
        items.append(
            EvaluationResultResponse(
                id=result.id,
                test_case_id=case.id,
                question=case.question,
                expected_behavior=case.expected_behavior,
                ground_truth_answer=case.ground_truth_answer,
                status=result.status,
                category=result.category,
                answer=result.answer,
                insufficient_context=result.insufficient_context,
                mode=result.mode,
                error_message=result.error_message,
                latency_ms=result.latency_ms,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                estimated_cost=result.estimated_cost,
                metrics=[_metric(m) for m in result_metrics],
                contexts=[
                    ResultContextResponse(
                        rank=c.rank,
                        filename=c.document_filename_snapshot,
                        page_number=c.page_number,
                        score=round(c.score, 4),
                        snippet=c.content_snapshot[:_SNIPPET],
                        relevant=(c.rank in relevant_ranks) if relevant_ranks is not None else None,
                    )
                    for c in contexts.get(result.id, [])
                ],
            )
        )
    return EvaluationResultListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{run_id}/report")
def report(
    run_id: uuid.UUID,
    format: Literal["csv"] = "csv",
    user: User = Depends(get_current_user),
    service: EvaluationService = Depends(get_evaluation_service),
) -> Response:
    run, content = service.report_csv(user, run_id)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="evaluation-{run.id}.csv"'},
    )
