"""Retrieval: query Pinecone with optional temporal filtering.

Public API:
    search(query, period, year_range, top_k) -> list[dict]
"""

from __future__ import annotations

from typing import Any

from pinecone import Pinecone

from chronicle.config import settings

# ---------------------------------------------------------------------------
# Lazy singleton
# ---------------------------------------------------------------------------

_pinecone_client: Pinecone | None = None
_index: Any = None


def _get_index() -> Any:
    global _pinecone_client, _index
    if _index is None:
        _pinecone_client = Pinecone(api_key=settings.pinecone_api_key)
        _index = _pinecone_client.Index(settings.pinecone_index)
    return _index


# ---------------------------------------------------------------------------
# Filter builder
# ---------------------------------------------------------------------------


def _build_filter(
    period: str | None,
    year_range: tuple[int, int] | None,
) -> dict | None:
    """Construct a Pinecone metadata filter from optional temporal constraints.

    - period only  → {"period": {"$eq": period}}
    - year_range only → {"year": {"$gte": start, "$lte": end}}
    - both → {"$and": [...]}
    - neither → None
    """
    clauses: list[dict] = []

    if period is not None:
        clauses.append({"period": {"$eq": period}})

    if year_range is not None:
        start, end = year_range
        clauses.append({"year": {"$gte": start, "$lte": end}})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


# ---------------------------------------------------------------------------
# Public search function
# ---------------------------------------------------------------------------


def search(
    query: str,
    period: str | None = None,
    year_range: tuple[int, int] | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Embed *query* and retrieve the top-k matching chunks from Pinecone.

    Args:
        query: Natural-language question or keyword string.
        period: Optional period label to restrict results. One of:
            "early", "transitional", "mature", "late".
        year_range: Optional (start_year, end_year) inclusive filter.
        top_k: Number of results to return.

    Returns:
        List of dicts with keys: text, work, year, period, chunk_index, score.
    """
    index = _get_index()

    # Embed the query — input_type="query" lets Pinecone prepend the correct
    # prefix internally; do NOT add "query: " manually.
    assert _pinecone_client is not None  # guaranteed by _get_index()
    response = _pinecone_client.inference.embed(
        model=settings.embedding_model,
        inputs=[query],
        parameters={"input_type": "query"},
    )
    query_vector: list[float] = response[0]["values"]

    metadata_filter = _build_filter(period, year_range)

    result = index.query(
        vector=query_vector,
        top_k=top_k,
        filter=metadata_filter,
        include_metadata=True,
    )

    return [
        {
            "text": match["metadata"]["text"],
            "work": match["metadata"]["work"],
            "year": int(match["metadata"]["year"]),
            "period": match["metadata"]["period"],
            "chunk_index": int(match["metadata"]["chunk_index"]),
            "score": float(match["score"]),
        }
        for match in result["matches"]
    ]
