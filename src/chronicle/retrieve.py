"""Retrieval: query Pinecone with optional temporal filtering.

Responsibilities:
- Embed an incoming query string
- Query the Pinecone index with top-k and optional year-range metadata filter
- Return a list of ranked chunk dicts (text, source, year, score)
"""
