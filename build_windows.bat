@echo off
REM build_windows.bat — Build ContainerOptimizer.exe for Windows
REM
REM Prerequisites:
REM   pip install pyinstaller
REM   pip install -r requirements.txt   (WITHOUT gurobipy)
REM
REM Run from the project root (Command Prompt or PowerShell):
REM   build_windows.bat

setlocal enabledelayedexpansion

echo.
echo ==========================================
echo  Container Optimizer -- Windows Build
echo ==========================================
echo.

REM ── Sanity check ──────────────────────────────────────────────────────────
where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo ERROR: pyinstaller not found. Run: pip install pyinstaller
    exit /b 1
)

python -c "import gurobipy" >nul 2>&1
if not errorlevel 1 (
    echo WARNING: gurobipy is installed in this environment.
    echo          Build will proceed but CPMpy may try to import it at runtime.
    echo          For a clean build, use a fresh venv without gurobipy.
    echo.
)

REM ── Clean previous build ──────────────────────────────────────────────────
echo Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

REM ── Build ─────────────────────────────────────────────────────────────────
echo Running PyInstaller...
pyinstaller ContainerOptimizer.spec --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed. Check output above.
    exit /b 1
)

REM ── Copy user-editable config alongside the exe ───────────────────────────
echo Copying optimizer_config.json alongside the executable...
copy optimizer_config.json dist\ContainerOptimizer\optimizer_config.json

REM ── Explicitly copy any DLLs bundled inside the ortools wheel ─────────────
REM    (belt-and-suspenders alongside PyInstaller collect_all)
REM    These include abseil_dll.dll, re2.dll, etc. that some ortools versions ship.
echo Copying OR-Tools native DLLs...
for /f "delims=" %%i in ('python -c "import ortools, os; print(os.path.dirname(ortools.__file__))"') do set ORTOOLS_DIR=%%i
if defined ORTOOLS_DIR (
    for %%F in ("%ORTOOLS_DIR%\*.dll") do (
        echo   %%~nxF
        copy "%%F" "dist\ContainerOptimizer\" >nul 2>&1
    )
    for %%F in ("%ORTOOLS_DIR%\sat\python\*.dll") do (
        echo   %%~nxF
        copy "%%F" "dist\ContainerOptimizer\" >nul 2>&1
    )
)

echo.
echo ==========================================
echo  Build complete!
echo.
echo  Executable folder : dist\ContainerOptimizer\
echo  Config file       : dist\ContainerOptimizer\optimizer_config.json
echo.
echo  To run   : dist\ContainerOptimizer\ContainerOptimizer.exe
echo  To ship  : zip the entire dist\ContainerOptimizer\ folder
echo.
echo  NOTE: Target Windows machines need the Visual C++ runtime (one-time):
echo    https://aka.ms/vs/17/release/vc_redist.x64.exe
echo  Any modern Windows with Office/Chrome/etc already has this installed.
echo ==========================================
