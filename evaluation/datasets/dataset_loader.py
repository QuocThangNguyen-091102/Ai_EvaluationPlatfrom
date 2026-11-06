"""Đọc và kiểm tra file import test case (CSV hoặc JSON). Không truy cập database.

JSON: một danh sách, hoặc {"test_cases": [...]}, mỗi phần tử:
    {"question", "ground_truth_answer", "question_type", "difficulty", "expected_behavior", "source_note",
     "reference_contexts": [{"filename": "...", "quote": "..."}]}

CSV (UTF-8, có dòng tiêu đề) các cột: question, ground_truth_answer, question_type, difficulty, expected_behavior,
source_note, reference_documents, reference_quotes. Nhiều tham chiếu thì ngăn bằng "||", hai cột phải khớp số lượng.
"""

import csv
import io
import json
from dataclasses import dataclass, field

QUESTION_TYPES = ("fact", "multi_hop", "summarization", "unanswerable")
DIFFICULTIES = ("easy", "medium", "hard")
EXPECTED_BEHAVIORS = ("answer", "insufficient_context")
MAX_ROWS = 1000
_SEPARATOR = "||"


@dataclass(frozen=True)
class ReferenceSpec:
    quote: str
    filename: str | None = None
    document_id: str | None = None


@dataclass(frozen=True)
class TestCaseSpec:
    row: int
    question: str
    ground_truth_answer: str | None
    question_type: str
    difficulty: str
    expected_behavior: str
    source_note: str | None
    references: list[ReferenceSpec] = field(default_factory=list)


@dataclass(frozen=True)
class RowError:
    row: int
    issue: str


def validate_spec(spec: TestCaseSpec) -> list[str]:
    """Các lỗi nội dung của một test case (dùng cho cả import và thêm từng câu)."""
    issues = []
    if not spec.question.strip():
        issues.append("Thiếu câu hỏi")
    if spec.question_type not in QUESTION_TYPES:
        issues.append(f"question_type phải là một trong {', '.join(QUESTION_TYPES)}")
    if spec.difficulty not in DIFFICULTIES:
        issues.append(f"difficulty phải là một trong {', '.join(DIFFICULTIES)}")
    if spec.expected_behavior not in EXPECTED_BEHAVIORS:
        issues.append(f"expected_behavior phải là một trong {', '.join(EXPECTED_BEHAVIORS)}")
    if spec.expected_behavior == "answer":
        if not spec.ground_truth_answer:
            issues.append("Câu cần trả lời phải có ground_truth_answer")
        if not spec.references:
            issues.append("Câu cần trả lời phải có ít nhất một reference context")
    if spec.expected_behavior == "insufficient_context" and spec.ground_truth_answer:
        issues.append("Câu không có đáp án trong tài liệu thì để trống ground_truth_answer")
    if (spec.question_type == "unanswerable") != (spec.expected_behavior == "insufficient_context"):
        issues.append("question_type 'unanswerable' phải đi cùng expected_behavior 'insufficient_context' và ngược lại")
    for reference in spec.references:
        if not reference.quote.strip():
            issues.append("Reference context có câu trích rỗng")
        if not reference.filename and not reference.document_id:
            issues.append("Reference context phải có filename hoặc document_id")
    return issues


def _clean(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _from_mapping(row: int, data: dict) -> TestCaseSpec:
    references = []
    for item in data.get("reference_contexts") or []:
        if not isinstance(item, dict):
            raise ValueError("reference_contexts phải là danh sách đối tượng")
        references.append(
            ReferenceSpec(quote=str(item.get("quote") or ""), filename=_clean(item.get("filename")), document_id=_clean(item.get("document_id")))
        )
    return TestCaseSpec(
        row=row,
        question=str(data.get("question") or "").strip(),
        ground_truth_answer=_clean(data.get("ground_truth_answer")),
        question_type=str(data.get("question_type") or "").strip(),
        difficulty=str(data.get("difficulty") or "").strip(),
        expected_behavior=str(data.get("expected_behavior") or "").strip(),
        source_note=_clean(data.get("source_note")),
        references=references,
    )


def _parse_json(text: str) -> list[dict]:
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("test_cases")
    if not isinstance(data, list):
        raise ValueError("JSON phải là danh sách test case hoặc {\"test_cases\": [...]}")
    return data


def _parse_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    required = {"question", "question_type", "difficulty", "expected_behavior"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"CSV thiếu cột: {', '.join(sorted(missing))}")
    rows = []
    for record in reader:
        documents = [d.strip() for d in (record.get("reference_documents") or "").split(_SEPARATOR) if d.strip()]
        quotes = [q.strip() for q in (record.get("reference_quotes") or "").split(_SEPARATOR) if q.strip()]
        if len(documents) != len(quotes):
            raise ValueError(f"Dòng {reader.line_num}: số reference_documents và reference_quotes không khớp")
        record["reference_contexts"] = [{"filename": d, "quote": q} for d, q in zip(documents, quotes)]
        rows.append(record)
    return rows


def load_test_cases(filename: str, content: bytes) -> tuple[list[TestCaseSpec], list[RowError]]:
    """Trả (các test case hợp lệ về hình thức, các lỗi theo dòng). Lỗi cấu trúc toàn file thì ném ValueError."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("File import phải mã hóa UTF-8") from None
    lowered = filename.lower()
    if lowered.endswith(".json"):
        try:
            records = _parse_json(text)
        except json.JSONDecodeError as error:
            raise ValueError(f"JSON không hợp lệ ở dòng {error.lineno}") from None
    elif lowered.endswith(".csv"):
        records = _parse_csv(text)
    else:
        raise ValueError("Chỉ nhận file .csv hoặc .json")
    if not records:
        raise ValueError("File không có test case nào")
    if len(records) > MAX_ROWS:
        raise ValueError(f"Tối đa {MAX_ROWS} test case mỗi lần import")

    specs, errors = [], []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append(RowError(index, "Mỗi test case phải là một đối tượng"))
            continue
        try:
            spec = _from_mapping(index, record)
        except ValueError as error:
            errors.append(RowError(index, str(error)))
            continue
        issues = validate_spec(spec)
        if issues:
            errors.extend(RowError(index, issue) for issue in issues)
        else:
            specs.append(spec)
    return specs, errors
