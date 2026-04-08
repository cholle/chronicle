"""Unit tests for chronicle.generate._build_prompt.

No live Anthropic calls are made.
"""

import pytest

from chronicle.generate import _build_prompt


CHUNK_A = {
    "text": "The history of all hitherto existing society is the history of class struggles.",
    "work": "The Communist Manifesto",
    "year": 1848,
    "period": "early",
    "chunk_index": 0,
    "score": 0.95,
}

CHUNK_B = {
    "text": "Capital is dead labour, that, vampire-like, only lives by sucking living labour.",
    "work": "Capital, Volume I",
    "year": 1867,
    "period": "mature",
    "chunk_index": 3,
    "score": 0.88,
}


def test_build_prompt_empty_chunks_raises():
    with pytest.raises(ValueError):
        _build_prompt("What is class struggle?", [])


def test_build_prompt_single_chunk_contains_metadata():
    prompt = _build_prompt("What is class struggle?", [CHUNK_A])
    assert CHUNK_A["work"] in prompt
    assert str(CHUNK_A["year"]) in prompt
    assert CHUNK_A["text"] in prompt


def test_build_prompt_multiple_chunks_numbered_and_query_at_end():
    query = "How does Marx describe capital?"
    prompt = _build_prompt(query, [CHUNK_A, CHUNK_B])

    assert "[Passage 1]" in prompt
    assert "[Passage 2]" in prompt

    # Both works present
    assert CHUNK_A["work"] in prompt
    assert CHUNK_B["work"] in prompt

    # Query appears after the passages
    passage_2_pos = prompt.index("[Passage 2]")
    query_pos = prompt.index(query)
    assert query_pos > passage_2_pos
