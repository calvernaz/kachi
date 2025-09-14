# Multi-stage Dockerfile for Kachi Billing Platform

# Stage 1: Frontend build
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/dashboard/package.json frontend/dashboard/yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy frontend source
COPY frontend/dashboard/ ./

# Build frontend
RUN yarn build

# Stage 2: Python backend
FROM python:3.12-slim AS backend

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_CACHE_DIR=/tmp/uv-cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Create app user
RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

# Copy Python dependency files and README (required by pyproject.toml)
COPY --chown=app:app pyproject.toml uv.lock README.md ./

# Install Python dependencies
RUN uv sync --frozen

# Copy application source
COPY --chown=app:app src/ ./src/
COPY --chown=app:app alembic.ini ./

# Copy built frontend assets
COPY --from=frontend-builder --chown=app:app /app/frontend/dist ./frontend/dashboard/dist/

# Create directories for logs and data
RUN mkdir -p logs data

# Expose ports
EXPOSE 8001 8002

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default command (can be overridden)
CMD ["uv", "run", "uvicorn", "kachi.apps.ingest_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
