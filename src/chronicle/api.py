"""FastAPI application — single /query endpoint.

Responsibilities:
- Accept POST /query with a JSON body {query, year_start?, year_end?}
- Call retrieve.search then generate.answer
- Return the answer and the source chunks used
"""
