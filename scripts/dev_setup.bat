@echo off
REM VoiceGuard Development Environment Setup Script
REM Run this script to set up the development environment

echo.
echo ========================================
echo VoiceGuard Development Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher from https://python.org
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Create virtual environment
echo.
echo Creating virtual environment...
if exist venv (
    echo Virtual environment already exists, skipping creation
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install development dependencies
echo.
echo Installing development dependencies...
pip install -r requirements-dev.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Install pre-commit hooks (if available)
echo.
echo Setting up pre-commit hooks...
pre-commit install 2>nul
if errorlevel 1 (
    echo Pre-commit not available, skipping hooks setup
) else (
    echo Pre-commit hooks installed successfully
)

REM Create necessary directories
echo.
echo Creating development directories...
if not exist "logs" mkdir logs
if not exist "temp" mkdir temp
if not exist "build" mkdir build
if not exist "dist" mkdir dist

REM Run initial tests
echo.
echo Running initial tests...
python -m pytest tests/ -v --tb=short
if errorlevel 1 (
    echo WARNING: Some tests failed, but setup continues
) else (
    echo All tests passed successfully
)

REM Display completion message
echo.
echo ========================================
echo Development Environment Setup Complete!
echo ========================================
echo.
echo To start developing:
echo 1. Activate the virtual environment: venv\Scripts\activate.bat
echo 2. Run tests: python -m pytest
echo 3. Start the service: python src\main_service.py console
echo 4. Start the helper: python src\main_helper.py
echo 5. Open configuration: python src\main_config.py
echo.
echo For more information, see README.md and CONTRIBUTING.md
echo.
pause
