"""Ingestion pipeline: chunk raw PDFs and upsert embeddings into Pinecone.

Pipeline:
  1. Read all .pdf files from data/raw/ (filename format: YYYY_slug.pdf).
  2. Extract text with pypdf, run a light cleanup pass.
  3. Split into ~400-token chunks with ~50-token overlap using tiktoken cl100k_base.
  4. Embed via Pinecone inference API (multilingual-e5-large, input_type=passage).
  5. Upsert to Pinecone with deterministic IDs for idempotent re-runs.
"""

from __future__ import annotations

import re
from pathlib import Path

import tiktoken
from pinecone import Pinecone
from pypdf import PdfReader

from chronicle.config import settings

# ---------------------------------------------------------------------------
# Corpus metadata
# ---------------------------------------------------------------------------

CORPUS_META: dict[str, dict[str, str]] = {
    "1844_manuscripts.pdf": {"work": "Economic and Philosophic Manuscripts", "period": "early"},
    "1848_manifesto.pdf": {"work": "The Communist Manifesto", "period": "transitional"},
    "1867_capital.pdf": {"work": "Capital, Volume I", "period": "mature"},
    "1875_gotha.pdf": {"work": "Critique of the Gotha Programme", "period": "late"},
}

# ---------------------------------------------------------------------------
# Chunking constants
# ---------------------------------------------------------------------------

TARGET_TOKENS = 400
OVERLAP_TOKENS = 50
HARD_CEILING = 450
EMBED_BATCH_SIZE = 96

DATA_RAW = Path(__file__).parents[3] / "data" / "raw"

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def _extract_text(pdf_path: Path) -> str:
    """Return concatenated page text from a PDF."""
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def clean_text(text: str) -> str:
    """Apply three cleanup rules to PDF-extracted text.

    1. Strip page-number-only lines.
    2. Collapse intra-paragraph whitespace runs to a single space while
       preserving paragraph breaks (double newlines).
    3. Join lines that end without terminal punctuation to the next line.
    """
    # Split on paragraph breaks first so we can work paragraph-by-paragraph.
    paragraphs = re.split(r"\n{2,}", text)
    cleaned: list[str] = []

    for para in paragraphs:
        lines = para.split("\n")

        # Rule 1: strip page-number-only lines.
        lines = [ln for ln in lines if not re.match(r"^\s*\d+\s*$", ln)]

        if not lines:
            continue

        # Rule 3: join lines that end mid-sentence.
        joined: list[str] = []
        buf = ""
        for ln in lines:
            stripped = ln.strip()
            if not stripped:
                if buf:
                    joined.append(buf)
                    buf = ""
                continue
            if buf:
                buf = buf + " " + stripped
            else:
                buf = stripped
            # Flush if the line ends with terminal punctuation.
            if re.search(r"[.!?][\"']?\s*$", buf):
                joined.append(buf)
                buf = ""
        if buf:
            joined.append(buf)

        # Rule 2: collapse whitespace within each joined line.
        para_text = " ".join(joined)
        para_text = re.sub(r"[ \t]+", " ", para_text).strip()
        if para_text:
            cleaned.append(para_text)

    return "\n\n".join(cleaned)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _count_tokens(text: str, enc: tiktoken.Encoding) -> int:
    return len(enc.encode(text))


def _split_on_sentences(text: str, enc: tiktoken.Encoding, ceiling: int) -> list[str]:
    """Split a single over-long paragraph on sentence boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    segments: list[str] = []
    current = ""
    for sent in sentences:
        candidate = (current + " " + sent).strip() if current else sent
        if _count_tokens(candidate, enc) > ceiling and current:
            segments.append(current)
            current = sent
        else:
            current = candidate
    if current:
        segments.append(current)
    return segments


def chunk_text(text: str) -> list[str]:
    """Split *text* into ~400-token chunks with ~50-token overlap.

    - First splits on paragraph boundaries.
    - Any paragraph exceeding HARD_CEILING tokens is split on sentence
      boundaries before merging.
    - Adjacent paragraphs are merged until the chunk approaches TARGET_TOKENS,
      then overlap is carried forward.
    """
    enc = tiktoken.get_encoding("cl100k_base")

    # Build a flat list of atomic units (paragraphs or sentence-split pieces).
    raw_paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    units: list[str] = []
    for para in raw_paragraphs:
        if _count_tokens(para, enc) > HARD_CEILING:
            units.extend(_split_on_sentences(para, enc, HARD_CEILING))
        else:
            units.append(para)

    if not units:
        return []

    chunks: list[str] = []
    current_units: list[str] = []
    current_tokens = 0

    for unit in units:
        unit_tokens = _count_tokens(unit, enc)
        if current_tokens + unit_tokens > TARGET_TOKENS and current_units:
            chunks.append("\n\n".join(current_units))

            # Build overlap: walk backward through current_units until we
            # have ~OVERLAP_TOKENS worth.
            overlap_units: list[str] = []
            overlap_tokens = 0
            for u in reversed(current_units):
                ut = _count_tokens(u, enc)
                if overlap_tokens + ut > OVERLAP_TOKENS:
                    break
                overlap_units.insert(0, u)
                overlap_tokens += ut

            current_units = overlap_units + [unit]
            current_tokens = overlap_tokens + unit_tokens
        else:
            current_units.append(unit)
            current_tokens += unit_tokens

    if current_units:
        chunks.append("\n\n".join(current_units))

    return chunks


# ---------------------------------------------------------------------------
# Embedding + upsert
# ---------------------------------------------------------------------------


def _embed_batch(pc: Pinecone, texts: list[str]) -> list[list[float]]:
    response = pc.inference.embed(
        model=settings.embedding_model,
        inputs=texts,
        parameters={"input_type": "passage"},
    )
    return [item["values"] for item in response]


def _upsert_chunks(
    pc: Pinecone,
    index_name: str,
    chunks: list[str],
    filename_stem: str,
    meta: dict[str, str],
    year: int,
) -> None:
    index = pc.Index(index_name)

    for batch_start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + EMBED_BATCH_SIZE]
        embeddings = _embed_batch(pc, batch)

        vectors = [
            {
                "id": f"{filename_stem}_{batch_start + i}",
                "values": embeddings[i],
                "metadata": {
                    "work": meta["work"],
                    "period": meta["period"],
                    "year": year,
                    "chunk_index": batch_start + i,
                    "text": batch[i],
                },
            }
            for i in range(len(batch))
        ]
        index.upsert(vectors=vectors)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def ingest_corpus() -> None:
    """Run the full ingestion pipeline for all PDFs in data/raw/."""
    pc = Pinecone(api_key=settings.pinecone_api_key)

    pdf_files = sorted(DATA_RAW.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {DATA_RAW}")
        return

    for pdf_path in pdf_files:
        filename = pdf_path.name
        meta = CORPUS_META.get(filename)
        if meta is None:
            print(f"  Skipping {filename} — not in CORPUS_META")
            continue

        year = int(filename.split("_")[0])
        print(f"Ingesting {filename} ({meta['work']}, {year})...")

        raw_text = _extract_text(pdf_path)
        clean = clean_text(raw_text)
        chunks = chunk_text(clean)

        print(f"  {len(chunks)} chunks")
        _upsert_chunks(pc, settings.pinecone_index, chunks, pdf_path.stem, meta, year)
        print(f"  Done.")

    print("Ingestion complete.")
