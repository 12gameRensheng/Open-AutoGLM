@echo off
REM Phone Agent EXE Build Script for Windows (Conda Environment)
REM Usage: build_exe.bat [conda_env_name]

setlocal enabledelayedexpansion

echo ============================================
echo Phone Agent EXE Build Script
echo ============================================
echo.

REM Check if conda environment name is provided
set CONDA_ENV=%1
if "%CONDA_ENV%"=="" (
    echo No conda environment specified, using current environment.
) else (
    echo Activating conda environment: %CONDA_ENV%
    call conda activate %CONDA_ENV%
    if errorlevel 1 (
        echo ERROR: Failed to activate conda environment '%CONDA_ENV%'
        echo Please make sure the environment exists.
        exit /b 1
    )
)

REM Check Python version
echo.
echo Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Please ensure Python is installed.
    exit /b 1
)

REM Install/upgrade PyInstaller
echo.
echo Installing/Upgrading PyInstaller...
pip install --upgrade pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller.
    exit /b 1
)

REM Install project dependencies
echo.
echo Installing project dependencies...
pip install -e .
if errorlevel 1 (
    echo WARNING: Failed to install project in editable mode.
    echo Trying to install requirements directly...
    pip install -r requirements.txt
)

REM Install optional dependency
pip install python-dotenv 2>nul

REM Clean previous build
echo.
echo Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Run PyInstaller
echo.
echo Building EXE with PyInstaller...
echo.
pyinstaller phone_agent.spec --clean
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

REM Check if EXE was created
if exist "dist\phone_agent.exe" (
    echo.
    echo ============================================
    echo BUILD SUCCESSFUL!
    echo ============================================
    echo.
    echo EXE location: dist\phone_agent.exe
    echo.

    REM Copy .env.example to dist directory
    if exist ".env.example" (
        copy ".env.example" "dist\.env.example" >nul
        echo Copied .env.example to dist folder.
    )

    REM Copy contact QR code to dist directory
    if exist "contact_qrcode.png" (
        copy "contact_qrcode.png" "dist\contact_qrcode.png" >nul
        echo Copied contact_qrcode.png to dist folder.
    )
    echo.

    echo Usage:
    echo   1. Copy dist\.env.example to dist\.env
    echo   2. Edit dist\.env with your configuration
    echo   3. Run: dist\phone_agent.exe
    echo.
    echo Examples:
    echo   dist\phone_agent.exe --help
    echo   dist\phone_agent.exe --list-devices
    echo   dist\phone_agent.exe "Open Chrome browser"
    echo.

    REM Show file size
    for %%A in ("dist\phone_agent.exe") do (
        set SIZE=%%~zA
        set /a SIZE_MB=!SIZE!/1048576
        echo File size: !SIZE_MB! MB
    )
) else (
    echo.
    echo ERROR: EXE was not created. Check the build output above.
    exit /b 1
)

endlocal
