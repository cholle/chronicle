"""Centralised configuration via Pydantic Settings.

All env vars are declared here. Every other module imports `settings` from
this module — no `os.getenv` calls elsewhere.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    pinecone_api_key: str
    pinecone_index: str = "chronicle"
    embedding_model: str = "multilingual-e5-large"
    claude_model: str = "claude-sonnet-4-6"

    # When set, POST /query requires a matching X-API-Key header.
    # When None (default), no auth is enforced — useful for local development.
    chronicle_api_key: str | None = None


settings = Settings()
