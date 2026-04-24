@echo off
REM Build script for EBI Windows distribution using PyInstaller
REM Creates ebi.zip containing the packaged application

echo ========================================
echo Building EQUELLA Bulk Importer (Windows)
echo ========================================
echo.

REM Check if Python 3 is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3 and ensure it's in your PATH

    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller not found
    echo Installing PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
    
        exit /b 1
    )
)

REM Clean previous build artifacts
echo Cleaning previous build...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist ebi rmdir /s /q ebi
if exist ebi.zip del /q ebi.zip

REM Build with PyInstaller
echo.
echo Building executable with PyInstaller...
python setup.py
if errorlevel 1 (
    echo ERROR: Build failed

    exit /b 1
)

REM Check if build succeeded
if not exist dist\ebi\ebi.exe (
    echo ERROR: Build succeeded but dist\ebi\ebi.exe not found

    exit /b 1
)

REM Move built directory to ebi for distribution
echo Preparing distribution directory...
move dist\ebi ebi
rmdir dist 2>nul

REM PyInstaller includes everything needed, but copy source files for reference
echo Copying source files for reference...
if not exist ebi\source mkdir ebi\source
copy ..\source\ebi.py ebi\source\ >nul 2>&1
copy ..\source\MainFrame.py ebi\source\ >nul 2>&1
copy ..\source\OptionsDialog.py ebi\source\ >nul 2>&1
copy ..\source\Engine.py ebi\source\ >nul 2>&1
copy ..\source\equellaclient41.py ebi\source\ >nul 2>&1
copy ..\source\ebi.properties ebi\source\ >nul 2>&1

REM Create zip package
echo.
echo Creating distribution archive...
python package.py
if errorlevel 1 (
    echo ERROR: Packaging failed

    exit /b 1
)

REM Verify zip was created
if not exist ebi.zip (
    echo ERROR: ebi.zip was not created

    exit /b 1
)

echo.
echo ========================================
echo Build complete: ebi.zip
echo ========================================
echo.