FROM python:3.11-slim

# Install uv from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency manifests first so Docker caches the dep install layer
COPY pyproject.toml uv.lock ./

# Install dependencies (without the project itself) into /app/.venv
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the project
COPY . .

# Install the project now that source is present
RUN uv sync --frozen --no-dev

# Railway injects $PORT at runtime; shell form lets us expand the env var
CMD ["sh", "-c", "uv run uvicorn chronicle.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
