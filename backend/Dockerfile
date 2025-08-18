# Dockerfile for New Tab Backend Service
# Multi-stage build for optimized production image

# Build stage
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install uv

# Create app directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create app directory and set permissions
WORKDIR /app
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser arc/ ./arc/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser pyproject.toml ./

# Create startup script
COPY --chown=appuser:appuser <<'EOF' ./start.sh
#!/bin/bash
set -e

# Default values
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}
LOG_LEVEL=${LOG_LEVEL:-info}
WORKERS=${WORKERS:-1}

# Set database file to persistent volume if not specified
if [ -z "$DATABASE_FILE" ]; then
    export DATABASE_FILE="/app/data/web_memory.db"
fi

# Set cache file to persistent volume if not specified  
if [ -z "$QUERY_CACHE_FILE" ]; then
    export QUERY_CACHE_FILE="/app/data/query_embeddings_cache.json"
fi

# Set log file to persistent volume if not specified
if [ -z "$LOG_FILE" ]; then
    export LOG_FILE="/app/logs/newtab.log"
fi

# Ensure data directory exists and is writable
mkdir -p /app/data /app/logs
chmod 755 /app/data /app/logs

# Log configuration
echo "Starting New Tab Backend..."
echo "Host: $HOST"
echo "Port: $PORT"
echo "Log Level: $LOG_LEVEL"
echo "Workers: $WORKERS"
echo "Database: $DATABASE_FILE"
echo "Cache File: $QUERY_CACHE_FILE"
echo "Log File: $LOG_FILE"
echo "API Token: ${ARK_API_TOKEN:0:8}..."

# Set PYTHONPATH to include the app directory
export PYTHONPATH="/app:$PYTHONPATH"

# Health check function
check_health() {
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
            echo "✅ Health check passed"
            return 0
        fi
        attempt=$((attempt + 1))
        echo "⏳ Health check attempt $attempt/$max_attempts..."
        sleep 2
    done
    
    echo "❌ Health check failed after $max_attempts attempts"
    return 1
}

# Start the server
if [ "$1" = "dev" ]; then
    echo "🔧 Starting in development mode..."
    exec python -m uvicorn src.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --log-level "$LOG_LEVEL" \
        --reload
elif [ "$1" = "test" ]; then
    echo "🧪 Running tests..."
    export ARK_API_TOKEN="test-token-for-testing"
    export DATABASE_FILE=":memory:"
    export QUERY_CACHE_FILE="/tmp/test_query_cache.json"
    exec python -m pytest tests/ -v
else
    echo "🚀 Starting in production mode..."
    exec python -m uvicorn src.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --log-level "$LOG_LEVEL" \
        --workers "$WORKERS"
fi
EOF

# Make startup script executable
RUN chmod +x ./start.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set default command
CMD ["./start.sh"]

# Labels for metadata
LABEL maintainer="New Tab Team <support@newtab.dev>" \
      version="2.0.0" \
      description="New Tab Backend Service - FastAPI with SQLite FTS5 and vector search" \
      org.opencontainers.image.title="New Tab Backend" \
      org.opencontainers.image.description="A FastAPI-powered service for local web page indexing and intelligent search" \
      org.opencontainers.image.version="2.0.0" \
      org.opencontainers.image.vendor="New Tab Team" \
      org.opencontainers.image.licenses="MIT"