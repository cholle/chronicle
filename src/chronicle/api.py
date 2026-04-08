"""FastAPI application — Chronicle temporal RAG API."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from chronicle.generate import answer

app = FastAPI(
    title="Chronicle",
    description="Temporal RAG over Marx's collected works",
    version="0.2.0",
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    period: Literal["early", "transitional", "mature", "late"] | None = None
    year_range: tuple[int, int] | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    answer: str
    citations: list[dict]
    chunks_used: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
def root() -> dict:
    return {
        "name": "Chronicle",
        "version": "0.2.0",
        "description": "Temporal RAG over Marx's collected works",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        result = answer(
            query=request.query,
            period=request.period,
            year_range=request.year_range,
            top_k=request.top_k,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return QueryResponse(**result)
