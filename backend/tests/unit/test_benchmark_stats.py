from decimal import Decimal

import pytest

from evaluation.benchmarks.benchmark_runner import ResultUsage, config_differences, percentile, usage_stats

BASE = {"llm_provider": "p", "llm_model": "a", "top_k": 5, "prompt_version": "rag-v1", "temperature": 0.0, "embedding_model": "e", "chunk_size": 250, "chunk_overlap": 50}


def test_percentile_uses_nearest_rank_so_value_is_a_real_observation():
    values = [10, 20, 30, 40, 1000]

    assert percentile(values, 50) == 30
    assert percentile(values, 95) == 1000
    assert percentile([], 50) is None


def test_usage_ignores_error_cases_and_flags_unknown_cost():
    stats = usage_stats(
        [
            ResultUsage(100, 50, 10, Decimal("0.001"), "ok"),
            ResultUsage(300, 70, 20, None, "ok"),
            ResultUsage(None, None, None, None, "error"),
        ]
    )

    assert stats.cases == 2
    assert stats.latency_mean_ms == 200
    assert (stats.prompt_tokens, stats.completion_tokens) == (120, 30)
    assert stats.total_cost == Decimal("0.001")
    assert stats.cost_incomplete is True


def test_no_token_data_stays_unknown_not_zero():
    stats = usage_stats([ResultUsage(5, None, None, Decimal(0), "ok")])

    assert stats.prompt_tokens is None
    assert stats.total_cost == Decimal(0) and stats.cost_incomplete is False


def test_config_differences_detects_single_and_extra_variables():
    assert config_differences([BASE, {**BASE, "top_k": 3}], "top_k") == (True, [])
    assert config_differences([BASE, {**BASE, "top_k": 3, "temperature": 0.7}], "top_k") == (True, ["temperature"])
    assert config_differences([BASE, {**BASE, "llm_model": "b", "llm_provider": "q"}], "llm_model") == (True, [])
    assert config_differences([BASE, {**BASE, "temperature": 0.5}], "top_k")[0] is False


def test_unknown_variable_is_rejected():
    with pytest.raises(ValueError):
        config_differences([BASE, BASE], "temperature")
