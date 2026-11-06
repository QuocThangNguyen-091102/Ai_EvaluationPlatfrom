import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status

from app.api.dependencies import get_benchmark_run_service, get_benchmark_service, get_current_user
from app.api.routes.evaluations import _metric
from app.models.benchmark import BenchmarkRun
from app.models.user import User
from app.schemas.benchmark import BenchmarkCreate, BenchmarkListResponse, BenchmarkResponse, BenchmarkVariantResponse
from app.services.benchmark_service import BenchmarkRunService, BenchmarkService

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


def _benchmark(benchmark: BenchmarkRun, variants: list[dict]) -> BenchmarkResponse:
    return BenchmarkResponse(
        id=benchmark.id,
        name=benchmark.name,
        dataset_version_id=benchmark.dataset_version_id,
        varied_variable=benchmark.varied_variable,
        status=benchmark.status,
        judge_model=benchmark.judge_model,
        notes=benchmark.notes or [],
        error_message=benchmark.error_message,
        started_at=benchmark.started_at,
        finished_at=benchmark.finished_at,
        created_at=benchmark.created_at,
        variants=[
            BenchmarkVariantResponse(**{**variant, "aggregate_metrics": [_metric(m) for m in variant["aggregate_metrics"]]})
            for variant in variants
        ],
    )


@router.post("", response_model=BenchmarkResponse, status_code=status.HTTP_202_ACCEPTED)
def create_benchmark(
    payload: BenchmarkCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    service: BenchmarkService = Depends(get_benchmark_service),
    runner: BenchmarkRunService = Depends(get_benchmark_run_service),
) -> BenchmarkResponse:
    benchmark, run_ids = service.create(user, payload)
    background_tasks.add_task(runner.execute, benchmark.id, run_ids)
    return _benchmark(benchmark, service.variants(benchmark))


@router.get("", response_model=BenchmarkListResponse)
def list_benchmarks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    service: BenchmarkService = Depends(get_benchmark_service),
) -> BenchmarkListResponse:
    items, total = service.list_benchmarks(user, limit=limit, offset=offset)
    return BenchmarkListResponse(items=[_benchmark(b, service.variants(b)) for b in items], total=total, limit=limit, offset=offset)


@router.get("/{benchmark_id}", response_model=BenchmarkResponse)
def get_benchmark(
    benchmark_id: uuid.UUID, user: User = Depends(get_current_user), service: BenchmarkService = Depends(get_benchmark_service)
) -> BenchmarkResponse:
    benchmark = service.get(user, benchmark_id)
    return _benchmark(benchmark, service.variants(benchmark))


@router.get("/{benchmark_id}/report")
def report(
    benchmark_id: uuid.UUID,
    format: Literal["csv"] = "csv",
    user: User = Depends(get_current_user),
    service: BenchmarkService = Depends(get_benchmark_service),
) -> Response:
    benchmark, content = service.report_csv(user, benchmark_id)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="benchmark-{benchmark.id}.csv"'},
    )
