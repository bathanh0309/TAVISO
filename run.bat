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
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment!
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [1/4] Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check if PyTorch is installed correctly
echo [2/4] Checking PyTorch installation...
python -c "import torch" 2>nul
if errorlevel 1 (
    echo PyTorch not found. Installing PyTorch CPU...
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
) else (
    echo PyTorch found. Verifying it's CPU version...
    python -c "import torch; torch.randn(1)" 2>nul
    if errorlevel 1 (
        echo PyTorch DLL error detected. Reinstalling CPU version...
        pip uninstall torch torchvision -y
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    ) else (
        echo PyTorch is working correctly.
    )
)

REM Install other dependencies if needed
echo [3/4] Checking other dependencies...
pip install -q -r requirements.txt

REM Start server
echo [4/4] Starting TAVISO server...
echo.
echo Server will be available at: http://localhost:8000
echo Press CTRL+C to stop the server
echo.

python -m backend.main

pause

