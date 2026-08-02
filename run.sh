#!/bin/bash
echo "========================================="
echo "      YGGDRASIL SECURITY FRAMEWORK"
echo "========================================="
if [ ! -f ".yggdrasil_auth" ]; then
    read -s -p "Enter System Password: " password
    echo ""
    if [ "$password" != "yggdrasil2026" ]; then
        echo -e "\033[0;31m[!] ACCESS DENIED. INITIATING LOCKDOWN...\033[0m"
        exit 1
    fi
    touch .yggdrasil_auth
fi
echo -e "\033[0;32m[+] ACCESS GRANTED. WELCOME ARCHITECT.\033[0m"

if [ ! -d "venv" ]; then
    echo "Virtual environment (venv) not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "Installing/updating dependencies..."
pip install -r requirements.txt
echo "Starting Yggdrasil Security Framework..."
(sleep 1.5 && xdg-open http://127.0.0.1:8080 || python3 -m webbrowser http://127.0.0.1:8080) >/dev/null 2>&1 &
python3 app.py
