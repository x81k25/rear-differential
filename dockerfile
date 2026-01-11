FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Non-sensitive defaults - secrets injected at runtime via K8s secretRef
ENV API_HOST="0.0.0.0"
ENV API_PORT="8000"
ENV LOG_LEVEL="INFO"

WORKDIR /rear-differential

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies using uv (production only, no dev dependencies)
RUN uv sync --no-dev --no-cache

# Copy application code
COPY ./app/ ./app

# Expose the port
EXPOSE ${API_PORT}

# Run the application
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]