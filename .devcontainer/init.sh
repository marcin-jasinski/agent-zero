#!/bin/bash
# DevContainer initialization script for Agent Zero
# This script runs when the container is being initialized

set -e  # Exit on error

echo "==================================================================="
echo "Agent Zero (L.A.B.) - DevContainer Initialization"
echo "==================================================================="

# Update package manager
echo "[1/5] Updating package manager..."
apt-get update -qq

# Install system dependencies (if not already in image)
echo "[2/5] Installing system dependencies..."
apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    build-essential \
    2>/dev/null || true

# Upgrade pip, setuptools, and wheel
echo "[3/5] Upgrading pip, setuptools, and wheel..."
python -m pip install -q --upgrade pip setuptools wheel

# Install project dependencies (editable install)
echo "[4/5] Installing project dependencies..."
cd /app
pip install -q -e ".[dev]"

# Set up pre-commit hooks (optional, only if not already done)
echo "[5/5] Setting up development tools..."
pip install -q pre-commit 2>/dev/null || true

# Clean up
apt-get clean
rm -rf /var/lib/apt/lists/*

echo ""
echo "==================================================================="
echo "✅ DevContainer initialization complete!"
echo ""
echo "Available commands:"
echo "  pytest             - Run all tests"
echo "  pytest -v          - Run tests with verbose output"
echo "  pytest --cov=src   - Run tests with coverage report"
echo "  black src tests    - Format code"
echo "  flake8 src tests   - Check code style"
echo "  mypy src           - Type checking"
echo ""
echo "Streamlit UI will be available at: http://localhost:8501"
echo "Langfuse Dashboard at: http://localhost:3000"
echo "==================================================================="
