# Chronicle

Temporal RAG over Marx's collected works — period-aware retrieval and citation across four phases of his thought.

## What it is

Chronicle lets you query Marx's writing with awareness of *when* something was written. Ask about his theory of alienation and filter to the early manuscripts; ask about Capital and filter to his mature period. Retrieval is grounded in the actual text; every answer cites the source and year.

## Setup

```bash
git clone https://github.com/your-username/chronicle
cd chronicle
cp .env.example .env  # fill in your API keys
uv sync
uv run scripts/ingest_corpus.py
uv run uvicorn chronicle.api:app --reload
```

## Example

```
POST /query
{
  "query": "What does Marx say about alienated labour?",
  "year_start": 1844,
  "year_end": 1848
}
```

## Roadmap

- [ ] Phase 2: LangGraph agent with multi-hop reasoning across periods
- [ ] Hybrid retrieval (dense + BM25 reranking)
- [ ] Railway deployment
- [ ] Docker image for reproducible embedding environment
- [ ] Streaming responses via SSE
