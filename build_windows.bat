@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo.
echo ============================================
echo   PDF Library Manager - Build Script
echo ============================================

REM ---- Locate main.py (handle bat in parent or same folder) ----
if exist "main.py" (
    echo Working directory: %CD%
) else if exist "pdf_manager\main.py" (
    cd pdf_manager
    echo Working directory: %CD%
) else (
    echo [ERROR] Cannot find main.py
    echo Please place this bat file in the same folder as main.py
    pause
    exit /b 1
)
echo.

REM ---- Find Python ----
set PYTHON=
where python >nul 2>&1 && set PYTHON=python
if "%PYTHON%"=="" where py >nul 2>&1 && set PYTHON=py
if "%PYTHON%"=="" (
    echo [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)
echo [OK] Python: %PYTHON% & %PYTHON% --version
echo.

REM ---- Virtual environment ----
echo [1/4] Setting up virtual environment...
if not exist "venv" %PYTHON% -m venv venv
call venv\Scripts\activate.bat
echo [OK] Ready.

REM ---- Install packages ----
echo.
echo [2/4] Installing packages...
python -m pip install --upgrade pip -q
python -m pip install PyQt6 PyMuPDF requests watchdog pyinstaller -q
if errorlevel 1 ( echo [ERROR] Install failed. & pause & exit /b 1 )
echo [OK] Done.

REM ---- PyInstaller ----
echo.
echo [3/4] Building exe...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "PDF_LibraryManager" ^
    --add-data "ui;ui" ^
    --add-data "core;core" ^
    --hidden-import PyQt6.QtWidgets ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import fitz ^
    --hidden-import watchdog.observers ^
    --hidden-import watchdog.events ^
    --hidden-import requests ^
    main.py

if errorlevel 1 ( echo [ERROR] Build failed. & pause & exit /b 1 )

echo.
echo ============================================
echo [4/4] SUCCESS!
echo Output: %CD%\dist\PDF_LibraryManager.exe
echo ============================================
echo.
pause
