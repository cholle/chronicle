"""Tests for the FastAPI application."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from chronicle.api import app

client = TestClient(app)

_MOCK_RESULT = {
    "answer": "Marx describes alienated labour as...",
    "citations": [
        {
            "text": "The worker becomes poorer the more wealth he produces.",
            "work": "Economic and Philosophic Manuscripts",
            "year": 1844,
            "period": "early",
            "chunk_index": 0,
            "score": 0.91,
        }
    ],
    "chunks_used": 1,
}


def test_root_returns_expected_json():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Chronicle"
    assert data["version"] == "0.2.0"
    assert "description" in data


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_post_query_calls_answer_and_returns_shape():
    with patch("chronicle.api.answer", return_value=_MOCK_RESULT) as mock_answer:
        response = client.post(
            "/query",
            json={"query": "What is alienated labour?", "period": "early"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == _MOCK_RESULT["answer"]
    assert data["chunks_used"] == 1
    assert len(data["citations"]) == 1

    mock_answer.assert_called_once_with(
        query="What is alienated labour?",
        period="early",
        year_range=None,
        top_k=5,
    )


def test_post_query_returns_500_on_generate_exception():
    with patch("chronicle.api.answer", side_effect=RuntimeError("Pinecone unavailable")):
        response = client.post("/query", json={"query": "test"})

    assert response.status_code == 500
    assert "Pinecone unavailable" in response.json()["detail"]


def test_post_query_rejects_empty_query():
    response = client.post("/query", json={"query": ""})
    assert response.status_code == 422


def test_post_query_rejects_top_k_out_of_range():
    response = client.post("/query", json={"query": "test", "top_k": 0})
    assert response.status_code == 422

    response = client.post("/query", json={"query": "test", "top_k": 21})
    assert response.status_code == 422
