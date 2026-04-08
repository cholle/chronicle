"""Generation: build a grounded prompt and call Claude for an answer.

Public API:
    answer(query, period, year_range, top_k) -> dict
"""

from __future__ import annotations

import anthropic

from chronicle.config import settings
from chronicle.retrieve import search

# ---------------------------------------------------------------------------
# Lazy singleton
# ---------------------------------------------------------------------------

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_PREAMBLE = """\
You are a scholarly assistant. Answer the user's question using ONLY the \
passages provided below, which come from Marx's works. Cite every claim with \
the work title and year in parentheses, e.g. "(Capital, Volume I, 1867)". \
If the passages do not contain enough information to answer the question, say \
so explicitly — do not draw on outside knowledge of Marx.\
"""


def _build_prompt(query: str, chunks: list[dict]) -> str:
    """Build the full prompt string from a query and retrieved chunks.

    Raises:
        ValueError: if chunks is empty (answer() prevents this in practice).
    """
    if not chunks:
        raise ValueError("chunks must not be empty")

    passages = []
    for i, chunk in enumerate(chunks, start=1):
        passages.append(
            f"[Passage {i}] {chunk['work']} ({chunk['year']}, period: {chunk['period']})\n"
            f"{chunk['text']}"
        )

    passages_block = "\n\n".join(passages)
    return f"{_PREAMBLE}\n\n{passages_block}\n\nQuestion: {query}"


# ---------------------------------------------------------------------------
# Public answer function
# ---------------------------------------------------------------------------

_EMPTY_RESPONSE: dict = {
    "answer": "No relevant passages found in the corpus for this query and filter combination.",
    "citations": [],
    "chunks_used": 0,
}


def answer(
    query: str,
    period: str | None = None,
    year_range: tuple[int, int] | None = None,
    top_k: int = 5,
) -> dict:
    """Retrieve relevant chunks and generate a grounded answer via Claude.

    Args:
        query: Natural-language question.
        period: Optional period label to restrict retrieval.
        year_range: Optional (start_year, end_year) inclusive filter.
        top_k: Number of chunks to retrieve and pass to Claude.

    Returns:
        Dict with keys:
            answer (str): Claude's response.
            citations (list[dict]): The chunks passed to Claude.
            chunks_used (int): Number of chunks used.
    """
    chunks = search(query, period, year_range, top_k)

    if not chunks:
        return _EMPTY_RESPONSE

    prompt = _build_prompt(query, chunks)

    client = _get_client()
    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "answer": response.content[0].text,
        "citations": chunks,
        "chunks_used": len(chunks),
    }
