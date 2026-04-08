"""CLI entry point: ingest all raw corpus files into Pinecone.

Usage:
    uv run scripts/ingest_corpus.py
"""

from chronicle.ingest import ingest_corpus

if __name__ == "__main__":
    ingest_corpus()
