"""Smoke tests for the retrieve module — no live Pinecone calls."""

from chronicle.retrieve import _build_filter


def test_build_filter_neither():
    assert _build_filter(None, None) is None


def test_build_filter_period_only():
    result = _build_filter("early", None)
    assert result == {"period": {"$eq": "early"}}


def test_build_filter_year_range_only():
    result = _build_filter(None, (1844, 1850))
    assert result == {"year": {"$gte": 1844, "$lte": 1850}}


def test_build_filter_both():
    result = _build_filter("transitional", (1845, 1850))
    assert result == {
        "$and": [
            {"period": {"$eq": "transitional"}},
            {"year": {"$gte": 1845, "$lte": 1850}},
        ]
    }
