"""Nạp và kiểm tra test case bảo mật từ YAML (nguồn chuẩn nằm trong repo, DB chỉ lưu bản chụp).

Placeholder `{canary}`, `{canary_head}`, `{canary_tail}` được thay bằng chuỗi ngẫu nhiên mỗi lượt chạy (`materialize`),
để model không thể "nhớ" sẵn đáp án và để phát hiện rò rỉ bằng so khớp chuỗi.
"""

import hashlib
import json
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CATEGORIES = ("prompt_injection", "jailbreak", "data_leakage", "access_control", "malicious_documents")
SEVERITIES = ("critical", "high", "medium", "low")
OWNERS = ("attacker", "victim")
# own_documents: chỉ tài liệu của chính test case (mặc định, để các case không ảnh hưởng nhau);
# all_own_documents: mọi tài liệu của kẻ tấn công trong lượt; victim_documents: ID tài liệu của nạn nhân.
SCOPES = ("own_documents", "all_own_documents", "victim_documents")
RULE_KEYS = (
    "forbidden_in_answer",
    "forbidden_in_contexts",
    "forbidden_patterns",
    "forbid_system_prompt",
    "forbid_secrets",
    "require_insufficient_context",
    "max_contexts",
)
_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_KNOWN_PLACEHOLDERS = {"canary", "canary_head", "canary_tail"}
DEFAULT_CASES_DIR = Path(__file__).resolve().parent / "test_cases"


class TestCaseError(ValueError):
    """File test case sai định dạng; thông điệp nêu file và mã case."""

    __test__ = False  # không phải test của pytest


@dataclass(frozen=True)
class SetupDocument:
    owner: str
    filename: str
    text: str


@dataclass(frozen=True)
class SecurityCase:
    key: str
    version: int
    category: str
    title: str
    description: str
    severity: str
    requires_llm: bool
    documents: tuple[SetupDocument, ...]
    question: str
    scope: str
    expected_behavior: str
    rules: dict[str, Any]
    judge_criterion: str | None
    mitigation: str
    content_hash: str
    raw: dict = field(repr=False, compare=False)


@dataclass(frozen=True)
class Canary:
    value: str

    @property
    def head(self) -> str:
        return self.value[: len(self.value) // 2]

    @property
    def tail(self) -> str:
        return self.value[len(self.value) // 2 :]

    @classmethod
    def generate(cls) -> "Canary":
        return cls(f"CNRY{secrets.token_hex(5).upper()}")


def load_cases(directory: Path = DEFAULT_CASES_DIR, categories: tuple[str, ...] | None = None) -> list[SecurityCase]:
    cases: list[SecurityCase] = []
    for path in sorted(directory.glob("*.yaml")):
        cases.extend(_load_file(path))
    keys = [case.key for case in cases]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise TestCaseError(f"Mã test case bị trùng: {', '.join(duplicates)}")
    if categories:
        cases = [case for case in cases if case.category in categories]
    return cases


def _load_file(path: Path) -> list[SecurityCase]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise TestCaseError(f"{path.name}: YAML không hợp lệ ({error})") from None
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise TestCaseError(f"{path.name}: thiếu schema_version: 1")
    category = data.get("category")
    if category not in CATEGORIES:
        raise TestCaseError(f"{path.name}: category phải là một trong {CATEGORIES}")
    items = data.get("cases")
    if not isinstance(items, list) or not items:
        raise TestCaseError(f"{path.name}: cần ít nhất một test case")
    return [_parse_case(path.name, category, item) for item in items]


def _parse_case(filename: str, category: str, item: Any) -> SecurityCase:
    if not isinstance(item, dict):
        raise TestCaseError(f"{filename}: mỗi test case phải là một đối tượng")
    key = item.get("key")
    where = f"{filename} [{key}]"

    def need(name: str, kind: type) -> Any:
        value = item.get(name)
        if not isinstance(value, kind) or (isinstance(value, str) and not value.strip()):
            raise TestCaseError(f"{where}: thiếu hoặc sai kiểu trường '{name}'")
        return value

    if not isinstance(key, str) or not re.fullmatch(r"[A-Z]{2}-\d{2}", key):
        raise TestCaseError(f"{where}: key phải có dạng 'AB-01'")
    version = need("version", int)
    severity = need("severity", str)
    if severity not in SEVERITIES:
        raise TestCaseError(f"{where}: severity phải là một trong {SEVERITIES}")
    requires_llm = item.get("requires_llm")
    if not isinstance(requires_llm, bool):
        raise TestCaseError(f"{where}: requires_llm phải là true hoặc false")

    documents = []
    for doc in (item.get("setup") or {}).get("documents") or []:
        if not isinstance(doc, dict) or doc.get("owner") not in OWNERS:
            raise TestCaseError(f"{where}: tài liệu setup cần owner là attacker hoặc victim")
        if not isinstance(doc.get("filename"), str) or not isinstance(doc.get("text"), str) or not doc["text"].strip():
            raise TestCaseError(f"{where}: tài liệu setup cần filename và text")
        documents.append(SetupDocument(doc["owner"], doc["filename"], doc["text"]))

    payload = need("input", dict)
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        raise TestCaseError(f"{where}: input.question bắt buộc")
    scope = payload.get("scope", "own_documents")
    if scope not in SCOPES:
        raise TestCaseError(f"{where}: input.scope phải là một trong {SCOPES}")
    if scope == "own_documents" and not any(d.owner == "attacker" for d in documents):
        raise TestCaseError(f"{where}: scope own_documents cần ít nhất một tài liệu của attacker")
    if scope == "victim_documents" and not any(d.owner == "victim" for d in documents):
        raise TestCaseError(f"{where}: scope victim_documents cần ít nhất một tài liệu của victim")

    rules = need("rules", dict)
    unknown = set(rules) - set(RULE_KEYS)
    if unknown:
        raise TestCaseError(f"{where}: luật không hỗ trợ: {', '.join(sorted(unknown))}")
    for name in ("forbidden_in_answer", "forbidden_in_contexts", "forbidden_patterns"):
        if name in rules and (not isinstance(rules[name], list) or not all(isinstance(v, str) and v for v in rules[name])):
            raise TestCaseError(f"{where}: {name} phải là danh sách chuỗi")
    for pattern in rules.get("forbidden_patterns", []):
        try:
            re.compile(pattern)
        except re.error:
            raise TestCaseError(f"{where}: regex không hợp lệ: {pattern}") from None
    if "max_contexts" in rules and (not isinstance(rules["max_contexts"], int) or rules["max_contexts"] < 0):
        raise TestCaseError(f"{where}: max_contexts phải là số nguyên không âm")

    judge = item.get("judge")
    criterion = judge.get("criterion") if isinstance(judge, dict) else None
    if judge is not None and (not isinstance(criterion, str) or not criterion.strip()):
        raise TestCaseError(f"{where}: judge cần criterion")

    texts = [question, *(d.text for d in documents), *_strings(rules)]
    for text in texts:
        for name in _PLACEHOLDER.findall(text):
            if name not in _KNOWN_PLACEHOLDERS:
                raise TestCaseError(f"{where}: placeholder không hỗ trợ: {{{name}}}")

    return SecurityCase(
        key=key,
        version=version,
        category=category,
        title=need("title", str),
        description=need("description", str),
        severity=severity,
        requires_llm=requires_llm,
        documents=tuple(documents),
        question=question,
        scope=scope,
        expected_behavior=need("expected_behavior", str),
        rules=rules,
        judge_criterion=criterion,
        mitigation=need("mitigation", str),
        content_hash=hashlib.sha256(json.dumps(item, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(),
        raw=item,
    )


def parse_case(category: str, item: dict, *, source: str = "snapshot") -> SecurityCase:
    """Dựng lại test case từ bản chụp (cùng dữ liệu thì cùng content_hash)."""
    if category not in CATEGORIES:
        raise TestCaseError(f"{source}: category không hợp lệ")
    return _parse_case(source, category, item)


def _strings(rules: dict) -> list[str]:
    return [value for name in ("forbidden_in_answer", "forbidden_in_contexts") for value in rules.get(name, [])]


def substitute(text: str, canary: Canary) -> str:
    # Thay theo tên placeholder, không dùng str.format (regex trong luật có dấu ngoặc nhọn).
    values = {"canary": canary.value, "canary_head": canary.head, "canary_tail": canary.tail}
    return _PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), text)


def materialize(case: SecurityCase, canary: Canary) -> SecurityCase:
    """Bản test case đã thay placeholder bằng canary của lượt chạy."""
    rules = dict(case.rules)
    for name in ("forbidden_in_answer", "forbidden_in_contexts"):
        if name in rules:
            rules[name] = [substitute(value, canary) for value in rules[name]]
    return SecurityCase(
        **{
            **case.__dict__,
            "question": substitute(case.question, canary),
            "documents": tuple(SetupDocument(d.owner, d.filename, substitute(d.text, canary)) for d in case.documents),
            "rules": rules,
        }
    )
