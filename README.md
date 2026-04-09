# Chronicle

**Temporal RAG over Marx's collected works — period-aware retrieval and cited answers across four phases of his thought.**

Chronicle is a retrieval-augmented generation system that treats *when* a text was written as a first-class signal alongside *what* it says. The corpus spans Marx from 1844 to 1875, tagged into four periods (early, transitional, mature, late). The same conceptual query returns visibly different passages — and produces visibly different answers — depending on which period you scope it to. The system surfaces how Marx reformulated his ideas across his lifetime rather than collapsing them into a single ahistorical voice.

This is a portfolio project demonstrating production patterns for temporal metadata filtering, idempotent ingestion, strict citation discipline, and bounded RAG retrieval against a real vector database.

## Why temporal RAG?

Naive RAG over a multi-period corpus is dominated by surface vocabulary. Search "alienated labor" and you get the 1844 Manuscripts, where Marx coined the term — never the *Capital* (1867) passages where he reformulated the same concept under completely different language. Temporal scoping solves this by letting the retriever surface conceptually related passages across periods even when the surface vocabulary diverges.

The two demos below show the architecture doing real work: first the retrieval layer, then the full pipeline producing cited answers.

## Demo 1: Temporal filtering

Same query, three period scopes. Run with `uv run python scripts/demo_temporal.py`.

Query: *"What is alienated labor and how does it shape human existence?"*

**Unfiltered (all periods)** — vector similarity is dominated by 1844's surface vocabulary. All top results are from the Economic and Philosophic Manuscripts. Zero results from *Capital*, despite *Capital* having 6× more chunks in the index.

**Early only (1844)** — same passages: estrangement, species-being, the worker facing his product as a stranger.

**Mature only (1867)** — *Capital* surfaces a completely different conceptual register:

> [1] Capital, Volume I (1867) — score 0.833
> *"He develops his slumbering powers and compels them to act in obedience to his sway. We are not now dealing with those primitive instinctive forms of labour that remind us of the mere animal..."*

The unfiltered query never surfaces the *Capital* perspective at all. The period filter is what makes Marx's intellectual evolution visible to the retrieval system.

## Demo 2: End-to-end Q&A with citations

Query against the mature period: *"How does Marx describe the labor process under capitalism?"* Run with `uv run python scripts/demo_qa.py`.

The system retrieves four passages from *Capital, Volume I*, then asks Claude to answer the question using only those passages, citing every claim. Excerpt of the response:

> Marx describes the labor process under capitalism as fundamentally characterized by the capitalist's domination over the worker. The capitalist exercises direct control: *"the labourer works under the control of the capitalist to whom his labour belongs; the capitalist taking good care that the work is done in a proper manner"* (*Capital, Volume I*, 1867). Crucially, once the worker enters the workplace, the product of labor ceases to belong to them — *"the product is the property of the capitalist and not that of the labourer, its immediate producer"* (*Capital, Volume I*, 1867).
>
> Under the factory system, this domination reaches its most complete technical form. Marx describes a fundamental inversion: *"it is not the workman that employs the instruments of labour, but the instruments of labour that employ the workman"* (*Capital, Volume I*, 1867). The machine, as congealed dead labour, actively dominates living labor: *"the instrument of labour confronts the labourer, during the labour-process, in the shape of capital, of dead labour, that dominates, and pumps dry, living labour-power"* (*Capital, Volume I*, 1867).

What makes this the thesis vindication: the query asks about the *labor process*, using mature Marx's terminology — and the system surfaces *Capital* Chapter 7 ("The Labour Process and the Process of Producing Surplus-Value") and the machinery sections, which scholars from Mészáros to Cleaver have identified as the loci where Marx's 1844 alienation framework persists under reformulated vocabulary. The retrieval is doing genuine conceptual matching, not lexical overlap, and the generation layer holds strict citation discipline — every claim is traceable to a retrieved chunk, with no outside knowledge bleeding in from Claude's training data.

The full demo runs three queries (early, mature, and late) and prints the generated answers with their source citations.

## Live demo

The API is deployed at https://chronicle-production-7df6.up.railway.app.

`GET /` and `GET /health` are public — try them in a browser to verify the service is up. Swagger UI is at `/docs`.

`POST /query` requires an API key (`X-API-Key` header). This protects the endpoint from unauthenticated LLM token burn.

For a demo key to test live queries, contact me via [LinkedIn](https://www.linkedin.com/in/chad-h-6038558) or open an issue on this repo.


## Quick start

```bash
git clone https://github.com/cholle/chronicle.git
cd chronicle
uv sync
cp .env.example .env  # then add ANTHROPIC_API_KEY and PINECONE_API_KEY
uv run python scripts/ingest_corpus.py
uv run python scripts/demo_temporal.py   # retrieval-only demo
uv run python scripts/demo_qa.py         # full end-to-end Q&A demo
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
│   ├── generate.py             # Claude integration with strict citation prompts
│   └── api.py                  # FastAPI endpoint — coming
├── scripts/
│   ├── ingest_corpus.py        # One-shot ingestion entry point
│   ├── demo_temporal.py        # Reproduces Demo 1 (retrieval only)
│   └── demo_qa.py              # Reproduces Demo 2 (end-to-end Q&A)
└── tests/                      # Unit tests for chunking, filters, prompts
```

The corpus is four works, one per period:

| Period       | Year | Work                                       | Chunks |
|--------------|------|--------------------------------------------|--------|
| early        | 1844 | Economic and Philosophic Manuscripts       | 175    |
| transitional | 1848 | The Communist Manifesto                    | 116    |
| mature       | 1867 | Capital, Volume I                          | 1,101  |
| late         | 1875 | Critique of the Gotha Programme            | 27     |

Total: 1,419 vectors. All four texts are public domain, sourced from marxists.org as single-PDF downloads, ingested via pypdf with a three-rule cleanup pass (page-number stripping, line-rejoining, whitespace collapsing).

Chunking targets ~400 tokens with ~50-token overlap, paragraph-merged, with a 450-token hard ceiling enforced by sentence-boundary splitting. Embedding is via Pinecone's inference API (`multilingual-e5-large`, `input_type=passage`). Chunk IDs are deterministic (`{filename_stem}_{chunk_index}`) so re-ingestion is idempotent.

Retrieval supports two filter modes via the `_build_filter` helper:

- **Period scoping**: `{"period": {"$eq": "early"}}`
- **Year range**: `{"year": {"$gte": 1860, "$lte": 1870}}`
- **Both combined**: wrapped in `$and`

Generation passes the retrieved chunks to Claude (Sonnet 4.6) with a prompt that enforces strict grounding: answer only from the provided passages, cite work and year for every claim, and explicitly say so if the passages don't contain enough information rather than drawing on outside knowledge of Marx.

## Tech stack

- **Vector DB**: Pinecone (serverless, cosine, 1024-dim)
- **Embeddings**: `multilingual-e5-large` via Pinecone inference API
- **Generation**: Anthropic Claude Sonnet 4.6
- **API**: FastAPI — *coming*
- **Package management**: `uv` + `pyproject.toml`
- **Python**: 3.11+

## Roadmap

This is the v0.2 end-to-end milestone. The full pipeline works: ingest → period-filtered retrieve → cited generation. Phase 2 builds on it:

- [x] **`ingest.py`** — PDF extraction, chunking, Pinecone embedding
- [x] **`retrieve.py`** — temporal metadata filtering
- [x] **`generate.py`** — Claude integration with strict citation prompts
- [ ] **`api.py`** — FastAPI endpoint exposing `/query` with optional period and year-range parameters
- [ ] **Temporal weighting** — boost underrepresented periods at retrieval time, not just filter (the unfiltered demo above shows why this matters)
- [ ] **Multi-hop reasoning** — agent loop that decomposes queries like *"How did Marx's view of alienation change between 1844 and 1867?"* into period-scoped sub-queries and synthesizes across them
- [ ] **Multilingual layer** — ingest the German originals alongside the English translations, enable cross-lingual retrieval
- [ ] **Entity tracking** — extract and link concepts (alienation, value, labor-power) across works to support graph-style queries
- [ ] **Railway deployment** — public endpoint for the demos

## Notes on what the architecture is implicitly arguing

There is a real scholarly debate about whether the concept of alienation in the 1844 Manuscripts persists into mature Marx (Mészáros, Ollman, Cleaver, the broader humanist Marxist tradition) or whether 1845 marks an "epistemological break" after which Marx operates in a fundamentally different theoretical register (Althusser, Balibar, the structural Marxist tradition).

Chronicle's temporal RAG architecture takes an implicit middle position. Period filtering only makes sense as a useful operation if you believe Marx's thought has identifiable phases that produce distinct conceptual registers — which is roughly the structural intuition. But cross-period conceptual retrieval (like Demo 2, where mature-Marx vocabulary surfaces 1867 passages that scholars have linked back to 1844 themes) only works if you also believe the underlying concepts are continuous enough to be traceable across reformulations — which is the humanist intuition.

The design wager is that the periods are real enough to filter on, and the underlying concepts are continuous enough that cross-period retrieval surfaces meaningful intellectual evolution rather than category errors. Demo 2 is the empirical test of that wager.

References for the continuity reading:

- Mészáros, István. *Marx's Theory of Alienation*. London: Merlin Press, 1970.
- Ollman, Bertell. *Alienation: Marx's Conception of Man in Capitalist Society*. Cambridge: Cambridge University Press, 1971.
- Cleaver, Harry. *Reading Capital Politically*. AK Press, 2000 (rev. ed.). Study guide to Chapter 7: [la.utexas.edu/users/hcleaver/357k/357ksg07.html](https://la.utexas.edu/users/hcleaver/357k/357ksg07.html).

## Development

Run the test suite:

```bash
uv run pytest tests/ -v
```

14 tests covering text cleanup, chunking edge cases (overlap, hard ceiling), filter construction (the four cases of the period × year-range truth table), and prompt building (empty / single chunk / multiple chunks).

## License

MIT. The Marx corpus in `data/raw/` is in the public domain (all texts pre-1928, well past any copyright term). The Moore/Aveling translation of *Capital Vol. I* and the standard *Manifesto* English text are both clear.

## Notes

This is a portfolio project. The git history is intentionally readable as a development arc — including the bugs caught and fixed along the way — rather than a fake-clean rewrite. Tags mark the milestones: `v0.1.0-corpus` (full corpus ingested) and `v0.2.0` (end-to-end RAG with cited answers).
