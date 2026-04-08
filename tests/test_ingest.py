"""Smoke tests for ingest.py — no Pinecone calls."""

from chronicle.ingest import chunk_text, clean_text


def test_clean_strips_page_numbers():
    raw = "Some text here.\n42\nMore text follows."
    result = clean_text(raw)
    assert "42" not in result.split()
    assert "Some text here." in result
    assert "More text follows." in result


def test_clean_joins_broken_lines():
    # Lines without terminal punctuation should be joined.
    raw = "This is a line that\ncontinues here. End of sentence."
    result = clean_text(raw)
    assert "line that continues here" in result


def test_clean_preserves_paragraph_breaks():
    raw = "First paragraph ends here.\n\nSecond paragraph starts here."
    result = clean_text(raw)
    assert "\n\n" in result


def test_chunk_count_short_text():
    # A short text should produce exactly one chunk.
    text = "This is a short paragraph. " * 10
    chunks = chunk_text(text)
    assert len(chunks) == 1


def test_chunk_count_long_text():
    # Enough text to force multiple chunks (~400 tokens each).
    # Each sentence is ~10 tokens; 200 sentences ≈ 2000 tokens → ~5 chunks.
    sentence = "The worker becomes poorer the more wealth he produces. "
    text = sentence * 150
    chunks = chunk_text(text)
    assert len(chunks) >= 3


def test_chunk_overlap():
    # The last units of chunk N should appear at the start of chunk N+1.
    sentence = "Labour produces not only commodities. "
    text = (sentence * 60 + "\n\n") * 8
    chunks = chunk_text(text)
    assert len(chunks) >= 2
    # Overlap: some text from the end of chunk 0 should appear in chunk 1.
    end_of_first = chunks[0].split()[-10:]
    start_of_second = chunks[1]
    assert any(word in start_of_second for word in end_of_first)


def test_chunk_hard_ceiling():
    # A single very long paragraph (>450 tokens) must still be chunked.
    long_sentence = "The alienation of the worker in his product means not only that his labour becomes an object. "
    giant_para = long_sentence * 60  # well over 450 tokens, no double newline
    chunks = chunk_text(giant_para)
    assert len(chunks) >= 2
