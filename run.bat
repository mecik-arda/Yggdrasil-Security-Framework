@echo off
color 0A
echo =========================================
echo       YGGDRASIL SECURITY FRAMEWORK
echo =========================================
if exist .yggdrasil_auth goto :authorized
set /p "password=Enter System Password: "
if not "%password%"=="yggdrasil2026" (
    color 0C
    echo.
    echo [!] ACCESS DENIED. INITIATING LOCKDOWN...
    pause
    exit /b
)
echo yggdrasil > .yggdrasil_auth
:authorized
echo.
echo [+] ACCESS GRANTED. WELCOME ARCHITECT.
if not exist venv (
    echo Virtual environment ^(venv^) not found!
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)
echo Starting Yggdrasil Security Framework...
start "" "http://127.0.0.1:5000"
python app.py
pause
