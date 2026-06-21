@echo off
TITLE Driver Manager - Build

echo ============================================
echo   Driver Update Manager - Building EXE
echo ============================================
echo.

:: Build the main app
echo [1/2] Building DriverManager.exe...
pyinstaller --noconfirm --onefile --windowed ^
    --name "DriverManager" ^
    --add-data "version.txt;." ^
    --hidden-import "wmi" ^
    --hidden-import "win32api" ^
    --hidden-import "win32con" ^
    --hidden-import "pystray" ^
    --hidden-import "PIL" ^
    main_window.py

IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Main app build failed.
    pause
    exit /b 1
)

:: Build the launcher (tiny, rarely changes)
echo [2/2] Building Launcher.exe...
pyinstaller --noconfirm --onefile --windowed ^
    --name "Launcher" ^
    launcher.py

IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Launcher build failed.
    pause
    exit /b 1
)

:: Copy both to a release folder
if not exist "release" mkdir release
copy "dist\DriverManager.exe" "release\" >nul
copy "dist\Launcher.exe" "release\" >nul

echo.
echo ============================================
echo   Build complete! Files in .\release\
echo   Next: run setup_builder\build_installer.bat
echo ============================================
pause
