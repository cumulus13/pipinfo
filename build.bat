@echo off

:: 1. Clean old files (Use wildcard for egg-info)
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
for /d %%i in (*.egg-info) do rmdir /s /q "%%i"
if exist __pycache__ rmdir /s /q __pycache__

:: 2. Build package
echo Building package...
python setup.py sdist bdist_wheel

:: Check if the build fails, the script stops
if %errorlevel% neq 0 (
    echo [ERROR] Build Failed!
    exit /b %errorlevel%
)

:: 3. Upload ke Private Repo (pypihub)
:: echo Uploading to Private Repo...
:: twine upload dist\* -r pypihub

:: 4. Upload Logic to Public PyPI (Script arguments)
:: IF structure fixed: Space before bracket, and ELSE one line with closing bracket
if "%1"=="" (
    echo [INFO] No Upload to public pypi.org
) else (
    if /i "%1"=="a" (
        echo [INFO] Uploading to Public PyPI...
        twine upload dist\*
    ) else (
        echo [INFO] Argument not recognized, not uploaded to Public PyPI.
    )
)
