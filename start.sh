#!/bin/bash
# ==========================================================================
# Agent Zero - Cross-Platform Startup Script (Linux/macOS)
# ==========================================================================
# This script provides GPU auto-detection and startup for Linux/macOS systems
#
# Usage:
#   ./start.sh          - Auto-detect GPU and start
#   ./start.sh gpu      - Force GPU mode
#   ./start.sh cpu      - Force CPU-only mode
#   ./start.sh stop     - Stop all services
# ==========================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

# Default action
ACTION="${1:-auto}"

case "$ACTION" in
    auto)
        echo ""
        echo -e "${BOLD}🚀 Starting Agent Zero...${RESET}"
        echo ""
        
        # Check if nvidia-smi is available
        if command -v nvidia-smi &> /dev/null; then
            echo -e "${GREEN}✅ NVIDIA GPU detected. Starting with GPU acceleration...${RESET}"
            start_gpu
        else
            echo -e "${YELLOW}ℹ️  No NVIDIA GPU detected. Starting in CPU-only mode...${RESET}"
            start_cpu
        fi
        ;;
    gpu)
        start_gpu
        ;;
    cpu)
        start_cpu
        ;;
    stop)
        stop_services
        ;;
    *)
        echo "Unknown command: $ACTION"
        echo "Use: $0 [auto|gpu|cpu|stop]"
        exit 1
        ;;
esac

# ==========================================================================
# Helper Functions
# ==========================================================================

start_gpu() {
    echo -e "${BOLD}🚀 Starting Agent Zero with NVIDIA GPU acceleration...${RESET}"
    docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
    echo ""
    echo -e "${GREEN}✅ Started with GPU support${RESET}"
    echo -e "${BOLD}📊 Chainlit UI: http://localhost:8501${RESET}"
    echo -e "${BOLD}🔌 Ollama API: http://localhost:11434${RESET}"
    echo ""
}

start_cpu() {
    echo -e "${BOLD}🚀 Starting Agent Zero in CPU-only mode...${RESET}"
    docker-compose up -d
    echo ""
    echo -e "${GREEN}✅ Started in CPU-only mode${RESET}"
    echo -e "${BOLD}📊 Chainlit UI: http://localhost:8501${RESET}"
    echo -e "${BOLD}🔌 Ollama API: http://localhost:11434${RESET}"
    echo ""
}

stop_services() {
    echo -e "${BOLD}Stopping Agent Zero...${RESET}"
    docker-compose down
    echo -e "${GREEN}✅ All services stopped${RESET}"
}

# Run the appropriate function
export -f start_gpu
export -f start_cpu
export -f stop_services
