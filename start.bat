@echo off
REM ==========================================================================
REM Agent Zero - Cross-Platform Startup Script (Windows)
REM ==========================================================================
REM This script provides GPU auto-detection and startup for Windows systems
REM
REM Usage:
REM   start.bat          - Auto-detect GPU and start
REM   start.bat gpu      - Force GPU mode
REM   start.bat cpu      - Force CPU-only mode
REM   start.bat stop     - Stop all services
REM ==========================================================================

setlocal enabledelayedexpansion

REM Colors for output (using escape codes)
for /F %%A in ('echo prompt $H^| cmd') do set "BS=%%A"

set "RESET=[0m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BOLD=[1m"

if "%1%"=="" (
    echo.
    echo %BOLD%Agent Zero - Cross-Platform Startup%RESET%
    echo ====================================
    echo.
    echo Usage:
    echo   start.bat          - Auto-detect GPU and start
    echo   start.bat gpu      - Force GPU mode
    echo   start.bat cpu      - Force CPU-only mode  
    echo   start.bat stop     - Stop all services
    echo.
    call :auto-detect
    exit /b 0
)

if "%1%"=="gpu" (
    call :start-gpu
    exit /b 0
)

if "%1%"=="cpu" (
    call :start-cpu
    exit /b 0
)

if "%1%"=="stop" (
    call :stop-services
    exit /b 0
)

echo Unknown command: %1%
echo Use: start.bat [gpu^|cpu^|stop]
exit /b 1

REM ==========================================================================
REM Helper Functions
REM ==========================================================================

:auto-detect
    echo %BOLD%🚀 Starting Agent Zero...%RESET%
    echo.
    
    REM Check if nvidia-smi is available
    where nvidia-smi >nul 2>&1
    if %errorlevel% equ 0 (
        echo %GREEN%✅ NVIDIA GPU detected. Starting with GPU acceleration...%RESET%
        call :start-gpu
    ) else (
        echo %YELLOW%ℹ️  No NVIDIA GPU detected. Starting in CPU-only mode...%RESET%
        call :start-cpu
    )
    exit /b 0

:start-gpu
    echo %BOLD%🚀 Starting Agent Zero with NVIDIA GPU acceleration...%RESET%
    docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
    if %errorlevel% equ 0 (
        echo.
        echo %GREEN%✅ Started with GPU support%RESET%
        echo %BOLD%📊 Streamlit UI: http://localhost:8501%RESET%
        echo %BOLD%🔌 Ollama API: http://localhost:11434%RESET%
        echo.
    ) else (
        echo %RED%❌ Failed to start with GPU support%RESET%
        exit /b 1
    )
    exit /b 0

:start-cpu
    echo %BOLD%🚀 Starting Agent Zero in CPU-only mode...%RESET%
    docker-compose up -d
    if %errorlevel% equ 0 (
        echo.
        echo %GREEN%✅ Started in CPU-only mode%RESET%
        echo %BOLD%📊 Streamlit UI: http://localhost:8501%RESET%
        echo %BOLD%🔌 Ollama API: http://localhost:11434%RESET%
        echo.
    ) else (
        echo %RED%❌ Failed to start services%RESET%
        exit /b 1
    )
    exit /b 0

:stop-services
    echo %BOLD%Stopping Agent Zero...%RESET%
    docker-compose down
    echo %GREEN%✅ All services stopped%RESET%
    exit /b 0
