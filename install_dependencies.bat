@echo off
TITLE Driver Manager - Dependency Installer

echo ============================================
echo   Driver Update Manager - Setup
echo ============================================
echo.

:: Check Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please download Python from https://python.org and install it.
    echo Make sure to check "Add Python to PATH" during installation!
    pause
    exit /b 1
)

echo [1/3] Python found. Upgrading pip...
python -m pip install --upgrade pip --quiet

echo [2/3] Installing dependencies...
python -m pip install -r requirements.txt

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Some packages failed to install.
    echo Try running this as Administrator.
    pause
    exit /b 1
)

echo [3/3] Installing pywin32 post-install...
python -m pywin32_postinstall -install >nul 2>&1

echo.
echo ============================================
echo   All dependencies installed successfully!
echo   You can now run: python main_window.py
echo ============================================
pause
