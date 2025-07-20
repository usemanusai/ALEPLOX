@echo off
REM VoiceGuard Development Runner
REM Quick script to run VoiceGuard components in development mode

echo.
echo ========================================
echo VoiceGuard Development Runner
echo ========================================
echo.

if "%1"=="" (
    echo Usage: run_dev.bat [component]
    echo.
    echo Available components:
    echo   service    - Run VoiceGuard service in console mode
    echo   helper     - Run VoiceGuard audio helper
    echo   config     - Open VoiceGuard configuration GUI
    echo   test       - Run test suite
    echo   install    - Install VoiceGuard service
    echo   uninstall  - Uninstall VoiceGuard service
    echo.
    goto :end
)

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Change to project root
cd /d "%~dp0\.."

if "%1"=="service" (
    echo Starting VoiceGuard service in console mode...
    python src\main_service.py console
) else if "%1"=="helper" (
    echo Starting VoiceGuard audio helper...
    python src\main_helper.py
) else if "%1"=="config" (
    echo Opening VoiceGuard configuration GUI...
    python src\main_config.py
) else if "%1"=="test" (
    echo Running test suite...
    python -m pytest tests/ -v
) else if "%1"=="install" (
    echo Installing VoiceGuard service...
    python install.py install
) else if "%1"=="uninstall" (
    echo Uninstalling VoiceGuard service...
    python install.py uninstall
) else (
    echo Unknown component: %1
    echo Run without arguments to see available components
)

:end
echo.
pause
