import subprocess
import platform
import os
import time

def handle_mimir_scanner(target, data):
    current_os = platform.system()
    runes_dir = os.path.join(os.getcwd(), 'Runes', 'mimir-scanner')
    frontend_dir = os.path.join(runes_dir, 'frontend')
    
    if not os.path.exists(runes_dir):
        return ">> ERROR: Mimir Scanner directory not found. Please sync runes."

    try:
        if current_os == 'Windows':
            # Run Spring Boot backend in a new command window
            subprocess.Popen('start "Mimir Backend" cmd /c "mvn spring-boot:run"', shell=True, cwd=runes_dir)
            time.sleep(3)
            # Run React frontend in another window
            subprocess.Popen('start "Mimir Frontend" cmd /c "npm install && npm start"', shell=True, cwd=frontend_dir)
        else:
            # Run in terminal using x-terminal-emulator or gnome-terminal
            subprocess.Popen(['x-terminal-emulator', '-e', 'bash -c "mvn spring-boot:run"'], cwd=runes_dir)
            time.sleep(3)
            subprocess.Popen(['x-terminal-emulator', '-e', 'bash -c "npm install && npm start"'], cwd=frontend_dir)
            
        return ">> INITIATING MIMIR SCANNER (REAL-TIME TRAFFIC ANALYZER)...\n>> PLEASE CHECK YOUR NEW TERMINAL WINDOWS AND BROWSER.\n>> BACKEND PORT: 8080 | FRONTEND PORT: 3000"
    except Exception as e:
        return f"System Error: {str(e)}"
