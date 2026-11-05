import pytest

from ai_engine.chunking.fixed_size_chunker import chunk_document, full_text
from ai_engine.ingestion.parsed_document import ParsedDocument, ParsedPage


def _doc(*pages: tuple[str, int | None]) -> ParsedDocument:
    return ParsedDocument(pages=[ParsedPage(text=text, page_number=number) for text, number in pages])


def _words(n: int, start: int = 0) -> str:
    return " ".join(f"w{i}" for i in range(start, start + n))


def test_short_document_becomes_a_single_chunk():
    chunks = chunk_document(_doc(("một hai ba", None)), chunk_size=10, overlap=2)

    assert len(chunks) == 1
    assert chunks[0].content == "một hai ba"
    assert chunks[0].word_count == 3


def test_chunks_have_the_configured_size_except_possibly_the_last():
    chunks = chunk_document(_doc((_words(105), None)), chunk_size=50, overlap=10)

    assert [c.word_count for c in chunks] == [50, 50, 25]


def test_consecutive_chunks_share_exactly_the_configured_overlap():
    chunks = chunk_document(_doc((_words(120), None)), chunk_size=40, overlap=8)

    for previous, current in zip(chunks, chunks[1:]):
        assert previous.content.split()[-8:] == current.content.split()[:8]


def test_zero_overlap_chunks_do_not_share_words():
    chunks = chunk_document(_doc((_words(30), None)), chunk_size=10, overlap=0)

    assert [c.content for c in chunks] == [_words(10, 0), _words(10, 10), _words(10, 20)]


def test_every_word_is_covered_by_at_least_one_chunk():
    chunks = chunk_document(_doc((_words(97), None)), chunk_size=30, overlap=7)

    seen = {word for chunk in chunks for word in chunk.content.split()}

    assert seen == set(_words(97).split())


def test_last_chunk_always_contains_new_words():
    # Phòng trường hợp chunk cuối chỉ lặp lại phần overlap của chunk trước.
    for n in range(1, 60):
        chunks = chunk_document(_doc((_words(n), None)), chunk_size=10, overlap=4)
        if len(chunks) > 1:
            assert chunks[-1].char_end > chunks[-2].char_end


def test_char_offsets_point_back_into_the_full_text():
    document = _doc(("Trang một có vài từ\nxuống dòng", 1), ("Trang hai cũng vậy", 2))
    text = full_text(document)

    for chunk in chunk_document(document, chunk_size=4, overlap=1):
        assert text[chunk.char_start : chunk.char_end] == chunk.content


def test_page_number_is_the_page_of_the_first_word():
    document = _doc((_words(6), 1), (_words(6, 100), 2))

    chunks = chunk_document(document, chunk_size=4, overlap=0)

    assert [c.page_number for c in chunks] == [1, 1, 2]
    # Chunk thứ hai bắt đầu ở trang 1 nhưng kéo sang trang 2: vẫn tính trang đầu.
    assert "w100" in chunks[1].content


def test_documents_without_pages_have_no_page_number():
    chunks = chunk_document(_doc((_words(5), None)), chunk_size=3, overlap=0)

    assert all(c.page_number is None for c in chunks)


def test_chunk_indexes_are_sequential_from_zero():
    chunks = chunk_document(_doc((_words(50), None)), chunk_size=10, overlap=2)

    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_chunking_is_deterministic():
    document = _doc((_words(77), 1))

    assert chunk_document(document, chunk_size=20, overlap=5) == chunk_document(document, chunk_size=20, overlap=5)


def test_original_line_breaks_inside_a_chunk_are_preserved():
    chunks = chunk_document(_doc(("dòng một\ndòng hai", None)), chunk_size=10, overlap=0)

    assert chunks[0].content == "dòng một\ndòng hai"


def test_empty_document_has_no_chunks():
    assert chunk_document(ParsedDocument(pages=[]), chunk_size=10, overlap=2) == []


@pytest.mark.parametrize(
    "chunk_size, overlap",
    [(0, 0), (-5, 0), (10, -1), (10, 10), (10, 11)],
)
def test_invalid_size_or_overlap_is_rejected(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_document(_doc(("a b c", None)), chunk_size=chunk_size, overlap=overlap)


def test_real_vietnamese_pdf_flows_through_parse_clean_and_chunk():
    from pathlib import Path

    from ai_engine.ingestion.pdf_parser import parse_pdf
    from ai_engine.ingestion.text_cleaner import clean_document

    pdf = Path(__file__).resolve().parent.parent / "fixtures" / "vi_two_pages.pdf"
    document = clean_document(parse_pdf(pdf.read_bytes()))

    chunks = chunk_document(document, chunk_size=12, overlap=3)

    text = full_text(document)
    assert len(chunks) > 1
    assert chunks[0].page_number == 1
    assert chunks[-1].page_number == 2
    assert all(text[c.char_start : c.char_end] == c.content for c in chunks)
    assert any("giấy phép" in c.content for c in chunks)
