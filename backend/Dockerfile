FROM python:3.11-slim

WORKDIR /app/backend

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first for layer caching
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY backend/src/ ./src/
COPY backend/alembic/ ./alembic/
COPY backend/alembic.ini ./
COPY backend/config/ ./config/
COPY backend/scripts/ ./scripts/

# Expose port
EXPOSE 8000

# Run migrations then start server (for local dev)
# For production, use a Release Command: uv run alembic upgrade head
# Run migrations then start server
# Using a script to capture errors
RUN echo '#!/bin/sh\necho "Running migrations..."\nuv run alembic upgrade head || echo "Migration skipped or failed"\necho "Starting server..."\nuvicorn src.main:app --host 0.0.0.0 --port 8000 --app-dir /app/backend' > /app/start.sh && chmod +x /app/start.sh
CMD ["/app/start.sh"]
