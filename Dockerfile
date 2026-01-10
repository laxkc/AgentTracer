# AgentTracer Platform - Dockerfile
# Multi-stage build with uv for fast dependency management

FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy pyproject.toml for dependency installation
COPY pyproject.toml ./

# Install Python dependencies using uv
RUN uv pip install --system -e .

# Copy application code
COPY server ./server
COPY sdk ./sdk

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose ports (will be overridden by docker-compose)
EXPOSE 8000 8001

# Default command (will be overridden by docker-compose)
CMD ["uvicorn", "server.api.query:app", "--host", "0.0.0.0", "--port", "8000"]
