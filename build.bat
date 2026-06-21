@echo off
TITLE Driver Handler by CROD - Build

echo ============================================
echo   Driver Handler by CROD - Building EXE
echo ============================================
echo.

echo [1/2] Building DriverHandlerByCROD.exe...

python -m PyInstaller --noconfirm --onefile --noconsole ^
 --name "DriverHandlerByCROD" ^
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

echo [2/2] Building Launcher.exe...

python -m PyInstaller --noconfirm --onefile --noconsole ^
 --name "Launcher" ^
 --hidden-import "auto_updater" ^
 --hidden-import "config" ^
 --hidden-import "logger" ^
 launcher.py

IF %ERRORLEVEL% NEQ 0 (
 echo [ERROR] Launcher build failed.
 pause
 exit /b 1
)

if not exist "release" mkdir release
copy "dist\DriverHandlerByCROD.exe" "release\" /Y >nul
copy "dist\Launcher.exe" "release\" /Y >nul
copy "version.txt" "release\" /Y >nul

echo.
echo ============================================
echo Build complete. Files are in .\release\
echo ============================================
pause
