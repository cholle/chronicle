# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv run pytest tests/ -v                     # full test suite
uv run pytest tests/test_generate.py -v    # single test file
uv run pytest tests/ -k "test_chunk"       # single test by name pattern
uv run python scripts/ingest_corpus.py     # one-shot Pinecone ingestion (~5 min)
uv run python scripts/demo_temporal.py     # retrieval-only demo
uv run python scripts/demo_qa.py           # end-to-end Q&A demo
```

Linting: `uv run ruff check src/ tests/` (line length 100).

## Architecture

Four modules with strict single responsibility. Data flows left to right:

```
ingest.py → (Pinecone) → retrieve.py → generate.py → api.py (stub)
```

**`config.py`** — Pydantic Settings singleton. All other modules import `settings` from here. No `os.getenv` elsewhere. Required env vars: `ANTHROPIC_API_KEY`, `PINECONE_API_KEY`. Defaults: `pinecone_index="chronicle"`, `embedding_model="multilingual-e5-large"`, `claude_model="claude-sonnet-4-6"`.

**`ingest.py`** — PDF extraction → 3-rule text cleanup (page-number strip, line-rejoining, whitespace collapse) → paragraph-merged chunking (400-tok target, 450-tok ceiling, 50-tok overlap via tiktoken) → Pinecone upsert. Chunk IDs are `{filename_stem}_{chunk_index}` — deterministic, so re-ingestion is idempotent. Embedding uses Pinecone inference API with `input_type="passage"`.

**`retrieve.py`** — Embeds query with `input_type="query"` (not `"passage"`) via `_pinecone_client.inference.embed`, builds a metadata filter via `_build_filter()`, queries Pinecone. Filter supports: period only, year range only, both (`$and`), or neither (no filter). Returns `list[dict]` with keys: `text, work, year, period, chunk_index, score`.

**`generate.py`** — Calls `retrieve.search()`, short-circuits with a canned message if zero results (no Claude call), builds prompt via `_build_prompt()`, calls `client.messages.create()`. Returns `{answer: str, citations: list[dict], chunks_used: int}`. The citations field is the raw chunk list passed to Claude — caller-verifiable provenance.

** `api.py` ** — FastAPI app with three endpoints: GET / (metadata), GET /health (Railway healthcheck), POST /query (wraps generate.answer()). Pydantic QueryRequest validates period as a Literal, enforces top_k range, and rejects empty queries at the 422 boundary. Lazy singletons in retrieve.py and generate.py cache the Pinecone/Anthropic clients across requests.

## Corpus metadata

Each vector carries: `text`, `work` (full title string), `year` (int), `period` (one of `"early"`, `"transitional"`, `"mature"`, `"late"`), `chunk_index`. Period labels and years are set in `ingest.py`'s `CORPUS` list — that's the single place to change if adding new works.

## Pinecone setup

Index name `chronicle`, 1024 dimensions, cosine similarity, serverless. Must use Pinecone's inference API (the client's `.inference.embed()` method) — not a local embedding model.

## Key design constraints

- The lazy singleton pattern (`_get_index()`, `_get_client()`) is single-threaded safe for scripts and demos. It will need refactoring for async FastAPI (thread-local or dependency injection).
- `sentence-transformers` is **not** in the dependencies — embedding is delegated entirely to Pinecone's inference API. Do not add local embedding.
- `_build_prompt` raises `ValueError` on empty chunks by design (invariant enforcement). The `answer()` function handles the empty case before calling it.

## Guardrails — what NOT to do

- Do not add LangChain, LangGraph, or sentence-transformers. This project deliberately uses direct SDK calls (Pinecone, Anthropic) to keep the stack minimal and the code path inspectable.
- Do not introduce `Index` as a type import from `pinecone` — the top-level symbol doesn't exist in v5+. Use `Any` or omit the annotation.
- Do not couple retrieve.py or generate.py to FastAPI. api.py is a thin layer; the lower modules must remain usable from CLI scripts.
- Do not add DocStore / BaseRetriever / ChunkingStrategy abstractions preemptively. Write concrete versions first; extract interfaces only when a second concrete implementation exists.