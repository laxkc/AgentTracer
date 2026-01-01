# Agent Observability Platform - Dockerfile
# Multi-stage build for optimized production image

FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend ./backend
COPY sdk ./sdk
COPY db ./db

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose ports (will be overridden by docker-compose)
EXPOSE 8000 8001

# Default command (will be overridden by docker-compose)
CMD ["uvicorn", "backend.ingest_api:app", "--host", "0.0.0.0", "--port", "8000"]
