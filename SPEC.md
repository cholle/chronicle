Here's a day-one layout that's small enough to actually finish but structured enough that Phase 2 doesn't require a rewrite.

```
chronicle/
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── README.md
├── data/
│   └── raw/                    # the four Marx texts as .txt
├── src/
│   └── chronicle/
│       ├── __init__.py
│       ├── config.py           # env vars, constants
│       ├── ingest.py           # chunk + upsert
│       ├── retrieve.py         # query Pinecone with temporal filter
│       ├── generate.py         # Claude call with citation prompt
│       └── api.py              # FastAPI app (one route)
├── scripts/
│   └── ingest_corpus.py        # CLI entry to run ingestion
└── tests/
    └── test_retrieve.py        # one smoke test
```

A few things about this shape worth justifying, because they're the decisions that pay off later.

**`src/` layout over flat.** With `uv` and `pyproject.toml` you get proper package semantics — `from chronicle.retrieve import search` works everywhere, tests don't need path hacks, and when you add the LangGraph agent in Phase 2 it lives at `src/chronicle/agent/` without disturbing anything. Flat layouts feel faster on day one and punish you on day thirty.

**Four modules, one responsibility each.** `ingest`, `retrieve`, `generate`, `api`. The temptation is to start with abstractions — a `BaseRetriever`, a `ChunkingStrategy` interface. Don't. Write the concrete version first. When you need a second retriever (hybrid, BM25, reranked), the abstraction will design itself from the diff. Premature interfaces are the #1 way solo projects stall.

**`config.py` as the single source of truth for env vars.** Pydantic Settings is the cleanest pattern here:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str
    pinecone_api_key: str
    pinecone_index: str = "chronicle"
    embedding_model: str = "multilingual-e5-large"
    claude_model: str = "claude-sonnet-4-6"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

Every other module imports `settings` from here. No `os.getenv` scattered around. When Railway deployment happens, you change zero code — Railway injects env vars, Pydantic picks them up.

**`pyproject.toml` minimal but real:**

```toml
[project]
name = "chronicle"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.40",
    "pinecone>=5.0",
    "fastapi>=0.115",
    "uvicorn>=0.32",
    "pydantic-settings>=2.6",
    "sentence-transformers>=3.3",
]

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.8"]

[tool.ruff]
line-length = 100

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Pin loosely on day one (`>=`), pin tightly when you deploy. `uv lock` handles reproducibility regardless.

**`.gitignore` essentials:** `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `data/processed/` if you cache embeddings locally. Commit `data/raw/` since Marx is public domain — having the corpus in the repo means `git clone && uv sync && uv run scripts/ingest_corpus.py` is the entire setup. That one-command reproducibility is the single biggest signal to a hiring manager that you ship things.

**README structure for day one:** what Chronicle is (two sentences), the thesis (temporal RAG over Marx), how to run it (four commands), an example query and response, and a "Roadmap" section listing the Phase 2 items as checkboxes. The roadmap section is doing real work — it tells a reader "this person knows what they're building toward, and they shipped the foundation first."

**One thing to skip on day one:** Docker. Railway can build directly from `pyproject.toml`, and a Dockerfile is a Phase 2 concern when you need to pin system deps for the embedding model. Adding it now is a half-day of yak-shaving for zero day-one value.

**Git hygiene from commit one:** initialize, make the first commit `chore: initial project structure` with just the empty tree and pyproject, then commit each module as you write it. Six to ten small commits beats one giant "initial implementation" commit — it makes the git history readable as a story, which matters since you've already been thinking about commit history as an artifact for Footwork. Same principle applies here, just less self-consciously.

Want me to write the actual `ingest.py` and `retrieve.py` next, or would you rather start with the four texts and the chunking decision (which shapes everything downstream)?