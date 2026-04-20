@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   ReckLabs AI Agent  v1.2.0  -  Windows Installer
echo   Zoho Books  ^|  Your ROI Partner  ^|  recklabs.com
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
echo Dependencies installed.

:: ---- Write connector_config.json (v1.2.0, Zoho Books only) ----
"%PYTHON_EXE%" -c "import json; cfg={'_comment':'ReckLabs AI Agent v1.2.0 - Zoho Books direct API (India endpoint, zoho.in). Official Zoho MCP is future work.','version':'1.2.0','selected_connectors':['zoho_books'],'generated_at':'%DATE%','connectors':{'zoho_books':{'mode':'direct_api','enabled':True,'standards':{'country':'IN','tax_system':'GST','default_gst_rate':18,'default_tds_rate':10,'currency':'INR','note':'Demo defaults - verify with your accountant before real use.'}}}}; open(r'%AGENT_DIR%\config\connector_config.json','w').write(json.dumps(cfg,indent=2))"
echo Connector config written (Zoho Books, direct API, India).

:: ---- Ensure storage and skill directories exist ----
if not exist "%AGENT_DIR%\storage" mkdir "%AGENT_DIR%\storage"
if not exist "%AGENT_DIR%\storage\tokens.json" echo {} > "%AGENT_DIR%\storage\tokens.json"
if not exist "%AGENT_DIR%\storage\license.json" echo {"key": null, "activated": false, "tier": "free"} > "%AGENT_DIR%\storage\license.json"
if not exist "%AGENT_DIR%\skills\base" mkdir "%AGENT_DIR%\skills\base"
if not exist "%AGENT_DIR%\skills\base\zoho_books" mkdir "%AGENT_DIR%\skills\base\zoho_books"
if not exist "%AGENT_DIR%\skills\client" mkdir "%AGENT_DIR%\skills\client"
if not exist "%AGENT_DIR%\skills\client\zoho_books" mkdir "%AGENT_DIR%\skills\client\zoho_books"

:: ---- Optional: License Key ----
echo.
set /p "LICENSE_KEY=Enter your ReckLabs license key (press Enter to skip for Free plan): "
if not "%LICENSE_KEY%"=="" (
    echo Activating license key...
    "%PYTHON_EXE%" -c "import sys; sys.path.insert(0,'%AGENT_DIR%'); from config.settings import ensure_storage; ensure_storage(); from license.license_manager import activate_license; r=activate_license('%LICENSE_KEY%'); print('  Plan:', r.get('data',{}).get('plan_name','unknown') if r.get('success') else r.get('message','failed'))"
)

:: ---- Locate Claude Desktop config directory ----
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
echo   1. Add your Zoho OAuth credentials to: %AGENT_DIR%\.env
echo      ZOHO_CLIENT_ID=your_client_id
echo      ZOHO_CLIENT_SECRET=your_client_secret
echo      ZOHO_REDIRECT_URI=http://localhost:8000/callback
echo      (Get these from Zoho API Console: https://api-console.zoho.in/)
echo.
echo   2. Restart Claude Desktop completely (kill all instances)
echo.
echo   3. In Claude Desktop, say: "Authenticate with Zoho Books"
echo      Your browser will open the Zoho login page.
echo      Log in with your Zoho account. Done.
echo.
echo   4. Try: "Show my invoices" or "Review expenses"
echo.
echo Important notes:
echo   - Default GST: 18%%, Default TDS: 10%%, Currency: INR
echo   - These are demo defaults. Verify with your accountant before real filings.
echo   - Data domain: India (zoho.in)
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
echo Then:
echo   1. Add Zoho credentials to %AGENT_DIR%\.env
echo   2. Restart Claude Desktop
echo   3. Say "Authenticate with Zoho Books" in Claude Desktop
echo.
pause
exit /b 0
