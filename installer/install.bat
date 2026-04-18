@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   ReckLabs AI Agent  v1.0.0  -  Windows Installer
echo   Your ROI Partner  ^|  recklabs.com
echo ============================================================
echo.

:: ---- Resolve agent directory (one level up from installer\) ----
set "AGENT_DIR=%~dp0.."
pushd "%AGENT_DIR%"
set "AGENT_DIR=%CD%"
popd
echo Agent directory: %AGENT_DIR%

:: ---- Check Python ----
set "PYTHON_EXE="

:: Try common Python installation paths in order of preference
if exist "C:\Python314\python.exe" set "PYTHON_EXE=C:\Python314\python.exe"
if not defined PYTHON_EXE if exist "C:\Python313\python.exe" set "PYTHON_EXE=C:\Python313\python.exe"
if not defined PYTHON_EXE if exist "C:\Python312\python.exe" set "PYTHON_EXE=C:\Python312\python.exe"
if not defined PYTHON_EXE if exist "C:\Python311\python.exe" set "PYTHON_EXE=C:\Python311\python.exe"
if not defined PYTHON_EXE if exist "C:\Python310\python.exe" set "PYTHON_EXE=C:\Python310\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

:: Fall back to PATH
if not defined PYTHON_EXE (
    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=*" %%p in ('where python 2^>nul') do (
            if not defined PYTHON_EXE set "PYTHON_EXE=%%p"
        )
    )
)

if not defined PYTHON_EXE (
    echo ERROR: Python not found.
    echo Please install Python 3.10+ from https://python.org and re-run this installer.
    pause
    exit /b 1
)

"%PYTHON_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python at "%PYTHON_EXE%" is not working.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('"%PYTHON_EXE%" --version 2^>^&1') do set "PY_VER=%%v"
echo Python found: %PY_VER% at %PYTHON_EXE%

:: ---- Install Python dependencies ----
echo.
echo Installing Python dependencies...
"%PYTHON_EXE%" -m pip install --upgrade pip --quiet
"%PYTHON_EXE%" -m pip install -r "%AGENT_DIR%\requirements.txt"
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo Dependencies installed (requests, cryptography, flask, zoho-crm-mcp).

:: ---- Ensure storage and skill directories exist ----
if not exist "%AGENT_DIR%\storage" mkdir "%AGENT_DIR%\storage"
if not exist "%AGENT_DIR%\storage\tokens.json" echo {} > "%AGENT_DIR%\storage\tokens.json"
if not exist "%AGENT_DIR%\storage\license.json" echo {"key": null, "activated": false, "tier": "free"} > "%AGENT_DIR%\storage\license.json"
if not exist "%AGENT_DIR%\skills\base" mkdir "%AGENT_DIR%\skills\base"
if not exist "%AGENT_DIR%\skills\client" mkdir "%AGENT_DIR%\skills\client"

:: ---- Encrypt base skill files (if cryptography is installed) ----
echo.
echo Encrypting base skill files...
"%PYTHON_EXE%" "%AGENT_DIR%\scripts\encrypt_base_skills.py" >nul 2>&1
if errorlevel 1 (
    echo   Note: Base skill encryption skipped ^(cryptography package may need install^).
) else (
    echo   Base skill files encrypted.
)

:: ---- Optional: License Key ----
echo.
set /p "LICENSE_KEY=Enter your ReckLabs license key (press Enter to skip for Free plan): "
if not "%LICENSE_KEY%"=="" (
    echo Activating license key...
    "%PYTHON_EXE%" -c "import sys; sys.path.insert(0,'%AGENT_DIR%'); from config.settings import ensure_storage; ensure_storage(); from license.license_manager import activate_license; r=activate_license('%LICENSE_KEY%'); print('  Plan:', r.get('data',{}).get('plan_name','unknown') if r.get('success') else r.get('message','failed'))"
)

:: ---- Locate Claude Desktop config directory ----
:: Try Windows Store (UWP) path first, then regular install path
set "CLAUDE_CONFIG_DIR="

:: UWP / Windows Store version
for /d %%d in ("%LOCALAPPDATA%\Packages\Claude_*") do (
    if exist "%%d\LocalCache\Roaming\Claude" (
        set "CLAUDE_CONFIG_DIR=%%d\LocalCache\Roaming\Claude"
    )
)

:: Regular install fallback
if not defined CLAUDE_CONFIG_DIR (
    if exist "%APPDATA%\Claude" set "CLAUDE_CONFIG_DIR=%APPDATA%\Claude"
)

if not defined CLAUDE_CONFIG_DIR (
    echo.
    echo WARNING: Claude Desktop config directory not found.
    echo Please install Claude Desktop from https://claude.ai/download
    echo and re-run this installer, OR manually add the MCP config shown below.
    echo.
    goto :show_manual
)

:: ---- Write MCP config ----
set "MCP_CONFIG=%CLAUDE_CONFIG_DIR%\claude_desktop_config.json"
set "AGENT_DIR_JSON=%AGENT_DIR:\=\\%"
set "PYTHON_EXE_JSON=%PYTHON_EXE:\=\\%"

echo.
echo Writing MCP configuration to:
echo   %MCP_CONFIG%

:: Read existing config to preserve preferences (if any)
if exist "%MCP_CONFIG%" (
    set "BACKUP=%MCP_CONFIG%.bak"
    copy "%MCP_CONFIG%" "%BACKUP%" >nul 2>&1
    echo   Existing config backed up to %MCP_CONFIG%.bak
)

(
echo {
echo   "mcpServers": {
echo     "recklabs-ai-agent": {
echo       "command": "%PYTHON_EXE_JSON%",
echo       "args": ["%AGENT_DIR_JSON%\\main.py"]
echo     }
echo   }
echo }
) > "%MCP_CONFIG%"

if errorlevel 1 (
    echo ERROR: Could not write MCP config. Try running as Administrator.
    goto :show_manual
)

echo MCP configuration written successfully.
echo.
echo ============================================================
echo   Installation Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Restart Claude Desktop completely ^(kill all instances^)
echo   2. The 'recklabs-ai-agent' tools will appear in Claude Desktop
echo   3. Test with: "Get platform status"
echo   4. Then say: "Authenticate with Zoho"
echo      Your browser will open Zoho's login page - just log in to your Zoho account.
echo      No credentials to enter. Done.
echo.
echo Config location: %MCP_CONFIG%
echo Agent location:  %AGENT_DIR%
echo Python used:     %PYTHON_EXE%
echo.
pause
exit /b 0

:show_manual
set "AGENT_DIR_JSON=%AGENT_DIR:\=\\%"
set "PYTHON_EXE_JSON=%PYTHON_EXE:\=\\%"
echo ============================================================
echo   Manual MCP Configuration
echo ============================================================
echo.
echo Find your Claude Desktop config file:
echo   Windows Store: %%LOCALAPPDATA%%\Packages\Claude_*\LocalCache\Roaming\Claude\claude_desktop_config.json
echo   Regular:       %%APPDATA%%\Claude\claude_desktop_config.json
echo.
echo Add or merge this into claude_desktop_config.json:
echo.
echo {
echo   "mcpServers": {
echo     "recklabs-ai-agent": {
echo       "command": "%PYTHON_EXE_JSON%",
echo       "args": ["%AGENT_DIR_JSON%\\main.py"]
echo     }
echo   }
echo }
echo.
echo Then restart Claude Desktop.
echo.
pause
exit /b 0
