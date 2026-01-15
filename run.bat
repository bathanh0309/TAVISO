@echo off
REM TAVISO - Da Nang Traffic Monitoring System
REM Quick Start Script for Windows

echo ========================================
echo TAVISO - He Thong Giam Sat Giao Thong
echo Da Nang, Viet Nam
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv .venv
    echo Then run: .venv\Scripts\activate
    echo Then run: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
echo [1/2] Activating virtual environment...
call .venv\Scripts\activate.bat

REM Start server
echo [2/2] Starting TAVISO server...
echo.
echo Server will be available at: http://localhost:8000
echo Press CTRL+C to stop the server
echo.

python -m backend.main

pause
