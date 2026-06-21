@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================
echo Driver Handler by CROD - Build
echo ============================================
echo.

if not exist version.txt (
    echo 1.0.0>version.txt
)

for /f "usebackq delims=" %%v in ("version.txt") do set APP_VERSION=%%v

echo Version: %APP_VERSION%
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if not exist release mkdir release

echo.
echo [1/3] Building core app...
python -m PyInstaller --noconfirm --onefile --noconsole --clean ^
  --name "DriverHandlerByCROD_Core" ^
  --add-data "version.txt;." ^
  --hidden-import "wmi" ^
  --hidden-import "win32api" ^
  --hidden-import "win32con" ^
  --hidden-import "winreg" ^
  --hidden-import "pystray" ^
  --hidden-import "PIL" ^
  main_window.py

if errorlevel 1 (
    echo [ERROR] Core app build failed.
    exit /b 1
)

echo.
echo [2/3] Building visible launcher...
python -m PyInstaller --noconfirm --onefile --noconsole --clean ^
  --name "DriverHandlerByCROD" ^
  --add-data "version.txt;." ^
  --hidden-import "auto_updater" ^
  --hidden-import "config" ^
  --hidden-import "logger" ^
  launcher.py

if errorlevel 1 (
    echo [ERROR] Launcher build failed.
    exit /b 1
)

copy /y "dist\DriverHandlerByCROD_Core.exe" "release\DriverHandlerByCROD_Core.exe" >nul
copy /y "dist\DriverHandlerByCROD.exe" "release\DriverHandlerByCROD.exe" >nul
copy /y "version.txt" "release\version.txt" >nul

echo.
echo [3/3] Building installer if Inno Setup exists...

set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe

if "%ISCC%"=="" (
    echo WARNING: Inno Setup was not found.
    echo Install Inno Setup 6 to build Driver_Handler_By_CROD_Setup.exe
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Content 'setup_builder\installer.iss' -Raw) -replace '#define MyAppVersion \"[^\"]+\"', '#define MyAppVersion \"%APP_VERSION%\"' | Set-Content 'setup_builder\installer_build.iss' -Encoding UTF8"
    "%ISCC%" "setup_builder\installer_build.iss"
)

echo.
echo ============================================
echo Build done.
echo Output folder: release
echo Expected:
echo - DriverHandlerByCROD.exe
echo - DriverHandlerByCROD_Core.exe
echo - Driver_Handler_By_CROD_Setup.exe
echo ============================================
echo.

endlocal