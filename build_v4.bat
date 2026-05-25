@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo.
echo ============================================
echo   PDF Library Manager - Build Script v4
echo ============================================

REM ---- Locate main.py ----
if exist "main.py" (
    echo Working directory: %CD%
) else if exist "pdf_manager\main.py" (
    cd pdf_manager
    echo Working directory: %CD%
) else (
    echo [ERROR] Cannot find main.py
    pause & exit /b 1
)
echo.

REM ---- Find Python ----
set PYTHON=
where python >nul 2>&1 && set PYTHON=python
if "%PYTHON%"=="" where py >nul 2>&1 && set PYTHON=py
if "%PYTHON%"=="" (
    echo [ERROR] Python not found.
    pause & exit /b 1
)
echo [OK] %PYTHON% & %PYTHON% --version

REM ---- venv ----
echo.
echo [1/4] Virtual environment...
if not exist "venv" %PYTHON% -m venv venv
call venv\Scripts\activate.bat

REM ---- Install ----
echo [2/4] Installing packages...
python -m pip install --upgrade pip -q
python -m pip install PyQt6 PyMuPDF requests watchdog pyinstaller -q
if errorlevel 1 ( echo [ERROR] & pause & exit /b 1 )

REM ---- Clean old build ----
echo [3/4] Cleaning old build...
if exist "dist\PDF_LibraryManager.exe" del /q "dist\PDF_LibraryManager.exe"
if exist "build" rmdir /s /q build

REM ---- PyInstaller (with --collect-all PyQt6) ----
echo [4/4] Building exe...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "PDF_LibraryManager" ^
    --collect-all PyQt6 ^
    --add-data "ui;ui" ^
    --add-data "core;core" ^
    --hidden-import fitz ^
    --hidden-import watchdog.observers ^
    --hidden-import watchdog.events ^
    --hidden-import requests ^
    main.py

if errorlevel 1 ( echo [ERROR] Build failed. & pause & exit /b 1 )

echo.
echo ============================================
echo  SUCCESS: dist\PDF_LibraryManager.exe
echo ============================================
pause
