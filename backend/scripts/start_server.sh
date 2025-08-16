#!/bin/bash

# Local Web Memory Backend - Server Startup Script
set -e

echo "🚀 Starting Local Web Memory Backend Server..."

# Check if we're in the correct directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    echo "   Expected to find pyproject.toml in current directory"
    exit 1
fi

# Check for required environment variable
if [ -z "$ARK_API_TOKEN" ]; then
    echo "⚠️  Warning: ARK_API_TOKEN environment variable not set"
    echo "   The server will run in mock mode for API calls"
    echo "   To set: export ARK_API_TOKEN=\"your-token-here\""
    echo ""
fi

# Check if uv is available (preferred)
if command -v uv >/dev/null 2>&1; then
    echo "✅ Using uv for Python environment management"
    
    # Install dependencies if needed
    if [ ! -f "uv.lock" ] || [ "pyproject.toml" -nt "uv.lock" ]; then
        echo "📦 Installing/updating dependencies..."
        uv sync
    fi
    
    # Start the server with uv
    echo "🌐 Starting server at http://localhost:8000"
    echo "📚 API Documentation: http://localhost:8000/docs"
    echo "🔍 Health Check: http://localhost:8000/health"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo "----------------------------------------"
    
    uv run python -m src.main
else
    echo "❌ Error: uv not found"
    echo "   Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "   Or use pip: pip install uv"
    exit 1
fi