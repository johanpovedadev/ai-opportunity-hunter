@echo off
echo ============================================================
echo   CONFIGURAR SESION LINKEDIN
echo ============================================================
echo.
echo PASO 1: Abriendo Chrome para que inicies sesion en LinkedIn...
echo         (Si ya ves LinkedIn, solo verificamos la sesion)
echo.
start "" chrome.exe --profile-directory=Default "https://www.linkedin.com/feed/"
echo.
echo PASO 2: Despues de iniciar sesion, cierra Chrome y presiona
echo         cualquier tecla para continuar...
pause > nul
echo.
echo PASO 3: Extrayendo cookies de LinkedIn...
cd /d "%~dp0"
python backend\auth\extract_chrome_cookies.py
echo.
echo PASO 4: Probando la sesion...
if exist data\sessions\linkedin_session.json (
    python -m backend.scripts.cli read-profile
) else (
    echo [FAIL] No se encontro archivo de sesion.
)
echo.
pause
