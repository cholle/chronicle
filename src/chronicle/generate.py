"""Generation: call Claude with retrieved chunks and produce a cited answer.

Responsibilities:
- Accept a query string and a list of retrieved chunks
- Build a citation-aware system + user prompt
- Call the Anthropic Messages API via `settings.claude_model`
- Return the assistant's response text
"""
