#!/bin/bash
# ==============================================================================
# Agent Zero (L.A.B.) — Container Service Startup Script
#
# Starts two Chainlit processes in the same container:
#   - Chat UI       → port 8501  (src/ui/main.py)
#   - Admin Dashboard → port 8502  (src/ui/admin_app.py)
#
# The admin process runs in the background; the chat process runs in the
# foreground so that its exit code controls the container lifecycle.
# ==============================================================================

set -e

PYTHONPATH="${PYTHONPATH:-/app}"
export PYTHONPATH

echo "[start_services] Starting Agent Zero services..."
echo "[start_services] PYTHONPATH=${PYTHONPATH}"
echo "[start_services] Working directory: $(pwd)"

# ------------------------------------------------------------------------------
# Start Admin Dashboard on port 8502 (background)
# ------------------------------------------------------------------------------
echo "[start_services] Launching Admin Dashboard on port 8502..."
chainlit run src/ui/admin_app.py \
    --host 0.0.0.0 \
    --port 8502 \
    --headless &

ADMIN_PID=$!
echo "[start_services] Admin Dashboard PID: ${ADMIN_PID}"

# Give the admin process a moment to start before the main app floods the logs
sleep 1

# ------------------------------------------------------------------------------
# Start Chat UI on port 8501 (foreground — keeps container alive)
# ------------------------------------------------------------------------------
echo "[start_services] Launching Chat UI on port 8501..."
exec chainlit run src/ui/main.py \
    --host 0.0.0.0 \
    --port 8501 \
    --headless
