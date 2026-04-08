# Chronicle

**Temporal RAG over Marx's collected works — period-aware retrieval and citation across four phases of his thought.**

Chronicle is a retrieval system that treats *when* a text was written as a first-class signal alongside *what* it says. The corpus spans Marx from 1844 to 1875, tagged into four periods (early, transitional, mature, late). The same conceptual query returns visibly different passages depending on which period you scope it to — surfacing how Marx reformulated his ideas across his lifetime rather than collapsing them into a single ahistorical voice.

This is a portfolio project demonstrating production patterns for temporal metadata filtering, idempotent ingestion, and bounded RAG retrieval against a real vector database.

## Why temporal RAG?

Naive RAG over a multi-period corpus is dominated by surface vocabulary. Search "alienated labor" and you get the 1844 Manuscripts, where Marx coined the term — never the *Capital* (1867) passages where he reformulated the same concept as commodity fetishism using completely different language.

Temporal scoping solves this by letting the retriever surface conceptually related passages across periods even when the surface vocabulary diverges. The demo below shows the same query against three different period scopes — and the difference is the entire point of the project.

## Demo

Query: *"What is alienated labor and how does it shape human existence?"*

**Unfiltered (all periods)** — dominated by 1844 vocabulary:

> [1] Economic and Philosophic Manuscripts (1844) — score 0.858
> *"How could the worker come to face the product of his activity as a stranger, were it not that in the very act of production he was estranging himself from himself?..."*

**Early only (1844)** — same passages, the canonical young-Marx formulation of estrangement and species-being.

**Mature only (1867)** — *Capital* surfaces a completely different conceptual register:

> [1] Capital, Volume I (1867) — score 0.833
> *"He develops his slumbering powers and compels them to act in obedience to his sway... We are not now dealing with those primitive instinctive forms of labour that remind us of the mere animal..."*

The unfiltered query never surfaces the *Capital* perspective at all, because vector similarity is dominated by the 1844 Manuscripts' surface vocabulary. The period filter is what makes Marx's intellectual evolution visible. Run `uv run python scripts/demo_temporal.py` to reproduce.

## Quick start

```bash
git clone https://github.com/cholle/chronicle.git
cd chronicle
uv sync
cp .env.example .env  # then add ANTHROPIC_API_KEY and PINECONE_API_KEY
uv run python scripts/ingest_corpus.py
uv run python scripts/demo_temporal.py
```

You'll need a Pinecone index named `chronicle` configured for `multilingual-e5-large` (1024 dimensions, cosine, served via Pinecone's inference API). Ingestion takes ~5 minutes including rate-limit pacing on the starter tier.

## Architecture

```
chronicle/
├── data/raw/                   # Four Marx works as PDF (public domain, included)
├── src/chronicle/
│   ├── config.py               # Pydantic settings, env-driven
│   ├── ingest.py               # PDF extract → clean → chunk → embed → upsert
│   ├── retrieve.py             # Temporal-filtered vector search
│   └── ...                     # generate.py, api.py — coming
├── scripts/
│   ├── ingest_corpus.py        # One-shot ingestion entry point
│   └── demo_temporal.py        # Reproduces the demo above
└── tests/                      # Unit tests for chunking and filter logic
```

The corpus is four works, one per period:

| Period       | Year | Work                                       | Chunks |
|--------------|------|--------------------------------------------|--------|
| early        | 1844 | Economic and Philosophic Manuscripts       | 175    |
| transitional | 1848 | The Communist Manifesto                    | 116    |
| mature       | 1867 | Capital, Volume I                          | 1101   |
| late         | 1875 | Critique of the Gotha Programme            | 27     |

Total: 1,419 vectors. All four texts are public domain, sourced from marxists.org as single-PDF downloads, ingested via pypdf with a three-rule cleanup pass (page-number stripping, line-rejoining, whitespace collapsing).

Chunking targets ~400 tokens with ~50-token overlap, paragraph-merged, with a 450-token hard ceiling enforced by sentence-boundary splitting. Embedding is via Pinecone's inference API (`multilingual-e5-large`, `input_type=passage`). Chunk IDs are deterministic (`{filename_stem}_{chunk_index}`) so re-ingestion is idempotent — the same script can run repeatedly without producing duplicates.

Retrieval supports two filter modes via the `_build_filter` helper:

- **Period scoping**: `{"period": {"$eq": "early"}}`
- **Year range**: `{"year": {"$gte": 1860, "$lte": 1870}}`
- **Both combined**: wrapped in `$and`

## Tech stack

- **Vector DB**: Pinecone (serverless, cosine, 1024-dim)
- **Embeddings**: `multilingual-e5-large` via Pinecone inference API
- **Generation**: Anthropic Claude (Sonnet 4.6) — *coming*
- **API**: FastAPI — *coming*
- **Package management**: `uv` + `pyproject.toml`
- **Python**: 3.11+

## Roadmap

This is the v0.1 corpus milestone. The thesis works end-to-end (ingest → period-filtered retrieve → visibly different results). Phase 2 builds on it:

- [ ] **`generate.py`** — Claude integration with strict citation prompts (cite work and year for every claim)
- [ ] **`api.py`** — FastAPI endpoint exposing `/query` with optional period and year-range parameters
- [ ] **Temporal weighting** — boost underrepresented periods at retrieval time, not just filter (the unfiltered demo above shows why this matters)
- [ ] **Multi-hop reasoning** — agent loop that decomposes queries like *"How did Marx's view of alienation change between 1844 and 1867?"* into period-scoped sub-queries and synthesizes across them
- [ ] **Multilingual layer** — ingest the German originals alongside the English translations, enable cross-lingual retrieval
- [ ] **Entity tracking** — extract and link concepts (alienation, value, labor-power) across works to support graph-style queries
- [ ] **Railway deployment** — public endpoint for the demo

## Development

Run the test suite:

```bash
uv run pytest tests/ -v
```

11 tests covering text cleanup, chunking edge cases (overlap, hard ceiling), and filter construction (the four cases of the period × year-range truth table).

## License

MIT. The Marx corpus in `data/raw/` is in the public domain (all texts pre-1928, well past any copyright term). The Moore/Aveling translation of *Capital Vol. I* and the standard *Manifesto* English text are both clear.

## Notes

This is a portfolio project. The git history is intentionally readable as a development arc — including the bugs caught and fixed along the way — rather than a fake-clean rewrite. The `v0.1.0-corpus` tag marks the moment full ingestion landed end-to-end.
