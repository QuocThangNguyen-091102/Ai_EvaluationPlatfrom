"""So sánh các lượt đánh giá trong một benchmark (hàm thuần, không truy cập DB).

Benchmark chỉ có ý nghĩa khi các lượt chạy trên CÙNG phiên bản dataset và các cấu hình chỉ khác nhau ở MỘT biến.
`config_differences` phát hiện cấu hình khác nhau ở nhiều biến để service cảnh báo.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

VARIED_VARIABLES = ("llm_model", "top_k", "prompt_version")
# Các trường của cấu hình có thể ảnh hưởng tới kết quả; llm_provider đi kèm llm_model.
COMPARED_FIELDS = ("llm_provider", "llm_model", "top_k", "prompt_version", "temperature", "embedding_model", "chunk_size", "chunk_overlap")


@dataclass(frozen=True)
class ResultUsage:
    latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    estimated_cost: Decimal | None
    status: str


@dataclass(frozen=True)
class UsageStats:
    cases: int
    latency_mean_ms: float | None
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_cost: Decimal | None
    # True khi có câu thiếu giá hoặc thiếu số token: tổng chỉ là một phần, không phải số đầy đủ.
    cost_incomplete: bool
    tokens_incomplete: bool

    def as_dict(self) -> dict:
        return {
            "cases": self.cases,
            "latency_mean_ms": self.latency_mean_ms,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_cost": str(self.total_cost) if self.total_cost is not None else None,
            "cost_incomplete": self.cost_incomplete,
            "tokens_incomplete": self.tokens_incomplete,
        }


def percentile(values: Sequence[float], q: float) -> float | None:
    """Percentile theo nearest-rank (không nội suy): luôn là một giá trị đo được thật."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(q / 100 * len(ordered)))
    return float(ordered[rank - 1])


def usage_stats(results: Sequence[ResultUsage]) -> UsageStats:
    answered = [r for r in results if r.status == "ok"]
    latencies = [r.latency_ms for r in answered if r.latency_ms is not None]
    prompt = [r.prompt_tokens for r in answered]
    completion = [r.completion_tokens for r in answered]
    costs = [r.estimated_cost for r in answered]
    known_prompt = [t for t in prompt if t is not None]
    known_completion = [t for t in completion if t is not None]
    known_costs = [c for c in costs if c is not None]
    return UsageStats(
        cases=len(answered),
        latency_mean_ms=round(sum(latencies) / len(latencies), 1) if latencies else None,
        latency_p50_ms=percentile(latencies, 50),
        latency_p95_ms=percentile(latencies, 95),
        prompt_tokens=sum(known_prompt) if known_prompt else None,
        completion_tokens=sum(known_completion) if known_completion else None,
        total_cost=sum(known_costs, Decimal(0)) if known_costs else None,
        cost_incomplete=len(known_costs) < len(costs),
        tokens_incomplete=len(known_prompt) < len(prompt) and bool(known_prompt),
    )


def config_differences(configs: Sequence[Mapping], varied_variable: str) -> tuple[bool, list[str]]:
    """Trả (biến khai báo có thực sự khác giữa các cấu hình không, danh sách biến KHÁC cũng thay đổi)."""
    if varied_variable not in VARIED_VARIABLES:
        raise ValueError(f"varied_variable phải là một trong {VARIED_VARIABLES}")
    varied_values = [config[varied_variable] for config in configs]
    varies = len(set(varied_values)) == len(varied_values)
    others = [
        field
        for field in COMPARED_FIELDS
        if field != varied_variable
        and not (field == "llm_provider" and varied_variable == "llm_model")
        and len({config[field] for config in configs}) > 1
    ]
    return varies, others
