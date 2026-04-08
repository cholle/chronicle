"""Centralised configuration via Pydantic Settings.

All env vars are declared here. Every other module imports `settings` from
this module — no `os.getenv` calls elsewhere.
"""

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
