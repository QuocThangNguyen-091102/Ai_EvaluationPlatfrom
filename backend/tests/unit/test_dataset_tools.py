import json
import unicodedata

import pytest

from evaluation.datasets.dataset_loader import load_test_cases
from evaluation.datasets.reference_locator import (
    AmbiguousQuoteError,
    ChunkSpan,
    QuoteNotFoundError,
    locate_quote,
    rebuild_text,
)

FULL = "Quy định nộp hồ sơ\nHồ sơ xin cấp giấy phép phải được nộp trong vòng 30 ngày.\n\nPhí và lệ phí: không thu năm đầu."


def _chunks(text: str, size: int) -> list[ChunkSpan]:
    """Chia theo ký tự (đủ cho test vị trí); các chunk chồng nhau 5 ký tự."""
    spans, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        spans.append(ChunkSpan(start, end, text[start:end]))
        if end == len(text):
            break
        start = end - 5
    return spans


# --------------------------------------------------------------------------------- locate
def test_rebuild_text_restores_the_original_from_overlapping_chunks():
    assert rebuild_text(_chunks(FULL, 20)) == FULL


def test_quote_is_found_and_offsets_point_into_the_document():
    start, end, found = locate_quote(_chunks(FULL, 20), "phải được nộp trong vòng 30 ngày")

    assert FULL[start:end] == found == "phải được nộp trong vòng 30 ngày"


def test_quote_with_different_whitespace_and_line_breaks_still_matches():
    start, end, found = locate_quote(_chunks(FULL, 25), "Quy định   nộp hồ sơ Hồ sơ xin")

    assert found == "Quy định nộp hồ sơ\nHồ sơ xin"
    assert FULL[start:end] == found


def test_quote_in_decomposed_unicode_matches():
    decomposed = unicodedata.normalize("NFD", "giấy phép")

    assert locate_quote(_chunks(FULL, 30), decomposed)[2] == "giấy phép"


def test_quote_spanning_a_page_break_matches():
    assert locate_quote(_chunks(FULL, 40), "30 ngày. Phí và lệ phí")[2] == "30 ngày.\n\nPhí và lệ phí"


def test_missing_quote_is_reported():
    with pytest.raises(QuoteNotFoundError):
        locate_quote(_chunks(FULL, 20), "nội dung không có trong tài liệu")


def test_ambiguous_quote_is_reported():
    with pytest.raises(AmbiguousQuoteError):
        locate_quote(_chunks(FULL, 20), "nộp")  # "nộp hồ sơ" và "được nộp"


def test_gaps_between_non_overlapping_chunks_are_treated_as_whitespace():
    text = "một hai ba bốn"
    spans = [ChunkSpan(0, 7, "một hai"), ChunkSpan(8, 14, "ba bốn")]

    assert locate_quote(spans, "hai ba")[2] == "hai ba"


# --------------------------------------------------------------------------------- loader
def _json(cases) -> bytes:
    return json.dumps(cases, ensure_ascii=False).encode("utf-8")


GOOD = {
    "question": "Hạn nộp hồ sơ?",
    "ground_truth_answer": "30 ngày",
    "question_type": "fact",
    "difficulty": "easy",
    "expected_behavior": "answer",
    "reference_contexts": [{"filename": "quy-dinh.pdf", "quote": "trong vòng 30 ngày"}],
}
UNANSWERABLE = {
    "question": "Lương giám đốc?",
    "ground_truth_answer": None,
    "question_type": "unanswerable",
    "difficulty": "medium",
    "expected_behavior": "insufficient_context",
}


def test_json_list_and_wrapped_object_are_both_accepted():
    specs, errors = load_test_cases("a.json", _json([GOOD, UNANSWERABLE]))
    wrapped, _ = load_test_cases("a.json", _json({"test_cases": [GOOD]}))

    assert errors == []
    assert [s.row for s in specs] == [1, 2]
    assert specs[0].references[0].filename == "quy-dinh.pdf"
    assert len(wrapped) == 1


def test_csv_with_multiple_references_is_parsed():
    csv_text = (
        "question,ground_truth_answer,question_type,difficulty,expected_behavior,source_note,reference_documents,reference_quotes\n"
        'Hạn và phí?,30 ngày và miễn phí,multi_hop,hard,answer,,a.pdf||b.pdf,trong vòng 30 ngày||không thu năm đầu\n'
    )

    specs, errors = load_test_cases("a.csv", csv_text.encode("utf-8"))

    assert errors == []
    assert [(r.filename, r.quote) for r in specs[0].references] == [("a.pdf", "trong vòng 30 ngày"), ("b.pdf", "không thu năm đầu")]


@pytest.mark.parametrize(
    "change, fragment",
    [
        ({"question": ""}, "Thiếu câu hỏi"),
        ({"question_type": "khac"}, "question_type"),
        ({"difficulty": "rat-kho"}, "difficulty"),
        ({"ground_truth_answer": None}, "ground_truth_answer"),
        ({"reference_contexts": []}, "reference context"),
        ({"question_type": "unanswerable"}, "unanswerable"),
        ({"reference_contexts": [{"quote": "x"}]}, "filename hoặc document_id"),
    ],
)
def test_invalid_cases_are_reported_by_row(change, fragment):
    _, errors = load_test_cases("a.json", _json([GOOD, {**GOOD, **change}]))

    assert errors and all(e.row == 2 for e in errors)
    assert any(fragment in e.issue for e in errors)


def test_unanswerable_case_must_not_carry_an_answer():
    _, errors = load_test_cases("a.json", _json([{**UNANSWERABLE, "ground_truth_answer": "bịa"}]))

    assert any("để trống ground_truth_answer" in e.issue for e in errors)


@pytest.mark.parametrize(
    "filename, content, fragment",
    [
        ("a.txt", b"x", ".csv hoặc .json"),
        ("a.json", b"{khong hop le", "JSON"),
        ("a.json", b"[]", "không có test case"),
        ("a.csv", b"question,difficulty\nx,easy\n", "thiếu cột"),
        ("a.json", "Viêt".encode("cp1258"), "UTF-8"),
    ],
)
def test_structurally_broken_files_are_rejected(filename, content, fragment):
    with pytest.raises(ValueError, match=fragment):
        load_test_cases(filename, content)


def test_row_limit():
    with pytest.raises(ValueError, match="Tối đa"):
        load_test_cases("a.json", _json([GOOD] * 1001))
