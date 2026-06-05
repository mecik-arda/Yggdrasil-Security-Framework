@echo off
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
