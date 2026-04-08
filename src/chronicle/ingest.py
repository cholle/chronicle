"""Ingestion pipeline: chunk raw text and upsert embeddings into Pinecone.

Responsibilities:
- Load raw .txt files from data/raw/
- Split text into overlapping chunks with metadata (source, year, chunk_index)
- Embed chunks with sentence-transformers
- Upsert vectors into the Pinecone index
"""
