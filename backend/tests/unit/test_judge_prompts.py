import pytest

from ai_engine.generation.prompt_templates import INSUFFICIENT_CONTEXT_ANSWER
from evaluation.evaluators.judge_prompts import (
    DEFAULT_JUDGE_PROMPT_VERSION,
    JUDGE_PROMPT_VERSIONS,
    faithfulness_messages,
    policy_messages,
    relevancy_messages,
)


def test_refusal_aware_is_the_default_and_both_versions_are_available():
    assert DEFAULT_JUDGE_PROMPT_VERSION == "judge-refusal-aware"
    assert set(JUDGE_PROMPT_VERSIONS) == {"judge-strict-json", "judge-refusal-aware"}


def test_refusal_aware_policy_prompt_names_the_standard_refusal_and_document_facts():
    system = policy_messages("judge-refusal-aware", "tiêu chí", "yêu cầu", "trả lời")[0].content

    assert INSUFFICIENT_CONTEXT_ANSWER in system
    assert "nội dung" in system and "tài liệu" in system
    assert '{"violated": false, "reason": "..."}' in system  # JSON mẫu không bị hỏng khi dựng f-string


def test_strict_json_policy_prompt_is_unchanged_so_old_runs_stay_reproducible():
    system = policy_messages("judge-strict-json", "t", "y", "c")[0].content

    assert INSUFFICIENT_CONTEXT_ANSWER not in system


def test_quality_prompts_are_identical_across_versions():
    assert faithfulness_messages("judge-strict-json", "a", ["c"]) == faithfulness_messages("judge-refusal-aware", "a", ["c"])
    assert relevancy_messages("judge-strict-json", "q", "a") == relevancy_messages("judge-refusal-aware", "q", "a")


def test_unknown_version_is_rejected():
    with pytest.raises(ValueError):
        policy_messages("judge-unknown", "t", "y", "c")
