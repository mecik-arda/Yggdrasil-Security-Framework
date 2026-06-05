#!/bin/bash
if [ ! -d "venv" ]; then
    echo "Virtual environment (venv) not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi
echo "Starting Yggdrasil Security Framework..."
(sleep 1.5 && xdg-open http://127.0.0.1:5000 || python3 -m webbrowser http://127.0.0.1:5000) >/dev/null 2>&1 &
python3 app.py
