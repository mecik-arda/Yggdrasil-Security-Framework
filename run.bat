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
)
call venv\Scripts\activate
echo Installing/updating dependencies...
pip install -r requirements.txt
echo Starting Yggdrasil Security Framework...
python app.py
pause
